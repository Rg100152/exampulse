#!/usr/bin/env python3
"""Build the four JSON question banks from the offline authoring modules.

    python generate_question_banks.py

The generator modules in generators/ are plain Python lists of questions; this
script validates them and writes data/*.json. No API calls, no randomness and no
network access - the output is deterministic and reproducible.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from exampulse_core import DATA_DIR, SUBJECTS, validate_item

GENERATORS = Path(__file__).resolve().parent / "generators"
MODULE_FOR_SLUG = {
    "python": "python_bank.py",
    "datamining": "datamining_bank.py",
    "dotnet": "dotnet_bank.py",
    "webdesign": "webdesign_bank.py",
}


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    grand_total = 0
    for slug, meta in SUBJECTS.items():
        module_path = GENERATORS / MODULE_FOR_SLUG[slug]
        if not module_path.exists():
            print(f"[SKIP] {module_path.name} not found", file=sys.stderr)
            continue
        module = load_module(module_path)
        items = getattr(module, "QUESTIONS", None)
        if items is None:
            raise ValueError(f"{module_path.name} has no QUESTIONS list")

        seen: set[str] = set()
        for index, item in enumerate(items, start=1):
            problems = validate_item(item, slug, meta["topics"])
            if problems:
                raise ValueError(f"{slug} #{index}: {'; '.join(problems)}")
            key = " ".join(item["question"].casefold().split())
            if key in seen:
                raise ValueError(f"{slug} #{index}: duplicate question text")
            seen.add(key)
        if len(items) != 250:
            raise ValueError(f"{slug}: expected 250 questions, got {len(items)}")

        payload = {
            "subject": slug,
            "title": meta["name"],
            "total_questions": len(items),
            "questions": items,
        }
        out_path = DATA_DIR / meta["file"]
        with out_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        grand_total += len(items)
        print(f"[OK] {out_path.relative_to(DATA_DIR.parent)}  -> {len(items)} questions")
    print(f"\nTotal written: {grand_total}")
    return 0 if grand_total == 1000 else 1


if __name__ == "__main__":
    raise SystemExit(main())
