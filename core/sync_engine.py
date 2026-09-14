"""
sync_engine.py

Motor de sincronizacion (misma logica que el sync_gcodes.py original),
refactorizado para ser usado desde una GUI:
  - En vez de imprimir a consola, todo reporta a traves de un callback
    log_fn(printer_name, level, msg).
  - Soporta cancelacion cooperativa via un threading.Event.
  - Expone funciones sueltas para el explorador remoto (listar/borrar
    archivos individuales de una impresora).

No cambia ningun criterio de negocio respecto del script original:
- Comparacion por tamaño en bytes (no mtime).
- Proteccion de archivos en impresion/cola via Moonraker.
- Manejo de thumbnails (.thumbs/).
- find remoto con fallback a SFTP recursivo.
"""

import hashlib
import os
import re
import stat
import threading
import time
from pathlib import Path, PurePosixPath

import paramiko
import requests

from core.i18n import tr

SIZE_AMBIGUITY_THRESHOLD = 10

SSH_CONNECT_TIMEOUT = 8
MOONRAKER_TIMEOUT = 5
MAX_RETRIES = 2
RETRY_DELAY = 3

FILE_OP_MAX_RETRIES = 2
FILE_OP_RETRY_DELAY = 1

THUMBS_DIRNAME = ".thumbs"
HASH_CHUNK_SIZE = 1024 * 1024


class SyncCancelled(Exception):
    """Se lanza internamente cuando el usuario cancela una sincronizacion."""


def _noop_log(printer_name, level, msg):
    pass


def _check_cancel(cancel_event):
    if cancel_event is not None and cancel_event.is_set():
        raise SyncCancelled()


# --------------------------------------------------------------------------
# Utilidades
# --------------------------------------------------------------------------

