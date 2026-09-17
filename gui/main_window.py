"""
main_window.py

Ventana principal: sidebar de navegación + páginas apiladas, más un pie
de página fijo abajo del todo con el logo y el crédito de diseño.

Al arrancar, aplica el idioma guardado en settings.json ANTES de crear
las páginas (para que nazcan ya traducidas). Cuando el usuario cambia
el idioma desde Configuración, se llama retranslate() en cascada sobre
el sidebar y cada página, sin necesidad de reiniciar la app.
"""

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QListWidget,
    QListWidgetItem, QStackedWidget, QLabel,
)

from core import store, theme, icons
from core.i18n import tr, set_language
from core.resources import resource_path
from gui.pages.sync_page import SyncPage
from gui.pages.printers_page import PrintersPage
from gui.pages.explorer_page import ExplorerPage
from gui.pages.settings_page import SettingsPage

NAV_KEYS = [
    ("sync", "nav.sync"),
    ("printer", "nav.printers"),
    ("folder_search", "nav.explorer"),
    ("settings", "nav.settings"),
]

SIDEBAR_WIDTH = 210
FOOTER_LOGO_MAX_SIZE = 170
HEADER_LOGO_MAX_WIDTH = 170
HEADER_LOGO_MAX_HEIGHT = 40


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.resize(1150, 740)

        self.cfg = store.load_config()
        self.settings = store.load_settings()
        set_language(self.settings.get("language", "es"))

        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        sidebar_container = QWidget()
        sidebar_container.setObjectName("sidebar")
        sidebar_container.setFixedWidth(SIDEBAR_WIDTH)
        sidebar_layout = QVBoxLayout(sidebar_container)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # --- Header (logo de la app) ---
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 20, 16, 20)
        header_layout.setAlignment(Qt.AlignHCenter)
        self.header_logo_label = QLabel()
        self.header_logo_label.setAlignment(Qt.AlignHCenter)
        self._header_logo_loaded = False
        self._load_header_logo()
        header_layout.addWidget(self.header_logo_label)
        sidebar_layout.addWidget(header)

        # --- Navegación ---
        self.sidebar = QListWidget()
        self.sidebar.setObjectName("navList")
        self.sidebar.setFrameShape(QListWidget.NoFrame)
        self.sidebar.setIconSize(QSize(18, 18))
        self._nav_icon_names = [icon_name for icon_name, _key in NAV_KEYS]
        for icon_name, key in NAV_KEYS:
            QListWidgetItem(icons.get_icon(icon_name, "#B8B8B8", 18), "", self.sidebar)
        self.sidebar.currentRowChanged.connect(self._on_nav_changed)
        sidebar_layout.addWidget(self.sidebar, 1)

        # --- Footer (logo Fixer Robotics arriba + crédito abajo) ---
        footer = QWidget()
        footer.setObjectName("sidebarFooter")
        footer_layout = QVBoxLayout(footer)
        footer_layout.setContentsMargins(16, 14, 16, 14)
        footer_layout.setSpacing(6)
        footer_layout.setAlignment(Qt.AlignHCenter)
        self.footer_logo_label = QLabel()
        self.footer_logo_label.setAlignment(Qt.AlignHCenter)
        self._load_footer_logo()
        footer_layout.addWidget(self.footer_logo_label, 0, Qt.AlignHCenter)
        self.footer_credit_label = QLabel()
        self.footer_credit_label.setObjectName("subtitle")
        self.footer_credit_label.setWordWrap(True)
        self.footer_credit_label.setAlignment(Qt.AlignHCenter)
        self.footer_credit_label.setStyleSheet("font-size: 10.5px;")
        footer_layout.addWidget(self.footer_credit_label)
        sidebar_layout.addWidget(footer)

        # --- Páginas ---
        self.stack = QStackedWidget()
        self.sync_page = SyncPage(self.cfg)
        self.printers_page = PrintersPage(self.cfg)
        self.explorer_page = ExplorerPage(self.cfg)
        self.settings_page = SettingsPage(self.cfg, self.settings)

        for page in (self.sync_page, self.printers_page, self.explorer_page, self.settings_page):
            self.stack.addWidget(page)

        layout.addWidget(sidebar_container)
        layout.addWidget(self.stack, 1)

        self.printers_page.printers_changed.connect(self.sync_page.refresh_printers)
        self.printers_page.printers_changed.connect(self.explorer_page.refresh_printer_list)
        self.settings_page.theme_changed.connect(self._apply_theme)
        self.settings_page.settings_changed.connect(self.retranslate_all)

        self.sidebar.setCurrentRow(0)
        self.retranslate_all()
        self._apply_theme()

    # ------------------------------------------------------------------

    def _load_scaled_logo(self, label, filename, max_width, max_height, fallback_text=None):
        """Carga un logo desde assets/ y lo escala para que entre en el
        espacio disponible sin recortarse ni deformarse (mantiene la
        relación de aspecto original). Si el archivo no existe todavía,
        muestra un texto de respaldo en vez de dejar el hueco vacío."""
        path = resource_path(f"assets/{filename}")
        pixmap = QPixmap(path)
        if pixmap.isNull():
            if fallback_text:
                label.setText(fallback_text)
                label.setStyleSheet("font-size: 15px; font-weight: 700;")
            return
        scaled = pixmap.scaled(
            max_width, max_height,
            Qt.KeepAspectRatio, Qt.SmoothTransformation,
        )
        label.setPixmap(scaled)
        label.setFixedSize(scaled.size())

    def _load_scaled_logo(self, label, filename, max_width, max_height, fallback_text=None):
        """Carga un logo desde assets/ y lo escala para que entre en el
        espacio disponible sin recortarse ni deformarse (mantiene la
        relación de aspecto original). Si el archivo no existe todavía,
        muestra un texto de respaldo en vez de dejar el hueco vacío."""
        path = resource_path(f"assets/{filename}")
        pixmap = QPixmap(path)
        if pixmap.isNull():
            if fallback_text:
                label.setText(fallback_text)
                label.setStyleSheet("font-size: 15px; font-weight: 700;")
            return False
        scaled = pixmap.scaled(
            max_width, max_height,
            Qt.KeepAspectRatio, Qt.SmoothTransformation,
        )
        label.setPixmap(scaled)
        label.setFixedSize(scaled.size())
        return True

    def _load_header_logo(self):
        self._header_logo_loaded = self._load_scaled_logo(
            self.header_logo_label, "FixSYNC.png",
            HEADER_LOGO_MAX_WIDTH, HEADER_LOGO_MAX_HEIGHT,
            fallback_text=tr("app.sidebar_name"),
        )

    def _load_footer_logo(self):
        self._load_scaled_logo(self.footer_logo_label, "fixer.png", FOOTER_LOGO_MAX_SIZE, FOOTER_LOGO_MAX_SIZE)

    def retranslate_all(self):
        self.setWindowTitle(tr("app.window_title"))
        if not self._header_logo_loaded:
            self.header_logo_label.setText(tr("app.sidebar_name"))
        self.footer_credit_label.setText(tr("app.footer_credit"))
        for i, (_icon_name, key) in enumerate(NAV_KEYS):
            self.sidebar.item(i).setText(f"  {tr(key)}")

        self.sync_page.retranslate()
        self.printers_page.retranslate()
        self.explorer_page.retranslate()
        self.settings_page.retranslate()

    def _on_nav_changed(self, index):
        self.stack.setCurrentIndex(index)
        if index == 0:
            self.sync_page.refresh_printers()
        elif index == 2:
            self.explorer_page.refresh_printer_list()
        self._recolor_nav_icons(index)

    def _recolor_nav_icons(self, active_index):
        accent = self.settings.get("accent_color", "#E53935")
        for i, icon_name in enumerate(self._nav_icon_names):
            color = accent if i == active_index else "#B8B8B8"
            self.sidebar.item(i).setIcon(icons.get_icon(icon_name, color, 18))

    def _apply_theme(self):
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        app.setStyleSheet(theme.build_stylesheet(self.settings))
        self._recolor_nav_icons(self.sidebar.currentRow())
