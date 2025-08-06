
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton
from PyQt6.QtCore import pyqtSignal

class SearchBar(QWidget):
    filter_changed = pyqtSignal()
    content_search_triggered = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        self.setLayout(layout)

        # Main search bar for file/folder names
        search_layout = QHBoxLayout()
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("ファイル名またはフォルダ名でフィルタリング...")
        self.search_bar.textChanged.connect(self.filter_changed.emit)
        search_layout.addWidget(self.search_bar)

        self.clear_search_button = QPushButton("X")
        self.clear_search_button.setObjectName("clear_search_button")
        self.clear_search_button.setFixedSize(24, 24)
        self.clear_search_button.clicked.connect(self.clear_all_filters)
        search_layout.addWidget(self.clear_search_button)
        layout.addLayout(search_layout)

        # Content search bar
        self.content_search_bar = QLineEdit()
        self.content_search_bar.setPlaceholderText("表示中のファイル内をテキスト検索 (Enterで実行)")
        self.content_search_bar.returnPressed.connect(self.on_content_search)
        layout.addWidget(self.content_search_bar)

    def on_content_search(self):
        self.content_search_triggered.emit(self.content_search_bar.text())

    def get_filter_pattern(self):
        return self.search_bar.text()

    def clear_all_filters(self):
        self.search_bar.clear()
        self.content_search_bar.clear()
        self.filter_changed.emit()
