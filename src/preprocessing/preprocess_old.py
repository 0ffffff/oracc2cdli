"""
[LEGACY] Preprocess data in the SQL database: remove duplicate IDs when content matches,
join transliteration and finaldf on id_text, and save the result to a new table.
Superseded by build_word_table.py for word-level CDLI/ORACC alignment.

Workflow position: Alternative to build_word_table; run only after load_to_db.py.

Prerequisites:
  - data/oracc2cdli.db with tables: transliteration, finaldf (i.e. run load_to_db.py first)

Outputs:
  - Table merged in data/oracc2cdli.db

Reads from and writes to data/oracc2cdli.db.
"""

import sqlite3
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "oracc2cdli.db"
MERGED_TABLE = "merged"


def load_tables(conn: sqlite3.Connection) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load transliteration and finaldf from the database."""
    trans = pd.read_sql("SELECT * FROM transliteration", conn)
    final = pd.read_sql("SELECT * FROM finaldf", conn)
    return trans, final


def dedupe_transliteration(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove duplicate id_text rows when content (transliteration) matches.
    Keeps one row per (id_text, transliteration).
    """
    before = len(df)
    out = df.drop_duplicates(subset=["id_text", "transliteration"], keep="first")
    removed = before - len(out)
    if removed:
        print(f"  Transliteration: removed {removed:,} duplicate rows (content match).")
    return out


def dedupe_finaldf(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove duplicate rows where id_text and all other content are identical.
    Keeps one row per unique full row.
    """
    before = len(df)
    out = df.drop_duplicates(keep="first")
    removed = before - len(out)
    if removed:
        print(f"  Finaldf: removed {removed:,} duplicate rows (content match).")
    return out


def preprocess(db_path: Path | str | None = None) -> None:
    """
    Load transliteration and finaldf from DB, dedupe by ID (when content matches),
    join on id_text, and save to table 'merged'.
    """
    db_path = Path(db_path) if db_path else DB_PATH
    if not db_path.exists():
        raise FileNotFoundError(
            f"Database not found: {db_path}. Run load_to_db.py first."
        )

    print("Loading tables from database...")
    with sqlite3.connect(db_path) as conn:
        trans, final = load_tables(conn)
        print(f"  Transliteration: {len(trans):,} rows")
        print(f"  Finaldf: {len(final):,} rows")

        print("Deduplicating (remove duplicate IDs when content matches)...")
        trans = dedupe_transliteration(trans)
        final = dedupe_finaldf(final)
        print(f"  Transliteration: {len(trans):,} rows after dedupe")
        print(f"  Finaldf: {len(final):,} rows after dedupe")

        print("Joining on id_text...")
        # Inner join: keep rows that have both transliteration and finaldf data
        # This lets us preserve the IDs that have both CDLI and ORACC transliterations.
        merged = trans.merge(final, on="id_text", how="inner")
        print(f"  Merged: {len(merged):,} rows")

        print(f"Writing table '{MERGED_TABLE}'...")
        merged.to_sql(MERGED_TABLE, conn, if_exists="replace", index=False)
        print(f"Done. Table '{MERGED_TABLE}' saved to {db_path}")


if __name__ == "__main__":
    preprocess()
