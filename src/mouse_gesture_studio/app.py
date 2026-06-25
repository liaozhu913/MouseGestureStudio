from __future__ import annotations

import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from .config import ConfigManager, resource_path
from .ui import MainWindow


def run() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("MouseGestureStudio")
    app.setWindowIcon(QIcon(str(resource_path("assets", "logo.ico"))))

    config_manager = ConfigManager()
    window = MainWindow(config_manager)
    window.show()
    return app.exec()
