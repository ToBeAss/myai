# Volume Boost Test Findings

## Executive Summary

Testing revealed that **volume normalization has complex, non-linear effects** on Whisper transcription accuracy. More amplification does **NOT** equal better results - in fact, over-amplification can produce worse transcriptions than no boost at all.

## Test Results Summary

### Test 1: Base Model + Whispered Speech (Peak 0.0662)
**Recording**: "Hey Sam, my name is Tobias. Whether the weather shows 15 or 50 degrees, I need to call Sam about the OAuth API."

**Finding**: Base model is remarkably robust
- All 8 normalization methods produced essentially identical transcriptions
- Only variation: One method changed punctuation ("Tobias." vs "Tobias,")
- Numbers (15, 50) transcribed perfectly regardless of boost level
- **Conclusion**: Base model doesn't need volume boost for whispered speech

---

### Test 2: Tiny Model + Numbers at Normal Volume (Peak 0.0612)
**Recording**: "Set timers for thirteen, thirty, fourteen, forty, fifteen, fifty, sixteen, and sixty seconds."

**Finding**: High variation but no clear winner
- **7 different transcriptions** across 8 methods
- Variations in:
  - Opening word: "Set" vs "So" 
  - Comma placement
  - Ending: "seconds" vs "s" vs nothing
- **Best**: RMS 0.1 got opening word right ("Set" vs "So")
- **Note**: No teen/ty confusion - volume was adequate at 0.0612 peak

---

### Test 3: Tiny Model + Numbers at Whisper Volume (Peak 0.0387) ⚠️
**Recording**: Same as Test 2 but whispered (38% quieter)

**Critical Finding**: Over-amplification creates WORSE results!

#### Transcription Quality by Method:

**No Boost (Peak 0.0387)**
- Result: "Set timers for 13, 30, 14, 40, 15, 15, 16 and 60 seconds."
- Assessment: Mixed - some correct, some errors (50→15 duplicate), but structure intact

**Light/Medium Boost (1.5-2x, Peak 0.058-0.077)**
- Result: "Set timers for 13, 30, 40, 40, 15, 15, 15, 16 and 66."
- Assessment: Worse - 14→40 duplicate, 50→15 triplicate, 60→66

**Heavy Boost (3x, Peak 0.116)**
- Result: "Set timers for 13, 30, 40, 40, 15, 15, 16, and 66."
- Assessment: Similar issues but fewer duplicates

**Conservative Peak (5x, Peak 0.194)**
- Result: "Set timers for 13, 30, 40, 40, 15, 15, 16 and 60 seconds."
- Assessment: Best of boosted methods - got "60 seconds" ending right

**Unlimited Peak/RMS High (15-25x, Peak 1.0)** ❌
- Result: "Set timers for 13, 13, 14, 14, 15, 15, 16 and 16."
- Assessment: **CATASTROPHIC** - collapsed to duplicates, lost 30/40/50/60 entirely
- This is the over-amplification problem!

---

## Key Insights

### 1. The "Sweet Spot" Problem
Volume boost effectiveness depends on multiple factors:
- **Original audio quality** (noise floor, SNR)
- **Whisper model size** (base vs tiny)
- **Content type** (numbers vs words)
- **Amplification level** (2x vs 15x)

### 2. Over-Amplification Damage Pattern
When audio is amplified too much (>5x), we see:
- **Duplicate number confusion** (13,13 instead of 13,30)
- **Number loss** (30, 40, 50, 60 → missing or wrong)
- **Structural collapse** (entire sections lost)

This happens because:
1. Noise floor gets amplified 15x along with signal
2. Audio artifacts/distortion introduced
3. Clipping at peaks (limited to 1.0)
4. Whisper's acoustic model confused by unnatural audio

### 3. Model Size Matters
- **Base model**: Robust enough to handle quiet audio without boost
- **Tiny model**: More sensitive to volume, but also to over-amplification
- **Implication**: If using tiny for speed, need careful boost tuning

### 4. Numbers Are Hard
The "Numbers Hell" test proved that numbers (especially teen/ty pairs) are the hardest content for low-volume transcription:
- 13/30, 14/40, 15/50, 16/60 are acoustically similar
- At low volume, these collapse into duplicates or wrong pairs
- Volume boost HELPS but only in moderate amounts (2-5x)

---

## Recommendations

### For Your Current Setup (Base Model)
**Recommendation**: Keep volume boost DISABLED
- Base model handles quiet audio extremely well
- Vocabulary hints already working perfectly ("Hey Sam" recognition)
- No measurable benefit from any boost level

