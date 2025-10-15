# Pipeline Benchmarking System Design

⚠️ **STATUS: DESIGN DOCUMENT - READY FOR IMPLEMENTATION** ⚠️

**Design Date:** October 15, 2025  
**Purpose:** Measure end-to-end pipeline performance and identify optimization opportunities  
**Priority Metric:** Time to First Sound (perceived system responsiveness)

---

## 🎯 Core Objectives

### Primary Goal: Time to First Sound
**The most critical metric for user experience.**

When a user finishes speaking, how long until they hear the AI start responding? This metric determines whether the system feels "alive" and natural like human conversation.

### Secondary Goals:
1. **Identify bottlenecks** - Which component is the slowest?
2. **Compare approaches** - Chunked vs non-chunked transcription
3. **Track improvements** - Historical comparison of optimizations
4. **Real-world accuracy** - Use actual recorded audio and live API calls

---

## 📊 Pipeline Components to Measure

### Complete Pipeline Flow

```
User Speech → STT Chunks → LLM Streaming → TTS Chunks → Audio Playback
     ↓            ↓              ↓              ↓            ↓
   [Time]      [Time]         [TTFT]        [TTFA]     [Perceived]
```

### Detailed Measurement Points

#### 1. Speech-to-Text (STT)
```
Audio Input
  ↓
┌─────────────────────────────────────────┐
│ STT Component                            │
├─────────────────────────────────────────┤
│ • Audio loading time                     │
│ • VAD chunk detection (if chunked)      │
│ • Per-chunk transcription times          │
│ • First chunk completion (CRITICAL)     │
│ • Total transcription time               │
└─────────────────────────────────────────┘
```

**Key Insights:**
- **Current chunking:** 300ms silence triggers chunk boundary (line 1428 in speech_to_text.py)
- **Chunked mode:** Processes while user is still speaking
- **Non-chunked mode:** Waits for complete audio before processing

#### 2. LLM Generation
```
Transcription Complete
  ↓
┌─────────────────────────────────────────┐
│ LLM Component                            │
├─────────────────────────────────────────┤
│ • Time to First Token (TTFT) - CRITICAL │
│ • Token generation rate (tokens/sec)     │
│ • Per-token timing                       │
│ • Total generation time                  │
│ • Number of tokens generated             │
└─────────────────────────────────────────┘
```

**Key Insights:**
- Streaming mode allows TTS to start before completion
- TTFT is the bottleneck for perceived responsiveness
- Token rate determines how smoothly TTS can chunk

#### 3. Text-to-Speech (TTS)
```
LLM Token Stream
  ↓
┌─────────────────────────────────────────┐
│ TTS Component                            │
├─────────────────────────────────────────┤
│ • Time to First Audio (TTFA) - CRITICAL │
│ • Per-chunk synthesis times              │
│ • Chunk detection timing                 │
│ • Parallel synthesis queue depth         │
│ • Total synthesis time                   │
└─────────────────────────────────────────┘
```

**Key Insights:**
- **Current chunking:** Splits on `",.!?—"` with min 30 chars (main_continuous.py line 121)
- **Smart chunking:** Avoids splitting decimals, abbreviations, lists
- **Parallel processing:** Synthesizes next chunk while playing current
- **Multiple chunks critical:** Each chunk needs timing measurement

#### 4. Audio Playback
```
TTS Audio Ready
  ↓
┌─────────────────────────────────────────┐
│ Playback Component                       │
├─────────────────────────────────────────┤
│ • Time to first playback start           │
│ • Per-chunk playback start times         │
│ • Playback durations                     │
│ • Queue management overhead              │
└─────────────────────────────────────────┘
```

---

## 🔬 Critical Metrics Definitions

### User Perception Metrics

#### 1. Time to First Sound (TTFS) ⭐⭐⭐⭐⭐
**Most Important Metric**

```
TTFS = (User Stops Speaking) → (AI Starts Speaking)

Components:
  STT First Chunk Time
  + LLM Time to First Token (TTFT)  
  + TTS Time to First Audio (TTFA)
  + Audio Playback Start Overhead
```

