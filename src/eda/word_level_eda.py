"""
Chunked EDA for word_level data from data/word_level.csv. Does NOT load the full file into memory.

Process: chunked accumulate (head from first chunk) -> report (basic info, head, dtypes, missing, numeric, key stats).
Writes results to src/eda/results/word_level_eda.md.
"""

import sys
from pathlib import Path
from collections import Counter

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CSV_PATH = PROJECT_ROOT / "data" / "word_level.csv"
RESULTS_PATH = PROJECT_ROOT / "src" / "eda" / "results" / "word_level_eda.md"

CHUNKSIZE = 100_000

# Key columns for word_level: internal_id (numeric), id_text, id_word, tr_oracc, tr_cdli
# We compute value_counts for id_text (top N), id_word nulls, and match rate tr_oracc vs tr_cdli


def _validate_csv() -> None:
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"CSV not found: {CSV_PATH}. Run export_word_level.py first.")


def _update_length_stats(
    stats: dict | None,
    lengths: pd.Series,
) -> dict:
    """Update running min/max/sum/sum_sq/n for a length series (avoids storing all lengths)."""
    s = lengths.dropna()
    if s.size == 0:
        return stats or {}
    s = s.astype("float64")
    sum_sq = (s**2).sum()
    if stats is None:
        return {
            "min": s.min(),
            "max": s.max(),
            "sum": float(s.sum()),
            "sum_sq": float(sum_sq),
            "n": int(s.count()),
        }
    stats["min"] = min(stats["min"], s.min())
    stats["max"] = max(stats["max"], s.max())
    stats["sum"] += float(s.sum())
    stats["sum_sq"] += float(sum_sq)
    stats["n"] += int(s.count())
    return stats


def _accumulate_from_chunk(
    chunk: pd.DataFrame,
    total_rows: int,
    null_counts: pd.Series | None,
    numeric_stats: dict,
    id_text_counts: Counter,
    match_count: int,
    tr_oracc_len_stats: dict | None,
    tr_cdli_len_stats: dict | None,
    columns: list | None,
    dtypes: pd.Series | None,
) -> tuple[int, pd.Series, dict, Counter, int, dict, dict, list | None, pd.Series | None]:
    n = len(chunk)
    new_total = total_rows + n

    if columns is None:
        columns = chunk.columns.tolist()
        dtypes = chunk.dtypes.copy()

    if null_counts is None:
        null_counts = chunk.isna().sum()
    else:
        null_counts = null_counts.add(chunk.isna().sum(), fill_value=0)

    # Numeric: internal_id
    if "internal_id" in chunk.columns:
        s = chunk["internal_id"].dropna()
        if s.size > 0:
            if "internal_id" not in numeric_stats:
                numeric_stats["internal_id"] = {
                    "min": s.min(),
                    "max": s.max(),
                    "sum": float(s.sum()),
                    "sum_sq": float((s.astype("float64") ** 2).sum()),
                    "n": int(s.count()),
                }
            else:
                st = numeric_stats["internal_id"]
                st["min"] = min(st["min"], s.min())
                st["max"] = max(st["max"], s.max())
                st["sum"] += float(s.sum())
                st["sum_sq"] += float((s.astype("float64") ** 2).sum())
                st["n"] += int(s.count())

    # id_text: value counts (accumulate for top N later)
    if "id_text" in chunk.columns:
        vc = chunk["id_text"].fillna("__NA__").value_counts()
        for val, cnt in vc.items():
            id_text_counts[val] += int(cnt)

    # Match rate: tr_oracc == tr_cdli (both present and equal)
    if "tr_oracc" in chunk.columns and "tr_cdli" in chunk.columns:
        match_count += (chunk["tr_oracc"].astype(str) == chunk["tr_cdli"].astype(str)).sum()

    # Length stats: running min/max/sum/sum_sq/n (no full list in memory)
    if "tr_oracc" in chunk.columns:
        tr_oracc_len_stats = _update_length_stats(
            tr_oracc_len_stats,
            chunk["tr_oracc"].astype(str).str.len(),
        )
    if "tr_cdli" in chunk.columns:
        tr_cdli_len_stats = _update_length_stats(
            tr_cdli_len_stats,
            chunk["tr_cdli"].astype(str).str.len(),
        )

    return (
        new_total,
        null_counts,
        numeric_stats,
        id_text_counts,
        match_count,
        tr_oracc_len_stats or {},
        tr_cdli_len_stats or {},
        columns,
        dtypes,
    )


