#!/usr/bin/env python3

# It's a lightweight Windows/macOS/Linux-style file browser written in Python that lets 
# you select a folder, browse its files recursively, sort them, and preview supported text, 
# RTF, and image files without editing them.

# One technical issue I'd flag: the program recursively scans the entire selected directory 
# immediately. For a directory containing a very large number of files or deeply nested 
# folders, populate_directory() could make the UI slow or temporarily unresponsive. 

# It also doesn't protect against symlink-related recursion, 
# depending on how entry.is_dir() behaves for links on the platform.

import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QFont, QKeySequence, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QMainWindow,
    QScrollArea,
    QSplitter,
    QTextEdit,
    QToolBar,
    QTreeWidget,
    QTreeWidgetItem,
    QWidget,
    QVBoxLayout,
)


# =========================================================
# File types
# =========================================================

TEXT_EXTENSIONS = {
    ".txt",
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".html",
    ".htm",
    ".css",
    ".json",
    ".xml",
    ".yaml",
    ".yml",
    ".md",
    ".csv",
    ".ini",
    ".cfg",
    ".conf",
    ".log",
    ".sql",
    ".sh",
    ".bat",
    ".ps1",
    ".java",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
    ".rs",
    ".go",
    ".php",
    ".rb",
    ".swift",
    ".kt",
}


IMAGE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".bmp",
    ".webp",
    ".svg",
}


# =========================================================
# File size limits
# =========================================================

MAX_TEXT_FILE_SIZE = 10 * 1024 * 1024       # 10 MB
MAX_RTF_FILE_SIZE = 20 * 1024 * 1024        # 20 MB
MAX_IMAGE_FILE_SIZE = 50 * 1024 * 1024      # 50 MB


# =========================================================
# Font settings
# =========================================================

DEFAULT_FONT_SIZE = 11
MIN_FONT_SIZE = 6
MAX_FONT_SIZE = 40
FONT_SIZE_STEP = 1


