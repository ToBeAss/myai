# Future Optimizations - On Hold

This document contains optimization ideas that are valuable but not yet implemented. These are documented for future reference and implementation when needed.

---

## 📝 1. Advanced Chunk Boundaries (TTS Optimization)

### Current Status: On Hold
**Reason:** Requires careful handling of edge cases to avoid awkward pauses

### The Problem
Currently, we only chunk on periods (`.`), which means we wait for complete sentences before starting TTS synthesis. Adding more chunk boundaries could speed up first audio output.

### Proposed Solution: Multi-boundary Chunking with Smart Detection

**Add semicolons and commas as chunk boundaries, BUT with intelligent filtering:**

```python
# In lib/text_to_speech.py

def _is_valid_chunk_boundary(self, text: str, position: int, boundary_char: str) -> bool:
    """
    Check if a boundary character at the given position is a valid chunking point.
    
    :param text: The full text
    :param position: Position of the boundary character
    :param boundary_char: The boundary character (., ;, ,)
    :return: True if it's a valid chunk boundary, False otherwise
    """
    if position < 0 or position >= len(text):
        return False
    
    before = text[:position]
    after = text[position + 1:] if position + 1 < len(text) else ""
    
    # === PERIOD HANDLING (already implemented) ===
    if boundary_char == '.':
        # Use existing _is_sentence_boundary() method
        return self._is_sentence_boundary(text, position)
    
    # === SEMICOLON HANDLING ===
    elif boundary_char == ';':
        # Semicolons are almost always valid boundaries
        # Exception: rare cases in code or special formatting
        # Check if we're in a code block or URL
        if '://' in text[max(0, position-10):position+10]:  # URL check
            return False
        if position > 0 and text[position-1] in '&<>':  # HTML entity check
            return False
        return True
    
    # === COMMA HANDLING ===
    elif boundary_char == ',':
        # Commas are trickier - only valid in certain contexts
        
        # 1. Minimum text length - avoid chunking too early
        if len(before.strip()) < 30:
            return False
        
        # 2. Don't split lists - check for "and/or" nearby
        words_after = after.strip().split()[:3]
        if words_after and words_after[0].lower() in ['and', 'or']:
            return False
        
        # 3. Don't split in addresses (e.g., "123 Main St., Apt. 5")
        # Check if comma follows common abbreviations
        words_before = before.strip().split()[-3:]
        address_indicators = ['st', 'ave', 'rd', 'blvd', 'dr', 'apt', 'suite', 'ste']
        if any(word.lower().rstrip('.') in address_indicators for word in words_before):
            return False
        
        # 4. Subordinate clauses - good places to pause
        subordinating_after = ['which', 'who', 'where', 'when', 'while', 'although', 'because']
        if words_after and words_after[0].lower() in subordinating_after:
            return True
        
        # 5. After introductory phrases
        intro_patterns = [
            'however', 'therefore', 'moreover', 'furthermore', 
            'in fact', 'for example', 'in addition'
        ]
        last_few_words = ' '.join(words_before).lower()
        if any(pattern in last_few_words for pattern in intro_patterns):
            return True
        
        # 6. Independent clauses - check for subject-verb after comma
        # Simple heuristic: comma followed by pronoun or article often indicates independent clause
        independent_starters = ['i', 'you', 'he', 'she', 'it', 'we', 'they', 'the', 'a', 'an']
        if words_after and words_after[0].lower() in independent_starters:
            # Make sure we have enough text before chunking
            if len(before.strip()) >= 40:
                return True
        
        # Default: don't chunk on commas unless one of above conditions met
        return False
    
    return False

def _find_smart_boundary(self, buffer: str, chunk_on: str = ".,;") -> int:
    """
    Find the last valid chunk boundary in the buffer using smart detection.
    
    :param buffer: The text buffer to search
    :param chunk_on: String of characters to consider as boundaries
    :return: Position of last valid boundary, or -1 if none found
    """
    last_valid = -1
    
    # Search for boundaries in priority order: . > ; > ,
    boundary_priority = ['.', ';', ',']
    
    for boundary_char in boundary_priority:
        if boundary_char not in chunk_on:
            continue
        
        # Find all occurrences of this boundary character
        for i in range(len(buffer) - 1, -1, -1):
            if buffer[i] == boundary_char:
                if self._is_valid_chunk_boundary(buffer, i, boundary_char):
                    last_valid = i
                    break  # Found valid boundary for this char
        
        if last_valid >= 0:
            break  # Found valid boundary, no need to check lower priority
    
    return last_valid
```

