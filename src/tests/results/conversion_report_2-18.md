# Word conversion test report

From `word_level.csv` dataset Feb. 18th version

## Unit tests (empty, None, malformed, edge cases)

- **empty**: 2/2 passed
- **none**: 2/2 passed
- **malformed**: 4/4 passed
- **edge_cdli_to_oracc**: 10/10 passed
- **edge_oracc_to_cdli**: 10/10 passed

## Dataset tests (word_level.csv)

- Total rows: 5,000
- Rows with both tr_cdli and tr_oracc: 5,000

### CDLI → ORACC (vs dataset)
- Passed: 2,990, Failed: 2,010, Skipped: 0
- Accuracy (of compared): 59.80%

Sample failures (first 50):
1. row_id=23 input='ma-n' expected='ma-na' actual='ma-n'
2. row_id=31 input='szu!?-bu-lum' expected='šu-bu-lum' actual='šu!?-bu-lum'
3. row_id=143 input='u4-kur2-sze3' expected='u₄' actual='u₄-kur₂-še₃'
4. row_id=144 input='u4' expected='kur₂-še₃' actual='u₄'
5. row_id=145 input='nu-me-a-ak' expected='u₄' actual='nu-me-a-ak'
6. row_id=146 input='ri-im-{d}suen' expected='nu-me-a-ak' actual='ri-im-{d}suen'
7. row_id=147 input='e2-mu' expected='ri-im-{d}suen' actual='e₂-mu'
8. row_id=148 input='nu-ub-be2-a' expected='e₂-mu' actual='nu-ub-be₂-a'
9. row_id=149 input='mu' expected='nu-ub-be₂-a' actual='mu'
10. row_id=150 input='{d}nanna' expected='mu' actual='{d}nanna'
11. row_id=151 input='{d}utu' expected='{d}nanna' actual='{d}utu'
12. row_id=152 input='u2' expected='{d}utu' actual='u₂'
13. row_id=153 input='su2-mu-dingir' expected='u₂' actual='su₂-mu-dingir'
14. row_id=154 input='in-pa3' expected='su₂-mu-dingir' actual='in-pa₃'
15. row_id=155 input='tukum-bi' expected='in-pa₃' actual='tukum-bi'
16. row_id=156 input='e2-mu' expected='tukum-bi' actual='e₂-mu'
17. row_id=157 input='na-ab-be2-a' expected='e₂-mu' actual='na-ab-be₂-a'
18. row_id=158 input='1/3(disz)' expected='na-ab-be₂-a' actual='1/3(diš)'
19. row_id=159 input='ma-na' expected='1/3(diš)' actual='ma-na'
20. row_id=160 input='ku3-babbar' expected='ma-na' actual='ku₃-babbar'

### ORACC → CDLI (vs dataset)
- Passed: 3,058, Failed: 1,942, Skipped: 0
- Accuracy (of compared): 61.16%

Sample failures (first 50):
1. row_id=23 input='ma-na' expected='ma-n' actual='ma-na'
2. row_id=31 input='šu-bu-lum' expected='szu!?-bu-lum' actual='szu-bu-lum'
3. row_id=143 input='u₄' expected='u4-kur2-sze3' actual='u4'
4. row_id=144 input='kur₂-še₃' expected='u4' actual='kur2-sze3'
5. row_id=145 input='u₄' expected='nu-me-a-ak' actual='u4'
6. row_id=146 input='nu-me-a-ak' expected='ri-im-{d}suen' actual='nu-me-a-ak'
7. row_id=147 input='ri-im-{d}suen' expected='e2-mu' actual='ri-im-{d}suen'
8. row_id=148 input='e₂-mu' expected='nu-ub-be2-a' actual='e2-mu'
9. row_id=149 input='nu-ub-be₂-a' expected='mu' actual='nu-ub-be2-a'
10. row_id=150 input='mu' expected='{d}nanna' actual='mu'
11. row_id=151 input='{d}nanna' expected='{d}utu' actual='{d}nanna'
12. row_id=152 input='{d}utu' expected='u2' actual='{d}utu'
13. row_id=153 input='u₂' expected='su2-mu-dingir' actual='u2'
14. row_id=154 input='su₂-mu-dingir' expected='in-pa3' actual='su2-mu-dingir'
15. row_id=155 input='in-pa₃' expected='tukum-bi' actual='in-pa3'
16. row_id=156 input='tukum-bi' expected='e2-mu' actual='tukum-bi'
17. row_id=157 input='e₂-mu' expected='na-ab-be2-a' actual='e2-mu'
18. row_id=158 input='na-ab-be₂-a' expected='1/3(disz)' actual='na-ab-be2-a'
19. row_id=159 input='1/3(diš)' expected='ma-na' actual='1/3(disz)'
20. row_id=160 input='ma-na' expected='ku3-babbar' actual='ma-na'

### Round-trip CDLI → ORACC → CDLI (sample)
- Passed: 490, Failed: 10

### Round-trip ORACC → CDLI → ORACC (sample)
- Passed: 484, Failed: 16
