import whisper
import pyaudio
import wave
import tempfile
import threading
import time
import keyboard
import os
import numpy as np
from typing import Optional, Callable
import struct
import ssl
import urllib.request
import json
from datetime import datetime
import warnings

# Suppress the FP16 warning - it's expected behavior on CPU
warnings.filterwarnings("ignore", message="FP16 is not supported on CPU; using FP32 instead")

class WakeWordMetrics:
    """Track wake word activation metrics for analytics and optimization."""
    
    def __init__(self, metrics_file: str = "wake_word_metrics.json"):
        """
        Initialize metrics tracking.
        
        :param metrics_file: Path to file for storing metrics
        """
        self.metrics_file = metrics_file
        self.session_start = time.time()
        
        # Session metrics
        self.true_positives = 0
        self.false_positives = 0
        self.false_negatives = 0
        self.true_negatives = 0
        
        # Detailed activation log
        self.activation_log = []
        
        # Confidence distribution
        self.confidence_distribution = {
            "80-100": {"count": 0, "engaged": 0},
            "60-79": {"count": 0, "engaged": 0},
            "40-59": {"count": 0, "engaged": 0},
            "0-39": {"count": 0, "engaged": 0}
        }
        
        # Load historical metrics if available
        self._load_metrics()
    
    def _load_metrics(self):
        """Load historical metrics from file."""
        if os.path.exists(self.metrics_file):
            try:
                with open(self.metrics_file, 'r') as f:
                    data = json.load(f)
                    # Could load historical data here for long-term tracking
            except Exception as e:
                print(f"⚠️ Could not load metrics: {e}")
    
    def _save_metrics(self):
        """Save metrics to file."""
        try:
            data = {
                "session_start": datetime.fromtimestamp(self.session_start).isoformat(),
                "true_positives": self.true_positives,
                "false_positives": self.false_positives,
                "false_negatives": self.false_negatives,
                "true_negatives": self.true_negatives,
                "confidence_distribution": self.confidence_distribution,
                "recent_activations": self.activation_log[-50:]  # Keep last 50
            }
            with open(self.metrics_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"⚠️ Could not save metrics: {e}")
    
    def log_activation(self, transcription: str, confidence: int, wake_word_position: int):
        """
        Log an activation attempt.
        
        :param transcription: Full transcription
        :param confidence: Confidence score
        :param wake_word_position: Position of wake word
        """
        entry = {
            "timestamp": time.time(),
            "transcription": transcription[:100],  # Truncate for privacy
            "confidence": confidence,
            "position": wake_word_position,
            "outcome": "pending"  # Will be updated by log_outcome
        }
        self.activation_log.append(entry)
        
        # Update confidence distribution
        if confidence >= 80:
            self.confidence_distribution["80-100"]["count"] += 1
        elif confidence >= 60:
            self.confidence_distribution["60-79"]["count"] += 1
        elif confidence >= 40:
            self.confidence_distribution["40-59"]["count"] += 1
        else:
            self.confidence_distribution["0-39"]["count"] += 1
    
    def log_outcome(self, engaged: bool):
        """
        Log the outcome of the most recent activation.
        
        :param engaged: True if user engaged (TP), False if ignored (FP)
        """
        if not self.activation_log:
            return
        
        last_entry = self.activation_log[-1]
        confidence = last_entry["confidence"]
        
        if engaged:
            last_entry["outcome"] = "true_positive"
            self.true_positives += 1
            
            # Update engagement rate for confidence range
            if confidence >= 80:
                self.confidence_distribution["80-100"]["engaged"] += 1
            elif confidence >= 60:
                self.confidence_distribution["60-79"]["engaged"] += 1
            elif confidence >= 40:
                self.confidence_distribution["40-59"]["engaged"] += 1
        else:
            last_entry["outcome"] = "false_positive"
            self.false_positives += 1
        
        self._save_metrics()
    
    def log_false_negative(self, transcription: str):
        """
        Log a false negative (missed activation that user had to repeat).
        
        :param transcription: The transcription that was missed
        """
        self.false_negatives += 1
        entry = {
            "timestamp": time.time(),
            "transcription": transcription[:100],
            "confidence": 0,
            "position": -1,
            "outcome": "false_negative"
        }
        self.activation_log.append(entry)
        self._save_metrics()
    
    def log_true_negative(self):
        """Log a true negative (correctly ignored non-activation)."""
        self.true_negatives += 1
    
    def generate_report(self) -> dict:
        """
        Generate performance statistics report.
        
        :return: Dictionary with metrics and recommendations
        """
        total_activations = self.true_positives + self.false_positives
        
        report = {
            "session_duration": time.time() - self.session_start,
            "total_activations": total_activations,
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "true_negatives": self.true_negatives,
            "success_rate": (self.true_positives / total_activations * 100) if total_activations > 0 else 0,
            "confidence_distribution": {}
        }
        
        # Calculate engagement rates per confidence range
        for range_key, data in self.confidence_distribution.items():
            count = data["count"]
            engaged = data["engaged"]
            engagement_rate = (engaged / count * 100) if count > 0 else 0
            report["confidence_distribution"][range_key] = {
                "activations": count,
                "engagement_rate": engagement_rate
            }
        
        return report
    
    def print_report(self):
        """Print a formatted metrics report."""
        report = self.generate_report()
        
        print("\n" + "="*60)
        print("📊 WAKE WORD PERFORMANCE METRICS")
        print("="*60)
        print(f"⏱️  Session Duration: {report['session_duration']:.1f} seconds")
        print(f"🎯 Total Activations: {report['total_activations']}")
        print(f"✅ True Positives: {report['true_positives']} ({report['success_rate']:.1f}%)")
        print(f"❌ False Positives: {report['false_positives']}")
        print(f"😞 False Negatives: {report['false_negatives']}")
        print(f"✓  True Negatives: {report['true_negatives']}")
        print("\n📈 Confidence Distribution:")
        for range_key in ["80-100", "60-79", "40-59", "0-39"]:
            data = report["confidence_distribution"][range_key]
            print(f"   {range_key}: {data['activations']} activations "
                  f"({data['engagement_rate']:.0f}% engagement)")
        print("="*60 + "\n")

