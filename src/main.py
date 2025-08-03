# main.py
import sys, os, re, shutil, tempfile, getpass, fitz
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTreeView, QTextEdit,
    QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox, QLabel, QPushButton, QStatusBar, QStackedLayout, QSplitter,
    QFileDialog
)
from PyQt6.QtCore import Qt, QDir, QTimer, QSortFilterProxyModel
from PyQt6.QtGui import QFileSystemModel, QPixmap, QImage, QTextCharFormat, QTextCursor, QShortcut, QKeySequence
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

        # --- 1. 最初に開くフォルダを選択 ---
        self.initial_dir = self.select_initial_directory()
        if not self.initial_dir:
            sys.exit() # Exit if no directory is selected

        self.model = QFileSystemModel()
        self.model.setRootPath(QDir.rootPath())
        self.model.setFilter(QDir.Filter.AllDirs | QDir.Filter.AllEntries | QDir.Filter.NoDotAndDotDot)

        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.proxy_model.setRecursiveFilteringEnabled(True)

        self.tree = QTreeView()
        self.tree.setModel(self.proxy_model)
        self.tree.setColumnWidth(0, 300)
        self.tree.setRootIndex(self.proxy_model.mapFromSource(self.model.index(self.initial_dir)))
        self.tree.doubleClicked.connect(self.on_item_double_clicked)
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(15)

        # --- 2. パスバーの機能拡張 ---
        self.path_bar = QLineEdit()
        self.path_bar.setReadOnly(False) # Allow editing
        self.path_bar.returnPressed.connect(self.on_path_entered) # Handle Enter key press
        self.path_bar.setText(self.model.filePath(self.proxy_model.mapToSource(self.tree.rootIndex())))

        shortcut = QShortcut(QKeySequence("Ctrl+L"), self)
        shortcut.activated.connect(self.path_bar.selectAll)

        self.back_button = QPushButton("⬅")
        self.back_button.clicked.connect(self.go_to_parent_directory)
        self.back_button.setShortcut("Alt+Left")

        path_layout = QHBoxLayout()
        path_layout.addWidget(self.back_button)
        path_layout.addWidget(self.path_bar)

        left_panel_layout = QVBoxLayout()
        left_panel_layout.addLayout(path_layout)
        left_panel_layout.addWidget(self.tree)

        left_panel_widget = QWidget()
        left_panel_widget.setLayout(left_panel_layout)

        self.preview = QTextEdit()
        self.preview.setReadOnly(True)

        self.pdf_preview = QLabel()
        self.pdf_preview.setObjectName("pdf_preview")
        self.pdf_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pdf_preview.setScaledContents(False)
        self.pdf_preview.hide()

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
        pdf_nav_layout.addStretch()

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("ファイル名またはフォルダ名、正規表現...")
        self.search_bar.textChanged.connect(self.apply_filter)

        self.content_search_bar = QLineEdit()
        self.content_search_bar.setPlaceholderText("フォルダ内ファイル内テキスト検索 (Enterで実行)")
        self.content_search_bar.returnPressed.connect(self.search_file_contents)

        # --- 3. UIレイアウト変更 ---
        self.filter_box = QComboBox()
        self.filter_box.addItems(["すべて", ".pdf", ".docx", ".xlsx", ".pptx", ".txt", ".csv", ".md"])
        self.filter_box.currentIndexChanged.connect(self.apply_filter)

        self.clear_search_button = QPushButton("X")
        self.clear_search_button.setFixedSize(24, 24)
        # --- 4. クリアボタンの機能拡張 ---
        self.clear_search_button.clicked.connect(self.clear_all_filters)

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(self.filter_box)
        filter_layout.addWidget(self.clear_search_button)
        filter_layout.setContentsMargins(0, 5, 0, 0) # Add some top margin

        search_layout = QVBoxLayout()
        search_layout.addWidget(self.search_bar) # Renamed from filename_search_bar for clarity
        search_layout.addWidget(self.content_search_bar)
        search_layout.addLayout(filter_layout) # Add the new filter layout here

        self.preview_stack = QStackedLayout()
        self.preview_stack.addWidget(self.preview)
        self.preview_stack.addWidget(self.pdf_preview)

        right_panel_layout = QVBoxLayout()
        right_panel_layout.addLayout(self.preview_stack)
        right_panel_layout.addLayout(pdf_nav_layout)

        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.addWidget(left_panel_widget)

        right_panel_widget = QWidget()
        right_panel_widget.setLayout(right_panel_layout)
        main_splitter.addWidget(right_panel_widget)

        main_splitter.setSizes([400, 1000])

        # Main layout setup
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.addLayout(search_layout) # Add search controls at the top
        layout.addWidget(main_splitter)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)

        self.temp_files = []
        QApplication.instance().aboutToQuit.connect(self.cleanup_temp_files)

    def select_initial_directory(self):
        # Use QFileDialog to let the user select a directory
        return QFileDialog.getExistingDirectory(
            self,
            "最初に開くフォルダを選択してください",
            QDir.homePath(), # Start at the user's home directory
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks
        )

    def on_path_entered(self):
        path = self.path_bar.text()
        if os.path.isdir(path):
            source_index = self.model.index(path)
            if source_index.isValid():
                proxy_index = self.proxy_model.mapFromSource(source_index)
                self.tree.setRootIndex(proxy_index)
                self.tree.scrollTo(proxy_index) # Ensure the view updates
            else:
                self.statusBar.showMessage("無効なフォルダパスです。", 3000)
        elif os.path.isfile(path):
            # To handle file opening, we need its QModelIndex
            dir_path = os.path.dirname(path)
            file_name = os.path.basename(path)
            
            # Set the tree root to the file's directory first
            source_dir_index = self.model.index(dir_path)
            if source_dir_index.isValid():
                proxy_dir_index = self.proxy_model.mapFromSource(source_dir_index)
                self.tree.setRootIndex(proxy_dir_index)

                # Now find the file's index within the current view
                # This is a simplified approach; a more robust solution might iterate
                for row in range(self.proxy_model.rowCount(proxy_dir_index)):
                    child_index = self.proxy_model.index(row, 0, proxy_dir_index)
                    if self.model.fileName(self.proxy_model.mapToSource(child_index)) == file_name:
                        self.on_item_double_clicked(child_index)
                        self.tree.setCurrentIndex(child_index) # Highlight the file
                        return
            self.statusBar.showMessage("ファイルが見つからないか、開けません。", 3000)
        else:
            self.statusBar.showMessage("入力されたパスは存在しないか、無効です。", 3000)

    def clear_all_filters(self):
        self.search_bar.clear()
        self.content_search_bar.clear()
        self.filter_box.setCurrentIndex(0) # Reset to "すべて"

        self.on_path_entered()
        self.apply_filter() # This will reset the main tree view filter

    def cleanup_temp_files(self):
        for f in self.temp_files:
            try:
                os.remove(f)
            except OSError as e:
                print(f"Error removing temporary file {f}: {e}")

    def apply_filter(self):
        text = self.search_bar.text()
        ext = self.filter_box.currentText()

        filter_pattern = ""
        if text:
            filter_pattern += text
        if ext != "すべて":
            escaped_ext = re.escape(ext)
            if filter_pattern:
                filter_pattern += ".*" + escaped_ext + "$"
            else:
                filter_pattern += ".*" + escaped_ext + "$"

        self.proxy_model.setFilterRegularExpression(filter_pattern)

    def on_item_double_clicked(self, index):
        format = QTextCharFormat()
        format.setBackground(self.preview.palette().base().color())
        cursor = self.preview.textCursor()
        cursor.setPosition(0)
        cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
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
                self.preview_stack.setCurrentWidget(self.pdf_preview)
            else:
                self.current_pdf_path = None
                self.pdf_prev_button.hide()
                self.pdf_next_button.hide()
                self.pdf_page_label.hide()

                text = extract_text_preview(temp_path)
                self.preview.setText(text)
                self.preview_stack.setCurrentWidget(self.preview)

        else:
            self.tree.setRootIndex(index)
            self.path_bar.setText(self.model.filePath(source_index))

    def show_pdf(self, path, page_num):
        images = render_pdf_as_pixmaps(path)
        if not images:
            self.preview.setText("PDF プレビューエラー")
            self.preview_stack.setCurrentWidget(self.preview)
            self.pdf_prev_button.hide()
            self.pdf_next_button.hide()
            self.pdf_page_label.hide()
            return

        self.total_pdf_pages = len(images)
        if not (0 <= page_num < self.total_pdf_pages):
            page_num = 0

        self.current_pdf_page = page_num
        self.pdf_page_label.setText(f"ページ: {self.current_pdf_page + 1}/{self.total_pdf_pages}")

        img = QImage(images[page_num].samples, images[page_num].width, images[page_num].height, images[page_num].stride, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(img)

        if pixmap.isNull():
            self.preview.setText("PDF プレビューエラー: 画像の読み込みに失敗しました")
            self.preview_stack.setCurrentWidget(self.preview)
            self.pdf_prev_button.hide()
            self.pdf_next_button.hide()
            self.pdf_page_label.hide()
            return

        if not pixmap.isNull():
            scaled_pixmap = pixmap.scaled(self.pdf_preview.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.pdf_preview.setPixmap(scaled_pixmap)
            self.preview_stack.setCurrentWidget(self.pdf_preview)

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
        with tempfile.NamedTemporaryFile(delete=False, mode='w+b', suffix=os.path.splitext(path)[1]) as tmp_file:
            with open(path, 'rb') as src_file:
                shutil.copyfileobj(src_file, tmp_file)
        
        self.temp_files.append(tmp_file.name)
        return tmp_file.name

    def go_to_parent_directory(self):
        keyword = self.content_search_bar.text()

        current_index = self.tree.rootIndex()
        source_index = self.proxy_model.mapToSource(current_index)
        parent_source_index = source_index.parent()
        if parent_source_index.isValid():
            parent_proxy_index = self.proxy_model.mapFromSource(parent_source_index)
            self.tree.setRootIndex(parent_proxy_index)
            self.path_bar.setText(self.model.filePath(parent_source_index))

        self.proxy_model.setFilterRegularExpression(keyword)

    def search_file_contents(self):
        self.preview.clear()
        self.preview.setText("")

        keyword = self.content_search_bar.text()
        if not keyword:
            self.statusBar.showMessage("検索キーワードを入力してください。", 2000)
            return

        current_dir_index = self.tree.rootIndex()
        source_index = self.proxy_model.mapToSource(current_dir_index)
        current_path = self.model.filePath(source_index)

        self.preview_stack.setCurrentWidget(self.preview)
        self.preview.setText(f"'{keyword}' を検索中...")
        self.statusBar.showMessage(f"'{keyword}' を検索中...", 5000)

        found_files = []
        for root, _, files in os.walk(current_path):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    text = extract_text_preview(file_path)
                    if keyword.lower() in text.lower():
                        found_files.append(file_path)
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")

        if found_files:
            self.preview.setText("検索結果:\n" + "\n".join(found_files))
            self.statusBar.showMessage(f"'{keyword}' が {len(found_files)} 件のファイルで見つかりました。", 5000)
        else:
            self.preview.setText("検索結果: 見つかりませんでした。")
            self.statusBar.showMessage(f"'{keyword}' に一致するファイルは見つかりませんでした。", 5000)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = FileViewer()
    # Don't show the main window if the user cancels the directory dialog
    if viewer.initial_dir:
        viewer.show()
        sys.exit(app.exec())