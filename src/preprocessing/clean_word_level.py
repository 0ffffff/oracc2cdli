"""
Clean word_level.csv by filtering out misaligned rows and garbage tokens.

Workflow position: Run after export_word_level.py. Produces a cleaned dataset
for training/evaluation that excludes likely misalignments and garbage.

Prerequisites:
  - data/word_level.csv (from load_to_db → build_word_table → export_word_level)

Outputs:
  - data/word_level_cleaned.csv (filtered dataset)

Filtering criteria:
  - KEEP: exact matches, high similarity (≥95%), conversion_issue (30-95% similarity)
  - DROP: likely_misaligned (<30% similarity), rows with garbage tokens ($, etc.)

Run before: Use word_level_cleaned.csv for conversion training/evaluation instead of word_level.csv.

Performance notes (2026-02-24):
  - Character mappings are loaded once per worker process and reused.
  - Redundant .strip() calls removed; stripping happens once in chunk preprocessing.
  - Redundant "$" check in _classify_pair removed; garbage filter is vectorized in
    chunk preprocessing.
  - ProcessPoolExecutor is created once and reused across all chunks.
  - kept/dropped counts derived from accumulators instead of sum(keep_mask).
"""

from __future__ import annotations

import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from rapidfuzz.distance import Levenshtein

# Project root
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import pandas as pd

from src.utils.word_conversion import word_cdli_to_oracc, word_oracc_to_cdli


# -----------------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------------

INPUT_CSV = _PROJECT_ROOT / "data" / "word_level.csv"
OUTPUT_CSV = _PROJECT_ROOT / "data" / "word_level_cleaned.csv"
CHUNK_SIZE = 100_000
MAX_WORKERS = None  # None = use CPU count - 1

# Similarity thresholds (same as analyze_dataset_quality.py)
SIM_EXACT = 1.0
SIM_HIGH = 0.95
SIM_LIKELY_MISALIGNED = 0.30

# Garbage tokens to filter out (rows containing these in either column)
GARBAGE_TOKENS = ["$", "($", "$)", "($)"]


def _char_similarity(a: str, b: str) -> float:
    """Return similarity in [0, 1] using rapidfuzz Levenshtein normalized_similarity."""
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return Levenshtein.normalized_similarity(a, b)


def _classify_row(tr_cdli: str, tr_oracc: str) -> tuple[float, float, str]:
    """
    Convert both ways and compute similarity vs gold. Return (sim_c2o, sim_o2c, label).
    Labels: exact | high | conversion_issue | likely_misaligned
    Early exit: if first conversion similarity is very low, skip second conversion and drop row.

    Expects pre-stripped inputs (stripping is done once in chunk preprocessing).
    """
    pred_oracc = word_cdli_to_oracc(tr_cdli)
    sim_c2o = _char_similarity(pred_oracc, tr_oracc)
    # Early exit: obvious mismatch, skip second conversion and similarity
    if sim_c2o < SIM_LIKELY_MISALIGNED:
        return sim_c2o, 0.0, "likely_misaligned"
    pred_cdli = word_oracc_to_cdli(tr_oracc)
    sim_o2c = _char_similarity(pred_cdli, tr_cdli)
    sim_min = min(sim_c2o, sim_o2c)
    sim_max = max(sim_c2o, sim_o2c)

    if sim_min >= SIM_EXACT:
        label = "exact"
    elif sim_min >= SIM_HIGH:
        label = "high"
    elif sim_min < SIM_LIKELY_MISALIGNED or sim_max < SIM_LIKELY_MISALIGNED:
        label = "likely_misaligned"
    else:
        label = "conversion_issue"
    return sim_c2o, sim_o2c, label


def _classify_pair(tr_cdli: str, tr_oracc: str) -> tuple[bool, str]:
    """
    Determine if a row should be kept. Returns (keep, reason).

    Expects pre-stripped, non-empty, garbage-free inputs. The empty-check and
    garbage-token check are kept as a safety net but should never trigger when
    called from the chunk pipeline (those rows are already filtered out).
    """
    if not tr_cdli or not tr_oracc:
        return False, "empty_column"

    # Handle exceptions at call site (matches analyze_dataset_quality.py pattern)
    try:
        _, _, label = _classify_row(tr_cdli, tr_oracc)
    except Exception:
        # If conversion fails, treat as misaligned
        return False, "misaligned"

    if label == "likely_misaligned":
        return False, "misaligned"
    return True, label


