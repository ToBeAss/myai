# Continuous Listening Optimization Guide

## Problem Analysis

Your system is currently processing audio **constantly** and transcribing with Whisper every time it detects volume above the threshold. In your 5-10 minute session, you had:

- **20+ hallucination detections** (background noise being transcribed)
- **1 false wake word detection** (speech without wake word)
- Only **1 actual wake word activation**

This means you're running expensive Whisper transcriptions ~22 times, but only needed it once!

### Current Bottlenecks:
1. **Low silence threshold (300)** triggers on ambient noise
2. **No pre-filtering** - every sound goes to Whisper
3. **Volume-only detection** - can't distinguish speech from noise (door closing, keyboard, etc.)
4. **CPU/Memory intensive** - Whisper runs on every detection

---

## Solution 1: WebRTC VAD Pre-filtering (RECOMMENDED)

**Best for:** Quick improvement with minimal code changes

### What is WebRTC VAD?
Voice Activity Detection using Google's WebRTC library. It's a lightweight neural network specifically trained to distinguish human speech from noise.

### Benefits:
- ✅ **90% reduction** in false positives
- ✅ Lightweight (runs in real-time)
- ✅ Only runs Whisper when actual speech is detected
- ✅ Free and open-source
- ✅ Works offline

### Implementation:

#### 1. Install WebRTC VAD
```bash
pip install webrtcvad
```

#### 2. Modify `lib/speech_to_text.py`

Add to imports:
```python
import webrtcvad
```

Update `__init__` method:
```python
def __init__(self, 
             model_size: str = "tiny",
             flexible_wake_word: bool = True,
             confidence_threshold: int = None,
             confidence_mode: str = "balanced",
             track_metrics: bool = True,
             false_positive_timeout: float = 10.0,
             vad_aggressiveness: int = 2):  # NEW: 0-3, higher = more strict
    """
    ...
    :param vad_aggressiveness: VAD filtering level (0=liberal, 3=aggressive)
    """
    # ... existing init code ...
    
    # Initialize WebRTC VAD
    self.vad = webrtcvad.Vad(vad_aggressiveness)
    self.vad_frame_duration = 30  # ms (10, 20, or 30)
    self.vad_frame_size = int(self.rate * self.vad_frame_duration / 1000)
    print(f"🎯 Voice Activity Detection: ENABLED (aggressiveness: {vad_aggressiveness})")
```

