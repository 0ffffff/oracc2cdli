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

Performance notes (2026-02-24):
  - Character mappings are loaded from CSV once and cached at module level.
  - _apply_mapping uses a single-pass compiled regex instead of N×str.replace loops.
  - The subscript-digit regex is pre-compiled.
  - word_cdli_to_oracc pre-computes its non-digit sub-mapping and caches the regex.
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

# Pre-built str.translate table: ASCII digit -> Unicode subscript digit.
_DIGIT_TO_SUBSCRIPT_TABLE = str.maketrans("0123456789", _SUBSCRIPT_DIGITS)


def _digits_to_subscript(s: str) -> str:
    """Convert a string of ASCII digits to Unicode subscript digits (e.g. '10' -> '₁₀')."""
    return s.translate(_DIGIT_TO_SUBSCRIPT_TABLE)


# -----------------------------------------------------------------------------
# Character mapping – loaded once and cached at module level
# -----------------------------------------------------------------------------

_CACHED_ORACC_TO_CDLI: dict[str, str] | None = None
_CACHED_CDLI_TO_ORACC: dict[str, str] | None = None


def _get_oracc_to_cdli_mapping(csv_path: Optional[str] = None) -> dict[str, str]:
    """Return ORACC -> CDLI character mapping (cached after first load)."""
    global _CACHED_ORACC_TO_CDLI
    if csv_path is not None:
        # Explicit path: always load fresh (rare / test use).
        from .utils import load_character_mapping
        return load_character_mapping(csv_path)
    if _CACHED_ORACC_TO_CDLI is None:
        from .utils import load_character_mapping
        _CACHED_ORACC_TO_CDLI = load_character_mapping()
    return _CACHED_ORACC_TO_CDLI


def _get_cdli_to_oracc_mapping(csv_path: Optional[str] = None) -> dict[str, str]:
    """Return CDLI -> ORACC character mapping (cached after first load)."""
    global _CACHED_CDLI_TO_ORACC
    if csv_path is not None:
        from .utils import load_reverse_character_mapping
        return load_reverse_character_mapping(csv_path)
    if _CACHED_CDLI_TO_ORACC is None:
        from .utils import load_reverse_character_mapping
        _CACHED_CDLI_TO_ORACC = load_reverse_character_mapping()
    return _CACHED_CDLI_TO_ORACC


# -----------------------------------------------------------------------------
# Single-pass regex replacement (replaces old N×str.replace loop)
# -----------------------------------------------------------------------------

# Cache: mapping id → (compiled_pattern, lookup_dict)
_REGEX_CACHE: dict[int, tuple[re.Pattern, dict[str, str]]] = {}


def _build_replacement_regex(mapping: dict[str, str]) -> tuple[re.Pattern, dict[str, str]]:
    """Build a compiled regex that matches any mapping key, longest-first."""
    keys = sorted(mapping.keys(), key=len, reverse=True)
    pattern = re.compile("|".join(re.escape(k) for k in keys))
    return pattern, mapping


def _apply_mapping(
    word: str,
    mapping: dict[str, str],
    *,
    sort_keys_by_length_desc: bool = True,  # kept for API compat; ignored (regex always longest-first)
) -> str:
    """
    Replace each key in *mapping* with its value in *word* using a single-pass
    compiled regex.  The regex is built once per unique mapping dict (keyed by
    ``id(mapping)``) and cached for the lifetime of the process.

    Keys are matched longest-first so that multi-char sequences like 'disz' or
    'sz' are consumed before shorter overlapping keys like 's'.
    """
    if not word or not mapping:
        return word
    cache_key = id(mapping)
    if cache_key not in _REGEX_CACHE:
        _REGEX_CACHE[cache_key] = _build_replacement_regex(mapping)
    pattern, lookup = _REGEX_CACHE[cache_key]
    return pattern.sub(lambda m: lookup[m.group()], word)


# -----------------------------------------------------------------------------
# Pre-compiled subscript-digit regex
# -----------------------------------------------------------------------------

_SUBSCRIPT_RE = re.compile(r"([a-zA-Z,'])(\d+)")


def _cdli_digits_to_oracc_subscripts(word: str) -> str:
    """
    Convert CDLI ASCII digits to ORACC subscripts only when they are part of a sign.

    In ATF, subscript numerals denote sign indices (e.g. du₁₀, i₃, gin₂). Plain
    numerals denote quantities (e.g. 1(asz) = one unit, 2(u) = two). So we replace
    a run of digits with subscripts only when it immediately follows a letter or
    sign-internal character (e.g. comma in s,). Regex: ([a-zA-Z,'])(\\d+) matches
    (letter/sign)(digit run); we replace the digit run with subscript form.
    """
    return _SUBSCRIPT_RE.sub(
        lambda m: m.group(1) + m.group(2).translate(_DIGIT_TO_SUBSCRIPT_TABLE),
        word,
    )


# -----------------------------------------------------------------------------
# Normalization helpers (determinatives, ellipsis, underscores)
# -----------------------------------------------------------------------------

_DETERMINATIVE_RE = re.compile(r"\{([^}]*)\}")


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
    word = _DETERMINATIVE_RE.sub(r"⁼\1", word)
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
# Pre-computed non-digit sub-mapping for word_cdli_to_oracc
# (avoids rebuilding the dict-comprehension on every call)
# -----------------------------------------------------------------------------

_CACHED_CDLI_TO_ORACC_NO_DIGITS: dict[str, str] | None = None


def _get_cdli_to_oracc_no_digits() -> dict[str, str]:
    """Return the CDLI->ORACC mapping with single-digit keys removed (cached)."""
    global _CACHED_CDLI_TO_ORACC_NO_DIGITS
    if _CACHED_CDLI_TO_ORACC_NO_DIGITS is None:
        full = _get_cdli_to_oracc_mapping()
        _CACHED_CDLI_TO_ORACC_NO_DIGITS = {
            k: v for k, v in full.items() if not (len(k) == 1 and k.isdigit())
        }
    return _CACHED_CDLI_TO_ORACC_NO_DIGITS


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

    if strip_underscores:
        word = word.replace("_", "")

    if normalize_determinatives:
        word = _normalize_determinatives_cdli_to_oracc(word)

    if normalize_ellipsis:
        word = _normalize_ellipsis_to_oracc(word)

    # Use caller-supplied mapping or the cached non-digit sub-mapping.
    if mapping is not None:
        non_digit_mapping = {k: v for k, v in mapping.items() if not (len(k) == 1 and k.isdigit())}
    else:
        non_digit_mapping = _get_cdli_to_oracc_no_digits()

    word = _apply_mapping(word, non_digit_mapping)

    # Convert digits to subscripts only when part of a sign (e.g. i3 -> i₃, du10 -> du₁₀).
    word = _cdli_digits_to_oracc_subscripts(word)

    return word
