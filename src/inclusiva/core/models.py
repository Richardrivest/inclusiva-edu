from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Subject:
    id: int
    name: str
    level: str
    created_at: str

    @property
    def label(self) -> str:
        return f"{self.name} ({self.level})" if self.level else self.name


@dataclass(slots=True)
class Session:
    id: int
    subject_id: int
    title: str
    created_at: str
    audio_file: str | None  # relative to the data folder
    duration_ms: int


@dataclass(slots=True)
class Segment:
    """One recognised (or typed) phrase of a class transcript."""

    id: int
    session_id: int
    seq: int
    text: str
    start_ms: int | None  # position in the session audio; None for typed text
    end_ms: int | None
    source: str  # manual | whisper | google
    new_paragraph: bool
    edited: bool
