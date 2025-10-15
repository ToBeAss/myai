# Pipeline Benchmark System

A comprehensive benchmarking system for measuring end-to-end performance of the AI voice assistant pipeline, with focus on **Time to First Sound (TTFS)** - the most critical metric for perceived system responsiveness.

## 🎯 What Gets Measured

### Primary Metric: Time to First Sound (TTFS)
**The time from when the user stops speaking until they hear the AI start responding.**

```
TTFS = STT First Chunk + LLM First Token + TTS First Audio
```

This is the most important UX metric - it determines whether your assistant feels "alive" and responsive.

### Component Breakdown
1. **Speech-to-Text (STT)**
   - First chunk completion time (critical for TTFS)
   - Per-chunk transcription times
   - Total transcription time
   - Number of chunks detected

2. **LLM Generation**
   - Time to First Token (TTFT) - critical for TTFS
   - Total generation time
   - Token generation rate (tokens/sec)
   - Total tokens generated

3. **Text-to-Speech (TTS)**
   - Time to First Audio (TTFA) - critical for TTFS
   - Per-chunk synthesis times
   - Total synthesis time
   - Number of TTS chunks

### Bottleneck Analysis
Identifies which component takes the most time (as percentage of total) so you know where to optimize first.

## 🚀 Quick Start

### 1. Record Test Audio

```bash
python record_benchmark_audio.py
```

This creates test audio files in `tests/audio/` covering different scenarios:
- **short_weather** - Quick query (speed baseline)
- **short_time** - Minimal query
- **medium_timer** - Natural pauses (chunking test)
- **medium_with_pause** - Intentional pause (chunking behavior)
- **long_explanation** - Complex response (realistic load)
- **complex_with_numbers** - Numbers and calculations

### 2. Run Benchmark

```bash
# Single test
python benchmark_pipeline.py tests/audio/short_weather.wav

# Save results to CSV
python benchmark_pipeline.py tests/audio/short_weather.wav --save

# Test all recordings
for file in tests/audio/*.wav; do
    python benchmark_pipeline.py "$file" --save
done
```

### 3. Compare Results

```bash
# View all results
python compare_benchmarks.py

# Compare specific test over time
python compare_benchmarks.py --test short_weather

# Show only recent runs
python compare_benchmarks.py --latest 10
```

## 📊 Example Output

```
================================================================================
🔬 PIPELINE BENCHMARK: short_weather.wav
================================================================================

📦 Benchmarking CHUNKED transcription...
  📂 Loading audio file...
     Duration: 3.2s
  🔍 Detecting natural chunks (300ms pause threshold)...
     Found 2 chunk(s)
       Chunk 1: 0.00s - 1.50s (1.50s)
       Chunk 2: 1.80s - 3.20s (1.40s)

  🎤 Transcribing chunks...
     Chunk 1: 95ms → 'hey sam'
       ⭐ FIRST CHUNK COMPLETE: 95ms
     Chunk 2: 87ms → 'what's the weather'

  📝 Full transcription: "hey sam what's the weather"

  🤖 Generating LLM response...
     ⭐ FIRST TOKEN: 234ms
     Generated 45 tokens in 1247ms
     Rate: 36.1 tokens/sec
  💬 Response: "The weather is currently 72°F and sunny with clear skies..."

  🔊 Synthesizing speech (chunked)...
     ⭐ FIRST AUDIO READY: 89ms
     Chunk 1: 89ms → "The weather is currently 72°F and sunny"
     Chunk 2: 92ms → "with clear skies."

================================================================================
⭐ KEY METRICS ⭐
================================================================================

🎯 TIME TO FIRST SOUND: 418ms  ✅ EXCELLENT
   └─ STT First Chunk:    95ms  (23%)
   └─ LLM First Token:   234ms  (56%)
   └─ TTS First Audio:    89ms  (21%)

📊 COMPONENT BREAKDOWN:
   STT Total:            182ms  (11%)
   LLM Total:           1247ms  (74%)  
   TTS Total:            181ms  (11%)
   ─────────────────────────────
   Total Pipeline:      1610ms

⚠️  BOTTLENECK: LLM (74.1% of total time)

📈 ADDITIONAL STATS:
   Audio Duration:       3.20s
   STT Chunks:           2
   LLM Tokens:           45 (36.1 tokens/sec)
   TTS Chunks:           2
================================================================================
```

## 📈 Performance Targets

### Time to First Sound (TTFS)
- **< 300ms**: 🎉 Exceptional (instant response feeling)
- **300-500ms**: ✅ Excellent (very natural)
- **500-800ms**: 👍 Great (responsive)
- **800-1200ms**: ✓ Good (acceptable)
- **> 1200ms**: ⚠️ Needs optimization

### Context: Comparison with Other Assistants

**Traditional Assistants (Siri/Alexa/Google Home):**
- TTFS: 200-400ms
- Use templated/retrieval-based responses
- No LLM generation involved

**LLM-Based Assistants (Your System):**
- Optimistic Target: 500-800ms (feels very responsive)
- Realistic Target: 800-1200ms (acceptable)
- Baseline (before optimization): 1200-2000ms

