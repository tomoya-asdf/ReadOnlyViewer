
import sys
from PyQt6.QtWidgets import QApplication
from file_viewer import FileViewer

if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = FileViewer()
    if viewer.initial_dir:
        viewer.show()
        sys.exit(app.exec())
