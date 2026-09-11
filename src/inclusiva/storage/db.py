"""SQLite storage: subjects → sessions (classes) → timestamped transcript segments."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from ..core.models import Segment, Session, Subject

SCHEMA_V1 = """
CREATE TABLE subjects (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    level       TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL
);

CREATE TABLE sessions (
    id           INTEGER PRIMARY KEY,
    subject_id   INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    title        TEXT NOT NULL,
    created_at   TEXT NOT NULL,
    audio_file   TEXT,
    duration_ms  INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX idx_sessions_subject ON sessions(subject_id);

CREATE TABLE segments (
    id             INTEGER PRIMARY KEY,
    session_id     INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    seq            INTEGER NOT NULL,
    text           TEXT NOT NULL,
    start_ms       INTEGER,
    end_ms         INTEGER,
    source         TEXT NOT NULL DEFAULT 'manual',
    new_paragraph  INTEGER NOT NULL DEFAULT 0,
    edited         INTEGER NOT NULL DEFAULT 0,
    created_at     TEXT NOT NULL
);
CREATE INDEX idx_segments_session ON segments(session_id, seq);

PRAGMA user_version = 1;
"""


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _subject(row: sqlite3.Row) -> Subject:
    return Subject(row["id"], row["name"], row["level"], row["created_at"])


def _session(row: sqlite3.Row) -> Session:
    return Session(row["id"], row["subject_id"], row["title"], row["created_at"], row["audio_file"], row["duration_ms"])


def _segment(row: sqlite3.Row) -> Segment:
    return Segment(
        id=row["id"],
        session_id=row["session_id"],
        seq=row["seq"],
        text=row["text"],
        start_ms=row["start_ms"],
        end_ms=row["end_ms"],
        source=row["source"],
        new_paragraph=bool(row["new_paragraph"]),
        edited=bool(row["edited"]),
    )


class Database:
    def __init__(self, path: Path | str):
        self.conn = sqlite3.connect(str(path), isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        if str(path) != ":memory:":
            self.conn.execute("PRAGMA journal_mode = WAL")
        self._migrate()

    def _migrate(self) -> None:
        version = self.conn.execute("PRAGMA user_version").fetchone()[0]
        if version < 1:
            self.conn.executescript(f"BEGIN;{SCHEMA_V1}COMMIT;")

    def close(self) -> None:
        self.conn.close()

    # -- subjects ---------------------------------------------------------------
    def list_subjects(self) -> list[Subject]:
        rows = self.conn.execute("SELECT * FROM subjects ORDER BY name COLLATE NOCASE, id")
        return [_subject(r) for r in rows]

    def get_subject(self, subject_id: int) -> Subject | None:
        row = self.conn.execute("SELECT * FROM subjects WHERE id = ?", (subject_id,)).fetchone()
        return _subject(row) if row else None

    def create_subject(self, name: str, level: str = "") -> Subject:
        cur = self.conn.execute(
            "INSERT INTO subjects (name, level, created_at) VALUES (?, ?, ?)", (name.strip(), level.strip(), _now())
        )
        return self.get_subject(cur.lastrowid)

    def update_subject(self, subject_id: int, name: str, level: str) -> None:
        self.conn.execute("UPDATE subjects SET name = ?, level = ? WHERE id = ?", (name.strip(), level.strip(), subject_id))

    def delete_subject(self, subject_id: int) -> list[str]:
        """Deletes the subject with all its sessions; returns their audio files for cleanup."""
        audio = [
            r[0]
            for r in self.conn.execute(
                "SELECT audio_file FROM sessions WHERE subject_id = ? AND audio_file IS NOT NULL", (subject_id,)
            )
        ]
        self.conn.execute("DELETE FROM subjects WHERE id = ?", (subject_id,))
        return audio

    # -- sessions ---------------------------------------------------------------
    def list_sessions(self, subject_id: int) -> list[Session]:
        rows = self.conn.execute("SELECT * FROM sessions WHERE subject_id = ? ORDER BY created_at, id", (subject_id,))
        return [_session(r) for r in rows]

    def count_sessions(self, subject_id: int) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM sessions WHERE subject_id = ?", (subject_id,)).fetchone()[0]

    def get_session(self, session_id: int) -> Session | None:
        row = self.conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        return _session(row) if row else None

    def create_session(self, subject_id: int, title: str) -> Session:
        cur = self.conn.execute(
            "INSERT INTO sessions (subject_id, title, created_at) VALUES (?, ?, ?)", (subject_id, title.strip(), _now())
        )
        return self.get_session(cur.lastrowid)

    def rename_session(self, session_id: int, title: str) -> None:
        self.conn.execute("UPDATE sessions SET title = ? WHERE id = ?", (title.strip(), session_id))

    def set_session_audio(self, session_id: int, audio_file: str | None, duration_ms: int) -> None:
        self.conn.execute(
            "UPDATE sessions SET audio_file = ?, duration_ms = ? WHERE id = ?", (audio_file, duration_ms, session_id)
        )

    def delete_session(self, session_id: int) -> str | None:
        """Deletes the session and its transcript; returns its audio file for cleanup."""
        row = self.conn.execute("SELECT audio_file FROM sessions WHERE id = ?", (session_id,)).fetchone()
        self.conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        return row[0] if row else None

    # -- segments ---------------------------------------------------------------
    def list_segments(self, session_id: int) -> list[Segment]:
        rows = self.conn.execute("SELECT * FROM segments WHERE session_id = ? ORDER BY seq", (session_id,))
        return [_segment(r) for r in rows]

    def add_segment(
        self,
        session_id: int,
        text: str,
        start_ms: int | None = None,
        end_ms: int | None = None,
        source: str = "manual",
        new_paragraph: bool = False,
    ) -> Segment:
        seq = self.conn.execute(
            "SELECT COALESCE(MAX(seq), 0) + 1 FROM segments WHERE session_id = ?", (session_id,)
        ).fetchone()[0]
        cur = self.conn.execute(
            "INSERT INTO segments (session_id, seq, text, start_ms, end_ms, source, new_paragraph, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (session_id, seq, text, start_ms, end_ms, source, int(new_paragraph), _now()),
        )
        return Segment(cur.lastrowid, session_id, seq, text, start_ms, end_ms, source, new_paragraph, False)

    def update_segment_text(self, segment_id: int, text: str, edited: bool = True) -> None:
        self.conn.execute(
            "UPDATE segments SET text = ?, edited = MAX(edited, ?) WHERE id = ?", (text, int(edited), segment_id)
        )

    def delete_segment(self, segment_id: int) -> None:
        self.conn.execute("DELETE FROM segments WHERE id = ?", (segment_id,))
