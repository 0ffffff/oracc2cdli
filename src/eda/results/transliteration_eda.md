============================================================
EDA: transliteration.csv
============================================================

============================================================
BASIC INFO
============================================================
Total rows: 132,951
Columns: 2
Column names: ['id_text', 'transliteration']

============================================================
FIRST 5 ROWS
============================================================
   id_text                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       transliteration
0  P496727                                                                                                                                                                                                                                                                                                                                                                                                                                 2(disz) me _udu hi-a_ sza su-ga-gu-ut {disz}me-et-mi-im _lu2_ iu-um-ha-mi-i sza a-di-ni la szu-ud-du-nu _iti_ a-bi-im _u4 2(u) 6(disz)-kam_ _mu_ zi#-im#-ri-li-im ma#-a-su2# u2-bi-bu
1  P353473                                                                                                                                                                                                                               1(disz) me 1(u) _udu hi-a_ sza su-ga-gu-ut a-an!-li-im 1(disz) me _udu-nita2_ sza su-ga-gu-ut la-a-ia-si-im 2(disz) _lu2_ a-bi-na-ka-ar{ki} 1(disz) me _udu hi-a_ sza su-ga-gu-ut i-ba-al-pi2-el3 _lu2_ er-si-ii(IA) 1(disz) me 5(u)# _udu# hi-a_ a-a-nu-um _lu2_ i-ba-al-[a-hi] sza a-di-ni la szu#-ud#-du#-nu _iti_ a-bi-im _u4 2(disz)-kam_ _mu_ zi-im-ri-li#-im# ma#-a-su2 u2-bi-bu
2  P496726  i-na 1(disz) ma-na ku3-babbar_ sza su-ga-gu#-ut# ha-ia3-{d}iszkur _lu2_ sza#-[am-da-di]-im#{ki} _sza3-[ba 1/2(disz) ma-na ku3]-babbar_ te-[er-di]-tum# a-na _[{gi}pisan] lugal#_ _1(disz) tug2 si#?-[sa2? sag?]_ _2(disz) tug2_ [...] ki-ma 5(disz)# [_su ku3-babbar_] te-er-di-tum a-na mu-ka-an-ni-szi-i _1(u) udu-nita2_ ki-ma _1(u) su ku3#-babbar#_ te-er-di-tum i-din-ku-bi [i]-na# ma-ri{ki} _[szu]-nigin2# 2/3(disz) ma#-na# 5(disz) ku3-babbar_ [ma-hi]-ir# [1(u) 5(disz) _su ku3-babbar la2-u_]-su2 [...] [_iti_ ...] [_u4 n-kam_] _mu#_ zi#-im#-ri#-li-[im] _{gesz#}gu-za gal_ a-na {d}[utu] u2-sze-lu-u2
3  P496725                                                                                                                                                                                                                                                                                                                                                                                                                             i-na 1(disz) me _udu hi-a_ sza su-ga-gu-ut ha-ad-ni-{d}iszkur _lu2_ sza-am-du-di-i-im{ki} _2(u) udu hi-a_ ma-hi-ir te-er-di-tum a-na i-din-ku-bi _iti_ {d}nin-bi-ri _u4 2(u) 1(disz)-kam_
4  P496724                                                                                                                                                                                                                             i-na _3(disz) 1/3(disz) ma-na ku3-babbar_ 2(disz) me _udu hi-a_ sza su-ga-gu-ut ha-ad-ni-{d}iszkur _lu2_ sza-am-da-di-i{ki} _[sza3]-ba 3(disz) ma-na ku3-babbar_ u3# 2(u)# _udu# hi#-a#_ [ma]-hi#-ir# _1/3(disz) ma#-na ku3-babbar_ 1(disz) me 1(gesz2) 2(u) _udu hi-a la2-u_-su2 _iti_ {d}nin-bi-ri _u4 1(u) 9(disz)-kam_ _mu_ zi-im-ri-li-im _{gesz}gu-za gal_ a-na {d}utu u2-sze-lu-u2

============================================================
DTYPES
============================================================
id_text            object
transliteration    object

============================================================
MISSING VALUES
============================================================
id_text               0
transliteration    2056

As % of rows:
id_text            0.0
transliteration    1.5

============================================================
ID_TEXT (CDLI text identifiers)
============================================================
Unique IDs: 132,895 / 132,951
Duplicate IDs: 56
Sample duplicated IDs (count):
id_text
P466003    3
P473112    3
P333397    2
P519665    2
P322505    2
Name: count, dtype: int64
IDs matching pattern P<digits>: 132,950 (100.0%)
Sample IDs:
['P496727', 'P353473', 'P496726', 'P496725', 'P496724', 'P496971', 'P496970', 'P496969', 'P496968', 'P496967']

============================================================
WORD COUNTS (space-separated tokens per transliteration)
============================================================
Mean words per text: 51.1
Std: 115.2
Min: 1, Max: 7010
Percentiles: 25%=16, 50%=25, 75%=48

============================================================
SPECIAL NOTATION IN TRANSLITERATIONS
============================================================
Rows with '{': 105,162 (79.1%)
Rows with '_': 21,514 (16.2%)
Rows with '[': 67,796 (51.0%)
Rows with digit+paren e.g. 1(disz): 102,451 (77.1%)

Done.
