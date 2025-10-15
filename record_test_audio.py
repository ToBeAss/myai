#!/usr/bin/env python3
"""
Simple audio recording tool to create test files for volume boost testing.

This script records audio from your microphone, saves it to a WAV file,
and optionally plays it back so you can verify the recording quality.
You can then test the audio with test_volume_boost.py.

Usage:
    python record_test_audio.py                    # Interactive mode (recommended)
    python record_test_audio.py 5                  # Record for 5 seconds
    python record_test_audio.py 5 my_test.wav     # Custom filename

Features:
    - Records audio at the same quality as your AI assistant (16kHz, mono)
    - Shows audio statistics (peak/RMS levels)
    - Plays back recordings immediately for verification
    - Suggests whether volume boost will help
    - Interactive mode for multiple recordings at different volumes
"""

import pyaudio
import wave
import sys
import time
import numpy as np
from datetime import datetime
import threading


def play_audio(filename: str):
    """
    Play back an audio file.
    
    :param filename: Path to WAV file to play
    """
    try:
        print(f"\n🔊 Playing back: {filename}")
        
        # Open the audio file
        wf = wave.open(filename, 'rb')
        
        # Initialize PyAudio
        audio = pyaudio.PyAudio()
        
        # Open stream for playback
        stream = audio.open(
            format=audio.get_format_from_width(wf.getsampwidth()),
            channels=wf.getnchannels(),
            rate=wf.getframerate(),
            output=True
        )
        
        # Read and play audio in chunks
        CHUNK = 1024
        data = wf.readframes(CHUNK)
        
        while data:
            stream.write(data)
            data = wf.readframes(CHUNK)
        
        # Cleanup
        stream.stop_stream()
        stream.close()
        audio.terminate()
        wf.close()
        
        print("✅ Playback complete!")
        
    except Exception as e:
        print(f"❌ Error playing audio: {e}")


def record_audio(duration_seconds: int = 5, output_filename: str = None, play_back: bool = True) -> str:
    """
    Record audio from microphone and save to WAV file.
    
    :param duration_seconds: How long to record (seconds)
    :param output_filename: Output filename (auto-generated if None)
    :param play_back: Whether to play back the recording after saving
    :return: Path to saved audio file
    """
    # Audio settings (match your speech_to_text.py settings)
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    
    # Generate filename if not provided
    if output_filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"test_audio_{timestamp}.wav"
    
    print("="*70)
    print("🎤 AUDIO RECORDER FOR VOLUME BOOST TESTING")
    print("="*70)
    print(f"\n📁 Output file: {output_filename}")
    print(f"⏱️  Duration: {duration_seconds} seconds")
    print(f"🎚️  Sample rate: {RATE}Hz")
    print(f"📊 Channels: {CHANNELS} (mono)")
    print(f"🔊 Format: 16-bit PCM")
    
    # Initialize PyAudio
    audio = pyaudio.PyAudio()
    
    try:
        # Open stream
        stream = audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK
        )
        
        print("\n" + "="*70)
        print("🔴 RECORDING STARTED")
        print("="*70)
        print(f"\n💡 Tips for testing volume boost:")
        print("   - Speak at WHISPER-QUIET volume to really test the boost")
        print("   - The quieter, the more dramatic the difference will be")
        print(f"\n💬 Suggested challenging phrases:")
        print("   SHORT: 'Hey Sam, my name is Tobias'")
        print("   MEDIUM: 'Hey Sam, whether the weather is fifteen or fifty degrees'")
        print("   LONG: 'Sam, I need to check if their schedule shows they're going there'")
        print(f"\n⏰ Recording for {duration_seconds} seconds...")
        
        frames = []
        
        # Record for specified duration
        for i in range(0, int(RATE / CHUNK * duration_seconds)):
            data = stream.read(CHUNK, exception_on_overflow=False)
            frames.append(data)
            
            # Progress indicator
            elapsed = (i + 1) * CHUNK / RATE
            remaining = duration_seconds - elapsed
            if int(elapsed) != int(elapsed - CHUNK / RATE):  # Every second
                print(f"   Recording... {remaining:.0f} seconds remaining")
        
        print("\n✅ Recording complete!")
        
        # Stop and close stream
        stream.stop_stream()
        stream.close()
        
        # Save audio to file
        print(f"💾 Saving to {output_filename}...")
        with wave.open(output_filename, 'wb') as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(audio.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(frames))
        
        # Calculate audio statistics
        audio_data = np.frombuffer(b''.join(frames), dtype=np.int16)
        audio_float = audio_data.astype(np.float32) / 32768.0
        
        peak = np.abs(audio_float).max()
        rms = np.sqrt(np.mean(audio_float ** 2))
        
        print("\n" + "="*70)
        print("📊 AUDIO STATISTICS")
        print("="*70)
        print(f"Peak level: {peak:.4f}")
        print(f"RMS level:  {rms:.4f}")
        
        if peak < 0.3:
            print("\n💡 Audio is VERY QUIET - Volume boost will likely help significantly!")
        elif peak < 0.6:
            print("\n💡 Audio is QUIET - Volume boost may help")
        elif peak < 0.9:
            print("\n✓  Audio is NORMAL - Volume boost will have minimal effect")
        else:
            print("\n⚠️  Audio is LOUD - Volume boost not needed")
        
        print("="*70)
        print(f"\n✅ Saved: {output_filename}")
        print(f"\n🧪 Test with volume boost:")
        print(f"   python test_volume_boost.py {output_filename}")
        print("="*70)
        
        # Play back the recording if requested
        if play_back:
            play_back_choice = input("\n▶️  Play back the recording? (Y/n): ").strip().lower()
            if play_back_choice not in ['n', 'no']:
                play_audio(output_filename)
        
        return output_filename
        
    except Exception as e:
        print(f"\n❌ Error recording audio: {e}")
        return None
        
    finally:
        audio.terminate()


