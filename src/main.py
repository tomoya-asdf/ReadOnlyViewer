from __future__ import annotations

import sys
from multiprocessing import Pool, cpu_count, freeze_support
from PyQt6.QtWidgets import QApplication
from file_viewer import FileViewer

if __name__ == "__main__":
    # For Windows compatibility
    freeze_support()

    app = QApplication(sys.argv)
    app.setOrganizationName("DevApp")
    app.setApplicationName("ReadOnlyViewer")
    
    # Create the process pool and pass it to the main window
    try:
        pool = Pool(processes=max(1, cpu_count() - 1))

        viewer = FileViewer()
        viewer.set_process_pool(pool)

        if viewer.initial_dir:
            viewer.show()
            exit_code = app.exec()
        else:
            exit_code = 0

    finally:
        # Ensure the pool is closed gracefully
        if 'pool' in locals() and pool is not None:
            pool.close()
            pool.join()
        sys.exit(exit_code)
