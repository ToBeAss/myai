# Volume Boost for Whisper Transcription

## Overview

Boosting audio volume before transcription can potentially improve Whisper's accuracy, especially when:
- Microphone input is very quiet
- Recording environment has low signal-to-noise ratio
- Users speak softly or from a distance

## Testing

Use the provided test script to evaluate if volume boosting helps with your audio:

```bash
python test_volume_boost.py path/to/your/audio.wav
```

The script tests 7 different normalization methods:
1. **No Boost** - Current behavior (normalize to [-1, 1])
2. **Light Boost (1.5x)** - Simple 1.5x amplification
3. **Medium Boost (2.0x)** - Simple 2.0x amplification
4. **Heavy Boost (3.0x)** - Simple 3.0x amplification
5. **Peak Normalization** - Scale to use full dynamic range
6. **RMS Normalization (0.1)** - Normalize based on loudness
7. **RMS Normalization (0.15)** - Higher loudness target

## Implementation Options

### Option 1: Peak Normalization (Recommended)

Peak normalization scales audio so the loudest sample uses the full [-1, 1] range. This maximizes signal-to-noise ratio without introducing distortion.

**Pros:**
- Simple and fast
- No distortion (no clipping)
- Maximizes dynamic range
- Works well for consistently quiet audio

**Cons:**
- Can amplify noise if audio is very quiet
- Single loud spike will limit overall boost

**Code:**
```python
def apply_peak_normalization(audio_data: np.ndarray) -> np.ndarray:
    """Scale audio to use full dynamic range."""
    peak = np.abs(audio_data).max()
    if peak > 0 and peak < 0.95:  # Only boost if below threshold
        return audio_data / peak
    return audio_data
```

### Option 2: RMS Normalization (Loudness-Based)

RMS normalization adjusts based on average loudness (Root Mean Square), which is more perceptually accurate than peak levels.

**Pros:**
- More consistent loudness across recordings
- Better handles audio with varying dynamic range
- Less affected by occasional loud spikes

**Cons:**
- Slightly more computation
- May clip if RMS target is too high
- Requires careful parameter tuning

**Code:**
```python
def apply_rms_normalization(audio_data: np.ndarray, target_rms: float = 0.1) -> np.ndarray:
    """
    Normalize based on average loudness.
    
    :param audio_data: Input audio
    :param target_rms: Target RMS level (0.05-0.15 typical)
    :return: Normalized audio
    """
    rms = np.sqrt(np.mean(audio_data ** 2))
    if rms > 0 and rms < target_rms * 0.8:  # Only boost if significantly below target
        normalized = audio_data * (target_rms / rms)
        return np.clip(normalized, -1.0, 1.0)  # Prevent distortion
    return audio_data
```

### Option 3: Simple Amplification

Multiply audio by a constant factor. Simple but can cause clipping.

**Pros:**
- Very simple
- Fast

**Cons:**
- Can introduce distortion if factor is too high
- Not adaptive to input levels

**Code:**
```python
def apply_simple_boost(audio_data: np.ndarray, factor: float = 1.5) -> np.ndarray:
    """Simple multiplication boost."""
    return np.clip(audio_data * factor, -1.0, 1.0)
```

## Integration into speech_to_text.py

### Where to Add Boosting

The `load_audio_data()` method is the ideal place to add volume boosting, right before returning the audio data to Whisper.

**Location:** `/lib/speech_to_text.py` - line ~977 (after normalization, before return)

### Example Integration (Peak Normalization)

```python
def load_audio_data(self, audio_file_path: str) -> np.ndarray:
    """
    Load audio data directly from WAV file without FFmpeg.
    
    :param audio_file_path: Path to the WAV file
    :return: Audio data as numpy array
    """
    try:
        with wave.open(audio_file_path, 'rb') as wav_file:
            # ... existing loading code ...
            
            # Convert to float32 and normalize to [-1, 1]
            if dtype == np.uint8:
                audio_data = (audio_data.astype(np.float32) - 128) / 128
            elif dtype == np.int16:
                audio_data = audio_data.astype(np.float32) / 32768
            elif dtype == np.int32:
                audio_data = audio_data.astype(np.float32) / 2147483648
            
            # Resample to 16kHz if needed
            if sample_rate != 16000:
                target_length = int(len(audio_data) * 16000 / sample_rate)
                audio_data = np.interp(
                    np.linspace(0, len(audio_data), target_length),
                    np.arange(len(audio_data)),
                    audio_data
                )
            
            # **NEW: Apply peak normalization for better transcription**
            peak = np.abs(audio_data).max()
            if peak > 0 and peak < 0.95:
                audio_data = audio_data / peak
                print(f"🔊 Boosted audio: peak {peak:.3f} → 1.0")
            
            return audio_data
```

## Testing Workflow

1. **Run the test script** on sample audio to see if boosting helps:
   ```bash
   python test_volume_boost.py recording.wav
   ```

2. **Analyze results:**
   - If all methods produce identical results → boosting won't help
   - If peak/RMS normalization improves results → implement boosting
   - Compare transcription quality across methods

3. **Choose the best method** based on your test results

4. **Integrate into code** at the appropriate location

5. **Test in real usage** and monitor for:
   - Improved transcription accuracy
   - Any distortion or artifacts
   - Performance impact (minimal expected)

## Configuration Option

For maximum flexibility, add volume boosting as a configurable option:

```python
def __init__(self, 
             model_size: str = "tiny",
             enable_volume_boost: bool = True,
             boost_method: str = "peak",  # "peak", "rms", or "none"
             rms_target: float = 0.1,
             # ... other parameters
             ):
    """
    :param enable_volume_boost: Enable audio volume boosting before transcription
    :param boost_method: Normalization method - "peak", "rms", or "none"
    :param rms_target: Target RMS level when using RMS normalization
    """
    self.enable_volume_boost = enable_volume_boost
    self.boost_method = boost_method
    self.rms_target = rms_target
```

Then in `load_audio_data()`:

```python
# Apply volume boosting if enabled
if self.enable_volume_boost:
    audio_data = self._apply_volume_boost(audio_data)
```

## Considerations

### When Volume Boosting Helps
- Quiet microphone input
- Soft-spoken users
- Low-quality microphone
- Background noise drowning out speech
- Distance from microphone

### When It May Not Help
- Already well-recorded audio (peak near 1.0)
- High-quality audio setup
- Close-mic recording
- Audio already properly normalized

### Potential Issues
- **Over-boosting:** Can amplify background noise
- **Clipping:** If boost is too aggressive, can cause distortion
- **Minimal gain:** If audio is already loud, no benefit

## Performance Impact

Volume boosting adds minimal overhead:
- **Peak normalization:** ~0.1ms for typical recording
- **RMS normalization:** ~0.2ms for typical recording
- **Impact on total pipeline:** <1% increase

## Recommendations

1. **Start with testing** - Run the test script on your typical audio
2. **Peak normalization** is the safest starting point
3. **Monitor results** - Check if accuracy improves in practice
4. **Make it configurable** - Allow disabling if not helpful
5. **Log boost levels** - Track when and how much boosting occurs

## Alternative: Pre-Recording Boost

Instead of boosting after recording, you could:
- Increase microphone gain in system settings
- Use audio preprocessing before recording
- Apply real-time AGC (Automatic Gain Control)

However, post-recording boost is simpler and doesn't require system-level changes.