**Usage in speak_streaming_async():**

```python
# Replace the current boundary finding logic:
# last_chunk_idx = self._find_sentence_boundary(buffer, chunk_on)

# With:
last_chunk_idx = self._find_smart_boundary(buffer, chunk_on=".,;")
```

### Expected Benefits
- **Semicolons**: ~50-100ms faster (safe, rare in abbreviations)
- **Commas**: ~100-200ms faster (with smart filtering)
- **Total**: ~150-300ms improvement

### Implementation Effort
- **Time**: 2-3 hours (testing all edge cases)
- **Risk**: Medium (requires thorough testing with various sentence structures)
- **Testing needed**: 
  - Lists: "apples, oranges, and bananas"
  - Addresses: "123 Main St., Apt. 5"
  - Subordinate clauses: "I went to the store, which was closed"
  - Independent clauses: "I like pizza, you like pasta"
  - Abbreviations: "Dr. Smith, Ph.D."

---

## 🧠 2. Smart Memory Context Optimization

### Current Status: On Hold
**Reason:** Need to balance speed with intelligence

### The Problem
Loading full conversation history increases prompt size and LLM latency. But simply truncating loses valuable context.

### Proposed Solution: Intelligent Context Pruning

**Strategy: Keep important messages, summarize or drop less critical ones**

```python
# In lib/agent.py, _structure_prompt() method

def _get_smart_context(self, max_messages: int = 10) -> list:
    """
    Intelligently select conversation history to maximize context while minimizing tokens.
    
    :param max_messages: Maximum number of message pairs to include
    :return: Pruned conversation history
    """
    if not self._memory:
        return []
    
    full_history = self._memory.retrieve_memory()
    
    # Always keep system messages (instructions)
    system_messages = [msg for msg in full_history if msg.get('role') == 'system']
    user_ai_messages = [msg for msg in full_history if msg.get('role') in ['human', 'ai']]
    
    # If we're under the limit, return everything
    if len(user_ai_messages) <= max_messages:
        return full_history
    
    # Scoring system for message importance
    def score_message_pair(user_msg, ai_msg, position):
        """Score a user-AI message pair for importance."""
        score = 0
        
        # 1. Recency - most recent are most important
        # Last 3 messages get high score
        if position >= len(user_ai_messages) - 6:  # Last 3 pairs
            score += 50
        elif position >= len(user_ai_messages) - 10:  # Last 5 pairs
            score += 30
        
        # 2. Questions about personal info (establishing context)
        context_keywords = ['my name', 'i am', 'i work', 'i live', 'remember']
        user_text = user_msg.get('message', '').lower()
        if any(keyword in user_text for keyword in context_keywords):
            score += 40
        
        # 3. Tool usage (important actions)
        ai_text = ai_msg.get('message', '')
        if 'tool' in str(ai_msg) or 'function' in str(ai_msg):
            score += 35
        
        # 4. Length (longer exchanges often more substantive)
        combined_length = len(user_text) + len(ai_text)
        if combined_length > 200:
            score += 20
        
        # 5. Follow-up indicators (part of ongoing topic)
        followup_words = ['also', 'and', 'additionally', 'furthermore']
        if any(word in user_text for word in followup_words):
            score += 15
        
        return score
    
    # Score all message pairs
    message_pairs = []
    for i in range(0, len(user_ai_messages) - 1, 2):
        if i + 1 < len(user_ai_messages):
            score = score_message_pair(
                user_ai_messages[i], 
                user_ai_messages[i + 1],
                i
            )
            message_pairs.append({
                'score': score,
                'messages': [user_ai_messages[i], user_ai_messages[i + 1]],
                'position': i
            })
    
    # Sort by score (descending)
    message_pairs.sort(key=lambda x: x['score'], reverse=True)
    
    # Take top N pairs
    selected_pairs = message_pairs[:max_messages // 2]
    
    # Re-sort by original position to maintain chronological order
    selected_pairs.sort(key=lambda x: x['position'])
    
    # Flatten back to message list
    selected_messages = []
    for pair in selected_pairs:
        selected_messages.extend(pair['messages'])
    
    # Combine system + selected messages
    return system_messages + selected_messages


# Usage in _structure_prompt():
def _structure_prompt(self, user_input: str, retrieved_data: Optional[List] = [], 
                     tool_results: Optional[List] = []) -> str:
    """Structure a prompt with smart context selection."""
    
    # Format instructions
    formatted_instructions = Memory.format_messages(self._instructions)
    
    # Smart conversation history (instead of retrieve_memory())
    formatted_conversation_history = ""
    if self._memory:
        smart_context = self._get_smart_context(max_messages=10)
        formatted_conversation_history = Memory.format_messages(smart_context)
    
    # ... rest of method unchanged
```

