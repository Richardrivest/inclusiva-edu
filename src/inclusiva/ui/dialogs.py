from __future__ import annotations

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QVBoxLayout, QWidget

from .widgets import label


class SubjectDialog(QDialog):
    def __init__(self, parent: QWidget | None = None, *, title: str = "Nueva materia", name: str = "", level: str = ""):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(420)

        self.name_edit = QLineEdit(name)
        self.name_edit.setPlaceholderText("Ej.: Lengua y Literatura, Historia Argentina…")
        self.level_edit = QLineEdit(level)
        self.level_edit.setPlaceholderText("Ej.: 1.° año A, Nivel secundario…")

        form = QFormLayout()
        form.setSpacing(10)
        form.addRow("Nombre de la materia", self.name_edit)
        form.addRow("Año / nivel / curso", self.level_edit)

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.button(QDialogButtonBox.StandardButton.Save).setText("Guardar")
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setProperty("variant", "secondary")
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)
        layout.addWidget(label(title, name="cardTitle"))
        layout.addLayout(form)
        layout.addWidget(self.buttons)

        self.name_edit.textChanged.connect(self._validate)
        self._validate()

    def _validate(self) -> None:
        self.buttons.button(QDialogButtonBox.StandardButton.Save).setEnabled(bool(self.name_edit.text().strip()))

    def values(self) -> tuple[str, str]:
        return self.name_edit.text().strip(), self.level_edit.text().strip()
