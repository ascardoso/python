#!/usr/bin/env python3

"""
Safari Bookmark Browser / Cleaner

Usage:
    python3 bookmark_browser.py bookmarks.html

Required:
    Python 3
    PyObjC

Install:
    python3 -m pip install pyobjc

Features:
    - Native macOS UI
    - Left bookmark navigator
    - Right-hand WebKit page viewer
    - Alphabetical sorting
    - Duplicate URL removal
    - Empty-folder removal
    - Search
    - Back / Forward / Reload
    - Background link checker
    - Persistent link-check results
    - Remove non-working links
    - Save cleaned bookmarks as Safari-compatible HTML
    - Original bookmarks.html is never modified automatically

Persistent checker data:

    bookmarks.html
    bookmarks.linkcheck.json
"""

import sys
import json
import html
import threading
import urllib.request
import urllib.error

from pathlib import Path
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urlsplit, urlunsplit

import objc

from Foundation import (
    NSObject,
    NSURL,
    NSURLRequest,
)

from AppKit import (
    NSAlert,
    NSApplication,
    NSApplicationActivationPolicyRegular,
    NSBackingStoreBuffered,
    NSButton,
    NSFont,
    NSMenu,
    NSMenuItem,
    NSMakeRect,
    NSOutlineView,
    NSSavePanel,
    NSOpenPanel,
    NSScrollView,
    NSSplitView,
    NSTextField,
    NSTableColumn,
    NSView,
    NSWindow,
    NSWindowStyleMaskClosable,
    NSWindowStyleMaskMiniaturizable,
    NSWindowStyleMaskResizable,
    NSWindowStyleMaskTitled,
)

from WebKit import (
    WKWebView,
    WKWebViewConfiguration,
)


# ============================================================
# Bookmark model
# ============================================================

class Bookmark:

    def __init__(self, title, url):

        self.title = title or url
        self.url = url

        self.status = "unchecked"
        self.status_code = None
        self.final_url = None
        self.error = None
        self.checked = None


class Folder:

    def __init__(self, title):

        self.title = title
        self.items = []


# ============================================================
# Safari / Netscape bookmark parser
# ============================================================

class BookmarkParser(HTMLParser):

    def __init__(self):

        super().__init__(
            convert_charrefs=True
        )

        self.root = Folder("Bookmarks")
        self.stack = [self.root]

        self.in_h3 = False
        self.in_a = False

        self.folder_title = ""
        self.bookmark_title = ""
        self.bookmark_url = ""

    def handle_starttag(self, tag, attrs):

        tag = tag.lower()
        attrs = dict(attrs)

        if tag == "h3":

            self.in_h3 = True
            self.folder_title = ""

        elif tag == "a":

            self.in_a = True
            self.bookmark_title = ""
            self.bookmark_url = attrs.get(
                "href",
                ""
            )

    def handle_data(self, data):

        if self.in_h3:

            self.folder_title += data

        elif self.in_a:

            self.bookmark_title += data

    def handle_endtag(self, tag):

        tag = tag.lower()

        if tag == "h3":

            self.in_h3 = False

            folder = Folder(
                self.folder_title.strip()
            )

            self.stack[-1].items.append(
                folder
            )

            self.stack.append(folder)

        elif tag == "a":

            self.in_a = False

            if self.bookmark_url.strip():

                bookmark = Bookmark(
                    self.bookmark_title.strip(),
                    self.bookmark_url.strip()
                )

                self.stack[-1].items.append(
                    bookmark
                )

        elif tag == "dl":

            if len(self.stack) > 1:

                self.stack.pop()


def load_bookmarks(path):

    text = Path(path).read_text(
        encoding="utf-8",
        errors="replace"
    )

    parser = BookmarkParser()
    parser.feed(text)

    return parser.root


# ============================================================
# URL utilities
# ============================================================

def normalize_url(url):

    url = url.strip()

    try:

        parts = urlsplit(url)

        path = parts.path

        if path == "/":

            path = ""

        elif path.endswith("/"):

            path = path.rstrip("/")

        return urlunsplit(
            (
                parts.scheme.lower(),
                parts.netloc.lower(),
                path,
                parts.query,
                parts.fragment,
            )
        )

    except Exception:

        return url


# ============================================================
# Bookmark utilities
# ============================================================

def get_all_bookmarks(folder):

    result = []

    for item in folder.items:

        if isinstance(item, Bookmark):

            result.append(item)

        elif isinstance(item, Folder):

            result.extend(
                get_all_bookmarks(item)
            )

    return result


def count_bookmarks(folder):

    return len(
        get_all_bookmarks(folder)
    )


def count_folders(folder):

    result = 0

    for item in folder.items:

        if isinstance(item, Folder):

            result += 1
            result += count_folders(item)

    return result


