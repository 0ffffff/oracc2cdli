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
│   ├── Q499899-cdli.txt          # Example CDLI-format input
│   ├── Q499899-oracc.txt         # Example ORACC-format input
│   ├── Q499899-cli-output.txt   # Example CLI conversion output
│   └── reference/
│       └── ATF_Character_Conventions.csv   # ORACC ↔ CDLI character mapping
├── examples/
│   ├── README.md
│   └── example.py               # Example ORACC→CDLI conversion (no CLI args)
└── src/
    ├── oracc_to_cdli.py         # CLI: ORACC → CDLI convert & clean
    ├── cdli_to_oracc.py         # CLI: CDLI → ORACC convert & clean
    ├── utils/
    │   ├── __init__.py          # Re-exports conversion, mapping, word_conversion, validate
    │   ├── utils.py             # Character mapping + line-level conversion (ORACC↔CDLI)
    │   ├── word_conversion.py   # Atomic word-level conversion (ORACC↔CDLI)
    │   └── validate.py         # Clean CDLI lines; compare predicted vs reference file
    ├── preprocessing/
    │   ├── __init__.py
    │   ├── load_to_db.py        # Load transliteration.csv + finaldf.csv → SQLite
    │   ├── build_word_table.py  # Build word-level table (id_text, tr_oracc, tr_cdli) in DB
    │   ├── export_word_level.py # Export word_level table from DB → data/word_level.csv
    │   └── preprocess_old.py    # [Legacy] Merge/dedupe transliteration+finaldf; superseded by build_word_table
    └── eda/
        ├── transliteration_eda.py  # EDA for transliteration.csv → results/transliteration_eda.md
        ├── finaldf_eda.py          # Chunked EDA for finaldf.csv → results/finaldf_eda.md
        ├── word_level_eda.py       # Chunked EDA for word_level.csv → results/word_level_eda.md
        └── results/                # Generated EDA reports (*.md)
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
| **src/preprocessing/preprocess_old.py** | [Legacy] Dedupe transliteration/finaldf, join on id_text, write merged table. Superseded by build_word_table. |
| **src/eda/transliteration_eda.py** | EDA for `transliteration.csv` (full load): basic info, dtypes, missing, id_text/word counts, special notation. Writes `src/eda/results/transliteration_eda.md`. |
| **src/eda/finaldf_eda.py** | Chunked EDA for `finaldf.csv`: basic info, dtypes, missing, numeric stats, value counts. Writes `src/eda/results/finaldf_eda.md`. |
| **src/eda/word_level_eda.py** | Chunked EDA for `word_level.csv`: basic info, dtypes, missing, key stats (e.g. tr_oracc vs tr_cdli match). Writes `src/eda/results/word_level_eda.md`. |
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

## Example without CLI

```bash
python3 examples/example.py
```

Runs the example that loads the mapping, reads `data/Q499899-oracc.txt`, converts to CDLI, and writes `data/Q499899-converted.txt`.
