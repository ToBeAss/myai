# Processing Time Analysis & Latency Optimization Guide

## 📊 Current Processing Pipeline

### Complete Interaction Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    1. SPEECH DETECTION                          │
│  • Continuous audio monitoring (25ms chunks)                    │
│  • Volume threshold check (STAGE 1: Fast pre-filter)            │
│  • VAD verification (STAGE 2: Accurate speech detection)        │
│  • Requires 3 consecutive VAD-confirmed frames (~75ms)          │
│  ⏱️  Latency: ~75-100ms (detection lag)                         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    2. AUDIO RECORDING                           │
│  • Buffering speech frames in memory                            │
│  • Waiting for 1.5s of silence (60 frames @ 25ms)               │
│  • OR max recording duration (15s)                              │
│  ⏱️  Latency: Variable (user-dependent, typically 2-5s)         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    3. SPEECH PROCESSING                         │
│  • Write audio buffer to temporary WAV file                     │
│  • Load audio data (resampling if needed to 16kHz)              │
│  • Run Whisper transcription (base model, English only)         │
│  • Hallucination detection check                                │
│  • Wake word detection & confidence scoring                     │
│  ⏱️  Latency: ~500ms - 2s (depends on audio length)             │
│                                                                  │
│  Breakdown:                                                      │
│    - File I/O: ~50-100ms                                        │
│    - Whisper transcription: 400ms - 1.8s                        │
│    - Wake word analysis: ~10-20ms                               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    4. LLM STREAMING                             │
│  • Structure prompt with memory & tools                         │
│  • Send request to OpenAI/Azure                                 │
│  • Stream tokens back as they arrive                            │
│  ⏱️  Latency:                                                    │
│    - Time to first token: ~200-600ms                            │
│    - Token generation: ~50-100 tokens/sec                       │
│                                                                  │
│  Network factors:                                                │
│    - API latency: 100-300ms                                     │
│    - Streaming overhead: ~50-150ms per chunk                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    5. TTS SYNTHESIS (Parallel)                  │
│  • Buffer accumulates text until sentence boundary              │
│  • Minimum chunk size: 20 characters                            │
│  • Parallel synthesis worker thread                             │
│  • Google TTS API synthesis                                     │
│  ⏱️  Latency:                                                    │
│    - First sentence detection: Variable (20+ chars)             │
│    - TTS API call: ~200-500ms per sentence                      │
│    - Audio file creation: ~50-100ms                             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    6. AUDIO PLAYBACK (Parallel)                 │
│  • Separate playback worker thread                              │
│  • Queue-based architecture (synthesis → playback)              │
│  • pygame mixer for audio playback                              │
│  ⏱️  Latency:                                                    │
│    - Playback initialization: ~50-100ms                         │
│    - Audio duration: Variable (sentence-dependent)              │
│    - Cleanup: ~10-20ms per file                                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    7. COMPLETION                                │
│  • All synthesis and playback queues empty                      │
│  • Conversation timer starts (5s for follow-ups)                │
│  • System returns to listening state                            │
└─────────────────────────────────────────────────────────────────┘
```

## 🔍 Detailed Latency Breakdown

### Total Time from Speech to First Audio Output

**Optimistic Case (Short question, quick response):**
```
Speech Detection:         ~100ms
Recording:              ~2,000ms (user speaks for ~2s)
Transcription:            ~500ms
LLM First Token:          ~300ms
First Sentence Buffer:    ~200ms (time to accumulate first sentence)
TTS Synthesis:            ~300ms
Playback Start:           ~100ms
─────────────────────────────────
TOTAL:                  ~3,500ms (3.5 seconds)
```

**Realistic Case (Normal question):**
```
Speech Detection:         ~100ms
Recording:              ~3,500ms (user speaks for ~3.5s)
Transcription:          ~1,000ms
LLM First Token:          ~500ms
First Sentence Buffer:    ~500ms (time to accumulate first sentence)
TTS Synthesis:            ~400ms
Playback Start:           ~100ms
─────────────────────────────────
TOTAL:                  ~6,100ms (6.1 seconds)
```

**Pessimistic Case (Long question or slow LLM):**
```
Speech Detection:         ~100ms
Recording:              ~5,000ms (user speaks for ~5s)
Transcription:          ~2,000ms
LLM First Token:        ~1,000ms
First Sentence Buffer:  ~1,000ms (slow token generation)
TTS Synthesis:            ~500ms
Playback Start:           ~100ms
─────────────────────────────────
TOTAL:                  ~9,700ms (9.7 seconds)
```

## 🚀 Optimization Strategies

### 1. Speech Detection Optimization (Target: -20-30ms)

**Current Bottleneck:**
- 3 consecutive VAD frames required (~75ms)
- 25ms chunks with 10ms sleep between iterations

**Improvements:**
```python
# In lib/speech_to_text.py, _continuous_listening()