### Alternative Approach: Sliding Window with Anchors

```python
def _get_windowed_context(self, window_size: int = 5, anchor_keywords: list = None) -> list:
    """
    Get recent messages plus any older messages containing important keywords.
    
    :param window_size: Number of recent messages to always include
    :param anchor_keywords: Keywords that make older messages important
    :return: Windowed conversation history
    """
    if anchor_keywords is None:
        anchor_keywords = ['remember', 'my name', 'i told you', 'earlier']
    
    if not self._memory:
        return []
    
    full_history = self._memory.retrieve_memory()
    
    # Split into system and conversation
    system_messages = [msg for msg in full_history if msg.get('role') == 'system']
    conversation = [msg for msg in full_history if msg.get('role') in ['human', 'ai']]
    
    # Always include recent messages (sliding window)
    recent_messages = conversation[-window_size:] if len(conversation) > window_size else conversation
    
    # Find anchor messages (older messages with important context)
    anchor_messages = []
    older_messages = conversation[:-window_size] if len(conversation) > window_size else []
    
    for msg in older_messages:
        msg_text = msg.get('message', '').lower()
        if any(keyword in msg_text for keyword in anchor_keywords):
            anchor_messages.append(msg)
    
    # Combine: system + anchors + recent
    return system_messages + anchor_messages + recent_messages
```

### Expected Benefits
- **Smart pruning**: ~50-100ms (fewer tokens to process)
- **Maintains intelligence**: Keeps important context
- **Scales well**: Works even with long conversations

### Implementation Effort
- **Time**: 1-2 hours
- **Risk**: Low (easy to test and tune)
- **Can be A/B tested**: Compare responses with full vs pruned context

---

## 📊 Comparison Matrix

| Optimization | Speed Gain | Complexity | Accuracy Impact | Recommended Priority |
|-------------|-----------|------------|-----------------|---------------------|
| Smart Chunk Boundaries | 150-300ms | Medium | None (if done carefully) | Medium - when seeking more speed |
| Smart Memory Context | 50-100ms | Low | Minimal (with smart selection) | Low - optional refinement |
| Comma boundaries only | 100-200ms | Low | Low risk | High - if you want quick win |
| Semicolon boundaries only | 50-100ms | Very Low | Very low risk | High - safest boundary addition |

---

## 🎯 Recommended Implementation Order (When Ready)

1. **Add semicolons first** (30 minutes, very safe)
   - Change `chunk_on` from `"."` to `".;"`
   - Test with various responses
   - If successful, proceed to #2

2. **Add smart memory context** (1-2 hours, optional)
   - Implement if you have very long conversations
   - Monitor whether responses get "dumber"
   - Easy to tune threshold

3. **Add comma boundaries** (2-3 hours, requires testing)
   - Only if you want maximum speed
   - Requires careful edge case handling
   - Thoroughly test with various sentence structures

---

## 📝 Notes

- These optimizations are **additive** - you can implement any combination
- All can be **feature-flagged** for easy A/B testing
- **Measure before and after** using `test_parallel_processing.py`
- **User feedback** is key - do responses feel more natural or choppy?

---

## 🧪 Testing Checklist (When Implementing)

### For Chunk Boundaries:
- [ ] Lists: "apples, oranges, and bananas"
- [ ] Addresses: "123 Main St., Apt. 5" 
- [ ] Abbreviations: "Dr. Smith, M.D."
- [ ] Subordinate clauses: "The house, which is red, is nice"
- [ ] Independent clauses: "I like pizza, you like pasta"
- [ ] Semicolons in lists: "Paris, France; London, England"
- [ ] URLs: "Visit https://example.com; it's great"

### For Memory Context:
- [ ] Long conversation (20+ exchanges)
- [ ] Personal context establishment: "My name is X"
- [ ] Follow-up questions referencing earlier context
- [ ] Tool usage preservation
- [ ] Compare response quality with full vs pruned context

---

**Document Status:** Documented for future reference  
**Last Updated:** October 2, 2025  
**Review Date:** When seeking additional speed optimizations