class FileViewer(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("File Viewer")
        self.resize(1200, 750)
        self.setMinimumSize(800, 500)

        self.current_directory = None
        self.current_pixmap = None

        # -------------------------------------------------
        # Sorting defaults
        # -------------------------------------------------

        self.sort_column = "name"
        self.sort_order = Qt.AscendingOrder

        # -------------------------------------------------
        # Font defaults
        # -------------------------------------------------

        self.font_size = DEFAULT_FONT_SIZE

        self.create_ui()

    # =====================================================
    # Create UI
    # =====================================================

    def create_ui(self):

        # -------------------------------------------------
        # Menus
        # -------------------------------------------------

        self.create_menus()

        # -------------------------------------------------
        # Toolbar
        # -------------------------------------------------

        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)

        self.addToolBar(toolbar)

        open_action = toolbar.addAction(
            "Open Directory"
        )

        open_action.triggered.connect(
            self.open_directory
        )

        toolbar.addSeparator()

        self.path_label = QLabel(
            "No directory selected"
        )

        self.path_label.setStyleSheet(
            "padding-left: 8px; color: #666;"
        )

        toolbar.addWidget(
            self.path_label
        )

        # -------------------------------------------------
        # Left navigator
        # -------------------------------------------------

        self.tree = QTreeWidget()

        self.tree.setHeaderLabel(
            "Files"
        )

        self.tree.setAnimated(True)
        self.tree.setUniformRowHeights(True)

        # currentItemChanged fires for both:
        #
        #   Mouse selection
        #   Up/Down keyboard navigation
        #
        self.tree.currentItemChanged.connect(
            self.file_selection_changed
        )

        # -------------------------------------------------
        # Text viewer
        # -------------------------------------------------

        self.viewer = QTextEdit()

        self.viewer.setReadOnly(True)
        self.viewer.setAcceptRichText(True)

        # Default source-code/text font.
        self.apply_font()

        # -------------------------------------------------
        # Image viewer
        # -------------------------------------------------

        self.image_label = QLabel()

        self.image_label.setAlignment(
            Qt.AlignCenter
        )

        self.image_label.setStyleSheet(
            "background-color: #222;"
        )

        self.image_label.setText(
            "No image selected"
        )

        self.image_scroll = QScrollArea()

        self.image_scroll.setWidget(
            self.image_label
        )

        self.image_scroll.setWidgetResizable(
            True
        )

        self.image_scroll.setAlignment(
            Qt.AlignCenter
        )

        # -------------------------------------------------
        # Viewer container
        # -------------------------------------------------

        self.viewer_container = QWidget()

        viewer_layout = QVBoxLayout(
            self.viewer_container
        )

        viewer_layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        viewer_layout.addWidget(
            self.viewer
        )

        viewer_layout.addWidget(
            self.image_scroll
        )

        self.image_scroll.hide()

        # -------------------------------------------------
        # Splitter
        # -------------------------------------------------

        splitter = QSplitter(
            Qt.Horizontal
        )

        splitter.addWidget(
            self.tree
        )

        splitter.addWidget(
            self.viewer_container
        )

        splitter.setSizes(
            [350, 850]
        )

        self.setCentralWidget(
            splitter
        )

    # =====================================================
    # Menus
    # =====================================================

    def create_menus(self):

        # -------------------------------------------------
        # File menu
        # -------------------------------------------------

        file_menu = self.menuBar().addMenu(
            "File"
        )

        open_action = QAction(
            "Open Directory...",
            self
        )

        open_action.triggered.connect(
            self.open_directory
        )

        file_menu.addAction(
            open_action
        )

        file_menu.addSeparator()

        exit_action = QAction(
            "Exit",
            self
        )

        exit_action.triggered.connect(
            self.close
        )

        file_menu.addAction(
            exit_action
        )

        # -------------------------------------------------
        # Sort menu
        # -------------------------------------------------

        sort_menu = self.menuBar().addMenu(
            "Sort"
        )

        # -------------------------------------------------
        # Sort By submenu
        # -------------------------------------------------

        sort_by_menu = sort_menu.addMenu(
            "Sort By"
        )

        self.sort_name_action = QAction(
            "Name",
            self
        )

        self.sort_name_action.setCheckable(
            True
        )

        self.sort_name_action.setChecked(
            True
        )

        self.sort_name_action.triggered.connect(
            lambda: self.set_sort_column(
                "name"
            )
        )

        sort_by_menu.addAction(
            self.sort_name_action
        )

        self.sort_date_action = QAction(
            "Date Modified",
            self
        )

        self.sort_date_action.setCheckable(
            True
        )

        self.sort_date_action.setChecked(
            False
        )

        self.sort_date_action.triggered.connect(
            lambda: self.set_sort_column(
                "modified"
            )
        )

        sort_by_menu.addAction(
            self.sort_date_action
        )

        # -------------------------------------------------
        # Sort order submenu
        # -------------------------------------------------

        order_menu = sort_menu.addMenu(
            "Order"
        )

        self.sort_ascending_action = QAction(
            "Ascending",
            self
        )

        self.sort_ascending_action.setCheckable(
            True
        )

        self.sort_ascending_action.setChecked(
            True
        )

        self.sort_ascending_action.triggered.connect(
            lambda: self.set_sort_order(
                Qt.AscendingOrder
            )
        )

        order_menu.addAction(
            self.sort_ascending_action
        )

        self.sort_descending_action = QAction(
            "Descending",
            self
        )

        self.sort_descending_action.setCheckable(
            True
        )

        self.sort_descending_action.setChecked(
            False
        )

        self.sort_descending_action.triggered.connect(
            lambda: self.set_sort_order(
                Qt.DescendingOrder
            )
        )

        order_menu.addAction(
            self.sort_descending_action
        )

        # -------------------------------------------------
        # Quick sorting options
        # -------------------------------------------------

        sort_menu.addSeparator()

        name_az_action = QAction(
            "Name — A to Z",
            self
        )

        name_az_action.triggered.connect(
            lambda: self.set_sorting(
                "name",
                Qt.AscendingOrder
            )
        )

        sort_menu.addAction(
            name_az_action
        )

        name_za_action = QAction(
            "Name — Z to A",
            self
        )

        name_za_action.triggered.connect(
            lambda: self.set_sorting(
                "name",
                Qt.DescendingOrder
            )
        )

        sort_menu.addAction(
            name_za_action
        )

        newest_action = QAction(
            "Date Modified — Newest First",
            self
        )

        newest_action.triggered.connect(
            lambda: self.set_sorting(
                "modified",
                Qt.DescendingOrder
            )
        )

        sort_menu.addAction(
            newest_action
        )

        oldest_action = QAction(
            "Date Modified — Oldest First",
            self
        )

        oldest_action.triggered.connect(
            lambda: self.set_sorting(
                "modified",
                Qt.AscendingOrder
            )
        )

        sort_menu.addAction(
            oldest_action
        )

        # -------------------------------------------------
        # View menu
        # -------------------------------------------------

        view_menu = self.menuBar().addMenu(
            "View"
        )

        font_menu = view_menu.addMenu(
            "Font Size"
        )

        # Increase font
        increase_font_action = QAction(
            "Increase Font Size",
            self
        )

        increase_font_action.setShortcut(
            QKeySequence("Ctrl++")
        )

        increase_font_action.triggered.connect(
            self.increase_font_size
        )

        font_menu.addAction(
            increase_font_action
        )

        # Decrease font
        decrease_font_action = QAction(
            "Decrease Font Size",
            self
        )

        decrease_font_action.setShortcut(
            QKeySequence("Ctrl+-")
        )

        decrease_font_action.triggered.connect(
            self.decrease_font_size
        )

        font_menu.addAction(
            decrease_font_action
        )

        # Reset font
        reset_font_action = QAction(
            "Reset Font Size",
            self
        )

        reset_font_action.setShortcut(
            QKeySequence("Ctrl+0")
        )

        reset_font_action.triggered.connect(
            self.reset_font_size
        )

        font_menu.addAction(
            reset_font_action
        )

        font_menu.addSeparator()

        self.font_size_action = QAction(
            self.font_size_text(),
            self
        )

        self.font_size_action.setEnabled(
            False
        )

        font_menu.addAction(
            self.font_size_action
        )

    # =====================================================
    # Font controls
    # =====================================================

    def apply_font(self):

        font = QFont(
            "Consolas",
            self.font_size
        )

        if not font.exactMatch():

            font = QFont(
                "Courier New",
                self.font_size
            )

        self.viewer.setFont(
            font
        )

        self.update_font_menu()

    # -----------------------------------------------------

    def font_size_text(self):

        return f"Current Size: {self.font_size} pt"

    # -----------------------------------------------------

    def update_font_menu(self):

        if hasattr(
            self,
            "font_size_action"
        ):

            self.font_size_action.setText(
                self.font_size_text()
            )

    # -----------------------------------------------------

    def increase_font_size(self):

        if self.font_size >= MAX_FONT_SIZE:
            return

        self.font_size += FONT_SIZE_STEP

        self.apply_font()

    # -----------------------------------------------------

    def decrease_font_size(self):

        if self.font_size <= MIN_FONT_SIZE:
            return

        self.font_size -= FONT_SIZE_STEP

        self.apply_font()

    # -----------------------------------------------------

    def reset_font_size(self):

        self.font_size = DEFAULT_FONT_SIZE

        self.apply_font()

    # =====================================================
    # Sorting controls
    # =====================================================

    def set_sort_column(
        self,
        column
    ):

        self.sort_column = column

        self.update_sort_menu()

        self.reload_directory()

    # -----------------------------------------------------

    def set_sort_order(
        self,
        order
    ):

        self.sort_order = order

        self.update_sort_menu()

        self.reload_directory()

    # -----------------------------------------------------

    def set_sorting(
        self,
        column,
        order
    ):

        self.sort_column = column
        self.sort_order = order

        self.update_sort_menu()

        self.reload_directory()

    # -----------------------------------------------------

    def update_sort_menu(self):

        self.sort_name_action.setChecked(
            self.sort_column == "name"
        )

        self.sort_date_action.setChecked(
            self.sort_column == "modified"
        )

        self.sort_ascending_action.setChecked(
            self.sort_order
            == Qt.AscendingOrder
        )

        self.sort_descending_action.setChecked(
            self.sort_order
            == Qt.DescendingOrder
        )

    # -----------------------------------------------------

    def reload_directory(self):

        if not self.current_directory:
            return

        self.load_directory(
            self.current_directory
        )

    # =====================================================
    # Sort directory entries
    # =====================================================

    def sort_entries(
        self,
        entries
    ):

        # Remove hidden files/directories.
        entries = [
            entry
            for entry in entries
            if not entry.name.startswith(".")
        ]

        # -------------------------------------------------
        # Sort by Name
        # -------------------------------------------------

        if self.sort_column == "name":

            directories = [
                entry
                for entry in entries
                if entry.is_dir()
            ]

            files = [
                entry
                for entry in entries
                if not entry.is_dir()
            ]

            directories.sort(
                key=lambda entry:
                    entry.name.lower(),
                reverse=(
                    self.sort_order
                    == Qt.DescendingOrder
                )
            )

            files.sort(
                key=lambda entry:
                    entry.name.lower(),
                reverse=(
                    self.sort_order
                    == Qt.DescendingOrder
                )
            )

            return directories + files

        # -------------------------------------------------
        # Sort by Date Modified
        # -------------------------------------------------

        if self.sort_column == "modified":

            directories = [
                entry
                for entry in entries
                if entry.is_dir()
            ]

            files = [
                entry
                for entry in entries
                if not entry.is_dir()
            ]

            def get_modified_time(entry):

                try:
                    return entry.stat().st_mtime

                except OSError:
                    return 0

            directories.sort(
                key=get_modified_time,
                reverse=(
                    self.sort_order
                    == Qt.DescendingOrder
                )
            )

            files.sort(
                key=get_modified_time,
                reverse=(
                    self.sort_order
                    == Qt.DescendingOrder
                )
            )

            return directories + files

        return entries

    # =====================================================
    # Viewer switching
    # =====================================================

    def show_text_viewer(self):

        self.image_scroll.hide()
        self.viewer.show()

    # -----------------------------------------------------

    def show_image_viewer(self):

        self.viewer.hide()
        self.image_scroll.show()

    # =====================================================
    # Open directory
    # =====================================================

    def open_directory(self):

        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Directory"
        )

        if directory:

            self.load_directory(
                directory
            )

    # =====================================================
    # Load directory
    # =====================================================

    def load_directory(
        self,
        directory
    ):

        self.current_directory = directory

        # Clear old contents.
        self.tree.clear()

        self.viewer.clear()

        self.image_label.clear()

        self.image_label.setText(
            "No image selected"
        )

        self.current_pixmap = None

        self.show_text_viewer()

        self.path_label.setText(
            directory
        )

        # -------------------------------------------------
        # Root item
        # -------------------------------------------------

        root_name = os.path.basename(
            os.path.normpath(directory)
        )

        if not root_name:
            root_name = directory

        root_item = QTreeWidgetItem(
            [root_name]
        )

        root_item.setData(
            0,
            Qt.UserRole,
            directory
        )

        self.tree.addTopLevelItem(
            root_item
        )

        root_item.setExpanded(
            True
        )

        # Populate tree.
        self.populate_directory(
            root_item,
            directory
        )

        # Select root.
        self.tree.setCurrentItem(
            root_item
        )

    # =====================================================
    # Populate directory
    # =====================================================

    def populate_directory(
        self,
        parent_item,
        directory
    ):

        try:

            entries = list(
                os.scandir(directory)
            )

        except PermissionError:
            return

        except OSError:
            return

        entries = self.sort_entries(
            entries
        )

        for entry in entries:

            try:
                is_directory = entry.is_dir()

            except OSError:
                continue

            item = QTreeWidgetItem(
                [entry.name]
            )

            item.setData(
                0,
                Qt.UserRole,
                entry.path
            )

            parent_item.addChild(
                item
            )

            # Recursively populate directories.
            if is_directory:

                self.populate_directory(
                    item,
                    entry.path
                )

    # =====================================================
    # Selection changed
    # =====================================================

    def file_selection_changed(
        self,
        current,
        previous
    ):

        if current is None:
            return

        path = current.data(
            0,
            Qt.UserRole
        )

        if not path:
            return

        # -------------------------------------------------
        # Directory selected
        # -------------------------------------------------

        if os.path.isdir(path):

            self.viewer.clear()

            self.image_label.clear()

            self.image_label.setText(
                "Directory selected"
            )

            self.current_pixmap = None

            self.show_text_viewer()

            return

        # -------------------------------------------------
        # File selected
        # -------------------------------------------------

        self.display_file(
            path
        )

    # =====================================================
    # Display file
    # =====================================================

    def display_file(
        self,
        path
    ):

        extension = os.path.splitext(
            path
        )[1].lower()

        # Image.
        if extension in IMAGE_EXTENSIONS:

            self.display_image(
                path
            )

            return

        # Text viewer.
        self.show_text_viewer()

        self.viewer.clear()

        # RTF.
        if extension == ".rtf":

            self.display_rtf(
                path
            )

            return

        # Normal text.
        if extension in TEXT_EXTENSIONS:

            self.display_text(
                path
            )

            return

        # Unknown file type.
        self.viewer.setPlainText(
            "No preview available for this file type.\n\n"
            f"{path}"
        )

    # =====================================================
    # Display image
    # =====================================================

    def display_image(
        self,
        path
    ):

        self.show_image_viewer()

        try:

            file_size = os.path.getsize(
                path
            )

        except OSError as error:

            self.image_label.setText(
                f"Could not access image:\n\n{error}"
            )

            return

        if file_size > MAX_IMAGE_FILE_SIZE:

            self.image_label.setText(
                "This image is larger than 50 MB "
                "and was not loaded."
            )

            return

        pixmap = QPixmap(
            path
        )

        if pixmap.isNull():

            self.image_label.setText(
                "Could not load this image.\n\n"
                f"{path}"
            )

            return

        self.current_pixmap = pixmap

        self.update_image_preview()

    # =====================================================
    # Update image preview
    # =====================================================

    def update_image_preview(self):

        if self.current_pixmap is None:
            return

        if self.current_pixmap.isNull():
            return

        available_size = (
            self.image_scroll
            .viewport()
            .size()
        )

        scaled_pixmap = (
            self.current_pixmap.scaled(
                available_size,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
        )

        self.image_label.setPixmap(
            scaled_pixmap
        )

    # =====================================================
    # Window resize
    # =====================================================

    def resizeEvent(
        self,
        event
    ):

        super().resizeEvent(
            event
        )

        if self.current_pixmap is not None:

            if self.image_scroll.isVisible():

                self.update_image_preview()

    # =====================================================
    # Display normal text
    # =====================================================

    def display_text(
        self,
        path
    ):

        try:

            file_size = os.path.getsize(
                path
            )

        except OSError as error:

            self.viewer.setPlainText(
                f"Could not access file:\n\n{error}"
            )

            return

        if file_size > MAX_TEXT_FILE_SIZE:

            self.viewer.setPlainText(
                "This file is larger than 10 MB "
                "and was not loaded."
            )

            return

        try:

            # First try UTF-8.
            try:

                with open(
                    path,
                    "r",
                    encoding="utf-8"
                ) as file:

                    contents = file.read()

            except UnicodeDecodeError:

                # Fall back to Windows-1252.
                with open(
                    path,
                    "r",
                    encoding="cp1252"
                ) as file:

                    contents = file.read()

            self.viewer.setPlainText(
                contents
            )

        except PermissionError:

            self.viewer.setPlainText(
                "Permission denied."
            )

        except OSError as error:

            self.viewer.setPlainText(
                f"Could not open file:\n\n{error}"
            )

    # =====================================================
    # Display RTF
    # =====================================================

    def display_rtf(
        self,
        path
    ):

        try:

            file_size = os.path.getsize(
                path
            )

        except OSError as error:

            self.viewer.setPlainText(
                f"Could not access RTF file:\n\n{error}"
            )

            return

        if file_size > MAX_RTF_FILE_SIZE:

            self.viewer.setPlainText(
                "This RTF file is larger than 20 MB "
                "and was not loaded."
            )

            return

        # -------------------------------------------------
        # Import striprtf when needed.
        # -------------------------------------------------

        try:

            from striprtf.striprtf import (
                rtf_to_text
            )

        except ImportError:

            self.viewer.setPlainText(
                "The 'striprtf' package is not installed.\n\n"
                "Install it with:\n\n"
                "pip install striprtf"
            )

            return

        # -------------------------------------------------
        # Read and convert RTF.
        # -------------------------------------------------

        try:

            with open(
                path,
                "r",
                encoding="utf-8",
                errors="replace"
            ) as file:

                rtf_contents = file.read()

            contents = rtf_to_text(
                rtf_contents
            )

            self.viewer.setPlainText(
                contents
            )

        except PermissionError:

            self.viewer.setPlainText(
                "Permission denied."
            )

        except OSError as error:

            self.viewer.setPlainText(
                f"Could not open RTF file:\n\n{error}"
            )

        except Exception as error:

            self.viewer.setPlainText(
                f"Could not parse RTF file:\n\n{error}"
            )


# =========================================================
# Application entry point
# =========================================================

def main():

    app = QApplication(
        sys.argv
    )

    app.setApplicationName(
        "File Viewer"
    )

    window = FileViewer()

    window.show()

    sys.exit(
        app.exec()
    )


if __name__ == "__main__":
    main()

