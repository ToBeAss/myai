# Problem Statement: Text-to-Speech Streaming Chunking Logic Bug

## Context
I have a Google Cloud Text-to-Speech system that streams LLM responses. It needs to intelligently detect sentence boundaries to chunk text for speech synthesis. The system should NOT chunk at abbreviations like "J." in names or decimals like "3.14".

## Current Behavior (WRONG ❌)
```
Input: "The current U.S. president is Donald J. Trump. He was elected in 2016."

Actual chunks:
1. "The current U.S. president is Donald J."  (WRONG - chunks at "J.")
2. "Trump. He was elected in 2016."

Input: "Dr. Smith said the result is 3.14 exactly."

Actual chunks:
1. "Dr. Smith said the result is 3.14 exactly."  (CORRECT after fix ✅)
```

## Desired Behavior (CORRECT ✅)
```
Input: "The current U.S. president is Donald J. Trump. He was elected in 2016."

Expected chunks:
1. "The current U.S. president is Donald J. Trump."
2. "He was elected in 2016."
```

## Key Debug Finding
When buffer = `"The current U.S. president is Donald J. T"` (streaming character-by-character):
- Position 38 is the period in "J."
- `after = " T"` (space + T, NOT empty)
- Current code at line 185 checks: `if after and after[0].isupper()`
- `" T"[0]` is a space, not uppercase, so this check FAILS
- Current code at line 189 checks: `if not after or after.isspace()`
- `" T".isspace()` returns `False` because "T" is not whitespace
- Therefore the check FAILS and continues to line 193 onward
- Line 234-235 then returns `True` because `after[0]` is space and `after[1]` is uppercase "T"

## The Root Cause
The single-letter abbreviation check (lines 180-191) should return `False` when:
- We have a single uppercase letter before the period (like "J.")
- Followed by space + uppercase letter (like " T")

But currently:
- Line 185 checks `if after and after[0].isupper()` → Fails because `after[0]` is a space
- Line 189 checks `if not after or after.isspace()` → Fails because `" T"` is not pure whitespace

Neither check catches the case of " T" (space before the uppercase).

## Files and Functions Involved

**File:** `/Users/tobiasmolland/GitHub/myai/lib/text_to_speech.py`

**Function:** `_is_sentence_boundary(self, text: str, position: int) -> bool` (lines 147-239)

This function checks if a period at a given position is a true sentence boundary. It needs to correctly identify that "J." followed by " T" (or " Trump") is NOT a sentence boundary, it's a middle initial.

**Key logic section** (lines 180-191):
```python
# Check for common abbreviations (single letter + period)
# e.g., "J.", "M.", etc. - check character BEFORE the period
if position > 0 and text[position - 1].isupper() and text[position - 1].isalpha():
    # Check if there's a word boundary before the letter (space or start of string)
    if position == 1 or not text[position - 2].isalnum():
        # Check if next character is uppercase (likely part of name like "J. Trump")
        if after and after[0].isupper():
            return False
        # In streaming, we might get "J." with nothing after yet
        # If after is empty or only whitespace, be cautious - don't chunk yet
        if not after or after.isspace():
            return False
```

## The Fix Needed
Lines 185-191 should detect that " T" (space + uppercase) means we're in the middle of a name. The check needs to handle:
1. Empty after: `""` → False (don't chunk yet, more text coming)
2. Pure whitespace: `"   "` → False (don't chunk yet)
3. **Space + uppercase letter**: `" T"` or `" Trump"` → False (it's a name like "J. Trump")
4. Space + lowercase: `" said"` → True (likely a sentence boundary)

**Suggested fix:** Check if `after` starts with whitespace followed by an uppercase letter, which indicates the abbreviation is part of a name.

Replace lines 185-191 with:
```python
        # Check if next character is uppercase (likely part of name like "J. Trump")
        if after and after[0].isupper():
            return False
        # Check if it's space + uppercase (streaming case: "J. T" when "Trump" hasn't arrived yet)
        if after and len(after) >= 2 and after[0].isspace() and after[1].isupper():
            return False
        # In streaming, we might get "J." with nothing after yet
        # If after is empty or only whitespace, be cautious - don't chunk yet
        if not after or after.isspace():
            return False
```

## Test Cases to Verify
1. ✅ `"Dr. Smith said the result is 3.14 exactly."` → Should be 1 chunk (WORKS NOW)
2. ❌ `"The current U.S. president is Donald J. Trump."` → Should be 1 chunk (FAILS - chunks at "J.")
3. Should also handle: `"J. K. Rowling wrote Harry Potter."` → 1 chunk, not split at "J." or "K."

## Testing Command
```bash
cd /Users/tobiasmolland/GitHub/myai
source venv/bin/activate
python test_chunking.py "The current U.S. president is Donald J. Trump. He was elected in 2016."
```

Expected output after fix:
```
Total chunks: 2

Chunk 1 (47 chars):
  'The current U.S. president is Donald J. Trump.'

Chunk 2 (30 chars):
  'He was elected in 2016.'
```
