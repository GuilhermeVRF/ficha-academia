"""The shared exercise library shipped with the app (built by scripts/build_catalog.py)."""

import json
import unicodedata
from pathlib import Path

CATALOG_FILE = Path(__file__).resolve().parent.parent / "data" / "exercises.json"

MUSCLE_GROUPS = ("peito", "costas", "ombros", "biceps", "triceps", "antebraco", "pernas", "gluteos", "panturrilha", "abdomen")


def load_library() -> list[dict]:
    """Rows for the catalog_exercise table, without owner (shared by everyone)."""
    rows = json.loads(CATALOG_FILE.read_text(encoding="utf-8"))
    return [{**row, "user_id": None} for row in rows]


def search_key(text: str) -> str:
    """Lowercase without accents, matching how search_text is stored."""
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(char for char in decomposed if not unicodedata.combining(char))
