"""
explorer_page.py

Explorador remoto estilo Mainsail (navegación por carpetas, thumbnails,
preview en hover, borrado múltiple incluyendo carpetas), con textos
traducibles vía core.i18n.tr(). retranslate() refresca los textos
estáticos; la tabla y el breadcrumb ya se reconstruyen dinámicamente en
cada navegación, así que retranslate() simplemente vuelve a renderizar
la carpeta actual para que tomen el nuevo idioma.
"""

from datetime import datetime

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QIcon, QPainter
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QFrame, QMessageBox, QPlainTextEdit,
)

from core import icons
from core.i18n import tr
from core.sync_engine import fmt_size, find_thumbnails
from gui.workers import ExplorerListWorker, ExplorerDeleteWorker, ThumbnailWorker

ACCENT = "#E53935"
MUTED = "#9A9A9A"
THUMB_ICON_SIZE = 30
PREVIEW_WIDTH = 260


def _fmt_mtime(ts):
    if not ts:
        return "-"
    try:
        return datetime.fromtimestamp(ts).strftime("%d/%m/%Y %H:%M")
    except (ValueError, OSError):
        return "-"


class ExplorerPage(QWidget):
    def __init__(self, cfg, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.list_worker = None
        self.delete_worker = None
        self.thumb_worker = None

        self.current_files = []
        self.current_path = ""
        self.row_entries = []
        self.row_by_relpath = {}
        self.generation = 0

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(14)

        self.title = QLabel()
        self.title.setObjectName("title")
        self.subtitle = QLabel()
        self.subtitle.setObjectName("subtitle")
        root.addWidget(self.title)
        root.addWidget(self.subtitle)

        top_card = QFrame()
        top_card.setObjectName("card")
        top_layout = QHBoxLayout(top_card)
        top_layout.setContentsMargins(14, 12, 14, 12)
        self.printer_label = QLabel()
        top_layout.addWidget(self.printer_label)
        self.printer_combo = QComboBox()
        top_layout.addWidget(self.printer_combo, 1)
        self.connect_btn = QPushButton()
        self.connect_btn.setIcon(icons.get_icon("sync", "#FFFFFF", 16))
        self.connect_btn.setObjectName("primary")
        self.connect_btn.clicked.connect(self._connect_and_load_root)
        top_layout.addWidget(self.connect_btn)
        root.addWidget(top_card)

        self.breadcrumb_row = QHBoxLayout()
        self.breadcrumb_row.setSpacing(2)
        breadcrumb_wrap = QFrame()
        breadcrumb_wrap.setLayout(self.breadcrumb_row)
        root.addWidget(breadcrumb_wrap)

        select_row = QHBoxLayout()
        self.select_all_btn = QPushButton()
        self.select_all_btn.clicked.connect(lambda: self._set_all_checked(True))
        self.select_none_btn = QPushButton()
        self.select_none_btn.clicked.connect(lambda: self._set_all_checked(False))
        select_row.addWidget(self.select_all_btn)
        select_row.addWidget(self.select_none_btn)
        select_row.addStretch()
        self.count_label = QLabel("")
        self.count_label.setObjectName("subtitle")
        select_row.addWidget(self.count_label)
        root.addLayout(select_row)

        self.table = QTableWidget(0, 3)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 34)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setIconSize(QSize(THUMB_ICON_SIZE, THUMB_ICON_SIZE))
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(38)
        self.table.cellDoubleClicked.connect(self._on_cell_double_clicked)
        root.addWidget(self.table, 1)

        bottom_row = QHBoxLayout()
        bottom_row.addStretch()
        self.delete_btn = QPushButton()
        self.delete_btn.setIcon(icons.get_icon("trash", ACCENT, 16))
        self.delete_btn.setObjectName("danger")
        self.delete_btn.clicked.connect(self._delete_selected)
        bottom_row.addWidget(self.delete_btn)
        root.addLayout(bottom_row)

        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(90)
        root.addWidget(self.log_view)

        self.refresh_printer_list()
        self.retranslate()

    # ------------------------------------------------------------------

    def retranslate(self):
        self.title.setText(tr("explorer.title"))
        self.subtitle.setText(tr("explorer.subtitle"))
        self.printer_label.setText(tr("explorer.printer_label"))
        self.connect_btn.setText(tr("explorer.connect_btn"))
        self.select_all_btn.setText(tr("explorer.select_all_btn"))
        self.select_none_btn.setText(tr("explorer.select_none_btn"))
        self.table.setHorizontalHeaderLabels(["", tr("explorer.col_name"), tr("explorer.col_modified")])
        self.delete_btn.setText(tr("explorer.delete_btn"))
        self._render_breadcrumb()
        if self.current_files:
            self._render_current_folder()

    # ------------------------------------------------------------------
    # Setup / navegacion
    # ------------------------------------------------------------------

    def refresh_printer_list(self):
        current = self.printer_combo.currentText()
        self.printer_combo.clear()
        for p in self.cfg["printers"]:
            self.printer_combo.addItem(p["name"])
        idx = self.printer_combo.findText(current)
        if idx >= 0:
            self.printer_combo.setCurrentIndex(idx)

    def _current_printer_cfg(self):
        name = self.printer_combo.currentText()
        return next((p for p in self.cfg["printers"] if p["name"] == name), None)

    def _connect_and_load_root(self):
        self.current_path = ""
        self._load_files()

    def _load_files(self):
        printer_cfg = self._current_printer_cfg()
        if not printer_cfg:
            QMessageBox.information(self, tr("explorer.no_printers_title"), tr("explorer.no_printers_msg"))
            return
        if not self.cfg.get("ssh_password"):
            QMessageBox.warning(self, tr("explorer.no_password_title"), tr("explorer.no_password_msg"))
            return

        self.connect_btn.setEnabled(False)
        self.log_view.appendPlainText(tr("explorer.connecting_log", name=printer_cfg['name']))

        self.list_worker = ExplorerListWorker(printer_cfg, self.cfg, self.cfg["ssh_password"])
        self.list_worker.finished_ok.connect(self._on_files_loaded)
        self.list_worker.finished_err.connect(self._on_error)
        self.list_worker.log_line.connect(lambda p, lvl, msg: self.log_view.appendPlainText(f"[{lvl}] {msg}"))
        self.list_worker.start()

    def _on_files_loaded(self, files):
        self.connect_btn.setEnabled(True)
        self.current_files = files
        self.log_view.appendPlainText(tr("explorer.files_found_log", count=len(files)))
        self._render_current_folder()

    def _on_error(self, msg):
        self.connect_btn.setEnabled(True)
        self.log_view.appendPlainText(f"[ERR] {msg}")
        QMessageBox.warning(self, tr("explorer.error_title"), msg)

    def _navigate_to(self, path):
        self.current_path = path
        self._render_current_folder()

    # ------------------------------------------------------------------
    # Breadcrumb
    # ------------------------------------------------------------------

    def _render_breadcrumb(self):
        while self.breadcrumb_row.count():
            item = self.breadcrumb_row.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        home_btn = QPushButton(tr("explorer.home_breadcrumb"))
        home_btn.setIcon(icons.get_icon("home", MUTED if self.current_path else ACCENT, 15))
        home_btn.setFlat(True)
        home_btn.setCursor(Qt.PointingHandCursor)
        home_btn.clicked.connect(lambda: self._navigate_to(""))
        self.breadcrumb_row.addWidget(home_btn)

        parts = self.current_path.split("/") if self.current_path else []
        accumulated = ""
        for i, part in enumerate(parts):
            chevron = QLabel()
            chevron.setPixmap(icons.get_icon("chevron_right", MUTED, 14).pixmap(14, 14))
            self.breadcrumb_row.addWidget(chevron)

            accumulated = f"{accumulated}/{part}" if accumulated else part
            is_last = (i == len(parts) - 1)
            btn = QPushButton(part)
            btn.setFlat(True)
            if is_last:
                btn.setEnabled(False)
                btn.setStyleSheet(f"color: {ACCENT}; font-weight: 600; border: none;")
            else:
                btn.setCursor(Qt.PointingHandCursor)
                target = accumulated
                btn.clicked.connect(lambda _checked=False, t=target: self._navigate_to(t))
            self.breadcrumb_row.addWidget(btn)

        self.breadcrumb_row.addStretch()

    # ------------------------------------------------------------------
    # Render de la carpeta actual
    # ------------------------------------------------------------------

    def _compute_children(self):
        prefix = f"{self.current_path}/" if self.current_path else ""
        folder_names = set()
        file_entries = []
        for f in self.current_files:
            rel = f["rel_path"]
            if not rel.startswith(prefix):
                continue
            remainder = rel[len(prefix):]
            if not remainder:
                continue
            parts = remainder.split("/")
            if ".thumbs" in parts:
                continue
            if len(parts) > 1:
                folder_names.add(parts[0])
            else:
                file_entries.append(f)
        return sorted(folder_names), sorted(file_entries, key=lambda f: f["rel_path"].lower())

    def _folder_mtime(self, folder_rel_path):
        prefix = f"{folder_rel_path}/"
        mtimes = [f["mtime"] for f in self.current_files
                  if f["rel_path"].startswith(prefix) and not f["is_thumb"]]
        return max(mtimes) if mtimes else 0

    def _render_current_folder(self):
        self.generation += 1
        gen = self.generation
        self._render_breadcrumb()

        folder_names, file_entries = self._compute_children()

        self.table.setRowCount(0)
        self.row_entries = []
        self.row_by_relpath = {}

        default_file_icon = icons.get_icon("gcode_file", ACCENT, THUMB_ICON_SIZE)
        folder_icon = icons.get_icon("folder", "#FFC107", THUMB_ICON_SIZE)

        for folder_name in folder_names:
            folder_rel = f"{self.current_path}/{folder_name}" if self.current_path else folder_name
            row = self.table.rowCount()
            self.table.insertRow(row)
            self._set_checkbox_cell(row)
            name_item = QTableWidgetItem(folder_icon, folder_name)
            name_item.setToolTip(folder_name)
            self.table.setItem(row, 1, name_item)
            self.table.setItem(row, 2, QTableWidgetItem(_fmt_mtime(self._folder_mtime(folder_rel))))
            self.row_entries.append({"type": "folder", "rel_path": folder_rel, "protected": False})

        thumb_jobs = []
        all_rel_paths = [f["rel_path"] for f in self.current_files]

        for f in file_entries:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self._set_checkbox_cell(row)

            base_icon_pixmap = default_file_icon.pixmap(THUMB_ICON_SIZE, THUMB_ICON_SIZE)
            if f["protected"]:
                base_icon_pixmap = icons.compose_badge(base_icon_pixmap)

            display_name = f["rel_path"].rsplit("/", 1)[-1]
            name_item = QTableWidgetItem(QIcon(base_icon_pixmap), display_name)
            tooltip = f"{display_name}\n{fmt_size(f['size'])} · {_fmt_mtime(f['mtime'])}"
            if f["protected"]:
                tooltip += f"\n{tr('explorer.in_use_tooltip')}"
            name_item.setToolTip(tooltip)
            self.table.setItem(row, 1, name_item)
            self.table.setItem(row, 2, QTableWidgetItem(_fmt_mtime(f["mtime"])))

            self.row_entries.append({"type": "file", "rel_path": f["rel_path"], "protected": f["protected"]})
            self.row_by_relpath[f["rel_path"]] = row

            candidates = find_thumbnails(f["rel_path"], all_rel_paths)
            if candidates:
                thumb_jobs.append({
                    "gcode_rel_path": f["rel_path"],
                    "icon_rel": candidates[0],
                    "preview_rel": candidates[-1],
                })

        self.count_label.setText(tr("explorer.count_label", folders=len(folder_names), files=len(file_entries)))

        if thumb_jobs:
            self._start_thumbnail_worker(thumb_jobs, gen)

    def _set_checkbox_cell(self, row):
        chk_item = QTableWidgetItem()
        chk_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        chk_item.setCheckState(Qt.Unchecked)
        self.table.setItem(row, 0, chk_item)

    # ------------------------------------------------------------------
    # Thumbnails
    # ------------------------------------------------------------------

    def _start_thumbnail_worker(self, jobs, gen):
        printer_cfg = self._current_printer_cfg()
        if not printer_cfg:
            return
        self.thumb_worker = ThumbnailWorker(printer_cfg, self.cfg, self.cfg["ssh_password"], jobs)
        self.thumb_worker.thumbnail_ready.connect(
            lambda rel, icon_b, prev_b: self._on_thumbnail_ready(gen, rel, icon_b, prev_b))
        self.thumb_worker.start()

    def _on_thumbnail_ready(self, gen, rel_path, icon_bytes, preview_bytes):
        if gen != self.generation:
            return
        row = self.row_by_relpath.get(rel_path)
        if row is None:
            return

        entry = self.row_entries[row]
        name_item = self.table.item(row, 1)
        if name_item is None:
            return

        source_bytes = icon_bytes or preview_bytes
        if source_bytes:
            pm = QPixmap()
            pm.loadFromData(source_bytes)
            if not pm.isNull():
                pm = pm.scaled(THUMB_ICON_SIZE, THUMB_ICON_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                canvas = QPixmap(THUMB_ICON_SIZE, THUMB_ICON_SIZE)
                canvas.fill(Qt.transparent)
                painter = QPainter(canvas)
                painter.drawPixmap((THUMB_ICON_SIZE - pm.width()) // 2, (THUMB_ICON_SIZE - pm.height()) // 2, pm)
                painter.end()
                if entry["protected"]:
                    canvas = icons.compose_badge(canvas)
                name_item.setIcon(QIcon(canvas))

        preview_source = preview_bytes or icon_bytes
        if preview_source:
            preview_pm = QPixmap()
            preview_pm.loadFromData(preview_source)
            if not preview_pm.isNull():
                preview_pm = preview_pm.scaledToWidth(PREVIEW_WIDTH, Qt.SmoothTransformation)
                b64 = icons.pixmap_to_data_uri(preview_pm)
                name = rel_path.rsplit("/", 1)[-1]
                html = (f'<div style="text-align:center; padding:2px;">'
                        f'<img src="data:image/png;base64,{b64}"/><br/>'
                        f'<span>{name}</span></div>')
                name_item.setToolTip(html)

    # ------------------------------------------------------------------
    # Interaccion
    # ------------------------------------------------------------------

    def _on_cell_double_clicked(self, row, _col):
        entry = self.row_entries[row] if row < len(self.row_entries) else None
        if entry and entry["type"] == "folder":
            self._navigate_to(entry["rel_path"])

    def _set_all_checked(self, checked):
        state = Qt.Checked if checked else Qt.Unchecked
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item:
                item.setCheckState(state)

    def _delete_selected(self):
        printer_cfg = self._current_printer_cfg()
        if not printer_cfg:
            return

        checked_rows = [row for row in range(self.table.rowCount())
                         if self.table.item(row, 0) and self.table.item(row, 0).checkState() == Qt.Checked]
        if not checked_rows:
            QMessageBox.information(self, tr("explorer.nothing_checked_title"), tr("explorer.nothing_checked_msg"))
            return

        rel_paths_to_delete = []
        protected_skipped = []
        folders_selected = 0

        for row in checked_rows:
            entry = self.row_entries[row]
            if entry["type"] == "folder":
                folders_selected += 1
                prefix = f"{entry['rel_path']}/"
                for f in self.current_files:
                    if not f["rel_path"].startswith(prefix):
                        continue
                    if f["protected"]:
                        protected_skipped.append(f["rel_path"])
                    else:
                        rel_paths_to_delete.append(f["rel_path"])
            else:
                if entry["protected"]:
                    protected_skipped.append(entry["rel_path"])
                else:
                    rel_paths_to_delete.append(entry["rel_path"])

        if protected_skipped:
            QMessageBox.information(
                self, tr("explorer.protected_files_title"),
                tr("explorer.protected_files_msg", list="\n".join(protected_skipped)))

        if not rel_paths_to_delete:
            return

        extra = tr("explorer.folders_extra", count=folders_selected) if folders_selected else ""
        resp = QMessageBox.question(
            self, tr("explorer.confirm_delete_title"),
            tr("explorer.confirm_delete_msg", count=len(rel_paths_to_delete), printer=printer_cfg['name'], extra=extra))
        if resp != QMessageBox.Yes:
            return

        self.delete_btn.setEnabled(False)
        self.delete_worker = ExplorerDeleteWorker(printer_cfg, self.cfg, self.cfg["ssh_password"], rel_paths_to_delete)
        self.delete_worker.log_line.connect(lambda p, lvl, msg: self.log_view.appendPlainText(f"[{lvl}] {msg}"))
        self.delete_worker.finished_ok.connect(self._on_delete_finished)
        self.delete_worker.finished_err.connect(self._on_error)
        self.delete_worker.start()

    def _on_delete_finished(self, deleted, errors):
        self.delete_btn.setEnabled(True)
        self.log_view.appendPlainText(tr("explorer.deleted_summary_log", deleted=len(deleted), errors=len(errors)))
        for rel_path, err in errors:
            self.log_view.appendPlainText(f"[ERR] {rel_path}: {err}")
        self._load_files()