def dedupe_folder(folder, seen=None):

    if seen is None:

        seen = set()

    cleaned = []
    removed = 0

    for item in folder.items:

        if isinstance(item, Bookmark):

            key = normalize_url(
                item.url
            )

            if key in seen:

                removed += 1
                continue

            seen.add(key)
            cleaned.append(item)

        elif isinstance(item, Folder):

            removed += dedupe_folder(
                item,
                seen
            )

            # Empty folders are deliberately omitted.
            if item.items:

                cleaned.append(item)

    folder.items = cleaned

    return removed


def sort_folder(folder):

    for item in folder.items:

        if isinstance(item, Folder):

            sort_folder(item)

    folder.items.sort(
        key=lambda x: x.title.casefold()
    )


def filter_folder(folder, query):

    if not query:

        return folder

    query = query.casefold()

    result = Folder(folder.title)

    for item in folder.items:

        if isinstance(item, Bookmark):

            if (
                query in item.title.casefold()
                or
                query in item.url.casefold()
            ):

                result.items.append(item)

        else:

            if query in item.title.casefold():

                result.items.append(item)

            else:

                child = filter_folder(
                    item,
                    query
                )

                if child.items:

                    result.items.append(child)

    return result


# ============================================================
# Persistent link-check store
# ============================================================

class LinkCheckStore:

    def __init__(self, bookmarks_file):

        path = Path(bookmarks_file)

        self.path = (
            path.parent
            /
            f"{path.stem}.linkcheck.json"
        )

        self.data = {}

        self.load()

    def load(self):

        if not self.path.exists():

            return

        try:

            with self.path.open(
                "r",
                encoding="utf-8"
            ) as f:

                value = json.load(f)

            if isinstance(value, dict):

                self.data = value

        except Exception as e:

            print(
                f"WARNING: Could not load "
                f"{self.path}: {e}",
                file=sys.stderr
            )

    def save(self):

        temporary = self.path.with_suffix(
            ".tmp"
        )

        try:

            with temporary.open(
                "w",
                encoding="utf-8"
            ) as f:

                json.dump(
                    self.data,
                    f,
                    indent=2,
                    ensure_ascii=False,
                    sort_keys=True
                )

            temporary.replace(self.path)

        except Exception as e:

            print(
                f"WARNING: Could not save "
                f"{self.path}: {e}",
                file=sys.stderr
            )

            try:
                temporary.unlink(
                    missing_ok=True
                )
            except Exception:
                pass

    def restore(self, bookmarks):

        count = 0

        for bookmark in bookmarks:

            key = normalize_url(
                bookmark.url
            )

            record = self.data.get(key)

            if not isinstance(record, dict):

                continue

            bookmark.status = record.get(
                "status",
                "unchecked"
            )

            bookmark.status_code = record.get(
                "status_code"
            )

            bookmark.final_url = record.get(
                "final_url"
            )

            bookmark.error = record.get(
                "error"
            )

            bookmark.checked = record.get(
                "checked"
            )

            count += 1

        return count

    def update(self, bookmark):

        key = normalize_url(
            bookmark.url
        )

        self.data[key] = {
            "status": bookmark.status,
            "status_code": bookmark.status_code,
            "final_url": bookmark.final_url,
            "error": bookmark.error,
            "checked": bookmark.checked,
        }

    def remove(self, bookmark):

        self.data.pop(
            normalize_url(bookmark.url),
            None
        )


# ============================================================
# Link checker
# ============================================================