class SpeechToText:
    """Speech-to-text handler using OpenAI Whisper for offline processing."""
    
    def __init__(self, 
                 model_size: str = "tiny",
                 flexible_wake_word: bool = True,
                 confidence_threshold: int = None,
                 confidence_mode: str = "balanced",
                 track_metrics: bool = True,
                 false_positive_timeout: float = 10.0):
        """
        Initialize the speech-to-text system.
        
        :param model_size: Whisper model size ('tiny', 'base', 'small', 'medium', 'large')
                          'tiny' is fastest and smallest (39MB), 'base' is more accurate (142MB)
        :param flexible_wake_word: Enable flexible wake word positioning (anywhere in sentence)
        :param confidence_threshold: Minimum confidence score (0-100) to activate, None uses mode default
        :param confidence_mode: Preset mode - "strict" (80), "balanced" (60), "flexible" (40)
        :param track_metrics: Enable analytics tracking for TP/FP/FN
        :param false_positive_timeout: Seconds to wait for user engagement to detect FP
        """
        print(f"🎤 Loading Whisper '{model_size}' model... This might take a moment on first run.")
        try:
            # Create SSL context to handle certificate issues on macOS
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # Set up urllib to use the SSL context
            opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ssl_context))
            urllib.request.install_opener(opener)
            
            self.model = whisper.load_model(model_size)
            self.is_recording = False
            self.audio_format = pyaudio.paInt16
            self.channels = 1
            self.rate = 16000
            self.chunk = 1024
            
            # Language settings - English only for optimal accuracy
            self.preferred_language = "en"  # Force English for consistency
            self.task = "transcribe"
            
            # Wake word detection
            self.wake_words = ["hey myai", "hey assistant", "hey ai"]  # Default wake words
            self.is_listening = False
            self.wake_callback = None
            self.in_conversation = False
            self.conversation_timeout = 5.0  # seconds to wait for follow-up
            self.conversation_timer_thread = None
            self.conversation_last_activity = 0  # Track last activity time
            self.speech_being_processed = False  # Track if we're currently processing speech
            self.delayed_timer_start = True  # Start timer only after initial silence period
            self.initial_silence_duration = 3.0  # Seconds of silence before starting the countdown
            
            # Flexible wake word configuration
            self.flexible_wake_word = flexible_wake_word
            self.false_positive_timeout = false_positive_timeout
            
            # Set confidence threshold based on mode
            if confidence_threshold is not None:
                self.confidence_threshold = confidence_threshold
            else:
                # Use mode defaults
                mode_thresholds = {
                    "strict": 75,
                    "balanced": 55,  # Lowered from 60 to accept natural end-of-sentence patterns
                    "flexible": 40
                }
                self.confidence_threshold = mode_thresholds.get(confidence_mode, 55)
            
            self.confidence_mode = confidence_mode
            
            # Initialize metrics tracking
            self.track_metrics = track_metrics
            self.metrics = WakeWordMetrics() if track_metrics else None
            self.last_activation_time = 0
            self.waiting_for_engagement = False
            
            print("✅ Speech-to-text system ready!")
            print("�🇧 Language: English only (for optimal accuracy)")
            
            if flexible_wake_word:
                print(f"🎯 Flexible wake word: ENABLED (wake word can be anywhere in sentence)")
                print(f"📊 Confidence mode: {confidence_mode.upper()} (threshold: {self.confidence_threshold})")
                if track_metrics:
                    print(f"📈 Analytics tracking: ENABLED")
        except Exception as e:
            print(f"❌ Error loading Whisper model: {e}")
            raise
    
    def is_hallucination(self, text: str) -> bool:
        """
        Detect if transcribed text is likely a Whisper hallucination.
        
        Whisper sometimes hallucinates repetitive patterns when processing background noise.
        Common patterns include repeated numbers, percentages, or short phrases.
        
        :param text: Transcribed text to check
        :return: True if text appears to be a hallucination
        """
        if not text or len(text.strip()) < 3:
            return True
            
        text = text.strip().lower()
        
        # Check for very short repetitive patterns
        words = text.split()
        
        # If more than 50% of words are identical, likely hallucination
        if len(words) > 2:
            word_counts = {}
            for word in words:
                word_counts[word] = word_counts.get(word, 0) + 1
            max_count = max(word_counts.values())
            if max_count / len(words) > 0.5:
                print(f"🚫 Detected hallucination: Repetitive pattern ('{words[0]}' repeated {max_count} times)")
                return True
        
        # Check for repeated short sequences (like "1.5% 1.5% 1.5%")
        # Split into chunks of 2-3 words and check for repetition
        if len(words) >= 4:
            chunk_size = 2
            chunks = [' '.join(words[i:i+chunk_size]) for i in range(0, len(words)-chunk_size+1, chunk_size)]
            if len(set(chunks)) == 1 and len(chunks) >= 2:
                print(f"🚫 Detected hallucination: Repeated sequence ('{chunks[0]}')")
                return True
        
        # Check for suspiciously short transcriptions with very low diversity
        if len(text) < 15 and len(set(text.replace(' ', ''))) < 5:
            print(f"🚫 Detected hallucination: Low character diversity in short text")
            return True
            
        return False
    
    def calculate_confidence_score(self, transcription: str, wake_word: str, position: int) -> int:
        """
        Calculate confidence score (0-100) for wake word activation.
        
        Analyzes multiple factors to determine if this is a genuine activation
        or a casual mention of the wake word in conversation.
        
        :param transcription: Full transcribed text
        :param wake_word: The wake word that was detected
        :param position: Character position of wake word in transcription
        :return: Confidence score (0-100)
        """
        score = 0
        text_lower = transcription.lower()
        length = len(transcription)
        
        # 1. WAKE WORD POSITION ANALYSIS (40 points max)
        # Determines how naturally the wake word is positioned for a command
        if position < 10:  # Very start of transcription
            score += 40
        else:
            relative_pos = position / length if length > 0 else 0
            if relative_pos < 0.2:  # First 20%
                score += 35
            elif relative_pos > 0.8:  # Last 20%
                score += 35  # Increased from 30 - end position is natural for questions
            else:  # Middle 60%
                score += 20
        
        # 2. CONTENT ANALYSIS (30 points max)
        # Check for question words and command verbs
        question_words = ['what', 'where', 'when', 'who', 'why', 'how', 
                         'is', 'are', 'can', 'could', 'would', 'should', 'will']
        command_words = ['tell', 'show', 'find', 'search', 'get', 'play', 
                        'stop', 'set', 'turn', 'open', 'close', 'remind', 
                        'create', 'make', 'help', 'give', 'send']
        
        has_question = any(word in text_lower.split() for word in question_words)
        has_command = any(word in text_lower.split() for word in command_words)
        
        if has_question:
            score += 20  # Increased from 15
        if has_command:
            score += 10
        
        # Check for question mark (strong indicator)
        if '?' in transcription:
            score += 10  # Increased from 5
        
        # 3. GRAMMAR & CONTEXT ANALYSIS (20 points max)
        # Conversational indicators (talking TO assistant)
        conversational_pronouns = ['i ', ' i ', 'my ', 'me ', 'you ', 'your']
        if any(pron in text_lower for pron in conversational_pronouns):
            score += 10
        
        # INTENT TO ENGAGE: Phrases showing user wants to interact with assistant
        # These override third-person penalties because they show clear intent
        intent_phrases = ['need to ask', 'should ask', 'let me ask', 'want to ask',
                         'going to ask', 'have to ask', 'let\'s ask', 'i\'ll ask']
        has_intent = any(phrase in text_lower for phrase in intent_phrases)
        
        # CORRECTIONS & APOLOGIES: User is engaging to correct/clarify
        correction_phrases = ['no wait', 'sorry ' + wake_word, 'actually ' + wake_word,
                             'i meant', 'i mean', 'correction', 'my mistake']
        has_correction = any(phrase in text_lower for phrase in correction_phrases)
        
        if has_correction:
            score += 20  # Boost for corrections - clear engagement
        
        if has_intent:
            # Strong positive signal - user is expressing intent to engage
            score += 25
        else:
            # Only apply third-person penalty if there's NO intent phrase
            # Third person references (talking ABOUT someone)
            # Use word boundaries to avoid false positives like "the" matching "he"
            third_person = [' he ', ' she ', ' they ', ' them ', ' his ', ' her ', ' their ']
            if any(third in text_lower for third in third_person):
                score -= 15
        
        # REPORTING SPEECH: Phrases that report what Sam said/did (not addressing Sam)
        # Note: "Sam needs to know" is addressing Sam (telling to remember), so we exclude it
        reporting_verbs = [f'{wake_word} said', f'{wake_word} told', 
                          f'{wake_word} asked', f'{wake_word} mentioned',
                          f'{wake_word} thinks', f'{wake_word} wants',
                          f'{wake_word} doesn',  # "doesn't"
                          f'{wake_word} never ', f'{wake_word} walked',
                          f'{wake_word} looked', f'{wake_word} smiled']
        
        # Only penalize if it's not "needs to know" (which is engagement)
        has_reporting = any(report in text_lower for report in reporting_verbs)
        has_needs_to_know = f'{wake_word} needs to know' in text_lower
        
        if has_reporting and not has_needs_to_know:
            score -= 25
        
        # But DO penalize generic "Sam needs" statements (not "needs to know")
        if f'{wake_word} needs ' in text_lower and not has_needs_to_know:
            # Check if it's a statement about Sam's needs vs command to Sam
            # "Sam needs a computer" vs "Sam needs to remember this"
            needs_patterns = [f'{wake_word} needs a ', f'{wake_word} needs help',
                            f'{wake_word} needs more', f'{wake_word} needs some']
            if any(pattern in text_lower for pattern in needs_patterns):
                score -= 25
        
        # DESCRIPTIVE STATEMENTS: Describing Sam's characteristics (not addressing Sam)
        # We need to distinguish:
        #   "Sam works at office" → REJECT (statement about Sam)
        #   "Sam could you help?" → ACCEPT (question to Sam, even without comma)
        # 
        # Strategy: Only penalize if there's NO comma AND NO modal/question verb
        # Modal verbs (could/would/should/can) indicate addressing Sam
        has_comma_after_wake = f'{wake_word},' in text_lower or f'{wake_word} ,' in text_lower
        
        # Check for modal/question verbs that indicate addressing (even without comma)
        modal_verbs = ['could', 'would', 'should', 'can', 'will', 'may', 'might']
        has_modal = any(modal in text_lower.split() for modal in modal_verbs)
        
        # Only penalize descriptive patterns if:
        # 1. No comma after wake word (not clearly addressing)
        # 2. No modal verb (not a polite question/request)
        if not has_comma_after_wake and not has_modal:
            descriptive_patterns = [f'{wake_word} is ', f'{wake_word} was ',
                                   f'{wake_word} seems ', f'{wake_word} looks ',
                                   f'{wake_word} works ', f'{wake_word} lives ',
                                   f'{wake_word} does ', f'{wake_word} has ']
            if any(desc in text_lower for desc in descriptive_patterns):
                score -= 25
        
        # PAST ENCOUNTERS: Casual mentions of meeting/seeing Sam
        encounter_patterns = ['i met ' + wake_word, 'i saw ' + wake_word,
                             'i think ' + wake_word, 'i know ' + wake_word]
        if any(enc in text_lower for enc in encounter_patterns):
            score -= 20
        
        # NARRATIVE INDICATORS: Words that suggest storytelling/narration
        narrative_starters = ['then ' + wake_word, 'suddenly ' + wake_word, 
                             'meanwhile ' + wake_word, 'afterwards ' + wake_word]
        if any(narr in text_lower for narr in narrative_starters):
            score -= 25
        
        # COLLABORATIVE PAST TENSE: "Sam and I" with past tense verbs
        if f'{wake_word} and i ' in text_lower:
            # Check for past tense indicators
            past_verbs = ['went', 'did', 'had', 'were', 'saw', 'made', 'got', 'came']
            if any(past in text_lower for past in past_verbs):
                score -= 20
        
        # INDIRECT MESSAGES: "Tell Sam that..." (relaying message, not engaging)
        if f'tell {wake_word} that' in text_lower or f'ask {wake_word} to' in text_lower:
            score -= 25
        
        # Prepositions with wake word (e.g., "to Sam", "with Sam")
        # But NOT if it's an intent phrase like "need to ask Sam"
        if not has_intent:
            prepositions = [f' to {wake_word}', f' with {wake_word}', 
                           f' about {wake_word}', f' from {wake_word}']
            if any(prep in text_lower for prep in prepositions):
                score -= 15
        
        # Proper sentence structure
        if transcription and (transcription[0].isupper() or position < 5):
            score += 5
        
        # 4. WAKE WORD USAGE (10 points max)
        # Count wake words with word boundaries to avoid "same" matching "sam"
        import re
        wake_word_pattern = r'\b' + re.escape(wake_word) + r'\b'
        wake_word_matches = re.findall(wake_word_pattern, text_lower)
        wake_word_count = len(wake_word_matches)
        
        if wake_word_count == 1:
            score += 10
        elif wake_word_count == 2:
            # Two wake words might be emphasis ("Sam, Sam, are you there?")
            # Don't penalize as heavily if there's a question mark or comma between
            if '?' in transcription or transcription.count(',') >= 2:
                score += 5  # Still positive for emphatic addressing
            else:
                score -= 15  # Moderate penalty for ambiguous double mention
        elif wake_word_count > 2:
            score -= 25  # Strong penalty for multiple occurrences
        
        # Check if wake word is followed by a last name (e.g., "Sam Smith")
        # This indicates talking about a person, not addressing the assistant
        common_last_names = ['smith', 'jones', 'brown', 'johnson', 'williams', 'davis', 'miller', 'wilson', 'moore', 'taylor']
        words = text_lower.split()
        for i, word in enumerate(words):
            if wake_word in word and i + 1 < len(words):
                next_word = words[i + 1]
                # Check if next word is a last name or capitalized word (likely a last name)
                if next_word in common_last_names or (i + 1 < len(transcription.split()) and transcription.split()[i + 1][0].isupper()):
                    score -= 30  # Strong penalty for "Sam Smith" pattern
                    break
        
        # Check for possessive form (Sam's, Samantha's) and plural (Sams) - check ALL wake words
        has_possessive = False
        for ww in self.wake_words:
            # Possessive patterns: "sam's", "samantha's"
            possessive_patterns = [f"{ww}'s", f"{ww}'"]
            # Plural pattern: "sams" (not the wake word, but plural of the name)
            plural_pattern = f"{ww}s "
            
            if any(poss in text_lower for poss in possessive_patterns):
                has_possessive = True
                break
            # Check for plural (e.g., "Sams are nice people")
            if plural_pattern in text_lower and f"{ww} " not in text_lower:
                has_possessive = True  # Treat plural as possessive-like (not addressing)
                break
        
        if has_possessive:
            score -= 30
        
        # 5. MULTI-SENTENCE BONUS (10 points max)
        sentence_endings = text_lower.count('.') + text_lower.count('!') + text_lower.count('?')
        if sentence_endings >= 1:
            score += 10
        
        # 6. SPECIAL CASE: Just wake word alone (user calling the assistant)
        # This is a common and valid use case - user says "Sam" to get attention
        words_without_wake_word = [w for w in text_lower.split() if w not in self.wake_words]
        if len(words_without_wake_word) <= 1:  # Only wake word (or wake word + one filler word like "hey")
            score += 20  # Boost to ensure it passes threshold
        
        # 7. BONUS: Wake word at end with question mark (natural question format)
        if transcription.strip().endswith(wake_word + '?') or transcription.strip().endswith(wake_word):
            if '?' in transcription or has_question:
                score += 5  # Small boost for natural questioning format
        
        # Clamp score to 0-100 range
        return max(0, min(100, score))
    
    def extract_command_with_confidence(self, transcription: str, wake_words: list) -> tuple:
        """
        Extract command and calculate confidence score.
        
        Keeps entire transcription intact (including wake word) for maximum context.
        Only calculates confidence to determine if activation is genuine.
        
        :param transcription: Full transcribed text
        :param wake_words: List of wake words to search for
        :return: (full_transcription, confidence_score, wake_word_position) or (None, 0, None)
        """
        transcription_lower = transcription.lower()
        
        # Find first occurrence of any wake word (with word boundaries)
        import re
        wake_word_found = None
        wake_word_position = -1
        
        for wake_word in wake_words:
            # Use regex with word boundaries to avoid matching "sam" in "same"
            pattern = r'\b' + re.escape(wake_word) + r'\b'
            match = re.search(pattern, transcription_lower)
            if match:
                wake_word_found = wake_word
                wake_word_position = match.start()
                break
        
        if not wake_word_found:
            return None, 0, None
        
        # Calculate confidence score
        confidence = self.calculate_confidence_score(
            transcription, 
            wake_word_found, 
            wake_word_position
        )
        
        # Return ENTIRE transcription (preserve all context)
        return transcription, confidence, wake_word_position
    
    def record_audio(self, duration: Optional[int] = None) -> str:
        """
        Record audio from microphone and return the file path.
        
        :param duration: Max recording duration in seconds (None for manual stop)
        :return: Path to the recorded audio file
        """
        try:
            audio = pyaudio.PyAudio()
        except Exception as e:
            print(f"❌ Could not initialize audio system: {e}")
            print("💡 Make sure you have a microphone connected and permissions are granted.")
            return ""
        
        # Create temporary file for audio in current working directory instead of temp
        import uuid
        current_dir = os.getcwd()
        temp_filename = os.path.join(current_dir, f"myai_audio_{uuid.uuid4().hex}.wav")
        print(f"📁 Creating audio file: {temp_filename}")
        
        try:
            # Open audio stream
            stream = audio.open(
                format=self.audio_format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                frames_per_buffer=self.chunk
            )
        except Exception as e:
            print(f"❌ Could not open audio stream: {e}")
            audio.terminate()
            return ""
        
        print("🎤 Recording... Press SPACE to stop recording")
        print("💡 Speak clearly and loudly enough for good recognition")
        frames = []
        self.is_recording = True
        
        start_time = time.time()
        min_recording_time = 1.0  # Increased minimum recording time
        last_volume_update = 0
        
        try:
            while self.is_recording:
                data = stream.read(self.chunk, exception_on_overflow=False)
                frames.append(data)
                
                # Show volume indicator every 0.5 seconds
                current_time = time.time()
                if current_time - last_volume_update > 0.5:
                    # Calculate volume level for feedback
                    audio_chunk = np.frombuffer(data, dtype=np.int16)
                    volume = np.sqrt(np.mean(audio_chunk.astype(np.float32)**2))
                    volume_bars = int(volume / 1000)  # Scale for display
                    volume_indicator = "█" * min(volume_bars, 10)
                    print(f"\r🔊 Volume: [{volume_indicator:<10}] {volume:.0f}", end="", flush=True)
                    last_volume_update = current_time
                
                # Check for spacebar press to stop (but only after minimum time)
                if keyboard.is_pressed('space') and (time.time() - start_time) >= min_recording_time:
                    print(f"\n⏹️ Recording stopped by user ({time.time() - start_time:.1f}s)")
                    break
                
                # Check duration limit
                if duration and (time.time() - start_time) >= duration:
                    print(f"\n⏹️ Recording stopped - {duration}s limit reached")
                    break
                    
        except Exception as e:
            print(f"❌ Recording error: {e}")
        finally:
            stream.stop_stream()
            stream.close()
            audio.terminate()
            self.is_recording = False
        
        if not frames:
            print("❌ No audio recorded")
            return ""
        
        # Save recorded audio
        try:
            # Write audio data to file
            with wave.open(temp_filename, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(audio.get_sample_size(self.audio_format))
                wf.setframerate(self.rate)
                wf.writeframes(b''.join(frames))
            
            # Ensure file is completely written by adding a small delay
            time.sleep(0.1)
            
            # Verify file was created and has content
            if os.path.exists(temp_filename) and os.path.getsize(temp_filename) > 0:
                file_size = os.path.getsize(temp_filename)
                print(f"✅ Audio recorded successfully: {len(frames)} frames, {file_size} bytes")
            else:
                print("❌ Audio file was not created properly")
                return ""
                
        except Exception as e:
            print(f"❌ Error saving audio: {e}")
            # Clean up failed file
            try:
                if os.path.exists(temp_filename):
                    os.unlink(temp_filename)
            except:
                pass
            return ""
        
        return temp_filename
    
    def load_audio_data(self, audio_file_path: str) -> np.ndarray:
        """
        Load audio data directly from WAV file without FFmpeg.
        
        :param audio_file_path: Path to the WAV file
        :return: Audio data as numpy array
        """
        try:
            with wave.open(audio_file_path, 'rb') as wav_file:
                # Get audio parameters
                sample_rate = wav_file.getframerate()
                n_channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()
                n_frames = wav_file.getnframes()
                
                print(f"📊 Audio info: {sample_rate}Hz, {n_channels}ch, {sample_width}bytes, {n_frames}frames")
                
                # Read raw audio data
                raw_audio = wav_file.readframes(n_frames)
                
                # Convert to numpy array
                if sample_width == 1:
                    dtype = np.uint8
                elif sample_width == 2:
                    dtype = np.int16
                elif sample_width == 4:
                    dtype = np.int32
                else:
                    raise ValueError(f"Unsupported sample width: {sample_width}")
                
                audio_data = np.frombuffer(raw_audio, dtype=dtype)
                
                # Convert to mono if stereo
                if n_channels == 2:
                    audio_data = audio_data.reshape(-1, 2).mean(axis=1)
                
                # Convert to float32 and normalize to [-1, 1]
                if dtype == np.uint8:
                    audio_data = (audio_data.astype(np.float32) - 128) / 128
                elif dtype == np.int16:
                    audio_data = audio_data.astype(np.float32) / 32768
                elif dtype == np.int32:
                    audio_data = audio_data.astype(np.float32) / 2147483648
                
                # Resample to 16kHz if needed (Whisper expects 16kHz)
                if sample_rate != 16000:
                    # Simple resampling - for production you'd want proper resampling
                    target_length = int(len(audio_data) * 16000 / sample_rate)
                    audio_data = np.interp(
                        np.linspace(0, len(audio_data), target_length),
                        np.arange(len(audio_data)),
                        audio_data
                    )
                
                print(f"✅ Audio loaded: {len(audio_data)} samples at 16kHz")
                return audio_data
                
        except Exception as e:
            print(f"❌ Error loading audio data: {e}")
            raise

    def transcribe_audio(self, audio_file_path: str) -> str:
        """
        Transcribe audio file to text using Whisper.
        
        :param audio_file_path: Path to the audio file
        :return: Transcribed text
        """
        transcribed_text = ""
        try:
            print("🔄 Transcribing audio...")
            
            # Convert to absolute path and normalize
            audio_file_path = os.path.abspath(audio_file_path)
            print(f"📁 Absolute path: {audio_file_path}")
            
            # Check if file exists before transcribing
            if not os.path.exists(audio_file_path):
                print(f"❌ Audio file not found: {audio_file_path}")
                # List files in temp directory for debugging
                temp_dir = os.path.dirname(audio_file_path)
                try:
                    files = os.listdir(temp_dir)
                    myai_files = [f for f in files if 'myai_audio' in f]
                    print(f"🔍 MyAI audio files in temp dir: {myai_files}")
                except Exception as e:
                    print(f"🔍 Could not list temp directory: {e}")
                return ""
            
            # Check file size
            file_size = os.path.getsize(audio_file_path)
            if file_size == 0:
                print("❌ Audio file is empty")
                return ""
            
            print(f"📁 Transcribing audio file: {audio_file_path} ({file_size} bytes)")
            
            # Add a small delay to ensure file is fully written
            time.sleep(0.2)
            
            # Check if file still exists just before transcription
            if not os.path.exists(audio_file_path):
                print(f"❌ Audio file disappeared before transcription!")
                return ""
            
            # Try to open the file to verify it's accessible
            try:
                with open(audio_file_path, 'rb') as test_file:
                    first_bytes = test_file.read(10)
                    print(f"✅ File is accessible, first 10 bytes: {first_bytes}")
            except Exception as access_error:
                print(f"❌ File access test failed: {access_error}")
                return ""
            
            # Transcribe with Whisper using direct audio loading
            print("🔄 Starting Whisper transcription (English)...")
            
            # Load audio data directly (bypassing Whisper's FFmpeg dependency)
            audio_data = self.load_audio_data(audio_file_path)
            
            # Transcribe using English only
            result = self.model.transcribe(
                audio_data,
                language="en"  # Force English for optimal accuracy
            )
            
            transcribed_text = result["text"].strip()
            
            # Debug: Check if we got any result
            if not transcribed_text:
                print("⚠️ Empty transcription result - checking audio quality...")
                print(f"📊 Audio length: {len(audio_data)/16000:.2f} seconds")
                print(f"📊 Audio volume (max): {np.max(np.abs(audio_data)):.4f}")
                print(f"📊 Audio volume (RMS): {np.sqrt(np.mean(audio_data**2)):.4f}")
                
                # If audio is very quiet, try to amplify it
                if np.max(np.abs(audio_data)) < 0.01:
                    print("🔊 Audio seems very quiet, trying to amplify...")
                    amplified_audio = audio_data * 10  # Amplify by 10x
                    amplified_audio = np.clip(amplified_audio, -1.0, 1.0)  # Prevent clipping
                    
                    result = self.model.transcribe(
                        amplified_audio,
                        language="en"
                    )
                    transcribed_text = result["text"].strip()
                    
                    if transcribed_text:
                        print("✅ Amplification helped!")
                    else:
                        print("❌ Still no speech detected after amplification")
            
            print(f"✅ Transcription completed: '{transcribed_text}'")
            
            # Check for hallucinations (Whisper's tendency to generate repetitive text from noise)
            if self.is_hallucination(transcribed_text):
                print("⚠️ Transcription appears to be a hallucination, discarding...")
                transcribed_text = ""
            
        except Exception as e:
            print(f"❌ Transcription error: {e}")
            print(f"❌ Error type: {type(e).__name__}")
            # Try to get more detailed error info
            import traceback
            print(f"❌ Full traceback: {traceback.format_exc()}")
            
        finally:
            # Clean up temporary file in finally block with retry logic
            cleanup_attempts = 3
            for attempt in range(cleanup_attempts):
                try:
                    if os.path.exists(audio_file_path):
                        time.sleep(0.1)  # Small delay before cleanup
                        os.unlink(audio_file_path)
                        print(f"🗑️ Cleaned up temporary file (attempt {attempt + 1})")
                        break
                except Exception as cleanup_error:
                    if attempt == cleanup_attempts - 1:  # Last attempt
                        print(f"⚠️ Could not clean up temporary file: {cleanup_error}")
                    else:
                        time.sleep(0.2)  # Wait before retry
        
        return transcribed_text
    
    def listen_and_transcribe(self, max_duration: int = 30) -> str:
        """
        Record audio and transcribe it to text in one step.
        
        :param max_duration: Maximum recording duration in seconds
        :return: Transcribed text
        """
        audio_file = self.record_audio(duration=max_duration)
        
        if not audio_file:
            return ""
        
        transcribed_text = self.transcribe_audio(audio_file)
        
        if transcribed_text:
            print(f"📝 You said: '{transcribed_text}'")
        else:
            print("🔇 No speech detected or transcription failed")
        
        return transcribed_text

    def set_conversation_timeout(self, timeout: float):
        """
        Set how long to wait for follow-up questions after a response.
        
        :param timeout: Timeout in seconds (e.g., 5.0 for 5 seconds)
        """
        self.conversation_timeout = timeout
        print(f"⏱️ Conversation timeout set to {timeout} seconds")

    def enter_conversation_mode(self):
        """Enter conversation mode - listen for follow-ups without wake word."""
        self.in_conversation = True
        self.conversation_last_activity = time.time()
        print(f"💬 Conversation mode active - you can ask follow-up questions for {self.conversation_timeout} seconds")

    def exit_conversation_mode(self):
        """Exit conversation mode - return to wake word detection."""
        self.in_conversation = False
        self.speech_being_processed = False
        
        # Stop the timer thread
        if hasattr(self, 'stop_timer_flag'):
            self.stop_timer_flag = True
            
        if self.conversation_timer_thread and self.conversation_timer_thread.is_alive():
            # Timer thread will naturally end when stop_timer_flag becomes True
            pass
        print("👂 Conversation ended, listening for wake words...")

    def update_conversation_activity(self):
        """Mark that speech activity was detected (timer will handle this automatically)."""
        if self.in_conversation:
            print("🎙️ Speech activity detected - timer will restart after processing")
    
    def check_engagement_timeout(self):
        """Check if user engagement timeout has expired (for false positive detection)."""
        if not self.track_metrics or not self.waiting_for_engagement:
            return
        
        time_since_activation = time.time() - self.last_activation_time
        if time_since_activation > self.false_positive_timeout:
            # No engagement detected - likely false positive
            self.metrics.log_outcome(engaged=False)
            self.waiting_for_engagement = False

    def set_wake_words(self, wake_words: list):
        """
        Set custom wake words for voice activation.
        
        :param wake_words: List of wake phrases like ["hey myai", "hey assistant"]
        """
        self.wake_words = [word.lower() for word in wake_words]
        print(f"🎯 Wake words set: {', '.join(self.wake_words)}")

    def start_continuous_listening(self, wake_callback: Callable[[str], None]):
        """
        Start continuous listening for wake words in the background.
        
        :param wake_callback: Function to call when wake word is detected, receives transcribed text
        """
        # Clean up any leftover files first
        self.cleanup_audio_files()
        
        self.wake_callback = wake_callback
        self.is_listening = True
        
        # Start listening thread
        listening_thread = threading.Thread(target=self._continuous_listen_loop, daemon=True)
        listening_thread.start()

    def stop_continuous_listening(self):
        """Stop continuous listening."""
        self.is_listening = False
        # Clean up any leftover files
        self.cleanup_audio_files()
        print("🔇 Continuous listening stopped")
        
        # Print metrics report if tracking is enabled
        if self.track_metrics and self.metrics:
            self.metrics.print_report()

    def _continuous_listen_loop(self):
        """Main loop for continuous listening."""
        try:
            audio = pyaudio.PyAudio()
            
            # Create audio stream for continuous listening
            stream = audio.open(
                format=self.audio_format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                frames_per_buffer=self.chunk
            )
            
            # Buffer to store recent audio
            audio_buffer = []
            buffer_duration = 5.0  # Increased from 3 to 5 seconds
            buffer_size = int(self.rate * buffer_duration / self.chunk)
            
            silence_threshold = 300  # Lowered threshold for better sensitivity
            speech_detected = False
            speech_frames = []
            silence_count = 0
            speech_start_time = 0  # Track when speech recording started
            last_speech_time = 0  # Track when we last processed speech
            max_speech_duration = 60.0  # Maximum recording duration in seconds (failsafe for noisy environments)
            
            while self.is_listening:
                try:
                    # Read audio chunk
                    data = stream.read(self.chunk, exception_on_overflow=False)
                    audio_chunk = np.frombuffer(data, dtype=np.int16)
                    
                    # Calculate volume
                    volume = np.sqrt(np.mean(audio_chunk.astype(np.float32)**2))
                    
                    # Add to circular buffer
                    audio_buffer.append(data)
                    if len(audio_buffer) > buffer_size:
                        audio_buffer.pop(0)
                    
                    # Detect speech activity
                    current_time = time.time()
                    if volume > silence_threshold:
                        if not speech_detected:
                            # Only start new speech detection if enough time has passed since last speech
                            if current_time - last_speech_time > 2.0:  # 2 second gap required
                                speech_detected = True
                                speech_start_time = current_time  # Track when recording started
                                speech_frames = audio_buffer.copy()  # Include pre-speech audio
                                print("🎤 Speech detected, recording...")
                                
                                # CRITICAL: Mark speech processing as active immediately for conversation timer
                                self.speech_being_processed = True
                                
                                # If we're in conversation mode, notify once at the start
                                if self.in_conversation:
                                    self.update_conversation_activity()
                        
                        if speech_detected:
                            speech_frames.append(data)
                            silence_count = 0
                            
                            # Check if recording has gone on too long
                            if current_time - speech_start_time > max_speech_duration:
                                print("⏱️ Maximum recording duration reached, processing speech...")
                                self._process_speech_chunk(speech_frames)
                                speech_detected = False
                                speech_frames = []
                                silence_count = 0
                                last_speech_time = current_time
                    else:
                        if speech_detected:
                            silence_count += 1
                            speech_frames.append(data)
                            
                            # If we've had enough silence, process the speech
                            if silence_count > 60:  # Increased to 60 (about 1.5 seconds of silence for more complete speech)
                                print("🔄 Processing speech...")
                                self._process_speech_chunk(speech_frames)
                                speech_detected = False
                                speech_frames = []
                                silence_count = 0
                                last_speech_time = current_time  # Update last speech time
                    
                    # Check for engagement timeout (false positive detection)
                    if self.track_metrics:
                        self.check_engagement_timeout()
                    
                    time.sleep(0.01)  # Small delay to prevent CPU overload
                    
                except Exception as e:
                    print(f"❌ Error in continuous listening: {e}")
                    continue
                    
        except Exception as e:
            print(f"❌ Failed to start continuous listening: {e}")
        finally:
            try:
                stream.stop_stream()
                stream.close()
                audio.terminate()
            except:
                pass

    def _process_speech_chunk(self, speech_frames):
        """Process a chunk of speech to check for wake words."""
        temp_filename = None
        try:
            # Note: speech_being_processed is already set to True when speech was first detected
            # Note: update_conversation_activity() was already called when speech was first detected
            
            # Create temporary audio file
            import uuid
            current_dir = os.getcwd()
            temp_filename = os.path.join(current_dir, f"wake_audio_{uuid.uuid4().hex}.wav")
            
            # Save audio frames to file
            with wave.open(temp_filename, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(pyaudio.PyAudio().get_sample_size(self.audio_format))
                wf.setframerate(self.rate)
                wf.writeframes(b''.join(speech_frames))
            
            # Transcribe the audio (English only)
            audio_data = self.load_audio_data(temp_filename)
            result = self.model.transcribe(audio_data, language="en")
            transcribed_text = result["text"].strip().lower()
            
            # Check for hallucinations early to avoid processing noise
            if self.is_hallucination(transcribed_text):
                print("⚠️ Transcription appears to be a hallucination from background noise, ignoring...")
                # If we're in conversation mode, exit it since this is just noise
                if self.in_conversation:
                    self.exit_conversation_mode()
                return
            
            # If we're in conversation mode, treat any speech as a command
            if self.in_conversation:
                print(f"💬 Follow-up detected: '{transcribed_text}'")
                if transcribed_text and self.wake_callback:
                    # Mark engagement for previous activation
                    if self.track_metrics and self.waiting_for_engagement:
                        self.metrics.log_outcome(engaged=True)
                        self.waiting_for_engagement = False
                    self.wake_callback(transcribed_text)
                return
            
            # Use flexible wake word detection if enabled
            if self.flexible_wake_word:
                # Extract command with confidence scoring
                command, confidence, position = self.extract_command_with_confidence(
                    transcribed_text, 
                    self.wake_words
                )
                
                if command is None:
                    # No wake word found
                    if len(transcribed_text) > 3:
                        print(f"🔇 Speech without wake word ignored: '{transcribed_text[:30]}{'...' if len(transcribed_text) > 30 else ''}'")
                        if self.track_metrics:
                            self.metrics.log_true_negative()
                    return
                
                # Wake word found - check confidence
                print(f"🎯 Wake word detected at position {position}")
                print(f"📝 Full transcription: '{transcribed_text}'")
                print(f"📊 Confidence score: {confidence}/100")
                
                # Log activation
                if self.track_metrics:
                    self.metrics.log_activation(transcribed_text, confidence, position)
                    self.last_activation_time = time.time()
                    self.waiting_for_engagement = True
                
                # Determine action based on confidence
                if confidence >= self.confidence_threshold:
                    # Accept activation
                    if confidence >= 80:
                        print(f"✅ HIGH confidence - Processing command")
                    elif confidence >= 60:
                        print(f"⚠️  MEDIUM confidence - Processing command")
                    else:
                        print(f"❓ LOW confidence - Processing with caution")
                    
                    if self.wake_callback:
                        # Mark this activation as True Positive since we're processing it
                        if self.track_metrics and self.waiting_for_engagement:
                            self.metrics.log_outcome(engaged=True)
                            self.waiting_for_engagement = False
                        self.wake_callback(command)
                else:
                    # Reject activation
                    print(f"🚫 Confidence too low ({confidence} < {self.confidence_threshold}) - Ignoring")
                    if self.track_metrics:
                        self.metrics.log_true_negative()
                        self.waiting_for_engagement = False
            
            else:
                # Original wake word detection (for backward compatibility)
                wake_word_found = False
                for wake_word in self.wake_words:
                    if wake_word in transcribed_text:
                        print(f"🎯 Wake word detected: '{wake_word}'")
                        print(f"📝 Full transcription: '{transcribed_text}'")
                        wake_word_found = True
                        
                        # Extract the part after the wake word
                        wake_index = transcribed_text.find(wake_word)
                        command_text = transcribed_text[wake_index + len(wake_word):].strip()
                        
                        if command_text:
                            if self.wake_callback:
                                self.wake_callback(command_text)
                        else:
                            # Just wake word, no command
                            if self.wake_callback:
                                self.wake_callback("")
                        break
                
                # If no wake word found but we have meaningful speech, ignore it
                if not wake_word_found and len(transcribed_text) > 3:
                    print(f"🔇 Speech without wake word ignored: '{transcribed_text[:30]}{'...' if len(transcribed_text) > 30 else ''}'")
                    pass
                
        except Exception as e:
            print(f"❌ Error processing speech chunk: {e}")
        
        finally:
            # Clean up - always try to remove the file BEFORE marking processing complete
            if temp_filename:
                for attempt in range(3):  # Try up to 3 times
                    try:
                        if os.path.exists(temp_filename):
                            time.sleep(0.1)  # Small delay
                            os.unlink(temp_filename)
                            break
                    except Exception as cleanup_error:
                        if attempt == 2:  # Last attempt
                            print(f"⚠️ Could not clean up wake audio file after 3 attempts: {cleanup_error}")
                        else:
                            time.sleep(0.2)  # Wait before retry
            
            # Mark that speech processing is complete (do this LAST)
            self.speech_being_processed = False

    def start_conversation_timer(self):
        """Start a simple conversation timer that pauses when speech is detected."""
        # If a timer is already running, don't start a new one
        if hasattr(self, 'conversation_timer_thread') and self.conversation_timer_thread and self.conversation_timer_thread.is_alive():
            # Timer already running, just ensure we're in conversation mode
            if not self.in_conversation:
                self.in_conversation = True
            return
        
        # Stop any existing timer first
        if hasattr(self, 'stop_timer_flag'):
            self.stop_timer_flag = True
        
        # Create a new stop flag for this timer
        self.stop_timer_flag = False
        
        def simple_conversation_timer():
            print(f"🕐 Conversation timer started - {self.conversation_timeout}s for follow-up questions")
            timeout_start_time = time.time()
            timer_was_paused = False  # Track if we've already paused this cycle
            
            while self.in_conversation and not self.stop_timer_flag:
                current_time = time.time()
                
                # If speech is being processed, completely pause the timer
                if self.speech_being_processed:
                    # Only print pause message once per pause cycle
                    if not timer_was_paused:
                        print("⏸️ Timer paused - speech being processed")
                        timer_was_paused = True
                    
                    # Wait for speech processing to complete
                    while self.speech_being_processed and self.in_conversation and not self.stop_timer_flag:
                        time.sleep(0.1)
                    
                    # After speech processing, restart the timer from the beginning
                    if self.in_conversation and not self.stop_timer_flag:
                        print(f"▶️ Timer restarted - {self.conversation_timeout}s for follow-up questions")
                        timeout_start_time = time.time()
                        timer_was_paused = False  # Reset for next pause cycle
                        # Small delay to ensure we don't immediately catch the flag changing again
                        time.sleep(0.3)
                    continue
                
                # Check if timeout has been reached
                time_elapsed = current_time - timeout_start_time
                if time_elapsed >= self.conversation_timeout:
                    if self.in_conversation and not self.stop_timer_flag:
                        self.exit_conversation_mode()
                    break
                
                time.sleep(0.1)
            
            # Clean up
            if hasattr(self, 'conversation_timer_thread'):
                self.conversation_timer_thread = None
        
        self.conversation_timer_thread = threading.Thread(target=simple_conversation_timer, daemon=True)
        self.conversation_timer_thread.start()

    def cleanup_audio_files(self):
        """Clean up any leftover audio files."""
        try:
            import glob
            current_dir = os.getcwd()
            
            # Clean up wake audio files
            wake_files = glob.glob(os.path.join(current_dir, "wake_audio_*.wav"))
            for file in wake_files:
                try:
                    os.unlink(file)
                    print(f"🗑️ Cleaned up leftover file: {os.path.basename(file)}")
                except:
                    pass
            
            # Clean up myai audio files
            myai_files = glob.glob(os.path.join(current_dir, "myai_audio_*.wav"))
            for file in myai_files:
                try:
                    os.unlink(file)
                    print(f"🗑️ Cleaned up leftover file: {os.path.basename(file)}")
                except:
                    pass
                    
        except Exception as e:
            print(f"⚠️ Error during cleanup: {e}")

    def stop_recording(self):
        """Stop the current recording."""
        self.is_recording = False
