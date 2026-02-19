"""
Load transliteration.csv and finaldf.csv into an SQLite database for easier access.

Workflow position: First step in the data pipeline. No prior scripts required.

Prerequisites:
  - data/transliteration.csv
  - data/finaldf.csv

Outputs:
  - data/oracc2cdli.db with tables: transliteration, finaldf

Run before: build_word_table.py, export_word_level.py, preprocess_old.py (legacy).
Run from project root or as a module.
"""

import sqlite3
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
TRANSLITERATION_CSV = DATA_DIR / "transliteration.csv"
FINALDF_CSV = DATA_DIR / "finaldf.csv"
DB_PATH = DATA_DIR / "oracc2cdli.db"

# Chunk size for finaldf (large file)
CHUNKSIZE = 100_000

# Avoid mixed-type inference on finaldf columns (many are mixed in CSV)
FINALDF_DTYPE_OVERRIDES = {
    "headform": str,
    "contrefs": str,
    "cf": str,
    "gw": str,
    "sense": str,
    "norm": str,
    "norm0": str,
    "base": str,
    "morph": str,
    "stem": str,
    "cont": str,
    "morph2": str,
    "aform": str,
}


def load_transliteration() -> pd.DataFrame:
    """Load transliteration.csv into a DataFrame."""
    if not TRANSLITERATION_CSV.exists():
        raise FileNotFoundError(f"Not found: {TRANSLITERATION_CSV}")
    return pd.read_csv(TRANSLITERATION_CSV, dtype={"id_text": str, "transliteration": str})


def load_finaldf_chunked():
    """Yield finaldf in chunks."""
    if not FINALDF_CSV.exists():
        raise FileNotFoundError(f"Not found: {FINALDF_CSV}")
    return pd.read_csv(
        FINALDF_CSV,
        chunksize=CHUNKSIZE,
        dtype=FINALDF_DTYPE_OVERRIDES,
        low_memory=True,
    )


def load_to_db(db_path: Path | str | None = None) -> None:
    """
    Load both CSVs into SQLite. Creates tables 'transliteration' and 'finaldf'.
    Replaces existing tables if they exist.
    """
    db_path = Path(db_path) if db_path else DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Transliteration: load in one go (typically smaller)
    print("Loading transliteration.csv...")
    trans_df = load_transliteration()
    print(f"  Rows: {len(trans_df):,}")

    with sqlite3.connect(db_path) as conn:
        trans_df.to_sql("transliteration", conn, if_exists="replace", index=False)
        print("  Table 'transliteration' written.")

        # Finaldf: append chunks
        print("Loading finaldf.csv (chunked)...")
        total = 0
        for i, chunk in enumerate(load_finaldf_chunked()):
            chunk.to_sql(
                "finaldf",
                conn,
                if_exists="replace" if i == 0 else "append",
                index=False,
            )
            total += len(chunk)
            print(f"  Chunk {i + 1}: {total:,} rows so far")
        print("  Table 'finaldf' written.")

    print(f"Database saved to {db_path}")


if __name__ == "__main__":
    load_to_db()
