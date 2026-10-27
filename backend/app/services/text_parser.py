"""Parse a free-text routine (as pasted from WhatsApp, a PDF, notes...) into workouts.

Supported line formats::

    Treino A:                      -> starts a new workout block
    Supino reto 3x10 40kg          -> 3 sets of 10 reps at 40 kg
    Rosca direta 12,10,8 20,5kg    -> sets of 12, 10 and 8 reps at 20.5 kg
    Leg press 4x12                 -> weight defaults to 0
    Prancha                        -> defaults to 3x10, flagged with a warning
"""

import re
from dataclasses import dataclass, field

DEFAULT_SET_COUNT = 3
DEFAULT_REPS = 10
MAX_SETS = 20

_BULLET = re.compile(r"^\s*(?:[-*•–]|\d+[.)])\s*")
_HEADER = re.compile(r"^(?:(?:treino|ficha|dia|day|workout)\b.*|[A-Za-z])\s*:?\s*$", re.IGNORECASE)
_SETS_BY_REPS = re.compile(r"^(\d{1,2})x(\d{1,3})(?:-\d{1,3})?$", re.IGNORECASE)
_REPS_LIST = re.compile(r"^\d{1,3}(?:[,/]\d{1,3})+$")
_WEIGHT = re.compile(r"^(\d{1,4}(?:[.,]\d{1,2})?)(?:kg)?$", re.IGNORECASE)


@dataclass
class ParsedExercise:
    """An exercise extracted from one line."""

    name: str
    sets: list[tuple[float, int]]
    warning: str | None = None


@dataclass
class ParsedWorkout:
    """A block of exercises; ``name`` is None for lines before any header."""

    name: str | None
    exercises: list[ParsedExercise] = field(default_factory=list)


def parse_routine(text: str) -> list[ParsedWorkout]:
    """Split pasted text into workout blocks and exercises.

    Args:
        text: Multi-line routine description.

    Returns:
        Workout blocks in order of appearance, without empty ones.
    """
    blocks = [ParsedWorkout(name=None)]
    for raw_line in text.splitlines():
        line = _clean_line(raw_line)
        if not line:
            continue
        if _is_header(line):
            blocks.append(ParsedWorkout(name=line.rstrip(":").strip()))
            continue
        blocks[-1].exercises.append(parse_exercise_line(line))
    return [block for block in blocks if block.exercises]


def _clean_line(line: str) -> str:
    """Strip bullets, numbering and normalize ``3 x 10`` / ``40 kg`` spacing."""
    line = _BULLET.sub("", line).strip()
    line = re.sub(r"(\d)\s*[xX×]\s*(\d)", r"\1x\2", line)
    line = re.sub(r"(\d)\s+kg\b", r"\1kg", line, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", line)


def _is_header(line: str) -> bool:
    """Tell whether a line names a workout block instead of an exercise."""
    if _find_reps_token(line.split(" ")) is not None:
        return False
    return line.endswith(":") or bool(_HEADER.match(line))


def parse_exercise_line(line: str) -> ParsedExercise:
    """Parse a single cleaned exercise line.

    Args:
        line: Line already normalized by ``_clean_line``.

    Returns:
        The parsed exercise; lines without a reps token get default sets
        and a warning so the user can review them in the preview.
    """
    tokens = line.split(" ")
    reps_index = _find_reps_token(tokens)
    if reps_index is None or reps_index == 0:
        default_sets = [(0.0, DEFAULT_REPS)] * DEFAULT_SET_COUNT
        return ParsedExercise(name=line, sets=default_sets, warning="Séries não informadas; usando 3x10.")

    name = " ".join(tokens[:reps_index])
    reps_per_set = _parse_reps(tokens[reps_index])
    weight = _find_weight(tokens[reps_index + 1 :])
    return ParsedExercise(name=name, sets=[(weight, reps) for reps in reps_per_set])


def _find_reps_token(tokens: list[str]) -> int | None:
    """Return the index of the first ``NxR`` or ``R,R,R`` token, if any."""
    for index, token in enumerate(tokens):
        if _SETS_BY_REPS.match(token) or _REPS_LIST.match(token):
            return index
    return None


def _parse_reps(token: str) -> list[int]:
    """Expand a reps token into one reps value per set."""
    match = _SETS_BY_REPS.match(token)
    if match:
        set_count = min(int(match.group(1)), MAX_SETS)
        return [int(match.group(2))] * set_count
    return [int(value) for value in re.split(r"[,/]", token)][:MAX_SETS]


def _find_weight(tokens: list[str]) -> float:
    """Return the first weight-looking token after the reps, or 0."""
    for token in tokens:
        match = _WEIGHT.match(token)
        if match:
            return float(match.group(1).replace(",", "."))
    return 0.0
