"""Audio recording/loading/transcription helpers for SpeechToText."""

from __future__ import annotations

import time
import wave
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import keyboard
import numpy as np
import pyaudio

from myai.paths import REPO_ROOT, unique_tmp_audio_file

if TYPE_CHECKING:
    from .speech_to_text import SpeechToText


class STTAudioIO:
    """Encapsulate audio I/O concerns for SpeechToText."""

    def __init__(self, stt: "SpeechToText"):
        self.stt = stt

    def record_audio(self, duration: Optional[int] = None) -> str:
        try:
            audio = pyaudio.PyAudio()
        except Exception as e:
            print(f"❌ Could not initialize audio system: {e}")
            print("💡 Make sure you have a microphone connected and permissions are granted.")
            return ""

        temp_filename = unique_tmp_audio_file("myai_audio")
        try:
            display_path = temp_filename.relative_to(REPO_ROOT)
        except ValueError:
            display_path = temp_filename
        print(f"📁 Creating audio file: {display_path}")

        try:
            stream = audio.open(
                format=self.stt.audio_format,
                channels=self.stt.channels,
                rate=self.stt.rate,
                input=True,
                frames_per_buffer=self.stt.chunk,
            )
        except Exception as e:
            print(f"❌ Could not open audio stream: {e}")
            audio.terminate()
            return ""

        print("🎤 Recording... Press SPACE to stop recording")
        print("💡 Speak clearly and loudly enough for good recognition")
        frames = []
        self.stt.is_recording = True

        start_time = time.time()
        min_recording_time = 1.0
        last_volume_update = 0

        try:
            while self.stt.is_recording:
                data = stream.read(self.stt.chunk, exception_on_overflow=False)
                frames.append(data)

                current_time = time.time()
                if current_time - last_volume_update > 0.5:
                    audio_chunk = np.frombuffer(data, dtype=np.int16)
                    volume = np.sqrt(np.mean(audio_chunk.astype(np.float32) ** 2))
                    volume_bars = int(volume / 1000)
                    volume_indicator = "█" * min(volume_bars, 10)
                    print(f"\r🔊 Volume: [{volume_indicator:<10}] {volume:.0f}", end="", flush=True)
                    last_volume_update = current_time

                if keyboard.is_pressed("space") and (time.time() - start_time) >= min_recording_time:
                    print(f"\n⏹️ Recording stopped by user ({time.time() - start_time:.1f}s)")
                    break

                if duration and (time.time() - start_time) >= duration:
                    print(f"\n⏹️ Recording stopped - {duration}s limit reached")
                    break

        except Exception as e:
            print(f"❌ Recording error: {e}")
        finally:
            stream.stop_stream()
            stream.close()
            audio.terminate()
            self.stt.is_recording = False

        if not frames:
            print("❌ No audio recorded")
            return ""

        try:
            with wave.open(str(temp_filename), "wb") as wf:
                wf.setnchannels(self.stt.channels)
                wf.setsampwidth(audio.get_sample_size(self.stt.audio_format))
                wf.setframerate(self.stt.rate)
                wf.writeframes(b"".join(frames))

            time.sleep(0.1)

            if temp_filename.exists() and temp_filename.stat().st_size > 0:
                file_size = temp_filename.stat().st_size
                print(f"✅ Audio recorded successfully: {len(frames)} frames, {file_size} bytes")
            else:
                print("❌ Audio file was not created properly")
                return ""

        except Exception as e:
            print(f"❌ Error saving audio: {e}")
            try:
                if temp_filename.exists():
                    temp_filename.unlink()
            except Exception:
                pass
            return ""

        return str(temp_filename)

    def load_audio_data(self, audio_file_path: Path | str) -> np.ndarray:
        try:
            wav_path = Path(audio_file_path)
            with wave.open(str(wav_path), "rb") as wav_file:
                sample_rate = wav_file.getframerate()
                n_channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()
                n_frames = wav_file.getnframes()

                print(f"📊 Audio info: {sample_rate}Hz, {n_channels}ch, {sample_width}bytes, {n_frames}frames")
                raw_audio = wav_file.readframes(n_frames)

                if sample_width == 1:
                    dtype = np.uint8
                elif sample_width == 2:
                    dtype = np.int16
                elif sample_width == 4:
                    dtype = np.int32
                else:
                    raise ValueError(f"Unsupported sample width: {sample_width}")

                audio_data = np.frombuffer(raw_audio, dtype=dtype)

                if n_channels == 2:
                    audio_data = audio_data.reshape(-1, 2).mean(axis=1)

                if dtype == np.uint8:
                    audio_data = (audio_data.astype(np.float32) - 128) / 128
                elif dtype == np.int16:
                    audio_data = audio_data.astype(np.float32) / 32768
                elif dtype == np.int32:
                    audio_data = audio_data.astype(np.float32) / 2147483648

                if sample_rate != 16000:
                    target_length = int(len(audio_data) * 16000 / sample_rate)
                    audio_data = np.interp(
                        np.linspace(0, len(audio_data), target_length),
                        np.arange(len(audio_data)),
                        audio_data,
                    )

                print(f"✅ Audio loaded: {len(audio_data)} samples at 16kHz")
                return audio_data

        except Exception as e:
            print(f"❌ Error loading audio data: {e}")
            raise

    def transcribe_audio(self, audio_file_path: Path | str) -> str:
        if not audio_file_path:
            print("❌ No audio file path provided for transcription")
            return ""

        audio_path = Path(audio_file_path).expanduser()
        audio_path = (Path.cwd() / audio_path).resolve(strict=False)

        transcribed_text = ""
        try:
            print("🔄 Transcribing audio...")

            try:
                display_path = audio_path.relative_to(REPO_ROOT)
            except ValueError:
                display_path = audio_path
            print(f"📁 Absolute path: {display_path}")

            if not audio_path.exists():
                print(f"❌ Audio file not found: {audio_path}")
                temp_dir = audio_path.parent
                try:
                    files = [f.name for f in temp_dir.iterdir()]
                    myai_files = [f for f in files if "myai_audio" in f]
                    print(f"🔍 MyAI audio files in temp dir: {myai_files}")
                except Exception as e:
                    print(f"🔍 Could not list temp directory: {e}")
                return ""

            file_size = audio_path.stat().st_size
            if file_size == 0:
                print("❌ Audio file is empty")
                return ""

            print(f"📁 Transcribing audio file: {audio_path} ({file_size} bytes)")
            time.sleep(0.2)

            if not audio_path.exists():
                print("❌ Audio file disappeared before transcription!")
                return ""

            try:
                with audio_path.open("rb") as test_file:
                    first_bytes = test_file.read(10)
                    print(f"✅ File is accessible, first 10 bytes: {first_bytes}")
            except Exception as access_error:
                print(f"❌ File access test failed: {access_error}")
                return ""

            print("🔄 Starting Whisper transcription (English)...")
            audio_data = self.load_audio_data(audio_path)

            if self.stt.using_faster_whisper:
                segments, info = self.stt.model.transcribe(
                    audio_data,
                    language="en",
                    initial_prompt=self.stt.vocabulary_hints,
                    vad_filter=True,
                    vad_parameters=dict(min_silence_duration_ms=500),
                )
                transcribed_text = " ".join(str(getattr(segment, "text", segment)) for segment in segments).strip()
            else:
                result = self.stt.model.transcribe(audio_data, language="en", initial_prompt=self.stt.vocabulary_hints)
                if isinstance(result, dict):
                    transcribed_text = str(result.get("text", "")).strip()
                else:
                    transcribed_text = str(result).strip()

            if not transcribed_text:
                print("⚠️ Empty transcription result - checking audio quality...")
                print(f"📊 Audio length: {len(audio_data)/16000:.2f} seconds")
                print(f"📊 Audio volume (max): {np.max(np.abs(audio_data)):.4f}")
                print(f"📊 Audio volume (RMS): {np.sqrt(np.mean(audio_data**2)):.4f}")

                if np.max(np.abs(audio_data)) < 0.01:
                    print("🔊 Audio seems very quiet, trying to amplify...")
                    amplified_audio = audio_data * 10
                    amplified_audio = np.clip(amplified_audio, -1.0, 1.0)

                    if self.stt.using_faster_whisper:
                        segments, info = self.stt.model.transcribe(
                            amplified_audio,
                            language="en",
                            initial_prompt=self.stt.vocabulary_hints,
                        )
                        transcribed_text = " ".join(str(getattr(segment, "text", segment)) for segment in segments).strip()
                    else:
                        result = self.stt.model.transcribe(
                            amplified_audio,
                            language="en",
                            initial_prompt=self.stt.vocabulary_hints,
                        )
                        if isinstance(result, dict):
                            transcribed_text = str(result.get("text", "")).strip()
                        else:
                            transcribed_text = str(result).strip()

                    if transcribed_text:
                        print("✅ Amplification helped!")
                    else:
                        print("❌ Still no speech detected after amplification")

            print(f"✅ Transcription completed: '{transcribed_text}'")

            if self.stt.is_hallucination(transcribed_text):
                print("⚠️ Transcription appears to be a hallucination, discarding...")
                transcribed_text = ""

        except Exception as e:
            print(f"❌ Transcription error: {e}")
            print(f"❌ Error type: {type(e).__name__}")
            import traceback

            print(f"❌ Full traceback: {traceback.format_exc()}")

        finally:
            cleanup_attempts = 3
            for attempt in range(cleanup_attempts):
                try:
                    if audio_path.exists():
                        time.sleep(0.1)
                        audio_path.unlink()
                        print(f"🗑️ Cleaned up temporary file (attempt {attempt + 1})")
                        break
                except Exception as cleanup_error:
                    if attempt == cleanup_attempts - 1:
                        print(f"⚠️ Could not clean up temporary file: {cleanup_error}")
                    else:
                        time.sleep(0.2)

        return transcribed_text
