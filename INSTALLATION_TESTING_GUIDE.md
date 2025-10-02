# Installation & Testing Guide - Optimizations Applied

## ✅ Changes Applied

We've implemented the following optimizations:

1. **faster-whisper integration** (~500ms improvement)
2. **Dynamic silence threshold** (~300-500ms improvement)  
3. **Reduced min_chunk_size** (~50-100ms improvement)

**Expected total improvement: ~850-1,100ms (1-1.5 seconds faster!)**

---

## 📦 Installation Steps

### Step 1: Install faster-whisper

```bash
pip install faster-whisper
```

**What this does:**
- Installs optimized Whisper backend (CTranslate2)
- Same accuracy, 4-5x faster
- No model retraining needed

**Verify installation:**
```bash
python -c "from faster_whisper import WhisperModel; print('✅ faster-whisper installed successfully')"
```

If you see the success message, you're good to go!

---

## 🧪 Testing Your Optimizations

### Test 1: Quick Functionality Test

Run your voice assistant normally:

```bash
python main_continuous.py
```

**What to look for:**
- Startup should show: "🚀 Using faster-whisper for optimized transcription"
- Try a short command: "How are you Sam?"
- Try a longer question: "Sam, could you explain how photosynthesis works?"
- Notice the processing messages showing different silence thresholds

**Expected behavior:**
- Short commands should trigger processing faster (after ~750ms silence)
- Longer speech should wait longer (~1000-1250ms)
- No accuracy degradation

---

### Test 2: Detailed Performance Analysis

Run the parallel processing test to get exact measurements:

```bash
python test_parallel_processing.py
```

**What you'll see:**
1. ⏱️ Time to first token
2. 🎵 TTS synthesis events with timestamps
3. 🔊 Audio playback timing
4. ✅ Proof of parallel processing
5. 📊 Performance recommendations

**Compare before/after:**

**Before optimizations** (expected baseline):
- Time to first audio: ~6,400ms
- Transcription: ~1,000ms
- First sentence buffer: ~700ms

**After optimizations** (expected results):
- Time to first audio: ~5,300-5,500ms ⚡
- Transcription: ~500ms ⚡
- First sentence buffer: ~600ms ⚡
- Dynamic threshold working correctly ⚡

---

### Test 3: Edge Case Testing

Test various speech patterns to ensure dynamic threshold works correctly:

#### Short Commands (Should be FAST - 750ms threshold)
Say these quickly:
- "How are you?"
- "What's the time?"
- "Hello Sam"
- "Thank you"

**Expected:** Should process immediately after you finish speaking (~750ms)

#### Medium Length (Should be BALANCED - 1000ms threshold)
Say these naturally:
- "Sam, what's the weather forecast for tomorrow?"
- "Could you explain quantum physics to me?"
- "Tell me a fun fact about space exploration"

**Expected:** Should wait ~1 second after you stop speaking

#### Long Speech (Should be PATIENT - 1250ms threshold)
Say these with natural pauses:
- "Sam, I've been thinking about artificial intelligence and how it's changing the world. Could you give me your perspective on the ethical implications of AI development and what we should be concerned about?"

**Expected:** Should wait ~1.25 seconds to ensure you're done speaking

---

## 🔍 Troubleshooting

### Issue: faster-whisper not being used

**Symptoms:**
- Don't see "🚀 Using faster-whisper" message on startup
- See "⚠️ faster-whisper not available" message

**Solutions:**
1. Check installation: `pip show faster-whisper`
2. Reinstall: `pip uninstall faster-whisper && pip install faster-whisper`
3. Check Python version (requires Python 3.8+)
4. If on Mac M1/M2: `pip install faster-whisper --no-deps` then `pip install faster-whisper`

### Issue: Speech getting cut off

**Symptoms:**
- Your speech is interrupted mid-sentence
- You have to repeat yourself

**Solutions:**
1. You might be a slower speaker - adjust dynamic thresholds in `lib/speech_to_text.py`:
   ```python
   if len(speech_frames) < 80:
       dynamic_threshold = 35  # Increase from 30
   elif len(speech_frames) < 200:
       dynamic_threshold = 45  # Increase from 40
   else:
       dynamic_threshold = 55  # Increase from 50
   ```

