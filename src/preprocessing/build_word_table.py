"""
Build a word-level table: one row per word, with id_text, tr_oracc (ORACC form),
and tr_cdli (CDLI transliteration word). Slices full lines from transliteration
into individual words and aligns with finaldf 'form' by position within each id_text.

Workflow position: Run after load_to_db.py; required before export_word_level.py.

Prerequisites:
  - data/oracc2cdli.db with tables: transliteration, finaldf (i.e. run load_to_db.py first)

Outputs:
  - Table word_level in data/oracc2cdli.db (columns: internal_id, id_text, id_word, tr_oracc, tr_cdli)

Run before: export_word_level.py (to produce data/word_level.csv); EDA (word_level_eda.py)
and tests (run_word_conversion_tests.py) use that CSV.
"""

import sqlite3
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "oracc2cdli.db"
WORD_LEVEL_TABLE = "word_level"


def _cdli_words_from_transliteration(trans: pd.DataFrame) -> pd.DataFrame:
    """
    One row per (id_text, word). Dedupe by id_text (keep first), drop null
    transliteration, split by whitespace, explode to one row per word with word_rank.
    """
    trans = trans.dropna(subset=["transliteration"])
    trans = trans.drop_duplicates(subset=["id_text"], keep="first")
    trans = trans[["id_text", "transliteration"]].copy()
    # Split CDLI transliteration into words (space-separated)
    trans["tr_cdli"] = trans["transliteration"].astype(str).str.split()
    trans = trans.explode("tr_cdli", ignore_index=False).reset_index(drop=True)
    trans["word_rank"] = trans.groupby("id_text").cumcount()
    return trans[["id_text", "word_rank", "tr_cdli"]]


def _oracc_words_from_finaldf(final: pd.DataFrame) -> pd.DataFrame:
    """
    One row per (id_text, word). Use 'form' as tr_oracc; preserve id_word and row order
    within each id_text as word order (word_rank).
    """
    final = final.dropna(subset=["form"]).copy()
    final = final[["id_text", "form", "id_word"]].copy()
    final["word_rank"] = final.groupby("id_text").cumcount()
    final = final.rename(columns={"form": "tr_oracc"})
    return final[["id_text", "word_rank", "tr_oracc", "id_word"]]


def build_word_table(db_path: Path | str | None = None) -> None:
    """
    Load transliteration and finaldf from DB, slice transliteration into words,
    align with finaldf words by (id_text, word position), and write table
    word_level with columns: internal_id, id_text, id_word, tr_oracc, tr_cdli.
    """
    db_path = Path(db_path) if db_path else DB_PATH
    if not db_path.exists():
        raise FileNotFoundError(
            f"Database not found: {db_path}. Run load_to_db.py first."
        )

    with sqlite3.connect(db_path) as conn:
        print("Loading transliteration and finaldf...")
        trans = pd.read_sql("SELECT id_text, transliteration FROM transliteration", conn)
        final = pd.read_sql("SELECT id_text, form, id_word FROM finaldf", conn)
        print(f"  Transliteration: {len(trans):,} rows")
        print(f"  Finaldf: {len(final):,} rows")

        print("Slicing CDLI transliteration into words (one per row)...")
        cdli = _cdli_words_from_transliteration(trans)
        print(f"  CDLI word rows: {len(cdli):,}")

        print("Building ORACC word list (form per id_text position)...")
        oracc = _oracc_words_from_finaldf(final)
        print(f"  ORACC word rows: {len(oracc):,}")

        print("Aligning on (id_text, word_rank)...")
        merged = cdli.merge(oracc, on=["id_text", "word_rank"], how="inner")
        merged = merged[["id_text", "id_word", "tr_oracc", "tr_cdli"]]
        print(f"  Aligned word rows: {len(merged):,}")

        print("Assigning internal_id...")
        merged.insert(0, "internal_id", range(1, len(merged) + 1))

        print(f"Writing table '{WORD_LEVEL_TABLE}'...")
        merged.to_sql(WORD_LEVEL_TABLE, conn, if_exists="replace", index=False)
        print(f"Done. Table '{WORD_LEVEL_TABLE}' has columns: {list(merged.columns)}")
        print(f"Saved to {db_path}")


if __name__ == "__main__":
    build_word_table()
