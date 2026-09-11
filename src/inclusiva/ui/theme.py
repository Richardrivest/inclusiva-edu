"""Visual identity: the violet/blue look of the original inclusiva.edu, plus projector color themes."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPalette, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import QApplication

from .. import paths

UI_FONT_FAMILY = "Segoe UI"
CAPTION_FONT_FAMILY = "Segoe UI"


@dataclass(frozen=True)
class CaptionTheme:
    key: str
    name: str
    background: str
    text: str
    interim: str  # words already stable but not yet stored
    unstable: str  # words the recognizer may still change
    accent: str


CAPTION_THEMES: dict[str, CaptionTheme] = {
    t.key: t
    for t in (
        CaptionTheme("oscuro", "Oscuro — blanco sobre negro", "#0b0b12", "#ffffff", "#e8e8ee", "#8f95a3", "#93c5fd"),
        CaptionTheme("alto_contraste", "Alto contraste — amarillo sobre negro", "#000000", "#ffe600", "#fff176", "#a3962f", "#ffffff"),
        CaptionTheme("claro", "Claro — negro sobre blanco", "#ffffff", "#111111", "#2b2b2b", "#808080", "#1d4ed8"),
        CaptionTheme("violeta", "inclusiva.edu — violeta", "#1a0b3d", "#f5f3ff", "#e9e3ff", "#a78bfa", "#60a5fa"),
    )
}


def caption_theme(key: str) -> CaptionTheme:
    return CAPTION_THEMES.get(key) or CAPTION_THEMES["oscuro"]


APP_QSS = """
QWidget { color: #f1f5f9; }
QWidget#root {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #2e1065, stop:0.55 #0f0b24, stop:1 #3b0764);
}
QFrame#header {
    background: rgba(76, 29, 149, 0.45);
    border: 1px solid rgba(139, 92, 246, 0.35);
    border-radius: 16px;
}
QFrame#card {
    background: rgba(59, 7, 100, 0.55);
    border: 1px solid rgba(139, 92, 246, 0.35);
    border-radius: 16px;
}
QLabel { background: transparent; }
QLabel#brand { font-size: 17pt; font-weight: 800; color: #ffffff; }
QLabel#brandSub { color: #e9d5ff; font-size: 9pt; }
QLabel#credit { color: #93c5fd; font-size: 8.5pt; font-weight: 600; }
QLabel#cardTitle { font-size: 11.5pt; font-weight: 700; color: #ffffff; }
QLabel#section { color: #93c5fd; font-size: 8.5pt; font-weight: 700; letter-spacing: 1px; padding-top: 4px; }
QLabel#muted { color: #c4b5fd; }
QLabel#hint { color: #a5b4fc; font-size: 9pt; }
QLabel#pill {
    border-radius: 13px; padding: 5px 14px; font-weight: 700;
    background: rgba(15, 10, 40, 0.8); border: 1px solid rgba(139, 92, 246, 0.5); color: #c4b5fd;
}
QLabel#pill[state="live"] { color: #34d399; border-color: rgba(52, 211, 153, 0.7); }
QLabel#pill[state="paused"] { color: #fbbf24; border-color: rgba(251, 191, 36, 0.7); }

