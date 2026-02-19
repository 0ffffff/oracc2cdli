"""
Character mapping and line-level conversion between ORACC and CDLI transliteration.

Workflow position: Library module. No pipeline order; used by CLI (oracc_to_cdli, cdli_to_oracc),
examples, and any script that needs line-level conversion.

Prerequisites:
  - data/reference/ATF_Character_Conventions.csv (or pass csv_path to load_*_mapping).
  - No prior scripts or DB tables required.

Provides: load_character_mapping, load_reverse_character_mapping; convert_line_oracc_to_cdli,
convert_line_cdli_to_oracc; validate_conversion (accuracy vs a DataFrame column).
For single-word (atomic) conversion use word_conversion.py.
"""

import os
import re
import pandas as pd

# Default path to ATF character conventions, resolved relative to project root.
# __file__ is src/utils/utils.py -> go up to src, then to project root.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_DEFAULT_MAPPING_PATH = os.path.join(_PROJECT_ROOT, "data", "reference", "ATF_Character_Conventions.csv")


def load_character_mapping(csv_path=None):
    """Load the mapping from the reference CSV (ORACC -> CDLI)."""
    path = csv_path if csv_path is not None else _DEFAULT_MAPPING_PATH
    try:
        df = pd.read_csv(path)
        mapping = {}
        for _, row in df.iterrows():
            oracc_char = row['ASCII-ATF'] # e.g. 'š'
            cdli_char = row['Unicode-ATF'] # e.g. 'sz'
            if pd.notna(oracc_char) and pd.notna(cdli_char):
                mapping[str(oracc_char)] = str(cdli_char)
        return mapping
    except Exception as e:
        print(f"Error loading mapping: {e}")
        # Fallback basic mapping. This should never happen
        return {
            'š': 'sz', 'ṣ': 's,', 'ṭ': 't,', 'ḫ': 'h', 'ŋ': 'j',
            '₀': '0', '₁': '1', '₂': '2', '₃': '3', '₄': '4',
            '₅': '5', '₆': '6', '₇': '7', '₈': '8', '₉': '9'
        }

def convert_line_oracc_to_cdli(line, mapping=None, has_label=False):
    """
    Convert a single line from ORACC format to CDLI format.
    Example: P359065:obverse.1.3 qi₂-bi-ma -> P359065:obverse.1.3 qi2-bi-ma
    If has_label=False, it converts the string directly.
    """
    if mapping is None:
        mapping = load_character_mapping()

    if not line or not isinstance(line, str):
        return line

    if has_label:
        parts = line.strip().split(' ', 1)
        if len(parts) < 2:
            label = ""
            word = parts[0]
        else:
            label = parts[0]
            word = parts[1]
    else:
        label = ""
        word = line.strip()
    
    word = word.replace('…', '...')
    
    for oracc_char in sorted(mapping.keys(), key=len, reverse=True):
        word = word.replace(oracc_char, mapping[oracc_char])
    
    if label:
        return f'{label} {word}'
    return word

def load_reverse_character_mapping(csv_path=None):
    """Load the mapping from the reference CSV for CDLI -> ORACC conversion."""
    path = csv_path if csv_path is not None else _DEFAULT_MAPPING_PATH
    try:
        df = pd.read_csv(path)
        mapping = {}
        for _, row in df.iterrows():
            oracc_char = row['ASCII-ATF'] # e.g. 'š'
            cdli_char = row['Unicode-ATF'] # e.g. 'sz'
            if pd.notna(oracc_char) and pd.notna(cdli_char):
                # Reverse direction: CDLI val -> ORACC val
                mapping[str(cdli_char)] = str(oracc_char)
        return mapping
    except Exception as e:
        print(f"Error loading reverse mapping: {e}")
        return {
            'sz': 'š', 's,': 'ṣ', 't,': 'ṭ', 'h': 'ḫ', 'j': 'ŋ'
        }

def convert_line_cdli_to_oracc(line, mapping=None, has_label=False):
    """
    Convert a single line from CDLI format to ORACC format.
    """
    if mapping is None:
        mapping = load_reverse_character_mapping()

    if not line or not isinstance(line, str):
        return line

    if has_label:
        parts = line.strip().split(' ', 1)
        if len(parts) < 2:
            label = ""
            word = parts[0]
        else:
            label = parts[0]
            word = parts[1]
    else:
        label = ""
        word = line.strip()
    
    # Sort by length descending to replace "sz" before "s", etc.
    for cdli_char in sorted(mapping.keys(), key=len, reverse=True):
        word = word.replace(cdli_char, mapping[cdli_char])
    
    if label:
        return f'{label} {word}'
    return word

def validate_conversion(df, conversion_col='ORACC', target_col='CDLI_clean'):
    """
    Test the accuracy of the conversion against a target column.
    Only compatible with csv files--to test conversion of FactGrid-like formatted cuneiform texts (e.g. https://database.factgrid.de/wiki/ORACC-W-Q499899), use validate.py
    """
    mapping = load_character_mapping()
    
    results = []
    for _, row in df.iterrows():
        input_text = row[conversion_col]
        target_text = row[target_col]
        
        if pd.isna(input_text) or pd.isna(target_text):
            continue
            
        converted = convert_line_oracc_to_cdli(input_text, mapping, has_label=False)
        is_match = converted == target_text
        results.append(is_match)
        
    accuracy = sum(results) / len(results) if results else 0
    return accuracy, results