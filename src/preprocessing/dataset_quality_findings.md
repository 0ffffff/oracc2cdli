# Word-level dataset quality: findings and recommendations

This document summarizes an analysis of `data/word_level.csv` to separate **misalignment** (wrong word pairs in the same row) from **conversion failures** (our CDLI↔ORACC conversion producing a different string than the gold). It recommends changes to build a more reliable dataset.

---

## 1. Method

- **Data:** Rows from `word_level.csv` with non-empty `tr_cdli` and `tr_oracc` (first ~100k rows loaded, then 20,000 randomly sampled).
- **For each row:**
  1. Convert `tr_cdli` → ORACC using our word converter; compare to `tr_oracc` with **character-level similarity** (`difflib.SequenceMatcher.ratio`).
  2. Convert `tr_oracc` → CDLI; compare to `tr_cdli` with the same similarity measure.
- **Interpretation:**
  - If similarity is **0% or very low** (< 10–25%), the two strings are almost certainly **different words** (misalignment), not the same word in two scripts.
  - If similarity is **high but not exact** (e.g. 80–99%), the pair may be correct but our conversion or normalization differs (e.g. brackets, damage markers).
  - **Exact match** (100%) after conversion indicates a correct pair and a correct conversion.

**Thresholds used:**

| Label                | Condition (min of both directions) |
|----------------------|-------------------------------------|
| `exact`              | similarity = 1.0                    |
| `high`               | similarity ≥ 0.95                   |
| `conversion_issue`   | 0.25 ≤ similarity < 0.95             |
| `likely_misaligned`  | similarity < 0.25                    |

---

## 2. Findings (sample of 20,000 rows)

| Classification        | Count  | %     | Interpretation |
|-----------------------|--------|-------|----------------|
| **exact**             | 11,363 | 56.8% | Same word in both columns; conversion matches gold. |
| **high**              | 89     | 0.4%  | Near-exact; minor normalization differences. |
| **conversion_issue**  | 3,196  | 16.0% | Mix: some real conversion gaps (e.g. brackets), many borderline misalignments. |
| **likely_misaligned** | 5,352  | 26.8% | Different words in the two columns; row alignment is wrong. |

- **Mean character similarity** (converted vs gold): ~69% (CDLI→ORACC vs `tr_oracc`) and ~70% (ORACC→CDLI vs `tr_cdli`). The large share of misaligned pairs pulls this down.
- **Very low similarity (likely wrong pair):**
  - `sim(CDLI→ORACC, tr_oracc) < 10%`: 2,648 rows (~13%)
  - `sim(ORACC→CDLI, tr_cdli) < 10%`: 2,255 rows (~11%)
  - Below 25%: ~5,134 and ~4,823 respectively.

So roughly **one quarter to one third** of rows in the sample are likely **misaligned** (different words), not conversion errors. That explains why “accuracy vs dataset” in the conversion tests is low (e.g. ~60%) even when the conversion logic is correct.

---

## 3. Example rows

### 3.1 Likely misaligned (different words)

These pairs have low or zero character similarity after conversion; the two columns clearly refer to different words:

| tr_cdli              | tr_oracc     | sim_c2o | sim_o2c | Note |
|----------------------|-------------|---------|---------|------|
| gin2                 | 2(u)        | 0.00    | 0.25    | Number vs sign name |
| sila3                | gur         | 0.00    | 0.00    | Different signs |
| szu                  | nin-en-nu   | 0.18    | 0.17    | Different words |
| ur-an-si4-an-na       | AB          | 0.00    | 0.00    | Logogram vs spelling |
| gesz                 | zu₂-lum-bi  | 0.00    | 0.14    | Different words |
| ba-an-ti              | giri₃       | 0.15    | 0.15    | Different words |
| GAN2                 | 3(iku)      | 0.00    | 0.00    | Different words |
| sze-ba               | ki          | 0.00    | 0.00    | Different words |
| {d}nin-mar{ki}-ta    | sanga       | 0.18    | 0.18    | Different words |

### 3.2 Exact (correct pair and conversion)

