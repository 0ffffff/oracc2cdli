# How Clearly Mismatched Rows Passed the Cleaning Filter

## Example rows

From `word_level_cleaned_subset.csv`:

| internal_id | id_text  | tr_oracc (ORACC)   | tr_cdli (CDLI)      |
|-------------|----------|--------------------|---------------------|
| 2002        | P414628  | babbar-ra          | siskur2-re          |
| 2005        | P414628  | dumu               | dumu]-er-s,e-tim    |

These are different words (or one is a prefix of a damaged form) but were **kept** as "conversion_issue" instead of dropped as "likely_misaligned".

---

## Filter logic (recap)

> **Updated 2026-02-24:** The misaligned threshold was raised from 0.25 to **0.30** (recommendation #2 below). The garbage-token `$` check and redundant `.strip()` calls were moved to vectorized chunk preprocessing; `_classify_pair` no longer re-checks these. The `ProcessPoolExecutor` is now created once and reused across all chunks. Character mappings in `word_conversion.py` are cached at module level after first load. See the "Performance optimizations" section in the project README for the full list.

- **Drop** when `_classify_row` returns label `"likely_misaligned"`.
- `"likely_misaligned"` when: `sim_min < 0.30` **or** `sim_max < 0.30`.
- **Early exit:** If `sim_c2o < 0.30` we return `"likely_misaligned"` and never compute the second conversion/similarity.
- Similarity is `Levenshtein.normalized_similarity(a, b)` via rapidfuzz (equivalent to `1 - lev / max(len(a), len(b))`).

So a row is **kept** only if **both** directions have similarity **>= 0.30** (and it's not exact/high, so it's classified as conversion_issue).

---

## Why these rows passed (at the original 0.25 threshold)

The analysis below was written against the original threshold of 0.25. With the threshold raised to 0.30, both example rows below are now **dropped** as likely_misaligned. The analysis is preserved for reference.

### 1. Threshold boundary: **>= 0.25 is kept**

We use **strict** `< 0.25` to drop. So:

- **sim = 0.25** -> we do **not** drop; we classify as conversion_issue and **keep**.
- Any pair that lands exactly on 0.25 will therefore pass.

**Example: `dumu` vs `dumu]-er-s,e-tim`**

- One string is a 4-character prefix of the other.
- Levenshtein from `"dumu"` to `"dumu]-er-s,e-tim"` is the cost of inserting the rest -> 12 edits; `max_len = 16`.
- Similarity = `1 - 12/16 = 0.25` **exactly**.
- So `sim_c2o` or `sim_o2c` can be **exactly 0.25**. Then:
  - Early exit does not trigger (`0.25` is not `< 0.25`).
  - Final label is not `"likely_misaligned"` because neither `sim_min` nor `sim_max` is `< 0.25`.
- Result: row is **kept** as conversion_issue.

So: **boundary at 0.25** (and any similarity slightly above it) allows clearly mismatched pairs where one side is a short prefix of the other.

---

### 2. Accidental character overlap: **short shared substrings**

When the two words are different but share a few characters (e.g. same suffix or a couple of letters), Levenshtein can stay low enough that similarity rises **above** 0.25.

**Example: `babbar-ra` vs `siskur2-re`**

- Different words, but both end in `-re` and contain `r` and `-`.
- Shared parts reduce edit distance (e.g. a short "re" or "-" match in the diff).
- So Levenshtein can be, say, 7-8 instead of 9-10 -> similarity in the **0.2-0.4** range.
- If similarity is **>= 0.25** (e.g. 0.26-0.35):
  - Early exit does not trigger.
  - We do the second conversion/similarity; both can still be >= 0.25.
  - We then classify as **conversion_issue** and **keep** the row.

So: **different words with modest character overlap** (e.g. common suffix `-re`) can get similarity just above the drop threshold and slip through.

---

## Root causes (summary)

| Cause | Effect |
|-------|--------|
| **Strict `< 0.25`** | sim **= 0.25** is kept; prefix/short-vs-long pairs land exactly on the boundary. |
| **Low bar (0.25)** | Pairs with limited overlap (e.g. shared `-re`, `r`) can reach 0.26-0.35 and be kept. |
| **Levenshtein normalization** | `1 - lev / max(len(a), len(b))` can give relatively high scores when one string is much shorter or when a short substring matches. |

So rows that are clearly mismatched (different words or one word vs. a long damaged form) can still get **sim >= 0.25** and pass the filter.

---

## Recommended changes

1. **~~Drop when similarity <= 0.25~~** *(done 2026-02-24)*
   ~~Use `sim_min <= SIM_LIKELY_MISALIGNED` (and same for early exit) so that **0.25 is dropped**, not kept.~~
   The threshold was raised to **0.30**, which subsumes this change.

2. **~~Raise the "misaligned" threshold~~** *(done 2026-02-24)*
   ~~Use a higher bar, e.g. **0.30 or 0.35**.~~
   `SIM_LIKELY_MISALIGNED` is now **0.30** in `clean_word_level.py`.

3. **Add a length-ratio guard**
   If `min(len(tr_cdli), len(tr_oracc)) / max(...) < 0.5` (or similar), treat as misaligned and drop without running conversion/similarity. That would catch short-vs-long pairs (e.g. `dumu` vs `dumu]-er-s,e-tim`) even when similarity is exactly 0.30.

4. **Revisit "conversion_issue" band**
   Optionally require conversion_issue to have **sim_min >= 0.35** (or 0.4) so that only clearly related pairs (damage/normalization issues) are kept; everything in 0.30-0.35 would be dropped as likely misaligned.