**Target:** < 500ms feels natural (like human conversation)
- < 300ms: Exceptional (instant response feeling)
- 300-500ms: Great (very natural)
- 500-800ms: Good (acceptable)
- 800-1200ms: Noticeable lag
- \> 1200ms: Feels slow

#### 2. Total Response Time
**Secondary Importance** (user is already engaged)

```
Total Time = TTFS + (Remaining Audio Duration)
```

Once the AI starts talking, users will listen. This is less critical for perceived responsiveness.

### Optimization Metrics

#### 3. Component Breakdown
Percentage of total time spent in each component:

```
STT:  X% of total time
LLM:  Y% of total time  
TTS:  Z% of total time
```

**Bottleneck identification:** Component with highest percentage needs optimization first.

#### 4. Chunking Efficiency
**Chunked vs Non-Chunked Comparison:**

```
Chunked Approach:
  - Starts processing during user speech
  - Multiple smaller transcription tasks
  - Potential early LLM start

Non-Chunked Approach:
  - Single transcription after user finishes
  - One larger transcription task
  - Simpler implementation
```

---

## 🎤 Test Audio Requirements

### Recording Strategy

**Use real recordings for authenticity:**

1. **Record yourself** with actual wake word and natural speech patterns
2. **Multiple test scenarios** covering different use cases
3. **Natural pauses** that would trigger 300ms chunking in live mode
4. **Consistent environment** (same room, microphone, background noise)

### Test Suite Categories

#### Category 1: Speed Tests
**Focus: Time to First Sound optimization**

```yaml
short_weather:
  duration: ~3 seconds
  text: "Hey Sam, what's the weather?"
  expected_chunks: 1
  focus: Minimal latency baseline
  
short_time:
  duration: ~2 seconds
  text: "Hey Sam, what time is it?"
  expected_chunks: 1
  focus: Fastest possible response
```

#### Category 2: Chunking Tests
**Focus: Multi-chunk transcription efficiency**

```yaml
medium_timer:
  duration: ~5 seconds
  text: "Hey Sam, set a timer for 15 minutes and remind me to check the laundry"
  expected_chunks: 2-3
  focus: Natural pause handling
  
long_with_pauses:
  duration: ~8 seconds
  text: "Hey Sam, can you tell me... what the weather forecast is... for tomorrow?"
  expected_chunks: 3-4
  focus: Multiple chunk boundaries
```

#### Category 3: Complexity Tests
**Focus: System under realistic load**

```yaml
long_explanation:
  duration: ~10 seconds
  text: "Hey Sam, can you explain quantum entanglement in simple terms?"
  expected_chunks: 2-3
  focus: Long LLM response, multiple TTS chunks
  
complex_with_numbers:
  duration: ~7 seconds
  text: "Hey Sam, what's 15 times 23.5 plus 142?"
  expected_chunks: 2
  focus: Number handling, calculation tool
```

### Recording Script Template

```python
# record_benchmark_audio.py
import sounddevice as sd
import numpy as np
import wave
import os

def record_benchmark_audio(name: str, duration: int, description: str):
    """
    Record test audio for benchmarking.
    
    :param name: Test name (e.g., 'short_weather')
    :param duration: Recording duration in seconds
    :param description: What to say
    """
    print(f"\n🎤 Recording: {name}")
    print(f"📝 Say: {description}")
    print(f"⏱️  Duration: {duration} seconds")
    
    input("\nPress Enter when ready to record...")
    
    print("🔴 Recording...")
    audio = sd.rec(
        int(duration * 16000),
        samplerate=16000,
        channels=1,
        dtype=np.float32
    )
    sd.wait()
    print("✅ Recording complete!")
    
    # Save to tests/audio/
    os.makedirs('tests/audio', exist_ok=True)
    filepath = f'tests/audio/{name}.wav'
    
    with wave.open(filepath, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        audio_int16 = (audio * 32767).astype(np.int16)
        wf.writeframes(audio_int16.tobytes())
    
    print(f"💾 Saved to: {filepath}\n")
    return filepath

# Create test suite
TEST_SUITE = [
    ('short_weather', 4, "Hey Sam, what's the weather?"),
    ('short_time', 3, "Hey Sam, what time is it?"),
    ('medium_timer', 6, "Hey Sam, set a timer for 15 minutes and remind me to check the laundry"),
    ('long_explanation', 10, "Hey Sam, can you explain quantum entanglement in simple terms?"),
]

if __name__ == "__main__":
    print("="*70)
    print("🎙️  BENCHMARK AUDIO RECORDING SUITE")
    print("="*70)
    
    for name, duration, text in TEST_SUITE:
        record_benchmark_audio(name, duration, text)
    
    print("✅ All test recordings complete!")
```

