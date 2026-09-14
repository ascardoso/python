#!/usr/bin/env python3

import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import (
    QAction,
    QFont,
    QKeySequence,
    QPixmap,
)
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QInputDialog,
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

MAX_TEXT_FILE_SIZE = 10 * 1024 * 1024
MAX_RTF_FILE_SIZE = 20 * 1024 * 1024
MAX_IMAGE_FILE_SIZE = 50 * 1024 * 1024


# =========================================================
# Font settings
# =========================================================

DEFAULT_FONT_SIZE = 11
MIN_FONT_SIZE = 6
MAX_FONT_SIZE = 40
FONT_SIZE_STEP = 1


class FileViewer(QMainWindow):

    # =====================================================
    # Initialization
    # =====================================================

    def __init__(self):

        super().__init__()

        self.setWindowTitle(
            "File Viewer"
        )

        self.resize(
            1200,
            750
        )

        self.setMinimumSize(
            800,
            500
        )

        # -------------------------------------------------
        # Application state
        # -------------------------------------------------

        self.current_directory = None

        self.current_file = None

        self.current_pixmap = None

        # True while the program is loading a selection.
        #
        # This prevents currentItemChanged and itemClicked
        # from both loading the same file.
        self.loading_file = False

        # True when the user has enabled editing.
        self.editing_enabled = False

        # -------------------------------------------------
        # Find state
        # -------------------------------------------------

        self.find_text = ""

        # -------------------------------------------------
        # Sorting
        # -------------------------------------------------

        self.sort_column = "name"

        self.sort_order = Qt.AscendingOrder

        # -------------------------------------------------
        # Font
        # -------------------------------------------------

        self.font_size = DEFAULT_FONT_SIZE

        # -------------------------------------------------
        # Build UI
        # -------------------------------------------------

        self.create_ui()


    # =====================================================
    # Create UI
    # =====================================================

    def create_ui(self):

        self.create_menus()

        # -------------------------------------------------
        # Toolbar
        # -------------------------------------------------

        toolbar = QToolBar(
            "Main Toolbar"
        )

        toolbar.setMovable(
            False
        )

        self.addToolBar(
            toolbar
        )

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
        # Tree
        # -------------------------------------------------

        self.tree = QTreeWidget()

        self.tree.setHeaderLabel(
            "Files"
        )

        self.tree.setAnimated(
            True
        )

        self.tree.setUniformRowHeights(
            True
        )

        # One signal handles mouse and keyboard selection.
        self.tree.currentItemChanged.connect(
            self.file_selection_changed
        )

        # -------------------------------------------------
        # Text viewer
        # -------------------------------------------------

        self.viewer = QTextEdit()

        self.viewer.setReadOnly(
            True
        )

        self.viewer.setAcceptRichText(
            False
        )

        self.viewer.setStyleSheet(
            """
            QTextEdit {
                selection-background-color: #3399ff;
                selection-color: white;
            }
            """
        )

        self.viewer.document().modificationChanged.connect(
            self.document_modified_changed
        )

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

        # =================================================
        # File menu
        # =================================================

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

        # =================================================
        # Edit menu
        # =================================================

        edit_menu = self.menuBar().addMenu(
            "Edit"
        )

        self.edit_action = QAction(
            "Enable Editing",
            self
        )

        self.edit_action.setCheckable(
            True
        )

        self.edit_action.setShortcut(
            QKeySequence("Ctrl+E")
        )

        self.edit_action.triggered.connect(
            self.toggle_editing
        )

        edit_menu.addAction(
            self.edit_action
        )

        edit_menu.addSeparator()

        self.save_action = QAction(
            "Save",
            self
        )

        self.save_action.setShortcut(
            QKeySequence("Ctrl+S")
        )

        self.save_action.setEnabled(
            False
        )

        self.save_action.triggered.connect(
            self.save_file
        )

        edit_menu.addAction(
            self.save_action
        )

        self.save_as_action = QAction(
            "Save As...",
            self
        )

        self.save_as_action.setShortcut(
            QKeySequence("Ctrl+Shift+S")
        )

        self.save_as_action.setEnabled(
            False
        )

        self.save_as_action.triggered.connect(
            self.save_file_as
        )

        edit_menu.addAction(
            self.save_as_action
        )

        # =================================================
        # Find menu
        # =================================================

        find_menu = self.menuBar().addMenu(
            "Find"
        )

        self.find_action = QAction(
            "Find...",
            self
        )

        self.find_action.setShortcut(
            QKeySequence("Ctrl+F")
        )

        self.find_action.triggered.connect(
            self.find_text_in_viewer
        )

        find_menu.addAction(
            self.find_action
        )

        self.find_next_action = QAction(
            "Find Next",
            self
        )

        self.find_next_action.setShortcut(
            QKeySequence("F3")
        )

        self.find_next_action.triggered.connect(
            self.find_next
        )

        find_menu.addAction(
            self.find_next_action
        )

        # =================================================
        # Sort menu
        # =================================================

        sort_menu = self.menuBar().addMenu(
            "Sort"
        )

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
            lambda:
            self.set_sort_column(
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
            lambda:
            self.set_sort_column(
                "modified"
            )
        )

        sort_by_menu.addAction(
            self.sort_date_action
        )

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
            lambda:
            self.set_sort_order(
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
            lambda:
            self.set_sort_order(
                Qt.DescendingOrder
            )
        )

        order_menu.addAction(
            self.sort_descending_action
        )

        sort_menu.addSeparator()

        name_az_action = QAction(
            "Name — A to Z",
            self
        )

        name_az_action.triggered.connect(
            lambda:
            self.set_sorting(
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
            lambda:
            self.set_sorting(
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
            lambda:
            self.set_sorting(
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
            lambda:
            self.set_sorting(
                "modified",
                Qt.AscendingOrder
            )
        )

        sort_menu.addAction(
            oldest_action
        )

        # =================================================
        # View menu
        # =================================================

        view_menu = self.menuBar().addMenu(
            "View"
        )

        font_menu = view_menu.addMenu(
            "Font Size"
        )

        increase_action = QAction(
            "Increase Font Size",
            self
        )

        increase_action.setShortcut(
            QKeySequence("Ctrl++")
        )

        increase_action.triggered.connect(
            self.increase_font_size
        )

        font_menu.addAction(
            increase_action
        )

        decrease_action = QAction(
            "Decrease Font Size",
            self
        )

        decrease_action.setShortcut(
            QKeySequence("Ctrl+-")
        )

        decrease_action.triggered.connect(
            self.decrease_font_size
        )

        font_menu.addAction(
            decrease_action
        )

        reset_action = QAction(
            "Reset Font Size",
            self
        )

        reset_action.setShortcut(
            QKeySequence("Ctrl+0")
        )

        reset_action.triggered.connect(
            self.reset_font_size
        )

        font_menu.addAction(
            reset_action
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
    # Selection changed
    # =====================================================

    def file_selection_changed(
        self,
        current,
        previous
    ):

        print(
            "\nDEBUG: currentItemChanged fired"
        )

        if current is None:

            print(
                "DEBUG: current item is None"
            )

            return

        path = current.data(
            0,
            Qt.UserRole
        )

        print(
            "DEBUG: selected path =",
            path
        )

        if not path:

            return

        self.select_file_path(
            path
        )


    # =====================================================
    # Select file/path
    # =====================================================

    def select_file_path(
        self,
        path
    ):

        print(
            "\nDEBUG 2: select_file_path()"
        )

        print(
            "DEBUG 2: path =",
            path
        )

        print(
            "DEBUG 2: exists =",
            os.path.exists(path)
        )

        print(
            "DEBUG 2: is file =",
            os.path.isfile(path)
        )

        print(
            "DEBUG 2: is directory =",
            os.path.isdir(path)
        )

        # -------------------------------------------------
        # Prevent duplicate processing while this method
        # is already handling a selection.
        # -------------------------------------------------

        if self.loading_file:

            print(
                "DEBUG 2: loading_file=True; ignoring duplicate"
            )

            return

        # -------------------------------------------------
        # Protect unsaved changes when changing files.
        # -------------------------------------------------

        if (
            self.current_file
            and self.current_file != path
            and self.viewer.document().isModified()
        ):

            print(
                "DEBUG 2: current document has unsaved changes"
            )

            if not self.maybe_save_changes():

                print(
                    "DEBUG 2: selection cancelled"
                )

                return

        self.loading_file = True

        try:

            # -------------------------------------------------
            # Reset viewer state.
            # -------------------------------------------------

            self.current_pixmap = None

            self.editing_enabled = False

            self.edit_action.setChecked(
                False
            )

            self.save_action.setEnabled(
                False
            )

            self.save_as_action.setEnabled(
                False
            )

            self.viewer.setReadOnly(
                True
            )

            # -------------------------------------------------
            # Clear existing text.
            # -------------------------------------------------

            self.viewer.clear()

            # -------------------------------------------------
            # Clear selection correctly.
            #
            # QTextEdit has no clearSelection() method.
            # -------------------------------------------------

            cursor = self.viewer.textCursor()

            cursor.clearSelection()

            self.viewer.setTextCursor(
                cursor
            )

            self.viewer.document().setModified(
                False
            )

            # -------------------------------------------------
            # Directory.
            # -------------------------------------------------

            if os.path.isdir(path):

                print(
                    "DEBUG 2: displaying directory"
                )

                self.current_file = None

                self.image_label.clear()

                self.image_label.setText(
                    "Directory selected"
                )

                self.show_text_viewer()

                self.update_window_title()

                return

            # -------------------------------------------------
            # Invalid path.
            # -------------------------------------------------

            if not os.path.isfile(path):

                print(
                    "DEBUG 2: invalid file path"
                )

                self.current_file = None

                self.viewer.setPlainText(
                    "Unable to open this item:\n\n"
                    f"{path}"
                )

                return

            # -------------------------------------------------
            # File.
            # -------------------------------------------------

            self.current_file = path

            print(
                "DEBUG 2: loading file"
            )

            self.display_file(
                path
            )

        finally:

            self.loading_file = False

            print(
                "DEBUG 2: loading_file=False"
            )


    # =====================================================
    # Display file
    # =====================================================

    def display_file(
        self,
        path
    ):

        print(
            "\nDEBUG 3: display_file()"
        )

        print(
            "DEBUG 3: path =",
            path
        )

        extension = os.path.splitext(
            path
        )[1].lower()

        print(
            "DEBUG 3: extension =",
            extension
        )

        # -------------------------------------------------
        # Image.
        # -------------------------------------------------

        if extension in IMAGE_EXTENSIONS:

            print(
                "DEBUG 3: image"
            )

            self.display_image(
                path
            )

            return

        # -------------------------------------------------
        # Text viewer.
        # -------------------------------------------------

        self.show_text_viewer()

        # -------------------------------------------------
        # RTF.
        # -------------------------------------------------

        if extension == ".rtf":

            print(
                "DEBUG 3: RTF"
            )

            self.display_rtf(
                path
            )

            return

        # -------------------------------------------------
        # Normal text.
        # -------------------------------------------------

        if extension in TEXT_EXTENSIONS:

            print(
                "DEBUG 3: text"
            )

            self.display_text(
                path
            )

            return

        # -------------------------------------------------
        # Unknown file type.
        # -------------------------------------------------

        print(
            "DEBUG 3: unknown type"
        )

        self.viewer.setPlainText(
            "No preview available for this file type.\n\n"
            f"{path}"
        )

        self.viewer.document().setModified(
            False
        )

        self.update_window_title()


    # =====================================================
    # Display normal text
    # =====================================================

    def display_text(
        self,
        path
    ):

        print(
            "\nDEBUG 4: display_text()"
        )

        print(
            "DEBUG 4: path =",
            path
        )

        try:

            file_size = os.path.getsize(
                path
            )

        except OSError as error:

            print(
                "DEBUG 4: getsize error =",
                repr(error)
            )

            self.viewer.setPlainText(
                f"Could not access file:\n\n{error}"
            )

            return

        print(
            "DEBUG 4: file size =",
            file_size
        )

        if file_size > MAX_TEXT_FILE_SIZE:

            self.viewer.setPlainText(
                "This file is larger than 10 MB "
                "and was not loaded."
            )

            return

        try:

            # -------------------------------------------------
            # UTF-8 first.
            # -------------------------------------------------

            try:

                print(
                    "DEBUG 4: trying UTF-8"
                )

                with open(
                    path,
                    "r",
                    encoding="utf-8"
                ) as file:

                    contents = file.read()

            except UnicodeDecodeError:

                print(
                    "DEBUG 4: UTF-8 failed; trying cp1252"
                )

                with open(
                    path,
                    "r",
                    encoding="cp1252"
                ) as file:

                    contents = file.read()

            print(
                "DEBUG 4: characters read =",
                len(contents)
            )

            # -------------------------------------------------
            # Put contents into viewer.
            # -------------------------------------------------

            self.viewer.setPlainText(
                contents
            )

            # -------------------------------------------------
            # This load came from disk, so it is not modified.
            # -------------------------------------------------

            self.viewer.document().setModified(
                False
            )

            self.update_window_title()

            print(
                "DEBUG 4: viewer characters =",
                len(
                    self.viewer.toPlainText()
                )
            )

            print(
                "DEBUG 4: viewer visible =",
                self.viewer.isVisible()
            )

            print(
                "DEBUG 4: viewer geometry =",
                self.viewer.geometry()
            )

        except PermissionError:

            print(
                "DEBUG 4: permission denied"
            )

            self.viewer.setPlainText(
                "Permission denied."
            )

        except OSError as error:

            print(
                "DEBUG 4: open error =",
                repr(error)
            )

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

            self.viewer.document().setModified(
                False
            )

            self.update_window_title()

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
    # Resize
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
    # Editing
    # =====================================================

    def toggle_editing(
        self,
        checked
    ):

        print(
            "\nDEBUG EDIT: toggle_editing =",
            checked
        )

        if checked:

            if not self.current_file:

                self.edit_action.setChecked(
                    False
                )

                QMessageBox.information(
                    self,
                    "Edit",
                    "Select a text file first."
                )

                return

            extension = os.path.splitext(
                self.current_file
            )[1].lower()

            if (
                extension not in TEXT_EXTENSIONS
                and extension != ".rtf"
            ):

                self.edit_action.setChecked(
                    False
                )

                QMessageBox.information(
                    self,
                    "Edit",
                    "This file type cannot be edited."
                )

                return

            self.editing_enabled = True

            self.viewer.setReadOnly(
                False
            )

            self.save_action.setEnabled(
                True
            )

            self.save_as_action.setEnabled(
                True
            )

            self.viewer.setFocus()

            self.update_window_title()

            return

        # -------------------------------------------------
        # Turning editing off.
        # -------------------------------------------------

        if not self.maybe_save_changes():

            self.edit_action.setChecked(
                True
            )

            return

        self.editing_enabled = False

        self.viewer.setReadOnly(
            True
        )

        self.save_action.setEnabled(
            False
        )

        self.save_as_action.setEnabled(
            False
        )

        self.update_window_title()


    # =====================================================
    # Document modified
    # =====================================================

    def document_modified_changed(
        self,
        modified
    ):

        print(
            "DEBUG EDIT: document modified =",
            modified
        )

        self.update_window_title()


    # =====================================================
    # Window title
    # =====================================================

    def update_window_title(self):

        if not self.current_file:

            self.setWindowTitle(
                "File Viewer"
            )

            return

        filename = os.path.basename(
            self.current_file
        )

        if self.viewer.document().isModified():

            filename = "*" + filename

        self.setWindowTitle(
            f"{filename} - File Viewer"
        )


    # =====================================================
    # Unsaved changes
    # =====================================================

    def maybe_save_changes(self):

        if not self.viewer.document().isModified():

            return True

        if not self.current_file:

            return True

        filename = os.path.basename(
            self.current_file
        )

        result = QMessageBox.question(
            self,
            "Unsaved Changes",
            f"Save changes to '{filename}'?",
            QMessageBox.Save
            | QMessageBox.Discard
            | QMessageBox.Cancel,
            QMessageBox.Save
        )

        if result == QMessageBox.Save:

            return self.save_file()

        if result == QMessageBox.Discard:

            return True

        return False


    # =====================================================
    # Save
    # =====================================================

    def save_file(self):

        if not self.current_file:

            return self.save_file_as()

        if not self.editing_enabled:

            return False

        extension = os.path.splitext(
            self.current_file
        )[1].lower()

        # -------------------------------------------------
        # RTF.
        # -------------------------------------------------

        if extension == ".rtf":

            return self.save_rtf(
                self.current_file
            )

        # -------------------------------------------------
        # Normal text.
        # -------------------------------------------------

        try:

            contents = self.viewer.toPlainText()

            with open(
                self.current_file,
                "w",
                encoding="utf-8"
            ) as file:

                file.write(
                    contents
                )

            self.viewer.document().setModified(
                False
            )

            self.update_window_title()

            print(
                "DEBUG SAVE: saved",
                self.current_file
            )

            return True

        except PermissionError:

            QMessageBox.critical(
                self,
                "Save Error",
                "Permission denied.\n\n"
                f"{self.current_file}"
            )

            return False

        except OSError as error:

            QMessageBox.critical(
                self,
                "Save Error",
                f"Could not save the file:\n\n{error}"
            )

            return False


    # =====================================================
    # Save As
    # =====================================================

    def save_file_as(self):

        if not self.editing_enabled:

            return False

        default_name = (
            os.path.basename(
                self.current_file
            )
            if self.current_file
            else "untitled.txt"
        )

        path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Save File As",
            default_name,
            (
                "Text Files (*.txt *.py *.js *.ts *.jsx *.tsx "
                "*.html *.htm *.css *.json *.xml *.yaml *.yml "
                "*.md *.csv *.ini *.cfg *.conf *.log *.sql "
                "*.sh *.bat *.ps1 *.java *.c *.cpp *.h *.hpp "
                "*.rs *.go *.php *.rb *.swift *.kt);;"
                "RTF Files (*.rtf);;"
                "All Files (*)"
            )
        )

        if not path:

            return False

        extension = os.path.splitext(
            path
        )[1].lower()

        try:

            if extension == ".rtf":

                if not self.save_rtf(
                    path
                ):

                    return False

            else:

                contents = self.viewer.toPlainText()

                with open(
                    path,
                    "w",
                    encoding="utf-8"
                ) as file:

                    file.write(
                        contents
                    )

                self.viewer.document().setModified(
                    False
                )

            # -------------------------------------------------
            # IMPORTANT:
            #
            # Save As becomes the new current file.
            # -------------------------------------------------

            self.current_file = path

            self.viewer.document().setModified(
                False
            )

            self.update_window_title()

            print(
                "DEBUG SAVE AS: current_file =",
                self.current_file
            )

            return True

        except PermissionError:

            QMessageBox.critical(
                self,
                "Save Error",
                "Permission denied.\n\n"
                f"{path}"
            )

            return False

        except OSError as error:

            QMessageBox.critical(
                self,
                "Save Error",
                f"Could not save the file:\n\n{error}"
            )

            return False


    # =====================================================
    # Save RTF
    # =====================================================

    def save_rtf(
        self,
        path
    ):

        try:

            text = self.viewer.toPlainText()

            text = (
                text
                .replace(
                    "\\",
                    "\\\\"
                )
                .replace(
                    "{",
                    "\\{"
                )
                .replace(
                    "}",
                    "\\}"
                )
            )

            paragraphs = text.splitlines()

            rtf_body = "\\par\n".join(
                paragraphs
            )

            rtf_contents = (
                "{\\rtf1\\ansi\\deff0\n"
                "{\\fonttbl{\\f0 Courier New;}}\n"
                "\\f0\\fs22\n"
                f"{rtf_body}\n"
                "}"
            )

            with open(
                path,
                "w",
                encoding="ascii",
                errors="ignore"
            ) as file:

                file.write(
                    rtf_contents
                )

            self.viewer.document().setModified(
                False
            )

            self.update_window_title()

            print(
                "DEBUG SAVE RTF: saved",
                path
            )

            return True

        except OSError as error:

            QMessageBox.critical(
                self,
                "Save Error",
                f"Could not save RTF file:\n\n{error}"
            )

            return False


    # =====================================================
    # Find
    # =====================================================

    def find_text_in_viewer(self):

        if not self.viewer.isVisible():

            return

        text, accepted = QInputDialog.getText(
            self,
            "Find",
            "Find text:",
            text=self.find_text
        )

        if not accepted:

            return

        if not text:

            return

        self.find_text = text

        self.find_next()


    # =====================================================
    # Find Next
    # =====================================================

    def find_next(self):

        if not self.find_text:

            self.find_text_in_viewer()

            return

        if not self.viewer.isVisible():

            return

        document = self.viewer.document()

        cursor = self.viewer.textCursor()

        start_position = cursor.position()

        if cursor.hasSelection():

            start_position = cursor.selectionEnd()

        search_cursor = document.find(
            self.find_text,
            start_position
        )

        # -------------------------------------------------
        # Wrap around.
        # -------------------------------------------------

        if search_cursor.isNull():

            search_cursor = document.find(
                self.find_text,
                0
            )

        if search_cursor.isNull():

            QMessageBox.information(
                self,
                "Find",
                f'Text not found:\n\n"{self.find_text}"'
            )

            return

        # -------------------------------------------------
        # Select actual match.
        # -------------------------------------------------

        self.viewer.setTextCursor(
            search_cursor
        )

        self.viewer.ensureCursorVisible()

        self.viewer.setFocus()


    # =====================================================
    # Font
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

        return (
            f"Current Size: "
            f"{self.font_size} pt"
        )


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
    # Sorting
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

        if not self.maybe_save_changes():

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

        # -------------------------------------------------
        # Hide dot files.
        # -------------------------------------------------

        entries = [
            entry
            for entry in entries
            if not entry.name.startswith(".")
        ]

        # -------------------------------------------------
        # Sort by name.
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

            reverse = (
                self.sort_order
                == Qt.DescendingOrder
            )

            directories.sort(
                key=lambda entry:
                    entry.name.lower(),
                reverse=reverse
            )

            files.sort(
                key=lambda entry:
                    entry.name.lower(),
                reverse=reverse
            )

            return directories + files

        # -------------------------------------------------
        # Sort by modified time.
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

            def modified_time(
                entry
            ):

                try:

                    return entry.stat().st_mtime

                except OSError:

                    return 0

            reverse = (
                self.sort_order
                == Qt.DescendingOrder
            )

            directories.sort(
                key=modified_time,
                reverse=reverse
            )

            files.sort(
                key=modified_time,
                reverse=reverse
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

        if not self.maybe_save_changes():

            return

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

        self.current_file = None

        self.current_pixmap = None

        self.loading_file = False

        self.editing_enabled = False

        self.find_text = ""

        self.viewer.setReadOnly(
            True
        )

        self.edit_action.setChecked(
            False
        )

        self.save_action.setEnabled(
            False
        )

        self.save_as_action.setEnabled(
            False
        )

        self.tree.clear()

        self.viewer.clear()

        self.viewer.document().setModified(
            False
        )

        self.image_label.clear()

        self.image_label.setText(
            "No image selected"
        )

        self.show_text_viewer()

        self.path_label.setText(
            directory
        )

        self.update_window_title()

        # -------------------------------------------------
        # Root.
        # -------------------------------------------------

        root_name = os.path.basename(
            os.path.normpath(
                directory
            )
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

        self.populate_directory(
            root_item,
            directory
        )

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
                os.scandir(
                    directory
                )
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

            if is_directory:

                self.populate_directory(
                    item,
                    entry.path
                )


    # =====================================================
    # Close
    # =====================================================

    def closeEvent(
        self,
        event
    ):

        if self.maybe_save_changes():

            event.accept()

        else:

            event.ignore()


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
