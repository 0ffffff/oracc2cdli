"""
Reusable test functions for CDLI ↔ ORACC word-level conversion.

Use this module to build custom test flows: call the functions below with your data,
then aggregate results and report as needed. run_word_conversion_tests.py is a sample
runner that uses these functions.

Prerequisites for dataset tests:
  - word_level.csv with columns tr_cdli, tr_oracc (e.g. from load_to_db → build_word_table → export_word_level).
Unit tests (empty, None, malformed, edge cases, round-trip) require no CSV.

Result format: each test returns a dict with "passed", "message", and optional "details".

--------------------------------------------------------------------------------
Table of contents (public API)
--------------------------------------------------------------------------------

Dataset comparison (single row)
  - test_cdli_to_oracc_vs_dataset(cdli, expected_oracc, ...)  — convert CDLI→ORACC, compare to gold
  - test_oracc_to_cdli_vs_dataset(oracc, expected_cdli, ...)  — convert ORACC→CDLI, compare to gold

Round-trip (single value)
  - test_roundtrip_cdli_to_oracc_to_cdli(cdli, ...)   — CDLI → ORACC → CDLI, compare to original
  - test_roundtrip_oracc_to_cdli_to_oracc(oracc, ...) — ORACC → CDLI → ORACC, compare to original

Empty / None / malformed
  - test_empty_string_cdli_to_oracc()           — "" → ORACC
  - test_empty_string_oracc_to_cdli()           — "" → CDLI
  - test_none_cdli_to_oracc()                   — None → ORACC
  - test_none_oracc_to_cdli()                   — None → CDLI
  - test_malformed_cdli_to_oracc(value, ...)    — non-string CDLI → ORACC
  - test_malformed_oracc_to_cdli(value, ...)    — non-string ORACC → CDLI

Edge cases (fixed pairs)
  - test_edge_case_pairs()                      — list of (description, cdli, oracc) pairs
  - test_edge_cases_cdli_to_oracc()             — run CDLI→ORACC on those pairs; returns list of result dicts
  - test_edge_cases_oracc_to_cdli()             — run ORACC→CDLI on those pairs; returns list of result dicts

Batch: unit tests only
  - run_unit_tests()                            — empty, None, malformed, edge cases; returns dict[group_name, list[result]]

Batch: dataset from CSV (chunked)
  - run_dataset_tests(csv_path, chunk_size=..., run_roundtrip_sample=..., ...) — run comparison + optional round-trip sample; returns stats dict

Reporting
  - print_summary(unit_results, dataset_stats, report_path=None) — print and optionally write Markdown report

Constants (for use in your flow)
  - DEFAULT_CHUNK_SIZE, ROUNDTRIP_SAMPLE_SIZE, MAX_FAILURES_TO_REPORT
"""

from __future__ import annotations

import os
from typing import Any, Optional

import pandas as pd

def _converters():
    """Lazy import of conversion functions so tests work when run from project root or as module."""
    from src.utils.word_conversion import word_cdli_to_oracc, word_oracc_to_cdli
    return word_cdli_to_oracc, word_oracc_to_cdli


# -----------------------------------------------------------------------------
# Result type: consistent dict for every test
# -----------------------------------------------------------------------------

def _result(passed: bool, message: str, **details: Any) -> dict[str, Any]:
    """Build a standard test result dict."""
    out: dict[str, Any] = {"passed": passed, "message": message}
    if details:
        out["details"] = details
    return out


# -----------------------------------------------------------------------------
# Constants for batch dataset runs (tune in your own flow if needed)
# -----------------------------------------------------------------------------

DEFAULT_CHUNK_SIZE = 100_000
MAX_FAILURES_TO_REPORT = 50
ROUNDTRIP_SAMPLE_SIZE = 5000


# -----------------------------------------------------------------------------
# Dataset comparison tests (compare conversion output to dataset gold)
# -----------------------------------------------------------------------------