def _process_chunk(pairs: list[tuple[str, str]]) -> tuple[list[bool], dict, dict]:
    """
    Worker: process a list of (tr_cdli, tr_oracc) pairs. Returns (keep_mask, dropped_by_reason, kept_by_label).
    Must be top-level for multiprocessing pickling.
    """
    keep_mask = []
    dropped_by_reason = {"empty_column": 0, "garbage_token": 0, "misaligned": 0}
    kept_by_label = {"exact": 0, "high": 0, "conversion_issue": 0}

    for tr_cdli, tr_oracc in pairs:
        keep, reason = _classify_pair(tr_cdli, tr_oracc)
        keep_mask.append(keep)
        if keep:
            kept_by_label[reason] = kept_by_label.get(reason, 0) + 1
        else:
            dropped_by_reason[reason] = dropped_by_reason.get(reason, 0) + 1

    return keep_mask, dropped_by_reason, kept_by_label


def _split_pairs(pairs: list[tuple[str, str]], n_parts: int) -> list[list[tuple[str, str]]]:
    """Split pairs into n_parts contiguous sub-lists for parallel processing (order preserved)."""
    if n_parts <= 1 or len(pairs) <= n_parts:
        return [pairs]
    n = len(pairs)
    k = (n + n_parts - 1) // n_parts
    return [pairs[i * k : min((i + 1) * k, n)] for i in range(n_parts)]


def _merge_results(results: list[tuple[list[bool], dict, dict]]) -> tuple[list[bool], dict, dict]:
    """Merge keep_mask, dropped, and kept dicts from multiple worker results."""
    keep_mask: list[bool] = []
    d_drop: dict[str, int] = {"empty_column": 0, "garbage_token": 0, "misaligned": 0}
    d_keep: dict[str, int] = {"exact": 0, "high": 0, "conversion_issue": 0}
    for _mask, _drop, _keep in results:
        keep_mask.extend(_mask)
        for k, v in _drop.items():
            d_drop[k] = d_drop.get(k, 0) + v
        for k, v in _keep.items():
            d_keep[k] = d_keep.get(k, 0) + v
    return keep_mask, d_drop, d_keep


def clean_word_level(
    input_csv: Path | str | None = None,
    output_csv: Path | str | None = None,
    chunk_size: int = CHUNK_SIZE,
    max_workers: int | None = MAX_WORKERS,
) -> dict:
    """
    Load word_level.csv, filter rows, and save cleaned dataset.

    Returns dict with stats: {total_rows, kept_rows, dropped_rows, dropped_by_reason, elapsed_sec}
    """
    input_csv = Path(input_csv) if input_csv else INPUT_CSV
    output_csv = Path(output_csv) if output_csv else OUTPUT_CSV

    if not input_csv.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_csv}")

    output_csv.parent.mkdir(parents=True, exist_ok=True)

    t0 = time.perf_counter()

    # Stats
    total_rows = 0
    kept_rows = 0
    dropped_rows = 0
    dropped_by_reason: dict[str, int] = {"empty_column": 0, "garbage_token": 0, "misaligned": 0}
    kept_by_label: dict[str, int] = {"exact": 0, "high": 0, "conversion_issue": 0}

    n_workers = max_workers if max_workers is not None else max(1, (os.cpu_count() or 2) - 1)
    first_chunk = True
    chunk_num = 0

    # Create the pool once and reuse across all chunks (avoids repeated process spawn overhead).
    pool = ProcessPoolExecutor(max_workers=n_workers) if n_workers > 1 else None

    print("[1/2] Loading, classifying, and writing one chunk at a time (streaming)...", flush=True)
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

            # Vectorized garbage filter: drop rows with $ before expensive classification
            mask_no_garbage = ~(chunk["tr_cdli"].str.contains("$", regex=False) | chunk["tr_oracc"].str.contains("$", regex=False))
            chunk = chunk[mask_no_garbage]

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

            print(f"      Chunk {chunk_num}: {len(pairs):,} rows in {chunk_elapsed:.1f}s (total {total_rows:,} rows)", flush=True)
            chunk_cleaned = chunk[keep_mask]
            if len(chunk_cleaned) > 0:
                chunk_cleaned.to_csv(output_csv, mode="w" if first_chunk else "a", header=first_chunk, index=False)
                first_chunk = False
            # Chunk and pairs go out of scope here; only one chunk in memory at a time
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
    print("Cleaning word_level.csv...")
    print(f"Input:  {INPUT_CSV}")
    print(f"Output: {OUTPUT_CSV}")
    print()

    try:
        stats = clean_word_level()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    print("=" * 60)
    print("Cleaning complete")
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
    print(f"Cleaned dataset saved to: {stats['output_path']}")
    print(f"Elapsed time: {stats['elapsed_sec']} seconds")


if __name__ == "__main__":
    main()
