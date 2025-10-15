"""
Test script for chunked transcription performance.
Compares traditional vs chunked transcription timing.
"""

import time
from lib.speech_to_text import SpeechToText

print("="*80)
print("🧪 CHUNKED TRANSCRIPTION TEST")
print("="*80)
print("\nThis test will compare transcription methods:")
print("  • Traditional: Waits for full silence, then transcribes")
print("  • Chunked: Transcribes on short pauses, parallel processing")
print("\nTest scenarios:")
print("  1. Single phrase command (no pauses)")
print("  2. Multi-phrase command (with natural pauses)")
print("  3. Long statement (multiple thoughts)")
print("\n" + "="*80)

# Initialize speech-to-text with chunked mode
print("\n🔧 Initializing with CHUNKED TRANSCRIPTION mode...")
stt = SpeechToText(model_size="base", track_metrics=False, use_faster_whisper=True)
stt.enable_chunked_transcription_mode(max_workers=2)

# Set wake words
wake_words = ["sam", "samantha"]
stt.set_wake_words(wake_words)

# Track activations
activations = []

def test_callback(command_text):
    """Handle voice commands during test."""
    timestamp = time.time()
    activations.append({
        'time': timestamp,
        'command': command_text
    })
    print(f"\n✅ COMMAND RECEIVED: '{command_text}'")
    print(f"   Total time: {timestamp - test_start:.2f}s")

# Instructions
print("\n📋 TEST INSTRUCTIONS:")
print("-" * 80)
print("\nTest 1: Single phrase (no pauses)")
print('  Say: "Sam, what\'s the weather?"')
print("  Expected: Similar timing to traditional mode")

print("\nTest 2: Multi-phrase with pauses")  
print('  Say: "Sam, what\'s the weather" [pause 400ms] "in London?"')
print("  Expected: Faster! First chunk transcribes during pause")

print("\nTest 3: Long statement with thinking pauses")
print('  Say: "Sam, I need to know" [pause] "what the weather" [pause] "will be like tomorrow"')
print("  Expected: Much faster! All early chunks transcribe in parallel")

print("\nPress ENTER when ready to start...")
input()

# Start listening
print("\n🎧 Listening for wake word...")
print("💡 Say your test commands now!")
print("   (Press Ctrl+C when done testing)")
print()

test_start = time.time()

try:
    stt.start_continuous_listening(test_callback)
    
    # Keep running
    while True:
        time.sleep(1)
        
except KeyboardInterrupt:
    print("\n\n🛑 Stopping test...")
    stt.stop_continuous_listening()
    
    # Print summary
    print("\n" + "="*80)
    print("📊 TEST SUMMARY")
    print("="*80)
    print(f"\nTotal activations: {len(activations)}")
    
    for i, activation in enumerate(activations, 1):
        print(f"\n{i}. Command: '{activation['command']}'")
        print(f"   Time from start: {activation['time'] - test_start:.2f}s")
    
    print("\n💡 OBSERVATIONS:")
    print("  • Did multi-phrase commands respond faster?")
    print("  • Did you notice chunks being transcribed in parallel?")
    print("  • Were there any issues with chunk combining?")
    print("\n" + "="*80)
    
    print("\n👋 Test complete!")
