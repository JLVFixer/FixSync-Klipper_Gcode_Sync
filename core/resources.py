"""
resources.py

Resuelve rutas a assets (iconos, etc) tanto corriendo desde codigo fuente
como empaquetado con PyInstaller --onefile (donde los datos van a parar
a una carpeta temporal, sys._MEIPASS).
"""

import sys
from pathlib import Path


def resource_path(relative_path: str) -> str:
    if hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parent.parent
    return str(base / relative_path)
