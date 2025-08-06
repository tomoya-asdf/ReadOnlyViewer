import sys, os, shutil, tempfile
from functools import lru_cache
from multiprocessing import Pool, cpu_count

from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QSplitter, QFileDialog, QStatusBar
from PyQt6.QtCore import QDir, Qt, QThreadPool

from widgets.file_tree_view import FileTreeView
from widgets.previewer import Previewer
from widgets.search_bar import SearchBar
from utils.worker import Worker, WorkerSignals
# Import the new search worker
from utils.search_worker import search_file_worker, get_cached_text_preview

class FileViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("読み取り専用 ファイルビューア")
        self.setGeometry(100, 100, 1400, 800)
        self.temp_files = []
        self.threadpool = QThreadPool()
        self.signals = WorkerSignals()
        # The process pool will be created under the __main__ guard
        self.process_pool = None

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
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(self.file_tree_view)
        left_panel.setLayout(left_layout)

        right_panel = QWidget()
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(self.previewer)
        right_panel.setLayout(right_layout)

        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.setHandleWidth(10)
        main_splitter.addWidget(left_panel)
        main_splitter.addWidget(right_panel)
        main_splitter.setSizes([400, 1000])

        main_layout = QVBoxLayout()
        main_layout.setSpacing(5)
        main_layout.addWidget(self.search_bar)
        main_layout.addWidget(main_splitter, 1)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)

    def set_process_pool(self, pool):
        self.process_pool = pool

    def update_status(self, message):
        self.statusBar.showMessage(message)

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
        self.previewer.set_search_text(f"{os.path.basename(file_path)} を読み込み中...")

        worker = Worker(self.generate_preview, file_path)
        worker.signals.result.connect(self.display_preview)
        worker.signals.error.connect(self.preview_error)
        self.threadpool.start(worker)

    def generate_preview(self, file_path):
        temp_path = self.copy_to_temp_readonly(file_path)
        ext = os.path.splitext(temp_path)[1].lower()
        if ext == ".pdf":
            return ("pdf", temp_path) # content is path
        else:
            text = get_cached_text_preview(temp_path)
            return ("text", text)

    def display_preview(self, result):
        preview_type, content = result
        if preview_type == "pdf":
            self.previewer.show_pdf_preview(content)
        else:
            self.previewer.show_text_preview(content)

    def preview_error(self, error_tuple):
        print(error_tuple)
        self.previewer.set_search_text("プレビューの生成中にエラーが発生しました。")

    def search_file_contents(self, keyword):
        if not keyword:
            self.statusBar.showMessage("検索キーワードを入力してください。", 2000)
            return
        if not self.process_pool:
            self.statusBar.showMessage("検索プロセスが準備できていません。", 3000)
            return

        current_path = self.file_tree_view.get_current_directory()
        self.previewer.set_search_text(f"'{keyword}' を検索中 (並列処理実行中)...")
        self.statusBar.showMessage(f"'{keyword}' を検索中...", 0)

        # Pass the signals object to the worker
        worker = Worker(self._search_in_background, keyword, current_path, signals=self.signals)
        worker.signals.result.connect(self.search_finished)
        worker.signals.error.connect(self.search_error)
        worker.signals.progress.connect(self.update_status)  # Connect progress signal
        self.threadpool.start(worker)

    def _search_in_background(self, keyword, current_path):
        found_files = []
        tasks = ((os.path.join(root, file), keyword) for root, _, files in os.walk(current_path) for file in files)

        num_cpus = cpu_count()
        try:
            # Avoid division by zero if the directory is empty or has very few files.
            num_files = sum(1 for _ in os.walk(current_path) for _ in _[2])
            chunksize = max(1, num_files // (num_cpus * 4)) if num_files > 0 else 1
        except OSError:
            chunksize = 1 # Fallback if os.listdir fails (e.g., permissions)

        try:
            for file_path, found in self.process_pool.imap_unordered(search_file_worker, tasks, chunksize=chunksize):
                # The worker now has its own signals instance passed from the main thread
                self.signals.progress.emit(f"検索中: {os.path.basename(file_path)}")
                if found:
                    found_files.append(file_path)
        except Exception as e:
            print(f"An error occurred during search: {e}")
            # It is better to emit an error signal to be handled by the main thread
            self.signals.error.emit(('Search Error', str(e), traceback.format_exc()))

        return found_files, keyword

    def search_finished(self, result):
        print("search finished")
        found_files, keyword = result
        if found_files:
            self.previewer.set_search_text("検索結果:\n" + "\n".join(found_files))
            self.statusBar.showMessage(f"'{keyword}' が {len(found_files)} 件のファイルで見つかりました。", 5000)
        else:
            self.previewer.set_search_text("検索結果: 見つかりませんでした。")
            self.statusBar.showMessage(f"'{keyword}' に一致するファイルは見つかりませんでした。", 5000)

    def search_error(self, error_tuple):
        print(error_tuple)
        self.previewer.set_search_text("ファイル検索中にエラーが発生しました。")
        self.statusBar.showMessage("エラーが発生しました。", 5000)

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
        if self.process_pool:
            self.process_pool.terminate()
            self.process_pool.join() # Wait for the terminated processes to be cleaned up
        event.accept()
