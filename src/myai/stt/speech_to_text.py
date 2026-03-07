import whisper
import pyaudio
import wave
import threading
import time
import keyboard
import os
import numpy as np
from typing import Optional, Callable, Union
from pathlib import Path
import struct
import ssl
import urllib.request
import warnings
import webrtcvad
from concurrent.futures import ThreadPoolExecutor, Future
from myai.paths import unique_tmp_audio_file, TMP_AUDIO_DIR, REPO_ROOT

from . import conversation_state
from .audio_io import STTAudioIO
from .chunked_processing import ChunkedSpeechProcessor
from .speech_chunk_processing import SpeechChunkProcessor
from .wakeword_metrics import WakeWordMetrics
from .wakeword_scoring import WakeWordScorer

# Try to import faster-whisper for optimized performance
try:
    from faster_whisper import WhisperModel
    FASTER_WHISPER_AVAILABLE = True
except ImportError:
    FASTER_WHISPER_AVAILABLE = False
    print("ℹ️  faster-whisper not available. Install with: pip install faster-whisper")

# Suppress the FP16 warning - it's expected behavior on CPU
warnings.filterwarnings("ignore", message="FP16 is not supported on CPU; using FP32 instead")

class SpeechToText:
    """Speech-to-text handler using OpenAI Whisper for offline processing."""
    
    def __init__(self, 
                 model_size: str = "tiny",
                 flexible_wake_word: bool = True,
                 confidence_threshold: int = None,
                 confidence_mode: str = "balanced",
                 track_metrics: bool = True,
                 false_positive_timeout: float = 10.0,
                 enable_vad: bool = True,
                 vad_aggressiveness: int = 1,
                 use_faster_whisper: bool = True,
                 vocabulary_hints: str = "Tobias, Sam, hey Sam, weather, temperature, time, reminder, search"):
        """
        Initialize the speech-to-text system.
        
        :param model_size: Whisper model size ('tiny', 'base', 'small', 'medium', 'large')
                          'tiny' is fastest and smallest (39MB), 'base' is more accurate (142MB)
        :param flexible_wake_word: Enable flexible wake word positioning (anywhere in sentence)
        :param confidence_threshold: Minimum confidence score (0-100) to activate, None uses mode default
        :param confidence_mode: Preset mode - "strict" (80), "balanced" (60), "flexible" (40)
        :param track_metrics: Enable analytics tracking for TP/FP/FN
        :param false_positive_timeout: Seconds to wait for user engagement to detect FP
        :param enable_vad: Enable WebRTC Voice Activity Detection for noise filtering
        :param vad_aggressiveness: VAD filtering level (0=liberal, 1=moderate, 2=balanced, 3=aggressive)
        :param use_faster_whisper: Use optimized faster-whisper backend if available (4-5x faster)
        :param vocabulary_hints: Comma-separated common words/phrases to improve recognition (initial_prompt)
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
            
            # Load Whisper model with optional faster-whisper optimization
            if use_faster_whisper and FASTER_WHISPER_AVAILABLE:
                print("🚀 Using faster-whisper for optimized transcription (4-5x faster)")
                self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
                self.using_faster_whisper = True
            else:
                if use_faster_whisper and not FASTER_WHISPER_AVAILABLE:
                    print("⚠️  faster-whisper not available, falling back to standard whisper")
                    print("    Install with: pip install faster-whisper")
                self.model = whisper.load_model(model_size)
                self.using_faster_whisper = False
            self.is_recording = False
            self.audio_format = pyaudio.paInt16
            self.channels = 1
            self.rate = 16000
            self.chunk = 320  # 20ms frames (320 samples at 16kHz) - matches WebRTC VAD expectations
            
            # Language settings - English only for optimal accuracy
            self.preferred_language = "en"  # Force English for consistency
            self.task = "transcribe"
            
            # Wake word detection
            self.wake_words = ["hey myai", "hey assistant", "hey ai"]  # Default wake words
            self.wakeword_scorer = WakeWordScorer(self.wake_words)
            self.audio_io = STTAudioIO(self)
            self.chunked_processor = ChunkedSpeechProcessor(self)
            self.speech_chunk_processor = SpeechChunkProcessor(self)
            self.is_listening = False
            self.wake_callback = None
            self.in_conversation = False
            self.conversation_timeout = 5.0  # seconds to wait for follow-up
            self.conversation_timer_thread: Optional[threading.Thread] = None
            self.conversation_last_activity = 0.0  # Track last activity time
            self.stop_timer_flag = False
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
            self.metrics: Optional[WakeWordMetrics] = WakeWordMetrics() if track_metrics else None
            self.last_activation_time = 0.0
            self.waiting_for_engagement = False
            
            # Initialize WebRTC Voice Activity Detection
            self.enable_vad = enable_vad
            self.vad = None
            self.vad_frame_duration = 20  # ms (10, 20, or 30 supported by WebRTC VAD) - matches chunk size
            self.vad_frame_size = int(self.rate * self.vad_frame_duration / 1000)  # 320 samples at 16kHz
            
            if enable_vad:
                try:
                    self.vad = webrtcvad.Vad(vad_aggressiveness)
                    print(f"🎯 Voice Activity Detection: ENABLED (aggressiveness: {vad_aggressiveness}/3)")
                except Exception as e:
                    print(f"⚠️ Could not initialize VAD: {e}. Continuing without VAD...")
                    self.enable_vad = False
            
            # Chunked transcription for parallel processing
            self.enable_chunked_transcription = False  # Can be enabled after init
            self.transcription_chunks = []  # Store chunk futures
            self.chunk_lock = threading.Lock()  # Thread-safe chunk access
            
            # Vocabulary hints for improved recognition
            self.vocabulary_hints = vocabulary_hints
            
            print("✅ Speech-to-text system ready!")
            print("🇬🇧 Language: English only (for optimal accuracy)")
            
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
        
        # Note: We don't filter short transcriptions here because:
        # 1. Whisper has already run (no processing savings)
        # 2. Short speech like "Sam", "hey", "hello" is legitimate
        # 3. Wake word detection handles validation
        
        return False
    
    def enable_chunked_transcription_mode(self, max_workers: int = 2):
        """
        Enable chunked transcription with parallel processing.
        This allows transcribing audio chunks in parallel as speech continues.
        
        :param max_workers: Maximum number of parallel transcription threads
        """
        self.enable_chunked_transcription = True
        self.transcription_executor = ThreadPoolExecutor(max_workers=max_workers)
        print(f"⚡ Chunked transcription: ENABLED (up to {max_workers} parallel transcriptions)")
        print("   Benefits: Faster response time for multi-phrase commands")
    
    def _clean_chunked_transcript(self, transcripts: list) -> str:
        """
        Clean and merge chunked transcripts intelligently.
        
        Whisper adds punctuation thinking each chunk is complete, which can create
        awkward combinations like "What's the weather? in London."
        
        Also detects and removes duplicate words at chunk boundaries
        (e.g., "model too." + "to perform" → "model too to perform" should become "model to perform")
        
        :param transcripts: List of individual chunk transcripts
        :return: Cleaned combined transcript
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
            
            # Check for word overlap with previous chunk
            if cleaned_chunks and i > 0:
                # Get last 1-3 words from previous chunk (without punctuation)
                prev_chunk = cleaned_chunks[-1]
                prev_words = prev_chunk.rstrip('.!?,;:').split()
                
                # Get first 1-3 words from current chunk
                curr_words = chunk.split()
                
                # Check for overlap (comparing up to 3 words)
                max_overlap = min(3, len(prev_words), len(curr_words))
                overlap_found = 0
                
                for overlap_size in range(max_overlap, 0, -1):
                    prev_tail = ' '.join(prev_words[-overlap_size:]).lower()
                    curr_head = ' '.join(curr_words[:overlap_size]).lower()
                    
                    # Also handle phonetic duplicates like "too"/"to", "their"/"there"
                    phonetic_matches = {
                        'too': 'to',
                        'to': 'too',
                        'two': 'to',
                        'their': 'there',
                        'there': 'their',
                        'your': "you're",
                        "you're": 'your',
                    }
                    
                    # Direct match or phonetic match
                    if prev_tail == curr_head or prev_tail in phonetic_matches and phonetic_matches[prev_tail] == curr_head:
                        overlap_found = overlap_size
                        break
                
                # If overlap found, remove from current chunk
                if overlap_found > 0:
                    chunk = ' '.join(curr_words[overlap_found:])
                    if not chunk:  # If entire chunk was overlap, skip it
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
                    has_subject = any(word in first_words for word in ['i', 'you', 'he', 'she', 'it', 'we', 'they', 'also', 'and', 'but'])
                    
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
        
        # Clean up double punctuation (e.g., "weather. . in" → "weather in")
        import re
        combined = re.sub(r'[.!?]\s+[.!?]', '.', combined)
        
        # Clean up awkward punctuation before lowercase continuation
        # "weather? in london" → "weather in london"
        # "weather. in london" → "weather in london"  
        combined = re.sub(r'([.!?])\s+([a-z])', r' \2', combined)
        
        # If we removed all ending punctuation and the sentence doesn't end with one, add a period
        if combined and not combined[-1] in '.!?,;:':
            # Check if last chunk originally had punctuation
            if transcripts and transcripts[-1].strip() and transcripts[-1].strip()[-1] in '.!?':
                # Keep the original ending punctuation
                combined += transcripts[-1].strip()[-1]
        
        return combined.strip()
    
    def _transcribe_audio_chunk_async(self, audio_frames: list) -> Future:
        """
        Transcribe an audio chunk asynchronously in a background thread.
        
        :param audio_frames: List of audio frame data
        :return: Future object containing the transcription result
        """
        def transcribe_task():
            temp_filename: Optional[Path] = None
            try:
                # Create temporary audio file
                temp_filename = unique_tmp_audio_file("chunk")
                
                # Save audio frames to file
                with wave.open(str(temp_filename), 'wb') as wf:
                    wf.setnchannels(self.channels)
                    wf.setsampwidth(pyaudio.PyAudio().get_sample_size(self.audio_format))
                    wf.setframerate(self.rate)
                    wf.writeframes(b''.join(audio_frames))
                
                # Transcribe the audio
                audio_data = self.load_audio_data(str(temp_filename))
                
                # Handle both faster-whisper and standard whisper
                if self.using_faster_whisper:
                    segments, info = self.model.transcribe(audio_data, language="en", initial_prompt=self.vocabulary_hints)
                    transcribed_text = " ".join([segment.text for segment in segments]).strip()
                else:
                    result = self.model.transcribe(audio_data, language="en", initial_prompt=self.vocabulary_hints)
                    transcribed_text = result["text"].strip()
                
                return transcribed_text
                
            except Exception as e:
                print(f"❌ Error transcribing chunk: {e}")
                return ""
            finally:
                # Clean up temp file
                if temp_filename and temp_filename.exists():
                    try:
                        temp_filename.unlink()
                    except:
                        pass
        
        return self.transcription_executor.submit(transcribe_task)
    
    def calculate_confidence_score(self, transcription: str, wake_word: str, position: int) -> int:
        """Compatibility wrapper around extracted wake-word scorer."""
        return self.wakeword_scorer.calculate_confidence_score(transcription, wake_word, position)
    
    def extract_command_with_confidence(self, transcription: str, wake_words: list) -> tuple:
        """Compatibility wrapper around extracted wake-word scorer."""
        return self.wakeword_scorer.extract_command_with_confidence(transcription, wake_words)
    
    def record_audio(self, duration: Optional[int] = None) -> str:
        """Record audio from microphone and return the file path."""
        return self.audio_io.record_audio(duration=duration)
    
    def load_audio_data(self, audio_file_path: Union[str, Path]) -> np.ndarray:
        """Load audio data directly from WAV file without FFmpeg."""
        return self.audio_io.load_audio_data(audio_file_path)

    def transcribe_audio(self, audio_file_path: Union[str, Path]) -> str:
        """Transcribe audio file to text using Whisper."""
        return self.audio_io.transcribe_audio(audio_file_path)
    
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
        """Set how long to wait for follow-up questions after a response."""
        conversation_state.set_conversation_timeout(self, timeout)

    def enter_conversation_mode(self):
        """Enter conversation mode - listen for follow-ups without wake word."""
        conversation_state.enter_conversation_mode(self)

    def exit_conversation_mode(self):
        """Exit conversation mode - return to wake word detection."""
        conversation_state.exit_conversation_mode(self)

    def update_conversation_activity(self):
        """Mark that speech activity was detected (timer handles restart)."""
        conversation_state.update_conversation_activity(self)
    
    def check_engagement_timeout(self):
        """Check if user engagement timeout has expired (false-positive detection)."""
        conversation_state.check_engagement_timeout(self)

    def set_wake_words(self, wake_words: list):
        """
        Set custom wake words for voice activation.
        
        :param wake_words: List of wake phrases like ["hey myai", "hey assistant"]
        """
        self.wake_words = [word.lower() for word in wake_words]
        self.wakeword_scorer.set_wake_words(self.wake_words)
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

    def _is_speech_vad(self, audio_frame: bytes) -> bool:
        """
        Check if audio frame contains speech using WebRTC VAD.
        
        :param audio_frame: Raw audio bytes from pyaudio stream
        :return: True if speech detected, False otherwise
        """
        if not self.enable_vad or self.vad is None:
            # VAD disabled, assume all audio might be speech
            return True
        
        try:
            # WebRTC VAD requires specific frame sizes (10, 20, or 30ms)
            # Calculate required frame size in bytes (16-bit = 2 bytes per sample)
            frame_size_bytes = self.vad_frame_size * 2
            
            if len(audio_frame) < frame_size_bytes:
                # Frame too small, can't process
                return False
            
            # Take only the exact frame size needed for VAD
            frame = audio_frame[:frame_size_bytes]
            
            # VAD returns True if speech is detected in the frame
            return self.vad.is_speech(frame, self.rate)
        except Exception as e:
            # If VAD fails for any reason, default to True to avoid missing speech
            # This ensures the system degrades gracefully
            return True

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
            buffer_duration = 5.0  # Keep 5 seconds of rolling audio
            buffer_size = int(self.rate * buffer_duration / self.chunk)
            
            # Timing thresholds (in milliseconds for clarity)
            SILENCE_THRESHOLD_VOLUME = 300  # Volume level (lower OK since VAD does smart filtering)
            PRE_ROLL_MS = 200  # Capture 200ms before speech starts (context)
            POST_ROLL_MS = 300  # Require 300ms of silence to end recording
            MIN_COOLDOWN_MS = 500  # Minimum time between processing speech segments
            MAX_SPEECH_DURATION_S = 60.0  # Failsafe: stop after 60 seconds
            
            # Convert milliseconds to frame counts (each chunk = 20ms)
            CHUNK_DURATION_MS = 20  # 320 samples at 16kHz = 20ms
            pre_roll_frames = int(PRE_ROLL_MS / CHUNK_DURATION_MS)  # 10 frames = 200ms
            post_roll_frames = int(POST_ROLL_MS / CHUNK_DURATION_MS)  # 15 frames = 300ms
            min_cooldown_frames = int(MIN_COOLDOWN_MS / CHUNK_DURATION_MS)  # 25 frames = 500ms
            
            speech_detected = False
            speech_frames = []
            silence_count = 0
            speech_start_time = 0  # Track when speech recording started
            last_speech_time = 0  # Track when we last processed speech
            frames_since_last_speech = 0  # Track cooldown period
            
            # VAD consecutive frame tracking
            vad_speech_frames = 0
            vad_required_frames = 3  # Require 3 consecutive speech frames to confirm speech (60ms)
            
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
                    
                    # Track time since last speech processing (cooldown)
                    frames_since_last_speech += 1
                    
                    # Detect speech activity with two-stage filtering
                    current_time = time.time()
                    
                    # STAGE 1: Volume check (fast pre-filter)
                    if volume > SILENCE_THRESHOLD_VOLUME:
                        # STAGE 2: VAD check (accurate speech detection)
                        is_speech = self._is_speech_vad(data)
                        
                        if is_speech:
                            vad_speech_frames += 1
                        else:
                            vad_speech_frames = 0
                            # Reset speech detection if VAD says not speech (e.g., door slam, keyboard)
                            if speech_detected and silence_count == 0:
                                # Just started recording but VAD confirms it's not speech
                                speech_detected = False
                                speech_frames = []
                        
                        # Only proceed if we have enough consecutive VAD-confirmed speech frames
                        if vad_speech_frames >= vad_required_frames:
                            if not speech_detected:
                                # Only start new speech detection if enough time has passed since last speech (cooldown)
                                if frames_since_last_speech >= min_cooldown_frames:
                                    speech_detected = True
                                    speech_start_time = current_time  # Track when recording started
                                    frames_since_last_speech = 0  # Reset cooldown counter
                                    
                                    # Add pre-roll: Include recent audio buffer for context
                                    # pre_roll_frames is already calculated (10 frames = 200ms)
                                    speech_frames = list(audio_buffer)[-pre_roll_frames:] if len(audio_buffer) >= pre_roll_frames else list(audio_buffer)
                                    
                                    if self.enable_vad:
                                        print(f"🎤 Speech detected (VAD confirmed) with {PRE_ROLL_MS}ms pre-roll, recording...")
                                    else:
                                        print("🎤 Speech detected, recording...")
                                    
                                    # CRITICAL: Mark speech processing as active immediately for conversation timer
                                    self.speech_being_processed = True
                                    
                                    # If we're in conversation mode, notify once at the start
                                    if self.in_conversation:
                                        self.update_conversation_activity()
                            
                            if speech_detected:
                                speech_frames.append(data)
                                silence_count = 0
                                
                                # Failsafe: Check if recording has gone on too long
                                if current_time - speech_start_time > MAX_SPEECH_DURATION_S:
                                    print(f"⏱️ Maximum recording duration ({MAX_SPEECH_DURATION_S}s) reached, processing speech...")
                                    self._process_speech_chunk(speech_frames)
                                    speech_detected = False
                                    speech_frames = []
                                    silence_count = 0
                                    last_speech_time = current_time
                                    vad_speech_frames = 0
                    else:
                        # Volume below threshold - reset VAD counter
                        vad_speech_frames = 0
                        
                        if speech_detected:
                            silence_count += 1
                            speech_frames.append(data)
                            
                            # Use chunked transcription if enabled, otherwise use traditional approach
                            if self.enable_chunked_transcription:
                                # Chunked mode: Trigger on short pause (500ms = 25 frames at 20ms per frame)
                                short_pause_threshold = int(500 / CHUNK_DURATION_MS)  # 25 frames
                                
                                if silence_count > short_pause_threshold:
                                    print(f"⚡ Short pause detected (500ms), starting chunked processing...")
                                    # Pass the stream so we can continue listening
                                    self._process_speech_with_chunking(speech_frames, stream)
                                    speech_detected = False
                                    speech_frames = []
                                    silence_count = 0
                                    last_speech_time = current_time
                                    vad_speech_frames = 0
                                    # Clear audio buffer to prevent contamination from this interaction
                                    audio_buffer.clear()
                            else:
                                # Traditional mode: Use POST_ROLL_MS threshold (300ms = 15 frames)
                                # This provides consistent end-of-speech detection
                                if silence_count > post_roll_frames:
                                    print(f"🔄 Processing speech (after {POST_ROLL_MS}ms silence)...")
                                    self._process_speech_chunk(speech_frames)
                                    speech_detected = False
                                    speech_frames = []
                                    silence_count = 0
                                    last_speech_time = current_time  # Update last speech time
                                    vad_speech_frames = 0
                                    # Clear audio buffer to prevent contamination from this interaction
                                    audio_buffer.clear()
                    
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

    def _process_speech_with_chunking(self, initial_frames, stream):
        """Process speech with dynamic chunking and parallel transcription."""
        return self.chunked_processor.process_speech_with_chunking(initial_frames, stream)

    def _process_combined_transcript(self, transcribed_text):
        """Process a complete (potentially multi-chunk) transcript for wake word detection."""
        return self.chunked_processor.process_combined_transcript(transcribed_text)

    def _process_speech_chunk(self, speech_frames):
        """Process a chunk of speech to check for wake words."""
        return self.speech_chunk_processor.process_speech_chunk(speech_frames)

    def start_conversation_timer(self):
        """Start a simple conversation timer that pauses while speech is processed."""
        conversation_state.start_conversation_timer(self)

    def cleanup_audio_files(self):
        """Clean up any leftover audio files."""
        try:
            if TMP_AUDIO_DIR.exists():
                for pattern in ("wake_audio_*.wav", "myai_audio_*.wav", "chunk_*.wav"):
                    for file in TMP_AUDIO_DIR.glob(pattern):
                        try:
                            file.unlink()
                            print(f"🗑️ Cleaned up leftover file: {file.name}")
                        except Exception:
                            pass
                # If directory is empty, remove it
                if not any(TMP_AUDIO_DIR.iterdir()):
                    TMP_AUDIO_DIR.rmdir()
        except Exception as e:
            print(f"⚠️ Error during cleanup: {e}")

    def stop_recording(self):
        """Stop the current recording."""
        self.is_recording = False
