# Dataset Quality Analysis: Findings, Causes, and Fixes

This document explains the results of the word-level dataset quality analysis (`analyze_dataset_quality.py`), which compares `tr_cdli` and `tr_oracc` in `word_level.csv` by running CDLI↔ORACC conversion and measuring character-level similarity between converted output and the other column.

---

## 1. What the analysis does

- **Input:** `data/word_level.csv` (from `load_to_db` → `build_word_table` → `export_word_level`).
- **Method:** For a sample of rows with both `tr_cdli` and `tr_oracc` non-empty:
  - Convert `tr_cdli` → ORACC and compare to `tr_oracc` (similarity **sim_c2o**).
  - Convert `tr_oracc` → CDLI and compare to `tr_cdli` (similarity **sim_o2c**).
- **Similarity:** Character-level `SequenceMatcher.ratio()` in [0, 1].
- **Classification (per row):**
  - **exact** — Both directions match 100% (converted output equals gold).
  - **high** — Min(sim_c2o, sim_o2c) ≥ 95% (near-perfect; minor normalization).
  - **conversion_issue** — Min similarity in [25%, 95%); same word likely, but conversion or normalization gap.
  - **likely_misaligned** — Min or max similarity &lt; 25%; likely **different words** in the two columns (alignment problem, not conversion).

Thresholds used: `SIM_EXACT=1`, `SIM_HIGH=0.95`, `SIM_LIKELY_MISALIGNED=0.25`, `SIM_VERY_LOW=0.10`.

> **Note (2026-02-24):** The analysis script (`analyze_dataset_quality.py`) still uses `SIM_LIKELY_MISALIGNED=0.25` for classification reporting. The cleaning script (`clean_word_level.py`) has raised its threshold to **0.30** for filtering, meaning rows with similarity in [0.25, 0.30) are now **dropped** during cleaning even though they appear as "conversion_issue" in the analysis output.

---

## 2. Summary of findings (from `analysis_summary.json`)

| Metric | Value |
|--------|--------|
| Rows loaded (with both columns) | 99,992 |
| Sample size | 20,000 |
| **exact** | 11,363 (56.8%) |
| **high** | 89 (0.4%) |
| **conversion_issue** | 3,196 (16%) |
| **likely_misaligned** | 5,352 (26.8%) |
| Mean sim(CDLI→ORACC, tr_oracc) | 0.686 |
| Mean sim(ORACC→CDLI, tr_cdli) | 0.699 |
| sim_c2o &lt; 10% (very low) | 2,648 |
| sim_o2c &lt; 10% (very low) | 2,255 |
| sim_c2o &lt; 25% | 5,134 |
| sim_o2c &lt; 25% | 4,823 |

**Takeaways:**

- **~57% exact:** Conversion is correct and the row is well-aligned for over half the sample.
- **~27% likely misaligned:** In these rows, `tr_cdli` and `tr_oracc` are probably **not** the same word; the pipeline paired them by position, but content suggests alignment noise (e.g. different signs, numbers vs words, determinatives vs lexemes).
- **~16% conversion_issue:** Same word in both columns but conversion or normalization does not fully match (damage/editorial markers, determinatives, numerals, or missing rules).

---

## 3. Category-by-category: causes and fixes

### 3.1 Exact (56.8%)

**What it means:** The row is well-aligned and the current conversion rules correctly map this word pair in both directions.

**Causes:** None; this is the desired outcome.

**Fixes:** None. Use these rows for training/validation and as a baseline when improving conversion or alignment.

---

### 3.2 High (0.4%)

**What it means:** Conversion is almost perfect; small differences (e.g. trailing space, one character variant, or optional normalization like `⁼` vs `{d}`).

**Potential causes:**

- Slight normalization differences between CDLI and ORACC (e.g. determinative representation).
- Optional characters (e.g. primes, spacing) that our converter does not yet normalize.

**Fixes:**

- Optionally add a normalization step before comparison (e.g. collapse `⁼` and `{d}` to a canonical form) so these count as exact.
- If desired, extend conversion to handle the remaining character variants; otherwise treat as acceptable.

---

### 3.3 Conversion issue (16%)

**What it means:** The two columns likely refer to the **same** word, but after converting CDLI→ORACC or ORACC→CDLI, the result does not match the gold column (similarity in the 25–95% range). So the issue is conversion or normalization, not alignment.

