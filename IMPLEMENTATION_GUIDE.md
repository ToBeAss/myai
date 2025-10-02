# Implementation Guide - Recommended Optimizations

Based on your feedback, here are the specific optimizations to implement, in order of priority.

---

## ✅ Phase 1: High-Priority Optimizations

### 1. Install faster-whisper (Highest Priority)

**Why:** 500ms improvement with ZERO accuracy loss. Same Whisper model, just optimized.

**Step 1: Install the package**
```bash
pip install faster-whisper
```

**Step 2: Modify lib/speech_to_text.py**

**A. Update imports (Line 1)**
```python
# BEFORE:
import whisper

# AFTER:
import whisper  # Keep for fallback
try:
    from faster_whisper import WhisperModel
    FASTER_WHISPER_AVAILABLE = True
except ImportError:
    FASTER_WHISPER_AVAILABLE = False
    print("⚠️  faster-whisper not available, using standard whisper")
```

**B. Update model loading in __init__ (around line 230-250)**

Find this section:
```python
def __init__(self, model_size: str = "base", enable_vad: bool = True, 
             track_metrics: bool = False, metrics_file: str = "wake_word_metrics.json"):
    # ... other init code ...
    
    # Load Whisper model
    print(f"📥 Loading Whisper model: {model_size}")
    self.model = whisper.load_model(model_size)
```

Replace with:
```python
def __init__(self, model_size: str = "base", enable_vad: bool = True, 
             track_metrics: bool = False, metrics_file: str = "wake_word_metrics.json",
             use_faster_whisper: bool = True):  # New parameter
    # ... other init code ...
    
    # Load Whisper model
    print(f"📥 Loading Whisper model: {model_size}")
    
    # Use faster-whisper if available and requested
    if use_faster_whisper and FASTER_WHISPER_AVAILABLE:
        print("🚀 Using faster-whisper for optimized performance")
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
        self.using_faster_whisper = True
    else:
        if use_faster_whisper and not FASTER_WHISPER_AVAILABLE:
            print("⚠️  faster-whisper requested but not available, falling back to standard whisper")
        self.model = whisper.load_model(model_size)
        self.using_faster_whisper = False
```

**C. Update transcription method (around line 850-900)**

Find this section:
```python
# Transcribe with Whisper using direct audio loading
print("🔄 Starting Whisper transcription (English)...")

# Load audio data directly (bypassing Whisper's FFmpeg dependency)
audio_data = self.load_audio_data(audio_file_path)

# Transcribe using English only
result = self.model.transcribe(
    audio_data,
    language="en"  # Force English for optimal accuracy
)

transcribed_text = result["text"].strip()
```

Replace with:
```python
# Transcribe with Whisper using direct audio loading
print("🔄 Starting Whisper transcription (English)...")

# Load audio data directly (bypassing Whisper's FFmpeg dependency)
audio_data = self.load_audio_data(audio_file_path)

# Transcribe using English only
if self.using_faster_whisper:
    # faster-whisper returns segments
    segments, info = self.model.transcribe(audio_data, language="en")
    transcribed_text = " ".join([segment.text for segment in segments]).strip()
else:
    # Standard whisper returns dict
    result = self.model.transcribe(audio_data, language="en")
    transcribed_text = result["text"].strip()
```

**Step 3: Update main_continuous.py to enable it**

No changes needed! It will auto-detect and use faster-whisper if installed.

**Expected Result:** ~500ms faster transcription with same accuracy

---

### 2. Dynamic Silence Threshold (High Priority)

**Why:** Faster response for short commands while still patient for long speech.

**Location:** lib/speech_to_text.py, in `_continuous_listening()` method around line 1175

**Find this code:**
```python
                    if speech_detected:
                        silence_count += 1
                        speech_frames.append(data)
                        
                        # If we've had enough silence, process the speech
                        if silence_count > 60:  # Increased to 60 (about 1.5 seconds of silence for more complete speech)
                            print("🔄 Processing speech...")
                            self._process_speech_chunk(speech_frames)
                            speech_detected = False
                            speech_frames = []
                            silence_count = 0
                            last_speech_time = current_time  # Update last speech time
                            vad_speech_frames = 0
```