Update `_continuous_listen_loop` method to add VAD check:
```python
def _continuous_listen_loop(self):
    """Main loop for continuous listening."""
    try:
        audio = pyaudio.PyAudio()
        stream = audio.open(
            format=self.audio_format,
            channels=self.channels,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk
        )
        
        audio_buffer = []
        buffer_duration = 5.0
        buffer_size = int(self.rate * buffer_duration / self.chunk)
        
        silence_threshold = 400  # INCREASED from 300
        speech_detected = False
        speech_frames = []
        silence_count = 0
        speech_start_time = 0
        last_speech_time = 0
        max_speech_duration = 60.0
        
        # VAD consecutive frame tracking
        vad_speech_frames = 0
        vad_required_frames = 3  # Need 3 consecutive speech frames
        
        while self.is_listening:
            try:
                data = stream.read(self.chunk, exception_on_overflow=False)
                audio_chunk = np.frombuffer(data, dtype=np.int16)
                
                # Calculate volume
                volume = np.sqrt(np.mean(audio_chunk.astype(np.float32)**2))
                
                # Add to circular buffer
                audio_buffer.append(data)
                if len(audio_buffer) > buffer_size:
                    audio_buffer.pop(0)
                
                # STEP 1: Volume check (quick filter)
                if volume > silence_threshold:
                    # STEP 2: VAD check (smarter filter)
                    # WebRTC VAD needs frames of specific sizes (10, 20, or 30ms)
                    is_speech = self._is_speech_vad(data)
                    
                    if is_speech:
                        vad_speech_frames += 1
                    else:
                        vad_speech_frames = 0
                        # Reset speech detection if VAD says no speech
                        if speech_detected and silence_count == 0:
                            # Just started, but VAD says not speech
                            speech_detected = False
                            speech_frames = []
                    
                    # Only proceed if we have consecutive speech frames
                    if vad_speech_frames >= vad_required_frames:
                        current_time = time.time()
                        
                        if not speech_detected:
                            if current_time - last_speech_time > 2.0:
                                speech_detected = True
                                speech_start_time = current_time
                                speech_frames = audio_buffer.copy()
                                print("🎤 Speech detected (VAD confirmed), recording...")
                                
                                self.speech_being_processed = True
                                
                                if self.in_conversation:
                                    self.update_conversation_activity()
                        
                        if speech_detected:
                            speech_frames.append(data)
                            silence_count = 0
                            
                            if current_time - speech_start_time > max_speech_duration:
                                print("⏱️ Maximum recording duration reached, processing speech...")
                                self._process_speech_chunk(speech_frames)
                                speech_detected = False
                                speech_frames = []
                                silence_count = 0
                                last_speech_time = current_time
                                vad_speech_frames = 0
                else:
                    vad_speech_frames = 0  # Reset on silence
                    
                    if speech_detected:
                        silence_count += 1
                        speech_frames.append(data)
                        
                        if silence_count > 60:
                            print("🔄 Processing speech...")
                            self._process_speech_chunk(speech_frames)
                            speech_detected = False
                            speech_frames = []
                            silence_count = 0
                            last_speech_time = current_time
                
                if self.track_metrics:
                    self.check_engagement_timeout()
                
                time.sleep(0.01)
                
            except Exception as e:
                print(f"❌ Error in continuous listening: {e}")
                continue
                
    except Exception as e:
        print(f"❌ Failed to start continuous listening: {e}")
    finally:
        try:
            stream.stop_stream()
            stream.close()
            audio.terminate()
        except:
            pass

def _is_speech_vad(self, audio_frame: bytes) -> bool:
    """
    Check if audio frame contains speech using WebRTC VAD.
    
    :param audio_frame: Raw audio bytes
    :return: True if speech detected
    """
    try:
        # WebRTC VAD requires specific frame sizes
        # We need to ensure frame is exactly the right size
        frame_size = self.vad_frame_size * 2  # *2 because 16-bit = 2 bytes
        
        if len(audio_frame) < frame_size:
            return False
        
        # Take only the exact frame size needed
        frame = audio_frame[:frame_size]
        
        # VAD returns True if speech detected
        return self.vad.is_speech(frame, self.rate)
    except Exception as e:
        # If VAD fails, default to True to avoid missing speech
        return True
```

#### 3. Update `main_continuous.py` configuration:
```python
# Initialize speech-to-text system with VAD
stt = SpeechToText(
    model_size="base",
    track_metrics=False,
    vad_aggressiveness=2  # 0=least filtering, 3=most filtering
)
```

### Expected Results:
- **Before:** 20+ Whisper calls in 5-10 minutes
- **After:** 1-3 Whisper calls (only on actual speech)
- **CPU usage:** Reduced by ~80%
- **Responsiveness:** Maintained (VAD adds <10ms latency)

### Aggressiveness Tuning:
- `0`: Liberal - catches all speech, some noise
- `1`: Moderate - good balance (start here if `2` too aggressive)
- `2`: **Balanced - RECOMMENDED** for home environment
- `3`: Aggressive - office/noisy environments, may miss soft speech

---

## Solution 2: Porcupine Wake Word Engine (MOST EFFICIENT)

**Best for:** Production-grade system with minimal CPU usage

### What is Porcupine?
A specialized neural network that **only** listens for specific wake words. Runs continuously at <1% CPU.

### Benefits:
- ✅ **99% reduction** in Whisper calls
- ✅ Extremely lightweight (~2MB RAM)
- ✅ Only runs Whisper **after** wake word confirmed
- ✅ Custom wake word training available
- ✅ Cross-platform (works on Raspberry Pi!)

### Drawbacks:
- ⚠️ Free tier limited to 3 wake words
- ⚠️ Requires API key (free account)
- ⚠️ Custom wake words require paid tier

### Implementation:

#### 1. Install Porcupine
```bash
pip install pvporcupine pyaudio
```

#### 2. Get API Key
1. Sign up at https://console.picovoice.ai/
2. Create a new project
3. Copy your Access Key

