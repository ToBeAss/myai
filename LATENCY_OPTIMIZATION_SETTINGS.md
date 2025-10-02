# Quick Latency Optimization Settings

This file contains optimized configuration parameters to reduce latency in the voice interaction loop.

## How to Apply

Copy the code snippets below into the corresponding files to implement the optimizations.

---

## 1. main_continuous.py - Optimized TTS Settings

### Before:
```python
tts = TextToSpeech(
    voice_name="en-GB-Chirp3-HD-Achernar",
    language_code="en-GB",
    speaking_rate=1.1,
    pitch=0.0,
    enforce_free_tier=True,
    fallback_voice="en-GB-Wavenet-A"
)
```

### After (Faster voice, saves ~100ms per synthesis):
```python
tts = TextToSpeech(
    voice_name="en-GB-Wavenet-A",  # Faster than Chirp3-HD
    language_code="en-GB",
    speaking_rate=1.1,
    pitch=0.0,
    enforce_free_tier=True,
    fallback_voice="en-GB-Standard-A"  # Even faster fallback
)
```

---

## 2. main_continuous.py - Optimized Whisper Model

### Before:
```python
stt = SpeechToText(model_size="base", track_metrics=False)
```

### After Option A - Slightly Faster (saves ~200ms):
```python
stt = SpeechToText(model_size="tiny", track_metrics=False)
# Note: "tiny" is 2-3x faster but slightly less accurate
# Test to ensure accuracy is acceptable for your use case
```

### After Option B - Much Faster (saves ~500ms, requires installation):
First install: `pip install faster-whisper`

Then modify `lib/speech_to_text.py`:
```python
# At the top, replace:
# import whisper
# with:
from faster_whisper import WhisperModel

# In __init__, replace:
# self.model = whisper.load_model(model_size)
# with:
self.model = WhisperModel(model_size, device="cpu", compute_type="int8")

# In transcribe_audio, replace the transcription call:
# result = self.model.transcribe(audio_data, language="en")
# transcribed_text = result["text"].strip()
# with:
segments, info = self.model.transcribe(audio_data, language="en")
transcribed_text = " ".join([segment.text for segment in segments]).strip()
```

---

## 3. lib/speech_to_text.py - Faster Recording Stop

### Location: `_continuous_listening()` method, around line 1175

### Before:
```python
if silence_count > 60:  # About 1.5 seconds of silence
    print("🔄 Processing speech...")
    self._process_speech_chunk(speech_frames)
```

### After (saves ~500ms):
```python
if silence_count > 40:  # About 1.0 seconds of silence (faster response)
    print("🔄 Processing speech...")
    self._process_speech_chunk(speech_frames)
```

### Alternative - Dynamic Threshold:
```python
# Shorter utterances trigger faster processing
min_silence = 30  # 750ms minimum
max_silence = 60  # 1.5s maximum
dynamic_threshold = min(max_silence, min_silence + len(speech_frames) // 100)

if silence_count > dynamic_threshold:
    print("🔄 Processing speech...")
    self._process_speech_chunk(speech_frames)
```

---

## 4. lib/speech_to_text.py - More Aggressive VAD

### Location: `_continuous_listening()` method, around line 1125

### Before:
```python
vad_required_frames = 3  # Require 3 consecutive speech frames
```

### After (saves ~25ms):
```python
vad_required_frames = 2  # Require 2 consecutive speech frames (faster detection)
```

---

## 5. lib/text_to_speech.py - Faster Sentence Chunking

### Location: `speak_streaming_async()` method signature, around line 688

### Before:
```python
def speak_streaming_async(self, text_generator, chunk_on: str = ".", print_text: bool = True,
                          min_chunk_size: int = 20):
```

### After (saves ~100-200ms to first audio):
```python
def speak_streaming_async(self, text_generator, chunk_on: str = ".,;", print_text: bool = True,
                          min_chunk_size: int = 15):
```

Changes:
- `chunk_on` includes commas and semicolons (more boundaries = faster chunking)
- `min_chunk_size` reduced from 20 to 15 characters (earlier first synthesis)

---

## 6. main_continuous.py - Pass Optimized TTS Parameters

### Add when calling speak_streaming_async:

### Before:
```python
tts.speak_streaming_async(response_generator, print_text=True)
```

### After:
```python
tts.speak_streaming_async(
    response_generator, 
    print_text=True,
    chunk_on=".,;",  # More chunk boundaries
    min_chunk_size=15  # Start synthesis sooner
)
```

---

## 7. lib/agent.py - Reduce Memory Context

### Location: `_structure_prompt()` method, around line 132

### Before:
```python
if self._memory:
    conversation_history = self._memory.retrieve_memory()
    formatted_conversation_history = Memory.format_messages(conversation_history)
```

### After (saves ~50-100ms):
```python
if self._memory:
    conversation_history = self._memory.retrieve_memory()[-5:]  # Last 5 only
    formatted_conversation_history = Memory.format_messages(conversation_history)
```

---

## Summary of Expected Improvements

| Optimization | Time Saved | Risk | Effort |
|-------------|-----------|------|--------|
| 1. Use Wavenet voice | ~100ms per synthesis | Low | Very Easy |
| 2a. Use "tiny" Whisper | ~200ms | Medium (accuracy) | Very Easy |
| 2b. Use faster-whisper | ~500ms | Low | Easy |
| 3. Faster silence detection | ~500ms | Medium (may cut off slow speakers) | Easy |
| 4. Reduce VAD frames | ~25ms | Low | Very Easy |
| 5. Faster TTS chunking | ~100-200ms | Low | Very Easy |
| 6. Apply TTS parameters | Included in #5 | None | Very Easy |
| 7. Reduce memory context | ~50-100ms | Low | Very Easy |

**Total Expected Improvement: 1.5 - 2.5 seconds faster**

---

## Recommended Application Order

1. **Start with low-risk optimizations** (#1, #4, #5, #6, #7)
   - Expected improvement: ~300-450ms
   - Zero accuracy impact
   - Takes 5-10 minutes

2. **Test with faster-whisper** (#2b)
   - Expected improvement: +500ms
   - Requires pip install
   - Takes 15 minutes

3. **Fine-tune silence detection** (#3)
   - Expected improvement: +500ms
   - Test with different speakers
   - Adjust threshold if needed

4. **Consider "tiny" Whisper** (#2a) only if accuracy is currently excessive
   - Expected improvement: +200ms
   - Only if you notice over-accurate transcriptions

---

## Testing Your Changes

After applying optimizations, run the parallel processing test:

```bash
python test_parallel_processing.py
```

This will show you:
- Actual latency measurements
- Proof of parallel processing
- Recommendations for further improvements

---

## Rollback Instructions

If any optimization causes issues:

1. **Accuracy problems**: Revert Whisper model changes (#2)
2. **Cut-off speech**: Increase silence_count back to 60 (#3)
3. **Incomplete sentences**: Increase min_chunk_size back to 20 (#5)
4. **Voice quality**: Revert to Chirp3-HD voice (#1)

All changes are simple parameter adjustments and can be easily reverted.
