"""Caption rendering for the student screen.

The same widget draws the full-screen projector window and the teacher's preview. Sizes are
defined for a 1920-px-wide screen and scaled to the widget width, so the preview shows exactly
the same layout as the projector.
"""

from __future__ import annotations

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QLinearGradient,
    QPainter,
    QTextBlockFormat,
    QTextCharFormat,
    QTextCursor,
    QTextDocument,
)
from PySide6.QtWidgets import QSizePolicy, QVBoxLayout, QWidget

from ..core.live import capitalize_first
from ..core.projector import ProjectorState
from .theme import CAPTION_FONT_FAMILY, CaptionTheme, caption_theme

REFERENCE_WIDTH = 1920.0
PLACEHOLDER = "Esperando el inicio de la clase…"
LINE_HEIGHT_PERCENT = 130.0

_ALIGN_LEFT_CENTER = int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
_ALIGN_RIGHT_CENTER = int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
_ALIGN_CENTER = int(Qt.AlignmentFlag.AlignCenter)
_ALIGN_TOP_WRAP = int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop) | int(Qt.TextFlag.TextWordWrap)


def caption_font(px: int, weight: QFont.Weight = QFont.Weight.DemiBold) -> QFont:
    font = QFont(CAPTION_FONT_FAMILY)
    font.setPixelSize(max(1, px))
    font.setWeight(weight)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    return font


def visible_lines(font_px: int, screen_height: int = 1080) -> int:
    """Approximate number of caption lines that fit on a 1080p screen (shown to the teacher)."""
    usable = screen_height - 190
    return max(1, int(usable / (font_px * LINE_HEIGHT_PERCENT / 100 * 1.08)))


