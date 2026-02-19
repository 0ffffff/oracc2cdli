"""
Export the word_level table from SQLite to a CSV file in data/.

Workflow position: Run after build_word_table.py. Produces the CSV used by EDA and tests.

Prerequisites:
  - data/oracc2cdli.db with table word_level (i.e. run load_to_db.py then build_word_table.py first)

Outputs:
  - data/word_level.csv

Run before: src/eda/word_level_eda.py (expects this CSV); src/tests/run_word_conversion_tests.py
(optional dataset for comparison tests). Run from project root or as a module.
"""

import sqlite3
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "oracc2cdli.db"
OUTPUT_CSV = DATA_DIR / "word_level.csv"
WORD_LEVEL_TABLE = "word_level"


def export_word_level(db_path: Path | str | None = None, output_path: Path | str | None = None) -> Path:
    """
    Read the word_level table from the SQLite database and write it to a CSV file.
    Returns the path to the written CSV.
    """
    db_path = Path(db_path) if db_path else DB_PATH
    output_path = Path(output_path) if output_path else OUTPUT_CSV

    if not db_path.exists():
        raise FileNotFoundError(
            f"Database not found: {db_path}. Run load_to_db.py and build_word_table.py first."
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        df = pd.read_sql(f"SELECT * FROM {WORD_LEVEL_TABLE}", conn)

    df.to_csv(output_path, index=False)
    print(f"Exported {len(df):,} rows from '{WORD_LEVEL_TABLE}' to {output_path}")
    return output_path


if __name__ == "__main__":
    export_word_level()
