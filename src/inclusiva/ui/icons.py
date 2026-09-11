"""App icon, drawn in code: a caption speech bubble on the brand gradient."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QIcon, QLinearGradient, QPainter, QPainterPath, QPixmap, QPolygonF


def app_pixmap(size: int, dpr: float = 1.0) -> QPixmap:
    s = max(1, round(size * dpr))
    pixmap = QPixmap(s, s)
    pixmap.fill(Qt.GlobalColor.transparent)
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    gradient = QLinearGradient(0, s, s, 0)
    gradient.setColorAt(0.0, QColor("#2563eb"))
    gradient.setColorAt(0.55, QColor("#7c3aed"))
    gradient.setColorAt(1.0, QColor("#c084fc"))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(gradient))
    p.drawRoundedRect(QRectF(0, 0, s, s), s * 0.24, s * 0.24)

    bubble = QRectF(s * 0.17, s * 0.2, s * 0.66, s * 0.46)
    path = QPainterPath()
    path.addRoundedRect(bubble, s * 0.1, s * 0.1)
    path.addPolygon(
        QPolygonF([QPointF(s * 0.3, bubble.bottom() - 1), QPointF(s * 0.25, s * 0.81), QPointF(s * 0.47, bubble.bottom() - 1)])
    )
    p.setBrush(QColor("#ffffff"))
    p.drawPath(path.simplified())

    bar = s * 0.07
    p.setBrush(QColor("#6d28d9"))
    p.drawRoundedRect(QRectF(s * 0.27, s * 0.32, s * 0.46, bar), bar / 2, bar / 2)
    p.setBrush(QColor("#2563eb"))
    p.drawRoundedRect(QRectF(s * 0.27, s * 0.46, s * 0.3, bar), bar / 2, bar / 2)
    p.end()

    pixmap.setDevicePixelRatio(dpr)
    return pixmap


def app_icon() -> QIcon:
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(app_pixmap(size))
    return icon