def test_cdli_to_oracc_vs_dataset(
    cdli: str,
    expected_oracc: str,
    *,
    row_id: Optional[int] = None,
    normalize_determinatives: bool = False,
    strip_underscores: bool = False,
) -> dict[str, Any]:
    """
    Convert CDLI -> ORACC and compare to the expected ORACC value from the dataset.

    Returns a result dict with passed, message, and details (input, expected, actual).
    Skips comparison if expected_oracc is missing/empty (e.g. NaN); returns passed=False
    with message indicating skip reason if both are missing.
    """
    word_cdli_to_oracc, _ = _converters()
    if cdli is None or (isinstance(cdli, str) and not str(cdli).strip()):
        return _result(
            False,
            "cdli input is empty or None",
            input=cdli,
            expected_oracc=expected_oracc,
            row_id=row_id,
        )
    expected = None if expected_oracc is None else str(expected_oracc).strip()
    if expected is None or expected == "":
        return _result(
            False,
            "expected_oracc is missing (NaN or empty); cannot compare",
            input=cdli,
            expected_oracc=expected_oracc,
            row_id=row_id,
        )
    try:
        actual = word_cdli_to_oracc(
            str(cdli).strip(),
            normalize_determinatives=normalize_determinatives,
            strip_underscores=strip_underscores,
        )
    except Exception as e:
        return _result(
            False,
            f"cdli_to_oracc raised: {e!r}",
            input=cdli,
            expected_oracc=expected,
            row_id=row_id,
            error=str(e),
        )
    passed = actual == expected
    return _result(
        passed,
        "match" if passed else "mismatch",
        input=cdli,
        expected=expected,
        actual=actual,
        row_id=row_id,
    )


def test_oracc_to_cdli_vs_dataset(
    oracc: str,
    expected_cdli: str,
    *,
    row_id: Optional[int] = None,
) -> dict[str, Any]:
    """
    Convert ORACC -> CDLI and compare to the expected CDLI value from the dataset.

    Returns a result dict with passed, message, and details.
    """
    _, word_oracc_to_cdli = _converters()
    if oracc is None or (isinstance(oracc, str) and not str(oracc).strip()):
        return _result(
            False,
            "oracc input is empty or None",
            input=oracc,
            expected_cdli=expected_cdli,
            row_id=row_id,
        )
    expected = None if expected_cdli is None else str(expected_cdli).strip()
    if expected is None or expected == "":
        return _result(
            False,
            "expected_cdli is missing (NaN or empty); cannot compare",
            input=oracc,
            expected_cdli=expected_cdli,
            row_id=row_id,
        )
    try:
        actual = word_oracc_to_cdli(str(oracc).strip())
    except Exception as e:
        return _result(
            False,
            f"oracc_to_cdli raised: {e!r}",
            input=oracc,
            expected_cdli=expected,
            row_id=row_id,
            error=str(e),
        )
    passed = actual == expected
    return _result(
        passed,
        "match" if passed else "mismatch",
        input=oracc,
        expected=expected,
        actual=actual,
        row_id=row_id,
    )


# -----------------------------------------------------------------------------
# Round-trip tests (convert A -> B -> A and compare to original A)
# -----------------------------------------------------------------------------

def test_roundtrip_cdli_to_oracc_to_cdli(cdli: str, *, row_id: Optional[int] = None) -> dict[str, Any]:
    """
    Convert CDLI -> ORACC -> CDLI and compare the final CDLI to the original.

    Does not use normalize_determinatives or strip_underscores so that round-trip
    is character-stable where the dataset uses {d}/{ki} and no underscores.
    """
    word_cdli_to_oracc, word_oracc_to_cdli = _converters()
    if cdli is None:
        cdli = ""
    s = str(cdli).strip()
    if not s:
        return _result(True, "empty input; round-trip identity", input=s, row_id=row_id)
    try:
        oracc = word_cdli_to_oracc(s, normalize_determinatives=False, strip_underscores=False)
        back = word_oracc_to_cdli(oracc)
    except Exception as e:
        return _result(
            False,
            f"round-trip raised: {e!r}",
            input=s,
            row_id=row_id,
            error=str(e),
        )
    passed = back == s
    return _result(
        passed,
        "match" if passed else "mismatch",
        input=s,
        after_oracc=oracc,
        roundtrip_cdli=back,
        row_id=row_id,
    )


