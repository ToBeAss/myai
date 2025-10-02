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

class SpeechToText:
    """Speech-to-text handler using OpenAI Whisper for offline processing."""
    
    def __init__(self, model_size: str = "tiny"):
        """
        Initialize the speech-to-text system.
        
        :param model_size: Whisper model size ('tiny', 'base', 'small', 'medium', 'large')
                          'tiny' is fastest and smallest (39MB), 'base' is more accurate (142MB)
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
            
            # Language preferences (None = auto-detect)
            self.preferred_language = None  # Can be set to 'en', 'no', etc.
            self.task = "transcribe"  # or "translate" to always translate to English
            self.allowed_languages = None  # None = all languages, or list like ['en', 'no']
            
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
            
            print("✅ Speech-to-text system ready!")
            print("🌍 Multilingual support: Auto-detects English, Norwegian, and 97+ other languages")
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
            print("🔄 Starting Whisper transcription...")
            
            # Load audio data directly (bypassing Whisper's FFmpeg dependency)
            audio_data = self.load_audio_data(audio_file_path)
            
            # Transcribe using the loaded audio data with language detection
            # Whisper automatically detects language, but we can get that info
            result = self.model.transcribe(
                audio_data,
                language=self.preferred_language,  # Use preferred language or auto-detect
                task=self.task  # "transcribe" or "translate"
            )
            
            transcribed_text = result["text"].strip()
            detected_language = result.get("language", "unknown")
            
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
                        language=self.preferred_language,
                        task=self.task
                    )
                    transcribed_text = result["text"].strip()
                    detected_language = result.get("language", "unknown")
                    
                    if transcribed_text:
                        print("✅ Amplification helped!")
                    else:
                        print("❌ Still no speech detected after amplification")
            
            # Check if detected language is in allowed list
            if self.allowed_languages and detected_language not in self.allowed_languages:
                print(f"⚠️ Detected language '{detected_language}' not in allowed list {self.allowed_languages}")
                
                # Try with the most likely allowed language if Norwegian was detected as Swedish
                if detected_language == "sv" and "no" in self.allowed_languages:
                    print("🔄 Swedish detected, retrying as Norwegian...")
                    result = self.model.transcribe(
                        audio_data,
                        language="no",  # Force Norwegian
                        task=self.task
                    )
                    transcribed_text = result["text"].strip()
                    detected_language = "no (forced)"
                elif detected_language not in ["en", "no", "nb", "nn"] and "en" in self.allowed_languages:
                    print("🔄 Unknown language detected, retrying as English...")
                    result = self.model.transcribe(
                        audio_data,
                        language="en",  # Force English
                        task=self.task
                    )
                    transcribed_text = result["text"].strip()
                    detected_language = "en (forced)"
            
            # Show language detection result
            language_names = {
                "en": "English",
                "no": "Norwegian", 
                "nb": "Norwegian Bokmål",
                "nn": "Norwegian Nynorsk",
                "sv": "Swedish",
                "da": "Danish",
                "en (forced)": "English (forced)",
                "no (forced)": "Norwegian (forced)"
            }
            language_display = language_names.get(detected_language, detected_language)
            
            print(f"🌍 Detected language: {language_display} ({detected_language})")
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
    
    def set_language_preference(self, language: Optional[str] = None, task: str = "transcribe", allowed_languages: Optional[list] = None):
        """
        Set language preferences for transcription.
        
        :param language: Language code ('en', 'no', 'nb', 'nn', etc.) or None for auto-detect
        :param task: 'transcribe' to keep original language, 'translate' to translate to English
        :param allowed_languages: List of allowed language codes ['en', 'no'] or None for all languages
        """
        self.preferred_language = language
        self.task = task
        self.allowed_languages = allowed_languages
        
        language_names = {
            "en": "English",
            "no": "Norwegian",
            "nb": "Norwegian Bokmål", 
            "nn": "Norwegian Nynorsk"
        }
        
        if language:
            lang_name = language_names.get(language, language)
            print(f"🌍 Language preference set to: {lang_name}")
        else:
            print("🌍 Language preference: Auto-detect")
        
        if allowed_languages:
            lang_list = [language_names.get(lang, lang) for lang in allowed_languages]
            print(f"🔒 Allowed languages: {', '.join(lang_list)}")
        else:
            print("🌍 Allowed languages: All")
        
        if task == "translate":
            print("🔄 Task: Translate to English")
        else:
            print("📝 Task: Transcribe in original language")

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
        
        print("👂 Continuous listening started...")
        print(f"🎯 Say one of: {', '.join(self.wake_words)}")
        print("🔇 Press Ctrl+C to stop")

    def stop_continuous_listening(self):
        """Stop continuous listening."""
        self.is_listening = False
        # Clean up any leftover files
        self.cleanup_audio_files()
        print("🔇 Continuous listening stopped")

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
            
            print("✅ Listening for wake words...")
            
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
            
            # Transcribe the audio
            audio_data = self.load_audio_data(temp_filename)
            result = self.model.transcribe(audio_data, language=self.preferred_language)
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
                    self.wake_callback(transcribed_text)
                return
            
            # Check for wake words (only when not in conversation mode)
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
                        # Check if the command seems incomplete (ends with trailing words that suggest continuation)
                        incomplete_endings = ["a", "an", "the", "how", "what", "where", "when", "why", "how do", "how to", "what is", "make a"]
                        seems_incomplete = any(command_text.strip().endswith(ending) for ending in incomplete_endings)
                        
                        if seems_incomplete:
                            print(f"⚠️ Command seems incomplete: '{command_text}' - Please continue or repeat")
                            if self.wake_callback:
                                self.wake_callback(command_text + " [INCOMPLETE - Please continue or repeat your question]")
                        else:
                            # Complete command - use it directly
                            if self.wake_callback:
                                self.wake_callback(command_text)
                    else:
                        # Just wake word detected, but speech might have been cut off
                        # Wait a bit longer and try to capture more speech
                        print("👂 Wake word detected, waiting for complete question...")
                        time.sleep(1.0)  # Give user time to continue speaking
                        
                        # The speech detection will continue and capture more if they're still talking
                        # If they've finished, we'll ask them to continue
                        if self.wake_callback:
                            self.wake_callback("") # Empty command will trigger a "what can I help you with?" response
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
