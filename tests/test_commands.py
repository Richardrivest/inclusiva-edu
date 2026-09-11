from inclusiva.core.commands import apply_voice_commands, ensure_terminal_period


def pieces(text):
    return [(p.text, p.new_paragraph) for p in apply_voice_commands(text).pieces]


def test_plain_text_is_untouched():
    result = apply_voice_commands("Hoy vemos el punto de fusión y el estado de coma")
    assert pieces("Hoy vemos el punto de fusión y el estado de coma") == [
        ("Hoy vemos el punto de fusión y el estado de coma", False)
    ]
    assert not result.pending_paragraph and not result.close_previous and result.delete_last == 0


def test_punto_y_aparte_splits_into_paragraphs():
    assert pieces("Esto es el final punto y aparte ahora empieza otro tema") == [
        ("Esto es el final.", False),
        ("ahora empieza otro tema", True),
    ]


def test_trailing_command_leaves_pending_paragraph():
    result = apply_voice_commands("Terminamos la idea. Punto y aparte.")
    assert [(p.text, p.new_paragraph) for p in result.pieces] == [("Terminamos la idea.", False)]
    assert result.pending_paragraph


def test_command_alone_closes_previous_segment():
    result = apply_voice_commands("Punto y aparte")
    assert result.pieces == []
    assert result.close_previous and result.pending_paragraph


def test_whisper_spelling_a_parte():
    result = apply_voice_commands("fin, punto y a parte.")
    assert [(p.text, p.new_paragraph) for p in result.pieces] == [("fin.", False)]
    assert result.pending_paragraph


def test_new_paragraph_command():
    assert pieces("primera parte, nuevo párrafo segunda parte") == [("primera parte", False), ("segunda parte", True)]


def test_delete_within_same_utterance():
    result = apply_voice_commands("esto está mal borrar última frase esto está bien")
    assert [p.text for p in result.pieces] == ["esto está bien"]
    assert result.delete_last == 0


def test_delete_previous_segment():
    result = apply_voice_commands("Borrar última frase.")
    assert result.pieces == [] and result.delete_last == 1


def test_ensure_terminal_period():
    assert ensure_terminal_period("hola,") == "hola."
    assert ensure_terminal_period("¿qué es?") == "¿qué es?"
