# 🧠 Smart Sentence Boundary Detection

## The Problem

When streaming TTS, we need to detect sentence boundaries to know when to start speaking. A naive approach of simply splitting on periods (`.`) causes issues with:

- **Abbreviations**: "Dr. Smith" or "U.S. President"
- **Titles**: "Mr. Johnson" or "Mrs. Davis"
- **Initials**: "John F. Kennedy" or "Donald J. Trump"
- **Numbers**: "3.14 is pi" or "Version 2.0"
- **Acronyms**: "e.g.", "i.e.", "etc."

## The Solution

The TTS system now uses **smart sentence boundary detection** that distinguishes between:
- ✅ **Real sentence endings**: "The president is Donald J. Trump. He was elected in 2016."
- ❌ **Abbreviations**: "The president is Donald J. Trump" (doesn't break here!)

## How It Works

### Detection Rules

The system checks multiple conditions before treating a period as a sentence boundary:

#### 1️⃣ Single Letter Abbreviations
```
"Donald J. Trump" ← Period after "J." is NOT a sentence boundary
"He won. John" ← Period after "won" IS a sentence boundary
```

**Rule**: If a single capital letter is followed by a period and then another capital letter, it's likely a middle initial.

#### 2️⃣ Common Titles and Abbreviations
```
Detected: Dr., Mr., Mrs., Ms., Jr., Sr., Prof., Gen., Col., 
          Capt., Lt., Sgt., Rev., Hon., St., Ave., Dept.,
          Univ., Inc., Ltd., Co., Corp., etc., vs., 
          e.g., i.e., viz., al.
```

**Examples**:
- "Dr. Smith arrived" ← No break after "Dr."
- "The company is Apple Inc. today" ← No break after "Inc."
- "He likes apples, e.g. Fuji" ← No break after "e.g."

#### 3️⃣ Decimal Numbers
```
"The value is 3.14 exactly" ← Period in "3.14" is NOT a boundary
```

**Rule**: If digits come before and after the period, it's a decimal number.

#### 4️⃣ Lowercase Continuation
```
"He said i.e. meaning" ← Period followed by lowercase suggests continuation
```

#### 5️⃣ Ellipsis Detection
```
"He said..." ← Ellipsis is not a sentence boundary
"Wait..." ← Not a boundary until complete
```

#### 6️⃣ Valid Sentence Endings
```
"The president is Joe Biden. He won in 2020." ← VALID BOUNDARY
```

**Rule**: Period followed by space and capital letter, and no abbreviation patterns detected.

## Real-World Examples

### Example 1: Middle Initials
**Input Stream**: `"The current president is Donald J. Trump. He was elected in 2016."`

**Naive Chunking** (BAD):
```
Chunk 1: "The current president is Donald J."  ← WRONG!
Chunk 2: "Trump."
Chunk 3: "He was elected in 2016."
```

**Smart Chunking** (GOOD):
```
Chunk 1: "The current president is Donald J. Trump."  ← CORRECT!
Chunk 2: "He was elected in 2016."
```

### Example 2: Titles and Names
**Input**: `"Dr. Martin Luther King Jr. was a civil rights leader. He gave the famous speech."`

**Smart Chunking**:
```
Chunk 1: "Dr. Martin Luther King Jr. was a civil rights leader."
Chunk 2: "He gave the famous speech."
```

### Example 3: Company Names
**Input**: `"Apple Inc. is a tech company. It was founded by Steve Jobs."`

**Smart Chunking**:
```
Chunk 1: "Apple Inc. is a tech company."
Chunk 2: "It was founded by Steve Jobs."
```

### Example 4: Numbers and Decimals
**Input**: `"The value of pi is 3.14 approximately. It's used in math."`

**Smart Chunking**:
```
Chunk 1: "The value of pi is 3.14 approximately."
Chunk 2: "It's used in math."
```

### Example 5: Mixed Punctuation
**Input**: `"Is he here? Yes! He arrived via U.S. Airways Flight 123."`

**Smart Chunking**:
```
Chunk 1: "Is he here?"
Chunk 2: "Yes!"
Chunk 3: "He arrived via U.S. Airways Flight 123."
```

## Edge Cases Handled

### ✅ Successfully Handles:

1. **Multiple initials**: "J.R.R. Tolkien wrote the book."
2. **State abbreviations**: "He lives in Washington D.C. now."
3. **Academic titles**: "Prof. Einstein taught physics."
4. **Military ranks**: "Gen. Patton led the troops."
5. **Addresses**: "123 Main St. is the location."
6. **Time expressions**: "It's 3.30 p.m. currently."
7. **Latin abbreviations**: "He studies mammals, e.g. dogs and cats."
8. **Etc. usage**: "Fruits, vegetables, etc. are healthy."

### ⚠️ Potential Limitations:

1. **Unusual abbreviations**: Custom or domain-specific abbreviations might not be recognized
2. **Multiple languages**: Optimized for English
3. **Creative punctuation**: Artistic or non-standard usage might confuse the system
4. **URLs**: "Visit www.example.com. Click here" (might break incorrectly)

## Configuration

### Default Behavior
```python
# Default: Chunks on periods, exclamation marks, and question marks
tts.speak_streaming_async(myai.stream(user_input=text))
```

### Custom Chunk Characters
```python
# Only chunk on periods (more careful)
tts.speak_streaming_async(myai.stream(user_input=text), chunk_on=".")

# Chunk on all major punctuation
tts.speak_streaming_async(myai.stream(user_input=text), chunk_on=".!?")

# Even include semicolons and colons (faster, but mid-sentence breaks)
tts.speak_streaming_async(myai.stream(user_input=text), chunk_on=".!?;:")
```

## Performance Impact

The smart detection adds minimal overhead:

- **Naive split**: O(n) - just find last period
- **Smart detection**: O(n × m) where m is number of abbreviation patterns (~50)
- **Real-world impact**: < 1ms per chunk (negligible)

The improved user experience far outweighs the tiny performance cost!

## Debugging

If you encounter incorrect chunking, you can test the detection:

```python
# Test a specific case
tts = TextToSpeech(...)
text = "The president is Donald J. Trump. He won."

# Find where it would chunk
boundary = tts._find_sentence_boundary(text, ".!?")
print(f"Would chunk at position: {boundary}")
print(f"First chunk: {text[:boundary+1]}")
```

## Future Improvements

Possible enhancements (not currently implemented):

1. **Machine learning**: Train a model to detect sentence boundaries
2. **Context awareness**: Learn from correction patterns
3. **Language detection**: Adjust rules based on detected language
4. **Domain-specific rules**: Add medical, legal, or technical abbreviations
5. **Acronym database**: Maintain a larger list of known abbreviations

## Summary

The smart sentence detection ensures that your AI assistant:

✅ Doesn't break mid-name: "Donald J. Trump"
✅ Respects titles: "Dr. Smith"
✅ Handles numbers: "Version 3.14"
✅ Recognizes common abbreviations: "e.g.", "Inc.", "etc."
✅ Provides natural speech flow

All while maintaining the fast streaming performance you want! 🎯

---

**Note**: If you encounter a specific case that's not handled correctly, you can easily add it to the `common_abbrevs` list in the `_is_sentence_boundary()` method.