def test_roundtrip_oracc_to_cdli_to_oracc(oracc: str, *, row_id: Optional[int] = None) -> dict[str, Any]:
    """
    Convert ORACC -> CDLI -> ORACC and compare the final ORACC to the original.
    """
    word_cdli_to_oracc, word_oracc_to_cdli = _converters()
    if oracc is None:
        oracc = ""
    s = str(oracc).strip()
    if not s:
        return _result(True, "empty input; round-trip identity", input=s, row_id=row_id)
    try:
        cdli = word_oracc_to_cdli(s)
        back = word_cdli_to_oracc(cdli, normalize_determinatives=False, strip_underscores=False)
    except Exception as e:
        return _result(
            False,
            f"round-trip raised: {e!r}",
            input=s,
            row_id=row_id,
            error=str(e),
        )
    passed = back == s
    return _result(
        passed,
        "match" if passed else "mismatch",
        input=s,
        after_cdli=cdli,
        roundtrip_oracc=back,
        row_id=row_id,
    )


# -----------------------------------------------------------------------------
# Empty and malformed input tests
# -----------------------------------------------------------------------------

def test_empty_string_cdli_to_oracc() -> dict[str, Any]:
    """CDLI -> ORACC on empty string should return empty string (no exception)."""
    word_cdli_to_oracc, _ = _converters()
    try:
        out = word_cdli_to_oracc("")
        passed = out == ""
        return _result(passed, "match" if passed else "mismatch", input="", actual=out)
    except Exception as e:
        return _result(False, f"raised: {e!r}", input="", error=str(e))


def test_empty_string_oracc_to_cdli() -> dict[str, Any]:
    """ORACC -> CDLI on empty string should return empty string (no exception)."""
    _, word_oracc_to_cdli = _converters()
    try:
        out = word_oracc_to_cdli("")
        passed = out == ""
        return _result(passed, "match" if passed else "mismatch", input="", actual=out)
    except Exception as e:
        return _result(False, f"raised: {e!r}", input="", error=str(e))


def test_none_cdli_to_oracc() -> dict[str, Any]:
    """CDLI -> ORACC on None should return '' (no exception)."""
    word_cdli_to_oracc, _ = _converters()
    try:
        out = word_cdli_to_oracc(None)  # type: ignore[arg-type]
        passed = out == ""
        return _result(passed, "match" if passed else "mismatch", input=None, actual=out)
    except Exception as e:
        return _result(False, f"raised: {e!r}", input=None, error=str(e))


def test_none_oracc_to_cdli() -> dict[str, Any]:
    """ORACC -> CDLI on None should return '' (no exception)."""
    _, word_oracc_to_cdli = _converters()
    try:
        out = word_oracc_to_cdli(None)  # type: ignore[arg-type]
        passed = out == ""
        return _result(passed, "match" if passed else "mismatch", input=None, actual=out)
    except Exception as e:
        return _result(False, f"raised: {e!r}", input=None, error=str(e))


def test_malformed_cdli_to_oracc(value: Any, *, expect_no_raise: bool = True) -> dict[str, Any]:
    """
    Convert non-string or unusual CDLI-like value to ORACC.
    If expect_no_raise, passing means no exception and output is a string.
    """
    word_cdli_to_oracc, _ = _converters()
    try:
        out = word_cdli_to_oracc(value)  # type: ignore[arg-type]
        if expect_no_raise:
            passed = isinstance(out, str)
            return _result(passed, "no raise, string out" if passed else "non-string out", input=value, actual=out)
        return _result(True, "no raise", input=value, actual=out)
    except Exception as e:
        if expect_no_raise:
            return _result(False, f"raised: {e!r}", input=value, error=str(e))
        return _result(True, "raised as expected", input=value, error=str(e))


