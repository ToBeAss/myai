import os
from google.cloud import texttospeech
from dotenv import load_dotenv
import tempfile
import pygame
from typing import Optional, Union
import time
from pathlib import Path
import threading
import queue
from myai.paths import data_file
from .chunking import find_sentence_boundary, is_sentence_boundary, is_weak_comma
from .usage_tracker import TTSUsageTracker

class TextToSpeech:
    """Text-to-speech handler using Google Cloud TTS with usage tracking."""
    
    # Voice tier definitions with monthly free character limits
    VOICE_TIERS = {
        'standard': {
            'free_chars': 4_000_000,  # 4 million characters per month
            'patterns': ['Standard'],
            'price_per_million': 4.00  # USD (after free tier)
        },
        'wavenet': {
            'free_chars': 4_000_000,  # 4 million characters per month
            'patterns': ['WaveNet'],
            'price_per_million': 4.00  # USD (after free tier)
        },
        'neural2': {
            'free_chars': 1_000_000,  # 1 million characters per month
            'patterns': ['Neural2'],
            'price_per_million': 16.00  # USD (after free tier)
        },
        'studio': {
            'free_chars': 1_000_000,  # 1 million characters per month
            'patterns': ['Studio'],
            'price_per_million': 160.00  # USD (after free tier)
        },
        'chirp': {
            'free_chars': 1_000_000,  # 1 million characters per month (Chirp3-HD: cutting-edge LLM-powered TTS)
            'patterns': ['Chirp', 'Chirp3'],
            'price_per_million': 30.00  # USD (after free tier)
        },
        'polyglot': {
            'free_chars': 1_000_000,  # 1 million characters per month (Preview)
            'patterns': ['Polyglot'],
            'price_per_million': 16.00  # USD (after free tier)
        },
        # Note: Journey voices not listed - may not have free tier or are deprecated
        # Excluded: Instant custom voice, Gemini 2.5 Flash TTS, Gemini 2.5 Pro TTS (no free tier)
    }
    
    def __init__(self, voice_name: str = "en-US-Standard-A", language_code: str = "en-US", 
                 speaking_rate: float = 1.0, pitch: float = 0.0, 
                 enforce_free_tier: bool = True, usage_file: Optional[Union[str, Path]] = None,
                 fallback_voice: Optional[str] = None):
        """
        Initialize the Text-to-Speech system.
        
        :param voice_name: Google Cloud TTS voice name (e.g., 'en-US-Standard-A', 'en-GB-Standard-A')
        :param language_code: Language code (e.g., 'en-US', 'en-GB', 'nb-NO' for Norwegian)
        :param speaking_rate: Speaking rate (0.25 to 4.0, default 1.0)
        :param pitch: Voice pitch (-20.0 to 20.0, default 0.0)
        :param enforce_free_tier: If True, block requests that would exceed free tier
        :param usage_file: Path to file for tracking character usage
        :param fallback_voice: Optional fallback voice to use when primary voice quota is exhausted
        """
        print("🔊 Initializing Google Cloud Text-to-Speech...")
        
        # Load environment variables
        load_dotenv()
        
        # Check if credentials are set
        credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if not credentials_path:
            raise ValueError(
                "GOOGLE_APPLICATION_CREDENTIALS environment variable is not set. "
                "Please set it in your .env file to point to your Google Cloud credentials JSON file."
            )
        
        if not os.path.exists(credentials_path):
            raise FileNotFoundError(
                f"Google Cloud credentials file not found at: {credentials_path}. "
                f"Please ensure the file exists and the path in .env is correct."
            )
        
        try:
            # Initialize the Google Cloud TTS client
            self.client = texttospeech.TextToSpeechClient()
            
            # Store voice configuration
            self.primary_voice_name = voice_name  # Original preferred voice
            self.voice_name = voice_name  # Currently active voice
            self.fallback_voice = fallback_voice  # Fallback voice when quota exhausted
            self.language_code = language_code
            self.speaking_rate = speaking_rate
            self.pitch = pitch
            self.enforce_free_tier = enforce_free_tier
            self.usage_file = Path(usage_file) if usage_file else data_file("tts_usage.json")
            self.using_fallback = False  # Track if we're currently using fallback
            self._usage_tracker = TTSUsageTracker(self.usage_file, self.VOICE_TIERS)
            
            # Determine voice tiers
            self.voice_tier = self._determine_voice_tier(voice_name)
            self.fallback_tier = self._determine_voice_tier(fallback_voice) if fallback_voice else None
            
            # Load usage data
            self.usage_data = self._load_usage()
            
            # Initialize pygame mixer for audio playback
            pygame.mixer.init()
            
            # Test the connection by listing available voices (optional)
            self._test_connection()
            
            # Check if we should start with fallback due to quota
            self._check_and_switch_voice()
            
            print(f"✅ Text-to-Speech initialized successfully!")
            print(f"🗣️  Primary Voice: {self.primary_voice_name} ({language_code})")
            print(f"💎 Primary Tier: {self.voice_tier.upper()}")
            print(f"📊 Free Tier Limit: {self.VOICE_TIERS[self.voice_tier]['free_chars']:,} chars/month")
            
            if self.fallback_voice:
                print(f"🔄 Fallback Voice: {self.fallback_voice}")
                print(f"💎 Fallback Tier: {self.fallback_tier.upper()}")
                print(f"📊 Fallback Limit: {self.VOICE_TIERS[self.fallback_tier]['free_chars']:,} chars/month")
            
            self._print_usage_stats()
            
        except Exception as e:
            print(f"❌ Error initializing Google Cloud TTS: {e}")
            raise
    
    def _determine_voice_tier(self, voice_name: str) -> str:
        """Determine which tier a voice belongs to based on its name."""
        for tier, info in self.VOICE_TIERS.items():
            for pattern in info['patterns']:
                if pattern in voice_name:
                    return tier
        # Default to standard if no pattern matches
        return 'standard'
    
    def _is_sentence_boundary(self, text: str, position: int) -> bool:
        """Compatibility wrapper around chunk-boundary helper logic."""
        return is_sentence_boundary(text, position)
    
    def _is_weak_comma(self, text: str, position: int) -> bool:
        """Compatibility wrapper around chunk-boundary helper logic."""
        return is_weak_comma(text, position)
    
    def _find_sentence_boundary(self, text: str, chunk_chars: str = ".!?") -> int:
        """Compatibility wrapper around chunk-boundary helper logic."""
        return find_sentence_boundary(text, chunk_chars)
    
    def _load_usage(self) -> dict:
        """Load usage data from file."""
        return self._usage_tracker.load_usage()
    
    def _create_new_usage_data(self) -> dict:
        """Create fresh usage data structure."""
        return self._usage_tracker.create_new_usage_data()
    
    def _save_usage(self):
        """Save usage data to file."""
        self._usage_tracker.save_usage(self.usage_data)
    
    def _update_usage(self, char_count: int):
        """Update usage statistics."""
        self.usage_data = self._usage_tracker.update_usage(
            usage_data=self.usage_data,
            voice_name=self.voice_name,
            determine_voice_tier=self._determine_voice_tier,
            char_count=char_count,
        )
    
    def _check_and_switch_voice(self) -> bool:
        """Check if we should switch between primary and fallback voice."""
        switched, voice_name, using_fallback = self._usage_tracker.check_and_switch_voice(
            usage_data=self.usage_data,
            voice_name=self.voice_name,
            using_fallback=self.using_fallback,
            primary_voice_name=self.primary_voice_name,
            voice_tier=self.voice_tier,
            fallback_voice=self.fallback_voice,
            fallback_tier=self.fallback_tier,
        )
        self.voice_name = voice_name
        self.using_fallback = using_fallback
        return switched
    
    def _check_quota(self, text: str) -> tuple[bool, str]:
        """Check if the request would exceed free tier quota."""
        allowed, message, voice_name, using_fallback = self._usage_tracker.check_quota(
            text=text,
            enforce_free_tier=self.enforce_free_tier,
            usage_data=self.usage_data,
            voice_name=self.voice_name,
            using_fallback=self.using_fallback,
            fallback_voice=self.fallback_voice,
            voice_tier=self.voice_tier,
            fallback_tier=self.fallback_tier,
            determine_voice_tier=self._determine_voice_tier,
        )
        self.voice_name = voice_name
        self.using_fallback = using_fallback
        return allowed, message
    
    def _print_usage_stats(self):
        """Print current usage statistics."""
        self._usage_tracker.print_usage_stats(
            usage_data=self.usage_data,
            using_fallback=self.using_fallback,
            voice_tier=self.voice_tier,
            fallback_voice=self.fallback_voice,
            fallback_tier=self.fallback_tier,
            enforce_free_tier=self.enforce_free_tier,
        )
    
    def get_usage_stats(self) -> dict:
        """Get detailed usage statistics."""
        return self._usage_tracker.usage_stats(
            usage_data=self.usage_data,
            voice_name=self.voice_name,
            using_fallback=self.using_fallback,
            primary_voice_name=self.primary_voice_name,
            voice_tier=self.voice_tier,
            fallback_voice=self.fallback_voice,
            fallback_tier=self.fallback_tier,
        )
    
    def get_active_voice_info(self) -> dict:
        """Get information about the currently active voice."""
        return {
            'voice_name': self.voice_name,
            'is_primary': not self.using_fallback,
            'is_fallback': self.using_fallback,
            'primary_voice': self.primary_voice_name,
            'fallback_voice': self.fallback_voice
        }
    
    def _test_connection(self):
        """Test the connection to Google Cloud TTS API."""
        try:
            # This will fail if credentials are invalid
            response = self.client.list_voices()
            print(f"✅ Successfully connected to Google Cloud TTS API")
            print(f"📋 Available voices: {len(response.voices)} voices found")
        except Exception as e:
            print(f"⚠️  Warning: Could not verify connection to Google Cloud TTS: {e}")
    
    def set_voice(self, voice_name: str, language_code: Optional[str] = None):
        """
        Change the voice settings.
        
        :param voice_name: New voice name
        :param language_code: Optional new language code
        """
        self.voice_name = voice_name
        if language_code:
            self.language_code = language_code
        print(f"🗣️  Voice updated to: {voice_name} ({self.language_code})")
    
    def set_speaking_rate(self, rate: float):
        """
        Change the speaking rate.
        
        :param rate: Speaking rate (0.25 to 4.0)
        """
        if 0.25 <= rate <= 4.0:
            self.speaking_rate = rate
            print(f"⚡ Speaking rate set to: {rate}x")
        else:
            raise ValueError("Speaking rate must be between 0.25 and 4.0")
    
    def set_pitch(self, pitch: float):
        """
        Change the voice pitch.
        
        :param pitch: Voice pitch (-20.0 to 20.0)
        """
        if -20.0 <= pitch <= 20.0:
            self.pitch = pitch
            print(f"🎵 Pitch set to: {pitch}")
        else:
            raise ValueError("Pitch must be between -20.0 and 20.0")
    
    def synthesize_to_file(self, text: str, output_file: str) -> str:
        """
        Synthesize text to an audio file.
        
        :param text: Text to synthesize
        :param output_file: Path to save the audio file
        :return: Path to the saved audio file
        """
        if not text or not text.strip():
            print("⚠️  Warning: Empty text provided, skipping synthesis")
            return ""
        
        # Check quota before making API call
        allowed, message = self._check_quota(text)
        if not allowed:
            print(message)
            return ""
        
        try:
            # Set the text input to be synthesized
            synthesis_input = texttospeech.SynthesisInput(text=text)
            
            # Build the voice request
            voice = texttospeech.VoiceSelectionParams(
                language_code=self.language_code,
                name=self.voice_name
            )
            
            # Select the type of audio file you want returned
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=self.speaking_rate,
                pitch=self.pitch
            )
            
            # Perform the text-to-speech request
            response = self.client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            
            # Write the response to the output file
            with open(output_file, "wb") as out:
                out.write(response.audio_content)
            
            # Update usage tracking
            self._update_usage(len(text))
            
            return output_file
            
        except Exception as e:
            print(f"❌ Error synthesizing speech: {e}")
            return ""
    
    def speak(self, text: str, wait_until_done: bool = True) -> bool:
        """
        Convert text to speech and play it immediately.
        
        :param text: Text to speak
        :param wait_until_done: If True, block until speech is finished
        :return: True if successful, False otherwise
        """
        if not text or not text.strip():
            return False
        
        try:
            # Create a temporary file for the audio
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
                temp_filename = temp_file.name
            
            # Synthesize speech to the temp file
            audio_file = self.synthesize_to_file(text, temp_filename)
            
            if not audio_file:
                return False
            
            # Play the audio file
            pygame.mixer.music.load(audio_file)
            pygame.mixer.music.play()
            
            # Wait for playback to finish if requested
            if wait_until_done:
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
            
            # Clean up the temporary file after playback
            if wait_until_done:
                try:
                    os.remove(temp_filename)
                except:
                    pass  # Ignore errors when deleting temp files
            
            return True
            
        except Exception as e:
            print(f"❌ Error speaking text: {e}")
            return False
    
    def speak_streaming(self, text_generator, chunk_on: str = ".", print_text: bool = True, 
                       min_chunk_size: int = 20):
        """
        Speak text as it's being generated (streaming mode) with parallel processing.
        This accumulates text until a sentence boundary, then speaks it in a separate thread
        while continuing to receive new tokens from the LLM.
        
        :param text_generator: Generator that yields text tokens
        :param chunk_on: Character to chunk on (default: "." for sentences)
        :param print_text: If True, print the text as it's being spoken
        :param min_chunk_size: Minimum characters before considering a chunk (prevents tiny fragments)
        """
        buffer = ""
        speech_queue = queue.Queue()
        is_processing = threading.Event()
        is_processing.set()  # Start as processing
        
        def speech_worker():
            """Worker thread that speaks queued text chunks."""
            while True:
                item = speech_queue.get()
                if item is None:  # Poison pill to stop the thread
                    speech_queue.task_done()
                    break
                
                text_to_speak = item
                self.speak(text_to_speak, wait_until_done=True)
                speech_queue.task_done()
        
        # Start the speech worker thread
        speech_thread = threading.Thread(target=speech_worker, daemon=True)
        speech_thread.start()
        
        try:
            # Process tokens from the LLM
            for token in text_generator:
                if print_text:
                    print(token.content, end="", flush=True)
                buffer += token.content
                
                # Check if we have potential sentence boundaries
                if any(c in buffer for c in chunk_on):
                    # Find the last valid sentence boundary
                    last_chunk_idx = self._find_sentence_boundary(buffer, chunk_on)
                    
                    if last_chunk_idx >= 0:
                        # Extract the complete sentence(s)
                        to_speak = buffer[:last_chunk_idx + 1].strip()
                        
                        # Only chunk if we have substantial content (prevents tiny fragments)
                        # This ensures we don't speak very short incomplete phrases
                        if len(to_speak) >= min_chunk_size:
                            # Keep the remainder for the next iteration
                            buffer = buffer[last_chunk_idx + 1:]
                            
                            # Queue the text for speaking (non-blocking)
                            speech_queue.put(to_speak)
            
            # Speak any remaining text in the buffer
            if buffer.strip():
                speech_queue.put(buffer.strip())
            
            # Signal the worker to stop after finishing all queued items
            speech_queue.put(None)
            
            # Wait for all speech to complete
            speech_thread.join()
            
            if print_text:
                print()  # New line at the end
                
        except Exception as e:
            print(f"\n❌ Error in streaming speech: {e}")
            speech_queue.put(None)  # Stop the worker
            speech_thread.join()
    
    @staticmethod
    def _estimate_audio_duration(file_path: str) -> float:
        """Estimate the duration of an MP3 file from its size.

        Uses ~32 kbps (4 KB/s), which is typical for Google Cloud TTS MP3
        output.  This avoids calling any pygame API so it is safe to use
        from any thread.
        """
        try:
            return os.path.getsize(file_path) / 4000.0
        except Exception:
            return 0.0

    def speak_streaming_async(self, text_generator, chunk_on: str = ",.!?", print_text: bool = True,
                              min_chunk_size: int = 15):
        """
        Speak text as it's being generated with truly parallel processing.
        Multiple sentences can be synthesized and queued while others are playing.
        This provides the fastest response time.

        Chunking strategy
        -----------------
        * **Chunk 0 (fast start):** fire synthesis at the first punctuation
          boundary (including commas) to minimise time-to-first-sound.
        * **Chunk 1+ (quality chunks):** accumulate tokens and, once the
          remaining playback time of previously queued audio drops to within
          the chunk's *estimated* synthesis time + 200 ms (derived from an
          observed chars/sec rate), trigger synthesis at the last available
          sentence-ending boundary (``.!?``).  Scaling the threshold by chunk
          length keeps playback gapless even when chunk sizes vary widely.

        :param text_generator: Generator that yields text tokens
        :param chunk_on: Characters used to detect chunk 0 boundaries only (default: ``",.!?"``)
        :param print_text: If True, print the text as it's being spoken
        :param min_chunk_size: Minimum characters before considering a chunk (prevents tiny fragments, default 15)
        """
        buffer = ""
        synthesis_queue = queue.Queue()
        playback_queue = queue.Queue()

        # ---- per-call timing state (reset each invocation) ----
        chunk_index = 0
        pending_boundary = -1  # cached sentence boundary index for chunk 1+

        # Shared state – accessed from main + worker threads under state_lock
        state_lock = threading.Lock()
        state = {
            "playback_active": False,
            "play_start": 0.0,       # time.monotonic() when current file started
            "play_duration": 0.0,     # duration in seconds of current file
            "queued_total": 0.0,      # total duration of files waiting in playback_queue
            "has_audio": False,       # True once first synthesis result is queued
            "synth_count": 0,         # number of completed syntheses
            "synth_sum": 0.0,         # cumulative synthesis duration
            "avg_synth": 0.4,         # rolling average, seeded at 400 ms
            "synth_chars": 0,         # cumulative characters synthesised
        }

        def _remaining_playback_time() -> float:
            """Total seconds of audio still to play (current + queued)."""
            with state_lock:
                remaining = state["queued_total"]
                if state["playback_active"]:
                    elapsed = time.monotonic() - state["play_start"]
                    remaining += max(0.0, state["play_duration"] - elapsed)
                else:
                    # Chunk being loaded but not yet playing; its
                    # duration was moved from queued_total into
                    # play_duration on dequeue.
                    remaining += state["play_duration"]
                return remaining

        def _update_avg(duration: float, char_count: int):
            with state_lock:
                state["synth_count"] += 1
                state["synth_sum"] += duration
                state["synth_chars"] += char_count
                state["avg_synth"] = state["synth_sum"] / state["synth_count"]

        def _estimate_synth_time(char_count: int) -> float:
            """Estimate synthesis time for a chunk based on observed chars/sec."""
            with state_lock:
                chars = state["synth_chars"]
                total = state["synth_sum"]
                avg = state["avg_synth"]
            if chars > 0 and total > 0:
                rate = chars / total  # chars per second
                return char_count / rate
            return avg

        # ---- worker threads ----
        def synthesis_worker():
            """Worker thread that synthesizes speech."""
            while True:
                item = synthesis_queue.get()
                if item is None:
                    synthesis_queue.task_done()
                    playback_queue.put(None)  # Signal playback worker
                    break

                text_to_speak = item
                temp_filename = None
                try:
                    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
                        temp_filename = temp_file.name

                    t0 = time.monotonic()
                    audio_file = self.synthesize_to_file(text_to_speak, temp_filename)
                    synth_dur = time.monotonic() - t0

                    if audio_file:
                        audio_dur = self._estimate_audio_duration(audio_file)
                        _update_avg(synth_dur, len(text_to_speak))

                        with state_lock:
                            state["queued_total"] += audio_dur
                            state["has_audio"] = True

                        playback_queue.put((audio_file, audio_dur))
                    else:
                        # Synthesis returned nothing (e.g. quota block) – clean up
                        if temp_filename:
                            try:
                                os.remove(temp_filename)
                            except Exception:
                                pass
                except Exception as e:
                    print(f"\n❌ Synthesis error: {e}")
                    if temp_filename:
                        try:
                            os.remove(temp_filename)
                        except Exception:
                            pass

                synthesis_queue.task_done()

        def playback_worker():
            """Worker thread that plays synthesized audio."""
            last_end: float = 0.0  # monotonic time previous chunk finished
            while True:
                item = playback_queue.get()
                if item is None:
                    playback_queue.task_done()
                    break

                audio_file, estimated_dur = item

                # Immediately move the chunk out of queued_total and
                # into play_duration so _remaining_playback_time()
                # always accounts for it (either as queued or active).
                with state_lock:
                    state["queued_total"] = max(0.0, state["queued_total"] - estimated_dur)
                    state["play_duration"] = estimated_dur

                try:
                    # Detect stalls (playback queue went empty)
                    now = time.monotonic()
                    if last_end > 0 and (now - last_end) > 0.15:
                        print(f"\n⚠️  Playback stall: waited {now - last_end:.1f}s for next chunk")

                    # Get accurate duration via pygame (all pygame calls
                    # happen on this single thread to avoid cross-thread
                    # SDL_mixer issues).
                    try:
                        snd = pygame.mixer.Sound(audio_file)
                        actual_dur = snd.get_length()
                        del snd
                        if actual_dur <= 0:
                            actual_dur = estimated_dur
                    except Exception:
                        actual_dur = estimated_dur

                    pygame.mixer.music.load(audio_file)
                    pygame.mixer.music.play()

                    with state_lock:
                        state["play_duration"] = actual_dur
                        state["play_start"] = time.monotonic()
                        state["playback_active"] = True

                    while pygame.mixer.music.get_busy():
                        time.sleep(0.05)

                    last_end = time.monotonic()
                except Exception as e:
                    print(f"\n❌ Playback error: {e}")
                finally:
                    with state_lock:
                        state["playback_active"] = False
                        state["play_duration"] = 0.0
                    try:
                        os.remove(audio_file)
                    except Exception:
                        pass

                playback_queue.task_done()

        # Start worker threads
        synthesis_thread = threading.Thread(target=synthesis_worker, daemon=True)
        playback_thread = threading.Thread(target=playback_worker, daemon=True)
        synthesis_thread.start()
        playback_thread.start()

        try:
            for token in text_generator:
                if print_text:
                    print(token.content, end="", flush=True)
                buffer += token.content

                if chunk_index == 0:
                    # --- Chunk 0: fast start – fire at earliest acceptable boundary ---
                    if any(c in buffer for c in chunk_on):
                        search_start = 0
                        while search_start < len(buffer):
                            rel_idx = find_sentence_boundary(
                                buffer[search_start:], chunk_on, first_only=True,
                            )
                            if rel_idx < 0:
                                break
                            idx = search_start + rel_idx
                            candidate = buffer[:idx + 1].strip()
                            delimiter = buffer[idx]
                            effective_min = 5 if delimiter in '.!?' else min_chunk_size
                            if len(candidate) >= effective_min:
                                buffer = buffer[idx + 1:]
                                synthesis_queue.put(candidate)
                                chunk_index += 1
                                # Remainder may already contain sentence-
                                # ending punctuation; seed pending_boundary
                                # so chunk 1+ doesn't wait for a future token.
                                pending_boundary = self._find_sentence_boundary(
                                    buffer, ".!?",
                                )
                                break
                            search_start = idx + 1
                else:
                    # --- Chunk 1+: quality chunks – sentence boundaries only ---
                    # Only rescan the buffer when the new token contains
                    # sentence-ending punctuation; otherwise reuse the cached
                    # boundary so we still re-evaluate timing each token.
                    if any(c in token.content for c in ".!?"):
                        pending_boundary = self._find_sentence_boundary(buffer, ".!?")

                    if pending_boundary < 0:
                        continue

                    # Wait until chunk 0 has been synthesised and we have a real
                    # playback window to compare against; otherwise remaining==0
                    # would trigger immediately before any audio is ready.
                    with state_lock:
                        has_audio = state["has_audio"]
                    if not has_audio:
                        continue

                    to_speak = buffer[:pending_boundary + 1].strip()

                    # Threshold scales with chunk length: we need enough
                    # remaining playback time to cover synthesising *this*
                    # chunk, not just the average of past (possibly smaller)
                    # chunks.
                    expected_synth = _estimate_synth_time(len(to_speak))
                    threshold = expected_synth + 0.2  # 200 ms margin

                    remaining = _remaining_playback_time()

                    # Edge case: chunk 0 still playing with time to spare
                    # and buffer text is very short – hold for more tokens
                    if remaining > threshold * 2 and len(to_speak) < min_chunk_size:
                        continue

                    if remaining <= threshold:
                        buffer = buffer[pending_boundary + 1:]
                        synthesis_queue.put(to_speak)
                        chunk_index += 1
                        pending_boundary = -1  # reset after consuming

            # LLM stream ended – synthesize whatever is buffered
            if buffer.strip():
                synthesis_queue.put(buffer.strip())

            # Signal workers to stop
            synthesis_queue.put(None)

            # Wait for all work to complete
            synthesis_thread.join()
            playback_thread.join()

            if print_text:
                print()  # New line at the end

        except Exception as e:
            print(f"\n❌ Error in async streaming speech: {e}")
            synthesis_queue.put(None)
            synthesis_thread.join()
            playback_thread.join()
    
    def list_available_voices(self, language_code: Optional[str] = None, show_pricing: bool = True):
        """
        List all available voices from Google Cloud TTS with pricing tiers.
        
        :param language_code: Optional language code to filter voices (e.g., 'en-US', 'en-GB')
        :param show_pricing: If True, show pricing tier information
        """
        try:
            response = self.client.list_voices()
            
            print("\n📋 Available Google Cloud TTS Voices:")
            if show_pricing:
                print("💡 Pricing Tiers (free characters per month):")
                for tier, info in self.VOICE_TIERS.items():
                    print(f"   {tier.upper()}: {info['free_chars']:,} chars/month")
            print("-" * 80)
            
            # Group voices by tier
            voices_by_tier = {tier: [] for tier in self.VOICE_TIERS.keys()}
            other_voices = []
            
            for voice in response.voices:
                # Filter by language if specified
                if language_code:
                    # Check if any of the voice's languages match (prefix match)
                    if not any(lang.startswith(language_code) for lang in voice.language_codes):
                        continue
                
                # Determine tier
                tier = self._determine_voice_tier(voice.name)
                if tier in voices_by_tier:
                    voices_by_tier[tier].append(voice)
                else:
                    other_voices.append(voice)
            
            # Print voices grouped by tier (most free characters first)
            for tier in ['standard', 'wavenet', 'neural2', 'journey', 'chirp', 'studio', 'polyglot']:
                if voices_by_tier[tier]:
                    print(f"\n🎯 {tier.upper()} VOICES ({self.VOICE_TIERS[tier]['free_chars']:,} free/month):")
                    print("-" * 80)
                    for voice in voices_by_tier[tier]:
                        print(f"Voice: {voice.name}")
                        print(f"  Languages: {', '.join(voice.language_codes)}")
                        print(f"  Gender: {texttospeech.SsmlVoiceGender(voice.ssml_gender).name}")
                        print(f"  Sample Rate: {voice.natural_sample_rate_hertz} Hz")
                        print()
            
            if other_voices:
                print(f"\n📌 OTHER VOICES:")
                print("-" * 80)
                for voice in other_voices:
                    print(f"Voice: {voice.name}")
                    print(f"  Languages: {', '.join(voice.language_codes)}")
                    print()
                
        except Exception as e:
            print(f"❌ Error listing voices: {e}")
    
    def stop(self):
        """Stop any currently playing audio."""
        pygame.mixer.music.stop()
    
    def __del__(self):
        """Cleanup when the object is destroyed."""
        try:
            pygame.mixer.quit()
        except:
            pass
