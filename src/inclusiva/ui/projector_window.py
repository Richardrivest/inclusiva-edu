"""The student window. Goes full-screen on the projector automatically when one is connected."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QGuiApplication, QScreen
from PySide6.QtWidgets import QVBoxLayout, QWidget

from ..core.projector import ProjectorState
from .canvas import ProjectorCanvas


def describe_screen(screen: QScreen) -> str:
    screens = QGuiApplication.screens()
    number = screens.index(screen) + 1 if screen in screens else 0
    geometry = screen.geometry()
    ratio = screen.devicePixelRatio()
    width, height = round(geometry.width() * ratio), round(geometry.height() * ratio)
    name = (screen.model() or screen.manufacturer() or "").strip()
    text = f"Pantalla {number}"
    if name:
        text += f" · {name}"
    text += f" ({width}×{height})"
    if screen == QGuiApplication.primaryScreen():
        text += " — esta computadora"
    return text


class ProjectorWindow(QWidget):
    placement_changed = Signal()
    notice = Signal(str)  # messages for the teacher's status bar

    def __init__(self, state: ProjectorState):
        super().__init__(None, Qt.WindowType.Window)
        self.setWindowTitle("inclusiva.edu — Pantalla de estudiantes")
        self.canvas = ProjectorCanvas(state, self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)
        self._screen: QScreen | None = None  # full-screen target; None when windowed or hidden
        self._allow_close = False

        app = QGuiApplication.instance()
        app.screenAdded.connect(self._on_screen_added, Qt.ConnectionType.QueuedConnection)
        app.screenRemoved.connect(self._on_screen_removed)

    # -- placement --------------------------------------------------------------
    @property
    def fullscreen_screen(self) -> QScreen | None:
        return self._screen

    @property
    def placement(self) -> str:
        if self._screen is not None:
            return "fullscreen"
        return "window" if self.isVisible() else "hidden"

    def auto_place(self, preferred_name: str = "") -> None:
        """Full screen on the projector if one is connected; otherwise stay hidden (the teacher has a preview)."""
        primary = QGuiApplication.primaryScreen()
        others = [s for s in QGuiApplication.screens() if s != primary]
        target = next((s for s in others if s.name() == preferred_name), None) or (others[0] if others else None)
        if target is not None:
            self.show_fullscreen_on(target)
        else:
            self.hide_projector()

    def show_fullscreen_on(self, screen: QScreen) -> None:
        self._screen = screen
        if self.isFullScreen():
            self.showNormal()
        self.winId()  # make sure the native window exists before choosing its screen
        handle = self.windowHandle()
        if handle is not None:
            handle.setScreen(screen)
        self.setGeometry(screen.geometry())  # required, otherwise show() may pick another screen
        self.showFullScreen()
        if screen != QGuiApplication.primaryScreen():
            self.setCursor(Qt.CursorShape.BlankCursor)
        else:
            self.unsetCursor()
        self.placement_changed.emit()

    def show_preview_window(self) -> None:
        self._screen = None
        if self.isFullScreen():
            self.showNormal()
        self.unsetCursor()
        primary = QGuiApplication.primaryScreen()
        area = primary.availableGeometry()
        width = min(960, int(area.width() * 0.55))
        height = int(width * 9 / 16)
        self.winId()
        handle = self.windowHandle()
        if handle is not None:
            handle.setScreen(primary)
        self.setGeometry(area.right() - width - 24, area.bottom() - height - 56, width, height)
        self.show()
        self.raise_()
        self.placement_changed.emit()

    def hide_projector(self) -> None:
        self._screen = None
        if self.isFullScreen():
            self.showNormal()
        self.hide()
        self.placement_changed.emit()

    def force_close(self) -> None:
        self._allow_close = True
        self.close()

    # -- events -----------------------------------------------------------------
    def closeEvent(self, event) -> None:  # noqa: N802
        if self._allow_close:
            event.accept()
        else:  # closing the student window only hides it; the teacher can show it again
            event.ignore()
            self.hide_projector()

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Escape and self.isFullScreen():
            self.show_preview_window()
        elif event.key() == Qt.Key.Key_F11:
            self._toggle_fullscreen()
        else:
            super().keyPressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        self._toggle_fullscreen()

    def _toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self.show_preview_window()
        else:
            self.show_fullscreen_on(self.screen())

    def _on_screen_added(self, screen: QScreen) -> None:
        if self._screen is None and screen != QGuiApplication.primaryScreen():
            self.show_fullscreen_on(screen)
            self.notice.emit(f"Proyector detectado: la pantalla de estudiantes se muestra en {describe_screen(screen)}.")
        else:
            self.placement_changed.emit()

    def _on_screen_removed(self, screen: QScreen) -> None:
        if screen == self._screen:
            self._screen = None
            QTimer.singleShot(0, self.hide_projector)
            self.notice.emit("Se desconectó el proyector. La vista previa sigue disponible en el panel.")
        else:
            QTimer.singleShot(0, self.placement_changed.emit)