**Key Insight:** You're doing real AI generation, so 600-800ms is competitive and impressive!

## 🔍 Understanding the Results

### Component Analysis

**STT (Speech-to-Text)**
- Fast models (base): 80-150ms per chunk
- Larger models (large): 200-400ms per chunk
- Chunking helps: Process while user is still speaking

**LLM (Language Model)**
- Usually the bottleneck (60-80% of total time)
- TTFT depends on: model size, server load, prompt complexity
- Typical: 200-600ms for first token
- Streaming is critical: allows TTS to start early

**TTS (Text-to-Speech)**
- Modern APIs: 80-150ms for first chunk
- Quality voices (Neural2/Chirp): slightly slower
- Chunking helps: Synthesize in parallel with playback

### Optimization Priority

1. **If LLM > 60%**: Primary bottleneck
   - Use faster model (gpt-4o-mini vs gpt-4)
   - Reduce prompt complexity
   - Consider caching common responses

2. **If STT > 30%**: Transcription bottleneck
   - Use faster-whisper library
   - Use smaller model (tiny/base vs medium/large)
   - Ensure chunking is working properly

3. **If TTS > 30%**: Synthesis bottleneck
   - Use faster voices (Standard vs Neural2)
   - Optimize chunk boundaries
   - Ensure parallel synthesis is working

## 📁 Files Created

### Recording Script
- `record_benchmark_audio.py` - Records test scenarios

### Benchmark System
- `benchmark_pipeline.py` - Main benchmarking script
- `compare_benchmarks.py` - Results analysis and comparison

### Data Files (Created by Running)
- `tests/audio/*.wav` - Test audio recordings
- `benchmark_results.csv` - Historical results database

## 🔬 Technical Details

### Chunking Detection
Uses WebRTC VAD with 300ms silence threshold (matching production settings from `speech_to_text.py` line 1428).

### TTS Chunking Simulation
Matches production TTS chunking: splits on `",.!?—"` with 30-char minimum (from `main_continuous.py` line 121).

### Timing Precision
Uses `time.perf_counter()` for sub-millisecond accuracy.

## 📊 CSV Schema

Results saved to `benchmark_results.csv`:

```csv
timestamp              - ISO format timestamp
test_name              - Audio file name (without extension)
approach               - 'chunked' (may add 'non-chunked' in future)
audio_duration         - Length of test audio in seconds
stt_first_chunk        - First STT chunk completion time (seconds)
stt_total              - Total STT time (seconds)
stt_num_chunks         - Number of detected chunks
llm_ttft               - LLM Time to First Token (seconds)
llm_total              - Total LLM generation time (seconds)
llm_tokens             - Total tokens generated
llm_tokens_per_sec     - Token generation rate
tts_first_audio        - TTS Time to First Audio (seconds)
tts_total              - Total TTS synthesis time (seconds)
tts_num_chunks         - Number of TTS chunks
time_to_first_sound    - ⭐ PRIMARY METRIC (seconds)
total_pipeline         - Total end-to-end time (seconds)
bottleneck_component   - STT, LLM, or TTS
bottleneck_percentage  - Percentage of total time
```

## 🎓 Best Practices

### Recording Test Audio
1. **Consistent environment** - Same room, mic, background noise
2. **Natural speech** - Don't rush or speak robotically
3. **Include wake word** - Say "Hey Sam" naturally
4. **Realistic pauses** - Pause where you naturally would
5. **Multiple takes** - Record each scenario 2-3 times

### Running Benchmarks
1. **Warm-up runs** - First run may be slower (model loading)
2. **Multiple runs** - Run each test 3-5 times for average
3. **Consistent conditions** - Same time of day (API load varies)
4. **Save results** - Always use `--save` flag to track trends
5. **Test after changes** - Benchmark before/after optimizations

### Analyzing Results
1. **Focus on TTFS** - Primary UX metric
2. **Identify bottleneck** - Optimize the slowest component first
3. **Track trends** - Compare over time, not absolute values
4. **Consider variance** - API latency varies, look at averages
5. **Test scenarios** - Short queries should be fastest

## 🚀 Future Enhancements

Potential additions (not implemented yet):

- **Non-chunked comparison** - Compare chunked vs non-chunked STT
- **HTML reports** - Visual charts and waterfall diagrams
- **CPU/Memory profiling** - Resource usage tracking
- **A/B testing framework** - Statistical comparison of approaches
- **CI/CD integration** - Automated regression testing
- **Live monitoring** - Real-time performance dashboards

## 🤝 Contributing

When making optimizations:

1. **Benchmark before** - Establish baseline
2. **Make one change** - Isolate what helped
3. **Benchmark after** - Measure improvement
4. **Document findings** - Update optimization guides

## 📚 Related Documentation

- `BENCHMARK_PIPELINE_DESIGN.md` - Detailed design document
- `LATENCY_OPTIMIZATION_SETTINGS.md` - Optimization strategies
- `LATENCY_ANALYSIS.md` - Historical performance analysis

---

**Created:** October 15, 2025  
**Author:** Tobias Molland  
**Purpose:** Measure and optimize AI voice assistant responsiveness
