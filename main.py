#!/usr/bin/env python3
"""
main.py

Punto de entrada de Klipper Sync GUI.
Correr con: python main.py
"""

import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from core.resources import resource_path
from gui.main_window import MainWindow


def _set_windows_app_id():
    """Le avisa a Windows que esta app es su propia entidad (no 'python'),
    asi la barra de tareas no la agrupa con el icono generico de Python
    y usa el icono que le seteamos a la ventana."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("KlipperSync.App.1")
    except Exception:
        pass


def main():
    _set_windows_app_id()

    app = QApplication(sys.argv)
    app.setApplicationName("Klipper Sync")

    icon_path = resource_path("assets/icon.ico")
    app.setWindowIcon(QIcon(icon_path))

    window = MainWindow()
    window.setWindowIcon(QIcon(icon_path))
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