---

## 🔧 Implementation Design

### Architecture Overview

```python
# benchmark_pipeline.py

import time
import json
import wave
import numpy as np
from pathlib import Path
from contextlib import contextmanager
from typing import Dict, List, Any

@contextmanager
def timer(label: str, timings: dict):
    """Precise timing context manager."""
    start = time.perf_counter()
    yield
    elapsed = time.perf_counter() - start
    timings[label] = elapsed

class PipelineBenchmark:
    """
    Complete pipeline benchmarking system.
    
    Measures every component from user speech to AI audio playback,
    with focus on Time to First Sound as the primary UX metric.
    """
    
    def __init__(self, test_audio_file: str, save_results: bool = False):
        self.audio_file = test_audio_file
        self.save_results = save_results
        self.results = {}
        
        # Initialize components (same as production)
        from lib.speech_to_text import SpeechToText
        from lib.text_to_speech import TextToSpeech
        from lib.llm_wrapper import LLM_Wrapper
        from lib.agent import Agent
        from lib.memory import Memory
        
        self.stt = SpeechToText(
            model_size="base",
            use_faster_whisper=True,
            track_metrics=False
        )
        
        self.tts = TextToSpeech(
            voice_name="en-GB-Chirp3-HD-Achernar",
            language_code="en-GB",
            speaking_rate=1.1,
            pitch=0.0
        )
        
        self.llm = LLM_Wrapper(model_name="openai-gpt-4.1-mini")
        self.memory = Memory(history_limit=10)
        self.agent = Agent(
            llm=self.llm,
            memory=self.memory,
            agent_name="Sam",
            description="Benchmark test agent"
        )
    
    def run_full_benchmark(self) -> Dict[str, Any]:
        """
        Run complete benchmark suite.
        
        Returns comprehensive timing data for analysis.
        """
        print("\n" + "="*70)
        print(f"🔬 PIPELINE BENCHMARK: {Path(self.audio_file).name}")
        print("="*70)
        
        # Test both approaches
        print("\n📦 Benchmarking CHUNKED transcription...")
        chunked_results = self.benchmark_chunked_pipeline()
        
        print("\n📄 Benchmarking NON-CHUNKED transcription...")
        non_chunked_results = self.benchmark_non_chunked_pipeline()
        
        # Analysis
        print("\n📊 Analysis...")
        self.compare_approaches(chunked_results, non_chunked_results)
        self.analyze_bottlenecks(chunked_results)
        self.print_summary(chunked_results)
        
        # Save if requested
        if self.save_results:
            self.save_to_csv(chunked_results, non_chunked_results)
        
        return {
            'chunked': chunked_results,
            'non_chunked': non_chunked_results
        }
```

### Chunked Pipeline Implementation

