# Changelog

## 2025-10-02 - Text-to-Speech Chunking Improvements

### Fixed
- **Single-letter abbreviation handling**: Fixed `_is_sentence_boundary()` function in `lib/text_to_speech.py` to correctly handle single-letter abbreviations followed by space + uppercase letter (e.g., "Donald J. Trump" no longer chunks at "J.")
  - Added check for streaming case where "J. T" arrives before "Trump"
  - Prevents incorrect chunking at middle initials in names

### Cleaned Up
- Removed debug print statements from `test_chunking.py`
- Removed temporary debugging documentation files:
  - `CHUNKING_BUG_ANALYSIS.md`
  - `DEBUGGING_DECIMALS.md`

### Test Results
✅ "The current U.S. president is Donald J. Trump. He was elected in 2016."
  - Correctly chunks into 2 sentences (not 3)
  
✅ "Dr. Smith said the result is 3.14 exactly."
  - Correctly keeps as single chunk (doesn't split at decimal)

### Implementation Details
The fix adds a check in the single-letter abbreviation logic (lines 188-190):
```python
# Check if it's space + uppercase (streaming case: "J. T" when "Trump" hasn't arrived yet)
if after and len(after) >= 2 and after[0].isspace() and after[1].isupper():
    return False
```

This ensures that when streaming text character-by-character, patterns like "J. T" are recognized as part of a name, not a sentence boundary.
