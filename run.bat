@echo off
rem Runs inclusiva.edu in development mode.
rem The Python environment lives outside OneDrive so it is not synced.
set UV_PROJECT_ENVIRONMENT=%LOCALAPPDATA%\inclusiva_edu_venv
cd /d "%~dp0"
uv run python -m inclusiva %*
