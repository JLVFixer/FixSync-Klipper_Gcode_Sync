"""
printers_page.py

CRUD completo de impresoras, con textos traducibles vía core.i18n.tr().
El método retranslate() se llama cuando el usuario cambia el idioma en
Configuración, para refrescar todos los textos ya construidos.
"""

import ipaddress
import re

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QDialog, QFormLayout, QLineEdit,
    QSpinBox, QDialogButtonBox, QMessageBox, QAbstractItemView, QFrame,
)

from core import store, icons
from core.i18n import tr


def _valid_host(host: str) -> bool:
    if not host:
        return False
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        pass
    return bool(re.match(r"^[a-zA-Z0-9.\-]+$", host))


class PrinterDialog(QDialog):
    def __init__(self, cfg, printer=None, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.original_name = printer["name"] if printer else None
        self.setWindowTitle(tr("dialog.edit_title") if printer else tr("dialog.add_title"))
        self.setMinimumWidth(380)

        form = QFormLayout()
        self.name_edit = QLineEdit(printer.get("name", "") if printer else "")
        self.host_edit = QLineEdit(printer.get("host", "") if printer else "")
        self.ssh_port_spin = QSpinBox()
        self.ssh_port_spin.setRange(1, 65535)
        self.ssh_port_spin.setValue(printer.get("ssh_port", cfg.get("ssh_port", 22)) if printer else cfg.get("ssh_port", 22))
        self.moonraker_port_spin = QSpinBox()
        self.moonraker_port_spin.setRange(1, 65535)
        self.moonraker_port_spin.setValue(
            printer.get("moonraker_port", cfg.get("moonraker_port", 7125)) if printer else cfg.get("moonraker_port", 7125))
        self.remote_path_edit = QLineEdit(
            printer.get("remote_gcodes_path", cfg.get("remote_gcodes_path", "")) if printer
            else cfg.get("remote_gcodes_path", ""))

        form.addRow(tr("dialog.name_label"), self.name_edit)
        form.addRow(tr("dialog.host_label"), self.host_edit)
        form.addRow(tr("dialog.ssh_port_label"), self.ssh_port_spin)
        form.addRow(tr("dialog.moonraker_port_label"), self.moonraker_port_spin)
        form.addRow(tr("dialog.remote_path_label"), self.remote_path_edit)

        hint = QLabel(tr("dialog.hint"))
        hint.setObjectName("subtitle")
        hint.setWordWrap(True)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(hint)
        layout.addWidget(buttons)

        self.result_printer = None

    def _on_accept(self):
        name = self.name_edit.text().strip()
        host = self.host_edit.text().strip()

        if not name:
            QMessageBox.warning(self, tr("dialog.missing_name_title"), tr("dialog.missing_name_msg"))
            return
        if not _valid_host(host):
            QMessageBox.warning(self, tr("dialog.invalid_host_title"), tr("dialog.invalid_host_msg"))
            return

        printer = {"name": name, "host": host}

        global_ssh_port = self.cfg.get("ssh_port", 22)
        if self.ssh_port_spin.value() != global_ssh_port:
            printer["ssh_port"] = self.ssh_port_spin.value()

        global_moonraker_port = self.cfg.get("moonraker_port", 7125)
        if self.moonraker_port_spin.value() != global_moonraker_port:
            printer["moonraker_port"] = self.moonraker_port_spin.value()

        remote_path = self.remote_path_edit.text().strip()
        global_remote_path = self.cfg.get("remote_gcodes_path", "")
        if remote_path and remote_path != global_remote_path:
            printer["remote_gcodes_path"] = remote_path

        self.result_printer = printer
        self.accept()


class PrintersPage(QWidget):
    printers_changed = Signal()

    def __init__(self, cfg, parent=None):
        super().__init__(parent)
        self.cfg = cfg

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        self.title = QLabel()
        self.title.setObjectName("title")
        self.subtitle = QLabel()
        self.subtitle.setObjectName("subtitle")
        layout.addWidget(self.title)
        layout.addWidget(self.subtitle)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)

        btn_row = QHBoxLayout()
        self.add_btn = QPushButton()
        self.add_btn.setIcon(icons.get_icon("plus", "#FFFFFF", 14))
        self.add_btn.setObjectName("primary")
        self.edit_btn = QPushButton()
        self.edit_btn.setIcon(icons.get_icon("edit", "#B8B8B8", 14))
        self.delete_btn = QPushButton()
        self.delete_btn.setIcon(icons.get_icon("trash", "#E53935", 14))
        self.delete_btn.setObjectName("danger")
        self.up_btn = QPushButton()
        self.up_btn.setIcon(icons.get_icon("arrow_up", "#B8B8B8", 14))
        self.down_btn = QPushButton()
        self.down_btn.setIcon(icons.get_icon("arrow_down", "#B8B8B8", 14))
        for b in (self.add_btn, self.edit_btn, self.delete_btn, self.up_btn, self.down_btn):
            btn_row.addWidget(b)
        btn_row.addStretch()
        card_layout.addLayout(btn_row)

        self.table = QTableWidget(0, 5)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        card_layout.addWidget(self.table)

        layout.addWidget(card)

        self.add_btn.clicked.connect(self._on_add)
        self.edit_btn.clicked.connect(self._on_edit)
        self.delete_btn.clicked.connect(self._on_delete)
        self.up_btn.clicked.connect(lambda: self._move(-1))
        self.down_btn.clicked.connect(lambda: self._move(1))
        self.table.itemDoubleClicked.connect(lambda _item: self._on_edit())

        self.retranslate()
        self.refresh()

    def retranslate(self):
        self.title.setText(tr("printers.title"))
        self.subtitle.setText(tr("printers.subtitle"))
        self.add_btn.setText(tr("printers.add_btn"))
        self.edit_btn.setText(tr("printers.edit_btn"))
        self.delete_btn.setText(tr("printers.delete_btn"))
        self.up_btn.setText(tr("printers.up_btn"))
        self.down_btn.setText(tr("printers.down_btn"))
        self.table.setHorizontalHeaderLabels([
            tr("printers.col_name"), tr("printers.col_host"),
            tr("printers.col_ssh_port"), tr("printers.col_moonraker_port"),
            tr("printers.col_remote_path"),
        ])

    def refresh(self):
        self.table.setRowCount(0)
        for printer in self.cfg["printers"]:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(printer["name"]))
            self.table.setItem(row, 1, QTableWidgetItem(printer["host"]))
            self.table.setItem(row, 2, QTableWidgetItem(str(printer.get("ssh_port", self.cfg.get("ssh_port", 22)))))
            self.table.setItem(row, 3, QTableWidgetItem(str(printer.get("moonraker_port", self.cfg.get("moonraker_port", 7125)))))
            self.table.setItem(row, 4, QTableWidgetItem(printer.get("remote_gcodes_path", self.cfg.get("remote_gcodes_path", ""))))

    def _selected_printer_name(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        return self.table.item(row, 0).text()

    def _on_add(self):
        dlg = PrinterDialog(self.cfg, parent=self)
        if dlg.exec() == QDialog.Accepted and dlg.result_printer:
            try:
                store.add_printer(self.cfg, dlg.result_printer)
            except store.DuplicateNameError as e:
                QMessageBox.warning(self, tr("printers.cant_add_title"), tr("printers.duplicate_name_msg", name=e.name))
                return
            self.refresh()
            self.printers_changed.emit()

    def _on_edit(self):
        name = self._selected_printer_name()
        if not name:
            QMessageBox.information(self, tr("printers.select_first_title"), tr("printers.select_first_msg"))
            return
        printer = next(p for p in self.cfg["printers"] if p["name"] == name)
        dlg = PrinterDialog(self.cfg, printer=printer, parent=self)
        if dlg.exec() == QDialog.Accepted and dlg.result_printer:
            try:
                store.update_printer(self.cfg, name, dlg.result_printer)
            except store.DuplicateNameError as e:
                QMessageBox.warning(self, tr("printers.cant_save_title"), tr("printers.duplicate_name_msg", name=e.name))
                return
            except store.PrinterNotFoundError as e:
                QMessageBox.warning(self, tr("printers.cant_save_title"), tr("printers.not_found_msg", name=e.name))
                return
            self.refresh()
            self.printers_changed.emit()

    def _on_delete(self):
        name = self._selected_printer_name()
        if not name:
            QMessageBox.information(self, tr("printers.select_first_title"), tr("printers.select_first_msg"))
            return
        resp = QMessageBox.question(
            self, tr("printers.confirm_delete_title"), tr("printers.confirm_delete_msg", name=name))
        if resp == QMessageBox.Yes:
            store.delete_printer(self.cfg, name)
            self.refresh()
            self.printers_changed.emit()

    def _move(self, direction):
        name = self._selected_printer_name()
        if not name:
            return
        store.move_printer(self.cfg, name, direction)
        self.refresh()
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).text() == name:
                self.table.selectRow(row)
                break
        self.printers_changed.emit()
