
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox, QPushButton
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
        layout.setSpacing(5) # Add this line to reduce vertical spacing
        self.setLayout(layout)

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("ファイル名またはフォルダ名、正規表現...")
        self.search_bar.textChanged.connect(self.filter_changed.emit)
        layout.addWidget(self.search_bar)

        self.content_search_bar = QLineEdit()
        self.content_search_bar.setPlaceholderText("フォルダ内ファイル内テキスト検索 (Enterで実行)")
        self.content_search_bar.returnPressed.connect(self.on_content_search)
        layout.addWidget(self.content_search_bar)

        filter_layout = QHBoxLayout()
        self.filter_box = QComboBox()
        self.filter_box.addItems(["すべて", ".pdf", ".docx", ".xlsx", ".pptx", ".txt", ".csv", ".md"])
        self.filter_box.currentIndexChanged.connect(self.filter_changed.emit)
        filter_layout.addWidget(self.filter_box)

        self.clear_search_button = QPushButton("X")
        self.clear_search_button.setObjectName("clear_search_button")
        self.clear_search_button.setFixedSize(24, 24)
        self.clear_search_button.clicked.connect(self.clear_all_filters)
        filter_layout.addWidget(self.clear_search_button)
        
        layout.addLayout(filter_layout)

    def on_content_search(self):
        self.content_search_triggered.emit(self.content_search_bar.text())

    def get_filter_pattern(self):
        text = self.search_bar.text()
        ext = self.filter_box.currentText()
        
        filter_pattern = ""
        if text:
            filter_pattern += text
        if ext != "すべて":
            import re
            escaped_ext = re.escape(ext)
            if filter_pattern:
                filter_pattern += ".*" + escaped_ext + "$"
            else:
                filter_pattern += ".*" + escaped_ext + "$"
        return filter_pattern

    def clear_all_filters(self):
        self.search_bar.clear()
        self.content_search_bar.clear()
        self.filter_box.setCurrentIndex(0)
        self.filter_changed.emit()
