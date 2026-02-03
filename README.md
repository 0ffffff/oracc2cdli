# ORACC2CDLI

A tool to convert ORACC transliteration to CDLI transliteration formats.
Achieves 99.96% accuracy on oldassyrian-lines.csv dataset

Current progress: can convert ORACC to CDLI_clean, likely impossible to fully convert to CDLI. This is partly due to the physical damage markers and editorial corrections.
TODO: refactor code, make it more user-friendly

To see an example usage without args: examples/example.py

To use the cli tool:
```bash
python3 src/oracc_to_cdli.py <input_file> <output_file> [--has-label]
```

To validate results against a test file that's already written in CDLI format:
```bash
python3 src/validate.py <predicted_file> <test_file>
```