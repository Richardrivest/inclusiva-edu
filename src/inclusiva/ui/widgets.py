"""Small building blocks shared by the teacher window panels."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


class Card(QFrame):
    """Rounded panel with a title row (`header`) and a content layout (`body`)."""

    def __init__(self, title: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("card")
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(16, 14, 16, 16)
        self.body.setSpacing(10)
        self.header = QHBoxLayout()
        self.header.setSpacing(8)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("cardTitle")
        self.header.addWidget(self.title_label)
        self.header.addStretch(1)
        self.body.addLayout(self.header)


def button(text: str, *, variant: str | None = None, checkable: bool = False, tooltip: str | None = None) -> QPushButton:
    btn = QPushButton(text)
    if variant:
        btn.setProperty("variant", variant)
    btn.setCheckable(checkable)
    if tooltip:
        btn.setToolTip(tooltip)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    return btn


def label(text: str = "", *, name: str | None = None, wrap: bool = False) -> QLabel:
    lbl = QLabel(text)
    if name:
        lbl.setObjectName(name)
    lbl.setWordWrap(wrap)
    return lbl


def repolish(widget: QWidget) -> None:
    """Re-apply the stylesheet after changing a dynamic property used in selectors."""
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


def hrow(*widgets: QWidget, stretch_index: int | None = None, spacing: int = 8) -> QHBoxLayout:
    row = QHBoxLayout()
    row.setSpacing(spacing)
    for i, widget in enumerate(widgets):
        row.addWidget(widget, 1 if i == stretch_index else 0)
    return row
