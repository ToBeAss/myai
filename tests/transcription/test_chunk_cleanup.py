"""
Test the chunk cleanup function to demonstrate punctuation fixing.
"""

import re

def clean_chunked_transcript(transcripts: list) -> str:
    """
    Clean and merge chunked transcripts intelligently.
    
    Whisper adds punctuation thinking each chunk is complete, which can create
    awkward combinations like "What's the weather? in London."
    This function cleans up such artifacts.
    """
    if not transcripts:
        return ""
    
    if len(transcripts) == 1:
        return transcripts[0].strip()
    
    cleaned_chunks = []
    
    for i, chunk in enumerate(transcripts):
        chunk = chunk.strip()
        if not chunk:
            continue
        
        # Detect if this looks like a continuation (not a new sentence)
        is_continuation = False
        if i > 0 and chunk:
            # Lowercase start = definitely continuation
            if chunk[0].islower():
                is_continuation = True
            else:
                # Fragment without subject pronoun = likely continuation
                # Check first two words for subject indicators
                words = chunk.lower().split()
                first_words = words[:2] if len(words) >= 2 else words
                
                # Look for actual subject pronouns or sentence connectors
                has_subject = any(word in first_words for word in ['i', 'you', 'he', 'she', 'it', 'we', 'they', 'also', 'and', 'but', 'sam'])
                
                # Fragments starting with "what", "where", etc. without subject = continuation
                # e.g., "what the weather" is part of "know what the weather"
                question_words = ['what', 'where', 'when', 'why', 'how', 'which', 'who']
                if words and words[0] in question_words and not has_subject:
                    is_continuation = True
                # Short fragments without clear subject = continuation
                elif len(chunk) < 20 and not has_subject:
                    is_continuation = True
        
        # If this is a continuation, clean up previous chunk's punctuation
        if is_continuation and cleaned_chunks:
            if cleaned_chunks[-1].endswith(('?', '!', '.')):
                cleaned_chunks[-1] = cleaned_chunks[-1][:-1].strip()
            # Lowercase the first letter since it's a continuation
            if chunk:
                chunk = chunk[0].lower() + chunk[1:]
        
        # For middle chunks (not first, not last) - remove their ending punctuation
        if 0 < i < len(transcripts) - 1:
            if chunk.endswith(('?', '!', '.')):
                chunk = chunk[:-1].strip()
        
        cleaned_chunks.append(chunk)
    
    # Join with spaces
    combined = ' '.join(cleaned_chunks)
    
    # Clean up any remaining double punctuation
    combined = re.sub(r'[.!?]\s+[.!?]', '.', combined)
    
    # If we removed all ending punctuation and the sentence doesn't end with one, add a period
    if combined and not combined[-1] in '.!?,;:':
        # Check if last chunk originally had punctuation
        if transcripts and transcripts[-1].strip() and transcripts[-1].strip()[-1] in '.!?':
            # Keep the original ending punctuation
            combined += transcripts[-1].strip()[-1]
    
    return combined.strip()


print("="*80)
print("🧪 CHUNK CLEANUP DEMONSTRATION")
print("="*80)

test_cases = [
    {
        'name': 'Test 1: Question with continuation',
        'chunks': ["Sam, what's the weather?", "in London."],
        'expected': "Sam, what's the weather in London."
    },
    {
        'name': 'Test 2: Statement with multiple parts',
        'chunks': ["Sam, I need to know.", "What the weather?", "will be like tomorrow."],
        'expected': "Sam, I need to know what the weather will be like tomorrow."
    },
    {
        'name': 'Test 3: Complete sentence (single chunk)',
        'chunks': ["Sam, what's the weather?"],
        'expected': "Sam, what's the weather?"
    },
    {
        'name': 'Test 4: Two complete thoughts',
        'chunks': ["Sam, tell me the weather.", "Also check the forecast."],
        'expected': "Sam, tell me the weather. Also check the forecast."
    },
    {
        'name': 'Test 5: Question split in middle',
        'chunks': ["What's the", "weather like?"],
        'expected': "What's the weather like?"
    }
]

for test in test_cases:
    print(f"\n{test['name']}")
    print("-" * 80)
    print(f"Input chunks:")
    for i, chunk in enumerate(test['chunks'], 1):
        print(f"  {i}. \"{chunk}\"")
    
    result = clean_chunked_transcript(test['chunks'])
    expected = test['expected']
    
    print(f"\nResult:   \"{result}\"")
    print(f"Expected: \"{expected}\"")
    
    if result == expected:
        print("✅ PASS")
    else:
        print(f"❌ FAIL - Mismatch!")

print("\n" + "="*80)
print("💡 KEY INSIGHTS:")
print("-" * 80)
print("  • Removes sentence-ending punctuation from middle chunks")
print("  • Detects lowercase continuations and removes preceding punctuation")
print("  • Preserves intentional sentence boundaries")
print("  • Restores proper ending punctuation")
print("\n" + "="*80)
