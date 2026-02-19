"""
Utilities for CDLI ↔ ORACC transliteration conversion.

Workflow: Library only; no run order. Prerequisites for conversion: data/reference/
ATF_Character_Conventions.csv. Used by CLI (oracc_to_cdli, cdli_to_oracc), examples,
preprocessing (e.g. build_word_table), and tests.

Line-level: load_character_mapping, load_reverse_character_mapping,
convert_line_oracc_to_cdli, convert_line_cdli_to_oracc, validate_conversion.
Word-level: word_oracc_to_cdli, word_cdli_to_oracc. Constants: CDLI_ELLIPSIS, ORACC_ELLIPSIS.
Validation: validate (module with clean_line_cdli and file comparison).
"""

from .utils import (
    load_character_mapping,
    load_reverse_character_mapping,
    convert_line_oracc_to_cdli,
    convert_line_cdli_to_oracc,
    validate_conversion,
)
from .word_conversion import (
    word_oracc_to_cdli,
    word_cdli_to_oracc,
    CDLI_ELLIPSIS,
    ORACC_ELLIPSIS,
)
from . import validate

__all__ = [
    "load_character_mapping",
    "load_reverse_character_mapping",
    "convert_line_oracc_to_cdli",
    "convert_line_cdli_to_oracc",
    "validate_conversion",
    "word_oracc_to_cdli",
    "word_cdli_to_oracc",
    "CDLI_ELLIPSIS",
    "ORACC_ELLIPSIS",
    "validate",
]