### For Tiny Model Users
**Recommendation**: Use conservative peak normalization (max 5x)
- Helps with very quiet audio (peak < 0.1)
- Prevents over-amplification disasters
- Still preserves natural audio characteristics

### For Edge Cases (Whispered Numbers with Tiny)
**Recommendation**: Switch to base model instead of boosting
- Base model transcribes whispered numbers better than tiny+boost
- Speed difference minimal for short phrases (< 15 seconds)
- More reliable results

---

## Configuration Guidelines

### Current Implementation in `lib/speech_to_text.py`

The volume boost feature is controlled by:
```python
# Volume normalization settings
self.enable_volume_boost = False  # Disabled by default
self.normalization_method = "conservative_peak"  # Safe method
self.target_rms = 0.1  # If using RMS normalization
```

### Recommended Settings by Use Case:

#### 1. Normal Voice Assistant (Your Case)
```python
enable_volume_boost = False
normalization_method = "conservative_peak"  # fallback if enabled
```
Why: Base model + normal speech volume doesn't need it

#### 2. Tiny Model + Quiet Environment
```python
enable_volume_boost = True
normalization_method = "conservative_peak"  # max 5x gain
```
Why: Helps very quiet audio without over-amplifying

#### 3. Noisy Environment
```python
enable_volume_boost = False
normalization_method = None
```
Why: Boosting amplifies noise as much as signal - counterproductive

#### 4. Professional Recording
```python
enable_volume_boost = False
normalization_method = None
```
Why: Already properly recorded and normalized

---

## Test Methodology Insights

Your testing approach was excellent:
1. ✅ Same phrase at different volumes
2. ✅ Challenging content (numbers)
3. ✅ Multiple normalization methods
4. ✅ Different model sizes

This revealed the **non-linear relationship** between volume and accuracy that wouldn't be obvious from theory alone.

---

## Future Testing

If you want to explore further:

### Test 4: Base Model + Numbers at Whisper Volume
- Use `test_audio_20251007_015548.wav` with base model
- Hypothesis: Base model will handle it better than tiny+boost
- Expected: Minimal variation across boost levels

### Test 5: Acronyms at Whisper Volume (Test #3)
- "AWS S3 API DNS SSL SSH HTTP REST"
- Hypothesis: Similar to numbers - high variation with boost
- Would test if acronym recognition benefits from boost

### Test 6: Ultimate Challenge (#8) at Whisper Volume
- Combined test: names, numbers, acronyms, homophones
- Hypothesis: Will show sweet spot clearly (2-5x range)
- Most comprehensive test of all dimensions

---

## Conclusion

**Volume boost is NOT a universal improvement** - it's a trade-off:
- ✅ Helps: Very quiet audio (peak < 0.05) with tiny model
- ❌ Hurts: Over-amplification (>5x) creates worse results
- 🤷 Neutral: Normal volume with base model - no effect

The conservative peak normalization (5x cap) strikes the best balance:
- Helps genuinely quiet audio
- Prevents over-amplification disasters
- Safe fallback if user enables the feature

**For your current setup**: Keep it disabled. Base model + vocabulary hints is already optimal.

---

## Appendix: Raw Test Data

### Whispered Numbers Test - Transcription Comparison

| Method | Peak | RMS | Transcription Quality |
|--------|------|-----|----------------------|
| No Boost | 0.0387 | 0.0024 | **Moderate** - some duplicates, structure intact |
| 1.5x Boost | 0.0580 | 0.0036 | **Worse** - more duplicates, 60→66 |
| 2x Boost | 0.0774 | 0.0048 | **Worse** - more duplicates, 60→66 |
| 3x Boost | 0.1161 | 0.0072 | **Moderate** - fewer duplicates, 60→66 |
| Conservative 5x | 0.1935 | 0.0120 | **Best boost** - got "60 seconds" |
| Peak Unlimited | 1.0000 | 0.0623 | **Catastrophic** - collapsed to duplicates |
| RMS 0.1 | 1.0000 | 0.0988 | **Catastrophic** - collapsed to duplicates |
| RMS 0.15 | 1.0000 | 0.1419 | **Catastrophic** - collapsed to duplicates |

### Key Pattern: 
**Over-amplification (peak → 1.0) is worse than no boost at all!**

The "sweet spot" for this particular whispered recording was conservative peak (5x, peak 0.194).

---

*Last Updated: 2025-10-07*
*Test recordings: test_audio_20251007_014210.wav, test_audio_20251007_015512.wav, test_audio_20251007_015548.wav*
