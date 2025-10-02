#!/usr/bin/env python3
"""
Debug script to test sentence chunking behavior.
This helps identify if issues are from chunking logic or TTS voice interpretation.
"""

import sys
sys.path.insert(0, '/Users/tobiasmolland/GitHub/myai')

from lib.text_to_speech import TextToSpeech

def test_chunking(text):
    """Test how text would be chunked."""
    print(f"\n{'='*80}")
    print(f"Testing: {text}")
    print(f"{'='*80}")
    
    # Create a simple token generator that simulates streaming
    class Token:
        def __init__(self, content):
            self.content = content
    
    def token_generator(text):
        # Simulate token-by-token streaming
        for char in text:
            yield Token(char)
    
    # Initialize TTS (won't actually speak, just test chunking)
    try:
        tts = TextToSpeech(
            voice_name="en-US-Standard-A",
            language_code="en-US",
            enforce_free_tier=False
        )
        
        # Track chunks
        chunks = []
        buffer = ""
        min_chunk_size = 30
        
        for token in token_generator(text):
            buffer += token.content
            
            # Check if we have potential sentence boundaries
            if any(c in buffer for c in ".!?"):
                # Find the last valid sentence boundary
                last_chunk_idx = tts._find_sentence_boundary(buffer, ".!?")
                
                if last_chunk_idx >= 0:
                    # Extract the complete sentence(s)
                    to_speak = buffer[:last_chunk_idx + 1].strip()
                    
                    # Only chunk if we have substantial content (prevents tiny fragments)
                    if len(to_speak) >= min_chunk_size:
                        chunks.append(to_speak)
                        buffer = buffer[last_chunk_idx + 1:]
        
        # Add any remaining buffer
        if buffer.strip():
            chunks.append(buffer.strip())
        
        print(f"\nTotal chunks: {len(chunks)}")
        for i, chunk in enumerate(chunks, 1):
            print(f"\nChunk {i} ({len(chunk)} chars):")
            print(f"  '{chunk}'")
        
        # Now test if TTS says it correctly
        print(f"\n{'='*80}")
        print("Testing actual TTS pronunciation...")
        print(f"{'='*80}")
        
        for i, chunk in enumerate(chunks, 1):
            print(f"\nSpeaking chunk {i}: '{chunk}'")
            response = input("Press ENTER to hear this chunk (or 's' to skip): ")
            if response.lower() != 's':
                tts.speak(chunk)
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Test cases
    test_cases = [
        "The value of pi is 3.14159.",
        "The president is Donald J. Trump.",
        "Dr. Smith said the result is 3.14 exactly.",
        "The current U.S. president is Donald J. Trump. He was elected in 2016.",
    ]
    
    if len(sys.argv) > 1:
        # Custom test from command line
        test_chunking(" ".join(sys.argv[1:]))
    else:
        # Run all test cases
        for test in test_cases:
            test_chunking(test)
            print("\n")
