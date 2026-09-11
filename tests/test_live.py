import pytest

from inclusiva.config import Settings
from inclusiva.core.live import ClassroomController, build_paragraphs, split_span
from inclusiva.core.projector import ProjectorState
from inclusiva.storage.db import Database


@pytest.fixture
def classroom():
    db = Database(":memory:")
    subject = db.create_subject("Física")
    session = db.create_session(subject.id, "Clase 1")
    state = ProjectorState(Settings())
    controller = ClassroomController(db, state)
    controller.open_session(session.id)
    yield controller, state
    db.close()


def texts(controller):
    return [s.text for s in controller.segments]


def test_recognized_text_is_stored_and_projected(classroom):
    controller, state = classroom
    controller.add_recognized_text("hoy vemos la energía", 0, 2000, "whisper")
    controller.add_recognized_text("y el trabajo.", 2000, 3500, "whisper")
    assert texts(controller) == ["Hoy vemos la energía", "y el trabajo."]
    paragraphs, _, _ = state.content()
    assert paragraphs == ["Hoy vemos la energía y el trabajo."]


def test_paragraph_command_starts_new_paragraph_on_projector(classroom):
    controller, state = classroom
    controller.add_recognized_text("primera idea punto y aparte", 0, 1000, "whisper")
    controller.add_recognized_text("segunda idea", 1000, 2000, "whisper")
    paragraphs, _, _ = state.content()
    assert paragraphs == ["Primera idea.", "Segunda idea"]


def test_delete_command_removes_previous_segment(classroom):
    controller, _ = classroom
    controller.add_recognized_text("frase equivocada", 0, 1000, "whisper")
    controller.add_recognized_text("borrar última frase", 1000, 2000, "whisper")
    assert texts(controller) == []
    assert controller.db.list_segments(controller.session.id) == []


def test_edit_updates_projector_and_marks_edited(classroom):
    controller, state = classroom
    controller.add_recognized_text("la fotosíntecis", 0, 1000, "whisper")
    segment = controller.segments[0]
    controller.edit_segment(segment.id, "La fotosíntesis")
    assert controller.segments[0].edited
    assert state.content()[0] == ["La fotosíntesis"]


def test_typed_text_gets_its_own_line(classroom):
    controller, state = classroom
    controller.add_recognized_text("anotamos la fórmula", 0, 1000, "whisper")
    controller.add_manual_text("Ep = m · g · h")
    controller.add_recognized_text("donde m es la masa", 1000, 2000, "whisper")
    assert state.content()[0] == ["Anotamos la fórmula", "Ep = m · g · h", "Donde m es la masa"]


def test_freeze_keeps_snapshot_until_released(classroom):
    controller, state = classroom
    controller.add_recognized_text("antes", 0, 500, "whisper")
    state.set_frozen(True)
    controller.add_recognized_text("después", 500, 1000, "whisper")
    assert state.content()[0] == ["Antes"]
    state.set_frozen(False)
    assert state.content()[0] == ["Antes después"]


def test_new_page_hides_old_text_but_keeps_transcript(classroom):
    controller, state = classroom
    controller.add_recognized_text("tema viejo.", 0, 500, "whisper")
    controller.new_projector_page()
    controller.add_recognized_text("tema nuevo.", 500, 1000, "whisper")
    assert state.content()[0] == ["Tema nuevo."]
    assert texts(controller) == ["Tema viejo.", "Tema nuevo."]
    controller.show_whole_transcript()
    assert state.content()[0] == ["Tema viejo. Tema nuevo."]


def test_split_span_is_proportional():
    assert split_span(0, 1000, ["aaaa", "a"]) == [(0, 800), (800, 1000)]
    assert split_span(None, None, ["a", "b"]) == [(None, None), (None, None)]


def test_build_paragraphs_empty():
    assert build_paragraphs([]) == []
