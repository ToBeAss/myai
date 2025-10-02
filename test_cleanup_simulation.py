"""
Simulate the chunked transcription cleanup with realistic examples.
Shows how the cleanup function fixes Whisper's punctuation artifacts.
"""

import re

def clean_chunked_transcript(transcripts: list) -> str:
    """Clean and merge chunked transcripts intelligently."""
    if not transcripts:
        return ""
    
    if len(transcripts) == 1:
        return transcripts[0].strip()
    
    cleaned_chunks = []
    
    for i, chunk in enumerate(transcripts):
        chunk = chunk.strip()
        if not chunk:
            continue
        
        # Detect if this looks like a continuation
        is_continuation = False
        if i > 0 and chunk:
            if chunk[0].islower():
                is_continuation = True
            else:
                words = chunk.lower().split()
                first_words = words[:2] if len(words) >= 2 else words
                has_subject = any(word in first_words for word in ['i', 'you', 'he', 'she', 'it', 'we', 'they', 'also', 'and', 'but', 'sam'])
                
                question_words = ['what', 'where', 'when', 'why', 'how', 'which', 'who']
                if words and words[0] in question_words and not has_subject:
                    is_continuation = True
                elif len(chunk) < 20 and not has_subject:
                    is_continuation = True
        
        # If continuation, clean previous chunk and lowercase first letter
        if is_continuation and cleaned_chunks:
            if cleaned_chunks[-1].endswith(('?', '!', '.')):
                cleaned_chunks[-1] = cleaned_chunks[-1][:-1].strip()
            if chunk:
                chunk = chunk[0].lower() + chunk[1:]
        
        # For middle chunks, remove ending punctuation
        if 0 < i < len(transcripts) - 1:
            if chunk.endswith(('?', '!', '.')):
                chunk = chunk[:-1].strip()
        
        cleaned_chunks.append(chunk)
    
    combined = ' '.join(cleaned_chunks)
    combined = re.sub(r'[.!?]\s+[.!?]', '.', combined)
    
    if combined and not combined[-1] in '.!?,;:':
        if transcripts and transcripts[-1].strip() and transcripts[-1].strip()[-1] in '.!?':
            combined += transcripts[-1].strip()[-1]
    
    return combined.strip()


print("="*80)
print("🎯 REALISTIC CHUNKED TRANSCRIPTION SCENARIOS")
print("="*80)
print()

scenarios = [
    {
        "name": "Weather Question with Location",
        "chunks": ["Sam, what's the weather?", "in London?"],
        "without_cleanup": "Sam, what's the weather? in London?",
        "with_cleanup": "Sam, what's the weather in London?"
    },
    {
        "name": "Nested Question",
        "chunks": ["Sam, I need to know.", "What the weather?", "will be like tomorrow."],
        "without_cleanup": "Sam, I need to know. What the weather? will be like tomorrow.",
        "with_cleanup": "Sam, I need to know what the weather will be like tomorrow."
    },
    {
        "name": "Command with Details",
        "chunks": ["Sam, set a reminder.", "for tomorrow morning.", "at 8 AM."],
        "without_cleanup": "Sam, set a reminder. for tomorrow morning. at 8 AM.",
        "with_cleanup": "Sam, set a reminder for tomorrow morning at 8 AM."
    },
    {
        "name": "Multiple Clauses",
        "chunks": ["Tell me about.", "the weather forecast.", "and traffic conditions."],
        "without_cleanup": "Tell me about. the weather forecast. and traffic conditions.",
        "with_cleanup": "Tell me about the weather forecast and traffic conditions."
    },
    {
        "name": "Question Word Continuation",
        "chunks": ["Can you check?", "what time it is?", "in New York?"],
        "without_cleanup": "Can you check? what time it is? in New York?",
        "with_cleanup": "Can you check what time it is in New York?"
    }
]

for i, scenario in enumerate(scenarios, 1):
    print(f"\n📝 Scenario {i}: {scenario['name']}")
    print("-" * 80)
    
    # Show input chunks
    print("\n🔹 Input chunks from Whisper:")
    for j, chunk in enumerate(scenario['chunks'], 1):
        print(f"   Chunk {j}: \"{chunk}\"")
    
    # Show what happens without cleanup
    print(f"\n❌ WITHOUT cleanup (awkward):")
    print(f"   \"{scenario['without_cleanup']}\"")
    
    # Show actual cleanup result
    actual_result = clean_chunked_transcript(scenario['chunks'])
    print(f"\n✅ WITH cleanup (natural):")
    print(f"   \"{actual_result}\"")
    
    # Verify
    if actual_result == scenario['with_cleanup']:
        print(f"\n   ✓ Result matches expected output")
    else:
        print(f"\n   ⚠ Result differs from expected:")
        print(f"      Expected: \"{scenario['with_cleanup']}\"")
        print(f"      Got:      \"{actual_result}\"")

print("\n" + "="*80)
print("📊 SUMMARY")
print("="*80)
print("""
The cleanup function successfully:
  • Detects continuations (lowercase start, question words without subjects)
  • Removes artificial punctuation from previous chunks
  • Lowercases first letter of continuation chunks
  • Preserves intentional sentence boundaries
  • Creates natural-sounding combined transcripts

This solves the issue where Whisper adds sentence-ending punctuation to each
chunk thinking it's complete, which was creating awkward combinations like
"weather? in London" → now becomes "weather in London" ✨
""")
print("="*80)
