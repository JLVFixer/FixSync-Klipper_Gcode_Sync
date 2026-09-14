"""
workers.py

QThreads que ejecutan el motor de sincronizacion / exploracion remota sin
bloquear la interfaz. Los callbacks del motor (log_fn, progress_fn) emiten
señales Qt, que son thread-safe incluso llamadas desde los threads internos
del ThreadPoolExecutor.
"""

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from PySide6.QtCore import QThread, Signal

from core import sync_engine as engine
from core.i18n import tr


class SyncWorker(QThread):
    log_line = Signal(str, str, str)          # printer_name, level, msg
    printer_progress = Signal(str, str, int, int, dict)  # printer, kind, idx, total, extra
    printer_finished = Signal(dict)           # result dict de una impresora
    all_finished = Signal(list, list)         # results, changes_to_review [(printer, rel_path)]

    def __init__(self, cfg, printers, password, dry_run, hash_cache=None, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.printers = printers
        self.password = password
        self.dry_run = dry_run
        self.cancel_event = threading.Event()

    def cancel(self):
        self.cancel_event.set()

    def _log_fn(self, printer_name, level, msg):
        self.log_line.emit(printer_name, level, msg)

    def _progress_fn(self, printer_name, kind, idx, total, extra):
        self.printer_progress.emit(printer_name, kind, idx, total, extra)

    def run(self):
        local_root = self.cfg["local_gcodes_dir"]
        try:
            from pathlib import Path
            local_files = engine.scan_local_dir(Path(local_root))
        except Exception as e:
            self.log_line.emit("", "ERR", tr("log.local_read_failed", path=local_root, error=e))
            self.all_finished.emit([], [])
            return

        self.log_line.emit("", "INFO", tr("log.local_files_found", count=len(local_files)))

        results = []
        all_changes = []

        def _run_one(printer_cfg):
            try:
                res = engine.sync_printer(
                    printer_cfg, self.cfg, local_files, self.password, self.dry_run,
                    log_fn=self._log_fn, progress_fn=self._progress_fn,
                    cancel_event=self.cancel_event,
                )
                for rel in res.get("changes_to_review", []):
                    all_changes.append((printer_cfg["name"], rel))
                return res
            except engine.SyncCancelled:
                return {"name": printer_cfg["name"], "status": "cancelled"}
            except Exception as e:
                self._log_fn(printer_cfg["name"], "ERR", tr("log.unexpected_error", error=e))
                return {"name": printer_cfg["name"], "status": "skipped", "reason": str(e)}

        with ThreadPoolExecutor(max_workers=max(1, len(self.printers))) as executor:
            future_map = {executor.submit(_run_one, p): p for p in self.printers}
            for future in as_completed(future_map):
                res = future.result()
                results.append(res)
                self.printer_finished.emit(res)

        order = {p["name"]: i for i, p in enumerate(self.printers)}
        results.sort(key=lambda r: order.get(r["name"], 999))
        self.all_finished.emit(results, all_changes)


class ExplorerListWorker(QThread):
    finished_ok = Signal(list)   # lista de dicts {rel_path, size, is_thumb, protected}
    finished_err = Signal(str)
    log_line = Signal(str, str, str)

    def __init__(self, printer_cfg, global_cfg, password, parent=None):
        super().__init__(parent)
        self.printer_cfg = printer_cfg
        self.global_cfg = global_cfg
        self.password = password

    def run(self):
        name = self.printer_cfg["name"]
        host = self.printer_cfg["host"]
        ssh_port = self.printer_cfg.get("ssh_port", self.global_cfg.get("ssh_port", 22))
        moonraker_port = self.printer_cfg.get("moonraker_port", self.global_cfg.get("moonraker_port", 7125))
        remote_root = self.printer_cfg.get("remote_gcodes_path", self.global_cfg["remote_gcodes_path"])
        user = self.global_cfg["ssh_user"]

        def _log(printer_name, level, msg):
            self.log_line.emit(printer_name, level, msg)

        try:
            ssh_client, sftp = engine.explorer_connect(host, ssh_port, user, self.password, _log, name)
        except Exception as e:
            self.finished_err.emit(f"No se pudo conectar a {name}: {e}")
            return
        try:
            files = engine.explorer_list_files(ssh_client, sftp, remote_root, host, moonraker_port, _log, name)
            self.finished_ok.emit(files)
        except Exception as e:
            self.finished_err.emit(f"Error listando archivos de {name}: {e}")
        finally:
            try:
                sftp.close()
            except Exception:
                pass
            ssh_client.close()


class ThumbnailWorker(QThread):
    """
    Descarga en background los thumbnails de una tanda de gcodes (icono
    chico + preview grande para el hover), reusando una sola conexion
    SSH/SFTP para toda la tanda. Emite un signal por cada gcode a medida
    que va llegando, para que la UI los muestre progresivamente.
    """
    thumbnail_ready = Signal(str, bytes, bytes)  # gcode_rel_path, icon_bytes, preview_bytes
    finished_all = Signal()

    def __init__(self, printer_cfg, global_cfg, password, jobs, parent=None):
        super().__init__(parent)
        self.printer_cfg = printer_cfg
        self.global_cfg = global_cfg
        self.password = password
        # jobs: lista de dicts {gcode_rel_path, icon_rel, preview_rel}
        self.jobs = jobs

    def run(self):
        host = self.printer_cfg["host"]
        ssh_port = self.printer_cfg.get("ssh_port", self.global_cfg.get("ssh_port", 22))
        remote_root = self.printer_cfg.get("remote_gcodes_path", self.global_cfg["remote_gcodes_path"])
        user = self.global_cfg["ssh_user"]

        try:
            ssh_client, sftp = engine.explorer_connect(host, ssh_port, user, self.password)
        except Exception:
            self.finished_all.emit()
            return

        cache = {}
        try:
            for job in self.jobs:
                icon_rel = job.get("icon_rel")
                preview_rel = job.get("preview_rel")
                icon_bytes = b""
                preview_bytes = b""
                try:
                    if icon_rel:
                        if icon_rel not in cache:
                            cache[icon_rel] = engine.download_remote_bytes(sftp, remote_root, icon_rel)
                        icon_bytes = cache[icon_rel]
                    if preview_rel:
                        if preview_rel not in cache:
                            cache[preview_rel] = engine.download_remote_bytes(sftp, remote_root, preview_rel)
                        preview_bytes = cache[preview_rel]
                except Exception:
                    pass
                if icon_bytes or preview_bytes:
                    self.thumbnail_ready.emit(job["gcode_rel_path"], icon_bytes, preview_bytes)
        finally:
            try:
                sftp.close()
            except Exception:
                pass
            ssh_client.close()
            self.finished_all.emit()


class ExplorerDeleteWorker(QThread):
    finished_ok = Signal(list, list)  # deleted, errors
    finished_err = Signal(str)
    log_line = Signal(str, str, str)

    def __init__(self, printer_cfg, global_cfg, password, rel_paths, parent=None):
        super().__init__(parent)
        self.printer_cfg = printer_cfg
        self.global_cfg = global_cfg
        self.password = password
        self.rel_paths = rel_paths

    def run(self):
        name = self.printer_cfg["name"]
        host = self.printer_cfg["host"]
        ssh_port = self.printer_cfg.get("ssh_port", self.global_cfg.get("ssh_port", 22))
        remote_root = self.printer_cfg.get("remote_gcodes_path", self.global_cfg["remote_gcodes_path"])
        user = self.global_cfg["ssh_user"]

        def _log(printer_name, level, msg):
            self.log_line.emit(printer_name, level, msg)

        try:
            ssh_client, sftp = engine.explorer_connect(host, ssh_port, user, self.password, _log, name)
        except Exception as e:
            self.finished_err.emit(f"No se pudo conectar a {name}: {e}")
            return
        try:
            deleted, errors = engine.explorer_delete_files(sftp, remote_root, self.rel_paths, _log, name)
            engine.prune_empty_dirs(ssh_client, remote_root, _log, name)
            self.finished_ok.emit(deleted, errors)
        finally:
            try:
                sftp.close()
            except Exception:
                pass
            ssh_client.close()
