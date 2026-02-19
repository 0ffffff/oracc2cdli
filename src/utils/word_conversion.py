"""
Atomic word-level conversion between CDLI and ORACC transliteration formats.

Workflow position: Library module. No pipeline order; used by code that needs per-word
conversion (e.g. build_word_table could use it; tests in src/tests compare against
word_level.csv produced by the preprocessing pipeline).

Prerequisites:
  - data/reference/ATF_Character_Conventions.csv (loaded via utils.load_character_mapping
    / load_reverse_character_mapping). No DB or prior scripts required.

CDLI (Canonical ATF) uses ASCII-only: subscript digits as 0-9, sz/s,/t,/h,/j for
special consonants, disz for diš. ORACC (Extended ATF) uses Unicode: ₀-₉, š, ṣ, ṭ, ḫ, ŋ, diš.
Determinatives: CDLI uses {d}, {ki}, {x}; ORACC may use ⁼. Ellipsis: CDLI ... ; ORACC ….

Converts a single word at a time. For line-level conversion use utils.py.
"""

from __future__ import annotations

import re
from typing import Optional

# -----------------------------------------------------------------------------
# Constants (from ATF documentation and plan)
# -----------------------------------------------------------------------------

# Ellipsis: CDLI uses three ASCII dots; ORACC uses Unicode horizontal ellipsis.
CDLI_ELLIPSIS = "..."
ORACC_ELLIPSIS = "\u2026"  # …

# Determinative markers: CDLI {d} -> d⁼, {ki} -> ⁼ki; generic {x} -> ⁼x, } removed.
DETERMINATIVE_D_PREFIX = "{d}"
DETERMINATIVE_KI_SUFFIX = "{ki}"

# Subscript numerals (Unicode) for sign indices: 0->₀, 1->₁, ...
_SUBSCRIPT_DIGITS = "\u2080\u2081\u2082\u2083\u2084\u2085\u2086\u2087\u2088\u2089"


def _digits_to_subscript(s: str) -> str:
    """Convert a string of ASCII digits to Unicode subscript digits (e.g. '10' -> '₁₀')."""
    return "".join(_SUBSCRIPT_DIGITS[int(c)] for c in s if c.isdigit())


# -----------------------------------------------------------------------------
# Character mapping (delegate to utils to avoid duplicating CSV path logic)
# -----------------------------------------------------------------------------

def _get_oracc_to_cdli_mapping(csv_path: Optional[str] = None):
    """Load ORACC -> CDLI character mapping from reference CSV."""
    from .utils import load_character_mapping
    return load_character_mapping(csv_path) if csv_path else load_character_mapping()


def _get_cdli_to_oracc_mapping(csv_path: Optional[str] = None):
    """Load CDLI -> ORACC character mapping from reference CSV."""
    from .utils import load_reverse_character_mapping
    return load_reverse_character_mapping(csv_path) if csv_path else load_reverse_character_mapping()


def _apply_mapping(
    word: str,
    mapping: dict[str, str],
    *,
    sort_keys_by_length_desc: bool = True,
) -> str:
    """
    Replace each key in mapping with its value in the string.

    Keys are applied in descending length order so that longer sequences
    are replaced first (e.g. 'disz' before 's', and 's,' before 's').
    This avoids shorter tokens incorrectly consuming parts of multi-char
    signs (e.g. 'sz' vs 's').
    """
    if not word or not mapping:
        return word
    keys = sorted(mapping.keys(), key=len, reverse=True) if sort_keys_by_length_desc else mapping.keys()
    result = word
    for key in keys:
        result = result.replace(key, mapping[key])
    return result


def _cdli_digits_to_oracc_subscripts(word: str) -> str:
    """
    Convert CDLI ASCII digits to ORACC subscripts only when they are part of a sign.

    In ATF, subscript numerals denote sign indices (e.g. du₁₀, i₃, gin₂). Plain
    numerals denote quantities (e.g. 1(asz) = one unit, 2(u) = two). So we replace
    a run of digits with subscripts only when it immediately follows a letter or
    sign-internal character (e.g. comma in s,). Regex: ([a-zA-Z,'])(\\d+) matches
    (letter/sign)(digit run); we replace the digit run with subscript form.
    """
    # Match one or more sign-name chars (letter or comma) then one or more digits.
    return re.sub(
        r"([a-zA-Z,'])(\d+)",
        lambda m: m.group(1) + _digits_to_subscript(m.group(2)),
        word,
    )


# -----------------------------------------------------------------------------
# Normalization helpers (determinatives, ellipsis, underscores)
# -----------------------------------------------------------------------------

def _normalize_determinatives_cdli_to_oracc(word: str) -> str:
    """
    Convert CDLI determinative notation to ORACC-style ⁼ notation.

    - {d} -> d⁼ (divine determinative before the sign)
    - {ki} -> ⁼ki (place determinative after the sign)
    - Any other {x} -> ⁼x (generic: replace { with ⁼, remove })
    Leaves compound determinatives like {+lum} unchanged except for the braces.
    """
    if "{" not in word:
        return word
    # Apply conventional forms first so they are not double-processed.
    word = word.replace(DETERMINATIVE_D_PREFIX, "d⁼")
    word = word.replace(DETERMINATIVE_KI_SUFFIX, "⁼ki")
    # Generic: {foo} -> ⁼foo (replace opening brace with ⁼, remove closing brace).
    # Regex: \{ matches literal '{', ([^}]*) captures non-'}' chars, \} matches '}'.
    word = re.sub(r"\{([^}]*)\}", r"⁼\1", word)
    return word


