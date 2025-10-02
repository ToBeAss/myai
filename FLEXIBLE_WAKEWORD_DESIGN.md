# Flexible Wake Word System - Design Document

## Overview

This document outlines the design and implementation of a flexible wake word detection system that allows natural wake word placement anywhere in a sentence, with intelligent confidence scoring to prevent false activations.

---

## 🎯 Goals

1. **Natural Interaction**: Allow wake word placement anywhere in a sentence
   - Start: "Sam, what's the weather?"
   - Middle: "Could you tell me, Sam, what's the weather?"
   - End: "What's the weather, Sam?"

2. **Context Preservation**: Keep entire transcription intact
   - No removal of wake word
   - Preserve all conversational context and tone
   - Let LLM handle natural language processing

3. **False Positive Protection**: Confidence scoring to distinguish real activations from casual mentions
   - "Sam, help me" → HIGH confidence → Activate ✅
   - "I was talking to Sam yesterday" → LOW confidence → Ignore 🚫

4. **Analytics & Learning**: Track performance metrics
   - True Positives (TP): Correct activations
   - False Positives (FP): Wrong activations
   - False Negatives (FN): Missed activations
   - True Negatives (TN): Correctly ignored mentions

---

## 📊 Confidence Scoring System

### Scoring Formula
```
Confidence Score = Σ(weighted factors)
Range: 0-100 points
```

### Factor Breakdown

#### 1. Wake Word Position (40 points max)
Determines how naturally the wake word is positioned for a command:

- **Start of transcription (0-10 chars)**: +40 points ✅
  - Example: "Sam, what's the weather?"
  - Most reliable activation pattern
  
- **First 20% of transcription**: +35 points ✅
  - Example: "Hey Sam, can you help me?"
  - Natural conversational pattern

- **Last 20% of transcription**: +30 points ⚠️
  - Example: "What's the weather, Sam?"
  - Natural but slightly more ambiguous

- **Middle 60% of transcription**: +20 points ⚠️
  - Example: "Could you, Sam, tell me the weather?"
  - Less common, potentially conversational reference

#### 2. Content Analysis (30 points max)
Analyzes whether the transcription contains command/question patterns:

**Question Words** (+15 points):
- what, where, when, who, why, how
- is, are, can, could, would, should
- Example: "Sam, **what's** the weather?"

**Command Verbs** (+10 points):
- tell, show, find, search, get, play, stop
- set, turn, open, close, remind
- Example: "Sam, **tell** me about the news"

**Question Mark** (+5 points):
- Explicit question indicator
- Example: "What's the time, Sam**?**"

#### 3. Grammar & Context Analysis (20 points max)

**Conversational Indicators** (+10 points):
- First person: "I", "me", "my"
- Second person: "you", "your"
- Example: "Sam, what's **your** weather forecast?"
- Indicates direct address to assistant

**Third Person References** (-15 points):
- "he", "she", "they", "them", "his", "her", "their"
- Example: "Sam said **he** would call"
- Indicates talking ABOUT someone, not TO them

**Prepositions with Wake Word** (-15 points):
- "to Sam", "with Sam", "about Sam", "from Sam"
- Example: "I was talking **to Sam** yesterday"
- Indicates reference, not activation

**Proper Sentence Structure** (+5 points):
- Capitalized first letter OR wake word within first 5 chars
- Indicates intentional statement

#### 4. Wake Word Usage (10 points max)

**Single Occurrence** (+10 points):
- Wake word appears exactly once
- Clear activation intent

**Multiple Occurrences** (-20 points):
- Wake word appears 2+ times
- Ambiguous which one is the activation trigger
- Example: "Tell Sam about Sam's project"

**Possessive Form** (-30 points):
- "Sam's laptop", "Samantha's idea"
- Clear indication of reference, not activation

#### 5. Multi-Sentence Bonus (10 points max)

**Multiple Sentences** (+10 points):
- Contains sentence endings (. ! ?)
- Example: "I felt rain earlier. What's the forecast, Sam?"
- Multi-sentence with wake word = likely intentional activation

**Logical Context Flow** (+5 points bonus):
- Sentences form coherent request
- Example: "I'm planning a trip. Sam, what's the weather forecast?"

