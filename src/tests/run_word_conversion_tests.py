"""
Sample runner for word-conversion tests using the reusable API in test_word_conversion.py.

This script demonstrates a typical flow: run unit tests, then chunked dataset tests
against word_level.csv, and print/write a summary. You can use it as-is or copy
and adapt it to build your own test flow (e.g. different CSV, filters, or reporting).

Workflow position: Run after the preprocessing pipeline if you want dataset comparison.
Prerequisites for dataset tests: data/word_level.csv (load_to_db → build_word_table → export_word_level).

Run from project root:
  python3 src/tests/run_word_conversion_tests.py
  python3 src/tests/run_word_conversion_tests.py --csv data/word_level.csv --chunk 50000 --report results/conversion_report.md
"""

from __future__ import annotations

import argparse
import os
import sys

# Ensure project root is on path when run as script
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_SCRIPT_DIR, "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from src.tests.test_word_conversion import (
    DEFAULT_CHUNK_SIZE,
    ROUNDTRIP_SAMPLE_SIZE,
    print_summary,
    run_dataset_tests,
    run_unit_tests,
)

DEFAULT_CSV = os.path.join(_PROJECT_ROOT, "data", "word_level.csv")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run word conversion tests (sample flow using test_word_conversion API)"
    )
    parser.add_argument("--csv", default=DEFAULT_CSV, help="Path to word_level.csv")
    parser.add_argument("--chunk", type=int, default=DEFAULT_CHUNK_SIZE, help="Chunk size for reading CSV")
    parser.add_argument("--report", default=None, help="Write Markdown report to this path")
    parser.add_argument("--no-roundtrip", action="store_true", help="Skip round-trip sample tests")
    parser.add_argument(
        "--roundtrip-sample",
        type=int,
        default=ROUNDTRIP_SAMPLE_SIZE,
        help="Number of rows for round-trip sample",
    )
    parser.add_argument("--max-rows", type=int, default=None, help="Limit CSV rows (for quick runs)")
    args = parser.parse_args()

    print("Running unit tests...")
    unit_results = run_unit_tests()
    total_unit = sum(len(r) for r in unit_results.values())
    passed_unit = sum(1 for results in unit_results.values() for r in results if r["passed"])
    print(f"Unit tests: {passed_unit}/{total_unit} passed")
    print("")

    print("Running dataset tests (chunked)...")
    dataset_stats = run_dataset_tests(
        args.csv,
        chunk_size=args.chunk,
        run_roundtrip_sample=not args.no_roundtrip,
        roundtrip_sample_size=args.roundtrip_sample,
        max_rows=args.max_rows,
    )
    print_summary(unit_results, dataset_stats, report_path=args.report)


if __name__ == "__main__":
    main()