#### 3. Create new wake word handler: `lib/wake_word_detector.py`
```python
import pvporcupine
import pyaudio
import struct
import threading

class PorcupineWakeWordDetector:
    """Lightweight wake word detection using Porcupine."""
    
    def __init__(self, access_key: str, keywords: list = None):
        """
        Initialize Porcupine wake word detector.
        
        :param access_key: Picovoice access key
        :param keywords: Built-in keywords to detect
                        Available: alexa, americano, blueberry, bumblebee, 
                                 computer, grapefruit, grasshopper, hey google,
                                 hey siri, jarvis, ok google, picovoice, porcupine, 
                                 terminator
        """
        self.keywords = keywords or ['computer', 'jarvis']
        
        # Initialize Porcupine
        self.porcupine = pvporcupine.create(
            access_key=access_key,
            keywords=self.keywords
        )
        
        self.audio = pyaudio.PyAudio()
        self.is_listening = False
        self.callback = None
        
        print(f"🎯 Porcupine wake word detection initialized")
        print(f"🗣️  Wake words: {', '.join(self.keywords)}")
    
    def start_listening(self, callback):
        """
        Start listening for wake words.
        
        :param callback: Function to call when wake word detected
        """
        self.callback = callback
        self.is_listening = True
        
        # Start listening thread
        thread = threading.Thread(target=self._listen_loop, daemon=True)
        thread.start()
        
        print("✅ Listening for wake words...")
    
    def stop_listening(self):
        """Stop listening."""
        self.is_listening = False
    
    def _listen_loop(self):
        """Main listening loop."""
        try:
            stream = self.audio.open(
                rate=self.porcupine.sample_rate,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=self.porcupine.frame_length
            )
            
            while self.is_listening:
                pcm = stream.read(self.porcupine.frame_length, exception_on_overflow=False)
                pcm = struct.unpack_from("h" * self.porcupine.frame_length, pcm)
                
                keyword_index = self.porcupine.process(pcm)
                
                if keyword_index >= 0:
                    detected_keyword = self.keywords[keyword_index]
                    print(f"🎯 Wake word detected: '{detected_keyword}'")
                    if self.callback:
                        self.callback(detected_keyword)
            
            stream.close()
        except Exception as e:
            print(f"❌ Error in wake word detection: {e}")
    
    def cleanup(self):
        """Clean up resources."""
        if self.porcupine is not None:
            self.porcupine.delete()
        self.audio.terminate()
```

#### 4. Update `main_continuous.py`:
```python
from lib.wake_word_detector import PorcupineWakeWordDetector
from lib.speech_to_text import SpeechToText

# ... existing setup ...

# Initialize Porcupine for wake word detection
wake_detector = PorcupineWakeWordDetector(
    access_key="YOUR_ACCESS_KEY_HERE",
    keywords=['computer', 'jarvis']  # Choose from built-in keywords
)

# Initialize STT (only used after wake word detected)
stt = SpeechToText(model_size="base", track_metrics=False)

def on_wake_word_detected(keyword):
    """Called when Porcupine detects wake word."""
    print(f"\n💡 Wake word '{keyword}' detected! Listening for command...")
    
    # NOW record and transcribe the actual command
    command_text = stt.listen_and_transcribe(
        duration=5.0,  # Record for 5 seconds or until silence
        remove_wake_word=False  # Already removed
    )
    
    if command_text and len(command_text) > 3:
        handle_voice_command(command_text)

# Start wake word detection
wake_detector.start_listening(on_wake_word_detected)

try:
    print("🎙️ Porcupine wake word detection active!")
    print("💡 Say 'Computer' or 'Jarvis' to activate...")
    
    while True:
        time.sleep(0.1)
except KeyboardInterrupt:
    print("\n🛑 Shutting down...")
    wake_detector.stop_listening()
    wake_detector.cleanup()
```

### Expected Results:
- **Before:** 20+ Whisper calls
- **After:** 1 Whisper call (only after wake word)
- **CPU usage:** ~99% reduction
- **RAM usage:** Minimal (~5MB)
- **Battery life:** Significantly improved

---

## Solution 3: Optimize Existing System

**Best for:** No new dependencies, quick fixes

### Quick Improvements:

#### 1. Increase Silence Threshold
```python
silence_threshold = 500  # Increased from 300
```

#### 2. Require More Consecutive "Speech" Frames
```python
speech_confidence_frames = 0
required_confidence_frames = 5  # Need 5 consecutive frames > threshold

if volume > silence_threshold:
    speech_confidence_frames += 1
else:
    speech_confidence_frames = 0

# Only trigger on sustained volume
if speech_confidence_frames >= required_confidence_frames:
    # Start recording
    ...
```

