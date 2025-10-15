# Challenging Test Phrases for Volume Boost Testing

## Purpose
These phrases are designed to stress-test Whisper's transcription accuracy at different volume levels, particularly with the `tiny` model which is less robust to quiet audio.

## Why These Are Challenging

### 1. Similar-Sounding Words
Words that sound alike and require good audio quality to distinguish.

### 2. Proper Names
Names that aren't common in the training data.

### 3. Technical Terms
Domain-specific vocabulary that might be misheard.

### 4. Homophones
Words that sound identical but have different meanings.

### 5. Short Commands
Brief phrases that offer less context for the model.

---

## Test Phrases (Recommended)

### Category 1: Names & Proper Nouns (High Priority)
These test the vocabulary hints feature AND volume sensitivity:

```
"Hey Sam, my name is Tobias"
"Sam, can you remind Tobias about the meeting?"
"Hey Sam, I need to call Tobias tomorrow"
```

**Why challenging:** 
- "Sam" sounds like "some", "psalm"
- "Tobias" sounds like "Tobius", "Tobis", "Tobyas"
- At low volume, these become even harder to distinguish

---

### Category 2: Similar-Sounding Words
```
"Can you search for information about their schedule"
"I need to check whether the weather is good"
"The device has fifty or fifteen features"
"I want to buy or by the store"
"He's going to the gym or Jim's house"
```

**Why challenging:**
- their/there/they're
- whether/weather
- fifty/fifteen (easily confused)
- buy/by/bye
- gym/Jim

---

### Category 3: Technical Jargon
```
"Hey Sam, can you help me with API authentication?"
"I need to deploy the Kubernetes cluster"
"Can you explain OAuth versus JWT tokens?"
"Help me configure the PostgreSQL database"
```

**Why challenging:**
- Technical acronyms (API, OAuth, JWT)
- Non-English technical terms (Kubernetes, PostgreSQL)
- Requires clear audio to distinguish from similar sounds

---

### Category 4: Short Commands (Minimal Context)
```
"Set timer"
"Play music"
"Stop that"
"What time?"
"Call Sam"
```

**Why challenging:**
- Very short = less context for the model
- Similar-sounding alternatives exist
- At low volume, could be completely missed

---

### Category 5: Number Sequences
```
"My phone number is five five five, one two three four"
"The code is three seven nine eight"
"Set an alarm for six forty-five"
```

**Why challenging:**
- Numbers sound very similar (six/sixteen, thirteen/thirty)
- Low volume makes distinction harder
- "teen" vs "ty" endings are subtle

---

### Category 6: Complex Multi-Part Queries
```
"Hey Sam, I was wondering if you could help me set up a Google Calendar integration because I've been wanting to automate my schedule"
"Can you search for the best Italian restaurants in San Francisco that are open on Tuesday evenings?"
"I need to send an email to Sarah about the project deadline which is next Friday at three PM"
```

**Why challenging:**
- Long sentences test transcription consistency
- Multiple proper nouns and details
- At low volume, model might lose track mid-sentence

---

### Category 7: Accents & Pronunciation Variations
```
"Schedule a meeting" (shed-yool vs sked-yool)
"I need to ask about the tomato sauce recipe" (tuh-may-toe vs tuh-mah-toe)
"Can you help me with the aluminium project?" (British vs American)
```

**Why challenging:**
- Pronunciation variations
- Low volume makes accent harder to detect

---

## Recommended Testing Workflow

### Test 1: Basic Names (Start Here)
**Record at very quiet volume:**
```
"Hey Sam, my name is Tobias. Can you remember that, Sam? Tobias is my name."
```

**Expected challenges:**
- "Sam" → "some", "psalm", "sum"
- "Tobias" → "Tobius", "Tobis", "Tobyas", "to bias"

**This tests:** Vocabulary hints + volume boost interaction

---

### Test 2: Homophones
**Record at quiet volume:**
```
"I need to check whether the weather is good today. Their schedule shows they're going there tomorrow."
```

**Expected challenges:**
- whether/weather confusion
- their/there/they're confusion
- At low volume, context clues become critical

---

### Test 3: Numbers & Similar Sounds
**Record at quiet volume:**
```
"The code is fifty fifteen or was it fifteen fifty? I need to call at six fifteen or sixteen fifty."
```

**Expected challenges:**
- fifty vs fifteen
- six fifteen vs sixteen fifty
- Numbers are particularly hard at low volume

---

### Test 4: Technical Terms
**Record at quiet volume:**
```
"Hey Sam, I need help with OAuth authentication and JWT tokens for the API endpoint."
```

**Expected challenges:**
- OAuth (O-auth, oh-off, oh-auth)
- JWT (J-W-T, jot)
- API (A-P-I, ay-pee-eye)
- Technical terms need clear audio

---

### Test 5: Rapid Fire Short Commands
**Record quickly at quiet volume:**
```
"Set timer. Play music. Stop that. What time? Call Sam. Set alarm."
```

**Expected challenges:**
- Minimal context per phrase
- Quick succession
- Low volume + speed = very challenging

---

## How to Test

### Setup
1. Run the recording tool:
   ```bash
   python record_test_audio.py
   ```

2. Choose a test phrase from above

3. Record at **deliberately quiet volume** (whisper-level)

4. Test with volume boost:
   ```bash
   python test_volume_boost.py your_recording.wav
   ```

### What to Look For

**No volume boost needed if:**
- All methods produce identical transcriptions
- Even quiet audio is transcribed correctly
- Only minor capitalization differences

**Volume boost helps if:**
- No boost: Words missing or wrong
- With boost: Correct transcription
- Clear improvement in accuracy

---

## Recommended First Test

**Try this phrase at very quiet volume:**

```
"Hey Sam, my name is Tobias. I need to check whether the weather 
forecast shows fifteen degrees or fifty degrees. Can you help me 
with that, Sam?"
```

**Why this is perfect:**
- ✅ Tests names (Sam, Tobias)
- ✅ Tests homophones (whether/weather)
- ✅ Tests numbers (fifteen/fifty)
- ✅ Tests vocabulary hints
- ✅ Tests volume sensitivity
- ✅ Long enough to show consistency issues

**Expected results:**
- **No boost (quiet):** Might get "some" instead of "Sam", "whether" wrong, number confusion
- **With boost:** Should get everything right

---

## Advanced Testing

### Extreme Quiet Test
Record at **barely audible** volume:
```
"Hey Sam" (whispered)
```

This tests the absolute limits of volume boost effectiveness.

### Background Noise Test
Record with TV or music in background:
```
"Hey Sam, what's the weather?"
```

This tests whether volume boost amplifies noise too much.

### Distance Test
Record from across the room:
```
"Hey Sam, can you hear me from here?"
```

This tests realistic usage scenarios.

---

## Summary

**Best single test phrase:**
```
"Hey Sam, my name is Tobias. Whether the weather is fifteen or fifty degrees, 
I need to set a timer and call Sam about the OAuth API."
```

This combines:
- Names (Sam, Tobias)
- Homophones (whether/weather)
- Numbers (fifteen/fifty)
- Technical terms (OAuth, API)
- Natural speech patterns

**Record this at whisper-quiet volume and test it!**
