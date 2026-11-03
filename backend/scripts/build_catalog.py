"""Build app/data/exercises.json from free-exercise-db (public domain) plus our Portuguese names.

Run from backend/: ``.venv/bin/python scripts/build_catalog.py``. The output is committed;
the app never downloads the dataset at runtime. Photos are served by jsDelivr from the
same pinned commit, so a future upstream change can't break or swap them.
"""

import csv
import json
import sys
import urllib.request
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.services.catalog import CATALOG_FILE as OUTPUT, search_key  # noqa: E402

SOURCE_COMMIT = "f00c92c7dcf1216a928a52c3706c7ce8e2f71ed5"
SOURCE_URL = f"https://raw.githubusercontent.com/yuhonas/free-exercise-db/{SOURCE_COMMIT}/dist/exercises.json"
IMAGE_BASE = f"https://cdn.jsdelivr.net/gh/yuhonas/free-exercise-db@{SOURCE_COMMIT}/exercises/"

KEPT_CATEGORIES = {"strength", "powerlifting"}
SKIPPED_EQUIPMENT = {"bands", "medicine ball", "exercise ball", "foam roll"}

# The dataset's 17 muscles folded into the groups people pick in a gym.
MUSCLE_GROUPS = {
    "chest": "peito",
    "lats": "costas",
    "middle back": "costas",
    "lower back": "costas",
    "traps": "costas",
    "shoulders": "ombros",
    "neck": "ombros",
    "biceps": "biceps",
    "triceps": "triceps",
    "forearms": "antebraco",
    "quadriceps": "pernas",
    "hamstrings": "pernas",
    "adductors": "pernas",
    "abductors": "pernas",
    "glutes": "gluteos",
    "calves": "panturrilha",
    "abdominals": "abdomen",
}
EQUIPMENT_PT = {
    "barbell": "Barra",
    "dumbbell": "Halteres",
    "cable": "Cabo",
    "machine": "Máquina",
    "body only": "Peso corporal",
    "kettlebells": "Kettlebell",
    "e-z curl bar": "Barra W",
    "other": "Outros",
    None: "Outros",
}

TRANSLATIONS = BACKEND / "scripts" / "catalog_pt.tsv"


def main() -> None:
    """Download, filter, translate and write the catalog."""
    with urllib.request.urlopen(SOURCE_URL, timeout=60) as response:
        source = json.load(response)
    names_pt = _load_translations()
    catalog = [_convert(item, names_pt) for item in source if _is_gym_exercise(item)]
    missing = [item["id"] for item in catalog if not item["name_pt"]]
    if missing:
        raise SystemExit(f"Missing Portuguese names for: {', '.join(missing)}")
    OUTPUT.write_text(json.dumps(catalog, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Wrote {len(catalog)} exercises to {OUTPUT.relative_to(BACKEND)}")


def _is_gym_exercise(item: dict) -> bool:
    """Strength work with common gym equipment and at least one photo."""
    return (
        item["category"] in KEPT_CATEGORIES
        and item.get("equipment") not in SKIPPED_EQUIPMENT
        and bool(item["images"])
    )


def _convert(item: dict, names_pt: dict[str, str]) -> dict:
    """Keep only what the app shows or searches."""
    name_pt = names_pt.get(item["id"], "")
    return {
        "id": item["id"],
        "name_pt": name_pt,
        "name_en": item["name"],
        "muscle_group": MUSCLE_GROUPS[item["primaryMuscles"][0]],
        "equipment": EQUIPMENT_PT[item.get("equipment")],
        "images": [IMAGE_BASE + path for path in item["images"][:2]],
        "search_text": search_key(f"{name_pt} {item['name']}"),
    }


def _load_translations() -> dict[str, str]:
    """Map dataset id to Portuguese name from the reviewed TSV (id, name)."""
    with TRANSLATIONS.open(encoding="utf-8", newline="") as file:
        return {row[0]: row[1].strip() for row in csv.reader(file, delimiter="\t") if row}


if __name__ == "__main__":
    main()
