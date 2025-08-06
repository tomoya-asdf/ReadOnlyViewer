
import sys
import traceback
from PyQt6.QtCore import QObject, QRunnable, pyqtSignal, pyqtSlot

class WorkerSignals(QObject):
    """
    Defines the signals available from a running worker thread.
    """
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    progress = pyqtSignal(object)

class Worker(QRunnable):
    """
    Worker thread
    Inherits from QRunnable to handle worker thread setup, signals, and wrap-up.
    """
    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()
        self.fn = fn
        self.args = args
        # Extract signals instance if passed in kwargs
        self.signals = kwargs.pop('signals', WorkerSignals())
        self.kwargs = kwargs

    @pyqtSlot()
    def run(self):
        """
        Initialise the runner function with passed args, kwargs.
        """
        try:
            result = self.fn(*self.args, **self.kwargs)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)
        finally:
            self.signals.finished.emit()