2. Monitor the console - it shows which threshold was used
3. Adjust based on your speaking pace

### Issue: Responses feel choppy

**Symptoms:**
- Audio pauses awkwardly in middle of thoughts
- Sentences are cut at weird points

**Solutions:**
1. This shouldn't happen with current settings (only chunking on periods)
2. If it does, increase min_chunk_size:
   ```python
   # In lib/text_to_speech.py
   min_chunk_size: int = 20  # Increase from 15
   ```

### Issue: Not faster than before

**Symptoms:**
- No noticeable speed improvement

**Solutions:**
1. Run `test_parallel_processing.py` to get exact measurements
2. Check if faster-whisper is actually being used
3. Try a completely fresh recording (clear any cached models)
4. Ensure you're testing comparable queries (same complexity)

---

## 📊 Performance Benchmarks

Here are realistic benchmarks you should see:

### Short Command: "How are you Sam?"

**Before:**
```
Speech detection:        75ms
Recording:            2,000ms (user speaking)
Silence wait:         1,500ms
Transcription:        1,000ms
LLM first token:        400ms
First sentence:         600ms
TTS synthesis:          300ms
Playback start:         100ms
─────────────────────────────
TOTAL:                5,975ms
```

**After:**
```
Speech detection:        75ms
Recording:            2,000ms (user speaking)
Silence wait:           750ms ⚡ (faster threshold)
Transcription:          500ms ⚡ (faster-whisper)
LLM first token:        400ms
First sentence:         550ms ⚡ (min_chunk_size=15)
TTS synthesis:          300ms
Playback start:         100ms
─────────────────────────────
TOTAL:                4,675ms ⚡ (-1,300ms / -22%)
```

### Normal Question: "Sam, what's the weather like?"

**Before:** ~6,100ms
**After:** ~5,000ms ⚡ (-1,100ms / -18%)

---

## ✅ Success Criteria

You'll know the optimizations are working if:

1. ✅ Startup shows faster-whisper is being used
2. ✅ Short commands feel noticeably snappier
3. ✅ test_parallel_processing.py shows ~1 second improvement
4. ✅ No accuracy degradation (commands understood correctly)
5. ✅ No speech cutoff issues (dynamic threshold working)
6. ✅ Audio still flows naturally (no choppy pauses)

---

## 🎯 Next Steps After Testing

Once you've confirmed everything works:

1. **Use it normally** for a few days
2. **Note any issues** with speech detection or cutoffs
3. **Fine-tune thresholds** if needed for your speaking style
4. **Consider Phase 2 optimizations** from `FUTURE_OPTIMIZATIONS.md` if you want more speed

---

## 📝 Quick Command Reference

```bash
# Start voice assistant
python main_continuous.py

# Run performance test
python test_parallel_processing.py

# Check faster-whisper installation
python -c "from faster_whisper import WhisperModel; print('✅ OK')"

# Reinstall faster-whisper if needed
pip uninstall faster-whisper
pip install faster-whisper

# Update packages
pip install --upgrade faster-whisper
```

---

## 🆘 Rollback Instructions

If anything doesn't work as expected:

### Disable faster-whisper:
```python
# In main_continuous.py line ~36
stt = SpeechToText(model_size="base", track_metrics=False, use_faster_whisper=False)
```

### Revert dynamic threshold:
```python
# In lib/speech_to_text.py around line 1203
if silence_count > 60:  # Change back to fixed threshold
    print("🔄 Processing speech...")
    self._process_speech_chunk(speech_frames)
```

### Revert min_chunk_size:
```python
# In lib/text_to_speech.py line ~687
min_chunk_size: int = 20  # Change back to 20

# In main_continuous.py line ~109
tts.speak_streaming_async(response_generator, print_text=True)  # Remove min_chunk_size parameter
```

---

## 💡 Tips for Best Results

1. **Speak naturally** - the dynamic threshold adapts to your pace
2. **Pause clearly** at end of questions - helps with detection
3. **Background noise** - keep it minimal for best VAD performance
4. **Test in your typical environment** - different rooms have different acoustics
5. **Monitor the console** - it shows useful timing information

---

**Enjoy your faster voice assistant! 🚀**

Report any issues or unexpected behavior, and we can fine-tune the parameters to your specific needs.