QPushButton {
    background: #2563eb; color: #ffffff;
    border: 1px solid rgba(147, 197, 253, 0.35); border-radius: 10px;
    padding: 7px 14px; font-weight: 600;
}
QPushButton:hover { background: #3b82f6; }
QPushButton:pressed { background: #1d4ed8; }
QPushButton:disabled { background: rgba(49, 46, 129, 0.6); color: #8b85b5; border-color: rgba(99, 102, 241, 0.2); }
QPushButton[variant="secondary"], QPushButton[variant="toggle"], QPushButton[variant="freeze"] {
    background: rgba(30, 16, 70, 0.9); border: 1px solid #5b21b6; color: #e9d5ff;
}
QPushButton[variant="secondary"]:hover, QPushButton[variant="toggle"]:hover, QPushButton[variant="freeze"]:hover {
    background: #4c1d95;
}
QPushButton[variant="toggle"]:checked { background: #2563eb; color: #ffffff; border-color: #93c5fd; }
QPushButton[variant="freeze"]:checked { background: #d97706; color: #ffffff; border-color: #fcd34d; }
QPushButton[variant="danger"] { background: #e11d48; border-color: rgba(253, 164, 175, 0.4); }
QPushButton[variant="danger"]:hover { background: #f43f5e; }

QLineEdit, QComboBox {
    background: rgba(15, 10, 40, 0.9); border: 1px solid #5b21b6; border-radius: 10px;
    padding: 6px 10px; selection-background-color: #2563eb;
}
QLineEdit:focus, QComboBox:focus { border: 1px solid #60a5fa; }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox::down-arrow { image: url(%ARROW%); width: 12px; height: 12px; margin-right: 8px; }
QComboBox QAbstractItemView {
    background: #1e1145; border: 1px solid #5b21b6; selection-background-color: #2563eb; outline: none;
}

QTreeWidget, QTableWidget {
    background: rgba(15, 10, 40, 0.85); border: 1px solid rgba(91, 33, 182, 0.8); border-radius: 12px;
    padding: 4px; alternate-background-color: rgba(46, 16, 101, 0.35); outline: none;
}
QTreeWidget { show-decoration-selected: 0; }
QTreeView::branch:selected, QTreeView::branch:hover { background: transparent; }
QTreeWidget::item { padding: 5px 4px; border-radius: 6px; }
QTreeWidget::item:hover { background: rgba(124, 58, 237, 0.25); }
QTreeWidget::item:selected, QTableWidget::item:selected { background: rgba(37, 99, 235, 0.6); color: #ffffff; }
QTableWidget::item { padding: 6px 4px; }
QTableWidget QLineEdit { padding: 2px 4px; border-radius: 4px; }
QHeaderView::section {
    background: transparent; color: #c4b5fd; border: none;
    border-bottom: 1px solid rgba(139, 92, 246, 0.35); padding: 4px 6px; font-weight: 600;
}

QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: rgba(129, 140, 248, 0.45); border-radius: 4px; min-height: 28px; }
QScrollBar::handle:vertical:hover { background: rgba(129, 140, 248, 0.8); }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
QScrollBar::handle:horizontal { background: rgba(129, 140, 248, 0.45); border-radius: 4px; min-width: 28px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }

QSlider::groove:horizontal { height: 6px; background: rgba(91, 33, 182, 0.8); border-radius: 3px; }
QSlider::sub-page:horizontal { background: #3b82f6; border-radius: 3px; }
QSlider::handle:horizontal { background: #ffffff; width: 16px; margin: -6px 0; border-radius: 8px; }

QCheckBox { spacing: 8px; }
QCheckBox::indicator { width: 16px; height: 16px; border-radius: 4px; border: 1px solid #7c3aed; background: rgba(15, 10, 40, 0.9); }
QCheckBox::indicator:checked { background: #2563eb; border-color: #93c5fd; image: url(%CHECK%); }

QSplitter::handle { background: transparent; }
QStatusBar { color: #c4b5fd; background: transparent; }
QStatusBar::item { border: none; }
QToolTip { background: #1e1145; color: #f1f5f9; border: 1px solid #7c3aed; padding: 6px; }
QMenu { background: #1e1145; border: 1px solid #5b21b6; padding: 4px; }
QMenu::item { padding: 6px 18px; border-radius: 6px; }
QMenu::item:selected { background: #2563eb; }
QDialog { background: #1e1145; }
QScrollArea#panelScroll { background: transparent; border: none; }
QWidget#panelViewport { background: transparent; }
"""


def _indicator_images() -> dict[str, str]:
    """Stylesheets can only draw arrows and check marks from image files, so draw them once."""
    folder = paths.data_dir() / "ui"
    folder.mkdir(exist_ok=True)

    arrow = QPixmap(24, 24)
    arrow.fill(Qt.GlobalColor.transparent)
    p = QPainter(arrow)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#c4b5fd"))
    p.drawPolygon(QPolygonF([QPointF(4, 8), QPointF(20, 8), QPointF(12, 17)]))
    p.end()
    arrow_path = folder / "arrow-down.png"
    arrow.save(str(arrow_path))

    check = QPixmap(32, 32)
    check.fill(Qt.GlobalColor.transparent)
    p = QPainter(check)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor("#ffffff"), 4.5)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.drawPolyline(QPolygonF([QPointF(7, 17), QPointF(13, 23), QPointF(25, 9)]))
    p.end()
    check_path = folder / "check.png"
    check.save(str(check_path))

    return {"%ARROW%": arrow_path.as_posix(), "%CHECK%": check_path.as_posix()}


def apply(app: QApplication) -> None:
    app.setStyle("Fusion")
    palette = QPalette()
    colors = {
        QPalette.ColorRole.Window: "#1e1145",
        QPalette.ColorRole.WindowText: "#f1f5f9",
        QPalette.ColorRole.Base: "#150a33",
        QPalette.ColorRole.AlternateBase: "#241052",
        QPalette.ColorRole.Text: "#f1f5f9",
        QPalette.ColorRole.Button: "#2a1460",
        QPalette.ColorRole.ButtonText: "#f1f5f9",
        QPalette.ColorRole.Highlight: "#2563eb",
        QPalette.ColorRole.HighlightedText: "#ffffff",
        QPalette.ColorRole.ToolTipBase: "#1e1145",
        QPalette.ColorRole.ToolTipText: "#f1f5f9",
        QPalette.ColorRole.PlaceholderText: "#8b85b5",
        QPalette.ColorRole.Link: "#60a5fa",
    }
    for role, color in colors.items():
        palette.setColor(role, QColor(color))
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.WindowText, QPalette.ColorRole.ButtonText):
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor("#6b6590"))
    app.setPalette(palette)
    app.setFont(QFont(UI_FONT_FAMILY, 10))
    qss = APP_QSS
    for token, path in _indicator_images().items():
        qss = qss.replace(token, path)
    app.setStyleSheet(qss)