```python
def benchmark_chunked_pipeline(self) -> Dict[str, Any]:
    """
    Benchmark with chunked transcription (production mode).
    
    This simulates live chunking by detecting natural 300ms pauses
    in the audio file using VAD.
    """
    timings = {}
    benchmark_start = time.perf_counter()
    
    # ============================================
    # PHASE 1: AUDIO LOADING & CHUNK DETECTION
    # ============================================
    
    print("  📂 Loading audio file...")
    with timer('audio_load', timings):
        audio_data, sample_rate = self.load_audio_file(self.audio_file)
    
    print(f"     Duration: {len(audio_data)/sample_rate:.2f}s")
    
    print("  🔍 Detecting natural chunks (300ms pause threshold)...")
    with timer('chunk_detection', timings):
        chunks = self.detect_natural_chunks(audio_data, sample_rate)
    
    print(f"     Found {len(chunks)} chunks")
    for i, (start, end) in enumerate(chunks):
        print(f"       Chunk {i+1}: {start:.2f}s - {end:.2f}s ({end-start:.2f}s)")
    
    # ============================================
    # PHASE 2: SPEECH-TO-TEXT (CHUNKED)
    # ============================================
    
    print("\n  🎤 Transcribing chunks...")
    chunk_timings = []
    transcriptions = []
    
    stt_start = time.perf_counter()
    
    for i, (start, end) in enumerate(chunks):
        chunk_audio = self.extract_chunk(audio_data, start, end, sample_rate)
        
        chunk_start_time = time.perf_counter()
        text = self.stt.transcribe_audio(chunk_audio)
        chunk_duration = time.perf_counter() - chunk_start_time
        
        chunk_timings.append(chunk_duration)
        transcriptions.append(text)
        
        print(f"     Chunk {i+1}: {chunk_duration*1000:.0f}ms → '{text}'")
        
        if i == 0:
            timings['stt_first_chunk'] = chunk_duration
            print(f"       ⭐ FIRST CHUNK COMPLETE: {chunk_duration*1000:.0f}ms")
    
    timings['stt_total'] = time.perf_counter() - stt_start
    timings['stt_per_chunk'] = chunk_timings
    timings['stt_num_chunks'] = len(chunks)
    
    full_transcription = " ".join(transcriptions)
    print(f"\n  📝 Full transcription: {full_transcription}")
    
    # ============================================
    # PHASE 3: LLM GENERATION (STREAMING)
    # ============================================
    
    print("\n  🤖 Generating LLM response...")
    
    llm_start = time.perf_counter()
    response_generator = self.agent.stream(user_input=full_transcription)
    
    tokens = []
    token_times = []
    ttft_recorded = False
    
    for token in response_generator:
        current_time = time.perf_counter() - llm_start
        
        if not ttft_recorded:
            timings['llm_ttft'] = current_time
            print(f"     ⭐ FIRST TOKEN: {current_time*1000:.0f}ms")
            ttft_recorded = True
        
        tokens.append(token.content if hasattr(token, 'content') else str(token))
        token_times.append(current_time)
    
    timings['llm_total'] = time.perf_counter() - llm_start
    timings['llm_tokens'] = len(tokens)
    timings['llm_tokens_per_sec'] = len(tokens) / timings['llm_total'] if timings['llm_total'] > 0 else 0
    
    response_text = "".join(tokens)
    print(f"     Generated {len(tokens)} tokens in {timings['llm_total']*1000:.0f}ms")
    print(f"     Rate: {timings['llm_tokens_per_sec']:.1f} tokens/sec")
    print(f"  💬 Response: {response_text[:100]}...")
    
    # ============================================
    # PHASE 4: TEXT-TO-SPEECH (STREAMING/CHUNKED)
    # ============================================
    
    print("\n  🔊 Synthesizing speech (chunked)...")
    
    # Instrument TTS to capture per-chunk timings
    tts_chunks = []
    tts_chunk_times = []
    ttfa_recorded = False
    
    def timed_token_generator():
        """Wrap token generator to measure TTS chunking."""
        for i, token in enumerate(tokens):
            yield token
    
    tts_start = time.perf_counter()
    
    # Simulate TTS chunking (detect where it splits on ",.!?—")
    tts_text_chunks = self.simulate_tts_chunking(response_text)
    
    for i, chunk_text in enumerate(tts_text_chunks):
        chunk_start = time.perf_counter()
        
        # Synthesize chunk
        audio_file = self.tts.synthesize_to_file(chunk_text, f'temp_tts_chunk_{i}.mp3')
        
        chunk_duration = time.perf_counter() - chunk_start
        tts_chunk_times.append(chunk_duration)
        tts_chunks.append({
            'text': chunk_text[:50] + ('...' if len(chunk_text) > 50 else ''),
            'duration': chunk_duration,
            'char_count': len(chunk_text)
        })
        
        if not ttfa_recorded:
            timings['tts_first_audio'] = time.perf_counter() - tts_start
            print(f"     ⭐ FIRST AUDIO READY: {timings['tts_first_audio']*1000:.0f}ms")
            ttfa_recorded = True
        
        print(f"     Chunk {i+1}: {chunk_duration*1000:.0f}ms → '{chunk_text[:40]}...'")
    
    timings['tts_total'] = time.perf_counter() - tts_start
    timings['tts_num_chunks'] = len(tts_chunks)
    timings['tts_per_chunk'] = tts_chunk_times
    
    # ============================================
    # PHASE 5: CALCULATE KEY METRICS
    # ============================================
    
    # ⭐⭐⭐ MOST IMPORTANT METRIC ⭐⭐⭐
    timings['time_to_first_sound'] = (
        timings['stt_first_chunk'] +
        timings['llm_ttft'] +
        timings['tts_first_audio']
    )
    
    timings['total_pipeline'] = (
        timings['stt_total'] +
        timings['llm_total'] +
        timings['tts_total']
    )
    
    timings['benchmark_overhead'] = time.perf_counter() - benchmark_start - timings['total_pipeline']
    
    return {
        'timings': timings,
        'transcription': full_transcription,
        'response': response_text,
        'tts_chunks': tts_chunks,
        'approach': 'chunked'
    }
```

