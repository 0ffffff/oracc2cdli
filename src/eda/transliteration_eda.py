"""
EDA for transliteration.csv. Loads full file into memory (smaller dataset).

Process: load (full) -> accumulate stats -> report (basic info, dtypes, missing, id_text/word counts, special notation).
Writes results to src/eda/results/transliteration_eda.md.
"""

from pathlib import Path
import sys

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_PATH = PROJECT_ROOT / "data" / "transliteration.csv"
RESULTS_PATH = PROJECT_ROOT / "src" / "eda" / "results" / "transliteration_eda.md"

# Columns in transliteration.csv: id_text, transliteration (no numeric or categorical value_counts)


def _validate_path() -> None:
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Data file not found: {DATA_PATH}")


def _load_data() -> pd.DataFrame:
    return pd.read_csv(DATA_PATH, dtype={"id_text": str, "transliteration": str})


def _report_basic(df: pd.DataFrame) -> None:
    print("=" * 60)
    print("EDA: transliteration.csv")
    print("=" * 60)
    print("\n" + "=" * 60)
    print("BASIC INFO")
    print("=" * 60)
    print(f"Total rows: {df.shape[0]:,}")
    print(f"Columns: {df.shape[1]}")
    print(f"Column names: {list(df.columns)}")
    
    print("\n" + "=" * 60)
    print("FIRST 5 ROWS")
    print("=" * 60)
    print(df.head(5).to_string())


def _report_dtypes(df: pd.DataFrame) -> None:
    print("\n" + "=" * 60)
    print("DTYPES")
    print("=" * 60)
    print(df.dtypes.to_string())


def _report_missing(df: pd.DataFrame) -> None:
    print("\n" + "=" * 60)
    print("MISSING VALUES")
    print("=" * 60)
    null_counts = df.isna().sum().astype(int)
    print(null_counts.to_string())
    total = len(df)
    pct = (null_counts / total * 100).round(1)
    print("\nAs % of rows:")
    print(pct.to_string())


def _report_id_text(df: pd.DataFrame) -> None:
    """Summarize id_text: uniqueness, format, sample (columns: id_text)."""
    print("\n" + "=" * 60)
    print("ID_TEXT (CDLI text identifiers)")
    print("=" * 60)
    ids = df["id_text"]
    n = len(ids)
    print(f"Unique IDs: {ids.nunique():,} / {n:,}")
    print(f"Duplicate IDs: {ids.duplicated().sum():,}")
    if ids.duplicated().any():
        dup = ids[ids.duplicated(keep=False)].value_counts().head(5)
        print(f"Sample duplicated IDs (count):\n{dup}")
    starts_with_p = ids.astype(str).str.match(r"^P\d+$").sum()
    print(f"IDs matching pattern P<digits>: {starts_with_p:,} ({100 * starts_with_p / n:.1f}%)")
    print(f"Sample IDs:\n{ids.head(10).tolist()}")


def _report_word_counts(df: pd.DataFrame) -> None:
    """Token/word counts per transliteration (column: transliteration)."""
    print("\n" + "=" * 60)
    print("WORD COUNTS (space-separated tokens per transliteration)")
    print("=" * 60)
    words = df["transliteration"].astype(str).str.split()
    word_counts = words.str.len()
    arr = word_counts.to_numpy(dtype=np.float64)
    arr = np.nan_to_num(arr, nan=0)
    arr = arr.astype(np.int64)
    print(f"Mean words per text: {np.mean(arr):.1f}")
    print(f"Std: {np.std(arr):.1f}")
    print(f"Min: {np.min(arr)}, Max: {np.max(arr)}")
    print(f"Percentiles: 25%={np.percentile(arr, 25):.0f}, 50%={np.percentile(arr, 50):.0f}, 75%={np.percentile(arr, 75):.0f}")


def _report_special_patterns(df: pd.DataFrame) -> None:
    """Summarize special notation in transliteration column."""
    print("\n" + "=" * 60)
    print("SPECIAL NOTATION IN TRANSLITERATIONS")
    print("=" * 60)
    trans = df["transliteration"].astype(str)
    n = len(df)
    has_curly = trans.str.contains(r"\{", regex=True).sum()
    has_underscore = trans.str.contains("_", regex=False).sum()
    has_brackets = trans.str.contains(r"\[", regex=True).sum()
    has_digit_paren = trans.str.contains(r"\d+\(", regex=True).sum()
    print(f"Rows with '{{': {has_curly:,} ({100 * has_curly / n:.1f}%)")
    print(f"Rows with '_': {has_underscore:,} ({100 * has_underscore / n:.1f}%)")
    print(f"Rows with '[': {has_brackets:,} ({100 * has_brackets / n:.1f}%)")
    print(f"Rows with digit+paren e.g. 1(disz): {has_digit_paren:,} ({100 * has_digit_paren / n:.1f}%)")


def run_eda() -> None:
    _validate_path()
    df = _load_data()

    # Redirect output to file
    original_stdout = sys.stdout
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_PATH, "w") as f:
        sys.stdout = f

        _report_basic(df)
        _report_dtypes(df)
        _report_missing(df)
        _report_id_text(df)
        _report_word_counts(df)
        _report_special_patterns(df)

        print("\nDone.")

        # Restore stdout
        sys.stdout = original_stdout
    
    print(f"EDA results saved to: {RESULTS_PATH}")


if __name__ == "__main__":
    run_eda()
