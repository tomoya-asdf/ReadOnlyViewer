
import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTreeView, QLineEdit, QPushButton
from PyQt6.QtCore import QDir, Qt, pyqtSignal, QSortFilterProxyModel
from PyQt6.QtGui import QFileSystemModel, QShortcut, QKeySequence

class FileTreeView(QWidget):
    file_double_clicked = pyqtSignal(str)
    directory_changed = pyqtSignal(str)

    def __init__(self, initial_dir, parent=None):
        super().__init__(parent)
        self.initial_dir = initial_dir
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)

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

        self.path_bar = QLineEdit()
        self.path_bar.setText(self.initial_dir)
        self.path_bar.returnPressed.connect(self.on_path_entered)
        
        shortcut = QShortcut(QKeySequence("Ctrl+L"), self)
        shortcut.activated.connect(self.path_bar.selectAll)

        self.back_button = QPushButton("⬅")
        self.back_button.setObjectName("back_button")
        self.back_button.clicked.connect(self.go_to_parent_directory)
        self.back_button.setShortcut("Alt+Left")

        path_layout = QHBoxLayout()
        path_layout.addWidget(self.back_button)
        path_layout.addWidget(self.path_bar)

        layout.addLayout(path_layout)
        layout.addWidget(self.tree)

    def on_item_double_clicked(self, index):
        source_index = self.proxy_model.mapToSource(index)
        file_path = self.model.filePath(source_index)
        if os.path.isfile(file_path):
            self.file_double_clicked.emit(file_path)
        else:
            self.tree.setRootIndex(index)
            self.path_bar.setText(file_path)
            self.directory_changed.emit(file_path)

    def on_path_entered(self):
        path = self.path_bar.text()
        if os.path.isdir(path):
            source_index = self.model.index(path)
            if source_index.isValid():
                proxy_index = self.proxy_model.mapFromSource(source_index)
                self.tree.setRootIndex(proxy_index)
                self.tree.scrollTo(proxy_index)
                self.directory_changed.emit(path)
        elif os.path.isfile(path):
            self.file_double_clicked.emit(path)

    def go_to_parent_directory(self):
        current_index = self.tree.rootIndex()
        source_index = self.proxy_model.mapToSource(current_index)
        parent_source_index = source_index.parent()
        if parent_source_index.isValid():
            parent_proxy_index = self.proxy_model.mapFromSource(parent_source_index)
            self.tree.setRootIndex(parent_proxy_index)
            file_path = self.model.filePath(parent_source_index)
            self.path_bar.setText(file_path)
            self.directory_changed.emit(file_path)

    def apply_filter(self, filter_pattern):
        self.proxy_model.setFilterRegularExpression(filter_pattern)

    def get_current_directory(self):
        source_index = self.proxy_model.mapToSource(self.tree.rootIndex())
        return self.model.filePath(source_index)

    def get_filtered_file_list(self):
        """Recursively fetches the list of all visible files under the current root."""
        visible_files = []
        root_index = self.tree.rootIndex()

        # Stack for iterative traversal
        stack = [root_index]

        while stack:
            parent_index = stack.pop()
            for row in range(self.proxy_model.rowCount(parent_index)):
                index = self.proxy_model.index(row, 0, parent_index)
                if not index.isValid():
                    continue

                source_index = self.proxy_model.mapToSource(index)
                file_path = self.model.filePath(source_index)
                
                # If it's a directory, add to stack to traverse its children
                if self.model.isDir(source_index):
                    stack.append(index)
                # If it's a file, add its path to the list
                else:
                    visible_files.append(file_path)
        
        return visible_files
