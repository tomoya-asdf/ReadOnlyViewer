
import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLabel, 
                             QPushButton, QStackedWidget, QListWidget, QListWidgetItem, QMenu, QApplication)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QImage, QTextCharFormat, QTextCursor, QColor, QTextDocument

from utils.file_operations import render_pdf_as_pixmaps

class Previewer(QWidget):
    file_selected_from_search = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_pdf_path = None
        self.current_pdf_page = 0
        self.total_pdf_pages = 0
        self.search_keyword = ""
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(main_layout)

        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack)

        # --- View 0: Initial/Info View ---
        self.info_view = QTextEdit()
        self.info_view.setReadOnly(True)
        self.info_view.setPlaceholderText("ファイルを選択してプレビューを表示するか、検索を実行してください。")
        self.stack.addWidget(self.info_view)

        # --- View 1: Search Results View ---
        self.search_results_view = QWidget()
        results_layout = QVBoxLayout()
        self.search_results_list = QListWidget()
        self.search_results_list.itemDoubleClicked.connect(self.on_search_result_selected)
        # Add context menu for copying path
        self.search_results_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.search_results_list.customContextMenuRequested.connect(self.show_search_result_context_menu)
        results_layout.addWidget(self.search_results_list)
        self.search_results_view.setLayout(results_layout)
        self.stack.addWidget(self.search_results_view)

        # --- View 2: File Preview View ---
        self.preview_view = QWidget()
        preview_layout = QVBoxLayout()
        preview_layout.setContentsMargins(5, 5, 5, 5)
        
        # Top bar with back button and file path
        top_bar_layout = QHBoxLayout()
        self.back_button = QPushButton("⬅ 検索結果に戻る")
        self.back_button.clicked.connect(self.show_search_results)
        self.current_file_label = QLabel("ファイルパス:")
        self.current_file_label.setWordWrap(True)
        top_bar_layout.addWidget(self.back_button)
        top_bar_layout.addSpacing(10)
        top_bar_layout.addWidget(self.current_file_label)
        top_bar_layout.addStretch()
        preview_layout.addLayout(top_bar_layout)

        self.preview_stack = QStackedWidget()
        self.text_preview = QTextEdit()
        self.text_preview.setReadOnly(True)
        self.pdf_preview = QLabel()
        self.pdf_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_stack.addWidget(self.text_preview)
        self.preview_stack.addWidget(self.pdf_preview)
        preview_layout.addWidget(self.preview_stack)

        # PDF navigation
        pdf_nav_layout = QHBoxLayout()
        self.pdf_prev_button = QPushButton("◀ 前のページ")
        self.pdf_next_button = QPushButton("次のページ ▶")
        self.pdf_page_label = QLabel("ページ: 0/0")
        pdf_nav_layout.addWidget(self.pdf_prev_button)
        pdf_nav_layout.addWidget(self.pdf_page_label)
        pdf_nav_layout.addWidget(self.pdf_next_button)
        self.pdf_controls = QWidget()
        self.pdf_controls.setLayout(pdf_nav_layout)
        preview_layout.addWidget(self.pdf_controls)
        self.pdf_prev_button.clicked.connect(self.show_prev_pdf_page)
        self.pdf_next_button.clicked.connect(self.show_next_pdf_page)

        self.preview_view.setLayout(preview_layout)
        self.stack.addWidget(self.preview_view)

        self.stack.setCurrentWidget(self.info_view)

    def set_info_text(self, text):
        self.info_view.setText(text)
        self.stack.setCurrentWidget(self.info_view)

    def show_text_preview(self, text_content, file_path):
        self.preview_stack.setCurrentWidget(self.text_preview)
        self.pdf_controls.hide()
        self.back_button.setVisible(bool(self.search_keyword))
        self.current_file_label.setText(file_path)
        self.text_preview.setText(text_content)
        self.stack.setCurrentWidget(self.preview_view)
        
        # Always call highlight_keyword. It will handle resetting if the keyword is empty.
        self.highlight_keyword(self.search_keyword)

    def highlight_keyword(self, keyword):
        cursor = self.text_preview.textCursor()
        cursor.beginEditBlock()

        # First, clear all previous formatting
        fmt = QTextCharFormat()
        fmt.setBackground(QColor('transparent'))
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.setCharFormat(fmt)
        cursor.clearSelection()
        self.text_preview.setTextCursor(cursor) # Move cursor to start

        # If no keyword, we are done (the view is now clean)
        if not keyword:
            cursor.endEditBlock()
            return

        # Apply new highlights for the given keyword
        fmt.setBackground(QColor('yellow'))
        doc = self.text_preview.document()
        find_flags = QTextDocument.FindFlag.FindCaseSensitively

        first_match_cursor = doc.find(keyword, 0, find_flags)
        if not first_match_cursor.isNull():
            # Use a separate cursor for highlighting to not interfere with find operation
            highlight_cursor = QTextCursor(doc)
            while not highlight_cursor.isNull() and not highlight_cursor.atEnd():
                highlight_cursor = doc.find(keyword, highlight_cursor, find_flags)
                if not highlight_cursor.isNull():
                    highlight_cursor.mergeCharFormat(fmt)
        
        cursor.endEditBlock()

        # Move viewport to the first match
        if not first_match_cursor.isNull():
            self.text_preview.setTextCursor(first_match_cursor)


    def show_pdf_preview(self, temp_path, file_path):
        self.current_pdf_path = temp_path
        self.current_pdf_page = 0
        self.preview_stack.setCurrentWidget(self.pdf_preview)
        self.pdf_controls.show()
        self.back_button.setVisible(bool(self.search_keyword))
        self.current_file_label.setText(file_path)
        self.display_pdf_page(0)
        self.stack.setCurrentWidget(self.preview_view)

    def display_pdf_page(self, page_num):
        images = render_pdf_as_pixmaps(self.current_pdf_path)
        if not images:
            self.set_info_text("PDFプレビューエラー")
            return

        self.total_pdf_pages = len(images)
        self.current_pdf_page = page_num
        self.pdf_page_label.setText(f"ページ: {self.current_pdf_page + 1}/{self.total_pdf_pages}")

        img = QImage(images[page_num].samples, images[page_num].width, images[page_num].height, images[page_num].stride, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(img)
        scaled_pixmap = pixmap.scaled(self.pdf_preview.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.pdf_preview.setPixmap(scaled_pixmap)

    def show_prev_pdf_page(self):
        if self.current_pdf_page > 0:
            self.display_pdf_page(self.current_pdf_page - 1)

    def show_next_pdf_page(self):
        if self.current_pdf_page < self.total_pdf_pages - 1:
            self.display_pdf_page(self.current_pdf_page + 1)

    def display_search_results(self, found_files, keyword):
        self.search_keyword = keyword
        self.search_results_list.clear()
        if not found_files:
            self.set_info_text(f"'{keyword}' は見つかりませんでした。")
            return
            
        for file_path in found_files:
            item = QListWidgetItem(file_path)
            self.search_results_list.addItem(item)
        self.show_search_results()

    def show_search_results(self):
        self.stack.setCurrentWidget(self.search_results_view)

    def on_search_result_selected(self, item):
        self.file_selected_from_search.emit(item.text())

    def clear_preview(self, clear_keyword=True):
        self.set_info_text("")
        if clear_keyword:
            self.search_keyword = ""

    def show_search_result_context_menu(self, pos):
        if not self.search_results_list.itemAt(pos):
            return
        
        menu = QMenu()
        copy_action = menu.addAction("パスをコピー")
        action = menu.exec(self.search_results_list.mapToGlobal(pos))
        
        if action == copy_action:
            item = self.search_results_list.currentItem()
            if item:
                QApplication.clipboard().setText(item.text())
