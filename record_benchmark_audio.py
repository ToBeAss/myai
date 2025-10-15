"""
Benchmark Audio Recording Script

Records test audio files with natural speech patterns for benchmarking the pipeline.
Each recording includes wake word detection and realistic pauses that would trigger
the 300ms chunking threshold in production.
"""

import sounddevice as sd
import numpy as np
import wave
import os
from pathlib import Path

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

# Test suite covering different scenarios
TEST_SUITE = [
    # Category 1: Speed Tests (minimal latency baseline)
    ('short_weather', 4, "Hey Sam, what's the weather?"),
    ('short_time', 3, "Hey Sam, what time is it?"),
    
    # Category 2: Chunking Tests (natural pause handling)
    ('medium_timer', 6, "Hey Sam, set a timer for 15 minutes and remind me to check the laundry"),
    ('medium_with_pause', 5, "Hey Sam, can you tell me... what the weather is like?"),
    
    # Category 3: Complexity Tests (realistic load)
    ('long_explanation', 12, "Hey Sam, can you explain quantum entanglement in simple terms?"),
    ('complex_with_numbers', 7, "Hey Sam, what's 15 times 23.5 plus 142?"),
]

def main():
    """Record all test audio files."""
    print("="*70)
    print("🎙️  BENCHMARK AUDIO RECORDING SUITE")
    print("="*70)
    print("\nTips for best results:")
    print("  • Speak naturally with realistic pauses")
    print("  • Say 'Hey Sam' clearly (wake word)")
    print("  • Use the same environment/microphone for consistency")
    print("  • Natural pauses of ~300ms will trigger chunking\n")
    
    recorded = []
    
    for name, duration, text in TEST_SUITE:
        filepath = record_benchmark_audio(name, duration, text)
        recorded.append((name, filepath))
    
    print("="*70)
    print("✅ All test recordings complete!")
    print("="*70)
    print("\nRecorded files:")
    for name, filepath in recorded:
        print(f"  • {name}: {filepath}")
    
    print("\n🚀 Next steps:")
    print("  1. Run: python benchmark_pipeline.py tests/audio/short_weather.wav")
    print("  2. Or test all: python benchmark_pipeline.py tests/audio/*.wav")

if __name__ == "__main__":
    main()