**Potential causes:**

1. **Damage/editorial markers**  
   CDLI uses `#`, `[]`, `!`, `?`, `<>`, `x`; ORACC may use different conventions or omit them. Our converter may strip or transform these in a way that doesn’t match the gold.

2. **Determinatives**  
   CDLI `{d}`, `{ki}`, `{x}` vs ORACC `⁼`. Mismatch in how we map or normalize these.

3. **Numerals and measure notation**  
   Different representation of numbers (e.g. `2(u)`, `1(disz)`, `1(barig)`, `3(iku)`). Gold may use one convention, our output another.

4. **Logograms vs phonetic**  
   One column may have a logogram (e.g. `GAN2`), the other a phonetic or numeric form (e.g. `3(iku)`); conversion does not translate between these.

5. **Abbreviations and special tokens**  
   Short forms (`ki`, `mu`, `lugal`) that are ambiguous or context-dependent; wrong expansion or no expansion.

6. **Character mapping gaps**  
   A character or digraph in the reference CSV is missing or wrong, so one direction converts incorrectly.

7. **Case or punctuation**  
   Uppercase/lowercase or punctuation differences (e.g. `($` vs normal form) that we don’t normalize.

**Example patterns from the analysis:**

- `[1(barig)]-ta` vs `1(barig)-ta` — bracketed/damage vs clean; conversion may drop or keep brackets differently.
- `<a-sza3>` vs `a-ša₃` — angle brackets (restoration?) vs plain; normalization or mapping gap.
- `kiszib3` (CDLI) vs `ki` (ORACC) — possible alignment error (different words) or abbreviation; if same word, conversion/expansion needed.
- `lugal` vs `mu` — likely **misalignment** (different words) that fell just above the 25% threshold; re-check threshold or add rules.

**Fixes:**

- **Damage/editorial:** Define a single “comparison normal form” (e.g. strip `#[]!?<>` and optionally `x`) and apply it to both gold and converted output before similarity; optionally extend conversion to emit the same convention as the gold.
- **Determinatives:** Unify `{d}`, `{ki}`, `⁼` in a canonical form for evaluation; ensure conversion and gold use the same convention in the pipeline.
- **Numerals/measures:** Add or adjust rules for `(disz)`, `(u)`, `(barig)`, `(iku)`, etc., so that converted output matches the gold convention (or normalize both to one convention for comparison).
- **Logograms vs phonetic:** Document that we do not convert between logogram and number/measure; optionally flag such pairs and exclude from conversion evaluation or add a separate “same meaning” check.
- **Character mapping:** Audit `data/reference/ATF_Character_Conventions.csv` and conversion code for missing or incorrect entries; add tests for the failing examples.
- **Case/punctuation:** Normalize case and known punctuation (e.g. `($`) before comparison, or extend conversion to match gold.

---

### 3.4 Likely misaligned (26.8%)

**What it means:** After conversion, similarity is very low (often &lt; 25%) in at least one direction. So the two columns are likely **different words** that ended up in the same row because of how the word-level table was built (position-based alignment of transliteration line vs finaldf `form`).

**Potential causes:**

1. **Position mismatch**  
   Transliteration is split by spaces; finaldf `form` is one row per word. If line segmentation or tokenization differs (e.g. compound signs, numbers with spaces, or line breaks), word rank in the line does not match word rank in finaldf, so we pair CDLI word *i* with ORACC word *j* (i ≠ j).

2. **Different segmentation**  
   One source uses more or fewer tokens for the same phrase (e.g. “one” as one token vs “1” and “(diš)” as two). So one column has a single word and the other has something from a different position.

3. **Missing or extra words**  
   One side has a word that the other omits (or vice versa), shifting all following alignments.

4. **Line-level vs word-level mismatch**  
   `transliteration` is line-level CDLI; we split by space. If the line does not exactly match the sequence of `form` in finaldf (e.g. due to different normalization or merging of lines), alignment by position is wrong.

5. **Id_text boundary issues**  
   Deduplication or filtering by `id_text` might keep one representative line per text, but finaldf might have more or fewer words for that text, so aligning by rank within `id_text` can still be off.

**Example patterns from the analysis:**

