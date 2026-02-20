# ORACC2CDLI

A tool to convert ORACC transliteration to CDLI transliteration formats, under the FactGrid Cuneiform system.  
Achieves 99.96% accuracy on the oldassyrian-lines dataset.

**Current progress:** Converts ORACC → CDLI_clean. Full conversion to CDLI is limited by physical damage markers and editorial corrections.  
**TODO:** Refactor code, improve user-friendliness.

---

## Repository structure

```
oracc2cdli/
├── README.md
├── data/
│   ├── Q499899-cdli.txt              # Example CDLI-format input
│   ├── Q499899-oracc.txt             # Example ORACC-format input
│   ├── Q499899-cli-output.txt        # Example CLI conversion output
│   ├── word_level_cleaned_subset.csv # Cleaned subset (first N rows) for benchmarking
│   └── reference/
│       └── ATF_Character_Conventions.csv   # ORACC ↔ CDLI character mapping
├── examples/
│   ├── README.md
│   └── example.py                    # Example ORACC→CDLI conversion (no CLI args)
└── src/
    ├── oracc_to_cdli.py              # CLI: ORACC → CDLI convert & clean
    ├── cdli_to_oracc.py              # CLI: CDLI → ORACC convert & clean
    ├── utils/
    │   ├── __init__.py               # Re-exports conversion, mapping, word_conversion, validate
    │   ├── utils.py                  # Character mapping + line-level conversion (ORACC↔CDLI)
    │   ├── word_conversion.py        # Atomic word-level conversion (ORACC↔CDLI)
    │   └── validate.py               # Clean CDLI lines; compare predicted vs reference file
    ├── preprocessing/
    │   ├── __init__.py
    │   ├── load_to_db.py             # Load transliteration.csv + finaldf.csv → SQLite
    │   ├── build_word_table.py       # Build word-level table (id_text, tr_oracc, tr_cdli) in DB
    │   ├── export_word_level.py      # Export word_level table from DB → data/word_level.csv
    │   ├── clean_word_level.py       # Filter word_level.csv → data/word_level_cleaned.csv (drop misaligned/garbage)
    │   ├── clean_word_level_subset.py # Same as clean_word_level on first N rows → word_level_cleaned_subset.csv
    │   ├── analyze_dataset_quality.py # Sample word_level.csv; classify misalignment vs conversion; summary + JSON
    │   ├── preprocess_old.py         # [Legacy] Merge/dedupe transliteration+finaldf; superseded by build_word_table
    │   └── dataset_quality_results/  # Quality analysis outputs
    │       ├── dataset_quality_findings.md   # Narrative findings on bad data / misalignment
    │       ├── cleaning_filter_analysis.md   # Analysis of cleaning filter impact
    │       ├── dataset_quality_2026-02-19.md # Dated quality report
    │       └── analysis_summary.json         # Summary stats for tooling
    ├── eda/
    │   ├── transliteration_eda.py    # EDA for transliteration.csv → results/transliteration_eda.md
    │   ├── finaldf_eda.py            # Chunked EDA for finaldf.csv → results/finaldf_eda.md
    │   ├── word_level_eda.py         # Chunked EDA for word_level.csv → results/word_level_eda.md
    │   └── results/                  # Generated EDA reports (*.md)
    └── tests/
        ├── __init__.py
        ├── test_word_conversion.py   # Reusable API: unit + dataset (chunked) word conversion tests
        ├── run_word_conversion_tests.py  # Runner: unit tests + dataset tests; optional --report path
        └── results/                  # Dated conversion reports (e.g. conversion_report_2-18.md, conversion_report_2-19.md)
```

---

## Script map (by purpose)

Script headers and roles (descriptions match each file’s module docstring):