def _normalize_ellipsis_to_oracc(word: str) -> str:
    """Replace CDLI ellipsis (...) with ORACC ellipsis (…)."""
    if CDLI_ELLIPSIS not in word:
        return word
    return word.replace(CDLI_ELLIPSIS, ORACC_ELLIPSIS)


def _normalize_ellipsis_to_cdli(word: str) -> str:
    """Replace ORACC ellipsis (…) with CDLI ellipsis (...)."""
    if ORACC_ELLIPSIS not in word:
        return word
    return word.replace(ORACC_ELLIPSIS, CDLI_ELLIPSIS)


# -----------------------------------------------------------------------------
# Public API: single-word conversion
# -----------------------------------------------------------------------------

def word_oracc_to_cdli(
    word: str,
    *,
    mapping: Optional[dict[str, str]] = None,
    normalize_ellipsis: bool = True,
) -> str:
    """
    Convert a single word from ORACC format to CDLI format.

    - Replaces Unicode subscript digits (₀-₉) with ASCII (0-9).
    - Replaces š, ṣ, ṭ, ḫ, ŋ, ʾ, etc. with their CDLI ASCII equivalents (sz, s,, t,, h,, j, ').
    - Replaces diš with disz.
    - If normalize_ellipsis is True (default), replaces ORACC ellipsis (…) with (...).

    Parameters
    ----------
    word : str
        A single transliteration word in ORACC (Unicode) format.
    mapping : dict, optional
        ORACC -> CDLI character map. If None, loaded from ATF_Character_Conventions.csv.
    normalize_ellipsis : bool
        If True, convert … to ...

    Returns
    -------
    str
        The word in CDLI (ASCII) format.

    Examples
    --------
    >>> word_oracc_to_cdli("i₃-kal-la")
    'i3-kal-la'
    >>> word_oracc_to_cdli("1(diš)")
    '1(disz)'
    """
    if word is None:
        return ""
    if not isinstance(word, str):
        return str(word)
    word = word.strip()
    if not word:
        return word

    if mapping is None:
        mapping = _get_oracc_to_cdli_mapping()

    if normalize_ellipsis:
        word = _normalize_ellipsis_to_cdli(word)

    return _apply_mapping(word, mapping)


def word_cdli_to_oracc(
    word: str,
    *,
    mapping: Optional[dict[str, str]] = None,
    normalize_ellipsis: bool = True,
    normalize_determinatives: bool = False,
    strip_underscores: bool = False,
) -> str:
    """
    Convert a single word from CDLI format to ORACC format.

    - Replaces ASCII subscript digits (0-9) with Unicode (₀-₉).
    - Replaces sz, s,, t,, h,, j, etc. with š, ṣ, ṭ, ḫ, ŋ.
    - Replaces disz with diš.
    - If normalize_ellipsis is True (default), replaces (...) with ….
    - If normalize_determinatives is True, converts {d} -> d⁼, {ki} -> ⁼ki, {x} -> ⁼x.
    - If strip_underscores is True, removes logogram underscores (_).

    Parameters
    ----------
    word : str
        A single transliteration word in CDLI (ASCII) format.
    mapping : dict, optional
        CDLI -> ORACC character map. If None, loaded from ATF_Character_Conventions.csv.
    normalize_ellipsis : bool
        If True, convert ... to …
    normalize_determinatives : bool
        If True, convert {d}/{ki}/{x} to ⁼ notation.
    strip_underscores : bool
        If True, remove '_' (logogram markers).

    Returns
    -------
    str
        The word in ORACC (Unicode) format.

    Examples
    --------
    >>> word_cdli_to_oracc("i3-kal-la")
    'i₃-kal-la'
    >>> word_cdli_to_oracc("1(disz)")
    '1(diš)'
    """
    if word is None:
        return ""
    if not isinstance(word, str):
        return str(word)
    word = word.strip()
    if not word:
        return word

    if mapping is None:
        mapping = _get_cdli_to_oracc_mapping()

    if strip_underscores:
        word = word.replace("_", "")

    if normalize_determinatives:
        word = _normalize_determinatives_cdli_to_oracc(word)

    if normalize_ellipsis:
        word = _normalize_ellipsis_to_oracc(word)

    # Apply non-digit mappings first (disz, sz, s,, t,, h,, j, s', ', x, X).
    # Exclude single digits 0-9 so numerals like 1(asz) stay as "1", not "₁".
    non_digit_mapping = {k: v for k, v in mapping.items() if not (len(k) == 1 and k.isdigit())}
    word = _apply_mapping(word, non_digit_mapping)

    # Convert digits to subscripts only when part of a sign (e.g. i3 -> i₃, du10 -> du₁₀).
    word = _cdli_digits_to_oracc_subscripts(word)

    return word
