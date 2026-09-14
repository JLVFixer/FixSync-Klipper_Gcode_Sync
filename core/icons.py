"""
icons.py

Set de íconos vectoriales minimalistas, dibujados a mano con QPainter
(sin depender de archivos externos ni de recordar paths SVG de memoria).
Todos se generan en un grid de 24x24 y se escalan al tamaño pedido, con
el color que se les pase — así heredan el tema (texto, acento, etc) y
se pueden recolorear al vuelo si el usuario cambia el tema.
"""

import math

from PySide6.QtCore import Qt, QRectF, QPointF, QByteArray, QBuffer, QIODevice
from PySide6.QtGui import QIcon, QPixmap, QPainter, QPen, QColor, QPainterPath


def _canvas(size):
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.scale(size / 24.0, size / 24.0)
    return pm, p


def _pen(color, width=2.0):
    pen = QPen(QColor(color))
    pen.setWidthF(width)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    return pen


def _line(p, x1, y1, x2, y2):
    p.drawLine(QPointF(x1, y1), QPointF(x2, y2))


def icon_home(color, size=20):
    pm, p = _canvas(size)
    p.setPen(_pen(color))
    path = QPainterPath()
    path.moveTo(3, 11); path.lineTo(12, 3); path.lineTo(21, 11)
    p.drawPath(path)
    p.drawRect(QRectF(5.5, 11, 13, 9))
    _line(p, 10, 20, 10, 14)
    _line(p, 14, 20, 14, 14)
    p.end()
    return QIcon(pm)


def icon_chevron_right(color, size=16):
    pm, p = _canvas(size)
    p.setPen(_pen(color, 2.4))
    path = QPainterPath()
    path.moveTo(9, 5); path.lineTo(16, 12); path.lineTo(9, 19)
    p.drawPath(path)
    p.end()
    return QIcon(pm)


def icon_folder(color, size=20):
    pm, p = _canvas(size)
    p.setPen(_pen(color, 1.8))
    path = QPainterPath()
    path.moveTo(3, 6); path.lineTo(3, 19); path.lineTo(21, 19)
    path.lineTo(21, 8); path.lineTo(11, 8); path.lineTo(9, 6)
    path.closeSubpath()
    p.drawPath(path)
    p.end()
    return QIcon(pm)


def icon_gcode_file(color, size=20):
    """Ícono por defecto para un gcode sin thumbnail: un cubo isométrico
    (representa un modelo 3D) en el color de acento."""
    pm, p = _canvas(size)
    p.setPen(_pen(color, 1.6))
    top = QPainterPath()
    top.moveTo(12, 3); top.lineTo(20, 7); top.lineTo(12, 11); top.lineTo(4, 7)
    top.closeSubpath()
    p.drawPath(top)
    _line(p, 4, 7, 4, 16)
    _line(p, 20, 7, 20, 16)
    _line(p, 12, 11, 12, 20)
    _line(p, 4, 16, 12, 20)
    _line(p, 20, 16, 12, 20)
    p.end()
    return QIcon(pm)


def icon_clock(color, size=14):
    pm, p = _canvas(size)
    p.setPen(_pen(color, 2))
    p.drawEllipse(QRectF(3, 3, 18, 18))
    _line(p, 12, 12, 12, 7)
    _line(p, 12, 12, 16, 14)
    p.end()
    return QIcon(pm)


def icon_plus(color, size=18):
    pm, p = _canvas(size)
    p.setPen(_pen(color, 2.4))
    _line(p, 12, 4, 12, 20)
    _line(p, 4, 12, 20, 12)
    p.end()
    return QIcon(pm)


def icon_edit(color, size=18):
    pm, p = _canvas(size)
    p.setPen(_pen(color, 2))
    path = QPainterPath()
    path.moveTo(4, 20); path.lineTo(5, 16); path.lineTo(15, 6)
    path.lineTo(18, 9); path.lineTo(8, 19); path.closeSubpath()
    p.drawPath(path)
    _line(p, 15, 6, 18, 9)
    p.end()
    return QIcon(pm)


def icon_trash(color, size=18):
    pm, p = _canvas(size)
    p.setPen(_pen(color, 2))
    _line(p, 4, 7, 20, 7)
    _line(p, 9, 7, 9, 4)
    _line(p, 15, 7, 15, 4)
    _line(p, 9, 4, 15, 4)
    path = QPainterPath()
    path.moveTo(6, 7); path.lineTo(7, 21); path.lineTo(17, 21); path.lineTo(18, 7)
    p.drawPath(path)
    _line(p, 10, 11, 10, 17)
    _line(p, 14, 11, 14, 17)
    p.end()
    return QIcon(pm)


def icon_arrow(color, size=16, direction="up"):
    pm, p = _canvas(size)
    p.setPen(_pen(color, 2.2))
    if direction == "up":
        _line(p, 12, 19, 12, 5)
        _line(p, 6, 11, 12, 5)
        _line(p, 18, 11, 12, 5)
    else:
        _line(p, 12, 5, 12, 19)
        _line(p, 6, 13, 12, 19)
        _line(p, 18, 13, 12, 19)
    p.end()
    return QIcon(pm)


