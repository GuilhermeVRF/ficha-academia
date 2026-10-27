"""Tests for the free-text routine parser."""

import pytest

from app.services.text_parser import parse_exercise_line, parse_routine


@pytest.mark.parametrize(
    ("line", "name", "sets"),
    [
        ("Supino reto 3x10 40kg", "Supino reto", [(40.0, 10)] * 3),
        ("Supino reto 3 x 10 40 kg", "Supino reto", [(40.0, 10)] * 3),
        ("Rosca direta 12,10,8 20,5kg", "Rosca direta", [(20.5, 12), (20.5, 10), (20.5, 8)]),
        ("Puxada 12/10/8 50", "Puxada", [(50.0, 12), (50.0, 10), (50.0, 8)]),
        ("Leg press 4x12", "Leg press", [(0.0, 12)] * 4),
        ("Elevação lateral 3X8-12 c/ 8kg", "Elevação lateral", [(8.0, 8)] * 3),
        ("Supino 45 graus 3×10 30.5kg", "Supino 45 graus", [(30.5, 10)] * 3),
    ],
)
def test_should_parse_supported_exercise_formats(line: str, name: str, sets: list) -> None:
    result = parse_routine(line)[0].exercises[0]

    assert result.name == name
    assert result.sets == sets
    assert result.warning is None


def test_should_default_to_three_by_ten_with_warning_when_reps_are_missing() -> None:
    result = parse_exercise_line("Prancha")

    assert result.sets == [(0.0, 10)] * 3
    assert result.warning is not None


def test_should_split_blocks_on_headers_and_strip_bullets() -> None:
    text = """
    Treino A - Peito:
    1. Supino reto 4x10 40kg
    - Crucifixo 3x12 14kg

    B:
    • Agachamento 4x8 60kg
    """

    blocks = parse_routine(text)

    assert [block.name for block in blocks] == ["Treino A - Peito", "B"]
    assert [exercise.name for exercise in blocks[0].exercises] == ["Supino reto", "Crucifixo"]
    assert blocks[1].exercises[0].sets == [(60.0, 8)] * 4


def test_should_keep_lines_before_any_header_in_an_unnamed_block() -> None:
    blocks = parse_routine("Supino 3x10 40kg\nTreino B\nRemada 3x10 30kg")

    assert [block.name for block in blocks] == [None, "Treino B"]