| Path | Purpose |
|------|--------|
| **src/oracc_to_cdli.py** | CLI: convert ORACC → CDLI, or clean an input file (strip lines). Subcommands: `convert`, `clean`. Uses `src.utils` for mapping and line conversion. |
| **src/cdli_to_oracc.py** | CLI: convert CDLI → ORACC, or clean an input file. Subcommands: `convert`, `clean`. Uses `src.utils` for reverse mapping and line conversion. |
| **src/utils/utils.py** | Character mapping (load_character_mapping, load_reverse_character_mapping from reference CSV); line-level conversion (convert_line_oracc_to_cdli, convert_line_cdli_to_oracc); validate_conversion for CSV accuracy. For single-word conversion use word_conversion. |
| **src/utils/word_conversion.py** | Atomic word-level conversion between CDLI and ORACC (word_oracc_to_cdli, word_cdli_to_oracc). Handles subscripts, determinatives, ellipsis. For line-level conversion use utils.py. |
| **src/utils/validate.py** | clean_line_cdli: normalise one line to CDLI_clean (strip markers, determinatives). validate: compare predicted vs reference file by line ID; CLI entry point. |
| **src/preprocessing/load_to_db.py** | Load `transliteration.csv` and `finaldf.csv` (chunked) into SQLite `data/oracc2cdli.db`. Run from project root or as module. |
| **src/preprocessing/build_word_table.py** | Build word-level table (id_text, tr_oracc, tr_cdli) from transliteration + finaldf; write table `word_level` to same DB. Run after load_to_db. |
| **src/preprocessing/export_word_level.py** | Export the `word_level` table from SQLite to `data/word_level.csv`. Requires oracc2cdli.db with table `word_level`. |
| **src/preprocessing/clean_word_level.py** | Clean `word_level.csv`: filter out misaligned rows and garbage tokens; output `data/word_level_cleaned.csv`. Run after export_word_level. Uses diff_match_patch for similarity; keeps exact/high/conversion_issue, drops likely_misaligned and garbage. |
| **src/preprocessing/clean_word_level_subset.py** | Same logic as clean_word_level on first N rows only; output `data/word_level_cleaned_subset.csv`. For benchmarking/timing; delete output when done. |
| **src/preprocessing/analyze_dataset_quality.py** | Sample `word_level.csv`, run CDLI↔ORACC conversion, classify rows (exact / high / conversion_issue / likely_misaligned). Writes summary and optional JSON to `dataset_quality_results/`. Run from project root. |
| **src/preprocessing/preprocess_old.py** | [Legacy] Dedupe transliteration/finaldf, join on id_text, write merged table. Superseded by build_word_table. |
| **src/eda/transliteration_eda.py** | EDA for `transliteration.csv` (full load): basic info, dtypes, missing, id_text/word counts, special notation. Writes `src/eda/results/transliteration_eda.md`. |
| **src/eda/finaldf_eda.py** | Chunked EDA for `finaldf.csv`: basic info, dtypes, missing, numeric stats, value counts. Writes `src/eda/results/finaldf_eda.md`. |
| **src/eda/word_level_eda.py** | Chunked EDA for `word_level.csv`: basic info, dtypes, missing, key stats (e.g. tr_oracc vs tr_cdli match). Writes `src/eda/results/word_level_eda.md`. |
| **src/tests/test_word_conversion.py** | Reusable test API: unit tests (empty, None, malformed, edge cases, round-trip) and chunked dataset tests on word_level CSV. Returns result dicts; use with run_word_conversion_tests or your own flow. |
| **src/tests/run_word_conversion_tests.py** | Runner: runs unit tests and dataset tests (chunked); optional `--report <path>` to write Markdown report (e.g. `results/conversion_report_2-19.md`). Supports `--csv`, `--chunk`, `--max-rows`, `--no-roundtrip`, `--roundtrip-sample`. Run from project root. |
| **examples/example.py** | Example: load mapping from reference CSV, read ORACC file, convert lines to CDLI with utils, save to file. No CLI arguments. |

---

## CLI usage

Input/output format examples: see `data/Q499899-*.txt`.

### ORACC → CDLI

```bash
python3 src/oracc_to_cdli.py convert <input_file> <output_file> [--has-label]
```

### CDLI → ORACC

```bash
python3 src/cdli_to_oracc.py convert <input_file> <output_file> [--has-label]
```

### Clean (strip lines; either format)

```bash
python3 src/oracc_to_cdli.py clean <input_file> <output_file>
# or
python3 src/cdli_to_oracc.py clean <input_file> <output_file>
```

Use `--has-label` when each line starts with an ID/label (e.g. `P359065:obverse.1.1`) followed by the word.  
Optional `--mapping <path>` overrides the default `data/reference/ATF_Character_Conventions.csv`.

### Validate predicted output against reference CDLI

```bash
python3 src/utils/validate.py <predicted_file> <test_file>
```

Compares predicted lines to the reference CDLI file (by line ID) and prints match rate and mismatches.

---

## Dataset quality and cleaning

After building and exporting the word-level table:

1. **Analyze quality** (sample-based): `python3 src/preprocessing/analyze_dataset_quality.py`  
   Writes summary and optional JSON to `src/preprocessing/dataset_quality_results/` (e.g. `dataset_quality_findings.md`, `dataset_quality_2026-02-19.md`, `analysis_summary.json`).

2. **Clean full dataset**: `python3 src/preprocessing/clean_word_level.py`  
   Reads `data/word_level.csv`, filters misaligned rows and garbage tokens, writes `data/word_level_cleaned.csv`.

3. **Benchmark cleaning** (subset): `python3 src/preprocessing/clean_word_level_subset.py`  
   Same logic on first N rows only; writes `data/word_level_cleaned_subset.csv`. For timing; delete output when done.

---

## Word conversion tests

Run unit and dataset (chunked) word conversion tests from project root:

```bash
python3 src/tests/run_word_conversion_tests.py
```

Optional: write a dated Markdown report:

```bash
python3 src/tests/run_word_conversion_tests.py --report src/tests/results/conversion_report_2-19.md
```

Reports are stored under `src/tests/results/` (e.g. `conversion_report_2-18.md`, `conversion_report_2-19.md`). Use `--csv`, `--chunk`, `--max-rows`, `--no-roundtrip`, or `--roundtrip-sample` to tune the run.

---

## Example without CLI

```bash
python3 examples/example.py
```

Runs the example that loads the mapping, reads `data/Q499899-oracc.txt`, converts to CDLI, and writes `data/Q499899-converted.txt`.
