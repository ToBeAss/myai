#!/usr/bin/env python3
"""
Test Google Cloud TTS pronunciation of numbers with decimals.
This helps identify if the issue is with the TTS voice model itself.
"""

import sys
sys.path.insert(0, '/Users/tobiasmolland/GitHub/myai')

from lib.text_to_speech import TextToSpeech

def test_tts_pronunciation():
    """Test how Google TTS pronounces different number formats."""
    
    test_phrases = [
        # Different ways to write pi
        ("Standard decimal", "The value of pi is 3.14"),
        ("Spelled out", "The value of pi is three point one four"),
        ("With word 'point'", "The value of pi is 3 point 14"),
        
        # Different contexts
        ("In sentence", "The number 3.14 is important."),
        ("Just number", "3.14"),
        ("With 'approximately'", "Approximately 3.14"),
        
        # Other decimals
        ("Different number", "The value is 2.5"),
        ("Money", "It costs $3.14"),
        ("Percentage", "It's 3.14 percent"),
        
        # Compare with no period
        ("No period", "The value is 314"),
        ("Version number", "Version 3.14 is ready"),
    ]
    
    try:
        tts = TextToSpeech(
            voice_name="en-GB-Chirp3-HD-Achernar",  # Your current voice
            language_code="en-GB",
            enforce_free_tier=False
        )
        
        print("="*80)
        print("GOOGLE CLOUD TTS PRONUNCIATION TEST")
        print("="*80)
        print("\nThis will test how the TTS voice pronounces numbers with decimals.")
        print("Listen carefully to see if it says 'point' or just the numbers.\n")
        
        for label, phrase in test_phrases:
            print(f"\n{label}:")
            print(f"  Text: '{phrase}'")
            response = input("  Press ENTER to hear this (or 's' to skip, 'q' to quit): ")
            
            if response.lower() == 'q':
                break
            elif response.lower() == 's':
                continue
            
            tts.speak(phrase)
            
            feedback = input("  How did it sound? (good/bad/notes): ")
            if feedback and feedback.lower() != 'good':
                print(f"  📝 Noted: {feedback}")
        
        print("\n" + "="*80)
        print("Test complete!")
        print("="*80)
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_tts_pronunciation()
