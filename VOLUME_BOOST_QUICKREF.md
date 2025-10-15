# Volume Boost Quick Reference

## TL;DR - How to Test This

```bash
# 1. Test if it helps
python test_volume_boost.py

# 2. If tests show improvement, enable in your code
# Edit main_continuous.py or main.py and add:
stt = SpeechToText(
    enable_volume_boost=True,
    boost_method="peak"
)

# 3. Run and observe
python main_continuous.py
# Look for "🔊 Peak boost:" messages
```

## What Does It Do?

Normalizes audio volume before Whisper transcription to potentially improve accuracy with quiet recordings.

## Should I Use It?

✅ **Yes, if:**
- Your microphone input is quiet
- You speak softly or from a distance
- Transcriptions miss words in quiet recordings
- Test shows improved results

❌ **No, if:**
- Your audio is already clear and loud
- Tests show no difference
- Current transcription accuracy is good

## Methods Available

| Method | Best For | When to Use |
|--------|----------|-------------|
| `"peak"` | Most cases | Audio consistently quiet (peak < 0.95) |
| `"rms"` | Variable volume | Inconsistent loudness across recordings |
| `"simple"` | Quick test | Just want to try 1.5x boost |
| `"none"` | Disable | Boosting not needed |

## Quick Code Examples

### Minimal (just enable)
```python
stt = SpeechToText(enable_volume_boost=True)
```

### Recommended
```python
stt = SpeechToText(
    enable_volume_boost=True,
    boost_method="peak"
)
```

### RMS (loudness-based)
```python
stt = SpeechToText(
    enable_volume_boost=True,
    boost_method="rms",
    rms_target=0.1  # Adjust 0.05-0.15
)
```

### Disable
```python
stt = SpeechToText(enable_volume_boost=False)  # Default
```

## Console Output

When enabled, you'll see:
```
🔊 Volume boosting: ENABLED (method: peak)
🔊 Peak boost: 0.312 → 1.0 (gain: 3.21x)
```

If nothing shows up during transcription, your audio is already loud enough (peak > 0.95).

## Testing Workflow

1. **Test:** `python test_volume_boost.py` 
2. **Check:** Did any method improve transcription?
3. **Enable:** Add parameters to your SpeechToText initialization
4. **Run:** Test in real usage
5. **Adjust:** Try different methods if needed

## Performance

- Adds ~0.1-0.2ms per recording
- Negligible impact on total processing time
- Safe to leave enabled even if not needed

## Files

- `test_volume_boost.py` - Test script
- `VOLUME_BOOST_GUIDE.md` - Full documentation
- `VOLUME_BOOST_SUMMARY.md` - Complete summary
- `example_volume_boost.py` - Code examples
- `lib/speech_to_text.py` - Implementation (modified)

## Defaults

```python
enable_volume_boost=False  # Disabled by default
boost_method="peak"         # Peak normalization when enabled
rms_target=0.1             # RMS target level
```

## When Will It Boost?

- **Peak method:** Only if peak < 0.95
- **RMS method:** Only if RMS < (target × 0.8)
- **Simple method:** Always (1.5x)

So it won't boost already-loud audio unnecessarily.
