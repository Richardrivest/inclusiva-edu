"""Application entry point: wires storage, controller and the two windows."""

from __future__ import annotations

import logging
import sys

from PySide6.QtCore import QLibraryInfo, QLocale, QTranslator
from PySide6.QtWidgets import QApplication, QMessageBox

from . import paths
from .config import Settings
from .core.live import ClassroomController, default_session_title
from .core.projector import ProjectorState
from .storage.db import Database
from .ui import theme
from .ui.icons import app_icon
from .ui.projector_window import ProjectorWindow
from .ui.teacher_window import TeacherWindow

log = logging.getLogger("inclusiva")


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(paths.logs_dir() / "inclusiva.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def _install_excepthook() -> None:
    def hook(exc_type, exc, tb) -> None:
        log.error("Unhandled error", exc_info=(exc_type, exc, tb))
        if QApplication.instance() is not None:
            QMessageBox.critical(
                None,
                "inclusiva.edu",
                f"Ocurrió un error inesperado:\n\n{exc}\n\nEl detalle quedó guardado en el registro de la aplicación.",
            )

    sys.excepthook = hook


def _install_translations(app: QApplication) -> None:
    translator = QTranslator(app)
    directory = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    if translator.load(QLocale("es"), "qtbase", "_", directory):
        app.installTranslator(translator)


def _set_windows_app_id() -> None:
    """Lets the Windows taskbar show the app's own icon instead of Python's."""
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("inclusiva.edu.desktop")
        except (AttributeError, OSError):
            pass


def _seed(db: Database) -> None:
    if not db.list_subjects():
        subject = db.create_subject("Mi primera materia")
        db.create_session(subject.id, default_session_title(1))


def main() -> int:
    _setup_logging()
    _set_windows_app_id()
    app = QApplication(sys.argv)
    app.setApplicationName("inclusiva.edu")
    app.setOrganizationName("inclusiva.edu")
    app.setWindowIcon(app_icon())
    _install_translations(app)
    theme.apply(app)
    _install_excepthook()

    settings = Settings.load()
    db = Database(paths.db_path())
    _seed(db)

    state = ProjectorState(settings)
    controller = ClassroomController(db, state)
    projector = ProjectorWindow(state)
    teacher = TeacherWindow(controller, db, state, projector, settings)
    teacher.show()
    teacher.open_initial_session()
    projector.auto_place(settings.projector_screen)
    log.info("inclusiva.edu started; data in %s", paths.data_dir())

    try:
        return app.exec()
    finally:
        settings.save()
        db.close()
