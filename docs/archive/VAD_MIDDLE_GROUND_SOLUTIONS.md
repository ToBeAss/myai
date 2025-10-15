# VAD Aggressiveness "Middle Ground" Solutions

## The Challenge

WebRTC VAD only supports integer levels **0, 1, 2, 3** - no 1.5 option exists.

**Your findings:**
- 🌙 **Evening (quiet):** Level 2 filters too aggressively, level 1 works great
- ☀️ **Daytime (louder):** Level 2 would probably work better

---

## Solution 1: Time-Based Auto-Adjustment (RECOMMENDED)

Automatically switch VAD aggressiveness based on time of day.

### Implementation:

Add this method to the `SpeechToText` class in `lib/speech_to_text.py`:

```python
def get_adaptive_vad_aggressiveness(self) -> int:
    """
    Get VAD aggressiveness based on time of day.
    
    Evening/night (20:00-08:00): Level 1 (more sensitive for quiet environments)
    Daytime (08:00-20:00): Level 2 (more filtering for ambient noise)
    
    :return: VAD aggressiveness level (0-3)
    """
    current_hour = datetime.now().hour
    
    # Evening/Night hours: 20:00 (8 PM) to 08:00 (8 AM) - Use level 1
    if current_hour >= 20 or current_hour < 8:
        return 1  # More sensitive for quiet evening
    else:
        return 2  # More filtering for daytime ambient noise
```

Then update your `__init__` to support "auto" mode:

```python
def __init__(self, 
             # ... other params ...
             vad_aggressiveness: int | str = "auto"):  # Now accepts "auto"
    """
    :param vad_aggressiveness: VAD filtering level (0-3) or "auto" for time-based adjustment
    """
    # ... existing initialization code ...
    
    # Initialize WebRTC Voice Activity Detection
    self.enable_vad = enable_vad
    self.vad = None
    self.vad_frame_duration = 30
    self.vad_frame_size = int(self.rate * self.vad_frame_duration / 1000)
    self.vad_aggressiveness_setting = vad_aggressiveness  # Store user setting
    
    if enable_vad:
        try:
            # Determine initial aggressiveness
            if vad_aggressiveness == "auto":
                initial_level = self.get_adaptive_vad_aggressiveness()
                print(f"🎯 Voice Activity Detection: ENABLED (auto mode, current: {initial_level}/3)")
            else:
                initial_level = vad_aggressiveness
                print(f"🎯 Voice Activity Detection: ENABLED (aggressiveness: {initial_level}/3)")
            
            self.vad = webrtcvad.Vad(initial_level)
            self.last_vad_adjustment = time.time()
            self.vad_check_interval = 300  # Check every 5 minutes if we should adjust
        except Exception as e:
            print(f"⚠️ Could not initialize VAD: {e}. Continuing without VAD...")
            self.enable_vad = False
```

Then add a method to update VAD dynamically:

```python
def update_vad_aggressiveness_if_needed(self):
    """
    Check if we should update VAD aggressiveness based on time of day.
    Only runs if in "auto" mode and enough time has passed.
    """
    if not self.enable_vad or self.vad_aggressiveness_setting != "auto":
        return
    
    # Only check every 5 minutes to avoid constant adjustments
    if time.time() - self.last_vad_adjustment < self.vad_check_interval:
        return
    
    new_level = self.get_adaptive_vad_aggressiveness()
    
    # Check if we need to change (compare with current VAD mode)
    # Note: WebRTC VAD doesn't expose current mode, so we track it
    if not hasattr(self, '_current_vad_level'):
        self._current_vad_level = new_level
    
    if new_level != self._current_vad_level:
        try:
            self.vad = webrtcvad.Vad(new_level)
            self._current_vad_level = new_level
            print(f"🔄 VAD adjusted to level {new_level} for current time of day")
        except Exception as e:
            print(f"⚠️ Could not adjust VAD: {e}")
    
    self.last_vad_adjustment = time.time()
```

Finally, call this in your `_continuous_listen_loop`:

