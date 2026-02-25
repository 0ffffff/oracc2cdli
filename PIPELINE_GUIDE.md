# Pipeline Guide: Building `word_level_cleaned.csv`

This guide walks through the full pipeline from raw source CSVs to a cleaned word-level dataset ready for conversion training and evaluation.

All commands are run from the project root.

---

## Prerequisites

You need two source CSV files placed in `data/`:

- **`data/transliteration.csv`** — CDLI-format transliterations (columns: `id_text`, `transliteration`)
- **`data/finaldf.csv`** — ORACC-format word data (columns include `id_text`, `id_word`, `form`, etc.)

These are the raw datasets containing CDLI and ORACC transliterations respectively.

---

## 1. Install dependencies

Requires Python ≥ 3.14. Install with [uv](https://docs.astral.sh/uv/):

```bash
uv sync
```

Or with pip:

```bash
pip install -r requirements.txt
```

Core dependencies: `pandas`, `rapidfuzz`. EDA scripts also use `numpy` (installed as a pandas dependency).

---

## 2. (Optional) Run EDA on source datasets

Explore the raw datasets before processing. Each script writes a Markdown report to `src/eda/results/`.

```bash
python3 src/eda/transliteration_eda.py   # → src/eda/results/transliteration_eda.md
python3 src/eda/finaldf_eda.py           # → src/eda/results/finaldf_eda.md
```

---

## 3. Load source CSVs into SQLite

Loads `transliteration.csv` and `finaldf.csv` into `data/oracc2cdli.db` (tables: `transliteration`, `finaldf`).

```bash
python3 src/preprocessing/load_to_db.py
```

Script: [`src/preprocessing/load_to_db.py`](src/preprocessing/load_to_db.py)

---

## 4. Build the word-level table

Joins and aligns the two source tables at the word level inside the database. Splits CDLI full-line transliterations into individual words and aligns them with ORACC word forms by position within each text.

Creates table `word_level` in the database with columns: `internal_id`, `id_text`, `id_word`, `tr_oracc`, `tr_cdli`.

```bash
python3 src/preprocessing/build_word_table.py
```

Script: [`src/preprocessing/build_word_table.py`](src/preprocessing/build_word_table.py)

---

## 5. Export word-level table to CSV

Exports the `word_level` table from the database to `data/word_level.csv`.

```bash
python3 src/preprocessing/export_word_level.py
```

Script: [`src/preprocessing/export_word_level.py`](src/preprocessing/export_word_level.py)

---

## 6. (Optional) Analyze dataset quality

Samples rows from `word_level.csv`, runs bidirectional CDLI↔ORACC conversion, and classifies each row by character-level similarity. Useful for understanding how much of the dataset is misaligned vs. has conversion gaps.

```bash
python3 src/preprocessing/analyze_dataset_quality.py
```

Outputs a dated Markdown report and `analysis_summary.json` to `src/preprocessing/dataset_quality_results/`.

Script: [`src/preprocessing/analyze_dataset_quality.py`](src/preprocessing/analyze_dataset_quality.py)

You can also run EDA on the raw word-level dataset:

```bash
python3 src/eda/word_level_eda.py   # → src/eda/results/word_level_eda.md
```

---

## 7. Clean the dataset

Filters `word_level.csv` to remove misaligned rows and garbage tokens, producing `data/word_level_cleaned.csv`.

```bash
python3 src/preprocessing/clean_word_level.py
```

Script: [`src/preprocessing/clean_word_level.py`](src/preprocessing/clean_word_level.py)

**What gets kept and dropped:**

- **Kept:** `exact` (100% similarity), `high` (≥95%), `conversion_issue` (30–95% — real pairs with conversion gaps)
- **Dropped:** `likely_misaligned` (<30% similarity — different words in the two columns), rows containing garbage tokens (`$`, `($`, `$)`, `($)`)

### Tuning thresholds

The similarity thresholds are defined as constants at the top of [`src/preprocessing/clean_word_level.py`](src/preprocessing/clean_word_level.py):

```python
SIM_EXACT = 1.0
SIM_HIGH = 0.95
SIM_LIKELY_MISALIGNED = 0.30
```

- **`SIM_LIKELY_MISALIGNED`** is the main knob. Lowering it (e.g. to `0.20`) keeps more borderline pairs; raising it (e.g. to `0.40`) drops more aggressively.
- **`SIM_HIGH`** sets the boundary between "high similarity" and "conversion issue." Adjusting this changes labeling but not what gets kept or dropped — both categories are retained.
- **`GARBAGE_TOKENS`** can be edited to add or remove tokens that indicate broken/incomplete data.

After changing thresholds, re-run the script to regenerate `word_level_cleaned.csv`.

---

## 8. (Optional) Post-cleaning EDA

Run EDA on the cleaned dataset. The report includes a comparison against the uncleaned `word_level.csv` stats.

```bash
python3 src/eda/word_level_cleaned_eda.py   # → src/eda/results/word_level_cleaned_eda.md
```

Script: [`src/eda/word_level_cleaned_eda.py`](src/eda/word_level_cleaned_eda.py)

---

## Summary

| Step | Command | Output |
|------|---------|--------|
| Install deps | `uv sync` | — |
| EDA (source) | `python3 src/eda/transliteration_eda.py` | `src/eda/results/transliteration_eda.md` |
| | `python3 src/eda/finaldf_eda.py` | `src/eda/results/finaldf_eda.md` |
| Load to DB | `python3 src/preprocessing/load_to_db.py` | `data/oracc2cdli.db` |
| Build table | `python3 src/preprocessing/build_word_table.py` | `word_level` table in DB |
| Export CSV | `python3 src/preprocessing/export_word_level.py` | `data/word_level.csv` |
| Quality analysis | `python3 src/preprocessing/analyze_dataset_quality.py` | `src/preprocessing/dataset_quality_results/` |
| EDA (word-level) | `python3 src/eda/word_level_eda.py` | `src/eda/results/word_level_eda.md` |
| Clean | `python3 src/preprocessing/clean_word_level.py` | `data/word_level_cleaned.csv` |
| EDA (cleaned) | `python3 src/eda/word_level_cleaned_eda.py` | `src/eda/results/word_level_cleaned_eda.md` |
