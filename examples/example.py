"""
Example script to demonstrate ORACC to CDLI conversion.

This script demonstrates how to:
1. Load character mappings from the reference CSV.
2. Read an ORACC formatted text file.
3. Convert the lines to CDLI format using utility functions.
4. Save the results to a new file.

Usage:
    python3 examples/example.py
"""

import os
import sys

# Add the project root to sys.path so we can import from src
# This allows running the script from anywhere within the project
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.append(project_root)

from src.utils import convert_line_oracc_to_cdli, load_character_mapping

def main():
    # create paths to files that are used in conversion
    mapping_path = os.path.join(project_root, 'data', 'reference', 'ATF_Character_Conventions.csv')
    input_path = os.path.join(project_root, 'data', 'Q499899-oracc.txt')
    output_path = os.path.join(project_root, 'data', 'Q499899-converted.txt')

    print("--- ORACC to CDLI Conversion Example ---")
    
    # 1. Load the conversion mapping
    print(f"Loading mapping from: {os.path.basename(mapping_path)}")
    mapping = load_character_mapping(mapping_path)
    
    # 2. Read the ORACC lines
    print(f"Reading ORACC file: {os.path.basename(input_path)}")
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            oracc_lines = f.readlines()
    except FileNotFoundError:
        print(f"Error: Could not find {input_path}")
        return

    # 3. Convert lines
    # We use has_label=True because the source file lines start with an ID
    # (e.g., 'P359065:obverse.1.1') followed by the transliterated word.
    print(f"Converting {len(oracc_lines)} lines...")
    converted_lines = [
        convert_line_oracc_to_cdli(line, mapping, has_label=True) 
        for line in oracc_lines
    ]

    # 4. Save the converted text
    print(f"Saving CDLI output to: {os.path.basename(output_path)}")
    with open(output_path, 'w', encoding='utf-8') as f:
        for line in converted_lines:
            f.write(line + '\n')

    print("\nSample Output (ORACC -> CDLI):")
    print("-" * 30)
    for i in range(min(5, len(oracc_lines))):
        original = oracc_lines[i].strip()
        converted = converted_lines[i]
        print(f"ORACC: {original}")
        print(f"CDLI:  {converted}")
        print()

if __name__ == "__main__":
    main()