---

## 🎬 Example Scenarios

### High Confidence Activations (80-100)

#### Example 1: Traditional Format
```
Transcription: "Sam, what's the weather?"
Wake Word Position: 0 (start)
Analysis:
  - Position: Start (+40)
  - Question word "what" (+15)
  - Proper structure (+5)
  - Single occurrence (+10)
Confidence: 70
Action: ACCEPT ✅
```

#### Example 2: Multi-Sentence Context
```
Transcription: "I think I felt some rain just now. Sam, what is the forecast saying?"
Wake Word Position: 38 (after sentence boundary)
Analysis:
  - Position: Middle, after sentence (+20)
  - Question word "what" (+15)
  - Multi-sentence (+10)
  - Question mark (+5)
  - Single occurrence (+10)
  - First person "I" (+10)
Confidence: 70
Action: ACCEPT ✅
```

#### Example 3: End Position
```
Transcription: "What's the weather like today, Sam?"
Wake Word Position: 31 (end)
Analysis:
  - Position: End (+30)
  - Question word "what" (+15)
  - Proper structure (+5)
  - Single occurrence (+10)
  - Question mark (+5)
Confidence: 65
Action: ACCEPT ✅
```

### Medium Confidence (60-79)

#### Example 4: Just Wake Word
```
Transcription: "Sam"
Wake Word Position: 0
Analysis:
  - Position: Start (+40)
  - No content (0)
  - Single occurrence (+10)
Confidence: 50
Action: ASK FOR CONFIRMATION ❓
Response: Play gentle chime or say "Yes?"
```

#### Example 5: Casual End Mention
```
Transcription: "I need to check the weather, Sam"
Wake Word Position: 33
Analysis:
  - Position: End (+30)
  - Command verb "check" (+10)
  - First person "I" (+10)
  - Single occurrence (+10)
Confidence: 60
Action: ACCEPT WITH CAUTION ⚠️
```

### Low Confidence - Ignore (0-39)

#### Example 6: Conversational Reference
```
Transcription: "I was talking to Sam yesterday"
Wake Word Position: 17
Analysis:
  - Position: Middle (+20)
  - Preposition "to Sam" (-15)
  - Past tense, casual conversation
  - First person "I" (+10)
  - Single occurrence (+10)
Confidence: 25
Action: IGNORE 🚫
```

#### Example 7: Possessive
```
Transcription: "Sam's laptop is broken"
Wake Word Position: 0
Analysis:
  - Position: Start (+40)
  - Possessive form (-30)
  - Third person context (0)
  - Single occurrence (+10)
Confidence: 20
Action: IGNORE 🚫
```

#### Example 8: Third Person Context
```
Transcription: "Sam said he would help me"
Wake Word Position: 0
Analysis:
  - Position: Start (+40)
  - Third person "he" (-15)
  - Single occurrence (+10)
Confidence: 35
Action: IGNORE 🚫
```

---

## 📈 Confidence Thresholds & Actions

### Threshold Modes

#### Strict Mode (Score ≥ 80)
- **False Positives**: Very Low (1-2%)
- **False Negatives**: Higher (10-15%)
- **Use Case**: Noisy environments, shared spaces, public demos
- **Trade-off**: More reliable but less flexible

#### Balanced Mode (Score ≥ 60) ⭐ RECOMMENDED
- **False Positives**: Low (3-5%)
- **False Negatives**: Low (5-8%)
- **Use Case**: General personal use
- **Trade-off**: Good balance of flexibility and reliability

#### Flexible Mode (Score ≥ 40)
- **False Positives**: Higher (8-12%)
- **False Negatives**: Very Low (2-3%)
- **Use Case**: Quiet environments, experimentation, solo use
- **Trade-off**: Maximum flexibility but more false activations

### Actions by Score Range

