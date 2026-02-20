"""
Analyze word_level.csv for misalignment vs conversion failures.

Samples rows, runs CDLI<->ORACC conversion, and computes character-level
similarity (SequenceMatcher.ratio) between converted output and the other
column. Low similarity (e.g. < 20%) suggests the row is misaligned (different
words in the two columns), not a conversion bug. High similarity but not
exact suggests conversion or normalization gaps.

Outputs a summary dict and optional JSON for use in dataset_quality_findings.md.
Run from project root: python3 src/preprocessing/analyze_dataset_quality.py
"""
# TODO: fix and make sure it runs faster

from __future__ import annotations

import json
import os
import sys
from datetime import date
from difflib import SequenceMatcher
from pathlib import Path

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

DEFAULT_CSV = _PROJECT_ROOT / "data" / "word_level.csv"
SAMPLE_SIZE = 20_000
RANDOM_STATE = 42
# Similarity thresholds
SIM_EXACT = 1.0
SIM_HIGH = 0.95
SIM_LIKELY_MISALIGNED = 0.25  # below this: likely different words
SIM_VERY_LOW = 0.10           # near 0%: almost certainly misaligned


def _char_similarity(a: str, b: str) -> float:
    """Return similarity in [0, 1] using SequenceMatcher (character-level)."""
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _classify_row(
    tr_cdli: str,
    tr_oracc: str,
) -> tuple[float, float, str]:
    """
    Convert both ways and compute similarity vs gold. Return (sim_c2o, sim_o2c, label).
    Labels: exact | high | conversion_issue | likely_misaligned
    """
    pred_oracc = word_cdli_to_oracc(tr_cdli.strip())
    pred_cdli = word_oracc_to_cdli(tr_oracc.strip())
    sim_c2o = _char_similarity(pred_oracc, tr_oracc.strip())
    sim_o2c = _char_similarity(pred_cdli, tr_cdli.strip())
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


def run_analysis(
    csv_path: Path | str | None = None,
    sample_size: int = SAMPLE_SIZE,
    random_state: int = RANDOM_STATE,
) -> dict:
    """
    Load word_level.csv, sample rows with both tr_cdli and tr_oracc,
    run conversion and similarity, return summary stats.
    """
    csv_path = Path(csv_path) if csv_path else DEFAULT_CSV
    if not csv_path.exists():
        return {"error": f"CSV not found: {csv_path}"}

    # Load in chunks to limit memory; sample across chunks for randomness
    chunk_size = 100_000
    chunks = []
    total_seen = 0
    for chunk in pd.read_csv(
        csv_path,
        chunksize=chunk_size,
        dtype={"internal_id": "Int64", "id_text": str, "tr_oracc": str, "tr_cdli": str},
    ):
        chunk = chunk.dropna(subset=["tr_cdli", "tr_oracc"])
        chunk["tr_cdli"] = chunk["tr_cdli"].astype(str).str.strip()
        chunk["tr_oracc"] = chunk["tr_oracc"].astype(str).str.strip()
        chunk = chunk[chunk["tr_cdli"].astype(bool) & chunk["tr_oracc"].astype(bool)]
        chunks.append(chunk)
        total_seen += len(chunk)
        if total_seen >= sample_size * 3:
            break
    df = pd.concat(chunks, ignore_index=True)
    total = len(df)
    if total == 0:
        return {"error": "No rows with both tr_cdli and tr_oracc", "total_rows": 0}

    if total > sample_size:
        df = df.sample(n=sample_size, random_state=random_state)

    counts = {"exact": 0, "high": 0, "conversion_issue": 0, "likely_misaligned": 0}
    sim_c2o_sum = 0.0
    sim_o2c_sum = 0.0
    very_low_c2o = 0  # sim_c2o < SIM_VERY_LOW
    very_low_o2c = 0
    low_c2o = 0   # sim_c2o < SIM_LIKELY_MISALIGNED
    low_o2c = 0
    examples_misaligned = []
    examples_exact = []
    examples_conversion_issue = []

    for _, row in df.iterrows():
        tr_cdli = row["tr_cdli"]
        tr_oracc = row["tr_oracc"]
        try:
            sim_c2o, sim_o2c, label = _classify_row(tr_cdli, tr_oracc)
        except Exception as e:
            counts["conversion_issue"] += 1
            sim_c2o, sim_o2c, label = 0.0, 0.0, "conversion_issue"
        counts[label] += 1
        sim_c2o_sum += sim_c2o
        sim_o2c_sum += sim_o2c
        if sim_c2o < SIM_VERY_LOW:
            very_low_c2o += 1
        if sim_o2c < SIM_VERY_LOW:
            very_low_o2c += 1
        if sim_c2o < SIM_LIKELY_MISALIGNED:
            low_c2o += 1
        if sim_o2c < SIM_LIKELY_MISALIGNED:
            low_o2c += 1
        # Collect a few examples
        if label == "likely_misaligned" and len(examples_misaligned) < 15:
            examples_misaligned.append({
                "tr_cdli": tr_cdli[:50],
                "tr_oracc": tr_oracc[:50],
                "sim_c2o": round(sim_c2o, 3),
                "sim_o2c": round(sim_o2c, 3),
            })
        if label == "exact" and len(examples_exact) < 5:
            examples_exact.append({"tr_cdli": tr_cdli[:40], "tr_oracc": tr_oracc[:40]})
        if label == "conversion_issue" and len(examples_conversion_issue) < 10:
            pred_o = word_cdli_to_oracc(tr_cdli)
            pred_c = word_oracc_to_cdli(tr_oracc)
            examples_conversion_issue.append({
                "tr_cdli": tr_cdli[:40],
                "tr_oracc": tr_oracc[:40],
                "pred_oracc": pred_o[:40],
                "pred_cdli": pred_c[:40],
                "sim_c2o": round(sim_c2o, 3),
                "sim_o2c": round(sim_o2c, 3),
            })

    n = len(df)
    return {
        "rows_loaded": total,
        "sample_size": n,
        "counts": counts,
        "pct": {k: round(100 * v / n, 1) for k, v in counts.items()},
        "mean_sim_cdli_to_oracc": round(sim_c2o_sum / n, 4),
        "mean_sim_oracc_to_cdli": round(sim_o2c_sum / n, 4),
        "very_low_similarity": {
            "sim_c2o_below_10pct": very_low_c2o,
            "sim_o2c_below_10pct": very_low_o2c,
            "sim_c2o_below_25pct": low_c2o,
            "sim_o2c_below_25pct": low_o2c,
        },
        "thresholds": {
            "SIM_EXACT": SIM_EXACT,
            "SIM_HIGH": SIM_HIGH,
            "SIM_LIKELY_MISALIGNED": SIM_LIKELY_MISALIGNED,
            "SIM_VERY_LOW": SIM_VERY_LOW,
        },
        "examples_misaligned": examples_misaligned,
        "examples_exact": examples_exact,
        "examples_conversion_issue": examples_conversion_issue,
    }


