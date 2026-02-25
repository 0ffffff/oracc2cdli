============================================================
CHUNKED EDA: word_level_cleaned (CSV)
============================================================
CSV: /Users/williamli/Developer/factgrid/data_harmonization/oracc2cdli/data/word_level_cleaned.csv
Chunk size: 100,000 rows
Processing chunks...
  Chunk 1: 100,000 rows processed so far...
  Chunk 10: 1,000,000 rows processed so far...
  Chunk 20: 2,000,000 rows processed so far...

============================================================
BASIC INFO
============================================================
Total rows: 2,853,522
Columns: 5
Column names: ['internal_id', 'id_text', 'id_word', 'tr_oracc', 'tr_cdli']

============================================================
FIRST 5 ROWS (table layout)
============================================================
   internal_id  id_text      id_word   tr_oracc    tr_cdli
0            1  P362523  P362523.3.1      1(aš)     1(asz)
1            2  P362523  P362523.3.2         še        sze
2            3  P362523  P362523.3.3        gur        gur
3            4  P362523  P362523.4.1         ki         ki
4            5  P362523  P362523.4.2  i₃-kal-la  i3-kal-la

============================================================
DTYPES (from first chunk)
============================================================
internal_id    int64
id_text          str
id_word          str
tr_oracc         str
tr_cdli          str

============================================================
MISSING VALUES (total across all chunks)
============================================================
internal_id    0
id_text        0
id_word        0
tr_oracc       0
tr_cdli        0

As % of rows:
internal_id    0.0
id_text        0.0
id_word        0.0
tr_oracc       0.0
tr_cdli        0.0

============================================================
NUMERIC COLUMNS: min, max, mean, std
============================================================
  internal_id: min=1, max=4546038, mean=2342531.2710, std=1294415.5635, n=2,853,522

============================================================
ID_TEXT: top 15 by row count (words per text)
============================================================
  P108840: 1,630 (0.1%)
  P110592: 1,570 (0.1%)
  P115730: 1,189 (0.0%)
  P110601: 1,136 (0.0%)
  P135735: 1,029 (0.0%)
  P137365: 981 (0.0%)
  P453060: 958 (0.0%)
  P110760: 951 (0.0%)
  P101079: 877 (0.0%)
  P320461: 864 (0.0%)
  P110112: 857 (0.0%)
  P108466: 854 (0.0%)
  P342806: 839 (0.0%)
  P361738: 836 (0.0%)
  P110596: 791 (0.0%)
  Unique id_text values: 92,688

============================================================
ID_WORD (ORACC word-level identifier)
============================================================
  Missing id_word: 0 (0.0%)

============================================================
ORACC vs CDLI MATCH (tr_oracc == tr_cdli)
============================================================
  Rows where tr_oracc == tr_cdli: 840,341 (29.4%)

============================================================
TR_ORACC: character length per word
============================================================
  Mean: 6.5, Std: 3.6, Min: 1, Max: 53, n=2,853,522

============================================================
TR_CDLI: character length per word
============================================================
  Mean: 7.0, Std: 3.9, Min: 1, Max: 57, n=2,853,522


============================================================
COMPARISON: word_level_cleaned vs word_level (uncleaned)
============================================================
(Uncleaned stats from src/eda/results/word_level_eda.md)

  Uncleaned rows:  4,546,052
  Cleaned rows:    2,853,522
  Rows removed:    1,692,530 (37.2%)
  Retention rate:  62.8%

  Unique id_text (uncleaned): 93,209
  Unique id_text (cleaned):   92,688
  Texts lost entirely:        521

  Exact match tr_oracc==tr_cdli (uncleaned): 871,323 (19.2%)
  Exact match tr_oracc==tr_cdli (cleaned):   840,341 (29.4%)
  Change in match rate:                      +10.2 pp

  TR_ORACC length (uncleaned): mean=6.3, std=3.8, min=1, max=58
  TR_ORACC length (cleaned):   mean=6.5, std=3.6, min=1, max=53
  Mean delta:                  +0.2

  TR_CDLI length (uncleaned):  mean=7.0, std=4.0, min=1, max=57
  TR_CDLI length (cleaned):    mean=7.0, std=3.9, min=1, max=57
  Mean delta:                  +0.0

  Top 5 id_text by word count (uncleaned -> cleaned):
    P393743: 3,517 -> 161 (-3,356)
    P200923: 3,249 -> 744 (-2,505)
    P450362: 3,071 -> 368 (-2,703)
    P422273: 3,002 -> 370 (-2,632)
    P131750: 2,915 -> 527 (-2,388)
  
  (Note: this suggests some files were badly aligned from the beginning.)

Done.