class ProjectorCanvas(QWidget):
    def __init__(self, state: ProjectorState, parent: QWidget | None = None):
        super().__init__(parent)
        self._state = state
        self._doc: QTextDocument | None = None
        self._doc_key: tuple | None = None
        state.changed.connect(self.update)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setMinimumSize(160, 90)

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt override)
        painter = QPainter(self)
        try:
            self._paint(painter)
        finally:
            painter.end()

    # -- painting ---------------------------------------------------------------
    def _paint(self, p: QPainter) -> None:
        st = self._state
        theme = caption_theme(st.theme_key)
        p.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing)
        p.fillRect(self.rect(), QColor(theme.background))
        scale = self.width() / REFERENCE_WIDTH

        if st.mode == "blank":
            self._paint_blank(p, theme, scale)
            return

        margin = round(72 * scale)
        top = round(40 * scale)
        if st.show_header:
            top = self._paint_header(p, theme, scale, margin) + round(28 * scale)
        area = QRect(margin, top, self.width() - 2 * margin, self.height() - top - round(44 * scale))
        if area.width() <= 0 or area.height() <= 0:
            return

        font_px = max(6, round(st.font_px * scale))
        paragraphs, (stable, unstable), _ = st.content()
        if not paragraphs and not stable and not unstable:
            p.setFont(caption_font(round(font_px * 0.7), QFont.Weight.Normal))
            p.setPen(QColor(theme.unstable))
            p.drawText(area, _ALIGN_TOP_WRAP, PLACEHOLDER)
            return

        doc = self._document(font_px, area.width(), theme)
        height = doc.size().height()
        overflow = height > area.height()
        y = area.bottom() + 1 - height if overflow else area.top()
        p.save()
        p.setClipRect(area)
        p.translate(area.left(), y)
        doc.drawContents(p)
        p.restore()

        if overflow:  # fade the oldest line out instead of cutting it
            fade = round(font_px * 1.4)
            gradient = QLinearGradient(0, area.top(), 0, area.top() + fade)
            solid = QColor(theme.background)
            clear = QColor(theme.background)
            clear.setAlpha(0)
            gradient.setColorAt(0.0, solid)
            gradient.setColorAt(1.0, clear)
            p.fillRect(QRect(0, area.top(), self.width(), fade), gradient)

    def _paint_header(self, p: QPainter, theme: CaptionTheme, scale: float, margin: int) -> int:
        st = self._state
        font = caption_font(max(9, round(28 * scale)))
        metrics = QFontMetrics(font)
        p.setFont(font)
        rect = QRect(margin, round(24 * scale), self.width() - 2 * margin, metrics.height())

        status, status_color = self._status()
        status_width = metrics.horizontalAdvance(status) + (round(32 * scale) if status else 0)
        title = " · ".join(t for t in (st.title, st.subtitle) if t)
        title = metrics.elidedText(title, Qt.TextElideMode.ElideRight, max(0, rect.width() - status_width))
        p.setPen(QColor(theme.accent))
        p.drawText(rect, _ALIGN_LEFT_CENTER, title)
        if status:
            p.setPen(QColor(status_color))
            p.drawText(rect, _ALIGN_RIGHT_CENTER, status)

        line_y = rect.bottom() + round(14 * scale)
        separator = QColor(theme.accent)
        separator.setAlpha(70)
        p.setPen(separator)
        p.drawLine(margin, line_y, self.width() - margin, line_y)
        return line_y

    def _paint_blank(self, p: QPainter, theme: CaptionTheme, scale: float) -> None:
        color = QColor(theme.accent)
        color.setAlpha(80)
        p.setPen(color)
        p.setFont(caption_font(max(8, round(40 * scale))))
        p.drawText(self.rect(), _ALIGN_CENTER, "inclusiva.edu")

    def _status(self) -> tuple[str, str]:
        st = self._state
        if st.frozen:
            return "❚❚  TEXTO DETENIDO", "#f59e0b"
        if st.live_state == "live":
            return "●  EN VIVO", "#ef4444"
        if st.live_state == "paused":
            return "❚❚  EN PAUSA", "#fbbf24"
        return "", ""

    # -- text layout ------------------------------------------------------------
    def _document(self, font_px: int, width: int, theme: CaptionTheme) -> QTextDocument:
        key = (self._state.version, font_px, width, theme.key)
        if self._doc is not None and self._doc_key == key:
            return self._doc

        paragraphs, (stable, unstable), pending_break = self._state.content()
        font = caption_font(font_px)
        doc = QTextDocument()
        doc.setUndoRedoEnabled(False)
        doc.setDocumentMargin(0)
        doc.setDefaultFont(font)
        doc.setTextWidth(width)

        block = QTextBlockFormat()
        block.setLineHeight(LINE_HEIGHT_PERCENT, QTextBlockFormat.LineHeightTypes.ProportionalHeight.value)
        block.setBottomMargin(font_px * 0.45)
        final_fmt = QTextCharFormat()
        final_fmt.setFont(font)
        final_fmt.setForeground(QColor(theme.text))
        stable_fmt = QTextCharFormat(final_fmt)
        stable_fmt.setForeground(QColor(theme.interim))
        unstable_fmt = QTextCharFormat(final_fmt)
        unstable_fmt.setForeground(QColor(theme.unstable))
        unstable_fmt.setFontItalic(True)

        cursor = QTextCursor(doc)
        cursor.setBlockFormat(block)
        for i, paragraph in enumerate(paragraphs):
            if i:
                cursor.insertBlock(block)
            cursor.insertText(paragraph, final_fmt)

        if stable or unstable:
            starts_block = pending_break or not paragraphs
            if paragraphs and pending_break:
                cursor.insertBlock(block)
            need_space = not starts_block
            if starts_block:  # match how the text will look once it is stored
                if stable:
                    stable = capitalize_first(stable)
                else:
                    unstable = capitalize_first(unstable)
            for text, fmt in ((stable, stable_fmt), (unstable, unstable_fmt)):
                if text:
                    cursor.insertText((" " if need_space else "") + text, fmt)
                    need_space = True

        self._doc, self._doc_key = doc, key
        return doc


class AspectBox(QWidget):
    """Keeps its child at a fixed aspect ratio (used for the teacher's preview).

    Height-for-width layouts are not honoured inside a QScrollArea, so the box fixes its own
    height whenever its width changes.
    """

    def __init__(self, child: QWidget, aspect: float = 16 / 9, parent: QWidget | None = None):
        super().__init__(parent)
        self._aspect = aspect
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(child)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(self.heightForWidth(360))

    def set_aspect(self, aspect: float) -> None:
        if aspect > 0 and abs(aspect - self._aspect) > 1e-3:
            self._aspect = aspect
            self._fit()

    def heightForWidth(self, width: int) -> int:  # noqa: N802
        return max(1, round(width / self._aspect))

    def sizeHint(self) -> QSize:  # noqa: N802
        return QSize(360, self.heightForWidth(360))

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._fit()

    def _fit(self) -> None:
        height = self.heightForWidth(self.width())
        if height != self.height():
            self.setFixedHeight(height)