def icon_sync(color, size=20):
    pm, p = _canvas(size)
    p.setPen(_pen(color, 2))
    p.drawArc(QRectF(4, 4, 15, 15), 20 * 16, 300 * 16)
    _line(p, 18.5, 4, 18.5, 9)
    _line(p, 18.5, 9, 13.5, 9)
    p.drawArc(QRectF(5, 5, 15, 15), 200 * 16, 300 * 16)
    _line(p, 5.5, 20, 5.5, 15)
    _line(p, 5.5, 15, 10.5, 15)
    p.end()
    return QIcon(pm)


def icon_settings(color, size=20):
    pm, p = _canvas(size)
    p.setPen(_pen(color, 2))
    p.drawEllipse(QRectF(8.5, 8.5, 7, 7))
    for i in range(8):
        angle = math.radians(i * 45)
        x1, y1 = 12 + 7 * math.cos(angle), 12 + 7 * math.sin(angle)
        x2, y2 = 12 + 10 * math.cos(angle), 12 + 10 * math.sin(angle)
        _line(p, x1, y1, x2, y2)
    p.end()
    return QIcon(pm)


def icon_printer(color, size=20):
    pm, p = _canvas(size)
    p.setPen(_pen(color, 2))
    p.drawRect(QRectF(6, 3, 12, 6))
    p.drawRect(QRectF(4, 9, 16, 8))
    p.drawRect(QRectF(7, 15, 10, 6))
    p.end()
    return QIcon(pm)


def icon_folder_search(color, size=20):
    pm, p = _canvas(size)
    p.setPen(_pen(color, 1.8))
    path = QPainterPath()
    path.moveTo(3, 6); path.lineTo(3, 19); path.lineTo(14, 19); path.lineTo(14, 8)
    path.lineTo(11, 8); path.lineTo(9, 6); path.closeSubpath()
    p.drawPath(path)
    p.drawEllipse(QRectF(14, 13, 6, 6))
    _line(p, 18.5, 17.5, 21, 20)
    p.end()
    return QIcon(pm)


def icon_check(color, size=16):
    pm, p = _canvas(size)
    p.setPen(_pen(color, 2.4))
    path = QPainterPath()
    path.moveTo(4, 13); path.lineTo(9, 18); path.lineTo(20, 5)
    p.drawPath(path)
    p.end()
    return QIcon(pm)


def icon_play(color, size=16):
    pm, p = _canvas(size)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(color))
    path = QPainterPath()
    path.moveTo(6, 4); path.lineTo(20, 12); path.lineTo(6, 20)
    path.closeSubpath()
    p.drawPath(path)
    p.end()
    return QIcon(pm)


def icon_stop(color, size=16):
    pm, p = _canvas(size)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(color))
    p.drawRoundedRect(QRectF(5, 5, 14, 14), 2, 2)
    p.end()
    return QIcon(pm)


ICON_FUNCS = {
    "home": icon_home,
    "chevron_right": icon_chevron_right,
    "folder": icon_folder,
    "gcode_file": icon_gcode_file,
    "clock": icon_clock,
    "plus": icon_plus,
    "edit": icon_edit,
    "trash": icon_trash,
    "sync": icon_sync,
    "settings": icon_settings,
    "printer": icon_printer,
    "folder_search": icon_folder_search,
    "check": icon_check,
    "play": icon_play,
    "stop": icon_stop,
}


def get_icon(name, color, size=20):
    if name in ("arrow_up", "arrow_down"):
        return icon_arrow(color, size, "up" if name == "arrow_up" else "down")
    func = ICON_FUNCS.get(name)
    if func is None:
        raise ValueError(f"Ícono desconocido: {name}")
    return func(color, size)


# --------------------------------------------------------------------------
# Composición de íconos (thumbnail + badge de "protegido/en cola")
# --------------------------------------------------------------------------

def compose_badge(base_pixmap: QPixmap, badge_color="#42A5F5") -> QPixmap:
    """Devuelve una copia de base_pixmap con un pequeño reloj superpuesto
    en la esquina inferior derecha, indicando archivo protegido/en cola."""
    size = base_pixmap.width()
    result = QPixmap(base_pixmap)
    painter = QPainter(result)
    painter.setRenderHint(QPainter.Antialiasing)
    badge_size = max(9, int(size * 0.5))
    x = size - badge_size + 2
    y = size - badge_size + 2
    painter.setBrush(QColor("#161616"))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(x - 1, y - 1, badge_size + 2, badge_size + 2)
    painter.setPen(_pen(badge_color, 1.6))
    painter.setBrush(Qt.NoBrush)
    cx, cy, r = x + badge_size / 2, y + badge_size / 2, badge_size / 2 - 2
    painter.drawEllipse(QPointF(cx, cy), r, r)
    painter.drawLine(QPointF(cx, cy), QPointF(cx, cy - r * 0.6))
    painter.drawLine(QPointF(cx, cy), QPointF(cx + r * 0.5, cy + r * 0.2))
    painter.end()
    return result


def pixmap_to_data_uri(pixmap: QPixmap) -> str:
    """Codifica un QPixmap como PNG base64 para insertarlo en un tooltip HTML."""
    ba = QByteArray()
    buf = QBuffer(ba)
    buf.open(QIODevice.WriteOnly)
    pixmap.save(buf, "PNG")
    buf.close()
    return bytes(ba.toBase64()).decode("ascii")