| tr_cdli              | tr_oracc              |
|----------------------|------------------------|
| lu2-{d}nin-szubur    | lu₂-{d}nin-šubur      |
| ki-masz{ki}          | ki-maš{ki}            |
| ba-a-hun             | ba-a-hun              |
| dub-sar              | dub-sar               |

### 3.3 Conversion / normalization issues (same word, different representation)

Here the pair is often the same word, but our converter does not normalize brackets or editorial markup, so similarity is high but not 100%:

| tr_cdli        | tr_oracc   | pred_oracc   | pred_cdli   | Note |
|----------------|------------|--------------|-------------|------|
| [1(barig)]-ta  | 1(barig)-ta | [1(barig)]-ta | 1(barig)-ta | Restoration brackets preserved |
| <a-sza3>       | a-ša₃     | <a-ša₃>     | a-sza3     | Editorial brackets preserved |
| [a2-bi]        | a₂-bi     | [a₂-bi]     | a2-bi      | Same |

Some “conversion_issue” rows are actually misaligned (e.g. lugal vs mu, ur-e2-ninnu vs ugula); the 0.25 threshold puts them in the middle bucket.

---

## 4. Root cause of misalignment

The word-level table is built in `build_word_table.py` by:

1. Splitting **transliteration** (CDLI full line) into words by whitespace and assigning **word_rank** (0, 1, 2, …).
2. Taking **finaldf** (ORACC) and assigning **word_rank** by row order per `id_text`.
3. **Merging** on `(id_text, word_rank)`.

Misalignment arises when:

- **CDLI and ORACC segment or count words differently** (e.g. different tokenization, or one source has an extra/missing token), so the same logical position has different words.
- **Row order in finaldf** does not match word order in the CDLI transliteration (e.g. different ordering of words, or finaldf is not strictly one row per word in the same order as the line).
- **Duplicate or missing words** in one source shift subsequent word_rank, so all following pairs are wrong.

So the pipeline assumes a **strict 1:1 positional correspondence** between “word N in CDLI line” and “row N in ORACC for that id_text,” which often does not hold.

---

## 5. Recommendations for a more reliable dataset

### 5.1 Filter the current table by similarity

- Run the same character-similarity analysis (or a fast approximation) on the full CSV.
- **Keep only rows** where, after conversion, similarity in both directions is above a threshold (e.g. ≥ 0.95 or 1.0). Use this as a **clean word-level dataset** for training or evaluation.
- Optionally tag rows with similarity scores and export a “quality” column for downstream use.

### 5.2 Validate alignment at build time

- In `build_word_table.py`, after merging on `(id_text, word_rank)`:
  - Run CDLI→ORACC and ORACC→CDLI on each pair and compute character similarity.
  - **Drop or flag** rows with similarity below a chosen threshold (e.g. 0.5 or 0.25).
- This yields a smaller but **aligned** word-level table and avoids persisting obvious mismatches.

### 5.3 Improve alignment instead of relying only on rank

- **Tokenize both sides** in a consistent way (e.g. same splitting rules, normalizations) before assigning rank, so “word 3” means the same thing in both sources.
- If ORACC provides **word indices or offsets**, use them instead of row order.
- If possible, **align by content** (e.g. edit distance or conversion-based similarity) within each `id_text` and then assign pairs, instead of assuming rank equality.

### 5.4 Separate “same word” from “same form”

- Our converter does not strip restoration `[]`, editorial `<>`, or damage `#`. For **evaluation**, either:
  - Normalize both sides (e.g. strip these markers) before comparison, or
  - Add an optional “clean” mode in the converter and compare in that mode.
- Keep raw forms in the dataset for research, but mark or separate “normalized” pairs for conversion accuracy metrics.

### 5.5 Document and version the pipeline

- Record how the word-level table was built (script version, thresholds, filters).
- Store a **small set of hand-verified (id_text, word_rank) or (tr_cdli, tr_oracc) pairs** and use them as a regression set for both dataset building and conversion.

---

## 6. How to reproduce

From the project root:

```bash
python3 src/preprocessing/analyze_dataset_quality.py
```

This loads a subset of `data/word_level.csv`, samples 20,000 rows, runs conversion and similarity, and writes:

- `src/preprocessing/dataset_quality_results/analysis_summary.json`

The numbers and examples in this document come from that run (same thresholds and sampling).
