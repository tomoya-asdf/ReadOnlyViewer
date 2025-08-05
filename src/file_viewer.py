
import sys, os, shutil, tempfile
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QSplitter, QFileDialog, QStatusBar
from PyQt6.QtCore import QDir, Qt

from widgets.file_tree_view import FileTreeView
from widgets.previewer import Previewer
from widgets.search_bar import SearchBar
from utils.file_operations import extract_text_preview

class FileViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("読み取り専用 ファイルビューア")
        self.setGeometry(100, 100, 1400, 800)
        self.temp_files = []

        try:
            with open('style.qss', 'r') as f:
                self.setStyleSheet(f.read())
        except FileNotFoundError:
            print("style.qss not found. Skipping style loading.")

        self.initial_dir = self.select_initial_directory()
        if not self.initial_dir:
            sys.exit()

        self.init_ui()

    def init_ui(self):
        self.search_bar = SearchBar()
        self.file_tree_view = FileTreeView(self.initial_dir)
        self.previewer = Previewer()

        self.search_bar.filter_changed.connect(self.apply_filter)
        self.search_bar.content_search_triggered.connect(self.search_file_contents)
        self.file_tree_view.file_double_clicked.connect(self.on_file_selected)

        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(5, 5, 5, 5)
        left_layout.addWidget(self.file_tree_view)
        left_panel.setLayout(left_layout)

        right_panel = QWidget()
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(5, 5, 5, 5)
        right_layout.addWidget(self.previewer)
        right_panel.setLayout(right_layout)

        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.setHandleWidth(10) # Make the handle easier to grab
        main_splitter.addWidget(left_panel)
        main_splitter.addWidget(right_panel)
        main_splitter.setSizes([400, 1000])

        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        main_layout.addWidget(self.search_bar)      # Fixed height
        main_layout.addWidget(main_splitter, 1) # Expands to fill vertical space

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)

    def select_initial_directory(self):
        return QFileDialog.getExistingDirectory(
            self,
            "最初に開くフォルダを選択してください",
            QDir.homePath(),
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks
        )

    def apply_filter(self):
        filter_pattern = self.search_bar.get_filter_pattern()
        self.file_tree_view.apply_filter(filter_pattern)

    def on_file_selected(self, file_path):
        self.previewer.clear_preview()
        temp_path = self.copy_to_temp_readonly(file_path)
        ext = os.path.splitext(temp_path)[1].lower()
        if ext == ".pdf":
            self.previewer.show_pdf_preview(temp_path)
        else:
            self.previewer.show_text_preview(temp_path)

    def search_file_contents(self, keyword):
        if not keyword:
            self.statusBar.showMessage("検索キーワードを入力してください。", 2000)
            return

        current_path = self.file_tree_view.get_current_directory()
        self.previewer.set_search_text(f"'{keyword}' を検索中...")
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
            self.previewer.set_search_text("検索結果:\n" + "\n".join(found_files))
            self.statusBar.showMessage(f"'{keyword}' が {len(found_files)} 件のファイルで見つかりました。", 5000)
        else:
            self.previewer.set_search_text("検索結果: 見つかりませんでした。")
            self.statusBar.showMessage(f"'{keyword}' に一致するファイルは見つかりませんでした。", 5000)

    def copy_to_temp_readonly(self, path):
        with tempfile.NamedTemporaryFile(delete=False, mode='w+b', suffix=os.path.splitext(path)[1]) as tmp_file:
            with open(path, 'rb') as src_file:
                shutil.copyfileobj(src_file, tmp_file)
        self.temp_files.append(tmp_file.name)
        return tmp_file.name

    def cleanup_temp_files(self):
        for f in self.temp_files:
            try:
                os.remove(f)
            except OSError as e:
                print(f"Error removing temporary file {f}: {e}")

    def closeEvent(self, event):
        self.cleanup_temp_files()
        event.accept()
