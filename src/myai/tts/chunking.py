"""Text chunk-boundary heuristics for streaming TTS."""

from __future__ import annotations

import re


def is_sentence_boundary(text: str, position: int) -> bool:
    """Check whether punctuation at position is a true sentence boundary."""
    if position < 0 or position >= len(text):
        return False

    before = text[:position]
    after = text[position + 1:] if position + 1 < len(text) else ""

    # Decimal handling: avoid splitting "3.14" and streaming "3." then "14"
    if position > 0 and text[position - 1].isdigit():
        if after and after[0].isdigit():
            return False
        if re.match(r"^\s*\d", after):
            return False
        if not after:
            return False

    # Initials such as "J. T" should stay connected.
    if position > 0 and text[position - 1].isupper() and text[position - 1].isalpha():
        if position == 1 or not text[position - 2].isalnum():
            if after and after[0].isupper():
                return False
            if after and len(after) >= 2 and after[0].isspace() and after[1].isupper():
                return False
            if not after or after.isspace():
                return False

    if not after:
        return True

    text_with_period = text[:position + 1]
    common_abbrevs = [
        r"\bDr\.$", r"\bMr\.$", r"\bMrs\.$", r"\bMs\.$",
        r"\bJr\.$", r"\bSr\.$", r"\bProf\.$", r"\bGen\.$",
        r"\bCol\.$", r"\bCapt\.$", r"\bLt\.$", r"\bSgt\.$",
        r"\bRev\.$", r"\bHon\.$", r"\bSt\.$", r"\bAve\.$",
        r"\bDept\.$", r"\bUniv\.$", r"\bInc\.$", r"\bLtd\.$",
        r"\bCo\.$", r"\bCorp\.$", r"\betc\.$", r"\bvs\.$",
        r"\be\.g\.$", r"\bi\.e\.$", r"\bviz\.$", r"\bal\.$",
        r"\bU\.S\.$", r"\bU\.K\.$", r"\bD\.C\.$",
    ]
    for abbrev_pattern in common_abbrevs:
        if re.search(abbrev_pattern, text_with_period, re.IGNORECASE):
            return False

    if re.match(r"^(\s+)([a-z])", after):
        return False

    if before.endswith("..") or after.startswith(".."):
        return False

    if after and (after[0].isupper() or (after[0] == " " and len(after) > 1 and after[1].isupper())):
        return True

    return bool(re.match(r"^\s+[A-Z]", after))


def is_weak_comma(text: str, position: int) -> bool:
    """Return True for commas that should not trigger chunking."""
    before = text[:position].strip().lower()
    after = text[position + 1:].strip()

    if after and re.match(r"^\s*\d", after):
        return True

    if position == 0 or (position > 0 and text[position - 1] == ","):
        return True

    before_words = before.split()
    if before_words:
        last_word = before_words[-1].lower()
        if last_word in ["and", "but", "or", "so", "yet", "nor"]:
            return True

    after_words = after.split()
    if after_words:
        first_word = after_words[0]
        if first_word[0].isupper() or first_word.lower() in ["sir", "ma'am", "miss", "mr", "mrs", "ms", "dr"]:
            return True

    prev_comma = text[:position].rfind(",")
    if prev_comma == -1:
        prev_comma = 0
    phrase_length = position - prev_comma
    if phrase_length < 15:
        return True

    return False


def find_sentence_boundary(text: str, chunk_chars: str = ".!?", first_only: bool = False) -> int:
    """Find a valid boundary index in text, or -1 if none found.

    When *first_only* is True the first valid boundary is returned (useful for
    fast-start chunking).  Otherwise the last valid boundary is returned
    (maximises chunk length for better prosody).

    >>> text = "Hello world. Another sentence!"
    >>> find_sentence_boundary(text)
    29
    >>> find_sentence_boundary(text, first_only=True)
    11

    Decimals should not be split at the period:

    >>> find_sentence_boundary("The value is 3.14 and rising.")
    28
    >>> find_sentence_boundary("Version 2.0")
    -1

    Initials / abbreviations stay connected:

    >>> find_sentence_boundary("Meet J. T. Smith.")
    16
    >>> find_sentence_boundary("Meet J. T. Smith.", first_only=True)
    16

    When commas are enabled, weak commas are skipped:

    >>> find_sentence_boundary("Count 1, 2, 3", chunk_chars=",")
    -1
    """
    last_valid_boundary = -1

    for i, char in enumerate(text):
        if char not in chunk_chars:
            continue

        valid = False
        if char == ".":
            if is_sentence_boundary(text, i):
                valid = True
        elif char == ",":
            if not is_weak_comma(text, i):
                valid = True
        elif char == "—":
            if i > 0 and (i + 1 >= len(text) or text[i + 1] != "—"):
                valid = True
        else:
            if i > 0 and text[i - 1] in "!?":
                continue
            valid = True

        if valid:
            if first_only:
                return i
            last_valid_boundary = i

    return last_valid_boundary
