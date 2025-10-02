#!/usr/bin/env python3
"""
Analyze failed test cases to understand scoring breakdown
This helps us identify which factors need adjustment
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Create a mock STT class similar to the test file
class MockSTT:
    def __init__(self):
        self.wake_words = ["sam", "samantha"]
        self.flexible_wake_word = True
        self.confidence_threshold = 55
        
    def calculate_confidence_score(self, transcription, wake_word, position):
        """Mock implementation matching speech_to_text.py logic"""
        score = 0
        text_lower = transcription.lower()
        length = len(transcription)
        
        # 1. Position (40 pts max)
        if position < 10:
            score += 40
        else:
            relative_pos = position / length if length > 0 else 0
            if relative_pos < 0.2:
                score += 35
            elif relative_pos > 0.8:
                score += 35
            else:
                score += 20
        
        # 2. Content (30 pts max)
        question_words = ['what', 'where', 'when', 'who', 'why', 'how', 
                         'is', 'are', 'can', 'could', 'would', 'should', 'will']
        command_words = ['tell', 'show', 'find', 'search', 'get', 'play', 
                        'stop', 'set', 'turn', 'open', 'close', 'remind', 
                        'create', 'make', 'help', 'give', 'send']
        
        has_question = any(word in text_lower.split() for word in question_words)
        has_command = any(word in text_lower.split() for word in command_words)
        
        if has_question:
            score += 20
        if has_command:
            score += 10
        if '?' in transcription:
            score += 10
        
        # 3. Grammar (20 pts max)
        conversational_pronouns = ['i ', ' i ', 'my ', 'me ', 'you ', 'your']
        if any(pron in text_lower for pron in conversational_pronouns):
            score += 10
        
        # Intent to engage
        intent_phrases = ['need to ask', 'should ask', 'let me ask', 'want to ask',
                         'going to ask', 'have to ask', 'let\'s ask', 'i\'ll ask']
        has_intent = any(phrase in text_lower for phrase in intent_phrases)
        
        if has_intent:
            score += 25
        else:
            third_person = ['he ', 'she ', 'they ', 'them ', 'his ', 'her ', 'their']
            if any(third in text_lower for third in third_person):
                score -= 15
        
        if not has_intent:
            prepositions = [f' to {wake_word}', f' with {wake_word}', 
                           f' about {wake_word}', f' from {wake_word}']
            if any(prep in text_lower for prep in prepositions):
                score -= 15
        
        if transcription and (transcription[0].isupper() or position < 5):
            score += 5
        
        # 4. Wake word usage (10 pts max)
        wake_word_count = text_lower.count(wake_word)
        if wake_word_count == 1:
            score += 10
        elif wake_word_count > 1:
            score -= 20
        
        possessive_patterns = [f"{wake_word}'s", f"{wake_word}s "]
        if any(poss in text_lower for poss in possessive_patterns):
            score -= 30
        
        # 5. Multi-sentence (10 pts max)
        sentence_endings = text_lower.count('.') + text_lower.count('!') + text_lower.count('?')
        if sentence_endings >= 1:
            score += 10
        
        # 6. Special boost for just wake word
        words_without_wake_word = [w for w in text_lower.split() if w not in self.wake_words]
        if len(words_without_wake_word) <= 1:
            score += 20
        
        # 7. End bonus
        if transcription.strip().endswith(wake_word + '?') or transcription.strip().endswith(wake_word):
            if '?' in transcription or has_question:
                score += 5
        
        return max(0, min(100, score))
    
    def extract_command_with_confidence(self, transcription, wake_words):
        """Extract command with confidence."""
        transcription_lower = transcription.lower()
        
        wake_word_found = None
        wake_word_position = -1
        
        for wake_word in wake_words:
            pos = transcription_lower.find(wake_word)
            if pos != -1:
                wake_word_found = wake_word
                wake_word_position = pos
                break
        
        if not wake_word_found:
            return None, 0, None
        
        confidence = self.calculate_confidence_score(
            transcription, 
            wake_word_found, 
            wake_word_position
        )
        
        return transcription, confidence, wake_word_position

def analyze_test(stt, transcription, should_accept, description):
    """Analyze a single test case and show detailed scoring breakdown"""
    command, confidence, position = stt.extract_command_with_confidence(transcription, stt.wake_words)
    accepted = confidence >= stt.confidence_threshold
    
    print(f"\n{'='*80}")
    print(f"Transcription: \"{transcription}\"")
    print(f"Description: {description}")
    print(f"Expected: {'ACCEPT' if should_accept else 'REJECT'}")
    print(f"Got: {'ACCEPT' if accepted else 'REJECT'} (score: {confidence})")
    print(f"Status: {'✓ PASS' if accepted == should_accept else '✗ FAIL'}")
    print(f"{'='*80}")
    
    # Manual breakdown of scoring factors to understand the issues
    words = transcription.lower().split()
    wake_word_count = sum(1 for w in words if 'sam' in w)
    
    # Analyze position
    wake_word_index = next((i for i, w in enumerate(words) if 'sam' in w), -1)
    if wake_word_index >= 0:
        position_pct = wake_word_index / len(words)
        print(f"\n🎯 Position: word {wake_word_index+1}/{len(words)} ({position_pct*100:.0f}%)")
        if position_pct < 0.15:
            print(f"   → Start position bonus: ~40 pts")
        elif position_pct > 0.8:
            print(f"   → End position bonus: ~35 pts")
        else:
            print(f"   → Middle position: reduced score")
    
    # Analyze content
    question_words = ['what', 'how', 'when', 'where', 'why', 'who', 'which', 'can', 'could', 'would', 'should', 'is', 'are', 'do', 'does']
    has_question_word = any(qw in transcription.lower() for qw in question_words)
    has_question_mark = '?' in transcription
    
    print(f"\n💬 Content:")
    if has_question_word:
        print(f"   ✓ Question word found: +20 pts")
    if has_question_mark:
        print(f"   ✓ Question mark: +10 pts")
    
    # Analyze grammar indicators
    third_person = ['he', 'she', 'his', 'her', 'him', 'their', 'they', 'them']
    conversational = ['you', 'i', 'we', 'me', 'my', 'our']
    prepositions = ['to sam', 'with sam', 'about sam', 'for sam', 'at sam']
    
    has_third_person = any(tp in transcription.lower() for tp in third_person)
    has_conversational = any(conv in transcription.lower() for conv in conversational)
    has_preposition = any(prep in transcription.lower() for prep in prepositions)
    is_possessive = "'s" in transcription or "s'" in transcription
    
    print(f"\n📝 Grammar:")
    if has_conversational:
        print(f"   ✓ Conversational pronouns (you/i/me): +10 pts")
    if has_third_person:
        print(f"   ⚠️  Third person pronouns (he/she/they): -15 pts")
    if has_preposition:
        print(f"   ⚠️  Preposition before wake word: -15 pts")
    if is_possessive:
        print(f"   ⚠️  Possessive form: -30 pts")
    
    # Analyze wake word usage
    print(f"\n🔑 Wake Word Usage:")
    print(f"   Count: {wake_word_count}")
    if wake_word_count == 1:
        print(f"   ✓ Single occurrence: +10 pts")
    elif wake_word_count > 1:
        print(f"   ⚠️  Multiple occurrences: penalty")
    
    # Check for multi-sentence
    sentence_count = transcription.count('.') + transcription.count('!') + transcription.count('?')
    if sentence_count > 0:
        print(f"\n📄 Multi-sentence: +10 pts")
    
    # Special boost
    words_without_wake = [w for w in words if 'sam' not in w.lower()]
    if len(words_without_wake) <= 1:
        print(f"\n⭐ Special: Just wake word alone: +20 pts")
    
    return confidence, accepted == should_accept

def main():
    stt = MockSTT()
    stt.confidence_threshold = 55
    
    print("="*80)
    print("FAILURE ANALYSIS - Understanding Why Tests Fail")
    print("="*80)
    
    # Analyze the failed tests from current test run (9 failures out of 57 tests)
    failed_tests = [
        # UNDER-SCORED (should accept but rejected)
        ("I'm planning a trip. Sam, what's the weather forecast?", True, "Multi-sentence context - UNDER-SCORED"),
        
        # OVER-SCORED (should reject but accepted)
        ("Sam said he would help me", False, "Reporting speech - OVER-SCORED"),
        ("Sam told me about it", False, "Reporting past tense - OVER-SCORED"),
        ("Sam and I went shopping", False, "Past collaborative activity - OVER-SCORED"),
        ("Samantha's idea was great", False, "Possessive with full name - OVER-SCORED"),
        ("I met Sam today", False, "Past encounter - OVER-SCORED"),
        ("I think Sam likes pizza", False, "Opinion about Sam - OVER-SCORED"),
        ("Sam is a nice person", False, "Describing characteristics - OVER-SCORED"),
        ("Tell Sam that Sam should help", False, "Indirect message with multiple wake words - OVER-SCORED"),
    ]
    
    results = []
    for transcription, should_accept, description in failed_tests:
        score, passed = analyze_test(stt, transcription, should_accept, description)
        results.append((transcription, score, should_accept, passed))
    
    # Summary of issues
    print(f"\n\n{'='*80}")
    print("SUMMARY OF ISSUES")
    print("="*80)
    
    print("\n🔴 OVER-SCORED (should be rejected but passed):")
    for trans, score, should_accept, passed in results:
        if not should_accept and not passed:
            print(f"   - \"{trans[:50]}...\" scored {score} (threshold: 55)")
    
    print("\n🔵 UNDER-SCORED (should be accepted but rejected):")
    for trans, score, should_accept, passed in results:
        if should_accept and not passed:
            print(f"   - \"{trans[:50]}...\" scored {score} (threshold: 55)")
    
    print("\n\n📊 RECOMMENDED ADJUSTMENTS:")
    print("="*80)
    print("""
