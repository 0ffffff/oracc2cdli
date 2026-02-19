============================================================
CHUNKED EDA: finaldf.csv
============================================================
Chunk size: 100,000 rows
Processing chunks...
  Chunk 1: 100,000 rows processed so far...
  Chunk 10: 1,000,000 rows processed so far...
  Chunk 20: 2,000,000 rows processed so far...
  Chunk 30: 3,000,000 rows processed so far...
  Chunk 40: 4,000,000 rows processed so far...
  Chunk 50: 5,000,000 rows processed so far...
  Chunk 60: 6,000,000 rows processed so far...
  Chunk 70: 7,000,000 rows processed so far...

============================================================
BASIC INFO
============================================================
Total rows: 7,271,149
Columns: 24
Column names: ['Unnamed: 0', 'lang', 'form', 'id_word', 'label', 'id_text', 'delim', 'gdl', 'pos', 'cf', 'gw', 'sense', 'norm', 'epos', 'headform', 'contrefs', 'norm0', 'base', 'morph', 'stem', 'cont', 'syntax_ub-after', 'morph2', 'aform']

============================================================
FIRST 5 ROWS
============================================================
   Unnamed: 0 lang     form      id_word label  id_text  delim  gdl  pos   cf   gw sense norm epos headform contrefs  norm0  base  morph  stem  cont  syntax_ub-after  morph2  aform
0           0  arc     mmxx  P522613.2.1   o 1  P522613    NaN  NaN  NaN  NaN  NaN   NaN  NaN  NaN      NaN      NaN    NaN   NaN    NaN   NaN   NaN              NaN     NaN    NaN
1           1  arc        t  P522613.2.2   o 1  P522613    NaN  NaN  NaN  NaN  NaN   NaN  NaN  NaN      NaN      NaN    NaN   NaN    NaN   NaN   NaN              NaN     NaN    NaN
2           2  arc     rmyt  P522613.2.3   o 1  P522613    NaN  NaN  NaN  NaN  NaN   NaN  NaN  NaN      NaN      NaN    NaN   NaN    NaN   NaN   NaN              NaN     NaN    NaN
3           3  arc     wsqn  P522613.3.1   o 2  P522613    NaN  NaN  NaN  NaN  NaN   NaN  NaN  NaN      NaN      NaN    NaN   NaN    NaN   NaN   NaN              NaN     NaN    NaN
4           4  arc  šʾymr/d  P522613.3.2   o 2  P522613    NaN  NaN  NaN  NaN  NaN   NaN  NaN  NaN      NaN      NaN    NaN   NaN    NaN   NaN   NaN              NaN     NaN    NaN

============================================================
DTYPES (from first chunk)
============================================================
Unnamed: 0           int64
lang                object
form                object
id_word             object
label               object
id_text             object
delim              float64
gdl                 object
pos                 object
cf                  object
gw                  object
sense               object
norm                object
epos                object
headform            object
contrefs            object
norm0              float64
base               float64
morph              float64
stem               float64
cont               float64
syntax_ub-after    float64
morph2             float64
aform              float64

============================================================
MISSING VALUES (total across all chunks)
============================================================
Unnamed: 0               0
lang                     0
form                  1104
id_word                  0
label                    0
id_text                  0
delim              7271149
gdl                  56441
pos                 905881
cf                 2819694
gw                 2819694
sense              2822609
norm               6085369
epos               2822609
headform           7270071
contrefs           7270071
norm0              4001078
base               3969738
morph              3968269
stem               7270899
cont               7152610
syntax_ub-after    7270649
morph2             7243039
aform              7249204

As % of rows:
Unnamed: 0           0.0
lang                 0.0
form                 0.0
id_word              0.0
label                0.0
id_text              0.0
delim              100.0
gdl                  0.8
pos                 12.5
cf                  38.8
gw                  38.8
sense               38.8
norm                83.7
epos                38.8
headform           100.0
contrefs           100.0
norm0               55.0
base                54.6
morph               54.6
stem               100.0
cont                98.4
syntax_ub-after    100.0
morph2              99.6
aform               99.7

============================================================
NUMERIC COLUMNS: min, max, mean, std
============================================================
  Unnamed: 0: min=0, max=7286183, mean=3636854.2601, std=2100540.5032, n=7,271,149

============================================================
VALUE COUNTS (top 15 per column)
============================================================

  lang:
    sux: 4,973,398 (68.4%)
    akk: 885,597 (12.2%)
    akk-x-neoass: 406,788 (5.6%)
    akk-x-stdbab: 240,509 (3.3%)
    akk-x-neobab: 194,623 (2.7%)
    akk-x-ltebab: 140,446 (1.9%)
    akk-x-midass: 139,218 (1.9%)
    akk-x-mbperi: 82,794 (1.1%)
    akk-949: 52,913 (0.7%)
    akk-x-oldbab: 51,009 (0.7%)
    sux-x-emesal: 34,434 (0.5%)
    xur: 22,573 (0.3%)
    qpc: 20,015 (0.3%)
    peo: 7,758 (0.1%)
    xur-946: 3,986 (0.1%)

  pos:
    N: 2,619,566 (36.0%)
    n: 1,210,312 (16.6%)
    __NA__: 905,881 (12.5%)
    u: 604,244 (8.3%)
    PN: 520,740 (7.2%)
    V/i: 242,856 (3.3%)
    V/t: 206,045 (2.8%)
    V: 137,439 (1.9%)
    PRP: 121,331 (1.7%)
    DN: 98,107 (1.3%)
    SN: 91,295 (1.3%)
    X: 87,627 (1.2%)
    AJ: 67,364 (0.9%)
    MN: 61,987 (0.9%)
    DET: 40,788 (0.6%)

  delim:
    __NA__: 7,271,149 (100.0%)

  epos:
    __NA__: 2,822,609 (38.8%)
    N: 2,617,523 (36.0%)
    PN: 517,009 (7.1%)
    V/i: 228,663 (3.1%)
    V/t: 204,144 (2.8%)
    PRP: 125,233 (1.7%)
    V: 122,171 (1.7%)
    DN: 97,423 (1.3%)
    SN: 91,924 (1.3%)
    MN: 61,874 (0.9%)
    AJ: 59,821 (0.8%)
    DET: 40,489 (0.6%)
    CNJ: 35,888 (0.5%)
    RN: 34,348 (0.5%)
    O: 33,421 (0.5%)

Done.