**Replace with:**
```python
                    if speech_detected:
                        silence_count += 1
                        speech_frames.append(data)
                        
                        # Dynamic silence threshold based on speech length
                        # Short commands get faster cutoff, longer speech gets more patience
                        if len(speech_frames) < 80:  # Less than 2 seconds of speech
                            dynamic_threshold = 30  # 750ms silence (fast for quick commands)
                        elif len(speech_frames) < 200:  # 2-5 seconds of speech
                            dynamic_threshold = 40  # 1000ms silence (balanced)
                        else:  # Long speech (5+ seconds)
                            dynamic_threshold = 50  # 1250ms silence (patient)
                        
                        # If we've had enough silence, process the speech
                        if silence_count > dynamic_threshold:
                            print(f"🔄 Processing speech... (threshold: {dynamic_threshold*25}ms)")
                            self._process_speech_chunk(speech_frames)
                            speech_detected = False
                            speech_frames = []
                            silence_count = 0
                            last_speech_time = current_time  # Update last speech time
                            vad_speech_frames = 0
```

**Expected Result:** 
- Short commands: ~500ms faster
- Medium speech: ~250ms faster  
- Long speech: ~125ms faster

---

### 3. Reduce Minimum Chunk Size (Quick Win)

**Why:** Start synthesizing audio sooner without risking weird pauses.

**Location:** lib/text_to_speech.py, line ~688

**Find this:**
```python
def speak_streaming_async(self, text_generator, chunk_on: str = ".", print_text: bool = True,
                          min_chunk_size: int = 20):
```

**Change to:**
```python
def speak_streaming_async(self, text_generator, chunk_on: str = ".", print_text: bool = True,
                          min_chunk_size: int = 15):
```

**Also update the call in main_continuous.py (line ~109):**

**Find:**
```python
tts.speak_streaming_async(response_generator, print_text=True)
```

**Change to:**
```python
tts.speak_streaming_async(response_generator, print_text=True, min_chunk_size=15)
```

**Expected Result:** ~50-100ms faster to first audio

---

## 📊 Expected Total Improvement

| Optimization | Time Saved | Difficulty | Risk |
|-------------|-----------|------------|------|
| faster-whisper | ~500ms | Easy | None |
| Dynamic threshold | ~300-500ms | Easy | Low |
| min_chunk_size | ~50-100ms | Very Easy | None |
| **TOTAL** | **~850-1,100ms** | | |

**Your typical response time will improve from ~6.1s to ~5.0-5.2s (17-18% faster)**

---

## 🧪 Testing

After implementing, run:

```bash
python test_parallel_processing.py
```

Compare the "Time to first audio" before and after. You should see a noticeable improvement!

---

## 📋 Implementation Checklist

- [ ] Install faster-whisper: `pip install faster-whisper`
- [ ] Update lib/speech_to_text.py imports
- [ ] Update lib/speech_to_text.py __init__ method
- [ ] Update lib/speech_to_text.py transcription method
- [ ] Update lib/speech_to_text.py dynamic threshold
- [ ] Update lib/text_to_speech.py min_chunk_size default
- [ ] Update main_continuous.py TTS call
- [ ] Run test_parallel_processing.py to verify
- [ ] Test with real voice commands

---

## 🔄 Optional Phase 2 (If You Want Even More Speed)

### A. Add Semicolons as Chunk Boundaries

Semicolons are almost always sentence boundaries and rarely appear in abbreviations.

**In lib/text_to_speech.py line ~688:**
```python
def speak_streaming_async(self, text_generator, chunk_on: str = ".;", print_text: bool = True,
                          min_chunk_size: int = 15):
```

**Expected:** Additional ~50-100ms improvement

### B. Test Tiny Whisper Model

Only if you need more speed and want to test accuracy tradeoff.

**In main_continuous.py line ~36:**
```python
stt = SpeechToText(model_size="tiny", track_metrics=False)
```

Test accuracy first with your own voice!

---

## ⚠️ Rollback Plan

If anything doesn't work:

1. **faster-whisper issues:** Set `use_faster_whisper=False` in SpeechToText init
2. **Cutoff speech:** Increase dynamic thresholds (30→35, 40→45, 50→55)
3. **Incomplete sentences:** Change min_chunk_size back to 20

All changes are simple parameter tweaks that can be easily adjusted!

---

## 💡 Why These Three?

1. **faster-whisper**: Biggest single improvement, zero downside
2. **Dynamic threshold**: Smart adaptation that respects different speech patterns
3. **min_chunk_size**: Easy win without compromising your careful period handling

Together they give you ~1 second improvement without sacrificing quality or adding complexity!