- `gin2` vs `2(u)` — number vs sign name; clearly different.
- `sila3` vs `gur` — different measure/word.
- `szu` vs `nin-en-nu` — different words.
- `ur-an-si4-an-na` vs `AB` — long form vs abbreviation.
- `($` vs `gub-ba` — garbage or control token vs word.
- `{d}nin-mar{ki}-ta` vs `sanga` — different words.

**Fixes:**

- **Improve alignment:** Do not rely only on position (word_rank). Options:
  - Use a proper aligner (e.g. dynamic programming, or a model) to match CDLI and ORACC token sequences by content or by embedding similarity.
  - Or restrict to rows where conversion similarity is above a high threshold (e.g. exact or high) and treat the rest as “unreliable alignment” for training.
- **Filter the dataset:** For conversion evaluation or training, **exclude** rows classified as `likely_misaligned` (e.g. sim &lt; 0.25) so that metrics and models are not biased by wrong pairs.
- **Flag for review:** Export `likely_misaligned` rows (e.g. with `id_text`, `word_rank`, `tr_cdli`, `tr_oracc`) for manual inspection and, if needed, correction of the alignment step in `build_word_table.py`.
- **Segment both sides consistently:** If possible, align on a common tokenization (e.g. same splitting rules for numerals and compounds) before building the word-level table.
- **Document limitation:** State in the README or pipeline docs that ~27% of word-level rows may be position-aligned but not content-equivalent, and that conversion accuracy on the full table is therefore an upper bound; report metrics also on “exact + high” or “sim ≥ 0.95” subsets.

---

## 4. Very low similarity (&lt; 10%)

About 2,600–2,650 rows have similarity below 10% in one direction. These are almost certainly **misaligned** (different words) or **garbage** (e.g. `($`). Treat them as non-comparable for conversion quality; exclude from conversion accuracy and consider excluding from training.

---

## 5. Recommended next steps

1. **Conversion quality**
   - Focus on the **conversion_issue** examples: add normalization or conversion rules for damage markers, determinatives, numerals, and character mapping.
   - Re-run the analysis and conversion tests after each change to track improvement.

2. **Alignment quality**
   - Treat **likely_misaligned** as an alignment problem, not a conversion problem.
   - Optionally implement a better alignment (e.g. similarity-based or sequence alignment) in `build_word_table.py`, or add a post-step that flags/low-weights low-similarity pairs.
   - Export and review a sample of misaligned rows by `id_text` to see if the pattern is per-text (e.g. one text has many wrong alignments).

3. **Reporting**
   - Report conversion accuracy on **aligned-only** subsets (e.g. exclude sim &lt; 0.25, or only exact+high+conversion_issue).
   - Keep `analysis_summary.json` and this findings document under version control or in CI so regressions are visible.

4. **Pipeline**
   - Ensure `analyze_dataset_quality.py` is run after `export_word_level.py` when you need up-to-date quality metrics; document this in the workflow (e.g. in README or SUGGESTED_MODIFICATIONS).

---

## 6. References

- **Analysis script:** `src/preprocessing/analyze_dataset_quality.py`
- **Input data:** `data/word_level.csv` (from `load_to_db` → `build_word_table` → `export_word_level`)
- **Results:** `src/preprocessing/dataset_quality_results/analysis_summary.json`
- **Conversion:** `src/utils/word_conversion.py` (word-level); `src/utils/utils.py` (line-level)
- **Cleaning:** `src/preprocessing/clean_word_level.py` (full dataset); `src/preprocessing/clean_word_level_subset.py` (benchmark subset)
- **Cleaning filter analysis:** `src/preprocessing/dataset_quality_results/cleaning_filter_analysis.md`

---

## 7. Performance notes (2026-02-24)

The cleaning pipeline (`clean_word_level.py`) was optimized for the full 4.5M-row dataset:

- Character mappings in `word_conversion.py` are now loaded from CSV **once** and cached at module level (previously re-read on every word conversion call).
- `_apply_mapping()` uses a single-pass compiled regex instead of N iterative `str.replace()` loops.
- The `ProcessPoolExecutor` is created once and reused across all chunks (previously re-created per chunk).
- Redundant `.strip()` calls and per-row `$` checks were removed from the classification hot path; these are now handled once in vectorized chunk preprocessing.
- The misaligned threshold (`SIM_LIKELY_MISALIGNED`) was raised from 0.25 to **0.30**.

Benchmark: 10,000 rows in 1.4s classification time (1.8s total). Estimated full-dataset time: ~10-14 minutes.