### Key Helper Methods

```python
def detect_natural_chunks(self, audio_data: np.ndarray, sample_rate: int) -> List[tuple]:
    """
    Detect where audio WOULD chunk during live recording.
    
    Uses same 300ms silence threshold as production (speech_to_text.py line 1428).
    Uses VAD to identify speech vs silence.
    
    :return: List of (start_time, end_time) tuples in seconds
    """
    import webrtcvad
    
    vad = webrtcvad.Vad(aggressiveness=2)  # Match production setting
    
    chunks = []
    current_chunk_start = 0
    silence_count = 0
    
    # VAD requires 10, 20, or 30ms frames at 8/16/32/48kHz
    frame_duration_ms = 30
    frame_duration_sec = frame_duration_ms / 1000.0
    frame_length = int(sample_rate * frame_duration_sec)
    
    # 300ms = 10 frames of 30ms
    SILENCE_THRESHOLD_FRAMES = 10
    
    # Process audio in frames
    for i in range(0, len(audio_data), frame_length):
        frame = audio_data[i:i+frame_length]
        
        if len(frame) < frame_length:
            break  # Skip incomplete final frame
        
        # Convert float32 to int16 for VAD
        frame_int16 = (frame * 32767).astype(np.int16)
        frame_bytes = frame_int16.tobytes()
        
        # Check if frame contains speech
        is_speech = vad.is_speech(frame_bytes, sample_rate)
        
        if not is_speech:
            silence_count += 1
            
            # If silence exceeds 300ms, mark chunk boundary
            if silence_count >= SILENCE_THRESHOLD_FRAMES:
                chunk_end = i / sample_rate
                
                if chunk_end > current_chunk_start:
                    chunks.append((current_chunk_start, chunk_end))
                    current_chunk_start = chunk_end
                
        else:
            silence_count = 0
    
    # Add final chunk
    final_time = len(audio_data) / sample_rate
    if final_time > current_chunk_start:
        chunks.append((current_chunk_start, final_time))
    
    return chunks

def simulate_tts_chunking(self, text: str) -> List[str]:
    """
    Simulate how TTS chunks text during streaming.
    
    Matches production settings:
    - chunk_on=",.!?—" (main_continuous.py line 121)
    - min_chunk_size=30 chars
    
    :return: List of text chunks
    """
    chunks = []
    current_chunk = ""
    
    for char in text:
        current_chunk += char
        
        # Check for chunk boundary
        if char in ",.!?—" and len(current_chunk) >= 30:
            chunks.append(current_chunk.strip())
            current_chunk = ""
    
    # Add remaining text
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    return chunks
```

---

## 📈 Output Format

### Console Output Example

