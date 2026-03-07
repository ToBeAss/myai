"""Chunked speech processing helpers for SpeechToText."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from .speech_to_text import SpeechToText


class ChunkedSpeechProcessor:
    """Handle chunked speech transcription orchestration."""

    def __init__(self, stt: "SpeechToText"):
        self.stt = stt

    def process_speech_with_chunking(self, initial_frames, stream) -> None:
        SHORT_PAUSE_MS = 500
        LONG_PAUSE_MS = 1500
        REMAINING_PAUSE_MS = LONG_PAUSE_MS - SHORT_PAUSE_MS
        CHUNK_DURATION_MS = 20

        chunks = []
        chunk_num = 1
        max_chunks = 10

        print(f"⚡ Chunk #{chunk_num}: Starting parallel transcription...")
        first_future = self.stt._transcribe_audio_chunk_async(initial_frames)
        chunks.append((initial_frames.copy(), first_future))

        short_pause_frames = SHORT_PAUSE_MS // CHUNK_DURATION_MS
        remaining_pause_frames = REMAINING_PAUSE_MS // CHUNK_DURATION_MS

        while chunk_num < max_chunks:
            current_chunk_frames = []
            silence_count = 0
            speech_detected_in_chunk = False

            while silence_count < remaining_pause_frames:
                try:
                    data = stream.read(self.stt.chunk, exception_on_overflow=False)
                    audio_chunk = np.frombuffer(data, dtype=np.int16)
                    volume = np.sqrt(np.mean(audio_chunk.astype(np.float32) ** 2))

                    current_chunk_frames.append(data)

                    if volume > 300:
                        is_speech = self.stt._is_speech_vad(data)
                        if is_speech:
                            speech_detected_in_chunk = True
                            silence_count = 0
                        else:
                            silence_count += 1
                    else:
                        silence_count += 1

                    if speech_detected_in_chunk and silence_count >= short_pause_frames:
                        print(f"   ⏸ Short pause detected ({SHORT_PAUSE_MS}ms) after speech in chunk #{chunk_num + 1}")
                        chunk_num += 1
                        print(f"⚡ Chunk #{chunk_num}: Starting parallel transcription...")
                        future = self.stt._transcribe_audio_chunk_async(current_chunk_frames)
                        chunks.append((current_chunk_frames.copy(), future))

                        current_chunk_frames = []
                        silence_count = 0
                        speech_detected_in_chunk = False
                        continue

                    time.sleep(0.01)

                except Exception as e:
                    print(f"❌ Error listening for more speech: {e}")
                    break

            if speech_detected_in_chunk:
                print(f"✅ Long pause detected ({LONG_PAUSE_MS}ms total), user done speaking.")
                chunk_num += 1
                print(f"⚡ Chunk #{chunk_num} (final): Starting transcription...")
                future = self.stt._transcribe_audio_chunk_async(current_chunk_frames)
                chunks.append((current_chunk_frames.copy(), future))
                break
            else:
                print(f"✅ No more speech detected ({LONG_PAUSE_MS}ms total silence), finalizing...")
                break

        print(f"🔄 Waiting for {len(chunks)} chunk(s) to finish transcribing...")
        transcripts = []

        for i, (frames, future) in enumerate(chunks):
            try:
                transcript = future.result(timeout=10.0)
                if transcript:
                    transcripts.append(transcript)
                    print(f"   ✓ Chunk #{i+1}: \"{transcript[:50]}{'...' if len(transcript) > 50 else ''}\"")
            except Exception as e:
                print(f"   ✗ Chunk #{i+1}: Transcription failed - {e}")

        full_transcript = self.stt._clean_chunked_transcript(transcripts).lower()

        if not full_transcript:
            print("⚠️ No valid transcription from chunks")
            chunks.clear()
            self.stt.speech_being_processed = False
            return

        print(f"📝 Combined transcript: \"{full_transcript}\"")
        print(f"   (Cleaned from {len(transcripts)} chunk(s))")

        chunks.clear()
        self.process_combined_transcript(full_transcript)
        self.stt.speech_being_processed = False

    def process_combined_transcript(self, transcribed_text: str) -> None:
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
                return

            print(f"✅ Wake word detected: '{transcribed_text}' (confidence: {confidence})")
            print(f"   Command: '{command}'")

            if self.stt.wake_callback:
                if self.stt.track_metrics and self.stt.metrics:
                    self.stt.metrics.log_activation(
                        transcription=transcribed_text,
                        confidence=confidence,
                        wake_word_position=position,
                    )
                    self.stt.waiting_for_engagement = True
                    self.stt.last_activation_time = time.time()

                self.stt.wake_callback(command)
        else:
            for wake_word in self.stt.wake_words:
                if wake_word in transcribed_text:
                    command = transcribed_text.replace(wake_word, "").strip()
                    print(f"✅ Wake word '{wake_word}' detected!")
                    print(f"   Command: '{command}'")

                    if self.stt.wake_callback:
                        self.stt.wake_callback(command)
                    return