def main() -> None:
    out = run_analysis()
    if "error" in out:
        print(out["error"])
        sys.exit(1)

    lines = [
        "# Dataset quality analysis",
        "",
        "Character-level similarity after CDLI↔ORACC conversion.",
        "",
        "## Summary",
        "",
        f"- **Rows loaded** (with both columns non-empty): {out['rows_loaded']:,}",
        f"- **Sample size**: {out['sample_size']:,}",
        "",
        "## Classification (min similarity in both directions)",
        "",
        "| Label | Count | % |",
        "|-------|-------|---|",
    ]
    for k, v in out["counts"].items():
        lines.append(f"| {k} | {v:,} | {out['pct'][k]}% |")
    lines.extend([
        "",
        "## Mean character similarity (converted vs gold)",
        "",
        f"- CDLI→ORACC vs tr_oracc: **{out['mean_sim_cdli_to_oracc']}**",
        f"- ORACC→CDLI vs tr_cdli: **{out['mean_sim_oracc_to_cdli']}**",
        "",
        "## Likely misaligned (similarity below threshold)",
        "",
    ])
    vl = out["very_low_similarity"]
    lines.extend([
        f"- sim(CDLI→ORACC, tr_oracc) < 10%: {vl['sim_c2o_below_10pct']:,}",
        f"- sim(ORACC→CDLI, tr_cdli) < 10%: {vl['sim_o2c_below_10pct']:,}",
        f"- sim(CDLI→ORACC, tr_oracc) < 25%: {vl['sim_c2o_below_25pct']:,}",
        f"- sim(ORACC→CDLI, tr_cdli) < 25%: {vl['sim_o2c_below_25pct']:,}",
        "",
    ])
    report_text = "\n".join(lines)

    print("Dataset quality analysis (character-level similarity after conversion)")
    print("=" * 60)
    print(f"Rows loaded (with both columns non-empty): {out['rows_loaded']:,}")
    print(f"Sample size: {out['sample_size']:,}")
    print()
    print("Classification (based on min similarity in both directions):")
    for k, v in out["counts"].items():
        print(f"  {k}: {v:,} ({out['pct'][k]}%)")
    print()
    print("Mean character similarity (converted vs gold):")
    print(f"  CDLI→ORACC vs tr_oracc: {out['mean_sim_cdli_to_oracc']}")
    print(f"  ORACC→CDLI vs tr_cdli:  {out['mean_sim_oracc_to_cdli']}")
    print()
    print("Likely misaligned (similarity below threshold):")
    print(f"  sim(CDLI→ORACC, tr_oracc) < 10%: {vl['sim_c2o_below_10pct']:,}")
    print(f"  sim(ORACC→CDLI, tr_cdli) < 10%:  {vl['sim_o2c_below_10pct']:,}")
    print(f"  sim(CDLI→ORACC, tr_oracc) < 25%: {vl['sim_c2o_below_25pct']:,}")
    print(f"  sim(ORACC→CDLI, tr_cdli) < 25%:  {vl['sim_o2c_below_25pct']:,}")

    results_dir = _SCRIPT_DIR / "dataset_quality_results"
    results_dir.mkdir(exist_ok=True)
    today = date.today().isoformat()
    md_path = results_dir / f"dataset_quality_{today}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(report_text)
    print(f"\nReport saved to {md_path}")

    out_path = results_dir / "analysis_summary.json"
    # JSON-serializable: no Path objects
    out_serial = {k: v for k, v in out.items()}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out_serial, f, indent=2, ensure_ascii=False)
    print(f"Results saved to {out_path}")


if __name__ == "__main__":
    main()