```
================================================================================
🔬 PIPELINE BENCHMARK: short_weather.wav
================================================================================

📦 Benchmarking CHUNKED transcription...
  📂 Loading audio file...
     Duration: 3.2s
  🔍 Detecting natural chunks (300ms pause threshold)...
     Found 2 chunks
       Chunk 1: 0.00s - 1.50s (1.50s)
       Chunk 2: 1.80s - 3.20s (1.40s)

  🎤 Transcribing chunks...
     Chunk 1: 95ms → 'hey sam'
       ⭐ FIRST CHUNK COMPLETE: 95ms
     Chunk 2: 87ms → 'what's the weather'

  📝 Full transcription: hey sam what's the weather

  🤖 Generating LLM response...
     ⭐ FIRST TOKEN: 234ms
     Generated 45 tokens in 1247ms
     Rate: 36.1 tokens/sec
  💬 Response: The weather is currently 72°F and sunny with clear skies...

  🔊 Synthesizing speech (chunked)...
     ⭐ FIRST AUDIO READY: 89ms
     Chunk 1: 89ms → 'The weather is currently 72°F and sunny'
     Chunk 2: 92ms → 'with clear skies.'

================================================================================
⭐ KEY METRICS ⭐
================================================================================

🎯 TIME TO FIRST SOUND: 418ms  ✅ EXCELLENT
   └─ STT First Chunk:    95ms  (23%)
   └─ LLM First Token:   234ms  (56%)
   └─ TTS First Audio:    89ms  (21%)

📊 COMPONENT BREAKDOWN:
   STT Total:            182ms  (11%)
   LLM Total:           1247ms  (74%)  ⚠️ BOTTLENECK
   TTS Total:            181ms  (11%)
   ─────────────────────────────
   Total Pipeline:      1610ms

🚀 EFFICIENCY:
   Chunked approach saved ~120ms on first transcription
   LLM is the primary bottleneck (74% of time)

💾 Results saved to: benchmark_results.csv
```

### CSV Output Format

```csv
timestamp,test_name,approach,audio_duration,stt_first_chunk,stt_total,stt_num_chunks,llm_ttft,llm_total,llm_tokens,tts_first_audio,tts_total,tts_num_chunks,time_to_first_sound,total_pipeline,bottleneck_component,bottleneck_percentage
2025-10-15T14:32:00,short_weather,chunked,3.2,0.095,0.182,2,0.234,1.247,45,0.089,0.181,2,0.418,1.610,LLM,74.1
2025-10-15T14:32:05,short_weather,non_chunked,3.2,0.198,0.198,1,0.234,1.247,45,0.089,0.181,2,0.521,1.626,LLM,76.7
```

---

## 🎓 Implementation Recommendations

### Phase 1: Foundation (Start Here)
**Estimated Time: 2-3 hours**

1. **Create test audio recording script** (30 min)
   - Use `record_benchmark_audio.py` template
   - Record 4-5 test scenarios
   - Save to `tests/audio/`

2. **Implement core timing infrastructure** (1 hour)
   - `timer()` context manager
   - `PipelineBenchmark` class skeleton
   - Basic audio loading

3. **Implement VAD-based chunk detection** (1 hour)
   - Port from `test_parallel_processing.py`
   - Match 300ms silence threshold
   - Validate against live chunking

### Phase 2: Measurement (Core Features)
**Estimated Time: 3-4 hours**

1. **STT measurement** (1 hour)
   - Per-chunk timing
   - First chunk timing (critical!)
   - Total transcription time

2. **LLM measurement** (1 hour)
   - Time to First Token (TTFT)
   - Per-token timing
   - Token generation rate

3. **TTS measurement** (1.5 hours)
   - Simulate TTS chunking logic
   - Per-chunk synthesis timing
   - Time to First Audio (TTFA)

4. **Calculate key metrics** (30 min)
   - Time to First Sound
   - Component breakdown percentages
   - Bottleneck identification

### Phase 3: Comparison & Analysis
**Estimated Time: 2 hours**

1. **Non-chunked implementation** (1 hour)
   - Single transcription approach
   - Same LLM/TTS measurement
   - Comparison logic

2. **Analysis & reporting** (1 hour)
   - Bottleneck identification
   - Chunked vs non-chunked comparison
   - Console output formatting

### Phase 4: Persistence (Optional)
**Estimated Time: 1 hour**