```python
def _continuous_listen_loop(self):
    """Main loop for continuous listening."""
    try:
        # ... existing setup code ...
        
        while self.is_listening:
            try:
                # Check if we should adjust VAD (every 5 minutes)
                self.update_vad_aggressiveness_if_needed()
                
                # ... rest of loop ...
```

### Usage in `main_continuous.py`:

```python
# Automatic adjustment based on time of day
stt = SpeechToText(
    model_size="base",
    track_metrics=False,
    vad_aggressiveness="auto"  # Automatically adjusts!
)
```

**Result:**
- 🌙 **8 PM - 8 AM:** Uses level 1 (sensitive for quiet evenings)
- ☀️ **8 AM - 8 PM:** Uses level 2 (filters daytime noise)
- 🔄 **Adjusts automatically** every 5 minutes if time bracket changes

---

## Solution 2: Hybrid Approach (VAD Level 1 + Extra Filtering)

Keep VAD at level 1, but add extra filtering logic to simulate "1.5":

```python
def _is_speech_vad_hybrid(self, audio_frame: bytes, volume: float) -> bool:
    """
    Hybrid VAD check: Uses level 1 VAD + volume-based adjustment.
    Simulates a "level 1.5" by being stricter during low volumes.
    
    :param audio_frame: Raw audio bytes
    :param volume: Current volume level
    :return: True if speech detected
    """
    if not self.enable_vad or self.vad is None:
        return True
    
    try:
        frame_size_bytes = self.vad_frame_size * 2
        if len(audio_frame) < frame_size_bytes:
            return False
        
        frame = audio_frame[:frame_size_bytes]
        vad_result = self.vad.is_speech(frame, self.rate)
        
        # Extra filtering: If volume is borderline, require stronger VAD confidence
        # This simulates a "level 1.5"
        if 400 < volume < 600:  # Borderline volume range
            # In borderline cases, be more strict
            # We can't make VAD stricter, but we can require consecutive positives
            # (This is already handled in the main loop with vad_required_frames)
            return vad_result
        
        return vad_result
    except Exception as e:
        return True
```

Then adjust `vad_required_frames` dynamically:

```python
def _continuous_listen_loop(self):
    """Main loop with adaptive consecutive frame requirement."""
    # ... setup ...
    
    # Adaptive consecutive frame requirement
    vad_speech_frames = 0
    
    # Function to get required frames based on current conditions
    def get_required_frames():
        current_hour = datetime.now().hour
        # Evening: require 3 frames (more sensitive)
        # Daytime: require 4-5 frames (more filtering)
        if current_hour >= 20 or current_hour < 8:
            return 3  # Evening - more sensitive
        else:
            return 4  # Daytime - more filtering
    
    while self.is_listening:
        vad_required_frames = get_required_frames()  # Update each iteration
        
        # ... rest of loop uses vad_required_frames ...
```

**Result:** Simulates "level 1.5" by keeping VAD at 1 but requiring more consecutive positive frames during daytime.

---

## Solution 3: Manual Toggle Command

Add a keyboard shortcut or voice command to toggle VAD levels on the fly:

```python
def toggle_vad_level(self):
    """Toggle between VAD level 1 and 2."""
    if not self.enable_vad:
        return
    
    if not hasattr(self, '_current_vad_level'):
        self._current_vad_level = 1
    
    # Toggle between 1 and 2
    new_level = 2 if self._current_vad_level == 1 else 1
    
    try:
        self.vad = webrtcvad.Vad(new_level)
        self._current_vad_level = new_level
        print(f"🔄 VAD manually switched to level {new_level}")
        return f"VAD switched to level {new_level}"
    except Exception as e:
        return f"Error switching VAD: {e}"
```

Then add a keyboard shortcut in `main_continuous.py`:

```python
import keyboard

def toggle_vad():
    """Toggle VAD level with keyboard shortcut."""
    result = stt.toggle_vad_level()
    print(f"\n{result}\n")

# Set up keyboard shortcut (Ctrl+V to toggle)
keyboard.add_hotkey('ctrl+v', toggle_vad)

print("💡 Press Ctrl+V to toggle VAD level between 1 and 2")
```

