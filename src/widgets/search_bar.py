
from __future__ import annotations

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton
from PyQt6.QtCore import pyqtSignal

class SearchBar(QWidget):
    filter_changed = pyqtSignal()
    content_search_triggered = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.init_ui()

    def init_ui(self) -> None:
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        self.setLayout(layout)

        # Main search bar for file/folder names
        search_layout = QHBoxLayout()
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("ファイル名/フォルダ名を入力して Enter で検索（正規表現可）")
        # フィルタは Enter で発火させる
        self.search_bar.returnPressed.connect(self.on_filter_enter)
        search_layout.addWidget(self.search_bar)

        self.clear_search_button = QPushButton("X")
        self.clear_search_button.setObjectName("clear_search_button")
        self.clear_search_button.setFixedSize(24, 24)
        self.clear_search_button.clicked.connect(self.clear_all_filters)
        search_layout.addWidget(self.clear_search_button)
        layout.addLayout(search_layout)

        # Content search bar
        self.content_search_bar = QLineEdit()
        self.content_search_bar.setPlaceholderText("表示中のファイル内をテキスト検索（Enterで実行）")
        self.content_search_bar.returnPressed.connect(self.on_content_search)
        layout.addWidget(self.content_search_bar)

    def on_filter_enter(self) -> None:
        self.filter_changed.emit()

    def on_content_search(self) -> None:
        self.content_search_triggered.emit(self.content_search_bar.text())

    def get_filter_pattern(self) -> str:
        return self.search_bar.text()

    def clear_all_filters(self) -> None:
        self.search_bar.clear()
        self.content_search_bar.clear()
        self.filter_changed.emit()
