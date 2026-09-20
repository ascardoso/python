#!/usr/bin/env python3

"""
MIT License

Copyright (c) 2026 asc

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

Hierarchical threaded outliner with autosave.

An hierarchical thread/outliner app built with PySide6,
letting you create, edit, reorder, indent, and outdent nested threads.
It autosaves the hierarchy to a JSON file, preserving each thread’s title,
text, ID, and children.

The application also supports multiple outline files through:

    File -> New
    File -> Open
    File -> Save
    File -> Save As
    File -> Print Outline

Printing includes the complete outline, including all nested threads
and their associated text.
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
import math
from pathlib import Path
from typing import Any

from PySide6.QtCore import (
    Qt,
    QTimer,
    QMarginsF,
)

from PySide6.QtGui import (
    QAction,
    QKeySequence,
    QPageLayout,
    QPageSize,
    QTextDocument,
    QPainter,
    QAbstractTextDocumentLayout,
)

from PySide6.QtPrintSupport import (
    QPrinter,
    QPrintDialog,
)

from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
    QInputDialog,
)

DEFAULT_DATA_PATH = (
    Path.home() / ".thread_outliner.json"
)


def new_node(
    title: str = "New thread",
    text: str = "",
) -> dict[str, Any]:

    return {
        "id": str(uuid.uuid4()),
        "title": title,
        "text": text,
        "children": [],
    }


class ThreadOutliner(QMainWindow):

    def __init__(
        self,
        data_path: Path,
    ):

        super().__init__()

        self.data_path = data_path

        self.nodes: list[
            dict[str, Any]
        ] = []

        self._loading = False

        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(450)

        self._save_timer.timeout.connect(
            self.save_data
        )

        self.setWindowTitle(
            "Thread Outliner"
        )

        self.resize(
            1150,
            760
        )

        self._build_ui()

        self._load_data()

        if not self.nodes:

            self.nodes = [
                new_node()
            ]

        self._rebuild_tree(
            select_id=self.nodes[0]["id"]
        )

        self._make_menus()

        self._update_window_title()

        print("=" * 60)
        print("THREAD OUTLINER STARTED")
        print(f"Data file: {self.data_path}")
        print("=" * 60)

        self._debug_print_hierarchy(
            "INITIAL HIERARCHY"
        )

    # ================================================================
    # Window title
    # ================================================================

    def _update_window_title(self):

        filename = self.data_path.name

        self.setWindowTitle(
            f"Thread Outliner - {filename}"
        )

    # ================================================================
    # UI
    # ================================================================

    def _build_ui(self):

        central = QWidget()

        layout = QVBoxLayout(
            central
        )

        toolbar = QHBoxLayout()

        actions = [
            (
                "＋ Thread",
                self.add_sibling,
            ),
            (
                "＋ Subthread",
                self.add_child,
            ),
            (
                "↑",
                self.move_up,
            ),
            (
                "↓",
                self.move_down,
            ),
            (
                "Indent →",
                self.indent,
            ),
            (
                "← Outdent",
                self.outdent,
            ),
            (
                "Rename",
                self.rename_selected,
            ),
            (
                "Delete",
                self.delete_selected,
            ),
        ]

        for label, callback in actions:

            button = QPushButton(
                label
            )

            button.clicked.connect(
                callback
            )

            toolbar.addWidget(
                button
            )

        toolbar.addStretch(1)

        layout.addLayout(
            toolbar
        )

        # ------------------------------------------------------------
        # Left / tree
        # ------------------------------------------------------------

        splitter = QSplitter(
            Qt.Orientation.Horizontal
        )

        left = QWidget()

        left_layout = QVBoxLayout(
            left
        )

        left_layout.setContentsMargins(
            0,
            0,
            6,
            0
        )

        left_layout.addWidget(
            QLabel("OUTLINE")
        )

        self.tree = QTreeWidget()

        self.tree.setHeaderHidden(
            True
        )

        self.tree.setWordWrap(
            True
        )

        self.tree.setTextElideMode(
            Qt.TextElideMode.ElideNone
        )

        self.tree.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )

        self.tree.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )

        self.tree.setIndentation(
            22
        )

        self.tree.setStyleSheet("""
            QTreeWidget {
                font-size: 14px;
                padding: 4px;
            }

            QTreeWidget::item {
                padding: 7px 4px;
            }
        """)

        left_layout.addWidget(
            self.tree,
            1
        )

        # ------------------------------------------------------------
        # Right / editor
        # ------------------------------------------------------------

        right = QWidget()

        right_layout = QVBoxLayout(
            right
        )

        right_layout.setContentsMargins(
            6,
            0,
            0,
            0
        )

        right_layout.addWidget(
            QLabel("TITLE")
        )

        self.title_edit = QTextEdit()

        self.title_edit.setAcceptRichText(
            False
        )

        self.title_edit.setPlaceholderText(
            "Thread title"
        )

        self.title_edit.setFixedHeight(
            68
        )

        self.title_edit.setStyleSheet(
            "font-size: 18px; font-weight: 600;"
        )

        right_layout.addWidget(
            self.title_edit
        )

        right_layout.addWidget(
            QLabel("TEXT")
        )

        self.body_edit = QTextEdit()

        self.body_edit.setAcceptRichText(
            False
        )

        self.body_edit.setPlaceholderText(
            "Write the text for this item…"
        )

        right_layout.addWidget(
            self.body_edit,
            1
        )

        splitter.addWidget(
            left
        )

        splitter.addWidget(
            right
        )

        splitter.setStretchFactor(
            0,
            1
        )

        splitter.setStretchFactor(
            1,
            3
        )

        splitter.setSizes(
            [360, 790]
        )

        layout.addWidget(
            splitter,
            1
        )

        self.setCentralWidget(
            central
        )

        self.tree.currentItemChanged.connect(
            self._selection_changed
        )

        self.title_edit.textChanged.connect(
            self._editor_changed
        )

        self.body_edit.textChanged.connect(
            self._editor_changed
        )

    # ================================================================
    # Menus
    # ================================================================

    def _make_menus(self):

        # ------------------------------------------------------------
        # File menu
        # ------------------------------------------------------------

        file_menu = self.menuBar().addMenu(
            "&File"
        )

        # ------------------------------------------------------------
        # New
        # ------------------------------------------------------------

        new = QAction(
            "&New",
            self
        )

        new.setShortcut(
            QKeySequence.StandardKey.New
        )

        new.triggered.connect(
            self.new_outline
        )

        file_menu.addAction(
            new
        )

        # ------------------------------------------------------------
        # Open
        # ------------------------------------------------------------

        open_action = QAction(
            "&Open...",
            self
        )

        open_action.setShortcut(
            QKeySequence.StandardKey.Open
        )

        open_action.triggered.connect(
            self.open_outline
        )

        file_menu.addAction(
            open_action
        )

        # ------------------------------------------------------------
        # Save
        # ------------------------------------------------------------

        save = QAction(
            "&Save",
            self
        )

        save.setShortcut(
            QKeySequence.StandardKey.Save
        )

        save.triggered.connect(
            self.save_data
        )

        file_menu.addAction(
            save
        )

        # ------------------------------------------------------------
        # Save As
        # ------------------------------------------------------------

        save_as = QAction(
            "Save &As...",
            self
        )

        save_as.setShortcut(
            QKeySequence(
                "Ctrl+Shift+S"
            )
        )

        save_as.triggered.connect(
            self.save_as
        )

        file_menu.addAction(
            save_as
        )

        file_menu.addSeparator()

        # ------------------------------------------------------------
        # Print
        # ------------------------------------------------------------

        print_action = QAction(
            "&Print Outline...",
            self
        )

        print_action.setShortcut(
            QKeySequence.StandardKey.Print
        )

        print_action.triggered.connect(
            self.print_outline
        )

        file_menu.addAction(
            print_action
        )

        file_menu.addSeparator()

        # ------------------------------------------------------------
        # Existing new sibling action
        # ------------------------------------------------------------

        new_sibling = QAction(
            "New &sibling",
            self
        )

        new_sibling.setShortcut(
            QKeySequence(
                "Ctrl+Alt+N"
            )
        )

        new_sibling.triggered.connect(
            self.add_sibling
        )

        file_menu.addAction(
            new_sibling
        )

        # ------------------------------------------------------------
        # Outline menu
        # ------------------------------------------------------------

        edit = self.menuBar().addMenu(
            "&Outline"
        )

        entries = [
            (
                "Add subthread",
                "Ctrl+Shift+N",
                self.add_child,
            ),
            (
                "Move up",
                "Alt+Up",
                self.move_up,
            ),
            (
                "Move down",
                "Alt+Down",
                self.move_down,
            ),
            (
                "Indent",
                "Alt+Right",
                self.indent,
            ),
            (
                "Outdent",
                "Alt+Left",
                self.outdent,
            ),
            (
                "Rename",
                "F2",
                self.rename_selected,
            ),
            (
                "Delete",
                "Ctrl+Backspace",
                self.delete_selected,
            ),
        ]

        for label, shortcut, callback in entries:

            action = QAction(
                label,
                self
            )

            action.setShortcut(
                QKeySequence(
                    shortcut
                )
            )

            action.triggered.connect(
                callback
            )

            edit.addAction(
                action
            )

    # ================================================================
    # Debugging
    # ================================================================

    def _debug_print_hierarchy(
        self,
        label: str
    ):

        print()
        print("=" * 60)
        print(label)
        print("=" * 60)

        print(
            json.dumps(
                self.nodes,
                ensure_ascii=False,
                indent=2
            )
        )

        print("=" * 60)
        print()

    def _debug_print_tree(self):

        print()
        print("VISIBLE QT TREE:")

        def walk(
            item,
            depth=0
        ):

            node_id = item.data(
                0,
                Qt.ItemDataRole.UserRole
            )

            print(
                "  " * depth
                + f"- {item.text(0)} "
                + f"[{node_id}]"
            )

            for i in range(
                item.childCount()
            ):

                walk(
                    item.child(i),
                    depth + 1
                )

        for i in range(
            self.tree.topLevelItemCount()
        ):

            walk(
                self.tree.topLevelItem(i)
            )

        print()

    # ================================================================
    # Load
    # ================================================================

    def _load_data(self):

        self.nodes = []

        if not self.data_path.exists():

            print(
                f"Data file does not exist yet: "
                f"{self.data_path}"
            )

            return

        try:

            print(
                f"Loading data from: "
                f"{self.data_path}"
            )

            data = json.loads(
                self.data_path.read_text(
                    encoding="utf-8"
                )
            )

            raw_nodes = (
                data.get("threads", [])
                if isinstance(data, dict)
                else []
            )

            self.nodes = [
                self._normalize_node(node)
                for node in raw_nodes
                if isinstance(
                    node,
                    dict
                )
            ]

            print(
                f"Loaded {len(self.nodes)} "
                f"top-level thread(s)"
            )

        except (
            OSError,
            json.JSONDecodeError
        ) as exc:

            QMessageBox.warning(
                self,
                "Could not load outline",
                f"Could not read "
                f"{self.data_path}:\n"
                f"{exc}\n\n"
                "Starting a new outline."
            )

            print(
                f"LOAD ERROR: {exc}"
            )

    def _normalize_node(
        self,
        raw
    ):

        node = new_node(
            str(
                raw.get(
                    "title",
                    "Untitled"
                )
            ),
            str(
                raw.get(
                    "text",
                    ""
                )
            )
        )

        node["id"] = str(
            raw.get("id")
            or uuid.uuid4()
        )

        children = raw.get(
            "children",
            []
        )

        node["children"] = [
            self._normalize_node(child)
            for child in children
            if isinstance(
                child,
                dict
            )
        ]

        return node

    # ================================================================
    # New outline
    # ================================================================

    def new_outline(self):

        print()
        print("#" * 60)
        print("NEW OUTLINE")
        print("#" * 60)

        answer = QMessageBox.question(
            self,
            "New outline",
            "Create a new outline?\n\n"
            "The current outline will remain saved "
            "under its existing file.",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if (
            answer
            != QMessageBox.StandardButton.Yes
        ):

            return

        self._save_timer.stop()

        self.nodes = [
            new_node()
        ]

        # A new outline starts with a temporary path.
        self.data_path = (
            Path.home()
            / "Untitled.json"
        )

        self._rebuild_tree(
            select_id=self.nodes[0]["id"]
        )

        self._update_window_title()

        self.statusBar().showMessage(
            "New outline created.",
            2500
        )

        self._debug_print_hierarchy(
            "NEW OUTLINE HIERARCHY"
        )

    # ================================================================
    # Open outline
    # ================================================================

    def open_outline(self):

        print()
        print("#" * 60)
        print("OPEN OUTLINE")
        print("#" * 60)

        filename, selected_filter = (
            QFileDialog.getOpenFileName(
                self,
                "Open Outline",
                str(self.data_path.parent),
                "Outline JSON (*.json);;All Files (*)",
            )
        )

        if not filename:

            print(
                "OPEN: cancelled"
            )

            return

        path = Path(
            filename
        ).expanduser().resolve()

        print(
            f"OPEN: selected file: {path}"
        )

        # Stop any pending autosave for the old outline.
        self._save_timer.stop()

        self.data_path = path

        self._load_data()

        if not self.nodes:

            self.nodes = [
                new_node()
            ]

        self._rebuild_tree(
            select_id=self.nodes[0]["id"]
        )

        self._update_window_title()

        print(
            f"OPEN: successfully loaded: "
            f"{self.data_path}"
        )

        self._debug_print_hierarchy(
            "OPENED OUTLINE"
        )

        self.statusBar().showMessage(
            f"Opened {self.data_path}",
            2500
        )

    # ================================================================
    # Save As
    # ================================================================

    def save_as(self):

        print()
        print("#" * 60)
        print("SAVE AS")
        print("#" * 60)

        self._commit_editor()

        filename, selected_filter = (
            QFileDialog.getSaveFileName(
                self,
                "Save Outline As",
                str(self.data_path),
                "Outline JSON (*.json);;All Files (*)",
            )
        )

        if not filename:

            print(
                "SAVE AS: cancelled"
            )

            return False

        path = Path(
            filename
        ).expanduser().resolve()

        # ------------------------------------------------------------
        # Add .json if the user did not provide an extension.
        # ------------------------------------------------------------

        if not path.suffix:

            path = path.with_suffix(
                ".json"
            )

        print(
            f"SAVE AS: destination: {path}"
        )

        old_path = self.data_path

        self.data_path = path

        success = self._write_data()

        if success:

            self._update_window_title()

            self.statusBar().showMessage(
                f"Saved as {self.data_path}",
                3000
            )

            print(
                "SAVE AS: successful"
            )

            return True

        # ------------------------------------------------------------
        # Restore old path if Save As failed.
        # ------------------------------------------------------------

        self.data_path = old_path

        self._update_window_title()

        print(
            "SAVE AS: failed; "
            "restored previous data path"
        )

        return False

    # ================================================================
    # Find node
    # ================================================================

    def _find(
        self,
        node_id,
        nodes=None
    ):
        """
        Find a node.

        Returns:

            (node, containing_list, index)
        """

        nodes = (
            self.nodes
            if nodes is None
            else nodes
        )

        for index, node in enumerate(
            nodes
        ):

            if node["id"] == node_id:

                return (
                    node,
                    nodes,
                    index
                )

            result = self._find(
                node_id,
                node["children"]
            )

            if result:

                return result

        return None

    def _selected_node(self):

        item = self.tree.currentItem()

        if not item:

            print(
                "DEBUG: _selected_node(): "
                "no current item"
            )

            return None

        node_id = item.data(
            0,
            Qt.ItemDataRole.UserRole
        )

        print(
            "DEBUG: _selected_node(): "
            f"'{item.text(0)}' "
            f"id={node_id}"
        )

        result = self._find(
            node_id
        )

        if result:

            node, siblings, index = result

            print(
                "DEBUG: _selected_node(): "
                f"found '{node['title']}' "
                f"at index {index} "
                f"in list of {len(siblings)} items"
            )

        else:

            print(
                "DEBUG: _selected_node(): "
                "NODE NOT FOUND"
            )

        return result

    # ================================================================
    # Find parent -- CORRECTED
    # ================================================================

    def _find_parent(
        self,
        node_id,
        nodes=None
    ):
        """
        Find the direct parent of node_id.

        IMPORTANT:

        Returns:

            (
                parent,
                parent's containing list,
                parent's index
            )

        Example:

            A
              B
                C

        For C this returns:

            (
                B,
                A.children,
                0
            )

        NOT:

            (
                B,
                B.children,
                0
            )

        That distinction is what makes Outdent work.
        """

        nodes = (
            self.nodes
            if nodes is None
            else nodes
        )

        for parent_index, node in enumerate(
            nodes
        ):

            # First check whether the requested node is
            # a direct child of this node.

            for child in node["children"]:

                if child["id"] == node_id:

                    print(
                        "DEBUG: _find_parent(): "
                        f"'{child['title']}' is a direct "
                        f"child of '{node['title']}'"
                    )

                    print(
                        "DEBUG: _find_parent(): "
                        f"parent is at index {parent_index} "
                        f"in its containing list"
                    )

                    return (
                        node,
                        nodes,
                        parent_index
                    )

            # Otherwise search deeper.

            result = self._find_parent(
                node_id,
                node["children"]
            )

            if result:

                return result

        return None

    # ================================================================
    # Rebuild tree
    # ================================================================

    def _rebuild_tree(
        self,
        select_id=None
    ):

        print(
            f"DEBUG: rebuilding tree; "
            f"select_id={select_id}"
        )

        self._loading = True

        self.tree.setUpdatesEnabled(
            False
        )

        try:

            self.tree.clear()

            def add_nodes(
                nodes,
                parent_item=None
            ):

                for node in nodes:

                    title = (
                        node.get(
                            "title",
                            ""
                        ).strip()
                        or "Untitled"
                    )

                    item = QTreeWidgetItem(
                        [title]
                    )

                    item.setData(
                        0,
                        Qt.ItemDataRole.UserRole,
                        node["id"]
                    )

                    item.setToolTip(
                        0,
                        node.get(
                            "title",
                            ""
                        )
                        or "Untitled"
                    )

                    if parent_item is None:

                        self.tree.addTopLevelItem(
                            item
                        )

                    else:

                        parent_item.addChild(
                            item
                        )

                    add_nodes(
                        node["children"],
                        item
                    )

                    item.setExpanded(
                        True
                    )

            add_nodes(
                self.nodes
            )

            target = (
                self._item_for_id(
                    select_id
                )
                if select_id
                else None
            )

            if target:

                self.tree.setCurrentItem(
                    target
                )

                print(
                    "DEBUG: selected rebuilt "
                    f"tree item '{target.text(0)}'"
                )

            elif self.tree.topLevelItemCount():

                self.tree.setCurrentItem(
                    self.tree.topLevelItem(0)
                )

        finally:

            self.tree.setUpdatesEnabled(
                True
            )

        self.tree.doItemsLayout()

        self.tree.viewport().update()

        self.tree.viewport().repaint()

        self._loading = False

        self._load_editor_from_selection()

        self._debug_print_tree()

    def _item_for_id(
        self,
        node_id
    ):

        if not node_id:

            return None

        stack = [
            self.tree.topLevelItem(i)
            for i in range(
                self.tree.topLevelItemCount()
            )
        ]

        while stack:

            item = stack.pop()

            if (
                item.data(
                    0,
                    Qt.ItemDataRole.UserRole
                )
                == node_id
            ):

                return item

            for i in range(
                item.childCount()
            ):

                stack.append(
                    item.child(i)
                )

        return None

    # ================================================================
    # Editor
    # ================================================================

    def _selection_changed(
        self,
        current,
        previous
    ):

        if not self._loading:

            self._load_editor_from_selection()

    def _load_editor_from_selection(
        self
    ):

        found = self._selected_node()

        self._loading = True

        enabled = found is not None

        self.title_edit.setEnabled(
            enabled
        )

        self.body_edit.setEnabled(
            enabled
        )

        if enabled:

            node = found[0]

            self.title_edit.setPlainText(
                node.get(
                    "title",
                    ""
                )
            )

            self.body_edit.setPlainText(
                node.get(
                    "text",
                    ""
                )
            )

        else:

            self.title_edit.clear()

            self.body_edit.clear()

        self._loading = False

    def _editor_changed(self):

        if self._loading:

            return

        found = self._selected_node()

        if not found:

            return

        node = found[0]

        node["title"] = (
            self.title_edit.toPlainText()
        )

        node["text"] = (
            self.body_edit.toPlainText()
        )

        item = self.tree.currentItem()

        if item:

            title = (
                node["title"].strip()
                or "Untitled"
            )

            item.setText(
                0,
                title
            )

            item.setToolTip(
                0,
                title
            )

        self._schedule_save()

    def _commit_editor(self):

        found = self._selected_node()

        if found and not self._loading:

            node = found[0]

            node["title"] = (
                self.title_edit.toPlainText()
            )

            node["text"] = (
                self.body_edit.toPlainText()
            )

    # ================================================================
    # Add sibling
    # ================================================================

    def add_sibling(self):

        self._commit_editor()

        found = self._selected_node()

        if found:

            _, siblings, index = found

            node = new_node()

            siblings.insert(
                index + 1,
                node
            )

        else:

            node = new_node()

            self.nodes.append(
                node
            )

        self._rebuild_tree(
            select_id=node["id"]
        )

        self.title_edit.setFocus()

        self.title_edit.selectAll()

        self._schedule_save()

    # ================================================================
    # Add child
    # ================================================================

    def add_child(self):

        self._commit_editor()

        found = self._selected_node()

        if not found:

            self.add_sibling()

            return

        parent = found[0]

        node = new_node()

        parent["children"].append(
            node
        )

        self._rebuild_tree(
            select_id=node["id"]
        )

        self.title_edit.setFocus()

        self.title_edit.selectAll()

        self._schedule_save()

    # ================================================================
    # Move up/down
    # ================================================================

    def move_up(self):

        self._move_sibling(
            -1
        )

    def move_down(self):

        self._move_sibling(
            1
        )

    def _move_sibling(
        self,
        delta
    ):

        found = self._selected_node()

        if not found:

            return

        node, siblings, index = found

        new_index = index + delta

        if not (
            0 <= new_index < len(siblings)
        ):

            return

        self._commit_editor()

        siblings[index], siblings[new_index] = (
            siblings[new_index],
            siblings[index]
        )

        self._rebuild_tree(
            select_id=node["id"]
        )

        self._schedule_save()

    # ================================================================
    # Indent
    # ================================================================

    def indent(self):
        """
        Make the selected item a child of its
        immediately preceding sibling.

        Before:

            A
            B
            C

        After indenting C:

            A
            B
              C
        """

        print()
        print("#" * 60)
        print("INDENT BUTTON PRESSED")
        print("#" * 60)

        found = self._selected_node()

        if not found:

            return

        node, siblings, index = found

        if index == 0:

            print(
                "INDENT: cannot indent; "
                "item is first sibling"
            )

            return

        self._commit_editor()

        parent = siblings[
            index - 1
        ]

        print(
            f"INDENT: moving '{node['title']}' "
            f"under '{parent['title']}'"
        )

        moved_node = siblings.pop(
            index
        )

        parent["children"].append(
            moved_node
        )

        self._debug_print_hierarchy(
            "HIERARCHY AFTER INDENT"
        )

        self._rebuild_tree(
            select_id=moved_node["id"]
        )

        self._schedule_save()

    # ================================================================
    # Outdent -- CORRECTED
    # ================================================================

    def outdent(self):
        """
        Move the selected item one level toward the root.

        Before:

            A
              B
                C

        After outdenting C:

            A
              B
            C

        The selected item becomes a sibling of its parent.
        """

        print()
        print("#" * 60)
        print("OUTDENT BUTTON PRESSED")
        print("#" * 60)

        self._debug_print_hierarchy(
            "OUTDENT BEFORE"
        )

        # ------------------------------------------------------------
        # Find selected item.
        # ------------------------------------------------------------

        found = self._selected_node()

        if not found:

            print(
                "OUTDENT: no selected node"
            )

            return

        node, current_siblings, current_index = found

        print(
            "OUTDENT: selected node:"
        )

        print(
            f"  title = {node['title']!r}"
        )

        print(
            f"  id = {node['id']}"
        )

        print(
            f"  current index = {current_index}"
        )

        # ------------------------------------------------------------
        # Find the parent.
        #
        # For A -> B -> C:
        #
        # parent = B
        # parent_siblings = A.children
        # parent_index = 0
        # ------------------------------------------------------------

        parent_info = self._find_parent(
            node["id"]
        )

        if not parent_info:

            print(
                "OUTDENT: item is already "
                "at the top level"
            )

            self.statusBar().showMessage(
                "Cannot outdent: already at top level.",
                2500
            )

            return

        parent, parent_siblings, parent_index = (
            parent_info
        )

        print(
            "OUTDENT: parent information:"
        )

        print(
            f"  parent title = {parent['title']!r}"
        )

        print(
            f"  parent id = {parent['id']}"
        )

        print(
            f"  parent index = {parent_index}"
        )

        print(
            f"  parent sibling list contains "
            f"{len(parent_siblings)} item(s)"
        )

        # ------------------------------------------------------------
        # IMPORTANT SAFETY CHECK
        #
        # The destination list must NOT be the current
        # children list.
        # ------------------------------------------------------------

        if parent_siblings is current_siblings:

            print(
                "OUTDENT ERROR: destination list and "
                "current list are the same!"
            )

            self.statusBar().showMessage(
                "Outdent aborted: invalid parent structure.",
                3000
            )

            return

        self._commit_editor()

        # ------------------------------------------------------------
        # Remove node from its current parent's children.
        # ------------------------------------------------------------

        print(
            f"OUTDENT: removing '{node['title']}' "
            f"from '{parent['title']}.children'"
        )

        removed = current_siblings.pop(
            current_index
        )

        # ------------------------------------------------------------
        # Insert immediately after the parent.
        #
        # This is the actual Outdent operation.
        # ------------------------------------------------------------

        destination_index = (
            parent_index + 1
        )

        print(
            f"OUTDENT: inserting '{removed['title']}' "
            f"into parent sibling list at "
            f"index {destination_index}"
        )

        parent_siblings.insert(
            destination_index,
            removed
        )

        # ------------------------------------------------------------
        # Verify the resulting structure.
        # ------------------------------------------------------------

        self._debug_print_hierarchy(
            "OUTDENT AFTER"
        )

        print(
            "OUTDENT: rebuilding Qt tree..."
        )

        self._rebuild_tree(
            select_id=removed["id"]
        )

        print(
            "OUTDENT: saving immediately..."
        )

        self.save_data()

        print(
            "OUTDENT: complete"
        )

        self.statusBar().showMessage(
            "Item outdented.",
            1500
        )

    # ================================================================
    # Rename
    # ================================================================

    def rename_selected(self):

        found = self._selected_node()

        if not found:

            return

        node = found[0]

        title, accepted = (
            QInputDialog.getText(
                self,
                "Rename thread",
                "Title:",
                text=node.get(
                    "title",
                    ""
                )
            )
        )

        if accepted:

            node["title"] = (
                title.strip()
                or "Untitled"
            )

            self._rebuild_tree(
                select_id=node["id"]
            )

            self._schedule_save()

    # ================================================================
    # Delete
    # ================================================================

    def delete_selected(self):

        found = self._selected_node()

        if not found:

            return

        node, siblings, index = found

        title = (
            node.get(
                "title",
                ""
            ).strip()
            or "Untitled"
        )

        answer = QMessageBox.question(
            self,
            "Delete thread",
            f"Delete “{title}” and all its subthreads?",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if (
            answer
            != QMessageBox.StandardButton.Yes
        ):

            return

        self._commit_editor()

        siblings.pop(
            index
        )

        if not self.nodes:

            self.nodes.append(
                new_node()
            )

        if siblings:

            select_id = siblings[
                min(
                    index,
                    len(siblings) - 1
                )
            ]["id"]

        else:

            select_id = (
                self.nodes[0]["id"]
                if self.nodes
                else None
            )

        self._rebuild_tree(
            select_id=select_id
        )

        self._schedule_save()

    # ================================================================
    # Saving
    # ================================================================

    def _schedule_save(self):

        print(
            "DEBUG: autosave scheduled"
        )

        self._save_timer.start()

    def _write_data(self):

        print()
        print("#" * 60)
        print("WRITE_DATA CALLED")
        print("#" * 60)

        self._commit_editor()

        self._debug_print_hierarchy(
            "HIERARCHY BEING SAVED"
        )

        try:

            self.data_path.parent.mkdir(
                parents=True,
                exist_ok=True
            )

            temp = self.data_path.with_suffix(
                self.data_path.suffix
                + ".tmp"
            )

            serialized = json.dumps(
                {
                    "threads": self.nodes
                },
                ensure_ascii=False,
                indent=2
            )

            print(
                "SAVE: writing temporary file:"
            )

            print(
                temp
            )

            temp.write_text(
                serialized,
                encoding="utf-8"
            )

            temp.replace(
                self.data_path
            )

            print(
                "SAVE: successfully replaced:"
            )

            print(
                self.data_path
            )

            self.statusBar().showMessage(
                f"Saved to {self.data_path}",
                2500
            )

            return True

        except OSError as exc:

            print(
                f"SAVE ERROR: {exc}"
            )

            QMessageBox.warning(
                self,
                "Save failed",
                f"Could not save outline:\n{exc}"
            )

            return False

    def save_data(self):

        print()
        print("#" * 60)
        print("SAVE_DATA CALLED")
        print("#" * 60)

        self._write_data()

    # ================================================================
    # Printing
    # ================================================================

    def _escape_print_html(
        self,
        text: str
    ) -> str:
        """
        Convert plain text to HTML-safe text for printing.
        """

        from html import escape

        return escape(
            text,
            quote=False
        ).replace(
            "\n",
            "<br>"
        )

    def _build_print_html(self):

        print()
        print("#" * 60)
        print("BUILDING PRINT DOCUMENT")
        print("#" * 60)

        self._commit_editor()

        lines = []

        lines.append(
            "<html>"
        )

        lines.append(
            "<head>"
        )

        lines.append(
            """
            <style>
                body {
                    font-family: Arial, Helvetica, sans-serif;
                    font-size: 11pt;
                    color: #000000;
                }

                h1 {
                    font-size: 22pt;
                    margin-bottom: 4px;
                }

                h2 {
                    font-size: 16pt;
                    margin-top: 18px;
                    margin-bottom: 6px;
                    border-bottom: 1px solid #888888;
                }

                h3 {
                    font-size: 13pt;
                    margin-top: 14px;
                    margin-bottom: 5px;
                }

                .path {
                    color: #555555;
                    font-size: 9pt;
                    margin-bottom: 20px;
                }

                .thread {
                    margin-left: 0px;
                    margin-bottom: 14px;
                }

                .subthread {
                    margin-left: 25px;
                }

                .title {
                    font-weight: bold;
                    font-size: 13pt;
                }

                .text {
                    margin-top: 5px;
                    line-height: 1.35;
                }

                .separator {
                    border-bottom: 1px solid #cccccc;
                    margin-top: 10px;
                    margin-bottom: 10px;
                }
            </style>
            """
        )

        lines.append(
            "</head>"
        )

        lines.append(
            "<body>"
        )

        lines.append(
            "<h1>Thread Outliner</h1>"
        )

        lines.append(
            "<div class='path'>"
            + self._escape_print_html(
                str(self.data_path)
            )
            + "</div>"
        )

        def add_nodes(
            nodes,
            depth=0
        ):

            for node in nodes:

                title = (
                    str(
                        node.get(
                            "title",
                            ""
                        )
                    ).strip()
                    or "Untitled"
                )

                text = str(
                    node.get(
                        "text",
                        ""
                    )
                )

                css_class = (
                    "thread"
                    if depth == 0
                    else "subthread"
                )

                lines.append(
                    f"<div class='{css_class}'>"
                )

                if depth == 0:

                    lines.append(
                        "<h2>"
                        + self._escape_print_html(
                            title
                        )
                        + "</h2>"
                    )

                else:

                    heading_level = min(
                        depth + 2,
                        6
                    )

                    lines.append(
                        f"<h{heading_level}>"
                        + self._escape_print_html(
                            title
                        )
                        + f"</h{heading_level}>"
                    )

                if text:

                    lines.append(
                        "<div class='text'>"
                        + self._escape_print_html(
                            text
                        )
                        + "</div>"
                    )

                lines.append(
                    "</div>"
                )

                add_nodes(
                    node.get(
                        "children",
                        []
                    ),
                    depth + 1
                )

        add_nodes(
            self.nodes
        )

        lines.append(
            "</body>"
        )

        lines.append(
            "</html>"
        )

        html = "\n".join(
            lines
        )

        print(
            f"PRINT: generated HTML "
            f"with {len(html)} characters"
        )

        return html

    def print_outline(self):

        print()
        print("#" * 60)
        print("PRINT OUTLINE")
        print("#" * 60)

        self._commit_editor()

        self._debug_print_hierarchy(
            "HIERARCHY BEING PRINTED"
        )

        # ------------------------------------------------------------
        # Build printer.
        # ------------------------------------------------------------

        printer = QPrinter(
            QPrinter.PrinterMode.HighResolution
        )

        # ------------------------------------------------------------
        # Configure page layout.
        # ------------------------------------------------------------

        page_layout = QPageLayout(
            QPageSize(
                QPageSize.PageSizeId.Letter
            ),
            QPageLayout.Orientation.Portrait,
            QMarginsF(
                15,
                15,
                15,
                15
            ),
            QPageLayout.Unit.Millimeter,
        )

        printer.setPageLayout(
            page_layout
        )

        # ------------------------------------------------------------
        # Show native print dialog.
        # ------------------------------------------------------------

        dialog = QPrintDialog(
            printer,
            self
        )

        dialog.setWindowTitle(
            "Print Outline"
        )

        result = dialog.exec()

        if result != QPrintDialog.DialogCode.Accepted:

            print(
                "PRINT: cancelled"
            )

            self.statusBar().showMessage(
                "Printing cancelled.",
                2000
            )

            return

        print(
            "PRINT: print dialog accepted"
        )

        # ------------------------------------------------------------
        # Create QTextDocument containing the entire outline.
        # ------------------------------------------------------------

        document = QTextDocument()

        document.setDocumentMargin(
            0
        )

        html = self._build_print_html()

        document.setHtml(
            html
        )

        # ------------------------------------------------------------
        # Print the complete document.
        #
        # PySide6 does not provide QTextDocument.print()
        # in this environment, so render the document manually
        # using QPainter and the document layout.
        # ------------------------------------------------------------

        print(
            "PRINT: rendering document to printer..."
        )

        painter = QPainter()

        try:

            if not painter.begin(printer):

                raise RuntimeError(
                    "Could not start printer painter."
                )

            # --------------------------------------------------------
            # Get the printable page rectangle in device pixels.
            # --------------------------------------------------------

            page_rect = printer.pageLayout().paintRectPixels(
                printer.resolution()
            )

            print(
                "PRINT: page rectangle:"
            )

            print(
                f"  x = {page_rect.x()}"
            )

            print(
                f"  y = {page_rect.y()}"
            )

            print(
                f"  width = {page_rect.width()}"
            )

            print(
                f"  height = {page_rect.height()}"
            )

            # --------------------------------------------------------
            # Scale the QTextDocument to the printer resolution.
            #
            # QTextDocument uses points (1/72 inch), while the
            # printer uses device pixels.
            # --------------------------------------------------------

            scale = (
                printer.resolution()
                / 72.0
            )

            painter.scale(
                scale,
                scale
            )

            # --------------------------------------------------------
            # Determine the document width in document coordinates.
            # --------------------------------------------------------

            document_width = (
                page_rect.width()
                / scale
            )

            document.setTextWidth(
                document_width
            )

            # --------------------------------------------------------
            # Determine the page height in document coordinates.
            # --------------------------------------------------------

            page_height = (
                page_rect.height()
                / scale
            )

            # --------------------------------------------------------
            # Render each page.
            # --------------------------------------------------------

            document_height = (
                document.documentLayout()
                .documentSize()
                .height()
            )

            page_count = max(
                1,
                math.ceil(
                    document_height / page_height
                )
            )

            print(
                f"PRINT: document height = "
                f"{document_height:.2f}"
            )

            print(
                f"PRINT: page height = "
                f"{page_height:.2f}"
            )

            print(
                f"PRINT: estimated page count = "
                f"{page_count}"
            )

            for page in range(
                page_count
            ):

                if page > 0:

                    printer.newPage()

                # ----------------------------------------------------
                # Translate to the printable area.
                # ----------------------------------------------------

                painter.save()

                painter.translate(
                    page_rect.x() / scale,
                    page_rect.y() / scale
                )

                # ----------------------------------------------------
                # Clip to the current page.
                # ----------------------------------------------------

                painter.setClipRect(
                    0,
                    0,
                    document_width,
                    page_height
                )

                # ----------------------------------------------------
                # Move the document upward for subsequent pages.
                # ----------------------------------------------------

                painter.translate(
                    0,
                    -page * page_height
                )

                # ----------------------------------------------------
                # Paint the QTextDocument.
                # ----------------------------------------------------

                context = QAbstractTextDocumentLayout.PaintContext()

                context.clip = painter.clipBoundingRect()

                document.documentLayout().draw(
                    painter,
                    context
                )

                painter.restore()

                print(
                    f"PRINT: rendered page "
                    f"{page + 1} of {page_count}"
                )

            painter.end()

            print(
                "PRINT: document successfully "
                "sent to printer"
            )

            self.statusBar().showMessage(
                f"Outline printed ({page_count} page(s)).",
                2500
            )

        except Exception as exc:

            if painter.isActive():

                painter.end()

            print(
                f"PRINT ERROR: {exc}"
            )

            QMessageBox.warning(
                self,
                "Print failed",
                f"Could not print outline:\n{exc}"
            )


    # ================================================================
    # Close
    # ================================================================

    def closeEvent(
        self,
        event
    ):

        print(
            "DEBUG: closing application"
        )

        self._save_timer.stop()

        self.save_data()

        event.accept()


# ====================================================================
# Main
# ====================================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Open a hierarchical thread outliner."
        )
    )

    parser.add_argument(
        "data_file",
        nargs="?",
        help="Optional JSON data file."
    )

    args, qt_args = parser.parse_known_args(
        sys.argv[1:]
    )

    data_path = (
        Path(
            args.data_file
        )
        .expanduser()
        .resolve()
        if args.data_file
        else DEFAULT_DATA_PATH
    )

    app = QApplication(
        [
            sys.argv[0],
            *qt_args
        ]
    )

    window = ThreadOutliner(
        data_path
    )

    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

