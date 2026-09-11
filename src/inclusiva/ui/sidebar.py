"""Subjects and their classes (sessions)."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QInputDialog, QMenu, QMessageBox, QTreeWidget, QTreeWidgetItem

from ..core.live import ClassroomController, default_session_title
from .dialogs import SubjectDialog
from .widgets import Card, button, hrow

KIND_ROLE = int(Qt.ItemDataRole.UserRole)
ID_ROLE = KIND_ROLE + 1


class SessionSidebar(Card):
    session_selected = Signal(object)  # session id or None

    def __init__(self, controller: ClassroomController):
        super().__init__("Materias y clases")
        self._controller = controller
        self._db = controller.db
        self._reloading = False

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(14)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.btn_subject = button("+ Materia", tooltip="Crear una materia nueva")
        self.btn_session = button("+ Clase", tooltip="Crear una clase nueva en la materia seleccionada")

        self.body.addWidget(self.tree, 1)
        self.body.addLayout(hrow(self.btn_subject, self.btn_session))

        self.tree.currentItemChanged.connect(self._on_current_changed)
        self.tree.customContextMenuRequested.connect(self._show_menu)
        self.btn_subject.clicked.connect(self.new_subject)
        self.btn_session.clicked.connect(self.new_session)

    # -- tree -------------------------------------------------------------------
    def reload(self, select_session_id: int | None = None, emit: bool = False) -> None:
        self._reloading = True
        self.tree.clear()
        selected: QTreeWidgetItem | None = None
        for subject in self._db.list_subjects():
            subject_item = QTreeWidgetItem([subject.label])
            subject_item.setData(0, KIND_ROLE, "subject")
            subject_item.setData(0, ID_ROLE, subject.id)
            font = subject_item.font(0)
            font.setBold(True)
            subject_item.setFont(0, font)
            for session in self._db.list_sessions(subject.id):
                item = QTreeWidgetItem([session.title])
                item.setData(0, KIND_ROLE, "session")
                item.setData(0, ID_ROLE, session.id)
                item.setToolTip(0, f"Creada el {session.created_at.replace('T', ' a las ')}")
                subject_item.addChild(item)
                if session.id == select_session_id:
                    selected = item
            self.tree.addTopLevelItem(subject_item)
            subject_item.setExpanded(True)
        if selected is not None:
            self.tree.setCurrentItem(selected)
        self._reloading = False
        self.btn_session.setEnabled(self.tree.topLevelItemCount() > 0)
        if emit:
            self.session_selected.emit(select_session_id if selected is not None else None)

    def first_session_id(self) -> int | None:
        for i in range(self.tree.topLevelItemCount()):
            subject_item = self.tree.topLevelItem(i)
            if subject_item.childCount():
                return subject_item.child(0).data(0, ID_ROLE)
        for subject in self._db.list_subjects():
            sessions = self._db.list_sessions(subject.id)
            if sessions:
                return sessions[0].id
        return None

    def _on_current_changed(self, current: QTreeWidgetItem | None, _previous) -> None:
        if self._reloading or current is None:
            return
        if current.data(0, KIND_ROLE) == "session":
            self.session_selected.emit(current.data(0, ID_ROLE))

    def _current_subject_id(self) -> int | None:
        item = self.tree.currentItem()
        if item is None:
            item = self.tree.topLevelItem(0)
            if item is None:
                return None
        if item.data(0, KIND_ROLE) == "session":
            item = item.parent()
        return item.data(0, ID_ROLE)

    def _current_session_id(self) -> int | None:
        return self._controller.session.id if self._controller.session else None

    # -- actions ----------------------------------------------------------------
    def new_subject(self) -> None:
        dialog = SubjectDialog(self)
        if dialog.exec() != SubjectDialog.DialogCode.Accepted:
            return
        name, level = dialog.values()
        subject = self._db.create_subject(name, level)
        session = self._db.create_session(subject.id, default_session_title(1))
        self.reload(session.id, emit=True)

    def new_session(self) -> None:
        subject_id = self._current_subject_id()
        if subject_id is None:
            return
        number = self._db.count_sessions(subject_id) + 1
        session = self._db.create_session(subject_id, default_session_title(number))
        self.reload(session.id, emit=True)

    def _show_menu(self, pos) -> None:
        item = self.tree.itemAt(pos)
        if item is None:
            return
        kind, item_id = item.data(0, KIND_ROLE), item.data(0, ID_ROLE)
        menu = QMenu(self)
        if kind == "subject":
            menu.addAction("Nueva clase", lambda: (self.tree.setCurrentItem(item), self.new_session()))
            menu.addAction("Editar materia…", lambda: self._edit_subject(item_id))
            menu.addSeparator()
            menu.addAction("Eliminar materia…", lambda: self._delete_subject(item_id))
        else:
            menu.addAction("Renombrar clase…", lambda: self._rename_session(item_id))
            menu.addSeparator()
            menu.addAction("Eliminar clase…", lambda: self._delete_session(item_id))
        menu.exec(self.tree.viewport().mapToGlobal(pos))

    def _edit_subject(self, subject_id: int) -> None:
        subject = self._db.get_subject(subject_id)
        if subject is None:
            return
        dialog = SubjectDialog(self, title="Editar materia", name=subject.name, level=subject.level)
        if dialog.exec() == SubjectDialog.DialogCode.Accepted:
            self._db.update_subject(subject_id, *dialog.values())
            self._controller.refresh_titles()
            self.reload(self._current_session_id())

    def _rename_session(self, session_id: int) -> None:
        session = self._db.get_session(session_id)
        if session is None:
            return
        title, ok = QInputDialog.getText(self, "Renombrar clase", "Nombre de la clase:", text=session.title)
        if ok and title.strip():
            self._db.rename_session(session_id, title)
            self._controller.refresh_titles()
            self.reload(self._current_session_id())

    def _delete_session(self, session_id: int) -> None:
        session = self._db.get_session(session_id)
        if session is None:
            return
        answer = QMessageBox.question(
            self,
            "Eliminar clase",
            f"¿Eliminar «{session.title}»?\n\nSe borrarán su transcripción y su audio. Esta acción no se puede deshacer.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._controller.delete_session(session_id)
        self._reselect_after_delete()

    def _delete_subject(self, subject_id: int) -> None:
        subject = self._db.get_subject(subject_id)
        if subject is None:
            return
        count = self._db.count_sessions(subject_id)
        answer = QMessageBox.question(
            self,
            "Eliminar materia",
            f"¿Eliminar la materia «{subject.name}» y sus {count} clase(s)?\n\n"
            "Se borrarán todas sus transcripciones y audios. Esta acción no se puede deshacer.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._controller.delete_subject(subject_id)
        self._reselect_after_delete()

    def _reselect_after_delete(self) -> None:
        current = self._current_session_id()
        if current is not None:
            self.reload(current)
        else:
            self.reload()
            self.reload(self.first_session_id(), emit=True)
