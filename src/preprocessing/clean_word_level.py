"""
Clean word_level.csv by filtering out misaligned rows and garbage tokens.

Workflow position: Run after export_word_level.py. Produces a cleaned dataset
for training/evaluation that excludes likely misalignments and garbage.

Prerequisites:
  - data/word_level.csv (from load_to_db → build_word_table → export_word_level)

Outputs:
  - data/word_level_cleaned.csv (filtered dataset)

Filtering criteria:
  - KEEP: exact matches, high similarity (≥95%), conversion_issue (25-95% similarity)
  - DROP: likely_misaligned (<25% similarity), rows with garbage tokens ($, etc.)

Run before: Use word_level_cleaned.csv for conversion training/evaluation instead of word_level.csv.
"""

from __future__ import annotations

import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import diff_match_patch as dmp_module

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

# Reuse a single dmp instance for similarity (thread-safe for diff_main + diff_levenshtein)
_dmp = dmp_module.diff_match_patch()


def _char_similarity(a: str, b: str) -> float:
    """Return similarity in [0, 1] using diff_match_patch Levenshtein (faster than SequenceMatcher)."""
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    diffs = _dmp.diff_main(a, b)
    lev = _dmp.diff_levenshtein(diffs)
    max_len = max(len(a), len(b))
    return 1.0 - (lev / max_len)


def _classify_row(tr_cdli: str, tr_oracc: str) -> tuple[float, float, str]:
    """
    Convert both ways and compute similarity vs gold. Return (sim_c2o, sim_o2c, label).
    Labels: exact | high | conversion_issue | likely_misaligned
    Early exit: if first conversion similarity is very low, skip second conversion and drop row.
    """
    tr_cdli = tr_cdli.strip()
    tr_oracc = tr_oracc.strip()
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
    Matches analyze_dataset_quality.py pattern: strip once, then classify.
    """
    # Strip once before classification (matches analyze_dataset_quality.py)
    tr_cdli = tr_cdli.strip()
    tr_oracc = tr_oracc.strip()
    
    if not tr_cdli or not tr_oracc:
        return False, "empty_column"
    if "$" in tr_cdli or "$" in tr_oracc:
        return False, "garbage_token"
    
    # Handle exceptions at call site (matches analyze_dataset_quality.py pattern)
    try:
        _, _, label = _classify_row(tr_cdli, tr_oracc)
    except Exception:
        # If conversion fails, treat as misaligned
        return False, "misaligned"
    
    if label == "likely_misaligned":
        return False, "misaligned"
    return True, label


def _process_chunk(args: tuple) -> tuple[list[bool], dict, dict]:
    """
    Worker: process a list of (tr_cdli, tr_oracc) pairs. Returns (keep_mask, dropped_by_reason, kept_by_label).
    Must be top-level for multiprocessing pickling.
    """
    pairs = args
    keep_mask = []
    dropped_by_reason = {"empty_column": 0, "garbage_token": 0, "misaligned": 0}
    kept_by_label = {"exact": 0, "high": 0, "conversion_issue": 0}

    for tr_cdli, tr_oracc in pairs:
        # Data already stripped in preprocessing; _classify_pair will strip again for safety
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
    dropped_by_reason = {"empty_column": 0, "garbage_token": 0, "misaligned": 0}
    kept_by_label = {"exact": 0, "high": 0, "conversion_issue": 0}

    n_workers = max_workers if max_workers is not None else max(1, (os.cpu_count() or 2) - 1)
    first_chunk = True
    chunk_num = 0

    print("[1/2] Loading, classifying, and writing one chunk at a time (streaming)...", flush=True)
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
        if n_workers <= 1 or n_pairs < n_workers:
            keep_mask, d_drop, d_keep = _process_chunk(pairs)
        else:
            parts = _split_pairs(pairs, n_workers)
            with ProcessPoolExecutor(max_workers=n_workers) as pool:
                futures = [pool.submit(_process_chunk, part) for part in parts]
                results = [f.result() for f in futures]
            keep_mask = []
            d_drop = {"empty_column": 0, "garbage_token": 0, "misaligned": 0}
            d_keep = {"exact": 0, "high": 0, "conversion_issue": 0}
            for _mask, _drop, _keep in results:
                keep_mask.extend(_mask)
                for k, v in _drop.items():
                    d_drop[k] = d_drop.get(k, 0) + v
                for k, v in _keep.items():
                    d_keep[k] = d_keep.get(k, 0) + v

        chunk_elapsed = time.perf_counter() - chunk_start
        total_rows += len(chunk)
        kept_rows += sum(keep_mask)
        dropped_rows += len(keep_mask) - sum(keep_mask)
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
