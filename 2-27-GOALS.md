# Next steps for a more robust oracc2cdli dataset

Currently, the process for cleaning involves simply dropping rows (words) that have low similarity, for whatever reason. This could be because `finaldf.csv` and `translitertion.csv` are misaligned in some parts. We aim to align these in a more intelligent manner, maybe looking forward/backward in the `word_level.csv` file and checking for matches.