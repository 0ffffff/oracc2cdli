"""
TEMPORARY: Clean only the first N rows of word_level.csv for timing the cleaning process.

Same logic as clean_word_level.py but stops after processing MAX_ROWS.
Uses constants and classification logic from clean_word_level.py so you can change
thresholds/filters in one place when manually modifying tests.

Output: data/word_level_cleaned_subset.csv. Delete this file when done benchmarking.
"""

from __future__ import annotations

import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

# Project root
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import pandas as pd

from src.preprocessing.clean_word_level import (
    CHUNK_SIZE,
    INPUT_CSV,
    MAX_WORKERS,
    _merge_results,
    _process_chunk,
    _split_pairs,
)


# -----------------------------------------------------------------------------
# Subset-only config (paths and row limit)
# -----------------------------------------------------------------------------

OUTPUT_CSV = _PROJECT_ROOT / "data" / "word_level_cleaned_subset.csv"
MAX_ROWS = 10_000  # Only process this many rows (for timing)


def clean_word_level_subset(
    input_csv: Path | str | None = None,
    output_csv: Path | str | None = None,
    chunk_size: int = CHUNK_SIZE,
    max_rows: int = MAX_ROWS,
    max_workers: int | None = MAX_WORKERS,
) -> dict:
    """
    Load word_level.csv, process only the first max_rows rows, filter, and save.

    Returns dict with stats: {total_rows, kept_rows, dropped_rows, dropped_by_reason, elapsed_sec}
    """
    input_csv = Path(input_csv) if input_csv else INPUT_CSV
    output_csv = Path(output_csv) if output_csv else OUTPUT_CSV

    if not input_csv.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_csv}")

    output_csv.parent.mkdir(parents=True, exist_ok=True)

    t0 = time.perf_counter()

    total_rows = 0
    kept_rows = 0
    dropped_rows = 0
    dropped_by_reason: dict[str, int] = {"empty_column": 0, "garbage_token": 0, "misaligned": 0}
    kept_by_label: dict[str, int] = {"exact": 0, "high": 0, "conversion_issue": 0}

    n_workers = max_workers if max_workers is not None else max(1, (os.cpu_count() or 2) - 1)
    first_chunk = True
    chunk_num = 0
    rows_accumulated = 0

    # Create the pool once and reuse across all chunks.
    pool = ProcessPoolExecutor(max_workers=n_workers) if n_workers > 1 else None

    print("[1/2] Loading, classifying, and writing one chunk at a time (streaming, max_rows cap)...", flush=True)
    try:
        for chunk in pd.read_csv(
            input_csv,
            chunksize=chunk_size,
            dtype={"internal_id": "Int64", "id_text": str, "tr_oracc": str, "tr_cdli": str},
        ):
            chunk_num += 1
            chunk = chunk.dropna(subset=["tr_cdli", "tr_oracc"])
            chunk["tr_cdli"] = chunk["tr_cdli"].astype(str).str.strip()
            chunk["tr_oracc"] = chunk["tr_oracc"].astype(str).str.strip()
            chunk = chunk[chunk["tr_cdli"].astype(bool) & chunk["tr_oracc"].astype(bool)]

            mask_no_garbage = ~(
                chunk["tr_cdli"].str.contains("$", regex=False)
                | chunk["tr_oracc"].str.contains("$", regex=False)
            )
            chunk = chunk[mask_no_garbage]

            # Trim chunk to not exceed max_rows
            if rows_accumulated + len(chunk) > max_rows:
                take = max_rows - rows_accumulated
                chunk = chunk.iloc[:take]

            pairs = list(zip(chunk["tr_cdli"].tolist(), chunk["tr_oracc"].tolist()))
            n_pairs = len(pairs)

            chunk_start = time.perf_counter()
            if pool is None or n_pairs < n_workers:
                keep_mask, d_drop, d_keep = _process_chunk(pairs)
            else:
                parts = _split_pairs(pairs, n_workers)
                futures = [pool.submit(_process_chunk, part) for part in parts]
                results = [f.result() for f in futures]
                keep_mask, d_drop, d_keep = _merge_results(results)

            chunk_elapsed = time.perf_counter() - chunk_start

            # Derive counts from accumulators (avoids iterating keep_mask again)
            chunk_kept = sum(d_keep.values())
            chunk_dropped = sum(d_drop.values())
            total_rows += len(chunk)
            kept_rows += chunk_kept
            dropped_rows += chunk_dropped
            for k, v in d_drop.items():
                dropped_by_reason[k] = dropped_by_reason.get(k, 0) + v
            for k, v in d_keep.items():
                kept_by_label[k] = kept_by_label.get(k, 0) + v

            rows_accumulated += len(chunk)
            pct = 100 * rows_accumulated / max_rows if max_rows else 0
            print(f"      Chunk {chunk_num}: {len(pairs):,} rows in {chunk_elapsed:.1f}s (total {rows_accumulated:,} / {max_rows:,}, {pct:.0f}%)", flush=True)
            chunk_cleaned = chunk[keep_mask]
            if len(chunk_cleaned) > 0:
                chunk_cleaned.to_csv(
                    output_csv, mode="w" if first_chunk else "a", header=first_chunk, index=False
                )
                first_chunk = False

            if rows_accumulated >= max_rows:
                break
    finally:
        if pool is not None:
            pool.shutdown(wait=False)

    print("[2/2] Done.", flush=True)
    elapsed = time.perf_counter() - t0

    return {
        "total_rows": total_rows,
        "kept_rows": kept_rows,
        "dropped_rows": dropped_rows,
        "kept_pct": round(100 * kept_rows / total_rows, 1) if total_rows > 0 else 0.0,
        "dropped_by_reason": dropped_by_reason,
        "kept_by_label": kept_by_label,
        "output_path": str(output_csv),
        "elapsed_sec": round(elapsed, 2),
    }


def main() -> None:
    """CLI entry point."""
    print(f"Cleaning word_level.csv (subset: first {MAX_ROWS} rows)...")
    print(f"Input:  {INPUT_CSV}")
    print(f"Output: {OUTPUT_CSV}")
    print(f"Max rows: {MAX_ROWS:,}")
    print()

    try:
        stats = clean_word_level_subset()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    print("=" * 60)
    print("Cleaning complete (subset)")
    print("=" * 60)
    print(f"Total rows processed: {stats['total_rows']:,}")
    print(f"Rows kept:            {stats['kept_rows']:,} ({stats['kept_pct']}%)")
    print(f"Rows dropped:         {stats['dropped_rows']:,}")
    print()
    print("Dropped by reason:")
    for reason, count in stats["dropped_by_reason"].items():
        if count > 0:
            print(f"  {reason}: {count:,}")
    print()
    print("Kept by label:")
    for label, count in stats["kept_by_label"].items():
        if count > 0:
            print(f"  {label}: {count:,}")
    print()
    print(f"Cleaned subset saved to: {stats['output_path']}")
    print(f"Elapsed time: {stats['elapsed_sec']} seconds")


if __name__ == "__main__":
    main()
