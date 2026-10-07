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
"""

# =========================================================
# File Viewer
# =========================================================
#
# Lightweight Windows/macOS/Linux-style file browser
# written in Python using PySide6.
#
# Features:
#
#   - Select a directory
#   - Browse files recursively
#   - Sort by name or date modified
#   - Preview text/source files
#   - Preview RTF files
#   - Preview images
#   - Preview PDF files
#   - Dedicated PDF toolbar
#   - PDF previous/next/first/last page
#   - PDF page number selector
#   - PDF zoom in/out/reset
#   - PDF fit-to-width
#   - PDF fit-to-page
#   - PDF single-page / continuous mode
#   - PDF back/forward navigation history
#   - Find text in the text viewer
#   - Find Next with F3
#   - Optional editing mode
#   - Save
#   - Save As
#   - Unsaved-change protection
#   - Font size controls
#
# Dependencies:
#
#   pip install PySide6 striprtf
#
# PDF support is provided by the QtPdf module included with
# PySide6.
#
# =========================================================


import os
import sys


from PySide6.QtCore import (
    QPointF,
    Qt,
)


from PySide6.QtGui import (
    QAction,
    QFont,
    QKeySequence,
    QPixmap,
)


from PySide6.QtPdf import (
    QPdfDocument,
)


from PySide6.QtPdfWidgets import (
    QPdfView,
)


from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QInputDialog,
    QScrollArea,
    QSpinBox,
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


PDF_EXTENSIONS = {
    ".pdf",
}


# =========================================================
# File size limits
# =========================================================


MAX_TEXT_FILE_SIZE = 10 * 1024 * 1024

MAX_RTF_FILE_SIZE = 20 * 1024 * 1024

MAX_IMAGE_FILE_SIZE = 50 * 1024 * 1024

MAX_PDF_FILE_SIZE = 250 * 1024 * 1024


# =========================================================
# Font settings
# =========================================================


DEFAULT_FONT_SIZE = 11

MIN_FONT_SIZE = 6

MAX_FONT_SIZE = 40

FONT_SIZE_STEP = 1


# =========================================================
# PDF settings
# =========================================================


PDF_DEFAULT_ZOOM = 1.0

PDF_MIN_ZOOM = 0.25

PDF_MAX_ZOOM = 5.0

PDF_ZOOM_STEP = 1.20


# =========================================================
# Main window
# =========================================================


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

        self.loading_file = False

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
        # PDF state
        # -------------------------------------------------

        self.pdf_document = QPdfDocument(
            self
        )

        self.pdf_view = QPdfView()

        self.pdf_view.setPageMode(
            QPdfView.PageMode.MultiPage
        )

        self.pdf_view.setZoomMode(
            QPdfView.ZoomMode.FitToWidth
        )

        self.pdf_view.setDocument(
            self.pdf_document
        )

        self.pdf_toolbar = None

        self.pdf_page_spin = None

        self.pdf_zoom_label = None

        self.pdf_zoom_combo = None

        self.pdf_previous_action = None

        self.pdf_next_action = None

        self.pdf_first_action = None

        self.pdf_last_action = None

        self.pdf_back_action = None

        self.pdf_forward_action = None

        self.pdf_zoom_in_action = None

        self.pdf_zoom_out_action = None

        self.pdf_zoom_reset_action = None

        self.pdf_fit_width_action = None

        self.pdf_fit_page_action = None

        self.pdf_single_page_action = None

        self.pdf_continuous_action = None

        # -------------------------------------------------
        # Build UI
        # -------------------------------------------------

        self.create_ui()

        self.create_pdf_toolbar()

        self.pdf_document.statusChanged.connect(
            self.pdf_status_changed
        )

        self.pdf_view.pageNavigator().currentPageChanged.connect(
            self.pdf_current_page_changed
        )

        self.pdf_view.pageNavigator().backAvailableChanged.connect(
            self.pdf_navigation_state_changed
        )

        self.pdf_view.pageNavigator().forwardAvailableChanged.connect(
            self.pdf_navigation_state_changed
        )

        self.pdf_view.zoomFactorChanged.connect(
            self.pdf_zoom_changed
        )

        self.pdf_view.zoomModeChanged.connect(
            self.pdf_zoom_mode_changed
        )

        self.update_pdf_toolbar_state()


    # =====================================================
    # Create UI
    # =====================================================

    def create_ui(self):

        self.create_menus()

        # -------------------------------------------------
        # Main toolbar
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

        viewer_layout.addWidget(
            self.pdf_view
        )

        self.image_scroll.hide()

        self.pdf_view.hide()

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
    # PDF toolbar
    # =====================================================

    def create_pdf_toolbar(self):

        toolbar = QToolBar(
            "PDF Viewer"
        )

        toolbar.setMovable(
            False
        )

        toolbar.setFloatable(
            False
        )

        toolbar.setObjectName(
            "PdfToolbar"
        )

        self.pdf_toolbar = toolbar

        self.addToolBar(
            Qt.TopToolBarArea,
            toolbar
        )

        # -------------------------------------------------
        # Navigation history
        # -------------------------------------------------

        self.pdf_back_action = toolbar.addAction(
            "← Back"
        )

        self.pdf_back_action.setToolTip(
            "Back in PDF navigation history"
        )

        self.pdf_back_action.triggered.connect(
            self.pdf_go_back
        )

        self.pdf_forward_action = toolbar.addAction(
            "Forward →"
        )

        self.pdf_forward_action.setToolTip(
            "Forward in PDF navigation history"
        )

        self.pdf_forward_action.triggered.connect(
            self.pdf_go_forward
        )

        toolbar.addSeparator()

        # -------------------------------------------------
        # Page navigation
        # -------------------------------------------------

        self.pdf_first_action = toolbar.addAction(
            "⏮ First"
        )

        self.pdf_first_action.triggered.connect(
            self.pdf_first_page
        )

        self.pdf_previous_action = toolbar.addAction(
            "◀ Previous"
        )

        self.pdf_previous_action.triggered.connect(
            self.pdf_previous_page
        )

        toolbar.addWidget(
            QLabel("Page:")
        )

        self.pdf_page_spin = QSpinBox()

        self.pdf_page_spin.setMinimum(
            1
        )

        self.pdf_page_spin.setMaximum(
            1
        )

        self.pdf_page_spin.setFixedWidth(
            75
        )

        self.pdf_page_spin.setToolTip(
            "PDF page number"
        )

        self.pdf_page_spin.valueChanged.connect(
            self.pdf_page_spin_changed
        )

        toolbar.addWidget(
            self.pdf_page_spin
        )

        self.pdf_page_count_label = QLabel(
            "of 0"
        )

        toolbar.addWidget(
            self.pdf_page_count_label
        )

        self.pdf_next_action = toolbar.addAction(
            "Next ▶"
        )

        self.pdf_next_action.triggered.connect(
            self.pdf_next_page
        )

        self.pdf_last_action = toolbar.addAction(
            "Last ⏭"
        )

        self.pdf_last_action.triggered.connect(
            self.pdf_last_page
        )

        toolbar.addSeparator()

        # -------------------------------------------------
        # Zoom
        # -------------------------------------------------

        self.pdf_zoom_out_action = toolbar.addAction(
            "− Zoom Out"
        )

        self.pdf_zoom_out_action.setToolTip(
            "Zoom out"
        )

        self.pdf_zoom_out_action.triggered.connect(
            self.pdf_zoom_out
        )

        self.pdf_zoom_label = QLabel(
            "Fit"
        )

        self.pdf_zoom_label.setMinimumWidth(
            65
        )

        self.pdf_zoom_label.setAlignment(
            Qt.AlignCenter
        )

        toolbar.addWidget(
            self.pdf_zoom_label
        )

        self.pdf_zoom_in_action = toolbar.addAction(
            "+ Zoom In"
        )

        self.pdf_zoom_in_action.setToolTip(
            "Zoom in"
        )

        self.pdf_zoom_in_action.triggered.connect(
            self.pdf_zoom_in
        )

        self.pdf_zoom_reset_action = toolbar.addAction(
            "100%"
        )

        self.pdf_zoom_reset_action.setToolTip(
            "Reset to 100% zoom"
        )

        self.pdf_zoom_reset_action.triggered.connect(
            self.pdf_zoom_reset
        )

        toolbar.addSeparator()

        # -------------------------------------------------
        # Fit modes
        # -------------------------------------------------

        toolbar.addWidget(
            QLabel("View:")
        )

        self.pdf_zoom_combo = QComboBox()

        self.pdf_zoom_combo.addItem(
            "Fit Width",
            "width"
        )

        self.pdf_zoom_combo.addItem(
            "Fit Page",
            "page"
        )

        self.pdf_zoom_combo.addItem(
            "Custom",
            "custom"
        )

        self.pdf_zoom_combo.setToolTip(
            "PDF zoom mode"
        )

        self.pdf_zoom_combo.currentIndexChanged.connect(
            self.pdf_zoom_mode_selected
        )

        toolbar.addWidget(
            self.pdf_zoom_combo
        )

        toolbar.addSeparator()

        # -------------------------------------------------
        # Page layout
        # -------------------------------------------------

        self.pdf_single_page_action = QAction(
            "Single Page",
            self
        )

        self.pdf_single_page_action.setCheckable(
            True
        )

        self.pdf_single_page_action.triggered.connect(
            self.pdf_single_page
        )

        toolbar.addAction(
            self.pdf_single_page_action
        )

        self.pdf_continuous_action = QAction(
            "Continuous",
            self
        )

        self.pdf_continuous_action.setCheckable(
            True
        )

        self.pdf_continuous_action.setChecked(
            True
        )

        self.pdf_continuous_action.triggered.connect(
            self.pdf_continuous
        )

        toolbar.addAction(
            self.pdf_continuous_action
        )

        # -------------------------------------------------
        # Hide until a PDF is selected.
        # -------------------------------------------------

        toolbar.hide()


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

        if current is None:

            return

        path = current.data(
            0,
            Qt.UserRole
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

        if self.loading_file:

            return

        # -------------------------------------------------
        # Protect unsaved changes.
        # -------------------------------------------------

        if (
            self.current_file
            and self.current_file != path
            and self.viewer.document().isModified()
        ):

            if not self.maybe_save_changes():

                return

        self.loading_file = True

        try:

            self.reset_non_pdf_state()

            # -------------------------------------------------
            # Directory.
            # -------------------------------------------------

            if os.path.isdir(path):

                self.current_file = None

                self.viewer.setPlainText(
                    "Directory selected"
                )

                self.show_text_viewer()

                self.update_window_title()

                return

            # -------------------------------------------------
            # Invalid path.
            # -------------------------------------------------

            if not os.path.isfile(path):

                self.current_file = None

                self.viewer.setPlainText(
                    "Unable to open this item:\n\n"
                    f"{path}"
                )

                self.show_text_viewer()

                return

            self.current_file = path

            self.display_file(
                path
            )

        finally:

            self.loading_file = False


    # =====================================================
    # Reset non-PDF state
    # =====================================================

    def reset_non_pdf_state(self):

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

        self.viewer.clear()

        cursor = self.viewer.textCursor()

        cursor.clearSelection()

        self.viewer.setTextCursor(
            cursor
        )

        self.viewer.document().setModified(
            False
        )

        self.image_label.clear()

        self.image_label.setText(
            "No image selected"
        )

        self.pdf_toolbar.hide()


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

        # -------------------------------------------------
        # PDF.
        # -------------------------------------------------

        if extension in PDF_EXTENSIONS:

            self.display_pdf(
                path
            )

            return

        # -------------------------------------------------
        # Image.
        # -------------------------------------------------

        if extension in IMAGE_EXTENSIONS:

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

            self.display_rtf(
                path
            )

            return

        # -------------------------------------------------
        # Normal text.
        # -------------------------------------------------

        if extension in TEXT_EXTENSIONS:

            self.display_text(
                path
            )

            return

        # -------------------------------------------------
        # Unknown file type.
        # -------------------------------------------------

        self.viewer.setPlainText(
            "No preview available for this file type.\n\n"
            f"{path}"
        )

        self.viewer.document().setModified(
            False
        )

        self.update_window_title()


    # =====================================================
    # PDF display
    # =====================================================

    def display_pdf(
        self,
        path
    ):

        self.show_pdf_viewer()

        try:

            file_size = os.path.getsize(
                path
            )

        except OSError as error:

            self.pdf_view.hide()

            self.show_text_viewer()

            self.viewer.setPlainText(
                f"Could not access PDF:\n\n{error}"
            )

            return

        if file_size > MAX_PDF_FILE_SIZE:

            self.pdf_view.hide()

            self.show_text_viewer()

            self.viewer.setPlainText(
                "This PDF is larger than 250 MB "
                "and was not loaded."
            )

            return

        # -------------------------------------------------
        # Close previous PDF.
        # -------------------------------------------------

        self.pdf_document.close()

        # -------------------------------------------------
        # Load new PDF.
        #
        # QPdfDocument.load() returns an Error enum.
        # -------------------------------------------------

        error = self.pdf_document.load(
            path
        )

        if error != QPdfDocument.Error.None_:

            self.pdf_toolbar.hide()

            self.show_text_viewer()

            self.viewer.setPlainText(
                "Could not open PDF:\n\n"
                f"{self.pdf_error_text(error)}\n\n"
                f"{path}"
            )

            self.update_window_title()

            return

        # -------------------------------------------------
        # For normal local files the document should be
        # ready synchronously, but statusChanged handles
        # versions/platforms where loading is asynchronous.
        # -------------------------------------------------

        if (
            self.pdf_document.status()
            == QPdfDocument.Status.Ready
        ):

            self.pdf_document_ready()

        else:

            self.viewer.setPlainText(
                "Loading PDF..."
            )

        self.update_window_title()


    # =====================================================
    # PDF status
    # =====================================================

    def pdf_status_changed(
        self,
        status
    ):

        if (
            self.current_file is None
            or not self.current_file.lower().endswith(
                ".pdf"
            )
        ):

            return

        if status == QPdfDocument.Status.Ready:

            self.pdf_document_ready()

        elif status == QPdfDocument.Status.Error:

            error = self.pdf_document.error()

            self.pdf_toolbar.hide()

            self.show_text_viewer()

            self.viewer.setPlainText(
                "Could not open PDF:\n\n"
                f"{self.pdf_error_text(error)}\n\n"
                f"{self.current_file}"
            )


    # =====================================================
    # PDF ready
    # =====================================================

    def pdf_document_ready(self):

        if not self.current_file:

            return

        if not self.current_file.lower().endswith(
            ".pdf"
        ):

            return

        self.show_pdf_viewer()

        page_count = self.pdf_document.pageCount()

        self.pdf_page_spin.blockSignals(
            True
        )

        self.pdf_page_spin.setMinimum(
            1
        )

        self.pdf_page_spin.setMaximum(
            max(
                1,
                page_count
            )
        )

        self.pdf_page_spin.setValue(
            1
        )

        self.pdf_page_spin.blockSignals(
            True
        )

        self.pdf_page_spin.blockSignals(
            False
        )

        self.pdf_page_count_label.setText(
            f"of {page_count}"
        )

        # -------------------------------------------------
        # Reset navigator.
        # -------------------------------------------------

        navigator = self.pdf_view.pageNavigator()

        navigator.clear()

        if page_count > 0:

            navigator.jump(
                0,
                QPointF(),
                0
            )

        # -------------------------------------------------
        # Default PDF presentation.
        # -------------------------------------------------

        self.pdf_view.setPageMode(
            QPdfView.PageMode.MultiPage
        )

        self.pdf_view.setZoomMode(
            QPdfView.ZoomMode.FitToWidth
        )

        self.pdf_continuous_action.setChecked(
            True
        )

        self.pdf_single_page_action.setChecked(
            False
        )

        self.update_pdf_toolbar_state()


    # =====================================================
    # PDF error text
    # =====================================================

    def pdf_error_text(
        self,
        error
    ):

        mapping = {
            QPdfDocument.Error.None_:
                "No error.",
            QPdfDocument.Error.Unknown:
                "Unknown PDF error.",
            QPdfDocument.Error.DataNotYetAvailable:
                "PDF data is not yet available.",
            QPdfDocument.Error.FileNotFound:
                "The PDF file could not be found.",
            QPdfDocument.Error.InvalidFileFormat:
                "The file is not a valid PDF.",
            QPdfDocument.Error.IncorrectPassword:
                "The PDF password is incorrect.",
            QPdfDocument.Error.UnsupportedSecurityScheme:
                "This PDF uses an unsupported security scheme.",
        }

        return mapping.get(
            error,
            str(error)
        )


    # =====================================================
    # PDF toolbar visibility
    # =====================================================

    def update_pdf_toolbar_state(self):

        is_pdf = (
            self.current_file is not None
            and self.current_file.lower().endswith(
                ".pdf"
            )
            and self.pdf_document.status()
            == QPdfDocument.Status.Ready
        )

        self.pdf_toolbar.setVisible(
            is_pdf
        )

        if not is_pdf:

            return

        page_count = self.pdf_document.pageCount()

        current_page = (
            self.pdf_view
            .pageNavigator()
            .currentPage()
        )

        if current_page < 0:

            current_page = 0

        current_page = min(
            current_page,
            max(
                0,
                page_count - 1
            )
        )

        self.pdf_page_spin.blockSignals(
            True
        )

        self.pdf_page_spin.setMaximum(
            max(
                1,
                page_count
            )
        )

        self.pdf_page_spin.setValue(
            current_page + 1
        )

        self.pdf_page_spin.blockSignals(
            False
        )

        self.pdf_page_count_label.setText(
            f"of {page_count}"
        )

        self.pdf_first_action.setEnabled(
            current_page > 0
        )

        self.pdf_previous_action.setEnabled(
            current_page > 0
        )

        self.pdf_next_action.setEnabled(
            current_page < page_count - 1
        )

        self.pdf_last_action.setEnabled(
            current_page < page_count - 1
        )

        navigator = self.pdf_view.pageNavigator()

        self.pdf_back_action.setEnabled(
            navigator.backAvailable()
        )

        self.pdf_forward_action.setEnabled(
            navigator.forwardAvailable()
        )

        self.pdf_zoom_in_action.setEnabled(
            self.pdf_view.zoomMode()
            == QPdfView.ZoomMode.Custom
            and self.pdf_view.zoomFactor()
            < PDF_MAX_ZOOM
        )

        self.pdf_zoom_out_action.setEnabled(
            self.pdf_view.zoomMode()
            == QPdfView.ZoomMode.Custom
            and self.pdf_view.zoomFactor()
            > PDF_MIN_ZOOM
        )


    # =====================================================
    # PDF current page changed
    # =====================================================

    def pdf_current_page_changed(
        self,
        page
    ):

        if page < 0:

            return

        self.pdf_page_spin.blockSignals(
            True
        )

        self.pdf_page_spin.setValue(
            page + 1
        )

        self.pdf_page_spin.blockSignals(
            False
        )

        self.update_pdf_toolbar_state()


    # =====================================================
    # PDF navigation state
    # =====================================================

    def pdf_navigation_state_changed(
        self,
        available
    ):

        self.update_pdf_toolbar_state()


    # =====================================================
    # PDF zoom changed
    # =====================================================

    def pdf_zoom_changed(
        self,
        factor
    ):

        if (
            self.pdf_view.zoomMode()
            == QPdfView.ZoomMode.Custom
        ):

            self.pdf_zoom_label.setText(
                f"{factor * 100:.0f}%"
            )

        self.update_pdf_toolbar_state()


    # =====================================================
    # PDF zoom mode changed
    # =====================================================

    def pdf_zoom_mode_changed(
        self,
        mode
    ):

        if mode == QPdfView.ZoomMode.FitToWidth:

            self.pdf_zoom_label.setText(
                "Fit Width"
            )

            self.pdf_zoom_combo.blockSignals(
                True
            )

            self.pdf_zoom_combo.setCurrentIndex(
                0
            )

            self.pdf_zoom_combo.blockSignals(
                False
            )

        elif mode == QPdfView.ZoomMode.FitInView:

            self.pdf_zoom_label.setText(
                "Fit Page"
            )

            self.pdf_zoom_combo.blockSignals(
                True
            )

            self.pdf_zoom_combo.setCurrentIndex(
                1
            )

            self.pdf_zoom_combo.blockSignals(
                False
            )

        else:

            self.pdf_zoom_label.setText(
                f"{self.pdf_view.zoomFactor() * 100:.0f}%"
            )

            self.pdf_zoom_combo.blockSignals(
                True
            )

            self.pdf_zoom_combo.setCurrentIndex(
                2
            )

            self.pdf_zoom_combo.blockSignals(
                False
            )

        self.update_pdf_toolbar_state()


    # =====================================================
    # PDF page navigation
    # =====================================================

    def pdf_jump_to_page(
        self,
        page
    ):

        page_count = self.pdf_document.pageCount()

        if page_count <= 0:

            return

        page = max(
            0,
            min(
                page,
                page_count - 1
            )
        )

        navigator = self.pdf_view.pageNavigator()

        zoom = navigator.currentZoom()

        # -------------------------------------------------
        # QPdfPageNavigator does NOT have setCurrentPage().
        #
        # jump() is the supported way to navigate to a page.
        # -------------------------------------------------

        navigator.jump(
            page,
            QPointF(),
            zoom
        )


    # -----------------------------------------------------

    def pdf_first_page(self):

        self.pdf_jump_to_page(
            0
        )


    # -----------------------------------------------------

    def pdf_previous_page(self):

        current = (
            self.pdf_view
            .pageNavigator()
            .currentPage()
        )

        self.pdf_jump_to_page(
            current - 1
        )


    # -----------------------------------------------------

    def pdf_next_page(self):

        current = (
            self.pdf_view
            .pageNavigator()
            .currentPage()
        )

        self.pdf_jump_to_page(
            current + 1
        )


    # -----------------------------------------------------

    def pdf_last_page(self):

        self.pdf_jump_to_page(
            self.pdf_document.pageCount() - 1
        )


    # =====================================================
    # PDF page spin box
    # =====================================================

    def pdf_page_spin_changed(
        self,
        value
    ):

        self.pdf_jump_to_page(
            value - 1
        )


    # =====================================================
    # PDF navigation history
    # =====================================================

    def pdf_go_back(self):

        self.pdf_view.pageNavigator().back()


    # -----------------------------------------------------

    def pdf_go_forward(self):

        self.pdf_view.pageNavigator().forward()


    # =====================================================
    # PDF zoom
    # =====================================================

    def pdf_zoom_in(self):

        current = self.pdf_view.zoomFactor()

        if (
            self.pdf_view.zoomMode()
            != QPdfView.ZoomMode.Custom
        ):

            current = PDF_DEFAULT_ZOOM

        new_factor = min(
            PDF_MAX_ZOOM,
            current * PDF_ZOOM_STEP
        )

        self.pdf_view.setZoomMode(
            QPdfView.ZoomMode.Custom
        )

        self.pdf_view.setZoomFactor(
            new_factor
        )


    # -----------------------------------------------------

    def pdf_zoom_out(self):

        current = self.pdf_view.zoomFactor()

        if (
            self.pdf_view.zoomMode()
            != QPdfView.ZoomMode.Custom
        ):

            current = PDF_DEFAULT_ZOOM

        new_factor = max(
            PDF_MIN_ZOOM,
            current / PDF_ZOOM_STEP
        )

        self.pdf_view.setZoomMode(
            QPdfView.ZoomMode.Custom
        )

        self.pdf_view.setZoomFactor(
            new_factor
        )


    # -----------------------------------------------------

    def pdf_zoom_reset(self):

        self.pdf_view.setZoomMode(
            QPdfView.ZoomMode.Custom
        )

        self.pdf_view.setZoomFactor(
            PDF_DEFAULT_ZOOM
        )


    # =====================================================
    # PDF zoom modes
    # =====================================================

    def pdf_fit_width(self):

        self.pdf_view.setZoomMode(
            QPdfView.ZoomMode.FitToWidth
        )


    # -----------------------------------------------------

    def pdf_fit_page(self):

        self.pdf_view.setZoomMode(
            QPdfView.ZoomMode.FitInView
        )


    # -----------------------------------------------------

    def pdf_zoom_mode_selected(
        self,
        index
    ):

        mode = self.pdf_zoom_combo.itemData(
            index
        )

        if mode == "width":

            self.pdf_fit_width()

        elif mode == "page":

            self.pdf_fit_page()

        elif mode == "custom":

            self.pdf_view.setZoomMode(
                QPdfView.ZoomMode.Custom
            )


    # =====================================================
    # PDF page modes
    # =====================================================

    def pdf_single_page(self):

        self.pdf_view.setPageMode(
            QPdfView.PageMode.SinglePage
        )

        self.pdf_single_page_action.setChecked(
            True
        )

        self.pdf_continuous_action.setChecked(
            False
        )


    # -----------------------------------------------------

    def pdf_continuous(self):

        self.pdf_view.setPageMode(
            QPdfView.PageMode.MultiPage
        )

        self.pdf_single_page_action.setChecked(
            False
        )

        self.pdf_continuous_action.setChecked(
            True
        )


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

            try:

                with open(
                    path,
                    "r",
                    encoding="utf-8"
                ) as file:

                    contents = file.read()

            except UnicodeDecodeError:

                with open(
                    path,
                    "r",
                    encoding="cp1252"
                ) as file:

                    contents = file.read()

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

        if extension == ".rtf":

            return self.save_rtf(
                self.current_file
            )

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

            self.current_file = path

            self.viewer.document().setModified(
                False
            )

            self.update_window_title()

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

        entries = [
            entry
            for entry in entries
            if not entry.name.startswith(".")
        ]

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

        self.pdf_view.hide()

        self.image_scroll.hide()

        self.viewer.show()

        self.pdf_toolbar.hide()


    # -----------------------------------------------------

    def show_image_viewer(self):

        self.pdf_view.hide()

        self.viewer.hide()

        self.image_scroll.show()

        self.pdf_toolbar.hide()


    # -----------------------------------------------------

    def show_pdf_viewer(self):

        self.viewer.hide()

        self.image_scroll.hide()

        self.pdf_view.show()

        self.pdf_toolbar.show()


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

        self.pdf_document.close()

        self.pdf_toolbar.hide()

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

            self.pdf_document.close()

            event.accept()

        else:

            event.ignore()


# =========================================================
# Application entry point
# =========================================================


def main():

    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "Browse and preview files in a directory."
        )
    )

    parser.add_argument(
        "directory",
        nargs="?",
        help=(
            "Directory to open when the viewer starts "
            "(optional)."
        ),
    )

    args, qt_args = parser.parse_known_args(
        sys.argv[1:]
    )

    directory = None

    if args.directory:

        directory = os.path.abspath(
            os.path.expanduser(
                args.directory
            )
        )

        if not os.path.isdir(
            directory
        ):

            parser.error(
                f"not a directory: {args.directory}"
            )

    app = QApplication(
        [
            sys.argv[0],
            *qt_args,
        ]
    )

    app.setApplicationName(
        "File Viewer"
    )

    window = FileViewer()

    if directory:

        window.load_directory(
            directory
        )

    window.show()

    sys.exit(
        app.exec()
    )


if __name__ == "__main__":

    main()

