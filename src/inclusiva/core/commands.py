"""Spoken editing commands recognised inside the dictation stream.

Only multi-word commands are supported. Single words such as "punto" or "coma" are too common
in real lessons ("el punto de fusión", "estado de coma"), and both speech engines already add
punctuation on their own.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_TERMINAL = ".?!…:;"

_COMMAND_RE = re.compile(
    r"[\s,.;:]*\b(?:"
    r"(?P<end>punto\s+(?:y\s+)?a\s*parte)"
    r"|(?P<para>nuevo\s+p[áa]rrafo|nueva\s+l[íi]nea)"
    r"|(?P<delete>borr(?:ar|a|á)\s+(?:la\s+)?[úu]ltima\s+(?:frase|l[íi]nea|oraci[óo]n))"
    r")\b[\s,.;:!?]*",
    re.IGNORECASE,
)


@dataclass
class Piece:
    text: str
    new_paragraph: bool = False


@dataclass
class CommandResult:
    pieces: list[Piece] = field(default_factory=list)
    delete_last: int = 0  # previously stored segments to delete
    close_previous: bool = False  # add a full stop to the previously stored segment
    pending_paragraph: bool = False  # the next segment starts a new paragraph


def ensure_terminal_period(text: str) -> str:
    stripped = text.rstrip().rstrip(",").rstrip()
    if stripped and stripped[-1] not in _TERMINAL:
        stripped += "."
    return stripped


def apply_voice_commands(text: str) -> CommandResult:
    result = CommandResult()
    buffer = ""
    new_paragraph = False
    pos = 0

    def flush() -> None:
        nonlocal buffer, new_paragraph
        clean = " ".join(buffer.split())
        if clean:
            result.pieces.append(Piece(clean, new_paragraph))
            new_paragraph = False
        buffer = ""

    for match in _COMMAND_RE.finditer(text):
        buffer += text[pos : match.start()]
        pos = match.end()
        if match.group("end"):
            if buffer.strip():
                buffer = ensure_terminal_period(buffer)
            elif result.pieces:
                result.pieces[-1].text = ensure_terminal_period(result.pieces[-1].text)
            else:
                result.close_previous = True
            flush()
            new_paragraph = True
        elif match.group("para"):
            flush()
            new_paragraph = True
        else:  # "borrar última frase"
            if buffer.strip():
                buffer = ""
            elif result.pieces:
                result.pieces.pop()
            else:
                result.delete_last += 1

    buffer += text[pos:]
    flush()
    result.pending_paragraph = new_paragraph
    return result