```python
Score 80-100: ACCEPT ✅
  → Process command immediately
  → High confidence activation
  → No confirmation needed

Score 60-79: ACCEPT WITH CAUTION ⚠️
  → Process command
  → Optional: Play subtle audio cue
  → Log for learning/analytics

Score 40-59: ASK FOR CONFIRMATION ❓
  → Play gentle chime or say "Yes?"
  → Wait for confirmation or command repeat
  → Timeout after 3 seconds if no response

Score 0-39: IGNORE 🚫
  → Likely false positive
  → Don't activate assistant
  → Continue wake word listening
  → Log as potential false positive
```

---

## 🔍 Multi-Sentence Handling

### Context Preservation Principle

**Key Insight**: Keep ALL transcribed text, regardless of wake word position.

The wake word is an **activation trigger**, not a **content delimiter**.

### Examples

All three variations should produce the same command:

#### Variation 1: Wake word at start
```
Input: "Sam, I think I felt some rain just now. What is the forecast saying?"
Confidence: 85
Extracted Command: "Sam, I think I felt some rain just now. What is the forecast saying?"
```

#### Variation 2: Wake word in middle
```
Input: "I think I felt some rain just now. Sam, what is the forecast saying?"
Confidence: 80
Extracted Command: "I think I felt some rain just now. Sam, what is the forecast saying?"
```

#### Variation 3: Wake word at end
```
Input: "I think I felt some rain just now. What is the forecast saying, Sam?"
Confidence: 75
Extracted Command: "I think I felt some rain just now. What is the forecast saying, Sam?"
```

### Why Keep Everything?

1. **Maximum Context**: LLM benefits from all available information
2. **Natural Speech**: Humans provide context before/after questions
3. **Better Responses**: "I felt rain" helps AI give rain-specific forecast
4. **Tone Preservation**: Keeps conversational nuance intact
5. **Simpler Logic**: No complex extraction rules needed

---

## 📊 Analytics & Tracking

### Metrics to Track

#### True Positive (TP) ✅
- **Definition**: System correctly activates when user intends it
- **Detection**: User engages with response or continues conversation
- **Example**: "Sam, weather?" → AI responds → User says "Thanks"

#### False Positive (FP) ❌
- **Definition**: System activates when user didn't intend it
- **Detection**: 
  - No follow-up within timeout period
  - User says "I wasn't talking to you"
  - User interrupts with "never mind" / "cancel"
- **Example**: "I was talking to Sam yesterday" → System activates → User ignores

#### True Negative (TN) ✅
- **Definition**: System correctly ignores non-activation speech
- **Detection**: Hard to measure directly (silence is ambiguous)
- **Tracking**: Log when score < threshold and no repeat attempt
- **Example**: "Sam's laptop" → Score: 20 → Ignored → No retry

#### False Negative (FN) ❌
- **Definition**: System fails to activate when user intends it
- **Detection**:
  - User immediately repeats with wake word at START
  - Pattern: Low score ignored → High score accepted within 10s
  - User explicitly says "Sam, I said..."
- **Example**: "Weather today, Sam?" → Ignored → "Sam, what's the weather?" → Activates

### Metrics Dashboard

```python
Session Statistics:
├─ Total Activations: 47
├─ True Positives: 43 (91.5% success rate)
├─ False Positives: 4 (8.5% error rate)
├─ False Negatives: 2 (detected via immediate repeats)
└─ True Negatives: 156 (estimated from ignored mentions)

Confidence Distribution:
├─ 80-100: 38 activations (92% engagement rate)
├─ 60-79: 7 activations (71% engagement rate)
└─ 40-59: 2 activations (50% engagement rate)

Recommendations:
└─ Current threshold (60) is optimal
   Predicted impact of lowering to 55:
   - +2% True Positives (1 more TP)
   - +1% False Positives (0.5 more FP)
```

### Learning & Adaptation (Future Feature)

