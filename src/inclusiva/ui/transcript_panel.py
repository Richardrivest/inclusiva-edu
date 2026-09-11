"""The teacher's editable transcript of the open class."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QLineEdit,
    QMenu,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
)

from ..core.live import ClassroomController
from ..core.models import Segment, Session
from .widgets import Card, button, hrow, label

ID_ROLE = int(Qt.ItemDataRole.UserRole)
EDITED_COLOR = QColor("#bfdbfe")
TIME_COLOR = QColor("#a5b4fc")


def format_ms(ms: int | None) -> str:
    if ms is None:
        return "✎"
    seconds = ms // 1000
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes:02d}:{secs:02d}"


class SegmentTable(QTableWidget):
    delete_requested = Signal(list)

    def __init__(self):
        super().__init__(0, 2)
        self.setHorizontalHeaderLabels(["Tiempo", "Texto"])
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setHighlightSections(False)
        self.verticalHeader().setVisible(False)
        self.setWordWrap(True)
        self.setShowGrid(False)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked | QAbstractItemView.EditTrigger.EditKeyPressed)
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        font = self.font()
        font.setPointSizeF(11.5)
        self.setFont(font)

    def selected_ids(self) -> list[int]:
        rows = sorted({index.row() for index in self.selectedIndexes()})
        return [self.item(r, 1).data(ID_ROLE) for r in rows if self.item(r, 1) is not None]

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Delete and self.state() != QAbstractItemView.State.EditingState:
            ids = self.selected_ids()
            if ids:
                self.delete_requested.emit(ids)
                return
        super().keyPressEvent(event)


class TranscriptPanel(Card):
    def __init__(self, controller: ClassroomController):
        super().__init__("Pizarra transcrita de la clase")
        self._controller = controller
        self._loading = False

        self.session_label = label(name="muted")
        self.header.addWidget(self.session_label)

        self.btn_live = button(
            "🎙  Iniciar transcripción",
            tooltip="El reconocimiento de voz se incorpora en el próximo paso del desarrollo.",
        )
        self.btn_live.setEnabled(False)
        self.engine_label = label("Reconocimiento de voz: disponible en el próximo paso", name="muted")
        self.body.addLayout(hrow(self.btn_live, self.engine_label, stretch_index=1))

        self.table = SegmentTable()
        self.body.addWidget(self.table, 1)

        self.entry = QLineEdit()
        self.entry.setPlaceholderText("Escribe aquí para agregar texto a la pantalla y presiona Enter…")
        self.btn_add = button("Agregar")
        self.btn_paragraph = button(
            "¶  Nuevo párrafo", variant="secondary", tooltip="La próxima frase comenzará un párrafo nuevo en la pantalla."
        )
        self.body.addLayout(hrow(self.entry, self.btn_add, self.btn_paragraph, stretch_index=0))
        self.body.addWidget(
            label(
                "Comandos de voz: «punto y aparte» · «nuevo párrafo» · «borrar última frase».  "
                "Doble clic sobre una frase para corregirla (el cambio aparece en el proyector); Supr para eliminarla.",
                name="hint",
                wrap=True,
            )
        )

        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.setInterval(60)
        self._resize_timer.timeout.connect(self.table.resizeRowsToContents)

        self.entry.returnPressed.connect(self._submit)
        self.btn_add.clicked.connect(self._submit)
        self.btn_paragraph.clicked.connect(controller.request_new_paragraph)
        self.table.itemChanged.connect(self._on_item_changed)
        self.table.delete_requested.connect(self._delete_ids)
        self.table.customContextMenuRequested.connect(self._show_menu)
        self.table.horizontalHeader().sectionResized.connect(lambda *_: self._resize_timer.start())

        controller.session_changed.connect(self._on_session_changed)
        controller.segments_reset.connect(self._reload)
        controller.segment_added.connect(self._append_row)
        controller.segment_updated.connect(self._update_row)
        controller.segment_removed.connect(self._remove_row)
        self._on_session_changed(controller.session)

    # -- controller → table -----------------------------------------------------
    def _on_session_changed(self, session: Session | None) -> None:
        subject = self._controller.subject
        if session is None:
            self.session_label.setText("Ninguna clase seleccionada")
        else:
            self.session_label.setText(f"{subject.name} · {session.title}" if subject else session.title)
        for widget in (self.entry, self.btn_add, self.btn_paragraph, self.table):
            widget.setEnabled(session is not None)

    def _reload(self) -> None:
        self._loading = True
        self.table.setRowCount(0)
        for segment in self._controller.segments:
            self._insert(self.table.rowCount(), segment)
        self._loading = False
        self.table.resizeRowsToContents()
        self.table.scrollToBottom()

    def _append_row(self, segment: Segment) -> None:
        bar = self.table.verticalScrollBar()
        at_bottom = bar.value() >= bar.maximum() - 4
        self._loading = True
        row = self.table.rowCount()
        self._insert(row, segment)
        self._loading = False
        self.table.resizeRowToContents(row)
        if at_bottom:
            self.table.scrollToBottom()

    def _update_row(self, segment: Segment) -> None:
        row = self._row_of(segment.id)
        if row is None:
            return
        self._loading = True
        self._style_text_item(self.table.item(row, 1), segment)
        self._loading = False
        self.table.resizeRowToContents(row)

    def _remove_row(self, segment_id: int) -> None:
        row = self._row_of(segment_id)
        if row is not None:
            self.table.removeRow(row)

    def _insert(self, row: int, segment: Segment) -> None:
        self.table.insertRow(row)
        time_item = QTableWidgetItem(("¶ " if segment.new_paragraph else "") + format_ms(segment.start_ms))
        time_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        time_item.setForeground(TIME_COLOR)
        time_item.setData(ID_ROLE, segment.id)
        if segment.start_ms is None:
            time_item.setToolTip("Texto escrito por el docente")
        text_item = QTableWidgetItem()
        text_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable)
        text_item.setData(ID_ROLE, segment.id)
        self._style_text_item(text_item, segment)
        self.table.setItem(row, 0, time_item)
        self.table.setItem(row, 1, text_item)

    @staticmethod
    def _style_text_item(item: QTableWidgetItem, segment: Segment) -> None:
        item.setText(segment.text)
        if segment.edited:
            item.setForeground(EDITED_COLOR)
            item.setToolTip("Corregido por el docente")

    def _row_of(self, segment_id: int) -> int | None:
        for row in range(self.table.rowCount() - 1, -1, -1):
            item = self.table.item(row, 1)
            if item is not None and item.data(ID_ROLE) == segment_id:
                return row
        return None

    # -- table → controller -----------------------------------------------------
    def _submit(self) -> None:
        text = self.entry.text().strip()
        if text:
            self._controller.add_manual_text(text)
            self.entry.clear()

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if self._loading or item.column() != 1:
            return
        self._controller.edit_segment(item.data(ID_ROLE), item.text())

    def _delete_ids(self, ids: list[int]) -> None:
        if len(ids) > 1:
            answer = QMessageBox.question(
                self,
                "Eliminar frases",
                f"¿Eliminar las {len(ids)} frases seleccionadas?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        for segment_id in ids:
            self._controller.delete_segment(segment_id)

    def _show_menu(self, pos) -> None:
        item = self.table.itemAt(pos)
        if item is None:
            return
        text_item = self.table.item(item.row(), 1)
        menu = QMenu(self)
        menu.addAction("Corregir frase", lambda: self.table.editItem(text_item))
        menu.addAction("Eliminar", lambda: self._delete_ids(self.table.selected_ids() or [text_item.data(ID_ROLE)]))
        menu.exec(self.table.viewport().mapToGlobal(pos))
