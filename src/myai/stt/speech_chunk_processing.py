"""Wake-word speech chunk processing helpers for SpeechToText."""

from __future__ import annotations

import time
import wave
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import pyaudio

from myai.paths import unique_tmp_audio_file

if TYPE_CHECKING:
    from .speech_to_text import SpeechToText


class SpeechChunkProcessor:
    """Process speech chunks for wake-word detection and command extraction."""

    def __init__(self, stt: "SpeechToText"):
        self.stt = stt

    def process_speech_chunk(self, speech_frames) -> None:
        temp_filename: Optional[Path] = None
        try:
            temp_filename = unique_tmp_audio_file("wake_audio")

            with wave.open(str(temp_filename), "wb") as wf:
                wf.setnchannels(self.stt.channels)
                wf.setsampwidth(pyaudio.PyAudio().get_sample_size(self.stt.audio_format))
                wf.setframerate(self.stt.rate)
                wf.writeframes(b"".join(speech_frames))

            audio_data = self.stt.load_audio_data(str(temp_filename))

            if self.stt.using_faster_whisper:
                segments, info = self.stt.model.transcribe(
                    audio_data,
                    language="en",
                    initial_prompt=self.stt.vocabulary_hints,
                )
                transcribed_text = " ".join(str(getattr(segment, "text", segment)) for segment in segments).strip().lower()
            else:
                result = self.stt.model.transcribe(
                    audio_data,
                    language="en",
                    initial_prompt=self.stt.vocabulary_hints,
                )
                if isinstance(result, dict):
                    transcribed_text = str(result.get("text", "")).strip().lower()
                else:
                    transcribed_text = str(result).strip().lower()

            if self.stt.is_hallucination(transcribed_text):
                print("⚠️ Transcription appears to be a hallucination from background noise, ignoring...")
                if self.stt.in_conversation:
                    self.stt.exit_conversation_mode()
                return

            if self.stt.in_conversation:
                print(f"💬 Follow-up detected: '{transcribed_text}'")
                if transcribed_text and self.stt.wake_callback:
                    if self.stt.track_metrics and self.stt.waiting_for_engagement and self.stt.metrics:
                        self.stt.metrics.log_outcome(engaged=True)
                        self.stt.waiting_for_engagement = False
                    self.stt.wake_callback(transcribed_text)
                return

            if self.stt.flexible_wake_word:
                command, confidence, position = self.stt.extract_command_with_confidence(
                    transcribed_text,
                    self.stt.wake_words,
                )

                if command is None:
                    if len(transcribed_text) > 3:
                        print(f"🔇 Speech without wake word ignored: '{transcribed_text[:30]}{'...' if len(transcribed_text) > 30 else ''}'")
                        if self.stt.track_metrics and self.stt.metrics:
                            self.stt.metrics.log_true_negative()
                    return

                print(f"🎯 Wake word detected at position {position}")
                print(f"📝 Full transcription: '{transcribed_text}'")
                print(f"📊 Confidence score: {confidence}/100")

                if self.stt.track_metrics and self.stt.metrics:
                    self.stt.metrics.log_activation(transcribed_text, confidence, position)
                    self.stt.last_activation_time = time.time()
                    self.stt.waiting_for_engagement = True

                if confidence >= self.stt.confidence_threshold:
                    if confidence >= 80:
                        print("✅ HIGH confidence - Processing command")
                    elif confidence >= 60:
                        print("⚠️  MEDIUM confidence - Processing command")
                    else:
                        print("❓ LOW confidence - Processing with caution")

                    if self.stt.wake_callback:
                        if self.stt.track_metrics and self.stt.waiting_for_engagement and self.stt.metrics:
                            self.stt.metrics.log_outcome(engaged=True)
                            self.stt.waiting_for_engagement = False
                        self.stt.wake_callback(command)
                else:
                    print(f"🚫 Confidence too low ({confidence} < {self.stt.confidence_threshold}) - Ignoring")
                    if self.stt.track_metrics and self.stt.metrics:
                        self.stt.metrics.log_true_negative()
                        self.stt.waiting_for_engagement = False

            else:
                wake_word_found = False
                for wake_word in self.stt.wake_words:
                    if wake_word in transcribed_text:
                        print(f"🎯 Wake word detected: '{wake_word}'")
                        print(f"📝 Full transcription: '{transcribed_text}'")
                        wake_word_found = True

                        wake_index = transcribed_text.find(wake_word)
                        command_text = transcribed_text[wake_index + len(wake_word):].strip()

                        if command_text:
                            if self.stt.wake_callback:
                                self.stt.wake_callback(command_text)
                        else:
                            if self.stt.wake_callback:
                                self.stt.wake_callback("")
                        break

                if not wake_word_found and len(transcribed_text) > 3:
                    print(f"🔇 Speech without wake word ignored: '{transcribed_text[:30]}{'...' if len(transcribed_text) > 30 else ''}'")

        except Exception as e:
            print(f"❌ Error processing speech chunk: {e}")

        finally:
            if temp_filename:
                for attempt in range(3):
                    try:
                        if temp_filename.exists():
                            time.sleep(0.1)
                            temp_filename.unlink()
                            break
                    except Exception as cleanup_error:
                        if attempt == 2:
                            print(f"⚠️ Could not clean up wake audio file after 3 attempts: {cleanup_error}")
                        else:
                            time.sleep(0.2)

            self.stt.speech_being_processed = False
