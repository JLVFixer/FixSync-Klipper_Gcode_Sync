"""
theme.py

Genera el QSS (stylesheet de Qt) del tema oscuro/minimalista con color de
acento configurable (rojo por defecto). Todo se recalcula a partir del
diccionario de settings, asi que cambiar el color de acento en la UI
recompila el stylesheet entero y se aplica al instante.
"""


def _lighten(hex_color: str, amount: float) -> str:
    """Aclara un color hex un porcentaje (0.0-1.0) hacia blanco."""
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    r = int(r + (255 - r) * amount)
    g = int(g + (255 - g) * amount)
    b = int(b + (255 - b) * amount)
    return f"#{r:02X}{g:02X}{b:02X}"


def _darken(hex_color: str, amount: float) -> str:
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    r = int(r * (1 - amount))
    g = int(g * (1 - amount))
    b = int(b * (1 - amount))
    return f"#{r:02X}{g:02X}{b:02X}"


def build_stylesheet(settings: dict) -> str:
    accent = settings.get("accent_color", "#E53935")
    bg = settings.get("background_color", "#121212")
    surface = settings.get("surface_color", "#1C1C1C")
    text = settings.get("text_color", "#E8E8E8")

    accent_hover = _lighten(accent, 0.15)
    accent_pressed = _darken(accent, 0.15)
    border = _lighten(surface, 0.15)
    surface_alt = _lighten(surface, 0.06)
    disabled_text = _lighten(text, -0.4) if False else "#7A7A7A"

    return f"""
    * {{
        font-family: "Segoe UI", "Inter", sans-serif;
        font-size: 13px;
        color: {text};
        outline: none;
    }}

    QMainWindow, QWidget#centralWidget {{
        background-color: {bg};
    }}

    QWidget {{
        background-color: transparent;
    }}

    /* --- Sidebar --- */
    QWidget#sidebar {{
        background-color: {surface};
        border-right: 1px solid {border};
    }}
    QListWidget#navList {{
        background-color: transparent;
        border: none;
        padding: 8px 0px;
    }}
    QListWidget#navList::item {{
        padding: 12px 20px;
        border-left: 3px solid transparent;
        margin: 2px 0px;
    }}
    QListWidget#navList::item:selected {{
        background-color: {surface_alt};
        border-left: 3px solid {accent};
        color: {text};
    }}
    QListWidget#navList::item:hover:!selected {{
        background-color: {surface_alt};
    }}
    QWidget#sidebarFooter {{
        border-top: 1px solid {border};
    }}

    /* --- Paneles / tarjetas --- */
    QFrame#card, QGroupBox {{
        background-color: {surface};
        border: 1px solid {border};
        border-radius: 8px;
    }}
    QGroupBox {{
        margin-top: 14px;
        padding: 14px 10px 10px 10px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 6px;
        color: {accent};
        font-weight: 600;
    }}

    /* --- Botones --- */
    QPushButton {{
        background-color: {surface_alt};
        border: 1px solid {border};
        border-radius: 6px;
        padding: 8px 16px;
        color: {text};
    }}
    QPushButton:hover {{
        border: 1px solid {accent};
    }}
    QPushButton:pressed {{
        background-color: {border};
    }}
    QPushButton:disabled {{
        color: {disabled_text};
        border: 1px solid {border};
    }}
    QPushButton#primary {{
        background-color: {accent};
        border: 1px solid {accent};
        color: white;
        font-weight: 600;
    }}
    QPushButton#primary:hover {{
        background-color: {accent_hover};
        border: 1px solid {accent_hover};
    }}
    QPushButton#primary:pressed {{
        background-color: {accent_pressed};
    }}
    QPushButton#danger {{
        border: 1px solid {accent};
        color: {accent};
    }}
    QPushButton#danger:hover {{
        background-color: {accent};
        color: white;
    }}

    /* --- Inputs --- */
    QLineEdit, QSpinBox, QComboBox, QPlainTextEdit, QTextEdit {{
        background-color: {bg};
        border: 1px solid {border};
        border-radius: 6px;
        padding: 6px 8px;
        selection-background-color: {accent};
    }}
    QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{
        border: 1px solid {accent};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {surface};
        border: 1px solid {border};
        selection-background-color: {accent};
    }}

    /* --- Checkbox / radio --- */
    QCheckBox::indicator {{
        width: 16px; height: 16px;
        border: 1px solid {border};
        border-radius: 3px;
        background-color: {bg};
    }}
    QCheckBox::indicator:checked {{
        background-color: {accent};
        border: 1px solid {accent};
    }}

    /* --- Tablas --- */
    QTableWidget, QTreeWidget {{
        background-color: {surface};
        border: 1px solid {border};
        border-radius: 8px;
        gridline-color: {border};
        alternate-background-color: {surface_alt};
    }}
    QHeaderView::section {{
        background-color: {surface_alt};
        color: {text};
        padding: 8px;
        border: none;
        border-bottom: 1px solid {border};
        font-weight: 600;
    }}
    QTableWidget::item:selected, QTreeWidget::item:selected {{
        background-color: {accent};
        color: white;
    }}

    /* --- Barras de progreso --- */
    QProgressBar {{
        background-color: {bg};
        border: 1px solid {border};
        border-radius: 6px;
        text-align: center;
        color: {text};
        height: 18px;
    }}
    QProgressBar::chunk {{
        background-color: {accent};
        border-radius: 5px;
    }}

    /* --- Scrollbars minimalistas --- */
    QScrollBar:vertical {{
        background: {bg};
        width: 10px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {border};
        border-radius: 5px;
        min-height: 24px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {accent};
    }}
    QScrollBar::add-line, QScrollBar::sub-line {{
        height: 0px;
    }}

    /* --- Tabs --- */
    QTabWidget::pane {{
        border: 1px solid {border};
        border-radius: 8px;
    }}
    QTabBar::tab {{
        background: {surface};
        padding: 8px 16px;
        border: 1px solid {border};
        border-bottom: none;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
    }}
    QTabBar::tab:selected {{
        background: {surface_alt};
        border-bottom: 2px solid {accent};
    }}

    QLabel#title {{
        font-size: 18px;
        font-weight: 700;
        color: {text};
    }}
    QLabel#subtitle {{
        color: #9A9A9A;
    }}
    QLabel#accentLabel {{
        color: {accent};
        font-weight: 600;
    }}

    QSplitter::handle {{
        background-color: {border};
    }}

    QToolTip {{
        background-color: {surface_alt};
        color: {text};
        border: 1px solid {accent};
        padding: 4px;
    }}
    """