def interactive_mode():
    """Interactive recording mode with user prompts."""
    print("="*70)
    print("🎤 INTERACTIVE AUDIO RECORDER")
    print("="*70)
    print("\nThis tool records audio for testing volume boost.")
    print("You can create multiple recordings at different volumes.")
    
    recordings = []
    
    while True:
        print("\n" + "-"*70)
        duration = input("\n⏱️  How many seconds to record? (default: 5, q to quit): ").strip()
        
        if duration.lower() in ['q', 'quit', 'exit']:
            break
        
        try:
            duration_sec = int(duration) if duration else 5
        except ValueError:
            print("❌ Invalid duration, using 5 seconds")
            duration_sec = 5
        
        if duration_sec < 1 or duration_sec > 60:
            print("❌ Duration must be between 1-60 seconds")
            continue
        
        # Optional custom filename
        custom_name = input("📁 Custom filename? (press Enter for auto-generated): ").strip()
        filename = custom_name if custom_name else None
        
        print("\n🎙️  Get ready...")
        print("   Speak clearly at the volume level you want to test")
        time.sleep(2)
        
        result = record_audio(duration_sec, filename, play_back=True)
        if result:
            recordings.append(result)
        
        another = input("\n🔄 Record another? (y/n): ").strip().lower()
        if another not in ['y', 'yes']:
            break
    
    # Summary
    if recordings:
        print("\n" + "="*70)
        print("📋 RECORDING SESSION COMPLETE")
        print("="*70)
        print(f"\n✅ Created {len(recordings)} recording(s):")
        for i, rec in enumerate(recordings, 1):
            print(f"   {i}. {rec}")
        
        print("\n🧪 Test all recordings:")
        for rec in recordings:
            print(f"   python test_volume_boost.py {rec}")
        
        # Option to play back all recordings
        if len(recordings) > 1:
            play_all = input("\n▶️  Play back all recordings? (y/N): ").strip().lower()
            if play_all in ['y', 'yes']:
                for i, rec in enumerate(recordings, 1):
                    print(f"\n▶️  Playing recording {i}/{len(recordings)}: {rec}")
                    play_audio(rec)
                    if i < len(recordings):
                        time.sleep(1)  # Brief pause between recordings
        
        print("="*70)


def main():
    """Main entry point."""
    if len(sys.argv) == 1:
        # No arguments - interactive mode
        interactive_mode()
    elif sys.argv[1] in ['-h', '--help', 'help']:
        print(__doc__)
        sys.exit(0)
    else:
        # Command-line mode
        try:
            duration = int(sys.argv[1])
        except ValueError:
            print(f"❌ Error: '{sys.argv[1]}' is not a valid duration")
            print("Usage: python record_test_audio.py [duration] [filename]")
            sys.exit(1)
        
        filename = sys.argv[2] if len(sys.argv) > 2 else None
        
        print("\n🎙️  Get ready to record...")
        print("   Speak clearly at the volume level you want to test")
        time.sleep(2)
        
        record_audio(duration, filename, play_back=True)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Recording interrupted by user")
        sys.exit(0)
