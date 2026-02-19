"""
Reusable test functions for CDLI ↔ ORACC word-level conversion.

Workflow position: Test library. No run order; used by run_word_conversion_tests.py.
Dataset comparison tests expect rows with tr_cdli / tr_oracc (e.g. from word_level.csv).

Prerequisites for dataset tests:
  - data/word_level.csv (produced by: load_to_db.py → build_word_table.py → export_word_level.py).
Unit tests (empty, None, malformed, round-trip) do not require any pipeline or CSV.

Each test function returns a result dict: { "passed", "message", "details" (optional) }.
When comparing to word_level.csv, a failure can mean (1) conversion differs from gold, or
(2) the row has misaligned tr_cdli/tr_oracc.
"""

from __future__ import annotations

from typing import Any, Optional

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