def _report(
    total_rows: int,
    columns: list,
    dtypes: pd.Series,
    null_counts: pd.Series,
    numeric_stats: dict,
    id_text_counts: Counter,
    match_count: int,
    tr_oracc_len_stats: dict,
    tr_cdli_len_stats: dict,
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
        print("FIRST 5 ROWS (table layout)")
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

    # Key info: id_text distribution (top 15)
    print("\n" + "=" * 60)
    print("ID_TEXT: top 15 by row count (words per text)")
    print("=" * 60)
    for val, cnt in id_text_counts.most_common(15):
        pct = 100 * cnt / total_rows
        print(f"  {val}: {cnt:,} ({pct:.1f}%)")
    print(f"  Unique id_text values: {len(id_text_counts):,}")

    # id_word: ORACC word-level identifier (one per row when present)
    if "id_word" in columns and null_counts is not None and "id_word" in null_counts.index:
        id_word_null = int(null_counts["id_word"])
        print("\n" + "=" * 60)
        print("ID_WORD (ORACC word-level identifier)")
        print("=" * 60)
        print(f"  Missing id_word: {id_word_null:,} ({100 * id_word_null / total_rows:.1f}%)" if total_rows else "  (no rows)")

    # Match rate: tr_oracc == tr_cdli
    print("\n" + "=" * 60)
    print("ORACC vs CDLI MATCH (tr_oracc == tr_cdli)")
    print("=" * 60)
    match_pct = 100 * match_count / total_rows if total_rows else 0
    print(f"  Rows where tr_oracc == tr_cdli: {match_count:,} ({match_pct:.1f}%)")

    # Length stats (running stats)
    if tr_oracc_len_stats and tr_oracc_len_stats.get("n", 0) > 0:
        st = tr_oracc_len_stats
        mean = st["sum"] / st["n"]
        var = (st["sum_sq"] / st["n"]) - (mean**2)
        std = np.sqrt(max(0, var))
        print("\n" + "=" * 60)
        print("TR_ORACC: character length per word")
        print("=" * 60)
        print(f"  Mean: {mean:.1f}, Std: {std:.1f}, Min: {int(st['min'])}, Max: {int(st['max'])}, n={st['n']:,}")
    if tr_cdli_len_stats and tr_cdli_len_stats.get("n", 0) > 0:
        st = tr_cdli_len_stats
        mean = st["sum"] / st["n"]
        var = (st["sum_sq"] / st["n"]) - (mean**2)
        std = np.sqrt(max(0, var))
        print("\n" + "=" * 60)
        print("TR_CDLI: character length per word")
        print("=" * 60)
        print(f"  Mean: {mean:.1f}, Std: {std:.1f}, Min: {int(st['min'])}, Max: {int(st['max'])}, n={st['n']:,}")


def run_eda() -> None:
    _validate_csv()

    row_count = 0
    null_counts = None
    numeric_stats = {}
    id_text_counts: Counter = Counter()
    match_count = 0
    tr_oracc_len_stats: dict | None = None
    tr_cdli_len_stats: dict | None = None
    columns = None
    dtypes = None
    head_df = None

    original_stdout = sys.stdout
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(RESULTS_PATH, "w") as f:
        sys.stdout = f

        print("=" * 60)
        print("CHUNKED EDA: word_level (CSV)")
        print("=" * 60)
        print(f"CSV: {CSV_PATH}")
        print(f"Chunk size: {CHUNKSIZE:,} rows")
        print("Processing chunks...")

        chunk_iter = pd.read_csv(
            CSV_PATH,
            chunksize=CHUNKSIZE,
            dtype={"id_text": str, "id_word": str, "tr_oracc": str, "tr_cdli": str},
        )
        for i, chunk in enumerate(chunk_iter):
            if head_df is None:
                head_df = chunk.head(5)
            (
                row_count,
                null_counts,
                numeric_stats,
                id_text_counts,
                match_count,
                tr_oracc_len_stats,
                tr_cdli_len_stats,
                columns,
                dtypes,
            ) = _accumulate_from_chunk(
                chunk,
                row_count,
                null_counts,
                numeric_stats,
                id_text_counts,
                match_count,
                tr_oracc_len_stats,
                tr_cdli_len_stats,
                columns,
                dtypes,
            )
            if (i + 1) % 10 == 0 or i == 0:
                print(f"  Chunk {i + 1}: {row_count:,} rows processed so far...")

        total_rows = row_count
        _report(
            total_rows,
            columns if columns is not None else [],
            dtypes if dtypes is not None else pd.Series(),
            null_counts if null_counts is not None else pd.Series(),
            numeric_stats,
            id_text_counts,
            match_count,
            tr_oracc_len_stats or {},
            tr_cdli_len_stats or {},
            head_df,
        )
        print("\nDone.")

        sys.stdout = original_stdout

    print(f"EDA results saved to: {RESULTS_PATH}")


if __name__ == "__main__":
    run_eda()
