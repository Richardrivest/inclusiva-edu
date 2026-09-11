"""Where the app keeps its data.

Data lives in %LOCALAPPDATA% rather than next to the code: the project folder is synced by
OneDrive, and syncing an open SQLite database can corrupt it.
"""

from __future__ import annotations

import os
from pathlib import Path

APP_DIR_NAME = "inclusiva_edu"


def data_dir() -> Path:
    override = os.environ.get("INCLUSIVA_DATA_DIR")
    if override:
        base = Path(override)
    else:
        local = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        base = Path(local) / APP_DIR_NAME
    base.mkdir(parents=True, exist_ok=True)
    return base


def audio_dir() -> Path:
    path = data_dir() / "audio"
    path.mkdir(exist_ok=True)
    return path


def logs_dir() -> Path:
    path = data_dir() / "logs"
    path.mkdir(exist_ok=True)
    return path


def db_path() -> Path:
    return data_dir() / "inclusiva.db"


def settings_path() -> Path:
    return data_dir() / "settings.json"
