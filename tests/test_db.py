from inclusiva.storage.db import Database


def test_subjects_sessions_segments_roundtrip(tmp_path):
    db = Database(tmp_path / "test.db")
    subject = db.create_subject("Historia", "1.° A")
    session = db.create_session(subject.id, "Clase 1")

    first = db.add_segment(session.id, "Hola a todos", 0, 1200, "whisper")
    second = db.add_segment(session.id, "Hoy vemos la Revolución de Mayo", 1200, 4000, "whisper", new_paragraph=True)
    assert [s.seq for s in db.list_segments(session.id)] == [1, 2]
    assert db.list_segments(session.id)[1].new_paragraph

    db.update_segment_text(first.id, "Hola a todas y todos")
    stored = db.list_segments(session.id)[0]
    assert stored.text == "Hola a todas y todos" and stored.edited

    db.delete_segment(second.id)
    assert [s.id for s in db.list_segments(session.id)] == [first.id]

    db.set_session_audio(session.id, "audio/1.ogg", 4000)
    assert db.delete_subject(subject.id) == ["audio/1.ogg"]
    assert db.get_session(session.id) is None
    assert db.list_segments(session.id) == []
    db.close()


def test_reopening_keeps_data(tmp_path):
    path = tmp_path / "test.db"
    db = Database(path)
    subject = db.create_subject("Biología")
    db.create_session(subject.id, "Clase 1")
    db.close()

    db = Database(path)
    assert [s.name for s in db.list_subjects()] == ["Biología"]
    assert db.count_sessions(subject.id) == 1
    db.close()
