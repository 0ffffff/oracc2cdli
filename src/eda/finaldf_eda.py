"""
Chunked EDA for finaldf.csv. Does NOT load the full file into memory.

Process: load (chunked) -> accumulate stats -> report (basic info, dtypes, missing, numeric, value counts).
Writes results to src/eda/results/finaldf_eda.md.
"""

from pathlib import Path
from collections import Counter
import sys

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_PATH = PROJECT_ROOT / "data" / "finaldf.csv"
RESULTS_PATH = PROJECT_ROOT / "src" / "eda" / "results" / "finaldf_eda.md"

CHUNKSIZE = 100_000
# Low-cardinality columns to compute value_counts; skip high-cardinality (form, id_word, etc.)
VALUECOUNT_COLUMNS = ["lang", "pos", "delim", "epos"]
# Avoid mixed-type inference on problematic columns
DTYPE_OVERRIDES = {"headform": str, "contrefs": str}


def _validate_path() -> None:
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Data file not found: {DATA_PATH}")


def _accumulate_from_chunk(
    chunk: pd.DataFrame,
    total_rows: int,
    null_counts: pd.Series | None,
    numeric_stats: dict,
    valuecounts: dict[str, Counter],
    columns: list | None,
    dtypes: pd.Series | None,
) -> tuple[int, pd.Series, dict, dict, list | None, pd.Series | None]:
    n = len(chunk)
    new_total = total_rows + n

    if columns is None:
        columns = chunk.columns.tolist()
        dtypes = chunk.dtypes.copy()

    if null_counts is None:
        null_counts = chunk.isna().sum()
    else:
        null_counts = null_counts.add(chunk.isna().sum(), fill_value=0)

    for col in chunk.select_dtypes(include=[np.number]).columns:
        s = chunk[col].dropna()
        if s.size == 0:
            continue
        if col not in numeric_stats:
            numeric_stats[col] = {
                "min": s.min(),
                "max": s.max(),
                "sum": float(s.sum()),
                "sum_sq": float((s.astype("float64") ** 2).sum()),
                "n": int(s.count()),
            }
        else:
            st = numeric_stats[col]
            st["min"] = min(st["min"], s.min())
            st["max"] = max(st["max"], s.max())
            st["sum"] += float(s.sum())
            st["sum_sq"] += float((s.astype("float64") ** 2).sum())
            st["n"] += int(s.count())

    for col in VALUECOUNT_COLUMNS:
        if col not in chunk.columns:
            continue
        vc = chunk[col].fillna("__NA__").value_counts()
        for val, cnt in vc.items():
            valuecounts[col][val] += int(cnt)

    return new_total, null_counts, numeric_stats, valuecounts, columns, dtypes


def _report(
    total_rows: int,
    columns: list,
    dtypes: pd.Series,
    null_counts: pd.Series,
    numeric_stats: dict,
    valuecounts: dict[str, Counter],
    head_df: pd.DataFrame | None,
) -> None:
    print("\n" + "=" * 60)
    print("BASIC INFO")
    print("=" * 60)
    print(f"Total rows: {total_rows:,}")
    print(f"Columns: {len(columns)}")
    print(f"Column names: {columns}")

    if head_df is not None:
        print("\n" + "=" * 60)
        print("FIRST 5 ROWS")
        print("=" * 60)
        print(head_df.to_string())

    print("\n" + "=" * 60)
    print("DTYPES (from first chunk)")
    print("=" * 60)
    print(dtypes.to_string())

    print("\n" + "=" * 60)
    print("MISSING VALUES (total across all chunks)")
    print("=" * 60)
    null_counts = null_counts.astype(int)
    print(null_counts.to_string())
    pct = (null_counts / total_rows * 100).round(1)
    print("\nAs % of rows:")
    print(pct.to_string())

    print("\n" + "=" * 60)
    print("NUMERIC COLUMNS: min, max, mean, std")
    print("=" * 60)
    for col in sorted(numeric_stats.keys()):
        st = numeric_stats[col]
        n = st["n"]
        if n == 0:
            continue
        mean = st["sum"] / n
        variance = (st["sum_sq"] / n) - (mean**2)
        std = np.sqrt(max(0, variance))
        print(f"  {col}: min={st['min']}, max={st['max']}, mean={mean:.4f}, std={std:.4f}, n={n:,}")

    print("\n" + "=" * 60)
    print("VALUE COUNTS (top 15 per column)")
    print("=" * 60)
    for col in VALUECOUNT_COLUMNS:
        if col not in valuecounts or not valuecounts[col]:
            continue
        print(f"\n  {col}:")
        for val, cnt in valuecounts[col].most_common(15):
            pct = 100 * cnt / total_rows
            print(f"    {val}: {cnt:,} ({pct:.1f}%)")


def run_eda() -> None:
    _validate_path()

    total_rows = 0
    null_counts = None
    numeric_stats = {}
    valuecounts = {col: Counter() for col in VALUECOUNT_COLUMNS}
    columns = None
    dtypes = None
    head_df = None

    # Redirect output to file
    original_stdout = sys.stdout
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_PATH, "w") as f:
        sys.stdout = f

        print("=" * 60)
        print("CHUNKED EDA: finaldf.csv")
        print("=" * 60)
        print(f"Chunk size: {CHUNKSIZE:,} rows")
        print("Processing chunks...")

        for i, chunk in enumerate(
            pd.read_csv(
                DATA_PATH,
                chunksize=CHUNKSIZE,
                dtype=DTYPE_OVERRIDES,
                low_memory=True,
            )
        ):
            # Save head from first chunk
            if i == 0:
                head_df = chunk.head(5).copy()
            
            total_rows, null_counts, numeric_stats, valuecounts, columns, dtypes = _accumulate_from_chunk(
                chunk, total_rows, null_counts, numeric_stats, valuecounts, columns, dtypes
            )
            if (i + 1) % 10 == 0 or i == 0:
                print(f"  Chunk {i + 1}: {total_rows:,} rows processed so far...")

        _report(
            total_rows,
            columns if columns is not None else [],
            dtypes if dtypes is not None else pd.Series(),
            null_counts if null_counts is not None else pd.Series(),
            numeric_stats,
            valuecounts,
            head_df,
        )
        print("\nDone.")

        # Restore stdout
        sys.stdout = original_stdout
    
    print(f"EDA results saved to: {RESULTS_PATH}")


if __name__ == "__main__":
    run_eda()
