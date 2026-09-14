"""
sync_page.py

Pantalla principal de sincronización, con textos traducibles vía
core.i18n.tr(). retranslate() refresca los textos estáticos cuando el
usuario cambia el idioma; el log y los estados en curso quedan en el
idioma en que se generaron (no se re-traducen retroactivamente).
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QCheckBox,
    QFileDialog, QLineEdit, QFrame, QPlainTextEdit, QProgressBar,
    QScrollArea, QMessageBox, QGridLayout,
)
from PySide6.QtGui import QTextCursor

from core import store, icons
from core.i18n import tr
from gui.workers import SyncWorker

LEVEL_COLORS = {
    "INFO": "#B0B0B0",
    "OK": "#4CAF50",
    "WARN": "#FFB300",
    "ERR": "#EF5350",
}


class PrinterStatusRow(QFrame):
    def __init__(self, name):
        super().__init__()
        self.setObjectName("card")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        self.name_label = QLabel(name)
        self.name_label.setMinimumWidth(90)
        self.status_label = QLabel(tr("sync.waiting_status"))
        self.status_label.setObjectName("subtitle")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(True)
        layout.addWidget(self.name_label)
        layout.addWidget(self.progress, 1)
        layout.addWidget(self.status_label, 1)

    def set_status(self, text):
        self.status_label.setText(text)

    def set_progress(self, pct):
        self.progress.setValue(int(pct))


class SyncPage(QWidget):
    def __init__(self, cfg, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.worker = None
        self.printer_rows = {}
        self.printer_checks = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(14)

        self.title = QLabel()
        self.title.setObjectName("title")
        self.subtitle = QLabel()
        self.subtitle.setObjectName("subtitle")
        root.addWidget(self.title)
        root.addWidget(self.subtitle)

        # --- Carpeta local ---
        folder_card = QFrame()
        folder_card.setObjectName("card")
        folder_layout = QHBoxLayout(folder_card)
        folder_layout.setContentsMargins(14, 12, 14, 12)
        self.folder_label = QLabel()
        folder_layout.addWidget(self.folder_label)
        self.folder_edit = QLineEdit(cfg.get("local_gcodes_dir", ""))
        self.folder_edit.setReadOnly(True)
        folder_layout.addWidget(self.folder_edit, 1)
        self.choose_btn = QPushButton()
        self.choose_btn.clicked.connect(self._choose_folder)
        folder_layout.addWidget(self.choose_btn)
        root.addWidget(folder_card)

        # --- Selección de impresoras + opciones ---
        options_card = QFrame()
        options_card.setObjectName("card")
        options_layout = QVBoxLayout(options_card)
        options_layout.setContentsMargins(14, 12, 14, 12)

        header_row = QHBoxLayout()
        self.printers_label = QLabel()
        header_row.addWidget(self.printers_label)
        header_row.addStretch()
        self.dry_run_check = QCheckBox()
        header_row.addWidget(self.dry_run_check)
        options_layout.addLayout(header_row)

        self.printers_grid = QGridLayout()
        options_layout.addLayout(self.printers_grid)
        root.addWidget(options_card)

        # --- Botones de acción ---
        action_row = QHBoxLayout()
        self.start_btn = QPushButton()
        self.start_btn.setIcon(icons.get_icon("play", "#FFFFFF", 14))
        self.start_btn.setObjectName("primary")
        self.start_btn.clicked.connect(self._start_sync)
        self.cancel_btn = QPushButton()
        self.cancel_btn.setIcon(icons.get_icon("stop", "#B8B8B8", 14))
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._cancel_sync)
        action_row.addWidget(self.start_btn)
        action_row.addWidget(self.cancel_btn)
        action_row.addStretch()
        root.addLayout(action_row)

        # --- Estado por impresora ---
        self.status_container = QVBoxLayout()
        status_scroll_widget = QWidget()
        status_scroll_widget.setLayout(self.status_container)
        status_scroll = QScrollArea()
        status_scroll.setWidgetResizable(True)
        status_scroll.setMaximumHeight(160)
        status_scroll.setWidget(status_scroll_widget)
        root.addWidget(status_scroll)

        # --- Log ---
        self.log_label = QLabel()
        self.log_label.setObjectName("accentLabel")
        root.addWidget(self.log_label)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        root.addWidget(self.log_view, 1)

        self.retranslate()
        self.refresh_printers()

    # ------------------------------------------------------------------

    def retranslate(self):
        self.title.setText(tr("sync.title"))
        self.subtitle.setText(tr("sync.subtitle"))
        self.folder_label.setText(tr("sync.local_folder_label"))
        self.choose_btn.setText(tr("sync.choose_folder_btn"))
        self.printers_label.setText(tr("sync.printers_label"))
        self.dry_run_check.setText(tr("sync.dry_run_label"))
        self.start_btn.setText(tr("sync.start_btn"))
        self.cancel_btn.setText(tr("sync.cancel_btn"))
        self.log_label.setText(tr("sync.log_label"))
        for row in self.printer_rows.values():
            if row.progress.value() == 0:
                row.set_status(tr("sync.waiting_status"))

    def refresh_printers(self):
        while self.printers_grid.count():
            item = self.printers_grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        while self.status_container.count():
            item = self.status_container.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        self.printer_checks = {}
        self.printer_rows = {}
        for i, printer in enumerate(self.cfg["printers"]):
            chk = QCheckBox(printer["name"])
            chk.setChecked(True)
            self.printers_grid.addWidget(chk, i // 4, i % 4)
            self.printer_checks[printer["name"]] = chk

            row = PrinterStatusRow(printer["name"])
            self.status_container.addWidget(row)
            self.printer_rows[printer["name"]] = row

    def _choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, tr("sync.choose_folder_btn"), self.folder_edit.text())
        if folder:
            self.folder_edit.setText(folder)
            self.cfg["local_gcodes_dir"] = folder
            store.save_config(self.cfg)

    def _append_log(self, printer_name, level, msg):
        color = LEVEL_COLORS.get(level, "#B0B0B0")
        tag = f"[{printer_name}] " if printer_name else ""
        html = f'<span style="color:{color}">{tag}{msg}</span>'
        self.log_view.appendHtml(html)
        self.log_view.moveCursor(QTextCursor.End)

    def _start_sync(self):
        if not self.cfg.get("local_gcodes_dir"):
            QMessageBox.warning(self, tr("sync.no_folder_title"), tr("sync.no_folder_msg"))
            return
        if not self.cfg.get("ssh_password"):
            QMessageBox.warning(self, tr("sync.no_password_title"), tr("sync.no_password_msg"))
            return

        selected = [p for p in self.cfg["printers"] if self.printer_checks.get(p["name"], None) and
                    self.printer_checks[p["name"]].isChecked()]
        if not selected:
            QMessageBox.information(self, tr("sync.nothing_selected_title"), tr("sync.nothing_selected_msg"))
            return

        self.log_view.clear()
        for row in self.printer_rows.values():
            row.set_progress(0)
            row.set_status(tr("sync.waiting_status"))

        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)

        self.worker = SyncWorker(self.cfg, selected, self.cfg["ssh_password"], self.dry_run_check.isChecked())
        self.worker.log_line.connect(self._append_log)
        self.worker.printer_progress.connect(self._on_progress)
        self.worker.printer_finished.connect(self._on_printer_finished)
        self.worker.all_finished.connect(self._on_all_finished)
        self.worker.start()

    def _cancel_sync(self):
        if self.worker:
            self.worker.cancel()
            self._append_log("", "WARN", tr("sync.cancelling_log"))
            self.cancel_btn.setEnabled(False)

    def _on_progress(self, printer_name, kind, idx, total, extra):
        row = self.printer_rows.get(printer_name)
        if not row:
            return
        if kind == "upload":
            pct = extra.get("pct", 0)
            row.set_progress(pct)
            row.set_status(tr("sync.uploading_status", idx=idx, total=total,
                               rel_path=extra.get("rel_path", ""), speed=extra.get("speed", 0)))
        elif kind == "delete":
            row.set_status(tr("sync.deleting_status", idx=idx, total=total, rel_path=extra.get("rel_path", "")))

    def _on_printer_finished(self, res):
        row = self.printer_rows.get(res.get("name"))
        if not row:
            return
        if res["status"] == "skipped":
            row.set_status(tr("sync.skipped_status", reason=res.get("reason", "")))
        elif res["status"] == "cancelled":
            row.set_status(tr("sync.cancelled_status"))
        else:
            row.set_progress(100)
            row.set_status(tr(
                "sync.ok_status",
                uploaded=len(res.get("uploaded", [])),
                deleted=len(res.get("deleted", [])),
                protected=len(res.get("skipped_protected", [])),
                errors=len(res.get("file_errors", [])),
            ))

    def _on_all_finished(self, results, changes_to_review):
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self._append_log("", "OK", tr("sync.finished_log"))
        if changes_to_review:
            self._append_log("", "WARN", tr("sync.review_log", count=len(changes_to_review)))
            for printer_name, rel_path in changes_to_review:
                self._append_log(printer_name, "WARN", f"   {rel_path}")