def fmt_size(num_bytes: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if num_bytes < 1024:
            return f"{num_bytes:.1f}{unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f}TB"


def fmt_eta(seconds: float) -> str:
    if seconds < 0 or seconds != seconds:
        return "?"
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    minutes, secs = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m{secs:02d}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h{minutes:02d}m"


def is_thumbs_path(rel_path: str) -> bool:
    parts = PurePosixPath(rel_path).parts
    return THUMBS_DIRNAME in parts


def thumb_owner_gcode_rel_path(thumb_rel_path: str):
    p = PurePosixPath(thumb_rel_path)
    parent_dir = p.parent.parent
    stem = p.stem
    m = re.match(r"^(.*)-\d+x\d+$", stem)
    if not m:
        return None
    base_name = m.group(1)
    return (parent_dir / f"{base_name}.gcode").as_posix()


def retry_file_op(description, func, errors_log, log_fn, printer_name, cancel_event=None):
    last_exc = None
    for attempt in range(1, FILE_OP_MAX_RETRIES + 2):
        _check_cancel(cancel_event)
        try:
            func()
            return True
        except Exception as e:
            last_exc = e
            if attempt <= FILE_OP_MAX_RETRIES:
                time.sleep(FILE_OP_RETRY_DELAY)
    log_fn(printer_name, "ERR", tr("log.file_op_failed", description=description, error=last_exc))
    errors_log.append((description, str(last_exc)))
    return False


def local_file_hash(path: Path) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(HASH_CHUNK_SIZE)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def scan_local_dir(local_root: Path):
    """Devuelve dict {ruta_relativa_posix: {'size':int, 'mtime':int, 'abs': Path}}"""
    result = {}
    for dirpath, _dirnames, filenames in os.walk(local_root):
        for fname in filenames:
            abs_path = Path(dirpath) / fname
            rel_path = abs_path.relative_to(local_root)
            rel_posix = rel_path.as_posix()
            st = abs_path.stat()
            result[rel_posix] = {"size": st.st_size, "mtime": int(st.st_mtime), "abs": abs_path}
    return result


# --------------------------------------------------------------------------
# Moonraker
# --------------------------------------------------------------------------

def get_protected_files(host: str, port: int):
    base = f"http://{host}:{port}"
    protected = set()
    state = "klipper_disconnected"

    try:
        r = requests.get(
            f"{base}/printer/objects/query?virtual_sdcard&display_status&print_stats",
            timeout=MOONRAKER_TIMEOUT,
        )
        if r.status_code in (404, 503):
            state = "klipper_disconnected"
        else:
            r.raise_for_status()
            data = r.json()
            status = data.get("result", {}).get("status", {})
            print_stats = status.get("print_stats", {})
            virtual_sdcard = status.get("virtual_sdcard", {})
            state = print_stats.get("state", "").lower()
            current_file = print_stats.get("filename")
            is_active = virtual_sdcard.get("is_active", False)
            if (state in ("printing", "paused") or is_active) and current_file:
                protected.add(current_file)
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code in (404, 503):
            state = "klipper_disconnected"
        else:
            raise

    r = requests.get(f"{base}/server/job_queue/status", timeout=MOONRAKER_TIMEOUT)
    r.raise_for_status()
    data = r.json()
    queued_jobs = data.get("result", {}).get("queued_jobs", [])
    for job in queued_jobs:
        fname = job.get("filename")
        if fname:
            protected.add(fname)

    return protected, state


def get_moonraker_status_with_retry(host, port, log_fn, printer_name, cancel_event=None):
    last_exc = None
    for attempt in range(1, MAX_RETRIES + 2):
        _check_cancel(cancel_event)
        try:
            return get_protected_files(host, port)
        except Exception as e:
            last_exc = e
            if attempt <= MAX_RETRIES:
                log_fn(printer_name, "WARN",
                       tr("log.moonraker_retry", attempt=attempt, error=e, delay=RETRY_DELAY))
                time.sleep(RETRY_DELAY)
    raise last_exc


# --------------------------------------------------------------------------
# SSH / SFTP
# --------------------------------------------------------------------------

def connect_ssh(host, port, user, password, log_fn=_noop_log, printer_name="", cancel_event=None):
    last_exc = None
    for attempt in range(1, MAX_RETRIES + 2):
        _check_cancel(cancel_event)
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(
                hostname=host, port=port, username=user, password=password,
                timeout=SSH_CONNECT_TIMEOUT, banner_timeout=SSH_CONNECT_TIMEOUT,
                auth_timeout=SSH_CONNECT_TIMEOUT,
            )
            return client
        except Exception as e:
            last_exc = e
            if attempt <= MAX_RETRIES:
                log_fn(printer_name, "WARN",
                       tr("log.ssh_retry", attempt=attempt, error=e, delay=RETRY_DELAY))
                time.sleep(RETRY_DELAY)
    raise last_exc


def scan_remote_dir(ssh_client, sftp, remote_root, log_fn=_noop_log, printer_name=""):
    quoted_root = remote_root.replace("'", "'\\''")
    cmd = f"find '{quoted_root}' -type f -printf '%s\\t%T@\\t%P\\n' 2>/dev/null"
    try:
        stdin, stdout, stderr = ssh_client.exec_command(cmd, timeout=MOONRAKER_TIMEOUT * 3)
        output = stdout.read().decode("utf-8", errors="replace")
        exit_status = stdout.channel.recv_exit_status()
        if exit_status != 0 and not output.strip():
            raise RuntimeError(f"find devolvio status {exit_status} sin output")

        result = {}
        for line in output.splitlines():
            if not line.strip():
                continue
            try:
                size_str, mtime_str, rel_path = line.split("\t", 2)
                result[rel_path] = {"size": int(size_str), "mtime": int(float(mtime_str))}
            except ValueError:
                continue
        return result
    except Exception as e:
        log_fn(printer_name, "WARN", tr("log.find_fallback", error=e))
        return _scan_remote_dir_sftp_fallback(sftp, remote_root)


def _scan_remote_dir_sftp_fallback(sftp, remote_root):
    result = {}

    def _walk(remote_dir, rel_prefix):
        try:
            entries = sftp.listdir_attr(remote_dir)
        except FileNotFoundError:
            return
        for entry in entries:
            remote_path = f"{remote_dir}/{entry.filename}"
            rel_path = f"{rel_prefix}{entry.filename}" if not rel_prefix else f"{rel_prefix}/{entry.filename}"
            if stat.S_ISDIR(entry.st_mode):
                _walk(remote_path, rel_path)
            else:
                result[rel_path] = {"size": entry.st_size, "mtime": entry.st_mtime}

    _walk(remote_root, "")
    return result


def ensure_remote_dir(sftp, remote_dir):
    parts = PurePosixPath(remote_dir).parts
    current = ""
    for part in parts:
        current = f"{current}/{part}" if current else part
        if current == "":
            continue
        try:
            sftp.stat(current)
        except FileNotFoundError:
            sftp.mkdir(current)


# --------------------------------------------------------------------------
# Sincronizacion de una impresora
# --------------------------------------------------------------------------

def sync_printer(printer_cfg, global_cfg, local_files, password, dry_run,
                  log_fn, progress_fn=None, cancel_event=None):
    """
    progress_fn(printer_name, kind, idx, total, extra_dict) se llama para
    reportar avance de listado/subida/borrado. kind in
    {"list_remote", "upload", "delete", "compare"}.
    """
    name = printer_cfg["name"]
    host = printer_cfg["host"]
    ssh_port = printer_cfg.get("ssh_port", global_cfg.get("ssh_port", 22))
    moonraker_port = printer_cfg.get("moonraker_port", global_cfg.get("moonraker_port", 7125))
    remote_root = printer_cfg.get("remote_gcodes_path", global_cfg["remote_gcodes_path"])
    user = global_cfg["ssh_user"]

    def _log(level, msg):
        log_fn(name, level, msg)

    _log("INFO", tr("log.header", name=name, host=host))

    try:
        protected_files, print_state = get_moonraker_status_with_retry(
            host, moonraker_port, log_fn, name, cancel_event)
    except SyncCancelled:
        raise
    except Exception as e:
        _log("ERR", tr("log.moonraker_unreachable", error=e))
        return {"name": name, "status": "skipped", "reason": tr("log.skip_reason_moonraker", error=e)}

    if protected_files:
        _log("INFO", tr("log.print_status_protected", state=print_state or "?", count=len(protected_files)))
        for pf in sorted(protected_files):
            _log("INFO", tr("log.protected_item", path=pf))
    else:
        _log("INFO", tr("log.print_status_idle", state=print_state or "idle"))

    try:
        ssh_client = connect_ssh(host, ssh_port, user, password, log_fn, name, cancel_event)
    except SyncCancelled:
        raise
    except Exception as e:
        _log("ERR", tr("log.ssh_unreachable", error=e))
        return {"name": name, "status": "skipped", "reason": tr("log.skip_reason_ssh", error=e)}

    result = {"name": name, "status": "ok", "uploaded": [], "deleted": [],
              "skipped_protected": [], "needs_review": [], "file_errors": []}
    file_errors = result["file_errors"]
    changes_to_review = []

    try:
        sftp = ssh_client.open_sftp()
        _log("INFO", tr("log.listing_remote"))
        remote_all = scan_remote_dir(ssh_client, sftp, remote_root, log_fn, name)

        remote_files = {p: info for p, info in remote_all.items() if not is_thumbs_path(p)}
        remote_thumbs = {p: info for p, info in remote_all.items() if is_thumbs_path(p)}

        _log("INFO", tr("log.files_found_compare", remote=len(remote_files),
                         thumbs=len(remote_thumbs), local=len(local_files)))

        def remote_path_of(rel):
            return f"{remote_root}/{rel}"

        def delete_thumbs_for(gcode_rel_path):
            gcode_p = PurePosixPath(gcode_rel_path)
            stem = gcode_p.stem
            thumbs_dir_rel = (gcode_p.parent / THUMBS_DIRNAME).as_posix()
            for thumb_rel in list(remote_thumbs.keys()):
                t = PurePosixPath(thumb_rel)
                if t.parent.as_posix() != thumbs_dir_rel:
                    continue
                if not t.stem.startswith(f"{stem}-"):
                    continue
                desc = tr("log.desc_delete_thumb_old", path=thumb_rel)
                ok = retry_file_op(desc, lambda t=thumb_rel: sftp.remove(remote_path_of(t)),
                                    file_errors, log_fn, name, cancel_event)
                if ok:
                    _log("INFO", tr("log.thumb_cleaned", path=thumb_rel))
                    del remote_thumbs[thumb_rel]

        total_local = len(local_files)
        for idx, (rel_path, local_info) in enumerate(local_files.items(), start=1):
            _check_cancel(cancel_event)
            remote_info = remote_files.get(rel_path)
            needs_upload = remote_info is None or local_info["size"] != remote_info["size"]
            if not needs_upload:
                continue

            is_protected = rel_path in protected_files
            if is_protected and remote_info is not None:
                _log("WARN", tr("log.change_protected_upload", path=rel_path))
                result["skipped_protected"].append(rel_path)
                result["needs_review"].append(rel_path)
                changes_to_review.append(rel_path)
                continue

            remote_path_full = remote_path_of(rel_path)
            if dry_run:
                _log("INFO", tr("log.dry_run_upload", idx=idx, total=total_local, path=rel_path))
                result["uploaded"].append(rel_path)
                continue

            remote_dir = str(PurePosixPath(remote_root) / PurePosixPath(rel_path).parent)
            file_size = local_info["size"]

            def _do_upload(_rel=rel_path, _abs=local_info["abs"], _dir=remote_dir,
                            _dest=remote_path_full, _size=file_size, _idx=idx):
                ensure_remote_dir(sftp, _dir)
                if _size > 0:
                    size_str = fmt_size(_size)
                    start_time = time.monotonic()
                    last_print = {"t": 0.0}

                    def _progress(transferred, total):
                        now = time.monotonic()
                        if now - last_print["t"] < 0.3 and transferred < total:
                            return
                        last_print["t"] = now
                        elapsed = now - start_time
                        pct = (transferred / total * 100) if total else 100
                        speed = transferred / elapsed if elapsed > 0 else 0
                        remaining = (total - transferred) / speed if speed > 0 else float("nan")
                        if progress_fn:
                            progress_fn(name, "upload", _idx, total_local, {
                                "rel_path": _rel, "pct": pct, "speed": speed,
                                "eta": remaining, "size_str": size_str,
                            })

                    sftp.put(str(_abs), _dest, callback=_progress)
                else:
                    sftp.put(str(_abs), _dest)
                if progress_fn:
                    progress_fn(name, "upload", _idx, total_local, {
                        "rel_path": _rel, "pct": 100, "speed": 0, "eta": 0, "size_str": fmt_size(_size),
                        "done": True,
                    })

            ok = retry_file_op(tr("log.desc_upload", path=rel_path), _do_upload, file_errors, log_fn, name, cancel_event)
            if ok:
                result["uploaded"].append(rel_path)
                delete_thumbs_for(rel_path)

        to_delete_candidates = [p for p in remote_files if p not in local_files]
        total_delete = len(to_delete_candidates)
        for idx, rel_path in enumerate(to_delete_candidates, start=1):
            _check_cancel(cancel_event)
            if rel_path in protected_files:
                _log("WARN", tr("log.change_protected_delete", path=rel_path))
                result["skipped_protected"].append(rel_path)
                result["needs_review"].append(rel_path)
                changes_to_review.append(rel_path)
                continue

            remote_path_full = remote_path_of(rel_path)
            if dry_run:
                _log("INFO", tr("log.dry_run_delete", idx=idx, total=total_delete, path=rel_path))
                result["deleted"].append(rel_path)
                continue

            ok = retry_file_op(
                tr("log.desc_delete", path=rel_path),
                lambda rp=remote_path_full: sftp.remove(rp),
                file_errors, log_fn, name, cancel_event,
            )
            if ok:
                _log("INFO", tr("log.deleted_item", idx=idx, total=total_delete, path=rel_path))
                result["deleted"].append(rel_path)
                delete_thumbs_for(rel_path)
                if progress_fn:
                    progress_fn(name, "delete", idx, total_delete, {"rel_path": rel_path})

        if not dry_run:
            orphans = []
            for thumb_rel in list(remote_thumbs.keys()):
                owner = thumb_owner_gcode_rel_path(thumb_rel)
                if owner is None:
                    continue
                if owner not in remote_files:
                    orphans.append(thumb_rel)

            if orphans:
                _log("INFO", tr("log.cleaning_orphans", count=len(orphans)))
                for thumb_rel in orphans:
                    ok = retry_file_op(
                        tr("log.desc_delete_thumb_orphan", path=thumb_rel),
                        lambda t=thumb_rel: sftp.remove(remote_path_of(t)),
                        file_errors, log_fn, name, cancel_event,
                    )
                    if ok:
                        result["deleted"].append(thumb_rel)

        sftp.close()
    except SyncCancelled:
        _log("WARN", tr("log.cancelled"))
        result["status"] = "cancelled"
        raise
    finally:
        ssh_client.close()

    if not result["uploaded"] and not result["deleted"] and not result["skipped_protected"]:
        _log("INFO", tr("log.already_synced"))

    if file_errors:
        _log("WARN", tr("log.file_errors_count", count=len(file_errors)))
        for desc, err in file_errors:
            _log("WARN", tr("log.error_detail", desc=desc, error=err))

    result["changes_to_review"] = changes_to_review
    return result


# --------------------------------------------------------------------------
# Funciones para el Explorador remoto
# --------------------------------------------------------------------------

def explorer_connect(host, ssh_port, user, password, log_fn=_noop_log, printer_name=""):
    """Conecta SSH+SFTP a una impresora. Devuelve (ssh_client, sftp)."""
    ssh_client = connect_ssh(host, ssh_port, user, password, log_fn, printer_name)
    sftp = ssh_client.open_sftp()
    return ssh_client, sftp


def explorer_list_files(ssh_client, sftp, remote_root, host, moonraker_port, log_fn=_noop_log, printer_name=""):
    """
    Lista todos los archivos remotos (incluyendo .thumbs/) con su tamaño y
    fecha de modificación, y marca cuales estan protegidos (imprimiendo/en
    cola) segun Moonraker.
    Devuelve lista de dicts: {rel_path, size, mtime, is_thumb, protected}
    """
    try:
        protected_files, _state = get_protected_files(host, moonraker_port)
    except Exception as e:
        log_fn(printer_name, "WARN", tr("log.moonraker_query_failed", error=e))
        protected_files = set()

    remote_all = scan_remote_dir(ssh_client, sftp, remote_root, log_fn, printer_name)
    files = []
    for rel_path, info in sorted(remote_all.items()):
        files.append({
            "rel_path": rel_path,
            "size": info["size"],
            "mtime": info.get("mtime", 0),
            "is_thumb": is_thumbs_path(rel_path),
            "protected": rel_path in protected_files,
        })
    return files


_THUMB_SUFFIX_RE = re.compile(r"^(.*)-(\d+)x(\d+)$")


def find_thumbnails(gcode_rel_path: str, all_rel_paths):
    """
    Busca los thumbnails asociados a un gcode dentro de la lista de rutas
    remotas ya escaneadas. Devuelve una lista de rutas relativas ordenada
    de menor a mayor resolución (para elegir la mas chica como ícono y la
    mas grande como preview al hacer hover).
    """
    p = PurePosixPath(gcode_rel_path)
    thumbs_dir = (p.parent / THUMBS_DIRNAME).as_posix()
    stem = p.stem
    candidates = []
    for rel in all_rel_paths:
        tp = PurePosixPath(rel)
        if tp.parent.as_posix() != thumbs_dir:
            continue
        if tp.suffix.lower() != ".png":
            continue
        m = _THUMB_SUFFIX_RE.match(tp.stem)
        if not m or m.group(1) != stem:
            continue
        area = int(m.group(2)) * int(m.group(3))
        candidates.append((area, rel))
    candidates.sort(key=lambda c: c[0])
    return [rel for _area, rel in candidates]


def download_remote_bytes(sftp, remote_root, rel_path) -> bytes:
    """Descarga un archivo remoto chico (pensado para thumbnails PNG) y
    devuelve su contenido en memoria."""
    import io
    buf = io.BytesIO()
    sftp.getfo(f"{remote_root}/{rel_path}", buf)
    return buf.getvalue()


def prune_empty_dirs(ssh_client, remote_root, log_fn=_noop_log, printer_name=""):
    """Borra recursivamente subcarpetas vacías que hayan quedado tras
    eliminar archivos (nunca borra remote_root en si, por mindepth 1)."""
    quoted_root = remote_root.replace("'", "'\\''")
    # se corre varias veces: al borrar una subcarpeta vacia, su padre
    # puede quedar vacio tambien, y find -delete no siempre repasa eso
    # en una sola pasada de arriba hacia abajo.
    for _ in range(4):
        cmd = f"find '{quoted_root}' -mindepth 1 -type d -empty -delete 2>/dev/null"
        try:
            _stdin, stdout, _stderr = ssh_client.exec_command(cmd, timeout=15)
            stdout.channel.recv_exit_status()
        except Exception as e:
            log_fn(printer_name, "WARN", tr("log.prune_failed", error=e))
            return


def explorer_delete_files(sftp, remote_root, rel_paths, log_fn=_noop_log, printer_name=""):
    """
    Borra una lista de archivos remotos (rutas relativas). Devuelve
    (borrados, errores) donde errores es lista de (rel_path, mensaje).
    """
    deleted, errors = [], []
    for rel_path in rel_paths:
        remote_path = f"{remote_root}/{rel_path}"
        try:
            sftp.remove(remote_path)
            deleted.append(rel_path)
            log_fn(printer_name, "INFO", tr("log.deleted", path=rel_path))
        except Exception as e:
            errors.append((rel_path, str(e)))
            log_fn(printer_name, "ERR", tr("log.delete_failed", path=rel_path, error=e))
    return deleted, errors
