# inclusiva.edu (desktop)

Live captioning for deaf and hard-of-hearing students. The teacher speaks, the app transcribes
in real time, and the text is shown full-screen on a projector. Every class session is stored
(audio + timestamped transcript), and activities can be generated from the transcript.

Created by Mag. Norma Espíndola. Rebuild of the original single-page `inclusiva_edu.html`
(kept in this folder as a reference).

## Running (development)

Requires [uv](https://docs.astral.sh/uv/) and Python 3.12.

```bash
run.bat
```

`run.bat` keeps the Python environment in `%LOCALAPPDATA%\inclusiva_edu_venv` so OneDrive does
not sync it. Class data (database, audio, settings, logs) lives in `%LOCALAPPDATA%\inclusiva_edu`.
Set `INCLUSIVA_DATA_DIR` to use another folder.

Tests:

```bash
set UV_PROJECT_ENVIRONMENT=%LOCALAPPDATA%\inclusiva_edu_venv && uv run pytest
```

## Architecture

One Python process (PySide6), two windows sharing the same state:

| Module | Responsibility |
|---|---|
| `core/live.py` | Open session, transcript segments, voice commands, feeds the projector |
| `core/projector.py` | What the students see (text, mode, freeze, appearance) |
| `core/commands.py` | Spoken commands: «punto y aparte», «nuevo párrafo», «borrar última frase» |
| `storage/db.py` | SQLite: subjects → sessions → timestamped segments |
| `ui/teacher_window.py` | Teacher control window |
| `ui/projector_window.py` | Full-screen student window on the projector (auto-detected) |
| `ui/canvas.py` | Caption rendering shared by the projector and the teacher's preview |

## Roadmap

1. ✅ Skeleton: database, subjects/classes, teacher window, projector window + preview
2. Microphone capture, session audio recording, offline Whisper live captions
3. Google Cloud Speech (Chirp 3, `es-US`) + hybrid online/offline switching
4. Session history: audio playback synced to transcript, class report export
5. Activities with Ollama (fill-in-the-blank, matching), projector activity mode, PDF/Word worksheets
6. Windows installer
