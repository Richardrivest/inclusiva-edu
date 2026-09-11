"""Live classroom controller: owns the open session's transcript and keeps the projector in sync."""

from __future__ import annotations

import logging
from datetime import date

from PySide6.QtCore import QObject, Signal

from .. import paths
from ..storage.db import Database
from .commands import apply_voice_commands, ensure_terminal_period
from .models import Segment, Session, Subject
from .projector import ProjectorState

log = logging.getLogger(__name__)

SENTENCE_END = ".?!…"
MAX_PROJECTED_SEGMENTS = 150


def default_session_title(number: int, day: date | None = None) -> str:
    return f"Clase {number} · {(day or date.today()):%d/%m/%Y}"


def build_paragraphs(segments: list[Segment]) -> list[str]:
    paragraphs: list[str] = []
    for segment in segments:
        if not paragraphs or segment.new_paragraph:
            paragraphs.append(segment.text)
        else:
            paragraphs[-1] = f"{paragraphs[-1]} {segment.text}"
    return paragraphs


def capitalize_first(text: str) -> str:
    for i, ch in enumerate(text):
        if ch.isalpha():
            return text[:i] + ch.upper() + text[i + 1 :]
    return text


def split_span(start_ms: int | None, end_ms: int | None, texts: list[str]) -> list[tuple[int | None, int | None]]:
    """Share an audio span between pieces of one utterance, proportionally to their length."""
    if start_ms is None or end_ms is None or not texts:
        return [(start_ms, end_ms)] * len(texts)
    total = sum(len(t) for t in texts) or 1
    spans: list[tuple[int | None, int | None]] = []
    cursor = start_ms
    for i, text in enumerate(texts):
        stop = end_ms if i == len(texts) - 1 else cursor + round((end_ms - start_ms) * len(text) / total)
        spans.append((cursor, stop))
        cursor = stop
    return spans


class ClassroomController(QObject):
    session_changed = Signal(object)  # Session | None
    segments_reset = Signal()
    segment_added = Signal(object)  # Segment
    segment_updated = Signal(object)  # Segment
    segment_removed = Signal(int)  # segment id

    def __init__(self, db: Database, projector: ProjectorState):
        super().__init__()
        self.db = db
        self.projector = projector
        self.session: Session | None = None
        self.subject: Subject | None = None
        self.segments: list[Segment] = []
        self._pending_paragraph = False
        self._display_from_seq = 0

    # -- sessions ---------------------------------------------------------------
    def open_session(self, session_id: int | None) -> None:
        session = self.db.get_session(session_id) if session_id is not None else None
        self.session = session
        self.subject = self.db.get_subject(session.subject_id) if session else None
        self.segments = self.db.list_segments(session.id) if session else []
        self._pending_paragraph = False
        self._display_from_seq = 0
        self._push_titles()
        self.projector.set_interim("", "")
        self.session_changed.emit(session)
        self.segments_reset.emit()
        self._push_transcript()

    def refresh_titles(self) -> None:
        """Re-read names after a rename."""
        if self.session is None:
            return
        self.session = self.db.get_session(self.session.id)
        self.subject = self.db.get_subject(self.session.subject_id) if self.session else None
        self._push_titles()
        self.session_changed.emit(self.session)

    def delete_session(self, session_id: int) -> None:
        if self.session and self.session.id == session_id:
            self.open_session(None)
        self._remove_audio(self.db.delete_session(session_id))

    def delete_subject(self, subject_id: int) -> None:
        if self.subject and self.subject.id == subject_id:
            self.open_session(None)
        for audio_file in self.db.delete_subject(subject_id):
            self._remove_audio(audio_file)

    # -- transcript -------------------------------------------------------------
    def add_recognized_text(
        self, text: str, start_ms: int | None = None, end_ms: int | None = None, source: str = "manual"
    ) -> None:
        if self.session is None or not text.strip():
            return
        result = apply_voice_commands(text)
        for _ in range(result.delete_last):
            if self.segments:
                self.delete_segment(self.segments[-1].id)
        if result.close_previous and self.segments:
            last = self.segments[-1]
            closed = ensure_terminal_period(last.text)
            if closed != last.text:
                self._set_text(last, closed, edited=False)
        spans = split_span(start_ms, end_ms, [p.text for p in result.pieces])
        for piece, (start, end) in zip(result.pieces, spans):
            self._append(piece.text, start, end, source, piece.new_paragraph)
        if result.pending_paragraph:
            self._pending_paragraph = True
        self._push_transcript()

    def add_manual_text(self, text: str) -> None:
        """Typed text (a formula, a key term, a page number) goes on a line of its own."""
        if self.session is None or not text.strip():
            return
        self._append(text, None, None, "manual", True)
        self._pending_paragraph = True
        self._push_transcript()

    def request_new_paragraph(self) -> None:
        if self.session is not None:
            self._pending_paragraph = True
            self._push_transcript()

    def edit_segment(self, segment_id: int, text: str) -> None:
        segment = self._find(segment_id)
        if segment is None:
            return
        text = " ".join(text.split())
        if not text:
            self.delete_segment(segment_id)
        elif text != segment.text:
            self._set_text(segment, text, edited=True)
            self._push_transcript()

    def delete_segment(self, segment_id: int) -> None:
        segment = self._find(segment_id)
        if segment is None:
            return
        self.db.delete_segment(segment_id)
        self.segments.remove(segment)
        self.segment_removed.emit(segment_id)
        self._push_transcript()

    def set_interim(self, stable: str, unstable: str = "") -> None:
        self.projector.set_interim(stable, unstable)

    # -- projector page ---------------------------------------------------------
    def new_projector_page(self) -> None:
        """Start the student screen from a blank page; the transcript itself is kept."""
        self._display_from_seq = self.segments[-1].seq if self.segments else 0
        self._push_transcript()

    def show_whole_transcript(self) -> None:
        self._display_from_seq = 0
        self._push_transcript()

    # -- internals --------------------------------------------------------------
    def _append(self, text: str, start_ms: int | None, end_ms: int | None, source: str, new_paragraph: bool) -> None:
        assert self.session is not None
        new_paragraph = new_paragraph or self._pending_paragraph
        self._pending_paragraph = False
        text = " ".join(text.split())
        previous = self.segments[-1] if self.segments else None
        if new_paragraph or previous is None or previous.text.rstrip()[-1:] in SENTENCE_END:
            text = capitalize_first(text)
        segment = self.db.add_segment(self.session.id, text, start_ms, end_ms, source, new_paragraph)
        self.segments.append(segment)
        self.segment_added.emit(segment)

    def _set_text(self, segment: Segment, text: str, edited: bool) -> None:
        self.db.update_segment_text(segment.id, text, edited=edited)
        segment.text = text
        segment.edited = segment.edited or edited
        self.segment_updated.emit(segment)

    def _find(self, segment_id: int) -> Segment | None:
        return next((s for s in self.segments if s.id == segment_id), None)

    def _push_titles(self) -> None:
        self.projector.set_titles(
            self.subject.name if self.subject else "",
            self.session.title if self.session else "",
        )

    def _push_transcript(self) -> None:
        visible = [s for s in self.segments if s.seq > self._display_from_seq][-MAX_PROJECTED_SEGMENTS:]
        self.projector.set_transcript(build_paragraphs(visible), self._pending_paragraph)

    @staticmethod
    def _remove_audio(audio_file: str | None) -> None:
        if not audio_file:
            return
        try:
            (paths.data_dir() / audio_file).unlink(missing_ok=True)
        except OSError:
            log.exception("Could not delete audio file %s", audio_file)
