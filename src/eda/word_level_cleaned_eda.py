"""
Chunked EDA for word_level_cleaned.csv. Does NOT load the full file into memory.

Process: chunked accumulate (head from first chunk) -> report (basic info, head, dtypes,
missing, numeric, key stats) -> comparison against uncleaned word_level.csv stats.

Writes results to src/eda/results/word_level_cleaned_eda.md.

Prerequisites:
  - data/word_level_cleaned.csv (from clean_word_level.py)
  - Uncleaned stats are sourced from src/eda/results/word_level_eda.md (hardcoded below
    from the last run of word_level_eda.py).
"""

import sys
from pathlib import Path
from collections import Counter

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CSV_PATH = PROJECT_ROOT / "data" / "word_level_cleaned.csv"
RESULTS_PATH = PROJECT_ROOT / "src" / "eda" / "results" / "word_level_cleaned_eda.md"

CHUNKSIZE = 100_000

# ---------------------------------------------------------------------------
# Reference stats from uncleaned word_level.csv (from word_level_eda.md)
# These are used for the comparison section at the end of the report.
# ---------------------------------------------------------------------------

_UNCLEANED = {
    "total_rows": 4_546_052,
    "columns": ["internal_id", "id_text", "id_word", "tr_oracc", "tr_cdli"],
    "missing_tr_cdli": 43,
    "unique_id_text": 93_209,
    "match_count": 871_323,         # rows where tr_oracc == tr_cdli
    "match_pct": 19.2,
    "tr_oracc_len_mean": 6.3,
    "tr_oracc_len_std": 3.8,
    "tr_oracc_len_min": 1,
    "tr_oracc_len_max": 58,
    "tr_cdli_len_mean": 7.0,
    "tr_cdli_len_std": 4.0,
    "tr_cdli_len_min": 1,
    "tr_cdli_len_max": 57,
    "internal_id_min": 1,
    "internal_id_max": 4_546_052,
    "internal_id_mean": 2_273_026.5,
    "internal_id_std": 1_312_332.173,
    # Top 5 id_text by row count (for comparison)
    "top_id_text": [
        ("P393743", 3_517),
        ("P200923", 3_249),
        ("P450362", 3_071),
        ("P422273", 3_002),
        ("P131750", 2_915),
    ],
}


# ---------------------------------------------------------------------------
# Helpers (same streaming accumulators as word_level_eda.py)
# ---------------------------------------------------------------------------


def _validate_csv() -> None:
    if not CSV_PATH.exists():
        raise FileNotFoundError(
            f"CSV not found: {CSV_PATH}. Run clean_word_level.py first."
        )


def _update_length_stats(
    stats: dict | None,
    lengths: pd.Series,
) -> dict:
    """Update running min/max/sum/sum_sq/n for a length series."""
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

    # id_text: value counts
    if "id_text" in chunk.columns:
        vc = chunk["id_text"].fillna("__NA__").value_counts()
        for val, cnt in vc.items():
            id_text_counts[val] += int(cnt)

    # Match rate: tr_oracc == tr_cdli
    if "tr_oracc" in chunk.columns and "tr_cdli" in chunk.columns:
        match_count += int(
            (chunk["tr_oracc"].astype(str) == chunk["tr_cdli"].astype(str)).sum()
        )

    # Length stats
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


def _len_stats_summary(st: dict) -> tuple[float, float, int, int]:
    """Return (mean, std, min, max) from running length stats."""
    n = st.get("n", 0)
    if n == 0:
        return 0.0, 0.0, 0, 0
    mean = st["sum"] / n
    var = (st["sum_sq"] / n) - (mean**2)
    std = float(np.sqrt(max(0, var)))
    return mean, std, int(st["min"]), int(st["max"])


