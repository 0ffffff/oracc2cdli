# Suggested modifications (non-binding)

Optional restructuring ideas. No code or directories have been changed; this file only documents suggestions.

---

## 1. Reference data for conversion (decouple from `data/`)

**Priority:** Conversion scripts should not depend on `data/`, since that folder is largely gitignored and may not be uploaded to GitHub. The character-mapping CSV is small, canonical reference data and should live in a committed location.

**Current state:** All conversion code defaults to `data/reference/ATF_Character_Conventions.csv`:
- **`src/utils/utils.py`** — `_DEFAULT_MAPPING_PATH` points to `data/reference/ATF_Character_Conventions.csv`; `load_character_mapping` and `load_reverse_character_mapping` use it when no `csv_path` is passed.
- **`src/utils/word_conversion.py`** — Uses `utils.load_character_mapping` / `load_reverse_character_mapping` (no path), so it inherits the same default.
- **`src/oracc_to_cdli.py`** and **`src/cdli_to_oracc.py`** — Default `mapping_path` is `project_root / 'data' / 'reference' / 'ATF_Character_Conventions.csv'`.
- **`examples/example.py`** — Hardcodes `mapping_path = project_root / 'data' / 'reference' / 'ATF_Character_Conventions.csv'` (and uses `data/` for input/output sample files).

**Suggested change:**
- Move **`data/reference/ATF_Character_Conventions.csv`** to a directory that is committed, for example:
  - **`reference/`** at repo root (e.g. `reference/ATF_Character_Conventions.csv`), or
  - **`mappings/`** at repo root, or
  - **`src/utils/reference/`** (or `src/reference/`) so the mapping ships with the package.
- Update the default path in:
  - **`src/utils/utils.py`**: set `_DEFAULT_MAPPING_PATH` to the new path (e.g. `PROJECT_ROOT / "reference" / "ATF_Character_Conventions.csv"`).
  - **`src/oracc_to_cdli.py`** and **`src/cdli_to_oracc.py`**: default `mapping_path` to the same location.
- Update docstrings that mention `data/reference/` in **`src/utils/utils.py`**, **`src/utils/word_conversion.py`**, and **`src/utils/__init__.py`**.
- Update the README repository-structure diagram to show `reference/` (or the chosen directory) at repo root and remove or clarify that pipeline inputs/outputs stay in `data/`.
- Update **`examples/example.py`**: change the mapping path to the new location (e.g. `project_root / 'reference' / 'ATF_Character_Conventions.csv'`). Optionally keep sample input/output in `data/` (e.g. `Q499899-oracc.txt`, `Q499899-converted.txt`) if those small example files are committed, or move them to **`examples/data/`** so the example is self-contained and does not depend on `data/` at all.

**Result:** Conversion (CLI and library) works out of the box after clone without requiring any files in `data/`. Pipeline scripts (load_to_db, build_word_table, export_word_level, EDA, tests that use `word_level.csv`) continue to read/write `data/` as today.

> **Update (2026-02-24):** The performance cost of reading the mapping CSV has been largely mitigated: `word_conversion.py` now caches both character mappings at module level after the first load, so the CSV is read at most once per process (not once per word). Moving the CSV to a committed location is still recommended for deployment/portability reasons, but it is no longer a performance concern.

---

## 2. Naming and single-purpose modules

- **`src/utils/utils.py`** — The name is vague and the file does two distinct things: (1) load character mapping from CSV, (2) convert lines ORACC↔CDLI (and `validate_conversion` for CSV-based accuracy). Consider splitting into:
  - **`src/utils/mapping.py`** (or `src/utils/character_mapping.py`): `load_character_mapping`, `load_reverse_character_mapping`.
  - **`src/utils/conversion.py`**: `convert_line_oracc_to_cdli`, `convert_line_cdli_to_oracc`, and optionally `validate_conversion`.
  Then keep `src/utils/__init__.py` re-exporting the public API so existing `from src.utils import ...` still works.

- **`src/utils/validate.py`** — Contains both “clean a CDLI line” (`clean_line_cdli`) and “validate predicted vs reference file” (`validate`). If the project grows, consider:
  - **`src/utils/clean.py`**: `clean_line_cdli` (and any other normalisation used by validation).
  - **`src/utils/validate.py`**: file-based validation only, importing `clean_line_cdli` from `clean.py`.

---

## 3. Legacy script location

- **`src/preprocessing/preprocess_old.py`** — Marked as superseded by `build_word_table.py`. Options:
  - Move to a **`src/preprocessing/legacy/`** (or repo-root **`legacy/`**) folder so active preprocessing scripts are not mixed with deprecated ones, or
  - Add a clear **DEPRECATED** notice at the top and in the README so it’s obvious not to use it for new work.

---

## 4. EDA and generated output location

- **`src/eda/results/*.md`** — Generated EDA reports live inside `src/`. Common alternatives:
  - **`output/eda/`** or **`reports/eda/`** at repo root: keeps all generated outputs outside source.
  - **`docs/eda/`**: if you want EDA reports treated as documentation.

  This would require updating path constants in `transliteration_eda.py`, `finaldf_eda.py`, and `word_level_eda.py` (and optionally `.gitignore` if you ignore generated reports).

- **`src/preprocessing/dataset_quality_results/`** — Outputs from **`analyze_dataset_quality.py`** (e.g. `dataset_quality_findings.md`, `analysis_summary.json`) also live under `src/`. For consistency, consider the same strategy as EDA: e.g. **`output/preprocessing/`** or **`reports/dataset_quality/`** at repo root.

- **`src/tests/results/`** — Conversion reports (e.g. `conversion_report_2-18.md`) are generated under `src/tests/`. Optionally move to **`output/tests/`** or **`reports/tests/`** if you want all generated artifacts outside `src/`.

---

## 5. CLI entry points vs library layout

- Conversion CLIs (**`oracc_to_cdli.py`**, **`cdli_to_oracc.py`**) live in **`src/`** next to packages (`utils/`, `preprocessing/`, `eda/`). Alternatives:
  - **`scripts/`** at repo root: e.g. `scripts/oracc_to_cdli.py`, `scripts/cdli_to_oracc.py`, so all runnable entry points are in one place and `src/` is clearly “library only”.
  - Or a single **`scripts/convert.py`** with subcommands `oracc2cdli` and `cdli2oracc` to avoid duplicating the `clean` and argument logic.

---

## 6. Package visibility for `src.utils`

- Imports use **`from src.utils import ...`**. For that to resolve to `src/utils/utils.py`, **`src/utils/__init__.py`** must exist and re-export the symbols (or the project relies on some other mechanism). If it’s missing or inconsistent, adding **`src/__init__.py`** (empty or with version) and **`src/utils/__init__.py`** that explicitly imports from `utils.py` (and `validate.py`) will make the package layout clear and robust.

---

## 7. Data pipeline documentation

- Preprocessing has a clear order: **load_to_db** → **build_word_table** → **export_word_level** (and EDA scripts expect the resulting CSVs). Additional scripts such as **clean_word_level.py**, **analyze_dataset_quality.py**, and **run_word_conversion_tests.py** consume or produce files in **`data/`** or under **`src/`**. Adding a short “Data pipeline” section to the README (or a **`docs/DATA_PIPELINE.md`**) that lists these steps and the expected inputs/outputs (e.g. `transliteration.csv`, `finaldf.csv` → `oracc2cdli.db` → `word_level.csv`; optional cleaning and quality analysis) would help future contributors run and extend the pipeline.

---

You can adopt any, all, or none of these; they are suggestions only.
