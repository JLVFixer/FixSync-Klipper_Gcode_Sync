"""
settings_page.py

Configuración global: idioma, credenciales SSH, defaults y
personalización de estética. Emite settings_changed cuando se guarda,
para que la ventana principal aplique el nuevo idioma/tema a toda la
app sin tener que reiniciarla.
"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QSpinBox, QFrame, QFormLayout, QCheckBox, QColorDialog, QMessageBox,
    QComboBox,
)
from PySide6.QtGui import QColor

from core import store
from core.i18n import tr, set_language, get_language

LANGUAGES = [("es", "Español"), ("en", "English")]


class ColorSwatchButton(QPushButton):
    color_changed = Signal(str)

    def __init__(self, color_hex, parent=None):
        super().__init__(parent)
        self.color_hex = color_hex
        self.setFixedSize(36, 28)
        self._apply_color()
        self.clicked.connect(self._pick_color)

    def _apply_color(self):
        self.setStyleSheet(f"background-color: {self.color_hex}; border-radius: 4px; border: 1px solid #444;")

    def _pick_color(self):
        color = QColorDialog.getColor(QColor(self.color_hex), self, "Color")
        if color.isValid():
            self.color_hex = color.name().upper()
            self._apply_color()
            self.color_changed.emit(self.color_hex)


class SettingsPage(QWidget):
    theme_changed = Signal()
    settings_changed = Signal()

    def __init__(self, cfg, settings, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.settings = settings

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(14)

        self.title = QLabel()
        self.title.setObjectName("title")
        self.subtitle = QLabel()
        self.subtitle.setObjectName("subtitle")
        root.addWidget(self.title)
        root.addWidget(self.subtitle)

        # --- Idioma ---
        lang_card = QFrame()
        lang_card.setObjectName("card")
        lang_form = QFormLayout(lang_card)
        lang_form.setContentsMargins(16, 16, 16, 16)
        self.language_label = QLabel()
        self.language_combo = QComboBox()
        for code, label in LANGUAGES:
            self.language_combo.addItem(label, code)
        idx = self.language_combo.findData(settings.get("language", "es"))
        if idx >= 0:
            self.language_combo.setCurrentIndex(idx)
        lang_form.addRow(self.language_label, self.language_combo)
        root.addWidget(lang_card)

        # --- SSH / conexión ---
        ssh_card = QFrame()
        ssh_card.setObjectName("card")
        ssh_form = QFormLayout(ssh_card)
        ssh_form.setContentsMargins(16, 16, 16, 16)

        self.user_edit = QLineEdit(cfg.get("ssh_user", ""))
        self.password_edit = QLineEdit(cfg.get("ssh_password", ""))
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.show_pass_check = QCheckBox()
        self.show_pass_check.toggled.connect(
            lambda checked: self.password_edit.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password))
        pass_row = QHBoxLayout()
        pass_row.addWidget(self.password_edit)
        pass_row.addWidget(self.show_pass_check)

        self.remote_path_edit = QLineEdit(cfg.get("remote_gcodes_path", ""))
        self.ssh_port_spin = QSpinBox()
        self.ssh_port_spin.setRange(1, 65535)
        self.ssh_port_spin.setValue(cfg.get("ssh_port", 22))
        self.moonraker_port_spin = QSpinBox()
        self.moonraker_port_spin.setRange(1, 65535)
        self.moonraker_port_spin.setValue(cfg.get("moonraker_port", 7125))

        self.user_label = QLabel()
        self.password_label = QLabel()
        self.remote_path_label = QLabel()
        self.ssh_port_label = QLabel()
        self.moonraker_port_label = QLabel()

        ssh_form.addRow(self.user_label, self.user_edit)
        ssh_form.addRow(self.password_label, pass_row)
        ssh_form.addRow(self.remote_path_label, self.remote_path_edit)
        ssh_form.addRow(self.ssh_port_label, self.ssh_port_spin)
        ssh_form.addRow(self.moonraker_port_label, self.moonraker_port_spin)

        self.password_warning = QLabel()
        self.password_warning.setObjectName("subtitle")
        self.password_warning.setWordWrap(True)
        ssh_form.addRow(self.password_warning)

        root.addWidget(ssh_card)

        # --- Tema ---
        theme_card = QFrame()
        theme_card.setObjectName("card")
        theme_form = QFormLayout(theme_card)
        theme_form.setContentsMargins(16, 16, 16, 16)

        self.accent_swatch = ColorSwatchButton(settings.get("accent_color", "#E53935"))
        self.bg_swatch = ColorSwatchButton(settings.get("background_color", "#121212"))
        self.surface_swatch = ColorSwatchButton(settings.get("surface_color", "#1C1C1C"))

        self.accent_label = QLabel()
        self.bg_label = QLabel()
        self.surface_label = QLabel()

        theme_form.addRow(self.accent_label, self.accent_swatch)
        theme_form.addRow(self.bg_label, self.bg_swatch)
        theme_form.addRow(self.surface_label, self.surface_swatch)

        self.reset_theme_btn = QPushButton()
        self.reset_theme_btn.clicked.connect(self._reset_theme)
        theme_form.addRow(self.reset_theme_btn)

        root.addWidget(theme_card)

        self.save_btn = QPushButton()
        self.save_btn.setObjectName("primary")
        self.save_btn.clicked.connect(self._save)
        root.addWidget(self.save_btn)
        root.addStretch()

        self.retranslate()

    def retranslate(self):
        self.title.setText(tr("settings.title"))
        self.subtitle.setText(tr("settings.subtitle"))
        self.language_label.setText(tr("settings.language_label"))
        self.user_label.setText(tr("settings.user_label"))
        self.password_label.setText(tr("settings.password_label"))
        self.show_pass_check.setText(tr("settings.show_password"))
        self.remote_path_label.setText(tr("settings.remote_path_label"))
        self.ssh_port_label.setText(tr("settings.ssh_port_label"))
        self.moonraker_port_label.setText(tr("settings.moonraker_port_label"))
        self.password_warning.setText(tr("settings.password_warning"))
        self.accent_label.setText(tr("settings.accent_label"))
        self.bg_label.setText(tr("settings.bg_label"))
        self.surface_label.setText(tr("settings.surface_label"))
        self.reset_theme_btn.setText(tr("settings.reset_theme_btn"))
        self.save_btn.setText(tr("settings.save_btn"))

    def _reset_theme(self):
        self.accent_swatch.color_hex = "#E53935"
        self.accent_swatch._apply_color()
        self.bg_swatch.color_hex = "#121212"
        self.bg_swatch._apply_color()
        self.surface_swatch.color_hex = "#1C1C1C"
        self.surface_swatch._apply_color()

    def _save(self):
        self.cfg["ssh_user"] = self.user_edit.text().strip()
        self.cfg["ssh_password"] = self.password_edit.text()
        self.cfg["remote_gcodes_path"] = self.remote_path_edit.text().strip()
        self.cfg["ssh_port"] = self.ssh_port_spin.value()
        self.cfg["moonraker_port"] = self.moonraker_port_spin.value()
        store.save_config(self.cfg)

        selected_lang = self.language_combo.currentData()
        language_changed = selected_lang != get_language()
        self.settings["language"] = selected_lang
        set_language(selected_lang)

        self.settings["accent_color"] = self.accent_swatch.color_hex
        self.settings["background_color"] = self.bg_swatch.color_hex
        self.settings["surface_color"] = self.surface_swatch.color_hex
        store.save_settings(self.settings)

        self.theme_changed.emit()
        self.settings_changed.emit()
        if language_changed:
            self.retranslate()
        QMessageBox.information(self, tr("settings.saved_title"), tr("settings.saved_msg"))