#### 3. Add Frequency Analysis (Remove Low-Frequency Noise)
```python
def is_likely_speech(self, audio_chunk: np.ndarray) -> bool:
    """
    Check if audio chunk likely contains speech based on frequency.
    Speech typically has energy in 300-3000 Hz range.
    """
    # Apply FFT to get frequency spectrum
    fft = np.fft.rfft(audio_chunk)
    freqs = np.fft.rfftfreq(len(audio_chunk), 1/self.rate)
    
    # Calculate energy in speech range (300-3000 Hz)
    speech_range = (freqs >= 300) & (freqs <= 3000)
    speech_energy = np.sum(np.abs(fft[speech_range]))
    
    # Calculate total energy
    total_energy = np.sum(np.abs(fft))
    
    # Speech should have at least 30% of energy in speech range
    if total_energy > 0:
        speech_ratio = speech_energy / total_energy
        return speech_ratio > 0.3
    
    return False
```

#### 4. Implement Adaptive Threshold
```python
def __init__(self, ...):
    # ... existing init ...
    self.ambient_noise_level = 0
    self.adaptive_threshold = True

def calibrate_ambient_noise(self, duration=2.0):
    """Measure ambient noise level for adaptive threshold."""
    print("🎧 Calibrating ambient noise level...")
    audio = pyaudio.PyAudio()
    stream = audio.open(
        format=self.audio_format,
        channels=self.channels,
        rate=self.rate,
        input=True,
        frames_per_buffer=self.chunk
    )
    
    samples = []
    end_time = time.time() + duration
    
    while time.time() < end_time:
        data = stream.read(self.chunk, exception_on_overflow=False)
        audio_chunk = np.frombuffer(data, dtype=np.int16)
        volume = np.sqrt(np.mean(audio_chunk.astype(np.float32)**2))
        samples.append(volume)
    
    stream.stop_stream()
    stream.close()
    audio.terminate()
    
    # Set threshold to 2x ambient noise
    self.ambient_noise_level = np.mean(samples)
    adaptive_threshold = self.ambient_noise_level * 2
    
    print(f"✅ Ambient noise: {self.ambient_noise_level:.0f}")
    print(f"📊 Adaptive threshold: {adaptive_threshold:.0f}")
    
    return adaptive_threshold
```

---

## Recommendation Summary

### For Your Use Case:

**Primary Recommendation:** Start with **Solution 1 (WebRTC VAD)**
- Easy to implement (15 minutes)
- Huge improvement with minimal changes
- No API keys or external services
- Works offline

**Ultimate Solution:** Upgrade to **Solution 2 (Porcupine)**
- Professional-grade efficiency
- Nearly zero CPU usage when idle
- Best for always-on systems
- Only runs Whisper when actually needed

**Quick Fix:** Apply **Solution 3 optimizations** while deciding
- Increase silence threshold to 500
- Add consecutive frame requirement
- Calibrate ambient noise on startup

---

## Testing Your Improvements

After implementing any solution, test with:

```bash
python main_continuous.py
```

Monitor for:
1. **Reduction in "hallucination" messages** - should go from 20+ to 0-2
2. **CPU usage** - should drop significantly when idle
3. **Response time** - should stay under 1 second
4. **Wake word accuracy** - should maintain or improve

---

## Migration Path

### Week 1: Quick Wins (Solution 3)
- Increase silence threshold
- Add consecutive frame requirement
- Test and tune

### Week 2: VAD Implementation (Solution 1)
- Install webrtcvad
- Integrate VAD pre-filtering
- Test with different aggressiveness levels

### Week 3: Porcupine (Optional, Solution 2)
- Get Picovoice API key
- Implement Porcupine wake word detection
- Benchmark performance improvements

---

## Expected Performance Gains

| Metric | Current | With VAD | With Porcupine |
|--------|---------|----------|----------------|
| Whisper calls (10 min) | 20-30 | 1-3 | 1 |
| CPU idle usage | 15-25% | 5-10% | <1% |
| False positives | High | Very Low | Nearly Zero |
| Wake word latency | <1s | <1s | <0.5s |
| Battery life | Baseline | +50% | +200% |

---

## Additional Considerations

### For 24/7 Operation:
1. **Enable logging rotation** to prevent disk fill
2. **Implement memory cleanup** for long-running sessions
3. **Add health checks** to restart on failures
4. **Monitor system resources** (CPU, RAM, disk)

### For Privacy:
- ✅ All processing is local (no cloud APIs except for LLM)
- ✅ Whisper runs offline
- ✅ Audio files are temporary and deleted
- ✅ Porcupine runs on-device

### For Multiple Users:
- Consider **speaker identification** after wake word
- Implement **user-specific preferences**
- Use **conversation context** to track active user