1. **CSV export** (30 min)
   - Save results to `benchmark_results.csv`
   - Append mode for historical tracking

2. **Results loading** (30 min)
   - Read previous benchmarks
   - Compare against baseline

---

## 🔗 Key Reference Files

### Existing Code to Study

1. **`test_parallel_processing.py`** (lines 1-200)
   - Timing instrumentation patterns
   - Generator wrapping technique
   - Event capture methodology

2. **`lib/speech_to_text.py`** (line 1428)
   - `SHORT_PAUSE_MS = 300` - chunking threshold
   - VAD-based silence detection
   - Chunked transcription mode

3. **`lib/text_to_speech.py`** (line 672)
   - `speak_streaming()` method
   - TTS chunking logic (`chunk_on=",.!?—"`)
   - Smart punctuation handling

4. **`main_continuous.py`** (line 121)
   - Production TTS parameters
   - `chunk_on=",.!?—", min_chunk_size=30`

---

## 💡 Future Enhancements

**Not needed initially, but valuable later:**

### Phase 5: Advanced Features (Future)
1. **HTML Report Generation**
   - Waterfall charts
   - Historical trend graphs
   - Component breakdown visualizations

2. **CPU/Memory Profiling**
   - Resource usage per component
   - Memory leaks detection
   - Parallel processing overhead

3. **A/B Testing Framework**
   - Compare different models (tiny vs base vs medium)
   - Test optimization strategies
   - Statistical significance testing

4. **Automated Regression Testing**
   - CI/CD integration
   - Performance regression alerts
   - Automatic benchmark on commits

---

## 🎯 Success Criteria

### Minimum Viable Benchmark (MVP)
- ✅ Record 4-5 test audio files
- ✅ Measure Time to First Sound accurately
- ✅ Identify primary bottleneck component
- ✅ Compare chunked vs non-chunked approaches
- ✅ Console output with key metrics

### Phase 2 Goals
- ✅ CSV export for historical tracking
- ✅ All component timings captured
- ✅ Per-chunk timing details

### Phase 3 Goals (Future)
- ✅ HTML report generation
- ✅ Visualization graphs
- ✅ Automated comparison tools

---

## 📝 Implementation Checklist

```
Foundation:
[ ] Create tests/audio/ directory
[ ] Record test audio files (4-5 scenarios)
[ ] Implement timer() context manager
[ ] Implement PipelineBenchmark class skeleton
[ ] Audio loading functionality

STT Measurement:
[ ] VAD-based chunk detection (match 300ms threshold)
[ ] Per-chunk transcription timing
[ ] First chunk completion timing (CRITICAL)
[ ] Total transcription time

LLM Measurement:
[ ] Time to First Token (TTFT) measurement
[ ] Per-token timing capture
[ ] Token generation rate calculation

TTS Measurement:
[ ] TTS chunking simulation (match production logic)
[ ] Per-chunk synthesis timing
[ ] Time to First Audio (TTFA) measurement

Key Metrics:
[ ] Time to First Sound calculation (CRITICAL)
[ ] Component breakdown percentages
[ ] Bottleneck identification

Comparison:
[ ] Non-chunked pipeline implementation
[ ] Chunked vs non-chunked comparison
[ ] Winner determination

Output:
[ ] Console output formatting
[ ] CSV export (optional but recommended)
[ ] Summary statistics

Testing:
[ ] Run with all test audio files
[ ] Verify timing accuracy
[ ] Validate chunk detection against live mode
```

---

## 🚀 Getting Started

### Quick Start Commands

```bash
# 1. Create test audio directory
mkdir -p tests/audio

# 2. Record test audio
python record_benchmark_audio.py

# 3. Run benchmark
python benchmark_pipeline.py tests/audio/short_weather.wav

# 4. Compare multiple tests
python benchmark_pipeline.py tests/audio/short_weather.wav --save
python benchmark_pipeline.py tests/audio/medium_timer.wav --save
python compare_benchmarks.py
```

---

**Author:** Tobias Molland  
**Reviewers:** GitHub Copilot  
**Next Steps:** Implement Phase 1 (Foundation) using test_parallel_processing.py as reference