def test_malformed_oracc_to_cdli(value: Any, *, expect_no_raise: bool = True) -> dict[str, Any]:
    """Convert non-string or unusual ORACC-like value to CDLI."""
    _, word_oracc_to_cdli = _converters()
    try:
        out = word_oracc_to_cdli(value)  # type: ignore[arg-type]
        if expect_no_raise:
            passed = isinstance(out, str)
            return _result(passed, "no raise, string out" if passed else "non-string out", input=value, actual=out)
        return _result(True, "no raise", input=value, actual=out)
    except Exception as e:
        if expect_no_raise:
            return _result(False, f"raised: {e!r}", input=value, error=str(e))
        return _result(True, "raised as expected", input=value, error=str(e))


# -----------------------------------------------------------------------------
# Edge-case tests (unusual characters, fractions, determinatives, etc.)
# -----------------------------------------------------------------------------

def test_edge_case_pairs() -> list[tuple[str, str, str]]:
    """
    Return a list of (description, cdli, oracc) for known good pairs.
    Used to run cdli->oracc and oracc->cdli and optionally round-trips.
    """
    return [
        ("numeric 1(asz)", "1(asz)", "1(aš)"),
        ("numeric 1(disz)", "1(disz)", "1(diš)"),
        ("fraction 1/2(disz)", "1/2(disz)", "1/2(diš)"),
        ("sign index i3", "i3-kal-la", "i₃-kal-la"),
        ("sign index du10", "nam-lugal-ni-du10", "nam-lugal-ni-du₁₀"),
        ("comma sign ṣ", "s,i2-s,u2-na-aw-ra-at", "ṣi₂-ṣu₂-na-aw-ra-at"),
        ("determinative {d}", "{d}i-bi2-{d}suen", "{d}i-bi₂-{d}suen"),
        ("ellipsis", "...", "…"),
        ("sz/szu", "szu", "šu"),
        ("identical", "gur", "gur"),
    ]


def test_edge_cases_cdli_to_oracc() -> list[dict[str, Any]]:
    """Run CDLI -> ORACC on fixed edge-case pairs; return list of result dicts."""
    word_cdli_to_oracc, _ = _converters()
    results = []
    for desc, cdli, expected_oracc in test_edge_case_pairs():
        try:
            actual = word_cdli_to_oracc(cdli)
            passed = actual == expected_oracc
            results.append(_result(
                passed,
                "match" if passed else "mismatch",
                description=desc,
                input=cdli,
                expected=expected_oracc,
                actual=actual,
            ))
        except Exception as e:
            results.append(_result(
                False,
                f"raised: {e!r}",
                description=desc,
                input=cdli,
                expected=expected_oracc,
                error=str(e),
            ))
    return results


def test_edge_cases_oracc_to_cdli() -> list[dict[str, Any]]:
    """Run ORACC -> CDLI on fixed edge-case pairs; return list of result dicts."""
    _, word_oracc_to_cdli = _converters()
    results = []
    for desc, expected_cdli, oracc in test_edge_case_pairs():
        try:
            actual = word_oracc_to_cdli(oracc)
            passed = actual == expected_cdli
            results.append(_result(
                passed,
                "match" if passed else "mismatch",
                description=desc,
                input=oracc,
                expected=expected_cdli,
                actual=actual,
            ))
        except Exception as e:
            results.append(_result(
                False,
                f"raised: {e!r}",
                description=desc,
                input=oracc,
                expected=expected_cdli,
                error=str(e),
            ))
    return results


# -----------------------------------------------------------------------------
# Run all unit-style tests (empty, None, malformed, edge cases)
# -----------------------------------------------------------------------------