CURRENT STATUS: 84.2% success rate (48/57 passing)
Recent improvement: Intent-to-engage patterns now working! ✅

REMAINING ISSUES:

1. ADD penalties for REPORTING SPEECH patterns:
   - "Sam said..." → -25 pts (reporting what Sam said)
   - "Sam told..." → -25 pts (reporting what Sam told)
   - "Sam asked..." → -25 pts (reporting what Sam asked)
   These are NOT addressing Sam, but talking ABOUT what Sam did.
   
2. ADD penalties for DESCRIPTIVE statements:
   - "Sam is {adjective}" → -25 pts (describing characteristics)
   - "I think Sam..." → -20 pts (opinion about Sam)
   - "I met/saw Sam" → -20 pts (past encounter)
   These describe Sam or report encounters, not engagement.
   
3. ADD penalty for COLLABORATIVE past tense:
   - "Sam and I {past_verb}" → -20 pts (past activity together)
   - Pattern indicates talking about Sam, not to Sam
   
4. FIX possessive detection for ALL wake word variants:
   - Current: Only checks "sam's" and "sams"
   - Need: Check ALL wake words (sam, samantha, etc.) + possessive
   - Keep: -30 pts penalty (appropriate strength)
   
5. ADD penalty for INDIRECT messages:
   - "Tell Sam that..." → -25 pts (message for Sam, not to Sam)
   - User wants to relay a message, not engage directly
   
6. IMPROVE multi-sentence scoring:
   - When wake word appears in sentence 2+, analyze that sentence separately
   - "Context. Sam, question?" should focus scoring on second sentence
   - Current issue: First sentence dilutes score
   
7. Keep third-person penalty at -15 pts:
   - Working well for most cases
   - Intent-to-engage override (+25) properly handles edge cases
""")

if __name__ == "__main__":
    main()
