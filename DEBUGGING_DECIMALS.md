# 🔍 Debugging Decimal Number Pronunciation

## The Issue

When the AI says "The value of pi is 3.14", you're hearing "three (pause) fourteen" instead of "three point fourteen".

## Two Possible Causes

### 1️⃣ Chunking Problem (Our Code)
**Symptom**: The text is being split incorrectly
```
Chunk 1: "The value of pi is 3."
Chunk 2: "14"
```

### 2️⃣ TTS Voice Model Problem (Google's Voice)
**Symptom**: The text is NOT being split, but the voice pronounces "3.14" as "three fourteen"
```
Chunk 1: "The value of pi is 3.14"  ← Correct chunk
Voice says: "three fourteen" ← Voice interprets it wrong
```

## How to Diagnose

### Test 1: Check Chunking Behavior

Run this command:
```bash
python test_chunking.py "The value of pi is 3.14"
```

This will show you exactly how the text is being chunked. Look at the output:

**If you see:**
```
Chunk 1: "The value of pi is 3."
Chunk 2: "14"
```
→ **It's a chunking problem** (our code needs fixing)

**If you see:**
```
Chunk 1: "The value of pi is 3.14"
```
→ **It's a voice model problem** (Google's TTS interprets it wrong)

### Test 2: Test Voice Pronunciation

Run this command:
```bash
python test_tts_pronunciation.py
```

This will test how the voice pronounces different formats:
- "3.14" 
- "3 point 14"
- "three point one four"

Listen to each one and note which sounds correct.

## Likely Culprit: Voice Model

Based on your feedback that:
- ✅ "Mr. Tobias" works fine (no pause)
- ❌ "3.14" has a pause
- ✅ "three point one four" works fine

This suggests **the chunking is working correctly**, but the **voice model** (especially Chirp3-HD) might have a quirk where it doesn't naturally pronounce decimal numbers.

## Solutions

### Solution 1: Post-Process Numbers (Recommended)

Add a preprocessing step that converts decimal numbers to words:

```python
def format_decimals_for_speech(text: str) -> str:
    """Convert decimal numbers to spoken format."""
    import re
    
    # Pattern to match decimal numbers like 3.14, 2.5, etc.
    def replace_decimal(match):
        whole = match.group(1)
        decimal = match.group(2)
        return f"{whole} point {' '.join(decimal)}"
    
    # Replace decimals like "3.14" with "3 point 1 4"
    text = re.sub(r'\b(\d+)\.(\d+)\b', replace_decimal, text)
    return text

# Use before TTS
text = "The value of pi is 3.14"
text = format_decimals_for_speech(text)
# Result: "The value of pi is 3 point 1 4"
tts.speak(text)
```

### Solution 2: Use SSML (Structured Markup)

Google Cloud TTS supports SSML (Speech Synthesis Markup Language) which gives precise control:

```python
ssml_text = """
<speak>
The value of pi is 
<say-as interpret-as="number" format="decimal">3.14</say-as>
</speak>
"""
```

This explicitly tells the TTS how to interpret the number.

### Solution 3: Try Different Voice

Standard voices might handle numbers differently than Chirp3-HD:

```python
# Try with Standard voice
tts = TextToSpeech(
    voice_name="en-GB-Standard-A",  # Instead of Chirp3-HD
    language_code="en-GB"
)
```

Standard voices are trained on more diverse data and might handle numbers better.

### Solution 4: Instruct the LLM

Add an instruction to your agent to spell out numbers:

```python
myai.add_instruction(
    "When mentioning decimal numbers, spell them out. "
    "For example, say 'three point one four' instead of '3.14'."
)
```

## Implementation: Let's Fix It

Based on the most likely cause (voice model issue), here's what I recommend:

### Option A: Quick Fix - Instruct LLM
Simplest solution - let the LLM handle it:

```python
# Add to your main_continuous.py
myai.add_instruction(
    "When mentioning numbers with decimals, spell them out in words. "
    "For example: say 'three point one four' not '3.14', "
    "say 'two point five' not '2.5'."
)
```

### Option B: Preprocessing - Convert Before TTS
More robust - handles any LLM output:

I can add a preprocessing function that automatically converts "3.14" → "3 point 1 4" before sending to TTS.

### Option C: SSML Support
Most powerful - add full SSML support to the TTS class for precise control over pronunciation.

## Which Solution Do You Want?

1. **Quick LLM instruction** (2 minutes) - Easiest, but LLM might forget
2. **Number preprocessing** (10 minutes) - Reliable, handles all numbers automatically  
3. **SSML support** (30 minutes) - Most powerful, handles numbers, emphasis, pauses, etc.
4. **Try different voice** (1 minute) - See if Standard voice handles it better
5. **Just debug first** - Run the test scripts to confirm the actual problem

What would you like me to implement?

---

## Quick Test Commands

```bash
# Test 1: See how text is chunked
python test_chunking.py "The value of pi is 3.14"

# Test 2: Hear how voice pronounces different formats
python test_tts_pronunciation.py

# Test 3: Test with your actual assistant
# Say: "What is the value of pi?"
# Listen carefully to how it pronounces the number
```

Let me know what you find out!
