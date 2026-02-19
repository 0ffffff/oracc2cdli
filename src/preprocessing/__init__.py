"""
Preprocessing: load CSVs into SQLite and build word-level tables.

Workflow order (for building data/oracc2cdli.db and data/word_level.csv):
  1. load_to_db.py       — Requires: transliteration.csv, finaldf.csv → DB with tables transliteration, finaldf
  2. build_word_table.py — Requires: DB from (1) → adds table word_level
  3. export_word_level.py — Requires: DB with word_level from (2) → data/word_level.csv

Legacy: preprocess_old.py (run after load_to_db; writes table merged; superseded by build_word_table).
"""
