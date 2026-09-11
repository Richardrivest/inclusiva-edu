"""Teacher controls for the student screen: preview, placement, what is shown, appearance."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication, QScreen
from PySide6.QtWidgets import QButtonGroup, QCheckBox, QComboBox, QMessageBox, QSlider

from ..core.live import ClassroomController
from ..core.projector import ProjectorState
from .canvas import AspectBox, ProjectorCanvas, visible_lines
from .projector_window import ProjectorWindow, describe_screen
from .theme import CAPTION_THEMES
from .widgets import Card, button, hrow, label


class ProjectorPanel(Card):
    def __init__(self, state: ProjectorState, window: ProjectorWindow, controller: ClassroomController):
        super().__init__("Pantalla de estudiantes")
        self._state = state
        self._window = window
        self._controller = controller

        # Preview
        self.canvas = ProjectorCanvas(state)
        self.preview = AspectBox(self.canvas)
        self.placement_label = label(name="muted", wrap=True)
        self.body.addWidget(self.preview)
        self.body.addWidget(self.placement_label)

        # Where
        self.body.addWidget(label("DÓNDE SE MUESTRA", name="section"))
        self.screen_combo = QComboBox()
        self.screen_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.screen_combo.setMinimumContentsLength(12)
        self.btn_fullscreen = button("Pantalla completa", tooltip="Mostrar la pantalla de estudiantes en la pantalla elegida")
        self.btn_window = button("Ventana", variant="secondary", tooltip="Mostrarla en una ventana que puedes mover")
        self.btn_hide = button("Ocultar", variant="secondary")
        self.body.addWidget(self.screen_combo)
        self.body.addLayout(hrow(self.btn_fullscreen, self.btn_window, self.btn_hide, stretch_index=0))

        # What
        self.body.addWidget(label("QUÉ VEN LOS ESTUDIANTES", name="section"))
        self.btn_captions = button("Subtítulos", variant="toggle", checkable=True)
        self.btn_blank = button("En blanco", variant="toggle", checkable=True, tooltip="Oculta el texto (Ctrl+B)")
        self.btn_freeze = button(
            "Congelar", variant="freeze", checkable=True, tooltip="Detiene el texto en pantalla para leerlo con calma (Ctrl+Shift+F)"
        )
        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)
        self.mode_group.addButton(self.btn_captions)
        self.mode_group.addButton(self.btn_blank)
        self.body.addLayout(hrow(self.btn_captions, self.btn_blank, self.btn_freeze))
        self.btn_new_page = button(
            "Página nueva", variant="secondary", tooltip="Limpia la pantalla sin borrar la transcripción (Ctrl+L)"
        )
        self.btn_show_all = button("Mostrar todo", variant="secondary", tooltip="Vuelve a mostrar toda la clase")
        self.body.addLayout(hrow(self.btn_new_page, self.btn_show_all))

        # Appearance
        self.body.addWidget(label("APARIENCIA", name="section"))
        self.size_slider = QSlider(Qt.Orientation.Horizontal)
        self.size_slider.setRange(28, 160)
        self.size_slider.setSingleStep(2)
        self.size_slider.setPageStep(8)
        self.size_value = label(name="muted")
        self.body.addWidget(label("Tamaño del texto"))
        self.body.addLayout(hrow(self.size_slider, self.size_value, stretch_index=0))
        self.theme_combo = QComboBox()
        for theme in CAPTION_THEMES.values():
            self.theme_combo.addItem(theme.name, theme.key)
        self.body.addWidget(label("Colores"))
        self.body.addWidget(self.theme_combo)
        self.header_check = QCheckBox("Mostrar materia, clase y estado arriba")
        self.body.addWidget(self.header_check)
        self.body.addStretch(1)

        # Initial values
        self.size_slider.setValue(state.font_px)
        self._update_size_label(state.font_px)
        self.theme_combo.setCurrentIndex(max(0, self.theme_combo.findData(state.theme_key)))
        self.header_check.setChecked(state.show_header)
        self._sync_from_state()

        # Signals
        self.btn_fullscreen.clicked.connect(self._fullscreen_clicked)
        self.btn_window.clicked.connect(window.show_preview_window)
        self.btn_hide.clicked.connect(window.hide_projector)
        self.btn_captions.clicked.connect(lambda: state.set_mode("captions"))
        self.btn_blank.clicked.connect(lambda: state.set_mode("blank"))
        self.btn_freeze.toggled.connect(state.set_frozen)
        self.btn_new_page.clicked.connect(controller.new_projector_page)
        self.btn_show_all.clicked.connect(controller.show_whole_transcript)
        self.size_slider.valueChanged.connect(self._size_changed)
        self.theme_combo.currentIndexChanged.connect(lambda _: state.set_theme(self.theme_combo.currentData()))
        self.header_check.toggled.connect(state.set_show_header)
        state.changed.connect(self._sync_from_state)
        window.placement_changed.connect(self._update_placement)
        app = QGuiApplication.instance()
        app.screenAdded.connect(lambda _: QTimer.singleShot(0, self._update_placement))
        app.screenRemoved.connect(lambda _: QTimer.singleShot(0, self._update_placement))
        self._update_placement()

    # -- shortcuts ----------------------------------------------------------------
    def toggle_blank(self) -> None:
        self._state.set_mode("captions" if self._state.mode == "blank" else "blank")

    def toggle_freeze(self) -> None:
        self.btn_freeze.toggle()

    # -- internals ----------------------------------------------------------------
    def _sync_from_state(self) -> None:
        for btn, checked in (
            (self.btn_captions, self._state.mode == "captions"),
            (self.btn_blank, self._state.mode == "blank"),
            (self.btn_freeze, self._state.frozen),
        ):
            if btn.isChecked() != checked:
                btn.blockSignals(True)
                btn.setChecked(checked)
                btn.blockSignals(False)

    def _size_changed(self, value: int) -> None:
        self._state.set_font_px(value)
        self._update_size_label(value)

    def _update_size_label(self, value: int) -> None:
        self.size_value.setText(f"≈ {visible_lines(value)} líneas")

    def _refresh_screens(self) -> None:
        current = self.screen_combo.currentData()
        target = self._window.fullscreen_screen
        primary = QGuiApplication.primaryScreen()
        self.screen_combo.blockSignals(True)
        self.screen_combo.clear()
        for screen in QGuiApplication.screens():
            self.screen_combo.addItem(describe_screen(screen), screen.name())
        preferred = target.name() if target is not None else current
        index = self.screen_combo.findData(preferred) if preferred else -1
        if index < 0:  # default to the first screen that is not this computer's
            index = next(
                (i for i, s in enumerate(QGuiApplication.screens()) if s != primary), self.screen_combo.count() - 1
            )
        self.screen_combo.setCurrentIndex(max(0, index))
        self.screen_combo.blockSignals(False)

    def _selected_screen(self) -> QScreen | None:
        name = self.screen_combo.currentData()
        return next((s for s in QGuiApplication.screens() if s.name() == name), None)

    def _fullscreen_clicked(self) -> None:
        screen = self._selected_screen()
        if screen is None:
            return
        if screen == QGuiApplication.primaryScreen():
            answer = QMessageBox.question(
                self,
                "Pantalla completa",
                "La pantalla elegida es la de esta computadora, así que cubrirá la ventana del docente.\n\n"
                "Para volver, presiona Esc (o haz doble clic) en la pantalla de estudiantes. ¿Continuar?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        self._window.show_fullscreen_on(screen)

    def _update_placement(self) -> None:
        self._refresh_screens()
        placement = self._window.placement
        target = self._window.fullscreen_screen
        if placement == "fullscreen" and target is not None:
            text = f"En pantalla completa: {describe_screen(target)}."
            geometry = target.geometry()
            self.preview.set_aspect(geometry.width() / max(1, geometry.height()))
        elif placement == "window":
            text = "Se muestra en una ventana. Puedes arrastrarla al proyector o usar «Pantalla completa»."
            self.preview.set_aspect(16 / 9)
        elif len(QGuiApplication.screens()) == 1:
            text = "No hay proyector conectado. Al conectarlo, la pantalla de estudiantes se abrirá sola en él."
            self.preview.set_aspect(16 / 9)
        else:
            text = "La pantalla de estudiantes está oculta."
        self.placement_label.setText(text)
        self.btn_hide.setEnabled(placement != "hidden")
        self.btn_window.setEnabled(placement != "window")