class LinkChecker:

    def __init__(self, browser):

        self.browser = browser
        self.running = False
        self.stop_requested = False

    def start(self):

        if self.running:

            return

        self.running = True
        self.stop_requested = False

        thread = threading.Thread(
            target=self.check_all,
            daemon=True
        )

        thread.start()

    def stop(self):

        self.stop_requested = True

    def check_all(self):

        bookmarks = get_all_bookmarks(
            self.browser.bookmarks
        )

        total = len(bookmarks)

        print(
            f"\nChecking {total} bookmarks...\n"
        )

        for number, bookmark in enumerate(
            bookmarks,
            1
        ):

            if self.stop_requested:

                print(
                    "\nLink check stopped."
                )

                break

            bookmark.status = "checking"

            self.notify(
                bookmark
            )

            self.check_bookmark(
                bookmark
            )

            bookmark.checked = (
                datetime.now(
                    timezone.utc
                ).isoformat()
            )

            self.browser.link_store.update(
                bookmark
            )

            # Save after every result. This makes the
            # checker resilient to interruption.
            self.browser.link_store.save()

            self.notify(
                bookmark
            )

            print(
                f"[{number}/{total}] "
                f"{bookmark.status:13} "
                f"{str(bookmark.status_code or '-'):4} "
                f"{bookmark.url}"
            )

        self.running = False

        self.browser.performSelectorOnMainThread_withObject_waitUntilDone_(
            "linkCheckFinished:",
            None,
            False
        )

    def notify(self, bookmark):

        self.browser.performSelectorOnMainThread_withObject_waitUntilDone_(
            "linkCheckUpdated:",
            bookmark,
            False
        )

    def check_bookmark(self, bookmark):

        url = bookmark.url.strip()

        if not url.startswith(
            (
                "http://",
                "https://"
            )
        ):

            bookmark.status = "skipped"
            bookmark.status_code = None
            bookmark.final_url = None
            bookmark.error = (
                "Not an HTTP/HTTPS URL"
            )

            return

        headers = {
            "User-Agent":
                "Mozilla/5.0 "
                "(Macintosh; Intel Mac OS X) "
                "AppleWebKit/605.1.15 "
                "(KHTML, like Gecko) "
                "Version/18.0 Safari/605.1.15",

            "Accept":
                "*/*",
        }

        # First try HEAD.
        try:

            request = urllib.request.Request(
                url,
                headers=headers,
                method="HEAD"
            )

            with urllib.request.urlopen(
                request,
                timeout=15
            ) as response:

                self.record_response(
                    bookmark,
                    response
                )

                return

        except urllib.error.HTTPError as e:

            if e.code not in (405, 501):

                self.record_http_error(
                    bookmark,
                    e
                )

                return

        except Exception:

            pass

        # Fall back to GET.
        try:

            request = urllib.request.Request(
                url,
                headers=headers,
                method="GET"
            )

            with urllib.request.urlopen(
                request,
                timeout=15
            ) as response:

                self.record_response(
                    bookmark,
                    response
                )

        except urllib.error.HTTPError as e:

            self.record_http_error(
                bookmark,
                e
            )

        except urllib.error.URLError as e:

            bookmark.status = "error"
            bookmark.status_code = None
            bookmark.final_url = None
            bookmark.error = str(e.reason)

        except Exception as e:

            bookmark.status = "error"
            bookmark.status_code = None
            bookmark.final_url = None
            bookmark.error = str(e)

    def record_response(
        self,
        bookmark,
        response
    ):

        code = response.status

        bookmark.status_code = code
        bookmark.final_url = response.geturl()
        bookmark.error = None

        if 200 <= code < 300:

            bookmark.status = "ok"

        elif 300 <= code < 400:

            bookmark.status = "redirect"

        elif code == 404:

            bookmark.status = "404"

        elif 400 <= code < 500:

            bookmark.status = "client-error"

        elif 500 <= code < 600:

            bookmark.status = "server-error"

        else:

            bookmark.status = "unknown"

    def record_http_error(
        self,
        bookmark,
        error
    ):

        code = error.code

        bookmark.status_code = code

        try:

            bookmark.final_url = error.geturl()

        except Exception:

            bookmark.final_url = None

        bookmark.error = str(error)

        if code == 404:

            bookmark.status = "404"

        elif 400 <= code < 500:

            bookmark.status = "client-error"

        elif 500 <= code < 600:

            bookmark.status = "server-error"

        else:

            bookmark.status = "error"


# ============================================================
# Outline data source / delegate
# ============================================================

class OutlineController(NSObject):

    def init(self):

        self = objc.super(
            OutlineController,
            self
        ).init()

        if self is None:

            return None

        self.root = None
        self.outline = None
        self.browser = None

        return self

    def outlineView_numberOfChildrenOfItem_(
        self,
        outline,
        item
    ):

        if item is None:

            return len(self.root.items)

        return len(item.items)

    def outlineView_isItemExpandable_(
        self,
        outline,
        item
    ):

        return (
            isinstance(item, Folder)
            and
            bool(item.items)
        )

    def outlineView_child_ofItem_(
        self,
        outline,
        index,
        item
    ):

        if item is None:

            return self.root.items[index]

        return item.items[index]

    def outlineView_viewForTableColumn_item_(
        self,
        outline,
        column,
        item
    ):

        identifier = "BookmarkCell"

        cell = (
            outline
            .makeViewWithIdentifier_owner_(
                identifier,
                self
            )
        )

        if cell is None:

            cell = (
                NSTextField
                .labelWithString_("")
            )

            cell.setIdentifier_(
                identifier
            )

        if isinstance(item, Folder):

            cell.setStringValue_(
                "📁  " + item.title
            )

            cell.setFont_(
                NSFont.boldSystemFontOfSize_(13)
            )

        else:

            icons = {
                "unchecked": "⚪",
                "checking": "🔵",
                "ok": "🟢",
                "redirect": "🟡",
                "404": "🔴",
                "client-error": "🔴",
                "server-error": "🟠",
                "error": "🔴",
                "skipped": "⚪",
                "unknown": "⚪",
            }

            icon = icons.get(
                item.status,
                "⚪"
            )

            cell.setStringValue_(
                f"{icon}  {item.title}"
            )

            cell.setFont_(
                NSFont.systemFontOfSize_(13)
            )

        return cell

    def outlineViewSelectionDidChange_(
        self,
        notification
    ):

        row = self.outline.selectedRow()

        if row < 0:

            return

        item = (
            self.outline.itemAtRow_(row)
        )

        if isinstance(item, Bookmark):

            self.browser.show_bookmark(
                item
            )


