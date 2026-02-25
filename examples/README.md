# Examples

> [!NOTE]
> These examples are outdated, and use `src/cdli_to_oracc.py` and `src/oracc_to_cdli.py`. For a more up-to-date conversion, leverage `src/utils/word_conversion.py`.

- **`example.py`** — Demonstrates ORACC → CDLI line-level conversion using `src.utils`. Loads the character mapping from `data/reference/ATF_Character_Conventions.csv`, reads `data/Q499899-oracc.txt`, converts each line, and writes `data/Q499899-converted.txt`. Run from project root:

  ```bash
  python3 examples/example.py
  ```

See `../README.md` for full CLI usage and the preprocessing pipeline.