def run_unit_tests() -> dict[str, list[dict[str, Any]]]:
    """
    Run all non-dataset tests: empty, None, malformed, edge cases.
    Returns a dict of test_group -> list of result dicts.
    """
    groups: dict[str, list[dict[str, Any]]] = {}

    groups["empty"] = [
        test_empty_string_cdli_to_oracc(),
        test_empty_string_oracc_to_cdli(),
    ]
    groups["none"] = [
        test_none_cdli_to_oracc(),
        test_none_oracc_to_cdli(),
    ]
    groups["malformed"] = [
        test_malformed_cdli_to_oracc(123),
        test_malformed_cdli_to_oracc("   "),
        test_malformed_oracc_to_cdli(123),
        test_malformed_oracc_to_cdli("   "),
    ]
    groups["edge_cdli_to_oracc"] = test_edge_cases_cdli_to_oracc()
    groups["edge_oracc_to_cdli"] = test_edge_cases_oracc_to_cdli()

    return groups


# -----------------------------------------------------------------------------
# Batch: run dataset tests from CSV (chunked)
# -----------------------------------------------------------------------------

def run_dataset_tests(
    csv_path: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    run_roundtrip_sample: bool = True,
    roundtrip_sample_size: int = ROUNDTRIP_SAMPLE_SIZE,
    max_rows: Optional[int] = None,
    max_failures: int = MAX_FAILURES_TO_REPORT,
) -> dict[str, Any]:
    """
    Read word_level-style CSV in chunks; for each row with valid tr_cdli and tr_oracc,
    run test_cdli_to_oracc_vs_dataset and test_oracc_to_cdli_vs_dataset.
    Optionally run round-trip tests on a sample of rows.

    Returns a dict with:
      total_rows, rows_with_both,
      cdli_to_oracc: {passed, failed, skipped, failures},
      oracc_to_cdli: same,
      roundtrip_cdli, roundtrip_oracc (if run).
    Or {"error": "..."} if the CSV is not found.
    """
    if not os.path.isfile(csv_path):
        return {"error": f"CSV not found: {csv_path}"}

    stats: dict[str, Any] = {
        "total_rows": 0,
        "rows_with_both": 0,
        "cdli_to_oracc": {"passed": 0, "failed": 0, "skipped": 0, "failures": []},
        "oracc_to_cdli": {"passed": 0, "failed": 0, "skipped": 0, "failures": []},
        "roundtrip_cdli": {"passed": 0, "failed": 0, "failures": []},
        "roundtrip_oracc": {"passed": 0, "failed": 0, "failures": []},
    }
    roundtrip_sample_rows: list[dict[str, Any]] = []

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

            if run_roundtrip_sample and len(roundtrip_sample_rows) < roundtrip_sample_size:
                roundtrip_sample_rows.append({
                    "internal_id": internal_id,
                    "tr_cdli": tr_cdli_s,
                    "tr_oracc": tr_oracc_s,
                })

            res_c2o = test_cdli_to_oracc_vs_dataset(tr_cdli_s, tr_oracc_s, row_id=internal_id)
            if res_c2o.get("details", {}).get("expected") is None:
                stats["cdli_to_oracc"]["skipped"] += 1
            elif res_c2o["passed"]:
                stats["cdli_to_oracc"]["passed"] += 1
            else:
                stats["cdli_to_oracc"]["failed"] += 1
                if len(stats["cdli_to_oracc"]["failures"]) < max_failures:
                    stats["cdli_to_oracc"]["failures"].append(res_c2o)

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

def print_summary(
    unit_results: dict[str, list[dict[str, Any]]],
    dataset_stats: dict[str, Any],
    report_path: Optional[str] = None,
) -> None:
    """
    Print a text summary of unit and dataset test results to stdout.
    If report_path is set, also write a Markdown report to that file.
    """
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