---

## Solution 4: Ambient Noise Calibration

Dynamically set VAD based on ambient noise level at startup:

```python
def calibrate_vad_level(self, duration: float = 3.0) -> int:
    """
    Calibrate VAD aggressiveness based on ambient noise.
    
    :param duration: Seconds to sample ambient noise
    :return: Recommended VAD level
    """
    print(f"🎧 Calibrating VAD based on ambient noise ({duration}s)...")
    
    audio = pyaudio.PyAudio()
    stream = audio.open(
        format=self.audio_format,
        channels=self.channels,
        rate=self.rate,
        input=True,
        frames_per_buffer=self.chunk
    )
    
    volumes = []
    end_time = time.time() + duration
    
    while time.time() < end_time:
        data = stream.read(self.chunk, exception_on_overflow=False)
        audio_chunk = np.frombuffer(data, dtype=np.int16)
        volume = np.sqrt(np.mean(audio_chunk.astype(np.float32)**2))
        volumes.append(volume)
    
    stream.stop_stream()
    stream.close()
    audio.terminate()
    
    avg_noise = np.mean(volumes)
    
    # Determine VAD level based on ambient noise
    if avg_noise < 100:
        level = 0  # Very quiet - be very sensitive
    elif avg_noise < 200:
        level = 1  # Quiet - moderately sensitive
    elif avg_noise < 400:
        level = 2  # Normal - balanced
    else:
        level = 3  # Noisy - aggressive filtering
    
    print(f"✅ Ambient noise: {avg_noise:.0f}, recommended VAD level: {level}")
    return level
```

Use at startup:

```python
# In __init__ or before starting continuous listening
if vad_aggressiveness == "auto":
    calibrated_level = self.calibrate_vad_level()
    self.vad = webrtcvad.Vad(calibrated_level)
```

---

## Comparison Table

| Solution | Pros | Cons | Best For |
|----------|------|------|----------|
| **Time-Based Auto** | ✅ Set and forget<br>✅ Matches natural quiet/busy times | ❌ Fixed schedule<br>❌ Doesn't adapt to environment | Regular home use |
| **Hybrid + Extra Frames** | ✅ Simulates "1.5"<br>✅ Fine control | ❌ More complex<br>❌ Tuning needed | Power users |
| **Manual Toggle** | ✅ User control<br>✅ Instant adjustment | ❌ Requires intervention<br>❌ Easy to forget | Variable environments |
| **Noise Calibration** | ✅ Adapts to environment<br>✅ Automatic | ❌ Only at startup<br>❌ Slow to adapt | Changing locations |

---

## My Recommendation for You

Based on your usage pattern (evening = quieter, daytime = louder), **Solution 1 (Time-Based Auto)** is perfect:

```python
# In main_continuous.py
stt = SpeechToText(
    model_size="base",
    track_metrics=False,
    vad_aggressiveness="auto"  # 🎯 Automatically adjusts!
)
```

**Why:**
1. Matches your natural environment (evening = quiet, day = busy)
2. Zero maintenance - set once, works forever
3. Adjusts every 5 minutes during transition times
4. You can customize the hours if needed

**Custom Schedule Example:**
```python
# Adjust the times in get_adaptive_vad_aggressiveness()
if current_hour >= 22 or current_hour < 7:  # 10 PM - 7 AM
    return 1  # Very quiet night hours
elif current_hour >= 7 and current_hour < 9:  # 7 AM - 9 AM
    return 1  # Early morning, still quiet
elif current_hour >= 21 and current_hour < 22:  # 9 PM - 10 PM  
    return 1  # Winding down
else:  # 9 AM - 9 PM
    return 2  # Active daytime hours
```

---

## Quick Implementation

Would you like me to implement the **time-based auto-adjustment** (Solution 1) for you? It's the cleanest solution and matches your needs perfectly!

Just say the word and I'll add the necessary methods to your `speech_to_text.py` file. 🚀
