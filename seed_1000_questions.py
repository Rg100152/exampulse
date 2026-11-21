#!/usr/bin/env python3
"""Load the four 250-question JSON banks into SQLite.

Usage:
    python seed_1000_questions.py            # idempotent, safe to re-run
    python seed_1000_questions.py --force    # wipe attempts + questions, then reload
    python seed_1000_questions.py --check    # validate JSON only (no DB writes)
"""

from __future__ import annotations

import argparse
import sys

from exampulse_core import DATA_DIR, DB_PATH, SUBJECTS, connect_db, load_bank_file, seed_questions


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed ExamPulse 1000 question banks")
    parser.add_argument("--force", action="store_true", help="delete existing data before seeding")
    parser.add_argument("--check", action="store_true", help="validate JSON files without writing to SQLite")
    args = parser.parse_args()

    print("=" * 62)
    print("  ExamPulse 1000  |  Question Bank Seeder")
    print("=" * 62)
    print(f"  Database: {DB_PATH}")
    print("  Banks   : " + ", ".join(meta["file"] for meta in SUBJECTS.values()))

    if args.check:
        for meta in SUBJECTS.values():
            items = load_bank_file(DATA_DIR / meta["file"])
            print(f"  {meta['short']:<14} {len(items):>4} items")
        return 0

    conn = connect_db()
    try:
        counts = seed_questions(conn=conn, force=args.force)
    except (ValueError, FileNotFoundError) as exc:
        print(f"\n  [FAILED] {exc}", file=sys.stderr)
        return 1
    finally:
        conn.close()

    print("\n  Subject                    Loaded   In database")
    print("  " + "-" * 52)
    for slug, meta in SUBJECTS.items():
        print(f"  {meta['name']:<25} {250:>5}   {counts[slug]:>10}")
    total = sum(counts.values())
    print("  " + "-" * 52)
    print(f"  {'TOTAL':<25} {1000:>5}   {total:>10}")
    if total != 1000:
        print(f"\n  [WARN] Expected 1000 questions, found {total}.")
        return 1
    print("\n  [OK] All 1,000 questions are indexed and ready.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
