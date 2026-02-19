"""
Clean CDLI transliteration lines and validate predicted output against a reference file.

Workflow position: Library + CLI. No pipeline order; used after running conversion CLIs
(oracc_to_cdli / cdli_to_oracc) to compare predicted output to a reference CDLI file.

Prerequisites:
  - Two text files (predicted and reference), typically produced by conversion scripts.
  - No DB tables or prior data pipeline steps required.

clean_line_cdli(line): normalise one line to CDLI_clean for comparison.
validate(predicted_lines, actual_lines): compare by line ID; report mismatches and accuracy.
CLI: python -m src.utils.validate <predicted_file> <test_file>.
"""

import argparse
import os
import sys

def clean_line_cdli(line):
    """
    Cleans a line of CDLI formatted transliteration.
    Strips markers like #, [], !, ?, and underscores, and handles determinative notation.
    Target output format is CDLI_clean (matching ORACC conventions).
    """
    line = line.strip()
    if not line:
        return ""
    
    # Expected format: <Header> <Word>
    parts = line.split(' ', 1)
    if len(parts) < 2:
        return line # If no space, return as is (could be nonsense)
    
    header, word = parts[0], parts[1]
    
    # 1. Remove damage/editorial markers
    for char in "#[]!?<>":
        word = word.replace(char, "")
        
    # 2. Remove logogram underscores
    word = word.replace("_", "")
    
    # 3. Handle determinatives: {d} -> d⁼, {ki} -> ⁼ki
    # This aligns CDLI with ORACC-style "clean" output
    word = word.replace("{d}", "d⁼").replace("{ki}", "⁼ki")
    word = word.replace("{", "⁼").replace("}", "")
    
    return f"{header} {word}"

def validate(predicted_lines, actual_lines):
    """
    Compares predicted lines against actual lines by matching headers.
    Reports mismatches with detailed output.
    """
    # creating a map here makes line lookup much faster
    predicted_map = {}
    for line in predicted_lines:
        line = line.strip()
        if not line:
            continue
        parts = line.split(' ', 1)
        if len(parts) == 2:
            predicted_map[parts[0]] = parts[1]
            
    matches = 0
    total = 0
    processed_headers = set()

    print(f"{'Header':<25} | {'Status':<10}")
    print("-" * 40)

    for line in actual_lines:
        line = line.strip()
        if not line:
            continue
            
        cleaned_actual = clean_line_cdli(line)
        parts = cleaned_actual.split(' ', 1)
        if len(parts) < 2:
            continue
            
        header, actual_word = parts[0], parts[1]
        processed_headers.add(header)
        total += 1
        
        if header in predicted_map:
            predicted_word = predicted_map[header]
            if predicted_word == actual_word:
                matches += 1
            else:
                print(f"Mismatch on line {header}: <{predicted_word}> <{actual_word}>")
        else:
            # Predicted file missing this header
            print(f"Mismatch on line {header}: <MISSING> <{actual_word}>")

    # Check for predicted lines that weren't in the actual file
    for header, predicted_word in predicted_map.items():
        if header not in processed_headers:
            print(f"Extra line in predicted {header}: <{predicted_word}> <HIDDEN>")

    if total == 0:
        print("\nResult: No lines found for validation. Ensure files follow the '<ID> <text>' format.")
    else:
        accuracy = (matches / total) * 100
        print(f"\nFinal Accuracy: {accuracy:.2f}% ({matches}/{total} matches)")

def main():
    parser = argparse.ArgumentParser(description="Validate converted ORACC2CDLI files with test CDLI files")
    parser.add_argument('predicted', help="Path to the converted file (Predicted)")
    parser.add_argument('test', help="Path to the test/original CDLI file (Actual)")

    args = parser.parse_args()

    if not os.path.exists(args.predicted):
        print(f"Error: Predicted file not found: {args.predicted}")
        sys.exit(1)
    if not os.path.exists(args.test):
        print(f"Error: Test file not found: {args.test}")
        sys.exit(1)

    try:
        with open(args.predicted, 'r', encoding='utf-8') as f:
            predicted_lines = f.readlines()
        with open(args.test, 'r', encoding='utf-8') as f:
            actual_lines = f.readlines()
    except Exception as e:
        print(f"Error reading files: {e}")
        sys.exit(1)

    validate(predicted_lines, actual_lines)

if __name__ == "__main__":
    main()