# ============================================================
# Main application window
# ============================================================

class BookmarkBrowser(NSObject):

    def initWithBookmarks_store_(
        self,
        bookmarks,
        link_store
    ):

        self = objc.super(
            BookmarkBrowser,
            self
        ).init()

        if self is None:

            return None

        self.bookmarks = bookmarks
        self.filtered_bookmarks = bookmarks
        self.link_store = link_store

        self.window = None
        self.outline = None
        self.webview = None
        self.url_field = None
        self.search_field = None
        self.controller = None

        self.link_checker = LinkChecker(self)

        return self

    # ========================================================
    # Build UI
    # ========================================================

    def build(self):

        width = 1400
        height = 900

        style = (
            NSWindowStyleMaskTitled
            |
            NSWindowStyleMaskClosable
            |
            NSWindowStyleMaskMiniaturizable
            |
            NSWindowStyleMaskResizable
        )

        self.window = (
            NSWindow.alloc()
            .initWithContentRect_styleMask_backing_defer_(
                NSMakeRect(
                    100,
                    100,
                    width,
                    height
                ),
                style,
                NSBackingStoreBuffered,
                False
            )
        )

        self.window.setTitle_(
            "Safari Bookmark Browser"
        )

        self.window.setMinSize_(
            (900, 600)
        )

        content = self.window.contentView()

        # ----------------------------------------------------
        # Search field
        # ----------------------------------------------------

        self.search_field = (
            NSTextField.alloc()
            .initWithFrame_(
                NSMakeRect(
                    10,
                    height - 40,
                    350,
                    30
                )
            )
        )

        self.search_field.setPlaceholderString_(
            "Search bookmarks…"
        )

        self.search_field.setTarget_(self)
        self.search_field.setAction_(
            "searchChanged:"
        )

        content.addSubview_(
            self.search_field
        )

        # ----------------------------------------------------
        # URL field
        # ----------------------------------------------------

        self.url_field = (
            NSTextField.alloc()
            .initWithFrame_(
                NSMakeRect(
                    370,
                    height - 40,
                    700,
                    30
                )
            )
        )

        self.url_field.setPlaceholderString_(
            "URL"
        )

        self.url_field.setTarget_(self)
        self.url_field.setAction_("go:")

        content.addSubview_(
            self.url_field
        )

        # ----------------------------------------------------
        # Navigation buttons
        # ----------------------------------------------------

        buttons = [
            ("←", 1080, "goBack:"),
            ("→", 1140, "goForward:"),
            ("Reload", 1200, "reload:"),
        ]

        for title, x, action in buttons:

            width_button = (
                55 if title in ("←", "→")
                else 70
            )

            button = (
                NSButton.alloc()
                .initWithFrame_(
                    NSMakeRect(
                        x,
                        height - 40,
                        width_button,
                        30
                    )
                )
            )

            button.setTitle_(title)
            button.setTarget_(self)
            button.setAction_(action)

            content.addSubview_(button)

        # ----------------------------------------------------
        # Split view
        # ----------------------------------------------------

        split = (
            NSSplitView.alloc()
            .initWithFrame_(
                NSMakeRect(
                    0,
                    0,
                    width,
                    height - 50
                )
            )
        )

        split.setVertical_(True)

        content.addSubview_(split)

        # ----------------------------------------------------
        # Left pane
        # ----------------------------------------------------

        left = (
            NSScrollView.alloc()
            .initWithFrame_(
                NSMakeRect(
                    0,
                    0,
                    350,
                    height - 50
                )
            )
        )

        left.setHasVerticalScroller_(True)
        left.setHasHorizontalScroller_(True)

        self.outline = (
            NSOutlineView.alloc()
            .initWithFrame_(
                NSMakeRect(
                    0,
                    0,
                    350,
                    height - 50
                )
            )
        )

        column = (
            NSTableColumn.alloc()
            .initWithIdentifier_(
                "BookmarkColumn"
            )
        )

        column.setWidth_(340)

        self.outline.addTableColumn_(
            column
        )

        self.outline.setOutlineTableColumn_(
            column
        )

        self.outline.setHeaderView_(None)
        self.outline.setRowHeight_(24)

        left.setDocumentView_(
            self.outline
        )

        split.addSubview_(left)

        # ----------------------------------------------------
        # Right pane
        # ----------------------------------------------------

        right = (
            NSView.alloc()
            .initWithFrame_(
                NSMakeRect(
                    0,
                    0,
                    1050,
                    height - 50
                )
            )
        )

        split.addSubview_(right)

        configuration = (
            WKWebViewConfiguration
            .alloc()
            .init()
        )

        self.webview = (
            WKWebView.alloc()
            .initWithFrame_configuration_(
                NSMakeRect(
                    0,
                    0,
                    1050,
                    height - 50
                ),
                configuration
            )
        )

        self.webview.setAutoresizingMask_(18)

        right.addSubview_(
            self.webview
        )

        # ----------------------------------------------------
        # Outline controller
        # ----------------------------------------------------

        self.controller = (
            OutlineController
            .alloc()
            .init()
        )

        self.controller.root = (
            self.filtered_bookmarks
        )

        self.controller.outline = (
            self.outline
        )

        self.controller.browser = self

        self.outline.setDataSource_(
            self.controller
        )

        self.outline.setDelegate_(
            self.controller
        )

        # ----------------------------------------------------
        # Menus
        # ----------------------------------------------------

        self.build_menu()

        self.window.center()

        self.window.makeKeyAndOrderFront_(None)

        NSApplication.sharedApplication().activateIgnoringOtherApps_(
            True
        )

        self.outline.reloadData()

        self.expand_visible_folders()

    # ========================================================
    # Menus
    # ========================================================

    def build_menu(self):

        main_menu = (
            NSMenu.alloc().init()
        )

        # ----------------------------------------------------
        # File
        # ----------------------------------------------------

        file_menu = (
            NSMenu.alloc()
            .initWithTitle_("File")
        )

        save_item = (
            NSMenuItem.alloc()
            .initWithTitle_action_keyEquivalent_(
                "Save Cleaned Bookmarks…",
                "saveBookmarks:",
                "s"
            )
        )

        save_item.setTarget_(self)

        file_menu.addItem_(
            save_item
        )

        file_menu.addItem_(
            NSMenuItem.separatorItem()
        )

        quit_item = (
            NSMenuItem.alloc()
            .initWithTitle_action_keyEquivalent_(
                "Quit",
                "terminate:",
                "q"
            )
        )

        file_menu.addItem_(
            quit_item
        )

        file_root = (
            NSMenuItem.alloc()
            .initWithTitle_action_keyEquivalent_(
                "File",
                "",
                ""
            )
        )

        main_menu.addItem_(file_root)

        main_menu.setSubmenu_forItem_(
            file_menu,
            file_root
        )

        # ----------------------------------------------------
        # Bookmarks
        # ----------------------------------------------------

        bookmark_menu = (
            NSMenu.alloc()
            .initWithTitle_("Bookmarks")
        )

        check_item = (
            NSMenuItem.alloc()
            .initWithTitle_action_keyEquivalent_(
                "Check All Links",
                "checkLinks:",
                "l"
            )
        )

        # Command-Shift-L
        check_item.setKeyEquivalentModifierMask_(
            (1 << 20) | (1 << 17)
        )

        check_item.setTarget_(self)

        bookmark_menu.addItem_(
            check_item
        )

        stop_item = (
            NSMenuItem.alloc()
            .initWithTitle_action_keyEquivalent_(
                "Stop Link Check",
                "stopLinkCheck:",
                ""
            )
        )

        stop_item.setTarget_(self)

        bookmark_menu.addItem_(
            stop_item
        )

        bookmark_menu.addItem_(
            NSMenuItem.separatorItem()
        )

        remove_item = (
            NSMenuItem.alloc()
            .initWithTitle_action_keyEquivalent_(
                "Remove Non-Working Links…",
                "removeNonWorking:",
                ""
            )
        )

        remove_item.setTarget_(self)

        bookmark_menu.addItem_(
            remove_item
        )

        reset_item = (
            NSMenuItem.alloc()
            .initWithTitle_action_keyEquivalent_(
                "Reset Link Status",
                "resetLinkStatus:",
                ""
            )
        )

        reset_item.setTarget_(self)

        bookmark_menu.addItem_(
            reset_item
        )

        bookmark_root = (
            NSMenuItem.alloc()
            .initWithTitle_action_keyEquivalent_(
                "Bookmarks",
                "",
                ""
            )
        )

        main_menu.addItem_(
            bookmark_root
        )

        main_menu.setSubmenu_forItem_(
            bookmark_menu,
            bookmark_root
        )

        NSApplication.sharedApplication().setMainMenu_(
            main_menu
        )

    # ========================================================
    # IMPORTANT:
    # Explicit menu validation fixes the disabled-menu
    # problem from the previous version.
    # ========================================================

    def validateMenuItem_(
        self,
        menu_item
    ):

        action = menu_item.action()

        if action == "checkLinks:":

            return not self.link_checker.running

        if action == "stopLinkCheck:":

            return self.link_checker.running

        if action == "removeNonWorking:":

            if self.link_checker.running:

                return False

            return self.number_of_non_working() > 0

        if action == "resetLinkStatus:":

            return not self.link_checker.running

        if action == "saveBookmarks:":

            return not self.link_checker.running

        return True

    # ========================================================
    # Link checking
    # ========================================================

    def checkLinks_(self, sender):

        self.link_checker.start()

    def stopLinkCheck_(self, sender):

        self.link_checker.stop()

    def linkCheckUpdated_(self, bookmark):

        self.outline.reloadData()

    def linkCheckFinished_(self, sender):

        self.outline.reloadData()

        print(
            "\nLink check complete."
        )

        self.show_info(
            "Link Check Complete",
            "The link-check results have been saved."
        )

    # ========================================================
    # Determine what is considered non-working
    # ========================================================

    def is_non_working(self, bookmark):

        return bookmark.status in (
            "404",
            "client-error",
            "error",
        )

    def number_of_non_working(self):

        return sum(
            1
            for bookmark in get_all_bookmarks(
                self.bookmarks
            )
            if self.is_non_working(bookmark)
        )

    # ========================================================
    # Remove non-working links
    # ========================================================

    def removeNonWorking_(self, sender):

        if self.link_checker.running:

            return

        bookmarks = get_all_bookmarks(
            self.bookmarks
        )

        dead = [
            bookmark
            for bookmark in bookmarks
            if self.is_non_working(bookmark)
        ]

        if not dead:

            self.show_info(
                "No Non-Working Links",
                "There are no bookmarks currently "
                "marked as non-working."
            )

            return

        # Build confirmation text.
        lines = []

        for bookmark in dead[:25]:

            code = (
                str(bookmark.status_code)
                if bookmark.status_code
                else bookmark.status
            )

            lines.append(
                f"• {bookmark.title} "
                f"({code})"
            )

        if len(dead) > 25:

            lines.append(
                f"… and {len(dead) - 25} more"
            )

        message = (
            f"{len(dead)} bookmark"
            f"{'s' if len(dead) != 1 else ''} "
            "are currently marked as non-working."
            "\n\n"
            +
            "\n".join(lines)
            +
            "\n\n"
            "Redirects and server errors are NOT included."
        )

        alert = (
            NSAlert.alloc()
            .init()
        )

        alert.setMessageText_(
            "Remove Non-Working Links?"
        )

        alert.setInformativeText_(
            message
        )

        alert.addButtonWithTitle_(
            f"Remove {len(dead)}"
        )

        alert.addButtonWithTitle_(
            "Cancel"
        )

        alert.setAlertStyle_(2)

        response = alert.runModal()

        # First button means remove.
        if response != 1000:

            return

        dead_keys = {
            normalize_url(bookmark.url)
            for bookmark in dead
        }

        self.remove_urls_from_folder(
            self.bookmarks,
            dead_keys
        )

        # Remove their persistent check records.
        for bookmark in dead:

            self.link_store.remove(
                bookmark
            )

        self.link_store.save()

        # Keep tree sorted and remove any folders
        # that became empty.
        self.remove_empty_folders(
            self.bookmarks
        )

        sort_folder(
            self.bookmarks
        )

        self.filtered_bookmarks = (
            filter_folder(
                self.bookmarks,
                self.search_field.stringValue()
            )
        )

        self.controller.root = (
            self.filtered_bookmarks
        )

        self.outline.reloadData()

        self.expand_visible_folders()

        self.show_info(
            "Bookmarks Removed",
            f"{len(dead)} non-working bookmark"
            f"{'s were' if len(dead) != 1 else ' was'} removed."
        )

    def remove_urls_from_folder(
        self,
        folder,
        urls
    ):

        remaining = []

        for item in folder.items:

            if isinstance(item, Bookmark):

                if normalize_url(item.url) not in urls:

                    remaining.append(item)

            else:

                self.remove_urls_from_folder(
                    item,
                    urls
                )

                if item.items:

                    remaining.append(item)

        folder.items = remaining

    def remove_empty_folders(self, folder):

        remaining = []

        for item in folder.items:

            if isinstance(item, Folder):

                self.remove_empty_folders(
                    item
                )

                if item.items:

                    remaining.append(item)

            else:

                remaining.append(item)

        folder.items = remaining

    # ========================================================
    # Reset link status
    # ========================================================

    def resetLinkStatus_(self, sender):

        if self.link_checker.running:

            return

        bookmarks = get_all_bookmarks(
            self.bookmarks
        )

        for bookmark in bookmarks:

            bookmark.status = "unchecked"
            bookmark.status_code = None
            bookmark.final_url = None
            bookmark.error = None
            bookmark.checked = None

            self.link_store.remove(
                bookmark
            )

        self.link_store.save()

        self.outline.reloadData()

    # ========================================================
    # Save cleaned Safari bookmark HTML
    # ========================================================

    def saveBookmarks_(self, sender):

        if self.link_checker.running:

            return

        panel = (
            NSSavePanel.savePanel()
        )

        panel.setTitle_(
            "Save Cleaned Bookmarks"
        )

        panel.setMessage_(
            "Save the cleaned Safari bookmark collection."
        )

        panel.setNameFieldStringValue_(
            "bookmarks-cleaned.html"
        )

        panel.setCanCreateDirectories_(True)

        panel.setAllowedFileTypes_(
            ["html", "htm"]
        )

        response = panel.runModal()

        if response != 1:

            return

        url = panel.URL()

        if url is None:

            return

        path = Path(
            url.path()
        )

        try:

            save_bookmarks_html(
                self.bookmarks,
                path
            )

            self.show_info(
                "Bookmarks Saved",
                f"Saved {count_bookmarks(self.bookmarks)} "
                f"bookmarks to:\n{path}"
            )

            print(
                f"\nSaved cleaned bookmarks to:\n{path}"
            )

        except Exception as e:

            self.show_error(
                "Save Failed",
                str(e)
            )

    # ========================================================
    # Browser
    # ========================================================

    def show_bookmark(self, bookmark):

        url = bookmark.url.strip()

        if not url:

            return

        if not url.startswith(
            (
                "http://",
                "https://",
                "file://"
            )
        ):

            url = "https://" + url

        self.url_field.setStringValue_(
            url
        )

        nsurl = NSURL.URLWithString_(
            url
        )

        if nsurl is None:

            return

        request = (
            NSURLRequest.requestWithURL_(
                nsurl
            )
        )

        self.webview.loadRequest_(
            request
        )

    def go_(self, sender):

        url = (
            self.url_field
            .stringValue()
            .strip()
        )

        if not url:

            return

        if not url.startswith(
            (
                "http://",
                "https://",
                "file://"
            )
        ):

            url = "https://" + url

        self.url_field.setStringValue_(
            url
        )

        nsurl = NSURL.URLWithString_(
            url
        )

        if nsurl is None:

            return

        request = (
            NSURLRequest.requestWithURL_(
                nsurl
            )
        )

        self.webview.loadRequest_(
            request
        )

    def goBack_(self, sender):

        if self.webview.canGoBack():

            self.webview.goBack()

    def goForward_(self, sender):

        if self.webview.canGoForward():

            self.webview.goForward()

    def reload_(self, sender):

        self.webview.reload()

    # ========================================================
    # Search
    # ========================================================

    def searchChanged_(self, sender):

        query = (
            self.search_field
            .stringValue()
            .strip()
        )

        self.filtered_bookmarks = (
            filter_folder(
                self.bookmarks,
                query
            )
        )

        self.controller.root = (
            self.filtered_bookmarks
        )

        self.outline.reloadData()

        self.expand_visible_folders()

    # ========================================================
    # UI helpers
    # ========================================================

    def expand_visible_folders(self):

        for item in self.filtered_bookmarks.items:

            if isinstance(item, Folder):

                self.outline.expandItem_(
                    item
                )

    def show_info(
        self,
        title,
        message
    ):

        alert = (
            NSAlert.alloc()
            .init()
        )

        alert.setMessageText_(title)
        alert.setInformativeText_(message)

        alert.addButtonWithTitle_("OK")

        alert.runModal()

    def show_error(
        self,
        title,
        message
    ):

        alert = (
            NSAlert.alloc()
            .init()
        )

        alert.setMessageText_(title)
        alert.setInformativeText_(message)

        alert.setAlertStyle_(2)

        alert.addButtonWithTitle_("OK")

        alert.runModal()


