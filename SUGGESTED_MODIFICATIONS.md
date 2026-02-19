# Suggested modifications (non-binding)

Optional restructuring ideas. No code or directories have been changed; this file only documents suggestions.

---

## 1. Naming and single-purpose modules

- **`src/utils/utils.py`** — The name is vague and the file does two distinct things: (1) load character mapping from CSV, (2) convert lines ORACC↔CDLI (and `validate_conversion` for CSV-based accuracy). Consider splitting into:
  - **`src/utils/mapping.py`** (or `src/utils/character_mapping.py`): `load_character_mapping`, `load_reverse_character_mapping`.
  - **`src/utils/conversion.py`**: `convert_line_oracc_to_cdli`, `convert_line_cdli_to_oracc`, and optionally `validate_conversion`.
  Then keep `src/utils/__init__.py` re-exporting the public API so existing `from src.utils import ...` still works.

- **`src/utils/validate.py`** — Contains both “clean a CDLI line” (`clean_line_cdli`) and “validate predicted vs reference file” (`validate`). If the project grows, consider:
  - **`src/utils/clean.py`**: `clean_line_cdli` (and any other normalisation used by validation).
  - **`src/utils/validate.py`**: file-based validation only, importing `clean_line_cdli` from `clean.py`.

---

## 2. Legacy script location

- **`src/preprocessing/preprocess_old.py`** — Marked as superseded by `build_word_table.py`. Options:
  - Move to a **`src/preprocessing/legacy/`** (or repo-root **`legacy/`**) folder so active preprocessing scripts are not mixed with deprecated ones, or
  - Add a clear **DEPRECATED** notice at the top and in the README so it’s obvious not to use it for new work.

---

## 3. EDA output location

- **`src/eda/results/*.md`** — Generated EDA reports live inside `src/`. Common alternatives:
  - **`output/eda/`** or **`reports/eda/`** at repo root: keeps all generated outputs outside source.
  - **`docs/eda/`**: if you want EDA reports treated as documentation.

This would require updating path constants in `transliteration_eda.py`, `finaldf_eda.py`, and `word_level_eda.py` (and optionally `.gitignore` if you ignore generated reports).

---

## 4. CLI entry points vs library layout

- Conversion CLIs (**`oracc_to_cdli.py`**, **`cdli_to_oracc.py`**) live in **`src/`** next to packages (`utils/`, `preprocessing/`, `eda/`). Alternatives:
  - **`scripts/`** at repo root: e.g. `scripts/oracc_to_cdli.py`, `scripts/cdli_to_oracc.py`, so all runnable entry points are in one place and `src/` is clearly “library only”.
  - Or a single **`scripts/convert.py`** with subcommands `oracc2cdli` and `cdli2oracc` to avoid duplicating the `clean` and argument logic.

---

## 5. Package visibility for `src.utils`

- Imports use **`from src.utils import ...`**. For that to resolve to `src/utils/utils.py`, **`src/utils/__init__.py`** must exist and re-export the symbols (or the project relies on some other mechanism). If it’s missing or inconsistent, adding **`src/__init__.py`** (empty or with version) and **`src/utils/__init__.py`** that explicitly imports from `utils.py` (and `validate.py`) will make the package layout clear and robust.

---

## 6. Data pipeline documentation

- Preprocessing has a clear order: **load_to_db** → **build_word_table** → **export_word_level** (and EDA scripts expect the resulting CSVs). Adding a short “Data pipeline” section to the README (or a **`docs/DATA_PIPELINE.md`**) that lists these steps and the expected inputs/outputs (e.g. `transliteration.csv`, `finaldf.csv` → `oracc2cdli.db` → `word_level.csv`) would help future contributors run and extend the pipeline.

---

You can adopt any, all, or none of these; they are suggestions only.
