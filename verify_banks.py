#!/usr/bin/env python3
"""Final integrity report for the four generated question banks.

    python verify_banks.py
"""

from __future__ import annotations

import collections
import json
import sys

from exampulse_core import DATA_DIR, SUBJECTS, load_bank_file, validate_item


def main() -> int:
    grand_total = 0
    failures = 0
    global_questions: dict[str, str] = {}
    print(f"{'Subject':<26} {'Count':>6} {'Easy':>6} {'Medium':>7} {'Hard':>6} {'A/B/C/D':>12}")
    print("-" * 70)
    for slug, meta in SUBJECTS.items():
        try:
            items = load_bank_file(DATA_DIR / meta["file"])
        except (OSError, json.JSONDecodeError) as exc:
            print(f"{meta['name']:<26} MISSING/INVALID: {exc}")
            failures += 1
            continue
        errors = []
        seen = set()
        for i, item in enumerate(items, start=1):
            errors.extend(f"#{i}: {e}" for e in validate_item(item, slug, meta["topics"]))
            key = " ".join(item["question"].casefold().split())
            if key in seen:
                errors.append(f"#{i}: duplicate question")
            seen.add(key)
            if key in global_questions:
                errors.append(f"#{i}: also in {global_questions[key]}")
            global_questions[key] = slug
        difficulties = collections.Counter(x["difficulty"] for x in items)
        letters = collections.Counter(x["correct_option"] for x in items)
        print(
            f"{meta['name']:<26} {len(items):>6} {difficulties['Easy']:>6} "
            f"{difficulties['Medium']:>7} {difficulties['Hard']:>6} "
            f"{'/'.join(str(letters[l]) for l in 'ABCD'):>12}"
        )
        if len(items) != 250:
            errors.append(f"expected 250, found {len(items)}")
        if errors:
            failures += 1
            for error in errors[:8]:
                print(f"   [!] {error}")
        grand_total += len(items)
    print("-" * 70)
    print(f"{'TOTAL':<26} {grand_total:>6}")
    if grand_total == 1000 and failures == 0:
        print("\n[OK] 1,000 unique, complete questions across 4 tracks.")
        return 0
    print(f"\n[FAILED] total={grand_total}, failing subjects={failures}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
