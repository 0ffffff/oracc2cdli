"""
Run word-conversion tests against the word_level.csv dataset in chunks.

Workflow position: Run after the preprocessing pipeline if you want dataset comparison tests.
Uses the reusable test functions from test_word_conversion.py.

Prerequisites:
  - Unit tests: none (no CSV or DB required).
  - Dataset comparison tests: data/word_level.csv must exist. Produce it with:
    load_to_db.py → build_word_table.py → export_word_level.py (in src/preprocessing).

Outputs: Console summary; optional --report path (e.g. src/tests/results/conversion_report.md).

Run from project root:
  python3 src/tests/run_word_conversion_tests.py
  python3 src/tests/run_word_conversion_tests.py --csv data/word_level.csv --chunk 50000 --report results/conversion_report.md
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Optional

# Ensure project root is on path when run as script
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_SCRIPT_DIR, "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import pandas as pd

from src.tests.test_word_conversion import (
    test_cdli_to_oracc_vs_dataset,
    test_oracc_to_cdli_vs_dataset,
    test_roundtrip_cdli_to_oracc_to_cdli,
    test_roundtrip_oracc_to_cdli_to_oracc,
    run_unit_tests,
)


# -----------------------------------------------------------------------------
# Default paths and options
# -----------------------------------------------------------------------------

DEFAULT_CSV = os.path.join(_PROJECT_ROOT, "data", "word_level.csv")
DEFAULT_CHUNK_SIZE = 100_000
MAX_FAILURES_TO_REPORT = 50
ROUNDTRIP_SAMPLE_SIZE = 5000  # number of rows to run round-trip on (per direction)


# -----------------------------------------------------------------------------
# Chunked dataset tests
# -----------------------------------------------------------------------------

def run_dataset_tests(
    csv_path: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    run_roundtrip_sample: bool = True,
    roundtrip_sample_size: int = ROUNDTRIP_SAMPLE_SIZE,
    max_rows: Optional[int] = None,
) -> dict:
    """
    Read word_level.csv in chunks; for each row with valid tr_cdli and tr_oracc,
    run test_cdli_to_oracc_vs_dataset and test_oracc_to_cdli_vs_dataset.
    Optionally run round-trip tests on a sample of rows.

    Returns a dict with:
      total_rows, rows_with_both, cdli_to_oracc (passed, failed, skipped, failures list),
      oracc_to_cdli (same), roundtrip_cdli (if run), roundtrip_oracc (if run).
    """
    if not os.path.isfile(csv_path):
        return {"error": f"CSV not found: {csv_path}"}

    stats = {
        "total_rows": 0,
        "rows_with_both": 0,
        "cdli_to_oracc": {"passed": 0, "failed": 0, "skipped": 0, "failures": []},
        "oracc_to_cdli": {"passed": 0, "failed": 0, "skipped": 0, "failures": []},
        "roundtrip_cdli": {"passed": 0, "failed": 0, "failures": []},
        "roundtrip_oracc": {"passed": 0, "failed": 0, "failures": []},
    }
    max_failures = MAX_FAILURES_TO_REPORT
    roundtrip_sample_rows: list[dict] = []  # collect rows for round-trip sample

    chunk_iter = pd.read_csv(
        csv_path,
        chunksize=chunk_size,
        dtype={"internal_id": "Int64", "id_text": str, "tr_oracc": str, "tr_cdli": str},
    )
    row_offset = 0
    for chunk in chunk_iter:
        if max_rows is not None and row_offset >= max_rows:
            break
        if max_rows is not None and row_offset + len(chunk) > max_rows:
            chunk = chunk.head(max_rows - row_offset)
        stats["total_rows"] += len(chunk)
        for idx, row in chunk.iterrows():
            internal_id = row.get("internal_id", row_offset + idx)
            tr_oracc = row.get("tr_oracc")
            tr_cdli = row.get("tr_cdli")
            # Skip if either is missing
            if pd.isna(tr_cdli) or pd.isna(tr_oracc):
                stats["cdli_to_oracc"]["skipped"] += 1
                stats["oracc_to_cdli"]["skipped"] += 1
                continue
            tr_cdli_s = str(tr_cdli).strip()
            tr_oracc_s = str(tr_oracc).strip()
            if not tr_cdli_s or not tr_oracc_s:
                stats["cdli_to_oracc"]["skipped"] += 1
                stats["oracc_to_cdli"]["skipped"] += 1
                continue
            stats["rows_with_both"] += 1

            # Collect rows for round-trip sample (first N with both values)
            if run_roundtrip_sample and len(roundtrip_sample_rows) < roundtrip_sample_size:
                roundtrip_sample_rows.append({
                    "internal_id": internal_id,
                    "tr_cdli": tr_cdli_s,
                    "tr_oracc": tr_oracc_s,
                })

            # CDLI -> ORACC vs dataset
            res_c2o = test_cdli_to_oracc_vs_dataset(tr_cdli_s, tr_oracc_s, row_id=internal_id)
            if res_c2o.get("details", {}).get("expected") is None:
                stats["cdli_to_oracc"]["skipped"] += 1
            elif res_c2o["passed"]:
                stats["cdli_to_oracc"]["passed"] += 1
            else:
                stats["cdli_to_oracc"]["failed"] += 1
                if len(stats["cdli_to_oracc"]["failures"]) < max_failures:
                    stats["cdli_to_oracc"]["failures"].append(res_c2o)

            # ORACC -> CDLI vs dataset
            res_o2c = test_oracc_to_cdli_vs_dataset(tr_oracc_s, tr_cdli_s, row_id=internal_id)
            if res_o2c.get("details", {}).get("expected") is None:
                stats["oracc_to_cdli"]["skipped"] += 1
            elif res_o2c["passed"]:
                stats["oracc_to_cdli"]["passed"] += 1
            else:
                stats["oracc_to_cdli"]["failed"] += 1
                if len(stats["oracc_to_cdli"]["failures"]) < max_failures:
                    stats["oracc_to_cdli"]["failures"].append(res_o2c)

        row_offset += len(chunk)

    # Round-trip on the collected sample
    if run_roundtrip_sample and roundtrip_sample_rows:
        for r in roundtrip_sample_rows:
            r_c = test_roundtrip_cdli_to_oracc_to_cdli(r["tr_cdli"], row_id=r["internal_id"])
            if r_c["passed"]:
                stats["roundtrip_cdli"]["passed"] += 1
            else:
                stats["roundtrip_cdli"]["failed"] += 1
                if len(stats["roundtrip_cdli"]["failures"]) < max_failures:
                    stats["roundtrip_cdli"]["failures"].append(r_c)
            r_o = test_roundtrip_oracc_to_cdli_to_oracc(r["tr_oracc"], row_id=r["internal_id"])
            if r_o["passed"]:
                stats["roundtrip_oracc"]["passed"] += 1
            else:
                stats["roundtrip_oracc"]["failed"] += 1
                if len(stats["roundtrip_oracc"]["failures"]) < max_failures:
                    stats["roundtrip_oracc"]["failures"].append(r_o)

    return stats


# -----------------------------------------------------------------------------
# Reporting
# -----------------------------------------------------------------------------

def print_summary(unit_results: dict, dataset_stats: dict, report_path: Optional[str] = None) -> None:
    """Print summary to stdout and optionally write a Markdown report file."""
    lines = []
    lines.append("# Word conversion test report")
    lines.append("")
    lines.append("## Unit tests (empty, None, malformed, edge cases)")
    lines.append("")
    for group_name, results in unit_results.items():
        passed = sum(1 for r in results if r["passed"])
        total = len(results)
        lines.append(f"- **{group_name}**: {passed}/{total} passed")
        for r in results:
            if not r["passed"]:
                lines.append(f"  - FAIL: {r['message']} {r.get('details', {})}")
    lines.append("")
    lines.append("## Dataset tests (word_level.csv)")
    lines.append("")
    if "error" in dataset_stats:
        lines.append(f"Error: {dataset_stats['error']}")
    else:
        lines.append(f"- Total rows: {dataset_stats['total_rows']:,}")
        lines.append(f"- Rows with both tr_cdli and tr_oracc: {dataset_stats['rows_with_both']:,}")
        lines.append("")
        c2o = dataset_stats["cdli_to_oracc"]
        o2c = dataset_stats["oracc_to_cdli"]
        for label, d in [("CDLI → ORACC (vs dataset)", c2o), ("ORACC → CDLI (vs dataset)", o2c)]:
            p, f, s = d["passed"], d["failed"], d["skipped"]
            total = p + f
            pct = (100 * p / total) if total else 0
            lines.append(f"### {label}")
            lines.append(f"- Passed: {p:,}, Failed: {f:,}, Skipped: {s:,}")
            lines.append(f"- Accuracy (of compared): {pct:.2f}%")
            if d.get("failures"):
                lines.append("")
                lines.append("Sample failures (first {}):".format(len(d["failures"])))
                for i, res in enumerate(d["failures"][:20], 1):
                    det = res.get("details", {})
                    lines.append(f"{i}. row_id={det.get('row_id')} input={det.get('input')!r} expected={det.get('expected')!r} actual={det.get('actual')!r}")
            lines.append("")
        rt_c = dataset_stats.get("roundtrip_cdli", {})
        rt_o = dataset_stats.get("roundtrip_oracc", {})
        if rt_c and (rt_c["passed"] + rt_c["failed"]) > 0:
            lines.append("### Round-trip CDLI → ORACC → CDLI (sample)")
            lines.append(f"- Passed: {rt_c['passed']:,}, Failed: {rt_c['failed']:,}")
            lines.append("")
        if rt_o and (rt_o["passed"] + rt_o["failed"]) > 0:
            lines.append("### Round-trip ORACC → CDLI → ORACC (sample)")
            lines.append(f"- Passed: {rt_o['passed']:,}, Failed: {rt_o['failed']:,}")
    lines.append("")
    text = "\n".join(lines)
    print(text)
    if report_path:
        report_dir = os.path.dirname(report_path)
        if report_dir:
            os.makedirs(report_dir, exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Report written to {report_path}")


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Run word conversion tests on word_level.csv (chunked)")
    parser.add_argument("--csv", default=DEFAULT_CSV, help="Path to word_level.csv")
    parser.add_argument("--chunk", type=int, default=DEFAULT_CHUNK_SIZE, help="Chunk size for reading CSV")
    parser.add_argument("--report", default=None, help="Write Markdown report to this path")
    parser.add_argument("--no-roundtrip", action="store_true", help="Skip round-trip sample tests")
    parser.add_argument("--roundtrip-sample", type=int, default=ROUNDTRIP_SAMPLE_SIZE, help="Number of rows for round-trip sample")
    parser.add_argument("--max-rows", type=int, default=None, help="Limit number of CSV rows to process (for quick runs)")
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