Track patterns over time:
- User's typical phrasing style
- Common false positives (learn to ignore specific patterns)
- Common false negatives (adjust scoring for user's speech)
- Time-of-day patterns
- Environmental factors

---

## 🛠️ Implementation Architecture

### Core Components

#### 1. Wake Word Detection (Existing)
```python
# Already implemented in continuous listening
# Transcribes full audio including wake word
```

#### 2. Confidence Calculator (New)
```python
def calculate_confidence_score(transcription: str, 
                               wake_word: str, 
                               position: int) -> int:
    """
    Calculate 0-100 confidence score for activation.
    
    Args:
        transcription: Full transcribed text
        wake_word: Which wake word was detected
        position: Character position of wake word
        
    Returns:
        Confidence score (0-100)
    """
    # Implement scoring logic from this document
    pass
```

#### 3. Command Extractor (New - Simplified)
```python
def extract_command_with_confidence(transcription: str, 
                                   wake_words: list) -> tuple:
    """
    Detect wake word and calculate confidence.
    Keep full transcription intact.
    
    Returns:
        (full_transcription, confidence_score, wake_word_position)
        or (None, 0, None) if no wake word found
    """
    # Find wake word
    # Calculate confidence
    # Return everything
    pass
```

#### 4. Metrics Tracker (New)
```python
class WakeWordMetrics:
    """Track TP/FP/FN/TN over time."""
    
    def log_activation(self, transcription, confidence, outcome):
        """Log each activation attempt."""
        pass
    
    def log_user_engagement(self, activated, user_responded):
        """Detect TP vs FP based on user engagement."""
        pass
    
    def generate_report(self) -> dict:
        """Generate performance statistics."""
        pass
```

### Configuration Options

```python
class SpeechToText:
    def __init__(self,
                 # Existing params...
                 flexible_wake_word: bool = True,
                 confidence_threshold: int = 60,
                 confidence_mode: str = "balanced",  # strict/balanced/flexible
                 track_metrics: bool = True,
                 false_positive_timeout: float = 10.0):
        """
        Args:
            flexible_wake_word: Enable wake word anywhere in sentence
            confidence_threshold: Minimum score to activate (0-100)
            confidence_mode: Preset mode (overrides threshold)
                - "strict": threshold=80
                - "balanced": threshold=60
                - "flexible": threshold=40
            track_metrics: Enable analytics tracking
            false_positive_timeout: Seconds to wait for engagement
        """
```

---

## 🔄 Processing Flow

### Wake Word Detection Flow

```
1. Audio captured by continuous listening
   ↓
2. Whisper transcribes full audio
   ↓
3. Check if wake word present in transcription
   ↓ YES
4. Calculate confidence score
   ↓
5. Check score against threshold
   ├─ Score ≥ 80: ACCEPT immediately ✅
   ├─ Score 60-79: ACCEPT with caution ⚠️
   ├─ Score 40-59: ASK FOR CONFIRMATION ❓
   └─ Score < 40: IGNORE 🚫
   ↓
6. If accepted: Pass FULL transcription to callback
   ↓
7. LLM processes natural language (including wake word)
   ↓
8. Track engagement for metrics
```

### Engagement Tracking Flow

```
After activation:
   ↓
1. Start engagement timer (10 seconds)
   ↓
2. Monitor for user activity:
   ├─ User speaks follow-up → TRUE POSITIVE ✅
   ├─ User says "cancel"/"never mind" → FALSE POSITIVE ❌
   └─ Timeout expires with no response → FALSE POSITIVE ❌
   ↓
3. Log outcome to metrics
   ↓
4. Update confidence calibration (future feature)
```

---

## 🎯 Benefits Summary

### For User Experience
- ✅ Natural conversation flow
- ✅ No need to remember rigid wake phrase format
- ✅ Can speak spontaneously
- ✅ More accessible for non-native speakers
- ✅ Feels more like talking to a person

### For System Intelligence
- ✅ LLM receives full context
- ✅ Better understanding of user intent
- ✅ More nuanced responses possible
- ✅ Tone and emphasis preserved
- ✅ Future-proof for multi-modal interaction

### For Reliability
- ✅ Confidence scoring prevents false positives
- ✅ Analytics track system performance
- ✅ Configurable thresholds for different environments
- ✅ Learning potential for future improvements

---

## 🚀 Implementation Phases

### Phase 1: Core Functionality
- [ ] Implement `calculate_confidence_score()`
- [ ] Implement `extract_command_with_confidence()`
- [ ] Update `_process_speech_chunk()` to use confidence scoring
- [ ] Add configuration parameters
- [ ] Test with example scenarios

### Phase 2: Analytics
- [ ] Implement `WakeWordMetrics` class
- [ ] Add engagement tracking
- [ ] Create metrics logging
- [ ] Build dashboard/report generator

### Phase 3: Refinement
- [ ] Collect real-world usage data
- [ ] Tune confidence scoring weights
- [ ] Optimize thresholds based on metrics
- [ ] Add user-specific calibration (optional)

### Phase 4: Advanced Features (Future)
- [ ] Adaptive learning from user patterns
- [ ] Multiple assistant support
- [ ] Voice biometrics for user identification
- [ ] Context-aware threshold adjustment

---

## 📝 Notes & Considerations

### Why Not Remove Wake Word?

**Decision**: Keep the wake word in the transcription

**Reasoning**:
1. **Natural Speech**: "Sam, what's the weather?" is complete and natural
2. **LLM Intelligence**: Modern LLMs understand vocative case (addressing someone)
3. **Context Preservation**: Maintains conversational tone and structure
4. **Future Compatibility**: Supports multi-assistant scenarios
5. **Debugging**: Easier to audit and understand logs
6. **Memory**: AI can reference how it was addressed

**Weak Arguments for Removal**:
- ❌ "It's redundant" → Human speech IS redundant naturally
- ❌ "Saves tokens" → Negligible (1-2 tokens per interaction)
- ❌ "Cleaner input" → Actually less clean, loses structure

### Sentence Boundary Detection

The existing `_is_sentence_boundary()` function from `text_to_speech.py` can be leveraged for:
- Splitting multi-sentence transcriptions
- Understanding wake word context position
- Bonus scoring for sentence-aware placement

### False Positive vs False Negative Trade-off

**Current Recommendation**: Favor False Negatives over False Positives

**Reasoning**:
- False Positive = Annoying interruption, breaks user trust
- False Negative = User simply repeats with clear wake word at start

**However**: Make it configurable for different use cases
- Quiet home office → Flexible mode (favor low FN)
- Noisy environment → Strict mode (favor low FP)

---

## 🧪 Testing Strategy

### Unit Tests

```python
def test_high_confidence_start():
    result = extract_command_with_confidence(
        "Sam, what's the weather?",
        ["sam", "samantha"]
    )
    assert result[1] >= 70  # High confidence

def test_low_confidence_reference():
    result = extract_command_with_confidence(
        "I was talking to Sam yesterday",
        ["sam", "samantha"]
    )
    assert result[1] < 40  # Low confidence, should ignore

def test_multi_sentence_context():
    result = extract_command_with_confidence(
        "I felt rain earlier. What's the forecast, Sam?",
        ["sam", "samantha"]
    )
    assert result[1] >= 60  # Accept
    assert "I felt rain" in result[0]  # Context preserved
```

### Integration Tests

- Test in conversation mode vs wake word mode
- Test with actual Whisper transcriptions
- Test false positive timeout mechanism
- Test metrics tracking accuracy

### Real-World Testing

1. Record various activation attempts
2. Calculate confidence scores
3. Compare predictions with actual user intent
4. Tune scoring weights based on results

---

## 📚 References

### Related Documentation
- `STREAMING_TTS_GUIDE.md` - Sentence boundary detection logic
- `main_continuous.py` - Current wake word implementation
- `lib/speech_to_text.py` - Speech processing pipeline

### Key Design Decisions
1. **Keep full transcription** (don't remove wake word)
2. **Confidence scoring only** (not extraction strategies)
3. **Context preservation** (all sentences included)
4. **Configurable thresholds** (strict/balanced/flexible)
5. **Analytics-driven** (track and learn from patterns)

---

## 🎉 Summary

This flexible wake word system brings natural conversation to voice assistants while maintaining reliability through intelligent confidence scoring. By preserving full context and letting the LLM do what it does best (understanding natural language), we create a more intuitive and powerful user experience.

**Key Innovation**: Wake word as activation trigger, not content delimiter.

**Result**: Natural speech patterns + Smart filtering = Reliable, conversational AI assistant.

---

*Document Version: 1.0*  
*Date: October 2, 2025*  
*Status: Design Complete - Ready for Implementation*
