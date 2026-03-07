"""Wake-word confidence scoring and command extraction logic."""

from __future__ import annotations

import re
from typing import Sequence


class WakeWordScorer:
    """Encapsulate wake-word confidence scoring heuristics."""

    def __init__(self, wake_words: Sequence[str]):
        self.wake_words = [word.lower() for word in wake_words]

    def set_wake_words(self, wake_words: Sequence[str]) -> None:
        self.wake_words = [word.lower() for word in wake_words]

    def calculate_confidence_score(self, transcription: str, wake_word: str, position: int) -> int:
        """Calculate confidence score (0-100) for wake-word activation."""
        score = 0
        text_lower = transcription.lower()
        length = len(transcription)

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

        question_words = [
            "what", "where", "when", "who", "why", "how", "is", "are", "can", "could", "would", "should", "will",
        ]
        command_words = [
            "tell", "show", "find", "search", "get", "play", "stop", "set", "turn", "open", "close", "remind", "create", "make", "help", "give", "send",
        ]

        has_question = any(word in text_lower.split() for word in question_words)
        has_command = any(word in text_lower.split() for word in command_words)

        if has_question:
            score += 20
        if has_command:
            score += 10
        if "?" in transcription:
            score += 10

        conversational_pronouns = ["i ", " i ", "my ", "me ", "you ", "your"]
        if any(pron in text_lower for pron in conversational_pronouns):
            score += 10

        intent_phrases = [
            "need to ask", "should ask", "let me ask", "want to ask", "going to ask", "have to ask", "let's ask", "i'll ask",
        ]
        has_intent = any(phrase in text_lower for phrase in intent_phrases)

        correction_phrases = [
            "no wait", "sorry " + wake_word, "actually " + wake_word, "i meant", "i mean", "correction", "my mistake",
        ]
        has_correction = any(phrase in text_lower for phrase in correction_phrases)

        if has_correction:
            score += 20

        if has_intent:
            score += 25
        else:
            third_person = [" he ", " she ", " they ", " them ", " his ", " her ", " their "]
            if any(third in text_lower for third in third_person):
                score -= 15

        reporting_verbs = [
            f"{wake_word} said", f"{wake_word} told", f"{wake_word} asked", f"{wake_word} mentioned", f"{wake_word} thinks", f"{wake_word} wants", f"{wake_word} doesn", f"{wake_word} never ", f"{wake_word} walked", f"{wake_word} looked", f"{wake_word} smiled",
        ]
        has_reporting = any(report in text_lower for report in reporting_verbs)
        has_needs_to_know = f"{wake_word} needs to know" in text_lower

        if has_reporting and not has_needs_to_know:
            score -= 25

        if f"{wake_word} needs " in text_lower and not has_needs_to_know:
            needs_patterns = [
                f"{wake_word} needs a ", f"{wake_word} needs help", f"{wake_word} needs more", f"{wake_word} needs some",
            ]
            if any(pattern in text_lower for pattern in needs_patterns):
                score -= 25

        has_comma_after_wake = f"{wake_word}," in text_lower or f"{wake_word} ," in text_lower
        modal_verbs = ["could", "would", "should", "can", "will", "may", "might"]
        has_modal = any(modal in text_lower.split() for modal in modal_verbs)

        if not has_comma_after_wake and not has_modal:
            descriptive_patterns = [
                f"{wake_word} is ", f"{wake_word} was ", f"{wake_word} seems ", f"{wake_word} looks ", f"{wake_word} works ", f"{wake_word} lives ", f"{wake_word} does ", f"{wake_word} has ",
            ]
            if any(desc in text_lower for desc in descriptive_patterns):
                score -= 25

        encounter_patterns = ["i met " + wake_word, "i saw " + wake_word, "i think " + wake_word, "i know " + wake_word]
        if any(enc in text_lower for enc in encounter_patterns):
            score -= 20

        narrative_starters = ["then " + wake_word, "suddenly " + wake_word, "meanwhile " + wake_word, "afterwards " + wake_word]
        if any(narr in text_lower for narr in narrative_starters):
            score -= 25

        if f"{wake_word} and i " in text_lower:
            past_verbs = ["went", "did", "had", "were", "saw", "made", "got", "came"]
            if any(past in text_lower for past in past_verbs):
                score -= 20

        if f"tell {wake_word} that" in text_lower or f"ask {wake_word} to" in text_lower:
            score -= 25

        if not has_intent:
            prepositions = [f" to {wake_word}", f" with {wake_word}", f" about {wake_word}", f" from {wake_word}"]
            if any(prep in text_lower for prep in prepositions):
                score -= 15

        if transcription and (transcription[0].isupper() or position < 5):
            score += 5

        wake_word_pattern = r"\b" + re.escape(wake_word) + r"\b"
        wake_word_matches = re.findall(wake_word_pattern, text_lower)
        wake_word_count = len(wake_word_matches)

        if wake_word_count == 1:
            score += 10
        elif wake_word_count == 2:
            if "?" in transcription or transcription.count(",") >= 2:
                score += 5
            else:
                score -= 15
        elif wake_word_count > 2:
            score -= 25

        common_last_names = ["smith", "jones", "brown", "johnson", "williams", "davis", "miller", "wilson", "moore", "taylor"]
        words = text_lower.split()
        original_words = transcription.split()
        for i, word in enumerate(words):
            if wake_word in word and i + 1 < len(words):
                next_word = words[i + 1]
                if next_word in common_last_names or (i + 1 < len(original_words) and original_words[i + 1][0].isupper()):
                    score -= 30
                    break

        has_possessive = False
        for ww in self.wake_words:
            possessive_patterns = [f"{ww}'s", f"{ww}'"]
            plural_pattern = f"{ww}s "

            if any(poss in text_lower for poss in possessive_patterns):
                has_possessive = True
                break
            if plural_pattern in text_lower and f"{ww} " not in text_lower:
                has_possessive = True
                break

        if has_possessive:
            score -= 30

        sentence_endings = text_lower.count(".") + text_lower.count("!") + text_lower.count("?")
        if sentence_endings >= 1:
            score += 10

        words_without_wake_word = [w for w in words if w not in self.wake_words]
        filler_words = ["hey", "hi", "hello", "a", "uh", "um", "okay", "ok"]
        meaningful_words = [w for w in words_without_wake_word if w not in filler_words]
        if len(meaningful_words) <= 1:
            score += 30

        if transcription.strip().endswith(wake_word + "?") or transcription.strip().endswith(wake_word):
            if "?" in transcription or has_question:
                score += 5

        return max(0, min(100, score))

    def extract_command_with_confidence(self, transcription: str, wake_words: Sequence[str]) -> tuple:
        """Extract command and confidence score from transcribed text."""
        transcription_lower = transcription.lower()

        wake_word_found = None
        wake_word_position = -1

        for wake_word in wake_words:
            pattern = r"\b" + re.escape(wake_word) + r"\b"
            match = re.search(pattern, transcription_lower)
            if match:
                wake_word_found = wake_word
                wake_word_position = match.start()
                break

        if not wake_word_found:
            return None, 0, None

        confidence = self.calculate_confidence_score(transcription, wake_word_found, wake_word_position)
        return transcription, confidence, wake_word_position
