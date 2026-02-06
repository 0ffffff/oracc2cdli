# ORACC2CDLI

A tool to convert ORACC transliteration to CDLI transliteration formats, under the FactGrid Cuneiform system.
Achieves 99.96% accuracy on oldassyrian-lines.csv dataset

Current progress: can convert ORACC to CDLI_clean, likely impossible to fully convert to CDLI. This is partly due to the physical damage markers and editorial corrections.
TODO: refactor code, make it more user-friendly

To see an example usage without args: examples/example.py

Before using the cli tool, check out data/Q499899-*.txt for examples of how the input files should be formatted.

To use the cli tool:

### ORACC to CDLI
```bash
python3 src/oracc_to_cdli.py convert <input_file> <output_file> [--has-label]
```

### CDLI to ORACC (Reverse)
```bash
python3 src/cdli_to_oracc.py convert <input_file> <output_file> [--has-label]
```

### Cleaning Files
```bash
python3 src/oracc_to_cdli.py clean <input_file> <output_file>
```
or
```bash
python3 src/cdli_to_oracc.py clean <input_file> <output_file>
```

To validate results against a test file that's already written in CDLI format:
```bash
python3 src/validate.py <predicted_file> <test_file>
```