#!/usr/bin/env python3
"""
VAD test script for manual validation.

This module requires microphone input and user interaction. Execute directly
with `python tests/manual/vad_demo.py` when you want to validate VAD behavior.
"""

import webrtcvad
import pyaudio
import numpy as np
import time

def test_vad():
    """Test VAD with live audio to show filtering in action."""
    
    print("="*60)
    print("🎯 WebRTC VAD Test")
    print("="*60)
    print()
    
    # Initialize VAD with different aggressiveness levels
    vad_levels = [0, 1, 2, 3]
    vads = {level: webrtcvad.Vad(level) for level in vad_levels}
    
    print("✅ VAD initialized with all aggressiveness levels (0-3)")
    print()
    print("📋 Test Instructions:")
    print("   1. The script will listen for 10 seconds")
    print("   2. Try making different sounds:")
    print("      - Say something (speech)")
    print("      - Clap your hands (non-speech)")
    print("      - Type on keyboard (non-speech)")
    print("      - Close a door (non-speech)")
    print("      - Cough or clear throat (speech-like)")
    print()
    input("Press Enter to start 10-second test...")
    print()
    
    # Audio settings
    rate = 16000
    chunk = 1024
    frame_duration = 30  # ms
    frame_size = int(rate * frame_duration / 1000)
    
    # Initialize audio
    audio = pyaudio.PyAudio()
    stream = audio.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=rate,
        input=True,
        frames_per_buffer=chunk
    )
    
    print("🎤 Listening... (10 seconds)")
    print()
    print("Format: Volume | VAD0 | VAD1 | VAD2 | VAD3")
    print("-" * 60)
    
    # Test for 10 seconds
    start_time = time.time()
    frame_count = 0
    
    speech_detections = {level: 0 for level in vad_levels}
    total_frames = 0
    
    while time.time() - start_time < 10.0:
        # Read audio
        data = stream.read(chunk, exception_on_overflow=False)
        audio_chunk = np.frombuffer(data, dtype=np.int16)
        
        # Calculate volume
        volume = np.sqrt(np.mean(audio_chunk.astype(np.float32)**2))
        
        # Check VAD for each aggressiveness level
        frame_size_bytes = frame_size * 2
        if len(data) >= frame_size_bytes:
            frame = data[:frame_size_bytes]
            
            vad_results = {}
            for level in vad_levels:
                try:
                    is_speech = vads[level].is_speech(frame, rate)
                    vad_results[level] = is_speech
                    if is_speech:
                        speech_detections[level] += 1
                except:
                    vad_results[level] = False
            
            total_frames += 1
            
            # Print results every 10 frames (reduce spam)
            frame_count += 1
            if frame_count % 10 == 0:
                vol_bar = "█" * int(volume / 100)
                vad_str = " | ".join([
                    "✅" if vad_results[level] else "❌" 
                    for level in vad_levels
                ])
                print(f"{volume:4.0f} {vol_bar:10s} | {vad_str}")
        
        time.sleep(0.01)
    
    stream.stop_stream()
    stream.close()
    audio.terminate()
    
    print("-" * 60)
    print()
    print("📊 Results Summary:")
    print()
    for level in vad_levels:
        percentage = (speech_detections[level] / total_frames * 100) if total_frames > 0 else 0
        print(f"   VAD Level {level}: {speech_detections[level]}/{total_frames} frames detected as speech ({percentage:.1f}%)")
    print()
    print("💡 Interpretation:")
    print("   - Level 0: Most sensitive (catches soft speech + some noise)")
    print("   - Level 1: Moderate (good for quiet environments)")
    print("   - Level 2: Balanced (recommended for normal use)")
    print("   - Level 3: Aggressive (best for noisy environments)")
    print()
    print("🎯 Recommended: Use level 2 for balanced filtering")
    print()
    print("="*60)

if __name__ == "__main__":
    try:
        test_vad()
    except KeyboardInterrupt:
        print("\n\n⏹️  Test stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure:")
        print("  1. webrtcvad is installed: pip install webrtcvad")
        print("  2. Microphone is connected and working")
        print("  3. Microphone permissions are granted")
