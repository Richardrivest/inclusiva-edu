"""What the students see. Shared by the projector window and the teacher's preview."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from ..config import Settings

MODES = ("captions", "blank")


class ProjectorState(QObject):
    changed = Signal()

    def __init__(self, settings: Settings):
        super().__init__()
        self._settings = settings
        self.mode = "captions"
        self.frozen = False
        self.live_state = "idle"  # idle | live | paused
        self.title = ""
        self.subtitle = ""
        self.version = 0  # bumped on every visible change; lets views cache layout
        self._paragraphs: list[str] = []
        self._pending_break = False
        self._interim: tuple[str, str] = ("", "")
        self._snapshot: tuple[list[str], tuple[str, str], bool] | None = None

    # -- appearance (persisted) -------------------------------------------------
    @property
    def font_px(self) -> int:
        return self._settings.projector_font_px

    @property
    def theme_key(self) -> str:
        return self._settings.projector_theme

    @property
    def show_header(self) -> bool:
        return self._settings.projector_show_header

    def set_font_px(self, px: int) -> None:
        self._settings.projector_font_px = int(px)
        self._bump()

    def set_theme(self, key: str) -> None:
        self._settings.projector_theme = key
        self._bump()

    def set_show_header(self, show: bool) -> None:
        self._settings.projector_show_header = bool(show)
        self._bump()

    # -- content ----------------------------------------------------------------
    def content(self) -> tuple[list[str], tuple[str, str], bool]:
        """(paragraphs, (stable interim, unstable interim), pending paragraph break)."""
        if self.frozen and self._snapshot is not None:
            return self._snapshot
        return self._paragraphs, self._interim, self._pending_break

    def set_transcript(self, paragraphs: list[str], pending_break: bool) -> None:
        self._paragraphs = list(paragraphs)
        self._pending_break = pending_break
        if not self.frozen:
            self._bump()

    def set_interim(self, stable: str, unstable: str) -> None:
        interim = (stable.strip(), unstable.strip())
        if interim == self._interim:
            return
        self._interim = interim
        if not self.frozen:
            self._bump()

    def set_frozen(self, frozen: bool) -> None:
        if frozen == self.frozen:
            return
        self.frozen = frozen
        self._snapshot = (list(self._paragraphs), self._interim, self._pending_break) if frozen else None
        self._bump()

    def set_mode(self, mode: str) -> None:
        if mode not in MODES or mode == self.mode:
            return
        self.mode = mode
        self._bump()

    def set_live_state(self, state: str) -> None:
        if state != self.live_state:
            self.live_state = state
            self._bump()

    def set_titles(self, title: str, subtitle: str) -> None:
        self.title, self.subtitle = title, subtitle
        self._bump()

    def _bump(self) -> None:
        self.version += 1
        self.changed.emit()
