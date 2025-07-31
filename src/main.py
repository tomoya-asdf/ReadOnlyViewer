# main.py
import sys, os, re, shutil, tempfile, getpass, fitz
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTreeView, QTextEdit,
    QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox, QLabel, QPushButton, QStatusBar, QStackedLayout, QSplitter
)
from PyQt6.QtCore import Qt, QDir, QTimer, QSortFilterProxyModel
from PyQt6.QtGui import QFileSystemModel, QPixmap, QImage, QTextCharFormat
from viewer_utils import extract_text_preview, render_pdf_as_pixmaps

class FileViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("読み取り専用 ファイルビューア")
        self.setGeometry(100, 100, 1400, 800)
        self.username = getpass.getuser()

        # Load QSS
        try:
            with open('style.qss', 'r') as f:
                self.setStyleSheet(f.read())
        except FileNotFoundError:
            print("style.qss not found. Skipping style loading.")

        self.model = QFileSystemModel()
        self.model.setRootPath(QDir.rootPath())
        self.model.setFilter(QDir.Filter.AllDirs | QDir.Filter.AllEntries | QDir.Filter.NoDotAndDotDot)

        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.proxy_model.setRecursiveFilteringEnabled(True) # Enable recursive filtering

        self.tree = QTreeView()
        self.tree.setModel(self.proxy_model)
        self.tree.setColumnWidth(0, 300)
        self.tree.setRootIndex(self.proxy_model.mapFromSource(self.model.index(QDir.homePath())))
        self.tree.doubleClicked.connect(self.on_item_double_clicked)
        self.tree.setHeaderHidden(True) # Hide headers for a cleaner look
        self.tree.setIndentation(15) # Adjust indentation for better visual hierarchy

        self.preview = QTextEdit()
        self.preview.setReadOnly(True)

        self.pdf_preview = QLabel()
        self.pdf_preview.setObjectName("pdf_preview") # Add object name for QSS
        self.pdf_preview.setAlignment(Qt.AlignmentFlag.AlignCenter) # Center the image
        self.pdf_preview.setScaledContents(False) # Don't scale contents directly, handle scaling manually
        self.pdf_preview.hide()

        # PDF Navigation
        self.current_pdf_path = None
        self.current_pdf_page = 0
        self.total_pdf_pages = 0

        self.pdf_prev_button = QPushButton("◀ 前のページ")
        self.pdf_prev_button.clicked.connect(self.show_prev_pdf_page)
        self.pdf_prev_button.hide()

        self.pdf_next_button = QPushButton("次のページ ▶")
        self.pdf_next_button.clicked.connect(self.show_next_pdf_page)
        self.pdf_next_button.hide()

        self.pdf_page_label = QLabel("ページ: 0/0")
        self.pdf_page_label.hide()

        pdf_nav_layout = QHBoxLayout()
        pdf_nav_layout.addWidget(self.pdf_prev_button)
        pdf_nav_layout.addWidget(self.pdf_page_label)
        pdf_nav_layout.addWidget(self.pdf_next_button)
        pdf_nav_layout.addStretch() # Push buttons to the left

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("ファイル名またはフォルダ名、正規表現...")
        self.search_bar.textChanged.connect(self.apply_filter)

        self.clear_search_button = QPushButton("X")
        self.clear_search_button.setFixedSize(24, 24) # Smaller size for clear button
        self.clear_search_button.clicked.connect(self.search_bar.clear)

        search_bar_layout = QHBoxLayout()
        search_bar_layout.addWidget(self.search_bar)
        search_bar_layout.setContentsMargins(0, 0, 0, 0)

        self.filter_box = QComboBox()
        self.filter_box.addItems(["すべて", ".pdf", ".docx", ".xlsx", ".pptx", ".txt", ".csv", ".md"])
        self.filter_box.currentIndexChanged.connect(self.apply_filter)

        self.back_button = QPushButton("⬅")
        self.back_button.clicked.connect(self.go_to_parent_directory)
        self.back_button.setShortcut("Alt+Left")
        
        self.regex_search_bar = QLineEdit()
        self.regex_search_bar.setPlaceholderText("プレビュー内検索 (Enterで実行)")
        self.regex_search_bar.returnPressed.connect(self.perform_content_search)

        self.search_results = []
        self.current_search_index = -1

        self.prev_match_button = QPushButton("▲")
        self.prev_match_button.setFixedSize(24, 24)
        self.prev_match_button.clicked.connect(self.find_prev_match)
        self.prev_match_button.hide()

        self.next_match_button = QPushButton("▼")
        self.next_match_button.setFixedSize(24, 24)
        self.next_match_button.clicked.connect(self.find_next_match)
        self.next_match_button.hide()

        search_controls_layout = QHBoxLayout()
        search_controls_layout.addWidget(self.regex_search_bar)
        search_controls_layout.addWidget(self.prev_match_button)
        search_controls_layout.addWidget(self.next_match_button)

        top_controls = QHBoxLayout()
        top_controls.setContentsMargins(0, 0, 0, 0) # Remove margins for a tighter look
        top_controls.addWidget(self.filter_box)
        top_controls.addWidget(self.clear_search_button)

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10) # Add some padding around the main layout
        layout.addWidget(self.back_button)
        layout.addLayout(top_controls)
        layout.addLayout(search_controls_layout)

        self.preview_stack = QStackedLayout()
        self.preview_stack.addWidget(self.preview)
        self.preview_stack.addWidget(self.pdf_preview)

        right_panel_layout = QVBoxLayout()
        right_panel_layout.addLayout(self.preview_stack)
        right_panel_layout.addLayout(pdf_nav_layout)

        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.addWidget(self.tree)

        right_panel_widget = QWidget()
        right_panel_widget.setLayout(right_panel_layout)
        main_splitter.addWidget(right_panel_widget)

        main_splitter.setSizes([400, 1000]) # Initial sizes for tree and right panel

        layout.addWidget(main_splitter)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)

        # Temporary file cleanup on exit
        self.temp_files = []
        QApplication.instance().aboutToQuit.connect(self.cleanup_temp_files)

    def cleanup_temp_files(self):
        for f in self.temp_files:
            try:
                os.remove(f)
            except OSError as e:
                print(f"Error removing temporary file {f}: {e}")

    def apply_filter(self):
        text = self.search_bar.text()
        ext = self.filter_box.currentText()

        # Combine text and extension filters
        filter_pattern = ""
        if text:
            filter_pattern += text
        if ext != "すべて":
            # Escape special regex characters in extension
            escaped_ext = re.escape(ext)
            # Ensure the pattern matches the end of the filename
            if filter_pattern:
                filter_pattern += ".*" + escaped_ext + "$"
            else:
                filter_pattern += ".*" + escaped_ext + "$"

        self.proxy_model.setFilterRegularExpression(filter_pattern)

    def on_item_double_clicked(self, index):
        # Clear search results and hide buttons when a new file is opened
        self.search_results = []
        self.current_search_index = -1
        self.prev_match_button.hide()
        self.next_match_button.hide()
        self.regex_search_bar.clear()

        # Clear previous highlights from the preview
        format = QTextCharFormat()
        format.setBackground(self.preview.palette().base().color()) # Reset to default background
        cursor = self.preview.textCursor()
        cursor.setPosition(0)
        cursor.movePosition(cursor.End, cursor.KeepAnchor)
        cursor.mergeCharFormat(format)

        source_index = self.proxy_model.mapToSource(index)
        file_path = self.model.filePath(source_index)
        if os.path.isfile(file_path):
            temp_path = self.copy_to_temp_readonly(file_path)
            ext = os.path.splitext(temp_path)[1].lower()
            if ext == ".pdf":
                self.current_pdf_path = temp_path
                self.current_pdf_page = 0
                self.show_pdf(temp_path, self.current_pdf_page)
                self.preview_stack.setCurrentWidget(self.pdf_preview) # Show PDF preview
            else:
                self.current_pdf_path = None # Clear PDF state
                self.pdf_prev_button.hide()
                self.pdf_next_button.hide()
                self.pdf_page_label.hide()

                text = extract_text_preview(temp_path)
                self.preview.setText(text)
                self.preview_stack.setCurrentWidget(self.preview) # Show text preview

        else:
            self.tree.setRootIndex(index) # Navigate in proxy model

    def show_pdf(self, path, page_num):
        # Clear search results and hide buttons when a PDF is opened
        self.search_results = []
        self.current_search_index = -1
        self.prev_match_button.hide()
        self.next_match_button.hide()
        self.regex_search_bar.clear()

        images = render_pdf_as_pixmaps(path)
        if not images:
            self.preview.setText("PDF プレビューエラー")
            self.preview_stack.setCurrentWidget(self.preview) # Show text preview
            self.pdf_prev_button.hide()
            self.pdf_next_button.hide()
            self.pdf_page_label.hide()
            return

        self.total_pdf_pages = len(images)
        if not (0 <= page_num < self.total_pdf_pages):
            page_num = 0 # Reset to first page if out of bounds

        self.current_pdf_page = page_num
        self.pdf_page_label.setText(f"ページ: {self.current_pdf_page + 1}/{self.total_pdf_pages}")

        img = QImage(images[page_num].samples, images[page_num].width, images[page_num].height, images[page_num].stride, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(img)

        if pixmap.isNull():
            self.preview.setText("PDF プレビューエラー: 画像の読み込みに失敗しました")
            self.preview_stack.setCurrentWidget(self.preview) # Show text preview
            self.pdf_prev_button.hide()
            self.pdf_next_button.hide()
            self.pdf_page_label.hide()
            return

        # Scale pixmap to fit the QLabel while maintaining aspect ratio
        if not pixmap.isNull():
            scaled_pixmap = pixmap.scaled(self.pdf_preview.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.pdf_preview.setPixmap(scaled_pixmap)
            self.preview_stack.setCurrentWidget(self.pdf_preview) # Show PDF preview

            # Show PDF navigation buttons
            self.pdf_prev_button.show()
            self.pdf_next_button.show()
            self.pdf_page_label.show()

    def show_prev_pdf_page(self):
        if self.current_pdf_path and self.current_pdf_page > 0:
            self.current_pdf_page -= 1
            self.show_pdf(self.current_pdf_path, self.current_pdf_page)

    def show_next_pdf_page(self):
        if self.current_pdf_path and self.current_pdf_page < self.total_pdf_pages - 1:
            self.current_pdf_page += 1
            self.show_pdf(self.current_pdf_path, self.current_pdf_page)

    def copy_to_temp_readonly(self, path):
        # Create a temporary file with a unique name in the system's temporary directory
        # delete=False ensures the file is not deleted immediately after closing,
        # allowing it to be read by other processes.
        # mode='w+b' for binary write/read, as files like PDFs need binary mode.
        with tempfile.NamedTemporaryFile(delete=False, mode='w+b', suffix=os.path.splitext(path)[1]) as tmp_file:
            with open(path, 'rb') as src_file:
                shutil.copyfileobj(src_file, tmp_file)
        
        self.temp_files.append(tmp_file.name) # Add to list for cleanup
        return tmp_file.name

    def go_to_parent_directory(self):
        current_index = self.tree.rootIndex()
        source_index = self.proxy_model.mapToSource(current_index)
        parent_source_index = source_index.parent()
        if parent_source_index.isValid():
            self.tree.setRootIndex(self.proxy_model.mapFromSource(parent_source_index))

    def perform_content_search(self):
        keyword = self.regex_search_bar.text()
        if not keyword:
            self.statusBar.showMessage("検索キーワードを入力してください。", 2000)
            self.prev_match_button.hide()
            self.next_match_button.hide()
            return

        # Clear previous highlights
        format = QTextCharFormat()
        format.setBackground(self.preview.palette().base().color()) # Reset to default background
        cursor = self.preview.textCursor()
        cursor.setPosition(0)
        cursor.movePosition(cursor.End, cursor.KeepAnchor)
        cursor.mergeCharFormat(format)

        self.search_results = []
        self.current_search_index = -1

        document = self.preview.document()
        cursor = self.preview.textCursor()
        
        # Use QTextDocument.find for searching
        # Reset cursor to the beginning for a new search
        cursor.setPosition(0)
        self.preview.setTextCursor(cursor)

        # Find all occurrences
        while True:
            cursor = self.preview.document().find(keyword, cursor)
            if not cursor.isNull():
                self.search_results.append(cursor.position())
            else:
                break
        
        if self.search_results:
            self.current_search_index = 0
            self._highlight_current_match()
            self.statusBar.showMessage(f"'{keyword}' の検索が完了しました。{len(self.search_results)} 件見つかりました。", 5000)
            self.prev_match_button.show()
            self.next_match_button.show()
        else:
            self.statusBar.showMessage(f"'{keyword}' に一致する箇所は見つかりませんでした。", 5000)
            self.prev_match_button.hide()
            self.next_match_button.hide()

    def _highlight_current_match(self):
        if not self.search_results:
            return

        # Clear previous highlight
        format = QTextCharFormat()
        format.setBackground(self.preview.palette().base().color()) # Reset to default background
        cursor = self.preview.textCursor()
        cursor.setPosition(0)
        cursor.movePosition(cursor.End, cursor.KeepAnchor)
        cursor.mergeCharFormat(format)

        # Highlight current match
        highlight_format = QTextCharFormat()
        highlight_format.setBackground(Qt.GlobalColor.yellow)
        
        cursor = self.preview.textCursor()
        cursor.setPosition(self.search_results[self.current_search_index])
        cursor.movePosition(cursor.EndOfWord, cursor.KeepAnchor) # Select the word
        cursor.mergeCharFormat(highlight_format)
        self.preview.setTextCursor(cursor) # Move cursor to the highlighted text
        
        # Ensure the highlighted text is visible
        self.preview.ensureCursorVisible()

    def find_prev_match(self):
        if not self.search_results:
            return
        
        self.current_search_index -= 1
        if self.current_search_index < 0:
            self.current_search_index = len(self.search_results) - 1 # Wrap around
        
        self._highlight_current_match()

    def find_next_match(self):
        if not self.search_results:
            return
        
        self.current_search_index += 1
        if self.current_search_index >= len(self.search_results):
            self.current_search_index = 0 # Wrap around
        
        self._highlight_current_match()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = FileViewer()
    viewer.show()
    sys.exit(app.exec())