# ---------------------------------------------------------------------------
# Report (cleaned EDA + comparison to uncleaned)
# ---------------------------------------------------------------------------


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
    uc = _UNCLEANED  # shorthand

    # ── Basic info ──────────────────────────────────────────────
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

    # ── Dtypes ──────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("DTYPES (from first chunk)")
    print("=" * 60)
    print(dtypes.to_string())

    # ── Missing values ──────────────────────────────────────────
    print("\n" + "=" * 60)
    print("MISSING VALUES (total across all chunks)")
    print("=" * 60)
    null_counts = null_counts.astype(int)
    print(null_counts.to_string())
    pct = (null_counts / total_rows * 100).round(1)
    print("\nAs % of rows:")
    print(pct.to_string())

    # ── Numeric columns ────────────────────────────────────────
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
        print(
            f"  {col}: min={st['min']}, max={st['max']}, "
            f"mean={mean:.4f}, std={std:.4f}, n={n:,}"
        )

    # ── id_text distribution ────────────────────────────────────
    print("\n" + "=" * 60)
    print("ID_TEXT: top 15 by row count (words per text)")
    print("=" * 60)
    for val, cnt in id_text_counts.most_common(15):
        pct_val = 100 * cnt / total_rows
        print(f"  {val}: {cnt:,} ({pct_val:.1f}%)")
    print(f"  Unique id_text values: {len(id_text_counts):,}")

    # ── id_word ─────────────────────────────────────────────────
    if (
        "id_word" in columns
        and null_counts is not None
        and "id_word" in null_counts.index
    ):
        id_word_null = int(null_counts["id_word"])
        print("\n" + "=" * 60)
        print("ID_WORD (ORACC word-level identifier)")
        print("=" * 60)
        if total_rows:
            print(
                f"  Missing id_word: {id_word_null:,} "
                f"({100 * id_word_null / total_rows:.1f}%)"
            )
        else:
            print("  (no rows)")

    # ── Match rate ──────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("ORACC vs CDLI MATCH (tr_oracc == tr_cdli)")
    print("=" * 60)
    match_pct = 100 * match_count / total_rows if total_rows else 0
    print(
        f"  Rows where tr_oracc == tr_cdli: {match_count:,} ({match_pct:.1f}%)"
    )

    # ── Length stats ────────────────────────────────────────────
    if tr_oracc_len_stats and tr_oracc_len_stats.get("n", 0) > 0:
        mean, std, mn, mx = _len_stats_summary(tr_oracc_len_stats)
        print("\n" + "=" * 60)
        print("TR_ORACC: character length per word")
        print("=" * 60)
        print(
            f"  Mean: {mean:.1f}, Std: {std:.1f}, Min: {mn}, Max: {mx}, "
            f"n={tr_oracc_len_stats['n']:,}"
        )
    if tr_cdli_len_stats and tr_cdli_len_stats.get("n", 0) > 0:
        mean, std, mn, mx = _len_stats_summary(tr_cdli_len_stats)
        print("\n" + "=" * 60)
        print("TR_CDLI: character length per word")
        print("=" * 60)
        print(
            f"  Mean: {mean:.1f}, Std: {std:.1f}, Min: {mn}, Max: {mx}, "
            f"n={tr_cdli_len_stats['n']:,}"
        )

    # ================================================================
    # COMPARISON: cleaned vs uncleaned word_level.csv
    # ================================================================

    print("\n")
    print("=" * 60)
    print("COMPARISON: word_level_cleaned vs word_level (uncleaned)")
    print("=" * 60)
    print(f"(Uncleaned stats from src/eda/results/word_level_eda.md)")

    # ── Row counts ──────────────────────────────────────────────
    rows_dropped = uc["total_rows"] - total_rows
    drop_pct = 100 * rows_dropped / uc["total_rows"] if uc["total_rows"] else 0
    retain_pct = 100 * total_rows / uc["total_rows"] if uc["total_rows"] else 0
    print(f"\n  Uncleaned rows:  {uc['total_rows']:,}")
    print(f"  Cleaned rows:    {total_rows:,}")
    print(f"  Rows removed:    {rows_dropped:,} ({drop_pct:.1f}%)")
    print(f"  Retention rate:  {retain_pct:.1f}%")

    # ── Unique id_text ──────────────────────────────────────────
    cleaned_unique = len(id_text_counts)
    texts_lost = uc["unique_id_text"] - cleaned_unique
    print(f"\n  Unique id_text (uncleaned): {uc['unique_id_text']:,}")
    print(f"  Unique id_text (cleaned):   {cleaned_unique:,}")
    print(f"  Texts lost entirely:        {texts_lost:,}")

    # ── Match rate comparison ───────────────────────────────────
    print(f"\n  Exact match tr_oracc==tr_cdli (uncleaned): {uc['match_count']:,} ({uc['match_pct']:.1f}%)")
    print(f"  Exact match tr_oracc==tr_cdli (cleaned):   {match_count:,} ({match_pct:.1f}%)")
    match_delta = match_pct - uc["match_pct"]
    print(f"  Change in match rate:                      {match_delta:+.1f} pp")

    # ── Length stats comparison ──────────────────────────────────
    if tr_oracc_len_stats and tr_oracc_len_stats.get("n", 0) > 0:
        c_mean, c_std, c_min, c_max = _len_stats_summary(tr_oracc_len_stats)
        print(f"\n  TR_ORACC length (uncleaned): mean={uc['tr_oracc_len_mean']:.1f}, std={uc['tr_oracc_len_std']:.1f}, min={uc['tr_oracc_len_min']}, max={uc['tr_oracc_len_max']}")
        print(f"  TR_ORACC length (cleaned):   mean={c_mean:.1f}, std={c_std:.1f}, min={c_min}, max={c_max}")
        print(f"  Mean delta:                  {c_mean - uc['tr_oracc_len_mean']:+.1f}")

    if tr_cdli_len_stats and tr_cdli_len_stats.get("n", 0) > 0:
        c_mean, c_std, c_min, c_max = _len_stats_summary(tr_cdli_len_stats)
        print(f"\n  TR_CDLI length (uncleaned):  mean={uc['tr_cdli_len_mean']:.1f}, std={uc['tr_cdli_len_std']:.1f}, min={uc['tr_cdli_len_min']}, max={uc['tr_cdli_len_max']}")
        print(f"  TR_CDLI length (cleaned):    mean={c_mean:.1f}, std={c_std:.1f}, min={c_min}, max={c_max}")
        print(f"  Mean delta:                  {c_mean - uc['tr_cdli_len_mean']:+.1f}")

    # ── Top id_text comparison ──────────────────────────────────
    print(f"\n  Top 5 id_text by word count (uncleaned -> cleaned):")
    for txt, uc_cnt in uc["top_id_text"]:
        c_cnt = id_text_counts.get(txt, 0)
        delta = c_cnt - uc_cnt
        print(f"    {txt}: {uc_cnt:,} -> {c_cnt:,} ({delta:+,})")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def run_eda() -> None:
    _validate_csv()

    row_count = 0
    null_counts = None
    numeric_stats: dict = {}
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
        print("CHUNKED EDA: word_level_cleaned (CSV)")
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