# ============================================================
# Safari bookmark HTML writer
# ============================================================

def save_bookmarks_html(
    root,
    path
):

    """
    Write a Safari-compatible Netscape bookmark HTML file.

    The structure is intentionally compatible with Safari's
    exported bookmarks.html format.
    """

    now = int(
        datetime.now().timestamp()
    )

    lines = [
        "<!DOCTYPE NETSCAPE-Bookmark-file-1>",
        "<META HTTP-EQUIV=\"Content-Type\" "
        "CONTENT=\"text/html; charset=UTF-8\">",
        "<TITLE>Bookmarks</TITLE>",
        "<H1>Bookmarks</H1>",
        "<DL><p>",
    ]

    def write_folder(
        folder,
        indent
    ):

        pad = "    " * indent

        # Do not write empty folders.
        if not folder.items:

            return

        title = html.escape(
            folder.title,
            quote=False
        )

        lines.append(
            f'{pad}<DT><H3 ADD_DATE="{now}">'
            f'{title}</H3>'
        )

        lines.append(
            f"{pad}<DL><p>"
        )

        for item in folder.items:

            if isinstance(item, Bookmark):

                bookmark_title = html.escape(
                    item.title,
                    quote=False
                )

                bookmark_url = html.escape(
                    item.url,
                    quote=True
                )

                lines.append(
                    f'{pad}    <DT><A HREF="{bookmark_url}" '
                    f'ADD_DATE="{now}">'
                    f'{bookmark_title}</A>'
                )

            elif isinstance(item, Folder):

                write_folder(
                    item,
                    indent + 1
                )

        lines.append(
            f"{pad}</DL><p>"
        )

    # Safari exports normally contain top-level
    # folders rather than putting everything under
    # another artificial "Bookmarks" folder.
    for item in root.items:

        if isinstance(item, Bookmark):

            bookmark_title = html.escape(
                item.title,
                quote=False
            )

            bookmark_url = html.escape(
                item.url,
                quote=True
            )

            lines.append(
                f'    <DT><A HREF="{bookmark_url}" '
                f'ADD_DATE="{now}">'
                f'{bookmark_title}</A>'
            )

        elif isinstance(item, Folder):

            write_folder(
                item,
                1
            )

    lines.append(
        "</DL><p>"
    )

    path.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8"
    )


