# Dataset quality analysis

Character-level similarity after CDLI↔ORACC conversion.

## Summary

- **Rows loaded** (with both columns non-empty): 99,992
- **Sample size**: 20,000

## Classification (min similarity in both directions)

| Label | Count | % |
|-------|-------|---|
| exact | 11,363 | 56.8% |
| high | 89 | 0.4% |
| conversion_issue | 3,196 | 16.0% |
| likely_misaligned | 5,352 | 26.8% |

## Mean character similarity (converted vs gold)

- CDLI→ORACC vs tr_oracc: **0.6864**
- ORACC→CDLI vs tr_cdli: **0.6994**

## Likely misaligned (similarity below threshold)

- sim(CDLI→ORACC, tr_oracc) < 10%: 2,648
- sim(ORACC→CDLI, tr_cdli) < 10%: 2,255
- sim(CDLI→ORACC, tr_oracc) < 25%: 5,134
- sim(ORACC→CDLI, tr_cdli) < 25%: 4,823
