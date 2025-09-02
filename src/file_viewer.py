import os
import shutil
import sys
import tempfile
from multiprocessing import cpu_count

from PyQt6.QtCore import QDir, QSettings, QThreadPool, Qt
from PyQt6.QtWidgets import QFileDialog, QMainWindow, QSplitter, QStatusBar, QVBoxLayout, QWidget

from utils.search_worker import get_cached_text_preview, search_file_worker
from utils.worker import Worker, WorkerSignals
from widgets.file_tree_view import FileTreeView
from widgets.previewer import Previewer
from widgets.search_bar import SearchBar


class FileViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("読み取り専用 ファイルビューア")
        self.temp_files: list[str] = []
        self.threadpool = QThreadPool()
        self.signals = WorkerSignals()
        self.process_pool = None

        # Load stylesheet relative to this file (works regardless of CWD)
        try:
            style_path = os.path.join(os.path.dirname(__file__), 'style.qss')
            with open(style_path, 'r', encoding='utf-8') as f:
                self.setStyleSheet(f.read())
        except FileNotFoundError:
            print("style.qss not found. Skipping style loading.")

        settings = QSettings()
        default_dir = settings.value("last_dir", QDir.homePath())
        self.initial_dir = self.select_initial_directory(default_dir)
        if not self.initial_dir:
            sys.exit()

        settings.setValue("last_dir", self.initial_dir)

        self.init_ui()
        self.load_settings()

    def init_ui(self):
        self.search_bar = SearchBar()
        self.file_tree_view = FileTreeView(self.initial_dir)
        self.previewer = Previewer()

        self.search_bar.filter_changed.connect(self.apply_filter)
        self.search_bar.content_search_triggered.connect(self.search_file_contents)
        self.file_tree_view.file_double_clicked.connect(self.on_file_selected)
        self.previewer.file_selected_from_search.connect(self.on_file_selected)

        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(self.file_tree_view)
        left_panel.setLayout(left_layout)

        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.addWidget(left_panel)
        self.main_splitter.addWidget(self.previewer)

        main_layout = QVBoxLayout()
        main_layout.setSpacing(5)
        main_layout.addWidget(self.search_bar)
        main_layout.addWidget(self.main_splitter, 1)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)

    def set_process_pool(self, pool):
        self.process_pool = pool

    def update_status(self, message):
        self.statusBar.showMessage(message)

    def select_initial_directory(self, default_dir):
        return QFileDialog.getExistingDirectory(
            self,
            "最初に開くフォルダを選択してください",
            default_dir,
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks,
        )

    def apply_filter(self):
        # When filter changes, clear the preview and any existing search results
        self.previewer.clear_preview(clear_keyword=True)
        filter_pattern = self.search_bar.get_filter_pattern()
        self.file_tree_view.apply_filter(filter_pattern)

    def on_file_selected(self, file_path):
        # When selecting a file from search results, don't clear the keyword
        is_from_search = (
            self.previewer.stack.currentWidget() == self.previewer.search_results_view
        )
        self.previewer.clear_preview(clear_keyword=not is_from_search)
        self.previewer.set_info_text(f"{os.path.basename(file_path)} を読み込み中...")

        # Pass the original file_path to the worker for context
        worker = Worker(self.generate_preview, file_path, signals=self.signals)
        worker.signals.result.connect(self.display_preview)
        worker.signals.error.connect(self.preview_error)
        self.threadpool.start(worker)

    def generate_preview(self, file_path):
        temp_path = self.copy_to_temp_readonly(file_path)
        ext = os.path.splitext(temp_path)[1].lower()
        if ext == ".pdf":
            return ("pdf", temp_path, file_path)
        else:
            text = get_cached_text_preview(temp_path)
            return ("text", text, file_path)

    def display_preview(self, result):
        preview_type, content, original_path = result
        if preview_type == "pdf":
            self.previewer.show_pdf_preview(content, original_path)
        else:
            self.previewer.show_text_preview(content, original_path)

    def preview_error(self, error_tuple):
        print(error_tuple)
        self.previewer.set_info_text("プレビューの生成中にエラーが発生しました。")

    def search_file_contents(self, keyword):
        if not keyword:
            self.statusBar.showMessage("検索キーワードを入力してください。", 2000)
            return
        if not self.process_pool:
            self.statusBar.showMessage("検索プロセスが準備できていません。", 3000)
            return

        self.previewer.search_keyword = keyword
        filtered_files = self.file_tree_view.get_filtered_file_list()
        if not filtered_files:
            self.previewer.set_info_text("検索対象のファイルがありません。")
            self.statusBar.showMessage("フィルタリングされたファイルがありません。", 3000)
            return

        self.previewer.set_info_text(
            f"'{keyword}' を {len(filtered_files)} 件のファイルから検索中..."
        )
        self.statusBar.showMessage(f"'{keyword}' を検索中...", 0)

        search_worker_thread = Worker(self._search_in_background, keyword, filtered_files)
        search_worker_thread.signals.result.connect(self.search_finished)
        search_worker_thread.signals.error.connect(self.search_error)
        self.threadpool.start(search_worker_thread)

    def _search_in_background(self, keyword, file_list):
        found_files = []
        tasks = [(file_path, keyword) for file_path in file_list]

        if not tasks:
            return ([], keyword)

        num_cpus = cpu_count()
        chunksize = max(1, len(tasks) // (num_cpus * 4))

        try:
            for file_path, found in self.process_pool.imap_unordered(
                search_file_worker, tasks, chunksize=chunksize
            ):
                if found:
                    found_files.append(file_path)
        except Exception as e:
            print(f"An error occurred during search: {e}")

        return (found_files, keyword)

    def search_finished(self, result):
        found_files, keyword = result
        self.previewer.display_search_results(found_files, keyword)
        if found_files:
            self.statusBar.showMessage(
                f"'{keyword}' が {len(found_files)} 件のファイルで見つかりました。",
                5000,
            )
        else:
            self.statusBar.showMessage(
                f"'{keyword}' に一致するファイルは見つかりませんでした。",
                5000,
            )

    def search_error(self, error_tuple):
        print(error_tuple)
        self.previewer.set_info_text("ファイル検索中にエラーが発生しました。")
        self.statusBar.showMessage("エラーが発生しました。", 5000)

    def copy_to_temp_readonly(self, path):
        with tempfile.NamedTemporaryFile(
            delete=False, mode='w+b', suffix=os.path.splitext(path)[1]
        ) as tmp_file:
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

    def load_settings(self):
        settings = QSettings()
        self.restoreGeometry(settings.value("geometry", self.saveGeometry()))
        self.main_splitter.restoreState(
            settings.value("splitter_state", self.main_splitter.saveState())
        )

    def save_settings(self):
        settings = QSettings()
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("splitter_state", self.main_splitter.saveState())
        settings.setValue("last_dir", self.file_tree_view.get_current_directory())

    def closeEvent(self, event):
        self.save_settings()
        self.cleanup_temp_files()
        if self.process_pool:
            self.process_pool.terminate()
            self.process_pool.join()
        event.accept()

