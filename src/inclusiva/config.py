"""User settings, persisted as JSON in the data folder."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from . import paths

log = logging.getLogger(__name__)


@dataclass
class Settings:
    # Student screen (projector)
    projector_font_px: int = 64  # relative to a 1920-px-wide screen
    projector_theme: str = "oscuro"
    projector_show_header: bool = True
    projector_screen: str = ""  # QScreen.name() of the last projector used

    # Speech recognition (steps 2 and 3)
    stt_engine: str = "hybrid"  # hybrid | whisper | google
    mic_device: str = ""  # "" = system default microphone
    whisper_model: str = "small"
    google_credentials_file: str = ""
    google_project_id: str = ""
    google_location: str = "us"
    google_model: str = "chirp_3"
    google_language: str = "es-US"

    last_session_id: int = 0

    @classmethod
    def load(cls, path: Path | None = None) -> Settings:
        path = path or paths.settings_path()
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return cls()
        except (OSError, json.JSONDecodeError):
            log.exception("Could not read settings; using defaults")
            return cls()
        known = {f.name for f in fields(cls)}
        return cls(**{key: value for key, value in raw.items() if key in known})

    def save(self, path: Path | None = None) -> None:
        path = path or paths.settings_path()
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(path)
