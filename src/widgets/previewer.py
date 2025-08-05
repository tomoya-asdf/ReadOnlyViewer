
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLabel, QPushButton, QStackedLayout
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QImage, QTextCharFormat, QTextCursor

from utils.file_operations import extract_text_preview, render_pdf_as_pixmaps

class Previewer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_pdf_path = None
        self.current_pdf_page = 0
        self.total_pdf_pages = 0
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)

        self.preview_stack = QStackedLayout()
        self.text_preview = QTextEdit()
        self.text_preview.setReadOnly(True)
        self.pdf_preview = QLabel()
        self.pdf_preview.setObjectName("pdf_preview")
        self.pdf_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pdf_preview.setScaledContents(False)

        self.preview_stack.addWidget(self.text_preview)
        self.preview_stack.addWidget(self.pdf_preview)

        layout.addLayout(self.preview_stack)

        pdf_nav_layout = QHBoxLayout()
        self.pdf_prev_button = QPushButton("◀ 前のページ")
        self.pdf_prev_button.setObjectName("pdf_prev_button")
        self.pdf_prev_button.clicked.connect(self.show_prev_pdf_page)
        self.pdf_next_button = QPushButton("次のページ ▶")
        self.pdf_next_button.setObjectName("pdf_next_button")
        self.pdf_next_button.clicked.connect(self.show_next_pdf_page)
        self.pdf_page_label = QLabel("ページ: 0/0")

        pdf_nav_layout.addWidget(self.pdf_prev_button)
        pdf_nav_layout.addWidget(self.pdf_page_label)
        pdf_nav_layout.addWidget(self.pdf_next_button)
        pdf_nav_layout.addStretch()
        layout.addLayout(pdf_nav_layout)

        self.hide_pdf_controls()

    def show_text_preview(self, temp_path):
        self.current_pdf_path = None
        self.hide_pdf_controls()
        text = extract_text_preview(temp_path)
        self.text_preview.setText(text)
        self.preview_stack.setCurrentWidget(self.text_preview)

    def show_pdf_preview(self, temp_path):
        self.current_pdf_path = temp_path
        self.current_pdf_page = 0
        self.display_pdf_page(self.current_pdf_page)
        self.preview_stack.setCurrentWidget(self.pdf_preview)

    def display_pdf_page(self, page_num):
        images = render_pdf_as_pixmaps(self.current_pdf_path)
        if not images:
            self.text_preview.setText("PDF プレビューエラー")
            self.preview_stack.setCurrentWidget(self.text_preview)
            self.hide_pdf_controls()
            return

        self.total_pdf_pages = len(images)
        if not (0 <= page_num < self.total_pdf_pages):
            page_num = 0

        self.current_pdf_page = page_num
        self.pdf_page_label.setText(f"ページ: {self.current_pdf_page + 1}/{self.total_pdf_pages}")

        img = QImage(images[page_num].samples, images[page_num].width, images[page_num].height, images[page_num].stride, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(img)

        if not pixmap.isNull():
            scaled_pixmap = pixmap.scaled(self.pdf_preview.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.pdf_preview.setPixmap(scaled_pixmap)
            self.show_pdf_controls()
        else:
            self.text_preview.setText("PDF プレビューエラー: 画像の読み込みに失敗しました")
            self.preview_stack.setCurrentWidget(self.text_preview)
            self.hide_pdf_controls()

    def show_prev_pdf_page(self):
        if self.current_pdf_path and self.current_pdf_page > 0:
            self.current_pdf_page -= 1
            self.display_pdf_page(self.current_pdf_page)

    def show_next_pdf_page(self):
        if self.current_pdf_path and self.current_pdf_page < self.total_pdf_pages - 1:
            self.current_pdf_page += 1
            self.display_pdf_page(self.current_pdf_page)

    def show_pdf_controls(self):
        self.pdf_prev_button.show()
        self.pdf_next_button.show()
        self.pdf_page_label.show()

    def hide_pdf_controls(self):
        self.pdf_prev_button.hide()
        self.pdf_next_button.hide()
        self.pdf_page_label.hide()

    def clear_preview(self):
        format = QTextCharFormat()
        format.setBackground(self.text_preview.palette().base().color())
        cursor = self.text_preview.textCursor()
        cursor.setPosition(0)
        cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
        cursor.mergeCharFormat(format)
        self.text_preview.clear()

    def set_search_text(self, text):
        self.preview_stack.setCurrentWidget(self.text_preview)
        self.text_preview.setText(text)