# ============================================================
# Application delegate
# ============================================================

class AppDelegate(NSObject):

    def applicationDidFinishLaunching_(
        self,
        notification
    ):

        global BOOKMARK_FILE

        try:

            bookmarks = load_bookmarks(
                BOOKMARK_FILE
            )

        except Exception as e:

            self.show_error(
                "Could Not Load Bookmarks",
                str(e)
            )

            NSApplication.sharedApplication().terminate_(
                None
            )

            return

        original_count = count_bookmarks(
            bookmarks
        )

        duplicates = dedupe_folder(
            bookmarks
        )

        sort_folder(
            bookmarks
        )

        final_count = count_bookmarks(
            bookmarks
        )

        folder_count = count_folders(
            bookmarks
        )

        # Persistent link-check information.
        link_store = LinkCheckStore(
            BOOKMARK_FILE
        )

        restored = link_store.restore(
            get_all_bookmarks(
                bookmarks
            )
        )

        print()
        print(
            "Safari Bookmark Browser"
        )
        print(
            "========================"
        )
        print(
            f"Source:              {BOOKMARK_FILE}"
        )
        print(
            f"Loaded bookmarks:    {original_count}"
        )
        print(
            f"Duplicates removed:  {duplicates}"
        )
        print(
            f"Remaining bookmarks: {final_count}"
        )
        print(
            f"Folders:             {folder_count}"
        )
        print(
            f"Previous checks:     {restored}"
        )
        print(
            f"Check database:      {link_store.path}"
        )
        print()

        self.browser = (
            BookmarkBrowser
            .alloc()
            .initWithBookmarks_store_(
                bookmarks,
                link_store
            )
        )

        self.browser.build()

    def show_error(
        self,
        title,
        message
    ):

        alert = (
            NSAlert.alloc()
            .init()
        )

        alert.setMessageText_(title)
        alert.setInformativeText_(message)
        alert.setAlertStyle_(2)
        alert.addButtonWithTitle_("OK")

        alert.runModal()


# ============================================================
# Main
# ============================================================

def main():

    global BOOKMARK_FILE

    if len(sys.argv) != 2:

        print(
            "Usage:"
        )

        print(
            "    python3 bookmark_browser.py bookmarks.html"
        )

        print()

        print(
            "Example:"
        )

        print(
            "    python3 bookmark_browser.py "
            "~/Downloads/bookmarks.html"
        )

        sys.exit(1)

    BOOKMARK_FILE = (
        Path(sys.argv[1])
        .expanduser()
        .resolve()
    )

    if not BOOKMARK_FILE.exists():

        print(
            f"ERROR: File not found:\n"
            f"{BOOKMARK_FILE}",
            file=sys.stderr
        )

        sys.exit(1)

    app = (
        NSApplication
        .sharedApplication()
    )

    app.setActivationPolicy_(
        NSApplicationActivationPolicyRegular
    )

    delegate = (
        AppDelegate
        .alloc()
        .init()
    )

    app.setDelegate_(
        delegate
    )

    app.run()


if __name__ == "__main__":

    main()

