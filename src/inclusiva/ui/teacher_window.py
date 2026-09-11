"""Main teacher window: subjects/classes, live transcript, student screen controls."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QMainWindow, QScrollArea, QSplitter, QStatusBar, QVBoxLayout, QWidget

from ..config import Settings
from ..core.live import ClassroomController
from ..core.projector import ProjectorState
from ..storage.db import Database
from .icons import app_pixmap
from .projector_panel import ProjectorPanel
from .projector_window import ProjectorWindow
from .sidebar import SessionSidebar
from .transcript_panel import TranscriptPanel
from .widgets import label, repolish

LIVE_TEXT = {
    "idle": "●  En espera",
    "live": "●  Transmitiendo en vivo",
    "paused": "❚❚  En pausa",
}


class HeaderBar(QFrame):
    def __init__(self, dpr: float):
        super().__init__()
        self.setObjectName("header")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 16, 8)
        layout.setSpacing(12)

        logo = QLabel()
        logo.setPixmap(app_pixmap(44, dpr))
        brand = QLabel('inclusiva<span style="color:#60a5fa;">.edu</span>')
        brand.setObjectName("brand")
        brand.setTextFormat(Qt.TextFormat.RichText)
        text = QVBoxLayout()
        text.setSpacing(0)
        text.addWidget(brand)
        text.addWidget(label("Plataforma de Accesibilidad e Inclusión Educativa", name="brandSub"))
        text.addWidget(label("★  Creado por: Mag. Norma Espíndola", name="credit"))

        self.pill = label(name="pill")
        layout.addWidget(logo)
        layout.addLayout(text)
        layout.addStretch(1)
        layout.addWidget(self.pill, 0, Qt.AlignmentFlag.AlignVCenter)
        self.set_live_state("idle")

    def set_live_state(self, state: str) -> None:
        self.pill.setText(LIVE_TEXT.get(state, LIVE_TEXT["idle"]))
        self.pill.setProperty("state", state)
        repolish(self.pill)


class TeacherWindow(QMainWindow):
    def __init__(
        self,
        controller: ClassroomController,
        db: Database,
        state: ProjectorState,
        projector: ProjectorWindow,
        settings: Settings,
    ):
        super().__init__()
        self._controller = controller
        self._db = db
        self._state = state
        self._projector = projector
        self._settings = settings

        self.setWindowTitle("inclusiva.edu — Docente")
        self.resize(1280, 780)
        self.setMinimumSize(1000, 620)

        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(14, 10, 14, 6)
        outer.setSpacing(10)

        self.header = HeaderBar(self.devicePixelRatioF())
        outer.addWidget(self.header)

        self.sidebar = SessionSidebar(controller)
        self.transcript = TranscriptPanel(controller)
        self.projector_panel = ProjectorPanel(state, projector, controller)

        right = QScrollArea()
        right.setObjectName("panelScroll")
        right.setWidgetResizable(True)
        right.setFrameShape(QFrame.Shape.NoFrame)
        right.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        right.viewport().setObjectName("panelViewport")
        right.setWidget(self.projector_panel)
        right.setMinimumWidth(340)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(10)
        splitter.addWidget(self.sidebar)
        splitter.addWidget(self.transcript)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        splitter.setSizes([240, 640, 400])
        outer.addWidget(splitter, 1)

        self.setStatusBar(QStatusBar())

        self.sidebar.session_selected.connect(self._on_session_selected)
        projector.notice.connect(lambda message: self.statusBar().showMessage(message, 10000))

        for keys, slot in (
            ("Ctrl+B", self.projector_panel.toggle_blank),
            ("Ctrl+Shift+F", self.projector_panel.toggle_freeze),
            ("Ctrl+L", controller.new_projector_page),
        ):
            QShortcut(QKeySequence(keys), self, activated=slot)

    def open_initial_session(self) -> None:
        target = self._settings.last_session_id
        if not target or self._db.get_session(target) is None:
            self.sidebar.reload()
            target = self.sidebar.first_session_id()
        self.sidebar.reload(target, emit=True)

    def _on_session_selected(self, session_id: int | None) -> None:
        if self._controller.session and self._controller.session.id == session_id:
            return
        self._controller.open_session(session_id)
        if session_id:
            self._settings.last_session_id = session_id

    def closeEvent(self, event) -> None:  # noqa: N802
        target = self._projector.fullscreen_screen
        if target is not None:
            self._settings.projector_screen = target.name()
        self._projector.force_close()
        event.accept()
