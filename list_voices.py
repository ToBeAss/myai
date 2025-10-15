#!/usr/bin/env python3
"""
Utility script to list available Google Cloud TTS voices with pricing information.
Usage: python list_voices.py [language_code]
Examples:
    python list_voices.py           # List all voices
    python list_voices.py en-GB     # List only British English voices
    python list_voices.py en-US     # List only US English voices
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_PATH = PROJECT_ROOT / "src"
if SRC_PATH.exists():
    sys.path.insert(0, str(SRC_PATH))

from myai.tts.text_to_speech import TextToSpeech

def main():
    # Get language code from command line argument if provided
    language_code = sys.argv[1] if len(sys.argv) > 1 else None
    
    print("🔍 Fetching available Google Cloud TTS voices...")
    print("=" * 80)
    
    try:
        # Initialize TTS with a dummy voice just to use the list function
        tts = TextToSpeech(
            voice_name="en-US-Standard-A",
            language_code="en-US",
            enforce_free_tier=False  # Don't enforce for listing
        )
        
        # List voices
        tts.list_available_voices(language_code=language_code, show_pricing=True)
        
        print("\n" + "=" * 80)
        print("💡 Recommendation: Use STANDARD voices for maximum free tier (4M chars/month)")
        print("💡 British English STANDARD voices: en-GB-Standard-A, en-GB-Standard-B, etc.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n💡 Make sure your .env file has GOOGLE_APPLICATION_CREDENTIALS set correctly")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
