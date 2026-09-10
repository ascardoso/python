import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QScrollArea,
    QSplitter,
    QTextEdit,
    QToolBar,
    QTreeWidget,
    QTreeWidgetItem,
    QWidget,
    QVBoxLayout,
)


# File types that will be displayed as normal text.
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


# Image files that can be previewed.
IMAGE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".bmp",
    ".webp",
    ".svg",
}


# Files larger than this won't automatically be loaded.
MAX_TEXT_FILE_SIZE = 10 * 1024 * 1024       # 10 MB
MAX_RTF_FILE_SIZE = 20 * 1024 * 1024        # 20 MB
MAX_IMAGE_FILE_SIZE = 50 * 1024 * 1024      # 50 MB


class FileViewer(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("File Viewer")
        self.resize(1200, 750)
        self.setMinimumSize(800, 500)

        self.current_directory = None

        self.create_ui()

    # =====================================================
    # UI
    # =====================================================

    def create_ui(self):
        # -------------------------------------------------
        # Toolbar
        # -------------------------------------------------

        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        open_action = toolbar.addAction("Open Directory")
        open_action.triggered.connect(self.open_directory)

        toolbar.addSeparator()

        self.path_label = QLabel("No directory selected")
        self.path_label.setStyleSheet(
            "padding-left: 8px; color: #666;"
        )

        toolbar.addWidget(self.path_label)

        # -------------------------------------------------
        # File tree
        # -------------------------------------------------

        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Files")
        self.tree.setAnimated(True)
        self.tree.setUniformRowHeights(True)

        self.tree.itemClicked.connect(
            self.file_selected
        )

        # -------------------------------------------------
        # Text viewer
        # -------------------------------------------------

        self.viewer = QTextEdit()

        self.viewer.setReadOnly(True)
        self.viewer.setAcceptRichText(True)

        # Default source-code/text font.
        font = QFont("Consolas", 11)

        if not font.exactMatch():
            font = QFont("Courier New", 11)

        self.viewer.setFont(font)

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

        # Scroll area allows large images to be viewed.
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
            0, 0, 0, 0
        )

        viewer_layout.addWidget(
            self.viewer
        )

        viewer_layout.addWidget(
            self.image_scroll
        )

        # Start with the text viewer visible.
        self.image_scroll.hide()

        # -------------------------------------------------
        # Splitter
        # -------------------------------------------------

        splitter = QSplitter(Qt.Horizontal)

        splitter.addWidget(self.tree)
        splitter.addWidget(self.viewer_container)

        # Initial widths.
        splitter.setSizes([350, 850])

        self.setCentralWidget(splitter)

    # =====================================================
    # Viewer switching
    # =====================================================

    def show_text_viewer(self):
        self.image_scroll.hide()
        self.viewer.show()

    def show_image_viewer(self):
        self.viewer.hide()
        self.image_scroll.show()

    # =====================================================
    # Directory selection
    # =====================================================

    def open_directory(self):
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Directory"
        )

        if directory:
            self.load_directory(directory)

    # =====================================================
    # Load directory
    # =====================================================

    def load_directory(self, directory):
        self.current_directory = directory

        self.tree.clear()

        self.viewer.clear()

        self.image_label.clear()
        self.image_label.setText(
            "No image selected"
        )

        self.show_text_viewer()

        self.path_label.setText(directory)

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

        self.tree.addTopLevelItem(root_item)

        root_item.setExpanded(True)

        self.populate_directory(
            root_item,
            directory
        )

    # =====================================================
    # Populate directory tree
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

        # Directories first.
        # Then files alphabetically.
        entries.sort(
            key=lambda entry: (
                not entry.is_dir(),
                entry.name.lower()
            )
        )

        for entry in entries:

            # Ignore hidden files/directories.
            if entry.name.startswith("."):
                continue

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

            parent_item.addChild(item)

            if is_directory:
                self.populate_directory(
                    item,
                    entry.path
                )

    # =====================================================
    # Tree selection
    # =====================================================

    def file_selected(self, item, column):
        path = item.data(
            0,
            Qt.UserRole
        )

        if not path:
            return

        if os.path.isdir(path):
            self.viewer.clear()
            self.image_label.clear()
            self.image_label.setText(
                "Directory selected"
            )
            self.show_text_viewer()
            return

        self.display_file(path)

    # =====================================================
    # Display selected file
    # =====================================================

    def display_file(self, path):
        extension = os.path.splitext(
            path
        )[1].lower()

        # Image
        if extension in IMAGE_EXTENSIONS:
            self.display_image(path)
            return

        # Everything below this point uses the text viewer.
        self.show_text_viewer()
        self.viewer.clear()

        # RTF
        if extension == ".rtf":
            self.display_rtf(path)
            return

        # Normal text files
        if extension in TEXT_EXTENSIONS:
            self.display_text(path)
            return

        # Unknown file
        self.viewer.setPlainText(
            "No preview available for this file type.\n\n"
            f"{path}"
        )

    # =====================================================
    # Display image
    # =====================================================

    def display_image(self, path):
        self.show_image_viewer()

        try:
            file_size = os.path.getsize(path)

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

        pixmap = QPixmap(path)

        if pixmap.isNull():
            self.image_label.setText(
                "Could not load this image.\n\n"
                f"{path}"
            )
            return

        # Keep a copy of the original image.
        self.current_pixmap = pixmap

        # Scale the image to fit the available viewer area.
        self.update_image_preview()

    # =====================================================
    # Resize image preview
    # =====================================================

    def update_image_preview(self):
        if not hasattr(self, "current_pixmap"):
            return

        if self.current_pixmap.isNull():
            return

        available_size = (
            self.image_scroll.viewport().size()
        )

        scaled_pixmap = self.current_pixmap.scaled(
            available_size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        self.image_label.setPixmap(
            scaled_pixmap
        )

    # =====================================================
    # Handle window/image viewer resizing
    # =====================================================

    def resizeEvent(self, event):
        super().resizeEvent(event)

        if hasattr(self, "current_pixmap"):
            if self.image_scroll.isVisible():
                self.update_image_preview()

    # =====================================================
    # Display normal text file
    # =====================================================

    def display_text(self, path):
        try:
            file_size = os.path.getsize(path)

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

    def display_rtf(self, path):
        try:
            file_size = os.path.getsize(path)

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
            # Import striprtf only when needed.
            from striprtf.striprtf import rtf_to_text

        except ImportError:
            self.viewer.setPlainText(
                "The 'striprtf' package is not installed.\n\n"
                "Install it with:\n\n"
                "pip install striprtf"
            )
            return

        try:
            # RTF is generally ASCII-compatible, but using
            # replacement handling makes the viewer more
            # tolerant of unusual files.
            with open(
                path,
                "r",
                encoding="utf-8",
                errors="replace"
            ) as file:
                rtf_contents = file.read()

            # Convert RTF markup into readable text.
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
    app = QApplication(sys.argv)

    app.setApplicationName("File Viewer")

    window = FileViewer()
    window.show()

    sys.exit(
        app.exec()
    )


if __name__ == "__main__":
    main()

