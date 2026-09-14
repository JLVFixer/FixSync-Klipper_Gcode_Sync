"""
store.py

Carga/guarda printers.json (misma estructura que el script original,
para que sea compatible si el usuario ya tenia uno) y settings.json
(preferencias de la app: color de acento, ultima carpeta, etc).

Los archivos de config viven siempre AL LADO del ejecutable (o del
script, si se corre desde Python sin compilar), para que la app sea
portable: se puede copiar la carpeta a un pendrive y sigue funcionando.
"""

import json
import sys
from pathlib import Path

APP_NAME = "KlipperSyncGUI"

DEFAULT_CONFIG = {
    "local_gcodes_dir": "",
    "ssh_user": "fixer",
    "ssh_password": "",
    "remote_gcodes_path": "/home/fixer/printer_data/gcodes",
    "moonraker_port": 7125,
    "ssh_port": 22,
    "printers": [],
}

DEFAULT_SETTINGS = {
    "language": "es",
    "accent_color": "#E53935",
    "background_color": "#121212",
    "surface_color": "#1C1C1C",
    "text_color": "#E8E8E8",
    "auto_sync_enabled": False,
    "auto_sync_minutes": 30,
}


def base_dir() -> Path:
    """Carpeta donde viven printers.json/settings.json: al lado del .exe
    si esta empaquetado (PyInstaller), o la raiz del proyecto si se corre
    desde codigo fuente."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def config_path() -> Path:
    return base_dir() / "printers.json"


def settings_path() -> Path:
    return base_dir() / "settings.json"


# --------------------------------------------------------------------------
# Config principal (printers.json)
# --------------------------------------------------------------------------

def load_config() -> dict:
    path = config_path()
    if not path.exists():
        cfg = dict(DEFAULT_CONFIG)
        save_config(cfg)
        return cfg
    with open(path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    # completar claves faltantes con default, por compatibilidad hacia atras
    for k, v in DEFAULT_CONFIG.items():
        cfg.setdefault(k, v)
    return cfg


def save_config(cfg: dict):
    path = config_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


class DuplicateNameError(ValueError):
    def __init__(self, name):
        self.name = name
        super().__init__(name)


class PrinterNotFoundError(ValueError):
    def __init__(self, name):
        self.name = name
        super().__init__(name)


def add_printer(cfg: dict, printer: dict):
    names = {p["name"].lower() for p in cfg["printers"]}
    if printer["name"].lower() in names:
        raise DuplicateNameError(printer["name"])
    cfg["printers"].append(printer)
    save_config(cfg)


def update_printer(cfg: dict, original_name: str, updated: dict):
    for i, p in enumerate(cfg["printers"]):
        if p["name"].lower() == original_name.lower():
            if updated["name"].lower() != original_name.lower():
                other_names = {pp["name"].lower() for j, pp in enumerate(cfg["printers"]) if j != i}
                if updated["name"].lower() in other_names:
                    raise DuplicateNameError(updated["name"])
            cfg["printers"][i] = updated
            save_config(cfg)
            return
    raise PrinterNotFoundError(original_name)


def delete_printer(cfg: dict, name: str):
    cfg["printers"] = [p for p in cfg["printers"] if p["name"].lower() != name.lower()]
    save_config(cfg)


def move_printer(cfg: dict, name: str, direction: int):
    """direction: -1 subir, +1 bajar"""
    idx = next((i for i, p in enumerate(cfg["printers"]) if p["name"].lower() == name.lower()), None)
    if idx is None:
        return
    new_idx = idx + direction
    if 0 <= new_idx < len(cfg["printers"]):
        cfg["printers"][idx], cfg["printers"][new_idx] = cfg["printers"][new_idx], cfg["printers"][idx]
        save_config(cfg)


# --------------------------------------------------------------------------
# Settings (tema, preferencias)
# --------------------------------------------------------------------------

def load_settings() -> dict:
    path = settings_path()
    if not path.exists():
        settings = dict(DEFAULT_SETTINGS)
        save_settings(settings)
        return settings
    with open(path, "r", encoding="utf-8") as f:
        settings = json.load(f)
    for k, v in DEFAULT_SETTINGS.items():
        settings.setdefault(k, v)
    return settings


def save_settings(settings: dict):
    path = settings_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)