# Option A: Reduce VAD requirement (trade accuracy for speed)
vad_required_frames = 2  # Change from 3 → saves ~25ms

# Option B: Increase chunk size (process more audio at once)
self.chunk = 512  # Change from 400 → saves ~10-15ms
# Note: Larger chunks = less granular detection

# Option C: Remove sleep in listening loop (use 100% CPU)
# time.sleep(0.01)  # Comment out → saves ~10ms per iteration
# Warning: Increases CPU usage significantly
```

**Recommended:** Use Option A (reduce to 2 frames) for ~25ms improvement.

### 2. Recording Optimization (Target: -300-500ms)

**Current Bottleneck:**
- Waiting for 1.5 seconds of silence (60 frames)
- Conservative to ensure complete utterances

**Improvements:**
```python
# In lib/speech_to_text.py, _continuous_listening()

# Option A: Reduce silence threshold (more aggressive)
if silence_count > 40:  # Change from 60 → saves ~500ms
    # Reduced from 1.5s to 1.0s of silence
    print("🔄 Processing speech...")
    
# Option B: Dynamic silence threshold based on speech length
min_silence = 30  # 750ms minimum
max_silence = 60  # 1.5s maximum
silence_threshold = min(max_silence, min_silence + len(speech_frames) // 100)
# Shorter utterances → quicker cutoff

# Option C: Use VAD-based end-of-speech detection
# Already partially implemented, but could be more aggressive
```

**Recommended:** Use Option A (reduce to 40 frames = 1.0s) for ~500ms improvement.
**Risk:** May cut off slow speakers. Consider making this configurable.

### 3. Transcription Optimization (Target: -200-500ms)

**Current Bottleneck:**
- Using Whisper "base" model (slower but more accurate)
- File I/O overhead
- Resampling operations

**Improvements:**
```python
# Option A: Use faster Whisper model
stt = SpeechToText(model_size="tiny", track_metrics=False)
# tiny: ~2-3x faster than base, slight accuracy loss
# base: Current (good balance)
# small: ~2x slower, better accuracy

# Option B: Use Whisper.cpp or faster-whisper
# Requires installation: pip install faster-whisper
# Can be 4-5x faster with same accuracy

# Option C: Use streaming Whisper (WhisperLive)
# Start transcription before recording completes
# Requires significant refactoring

# Option D: Remove file I/O overhead
# Already partially optimized (direct numpy array)
# Could use in-memory buffer entirely
```

**Recommended:** 
1. Try "tiny" model first (easiest, ~200ms improvement)
2. If accuracy acceptable, install faster-whisper for ~500ms improvement

```bash
# Install faster-whisper
pip install faster-whisper

# Modify lib/speech_to_text.py
from faster_whisper import WhisperModel

# In __init__:
self.model = WhisperModel(model_size, device="cpu", compute_type="int8")

# In transcribe_audio:
segments, info = self.model.transcribe(audio_data, language="en")
transcribed_text = " ".join([segment.text for segment in segments]).strip()
```

### 4. LLM Streaming Optimization (Target: -100-300ms)

**Current Bottleneck:**
- Time to first token from OpenAI/Azure
- Prompt size affects latency
- Network latency

**Improvements:**
```python
# Option A: Reduce prompt size
# In lib/agent.py, _structure_prompt()
# Trim conversation history more aggressively
if self._memory:
    conversation_history = self._memory.retrieve_memory()[-5:]  # Last 5 only
    
# Option B: Use lower latency model
# gpt-4.1-mini → already fast
# Could try gpt-3.5-turbo for even faster responses

# Option C: Implement prompt caching
# For repeated instructions/context

# Option D: Pre-warm connection with health check
# Send dummy request on startup to establish connection

# Option E: Parallel API calls
# Not applicable for streaming responses
```

**Recommended:** 
1. Reduce conversation history to last 5 messages (~50-100ms)
2. Add connection pre-warming on startup (~100-200ms saved on first call)

### 5. TTS Optimization (Target: -100-300ms)

**Current Bottleneck:**
- Waiting for first complete sentence (min 20 chars)
- Google TTS API synthesis latency
- Sequential sentence processing

**Improvements:**
```python
# In lib/text_to_speech.py, speak_streaming_async()

# Option A: Reduce minimum chunk size
min_chunk_size: int = 10  # Change from 20 → saves ~100-200ms

# Option B: Start synthesis on partial sentences
# Look for commas, semicolons, not just periods
chunk_on: str = ".,;:"  # More boundaries

# Option C: Use faster TTS service
# Google Chirp3-HD is slower but higher quality
# Switch to Wavenet or Standard for faster synthesis
voice_name="en-GB-Wavenet-A",  # Faster than Chirp3-HD

# Option D: Implement TTS caching for common phrases
# Cache "Hi!", "I don't know", etc.

# Option E: Use local TTS (piper, coqui)
# Instant synthesis, no API latency
# Requires installation and model download
```

**Recommended:**
1. Reduce min_chunk_size to 15 characters (~50-100ms)
2. Add commas to chunk boundaries (~100-200ms)
3. Consider Wavenet instead of Chirp3-HD (~100ms per synthesis)

```python
# In main_continuous.py
tts = TextToSpeech(
    voice_name="en-GB-Wavenet-A",  # Faster than Chirp3-HD
    language_code="en-GB",
    speaking_rate=1.1,
    pitch=0.0,
    enforce_free_tier=True,
    fallback_voice="en-GB-Standard-A"  # Even faster fallback
)

# In lib/text_to_speech.py
def speak_streaming_async(self, text_generator, chunk_on: str = ".,;", 
                          print_text: bool = True, min_chunk_size: int = 15):
```

### 6. Parallel Processing Verification

**Current Implementation:**
- ✅ TTS synthesis runs in separate thread (synthesis_worker)
- ✅ Audio playback runs in separate thread (playback_worker)
- ✅ LLM streaming continues while TTS processes

**Potential Issue:** The system appears to be working correctly, but the perception might be off due to:
1. First sentence buffer delay (waiting for complete sentence)
2. TTS synthesis latency for first chunk
3. Slow token generation rate

## 🧪 Testing Parallel Processing

To verify parallel processing is working correctly, add timing instrumentation:

```python
# Create this test file: test_parallel_tts.py

import time
from lib.llm_wrapper import LLM_Wrapper
from lib.agent import Agent
from lib.memory import Memory
from lib.text_to_speech import TextToSpeech

def test_streaming_with_timing():
    """Test to verify parallel TTS processing with detailed timing."""
    
    llm = LLM_Wrapper(model_name="openai-gpt-4.1-mini")
    memory = Memory(history_limit=10)
    myai = Agent(llm=llm, memory=memory, agent_name="Sam", 
                 description="Test agent for timing analysis")
    
    tts = TextToSpeech(
        voice_name="en-GB-Wavenet-A",
        language_code="en-GB",
        speaking_rate=1.1,
        pitch=0.0
    )
    
    # Instrumented text generator wrapper
    class TimedGenerator:
        def __init__(self, generator):
            self.generator = generator
            self.start_time = time.time()
            self.first_token_time = None
            self.token_times = []
            
        def __iter__(self):
            for token in self.generator:
                current_time = time.time()
                if self.first_token_time is None:
                    self.first_token_time = current_time - self.start_time
                    print(f"\n⏱️  FIRST TOKEN: {self.first_token_time*1000:.0f}ms")
                
                elapsed = current_time - self.start_time
                self.token_times.append(elapsed)
                yield token
    
    # Instrumented TTS wrapper
    original_synthesize = tts.synthesize_to_file
    synthesis_times = []
    
    def timed_synthesize(text, filename):
        start = time.time()
        result = original_synthesize(text, filename)
        duration = (time.time() - start) * 1000
        synthesis_times.append({
            'text': text[:50] + ('...' if len(text) > 50 else ''),
            'duration': duration,
            'time_from_start': (time.time() - test_start) * 1000
        })
        print(f"\n🎵 SYNTHESIZED: '{text[:30]}...' in {duration:.0f}ms")
        return result
    
    tts.synthesize_to_file = timed_synthesize
    
    # Run test
    print("\n" + "="*70)
    print("🧪 PARALLEL PROCESSING TEST")
    print("="*70)
    print("\nAsking: 'Tell me a short story about a robot.'\n")
    
    test_start = time.time()
    response_generator = myai.stream(user_input="Tell me a short story about a robot.")
    timed_gen = TimedGenerator(response_generator)
    
    print("🤖: ", end="", flush=True)
    tts.speak_streaming_async(timed_gen, print_text=True, min_chunk_size=15)
    
    total_time = (time.time() - test_start) * 1000
    
    print("\n\n" + "="*70)
    print("📊 TIMING ANALYSIS")
    print("="*70)
    print(f"\n⏱️  Total Time: {total_time:.0f}ms ({total_time/1000:.1f}s)")
    print(f"⏱️  First Token: {timed_gen.first_token_time*1000:.0f}ms")
    print(f"⏱️  Token Count: {len(timed_gen.token_times)}")
    print(f"⏱️  Avg Token Interval: {(timed_gen.token_times[-1] - timed_gen.first_token_time) / len(timed_gen.token_times) * 1000:.0f}ms")
    
    print(f"\n🎵 TTS Synthesis Events:")
    for i, synth in enumerate(synthesis_times, 1):
        print(f"  {i}. [{synth['time_from_start']:.0f}ms] Synthesized '{synth['text']}' in {synth['duration']:.0f}ms")
    
    print(f"\n✅ Total Synthesis Calls: {len(synthesis_times)}")
    print(f"✅ Avg Synthesis Time: {sum(s['duration'] for s in synthesis_times) / len(synthesis_times):.0f}ms")
    
    # Check for overlap
    if len(synthesis_times) >= 2:
        first_synth_end = synthesis_times[0]['time_from_start'] + synthesis_times[0]['duration']
        token_gen_end = timed_gen.token_times[-1] * 1000
        
        if first_synth_end < token_gen_end:
            print(f"\n✅ PARALLEL PROCESSING CONFIRMED!")
            print(f"   First synthesis completed at {first_synth_end:.0f}ms")
            print(f"   Token generation continued until {token_gen_end:.0f}ms")
            print(f"   Overlap: {token_gen_end - first_synth_end:.0f}ms")
        else:
            print(f"\n⚠️  NO OVERLAP DETECTED - May be sequential")
    
    print("="*70 + "\n")

if __name__ == "__main__":
    test_streaming_with_timing()
```

Run this test:
```bash
python test_parallel_tts.py
```

This will show you:
1. ✅ Time to first LLM token
2. ✅ When each TTS synthesis starts/completes
3. ✅ Whether synthesis happens in parallel with token generation
4. ✅ Total latency breakdown

## 📝 Summary of Recommended Changes

### Quick Wins (Low Risk, High Impact)
1. **Reduce silence threshold**: 60 → 40 frames (~500ms saved)
2. **Reduce min_chunk_size**: 20 → 15 characters (~100ms saved)
3. **Add comma boundaries**: chunk_on=".," (~100-200ms saved)
4. **Switch to Wavenet voice**: Chirp3-HD → Wavenet-A (~100ms per synth)
5. **Reduce conversation history**: Keep last 5 messages only (~50-100ms)

**Total Expected Improvement: ~850-1,350ms (1-1.5 seconds faster)**

### Medium Wins (Moderate Risk, Good Impact)
1. **Use "tiny" Whisper model** (~200ms saved, slight accuracy loss)
2. **Reduce VAD frames**: 3 → 2 frames (~25ms saved)
3. **Install faster-whisper** (~500ms saved, requires new dependency)

**Total Expected Improvement: ~725ms additional**

### Advanced Optimizations (High Effort, High Impact)
1. **Implement streaming Whisper** (transcribe while recording)
2. **Use local TTS** (Piper/Coqui for instant synthesis)
3. **Parallel API calls with fallback** (multiple LLM providers)
4. **Implement prompt caching** (reduce LLM processing)

**Total Expected Improvement: ~2-3 seconds additional**

## 🎯 Target Latency Goals

**Current Performance:**
- Typical interaction: ~6.1 seconds from speech to audio
- First response: ~3.5-9.7 seconds

**After Quick Wins:**
- Typical interaction: ~4.7 seconds (-1.4s / -23%)
- First response: ~2.5-8.0 seconds

**After Medium Wins:**
- Typical interaction: ~4.0 seconds (-2.1s / -34%)
- First response: ~2.0-7.3 seconds

**After Advanced Optimizations:**
- Typical interaction: ~2.0 seconds (-4.1s / -67%)
- First response: ~1.0-5.0 seconds

This would make the system feel significantly more responsive and conversational!
