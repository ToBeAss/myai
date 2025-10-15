# Quick Start: Benchmark Your Pipeline

This guide will get you benchmarking in 5 minutes.

## Prerequisites

Make sure you have all dependencies installed:

```bash
# Check if you need to install anything
pip list | grep -E "sounddevice|webrtcvad|faster-whisper"

# If missing, install:
pip install sounddevice webrtcvad
# faster-whisper should already be installed if you're using the optimized STT
```

## Step 1: Record Test Audio (3 minutes)

```bash
python record_benchmark_audio.py
```

Follow the prompts to record 6 test scenarios:
1. **short_weather** - "Hey Sam, what's the weather?" (4 seconds)
2. **short_time** - "Hey Sam, what time is it?" (3 seconds)
3. **medium_timer** - "Hey Sam, set a timer..." (6 seconds)
4. **medium_with_pause** - With intentional pause (5 seconds)
5. **long_explanation** - "Explain quantum entanglement..." (12 seconds)
6. **complex_with_numbers** - Math question (7 seconds)

**Tips:**
- Speak naturally with realistic pauses
- Say "Hey Sam" clearly at the start
- Don't worry about perfection - realistic is better

## Step 2: Run Your First Benchmark (1 minute)

```bash
python benchmark_pipeline.py tests/audio/short_weather.wav --save
```

This will:
- ✅ Load your audio
- ✅ Detect natural chunks (300ms pauses)
- ✅ Transcribe with STT
- ✅ Generate LLM response
- ✅ Synthesize with TTS
- ✅ Measure Time to First Sound (TTFS)
- ✅ Save results to CSV

**Expected output:**
```
🎯 TIME TO FIRST SOUND: 418ms  ✅ EXCELLENT
```

## Step 3: Test All Scenarios (5 minutes)

```bash
# Run all tests
for file in tests/audio/*.wav; do
    python benchmark_pipeline.py "$file" --save
    echo ""  # Blank line between tests
done
```

## Step 4: Analyze Results (1 minute)

```bash
# View summary
python compare_benchmarks.py

# View specific test trends
python compare_benchmarks.py --test short_weather
```

## What to Look For

### 🎯 Time to First Sound (TTFS)
**This is your main metric!**

- **< 500ms**: 🎉 Your system feels instant and responsive
- **500-800ms**: ✅ Great performance, users will be happy
- **800-1200ms**: ✓ Acceptable, but could be better
- **> 1200ms**: ⚠️ Users will notice lag, optimization needed

### 🔍 Bottleneck Identification

The system tells you where to optimize:

**If LLM is 60-80% of time:**
- Use faster model: `openai-gpt-4o-mini` instead of `gpt-4`
- Simplify system prompts
- This is normal - LLMs are typically the slowest part

**If STT is > 30% of time:**
- Check you're using `faster-whisper`
- Use smaller model: `base` instead of `medium` or `large`
- Verify chunking is working (should see 2-3 chunks)

**If TTS is > 30% of time:**
- Use faster voices: WaveNet or Standard instead of Neural2/Chirp
- Verify parallel synthesis is working

## Real-World Expectations

### Your System (LLM-Based)
- **Target:** 600-800ms TTFS
- **Why slower than Siri?** You're generating real AI responses, not templates
- **Competitive benchmark:** If you hit 600-800ms, that's impressive for true AI

### Traditional Assistants
- **Siri/Alexa/Google:** 200-400ms
- **Why faster?** Pre-computed responses, no LLM generation
- **Trade-off:** Much less intelligent, can't have real conversations

## Next Steps

### After First Benchmark:

1. **Establish Baseline**
   ```bash
   python compare_benchmarks.py
   ```
   Note your current TTFS for each test scenario.

2. **Try Optimizations**
   - Switch to faster model
   - Adjust chunk settings
   - Try different voices

3. **Re-benchmark**
   ```bash
   python benchmark_pipeline.py tests/audio/short_weather.wav --save
   ```

4. **Compare Improvement**
   ```bash
   python compare_benchmarks.py --test short_weather
   ```

### Common Optimizations to Try:

**Fastest Model (sacrifice quality slightly):**
```python
# In benchmark_pipeline.py or main_continuous.py
self.llm = LLM_Wrapper(model_name="openai-gpt-4o-mini")
```

**Smallest STT Model (fastest transcription):**
```python
self.stt = SpeechToText(
    model_size="tiny",  # or "base" for better accuracy
    use_faster_whisper=True,
)
```

**Fastest TTS Voice:**
```python
self.tts = TextToSpeech(
    voice_name="en-GB-Standard-A",  # Standard is faster than Neural2/Chirp
    speaking_rate=1.2,  # Slightly faster speech
)
```

## Troubleshooting

### "Module not found: webrtcvad"
```bash
pip install webrtcvad
```

### "Module not found: sounddevice"
```bash
pip install sounddevice
```

### "Audio file not found"
Make sure you ran `record_benchmark_audio.py` first!

### Results look inconsistent
- API latency varies by time of day
- Run each test 3-5 times
- Look at averages, not individual runs

### TTFS over 2000ms
- Check your internet connection
- API servers may be under heavy load
- Try again in a few minutes

## Understanding the Output

```
🎯 TIME TO FIRST SOUND: 418ms  ✅ EXCELLENT
   └─ STT First Chunk:    95ms  (23%)    ← How long to transcribe first chunk
   └─ LLM First Token:   234ms  (56%)    ← How long until LLM starts responding
   └─ TTS First Audio:    89ms  (21%)    ← How long to synthesize first audio
```

**The percentages show you where the time goes:**
- In this example, LLM is taking 56% of the total TTFS
- That's normal - LLM generation is typically the bottleneck
- If any component is > 40%, consider optimizing it

## Tips for Best Results

1. **Run benchmarks at consistent times** - API latency varies
2. **Take multiple measurements** - Average 3-5 runs
3. **Test after every optimization** - Track what actually helps
4. **Focus on TTFS** - Total time matters less than perceived responsiveness
5. **Keep test audio** - Use same recordings for fair comparison

## Advanced Usage

### Custom Test Scenarios

Record your own specific use cases:
```python
from record_benchmark_audio import record_benchmark_audio

record_benchmark_audio(
    name="my_custom_test",
    duration=5,
    description="Hey Sam, tell me a joke"
)
```

### Batch Testing

Create a script to test multiple configurations:
```bash
#!/bin/bash
# test_configurations.sh

# Baseline
python benchmark_pipeline.py tests/audio/short_weather.wav --save

# After optimization 1
# ... make changes ...
python benchmark_pipeline.py tests/audio/short_weather.wav --save

# After optimization 2
# ... make more changes ...
python benchmark_pipeline.py tests/audio/short_weather.wav --save

# Compare
python compare_benchmarks.py --test short_weather
```

## Questions?

- Check `BENCHMARK_README.md` for detailed documentation
- Review `BENCHMARK_PIPELINE_DESIGN.md` for technical details
- Check existing optimization guides: `LATENCY_OPTIMIZATION_SETTINGS.md`

---

🎉 **You're ready to benchmark!** Start with Step 1 and work your way through. Your goal: Get TTFS under 800ms for short queries.
