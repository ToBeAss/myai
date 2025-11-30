"""
Pipeline Benchmarking System

Measures end-to-end performance of the AI voice assistant pipeline with focus on
Time to First Sound (TTFS) - the most critical metric for perceived responsiveness.

Components measured:
1. Speech-to-Text (STT) - chunked and non-chunked approaches
2. LLM Generation - Time to First Token (TTFT) and streaming
3. Text-to-Speech (TTS) - Time to First Audio (TTFA) and chunking
4. Overall latency and bottleneck identification

Usage:
    python scripts/benchmark_pipeline.py tests/audio/short_weather.wav
    python scripts/benchmark_pipeline.py tests/audio/short_weather.wav --save
    python scripts/benchmark_pipeline.py tests/audio/*.wav --save
"""

import time
import json
import wave
import numpy as np
import csv
import argparse
import sys
from pathlib import Path
from contextlib import contextmanager
from typing import Dict, List, Any, Tuple, Generator
from datetime import datetime
import webrtcvad
import tempfile
import os

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if SRC_PATH.exists():
    sys.path.insert(0, str(SRC_PATH))

# Import pipeline components
from myai.stt.speech_to_text import SpeechToText
from myai.tts.text_to_speech import TextToSpeech
from myai.llm.llm_wrapper import LLM_Wrapper
from myai.llm.agent import Agent
from myai.llm.memory import Memory
from myai.paths import data_file


@contextmanager
def timer(label: str, timings: dict):
    """
    Precise timing context manager.
    
    :param label: Name for this timing measurement
    :param timings: Dictionary to store timing results
    """
    start = time.perf_counter()
    yield
    elapsed = time.perf_counter() - start
    timings[label] = elapsed


class PipelineBenchmark:
    """
    Complete pipeline benchmarking system.
    
    Measures every component from user speech to AI audio playback,
    with focus on Time to First Sound as the primary UX metric.
    """
    
    def __init__(self, test_audio_file: str, save_results: bool = False):
        """
        Initialize benchmark with test audio.
        
        :param test_audio_file: Path to recorded test audio
        :param save_results: Whether to save results to CSV
        """
        self.audio_file = test_audio_file
        self.save_results = save_results
        self.results = {}
        
        print("\n🔧 Initializing pipeline components...")
        
        # Import prompt loader to get Sam's actual configuration
        from myai.llm.prompt_loader import load_prompts
        prompts = load_prompts()
        
        # Initialize components (EXACT same as production main_continuous.py)
        self.stt = SpeechToText(
            model_size="base",
            use_faster_whisper=True,
            track_metrics=False
        )
        
        self.tts = TextToSpeech(
            voice_name="en-GB-Chirp3-HD-Achernar",
            language_code="en-GB",
            speaking_rate=1.1,
            pitch=0.0
        )
        
        # Use exact same model as production
        self.llm = LLM_Wrapper(model_name="openai-gpt-4.1-mini")
        self.memory = Memory(history_limit=10)
        self.agent = Agent(
            llm=self.llm,
            memory=self.memory,
            agent_name=prompts['name'],
            description=prompts['description']
        )
        
        # Load Sam's actual personality instructions from prompts file
        for instruction in prompts['instructions']:
            self.agent.add_instruction(instruction)
        
        print("✅ Components initialized\n")
    
    def load_audio_file(self, filepath: str) -> Tuple[np.ndarray, int]:
        """
        Load WAV audio file.
        
        :param filepath: Path to WAV file
        :return: (audio_data as float32, sample_rate)
        """
        with wave.open(filepath, 'rb') as wf:
            sample_rate = wf.getframerate()
            n_frames = wf.getnframes()
            audio_bytes = wf.readframes(n_frames)
            
            # Convert to numpy array
            audio_int16 = np.frombuffer(audio_bytes, dtype=np.int16)
            audio_float32 = audio_int16.astype(np.float32) / 32767.0
            
            return audio_float32, sample_rate
    
    def detect_natural_chunks(self, audio_data: np.ndarray, sample_rate: int) -> List[Tuple[float, float]]:
        """
        Detect where audio WOULD chunk during live recording.
        
        MATCHES PRODUCTION BEHAVIOR:
        - Strips silence BEFORE speech starts (recording doesn't start until speech detected)
        - Splits on 300ms silence DURING speech
        - Strips silence AFTER speech ends (last chunk with only silence is discarded)
        
        :param audio_data: Audio as float32 numpy array
        :param sample_rate: Sample rate (should be 16000 Hz)
        :return: List of (start_time, end_time) tuples in seconds
        """
        vad = webrtcvad.Vad(2)  # Aggressiveness level 2 (match production setting)
        
        # VAD requires 10, 20, or 30ms frames at 8/16/32/48kHz
        frame_duration_ms = 30
        frame_duration_sec = frame_duration_ms / 1000.0
        frame_length = int(sample_rate * frame_duration_sec)
        
        # 300ms = 10 frames of 30ms (SHORT_PAUSE_MS in production)
        SHORT_PAUSE_FRAMES = 10
        # 1000ms = 33 frames of 30ms (LONG_PAUSE_MS in production)
        LONG_PAUSE_FRAMES = 33
        
        chunks = []
        speech_start = None
        current_chunk_start = None
        silence_count = 0
        in_speech = False
        
        # Process audio in frames
        i = 0
        while i < len(audio_data):
            frame = audio_data[i:i+frame_length]
            
            if len(frame) < frame_length:
                break  # Skip incomplete final frame
            
            # Convert float32 to int16 for VAD
            frame_int16 = (frame * 32767).astype(np.int16)
            frame_bytes = frame_int16.tobytes()
            
            current_time = i / sample_rate
            
            try:
                # Check volume first (matches production: volume > 300)
                volume = np.sqrt(np.mean(frame_int16.astype(np.float32)**2))
                
                # Check if frame contains speech (using both volume and VAD)
                is_speech = False
                if volume > 300:  # Volume threshold from production
                    try:
                        is_speech = vad.is_speech(frame_bytes, sample_rate)
                    except:
                        # If VAD fails, use volume threshold only
                        is_speech = True
                
                if is_speech:
                    # Speech detected - reset silence counter
                    if in_speech and silence_count >= SHORT_PAUSE_FRAMES and current_chunk_start is None:
                        # Speech resuming after a 300ms+ pause - start new chunk
                        current_chunk_start = current_time
                    
                    silence_count = 0
                    
                    if not in_speech:
                        # First speech detected - this is where recording would start
                        in_speech = True
                        if speech_start is None:
                            speech_start = current_time
                        current_chunk_start = current_time
                        
                else:
                    # Silence detected
                    if in_speech:
                        silence_count += 1
                        
                        # If silence exceeds 300ms, create chunk boundary
                        if silence_count >= SHORT_PAUSE_FRAMES and current_chunk_start is not None:
                            # End current chunk at start of silence
                            chunk_end = current_time - (silence_count * frame_duration_sec)
                            if chunk_end > current_chunk_start:
                                chunks.append((current_chunk_start, chunk_end))
                                # Mark that we need a new chunk when speech resumes
                                current_chunk_start = None
                        
                        # If silence exceeds 1000ms, user is done speaking
                        if silence_count >= LONG_PAUSE_FRAMES:
                            in_speech = False
                            break
                            
            except Exception as e:
                # If VAD fails on a frame, just continue
                pass
            
            i += frame_length
        
        # Handle final chunk if still in speech
        if in_speech and current_chunk_start is not None:
            # Check if we have meaningful audio (not just silence)
            if silence_count < SHORT_PAUSE_FRAMES:
                chunk_end = (i / sample_rate) - (silence_count * frame_duration_sec)
                if chunk_end > current_chunk_start:
                    chunks.append((current_chunk_start, chunk_end))
            # Otherwise discard (matches production behavior - last chunk with only silence is discarded)
        
        # If no chunks detected, it means no speech was found - return empty
        # This matches production: if no speech detected, nothing happens
        return chunks
    
    def extract_chunk(self, audio_data: np.ndarray, start: float, end: float, sample_rate: int) -> np.ndarray:
        """
        Extract a chunk of audio between start and end times.
        
        :param audio_data: Full audio array
        :param start: Start time in seconds
        :param end: End time in seconds
        :param sample_rate: Sample rate
        :return: Audio chunk as float32 array
        """
        start_idx = int(start * sample_rate)
        end_idx = int(end * sample_rate)
        return audio_data[start_idx:end_idx]
    
    def simulate_tts_chunking(self, text: str) -> List[str]:
        """
        Simulate how TTS chunks text during streaming.
        
        Matches production settings:
        - chunk_on=",.!?—" (main_continuous.py line 121)
        - min_chunk_size=30 chars
        
        :param text: Full response text
        :return: List of text chunks
        """
        chunks = []
        current_chunk = ""
        
        for char in text:
            current_chunk += char
            
            # Check for chunk boundary
            if char in ",.!?—" and len(current_chunk) >= 30:
                chunks.append(current_chunk.strip())
                current_chunk = ""
        
        # Add remaining text
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks if chunks else [text]
    
    def benchmark_chunked_pipeline(self) -> Dict[str, Any]:
        """
        Benchmark with chunked transcription (production mode).
        
        This simulates live chunking by detecting natural 300ms pauses
        in the audio file using VAD.
        
        :return: Comprehensive timing results
        """
        timings = {}
        benchmark_start = time.perf_counter()
        
        print("  📂 Loading audio file...")
        with timer('audio_load', timings):
            audio_data, sample_rate = self.load_audio_file(self.audio_file)
        
        audio_duration = len(audio_data) / sample_rate
        print(f"     Duration: {audio_duration:.2f}s")
        
        print("  🔍 Detecting natural chunks (300ms pause threshold)...")
        with timer('chunk_detection', timings):
            chunks = self.detect_natural_chunks(audio_data, sample_rate)
        
        print(f"     Found {len(chunks)} chunk(s)")
        
        if not chunks:
            print("     ⚠️  No speech detected in audio file!")
            print("     This matches production behavior: recording doesn't start until speech is detected.")
            return {
                'timings': {'error': 'no_speech_detected'},
                'transcription': '',
                'response': '',
                'tts_chunks': [],
                'approach': 'chunked'
            }
        
        for i, (start, end) in enumerate(chunks):
            print(f"       Chunk {i+1}: {start:.2f}s - {end:.2f}s ({end-start:.2f}s)")
        
        # ============================================
        # PHASE 2: SPEECH-TO-TEXT (CHUNKED)
        # ============================================
        
        print("\n  🎤 Transcribing chunks...")
        chunk_timings = []
        transcriptions = []
        
        stt_start = time.perf_counter()
        
        for i, (start, end) in enumerate(chunks):
            chunk_audio = self.extract_chunk(audio_data, start, end, sample_rate)
            
            # Analyze chunk properties
            chunk_duration_sec = end - start
            chunk_samples = len(chunk_audio)
            
            # Calculate audio metrics
            rms_volume = np.sqrt(np.mean(chunk_audio**2))
            
            # Save chunk to temporary file for transcription
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                temp_file = tmp.name
            
            try:
                file_write_start = time.perf_counter()
                with wave.open(temp_file, 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(sample_rate)
                    audio_int16 = (chunk_audio * 32767).astype(np.int16)
                    wf.writeframes(audio_int16.tobytes())
                file_write_time = time.perf_counter() - file_write_start
                
                whisper_start_time = time.perf_counter()
                text = self.stt.transcribe_audio(temp_file)
                whisper_time = time.perf_counter() - whisper_start_time
                
                chunk_duration = whisper_time  # Total time for this chunk
            finally:
                # Clean up temp file
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            
            chunk_timings.append(chunk_duration)
            transcriptions.append(text)
            
            # Detailed logging
            ratio = chunk_duration / chunk_duration_sec if chunk_duration_sec > 0 else 0
            print(f"     Chunk {i+1}: {chunk_duration*1000:.0f}ms → '{text}'")
            print(f"       └─ Audio: {chunk_duration_sec:.2f}s ({chunk_samples} samples, RMS: {rms_volume:.4f})")
            print(f"       └─ Ratio: {ratio:.2f}x realtime (file write: {file_write_time*1000:.0f}ms, Whisper: {whisper_time*1000:.0f}ms)")
            
            if i == 0:
                timings['stt_first_chunk'] = chunk_duration
                print(f"       ⭐ FIRST CHUNK COMPLETE: {chunk_duration*1000:.0f}ms")
        
        timings['stt_total'] = time.perf_counter() - stt_start
        timings['stt_per_chunk'] = chunk_timings
        timings['stt_num_chunks'] = len(chunks)
        
        full_transcription = " ".join(transcriptions)
        print(f"\n  📝 Full transcription: \"{full_transcription}\"")
        
        # ============================================
        # PHASE 3: LLM GENERATION (STREAMING)
        # ============================================
        
        print("\n  🤖 Generating LLM response...")
        
        llm_start = time.perf_counter()
        response_generator = self.agent.invoke(user_input=full_transcription, is_streaming=True)
        
        tokens = []
        token_times = []
        ttft_recorded = False
        first_token_arrived = False
        
        # Force the generator to start and get first token
        try:
            for token in response_generator:
                current_time = time.perf_counter() - llm_start
                
                # Extract token content
                if hasattr(token, 'content'):
                    token_content = token.content
                else:
                    token_content = str(token)
                
                # Skip empty tokens
                if not token_content:
                    continue
                
                # Record TTFT on first real token
                if not ttft_recorded:
                    timings['llm_ttft'] = current_time
                    print(f"     ⭐ FIRST TOKEN: {current_time*1000:.0f}ms ('{token_content}')")
                    ttft_recorded = True
                    first_token_arrived = True
                
                tokens.append(token_content)
                token_times.append(current_time)
                
        except Exception as e:
            print(f"     ⚠️  Error during LLM generation: {e}")
            # If we got at least some tokens, continue
            if not tokens:
                raise
        
        # If no TTFT was recorded, something went wrong
        if not ttft_recorded:
            print(f"     ⚠️  WARNING: No tokens received from LLM!")
            timings['llm_ttft'] = 0
        
        timings['llm_total'] = time.perf_counter() - llm_start
        timings['llm_tokens'] = len(tokens)
        timings['llm_tokens_per_sec'] = len(tokens) / timings['llm_total'] if timings['llm_total'] > 0 else 0
        
        response_text = "".join(tokens)
        print(f"     Generated {len(tokens)} tokens in {timings['llm_total']*1000:.0f}ms")
        print(f"     Rate: {timings['llm_tokens_per_sec']:.1f} tokens/sec")
        print(f"  💬 Response: \"{response_text[:100]}{'...' if len(response_text) > 100 else ''}\"")
        
        # ============================================
        # PHASE 4: TEXT-TO-SPEECH (STREAMING/CHUNKED)
        # ============================================
        
        print("\n  🔊 Synthesizing speech (chunked)...")
        
        tts_chunks = []
        tts_chunk_times = []
        ttfa_recorded = False
        
        tts_start = time.perf_counter()
        
        # Simulate TTS chunking (detect where it splits on ",.!?—")
        tts_text_chunks = self.simulate_tts_chunking(response_text)
        
        for i, chunk_text in enumerate(tts_text_chunks):
            chunk_start = time.perf_counter()
            
            # Synthesize chunk
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
                temp_file = tmp.name
            
            try:
                audio_file = self.tts.synthesize_to_file(chunk_text, temp_file)
                
                chunk_duration = time.perf_counter() - chunk_start
                tts_chunk_times.append(chunk_duration)
                tts_chunks.append({
                    'text': chunk_text[:50] + ('...' if len(chunk_text) > 50 else ''),
                    'duration': chunk_duration,
                    'char_count': len(chunk_text)
                })
                
                if not ttfa_recorded:
                    timings['tts_first_audio'] = time.perf_counter() - tts_start
                    print(f"     ⭐ FIRST AUDIO READY: {timings['tts_first_audio']*1000:.0f}ms")
                    ttfa_recorded = True
                
                print(f"     Chunk {i+1}: {chunk_duration*1000:.0f}ms → \"{chunk_text[:40]}{'...' if len(chunk_text) > 40 else ''}\"")
            finally:
                # Clean up temp file
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
        
        timings['tts_total'] = time.perf_counter() - tts_start
        timings['tts_num_chunks'] = len(tts_chunks)
        timings['tts_per_chunk'] = tts_chunk_times
        
        # ============================================
        # PHASE 5: CALCULATE KEY METRICS
        # ============================================
        
        # Determine which chunk matters for TTFS
        if len(chunk_timings) == 1:
            # Single chunk: first = last
            relevant_stt_time = timings['stt_first_chunk']
            timings['stt_relevant_chunk'] = 'first (only chunk)'
        else:
            # Multiple chunks: last chunk matters (first chunks transcribe in parallel)
            # CRITICAL: Last chunk time includes the 700ms confirmation wait
            # (system waits 300ms to trigger chunk, then 700ms more to confirm done)
            relevant_stt_time = chunk_timings[-1]
            timings['stt_last_chunk'] = chunk_timings[-1]
            timings['stt_relevant_chunk'] = 'last'
        
        # Minimum wait time: 700ms confirmation after 300ms pause detection
        # (This is already included in the chunk transcription timing)
        MIN_CONFIRMATION_WAIT_MS = 700
        
        # ⭐⭐⭐ MOST IMPORTANT METRIC ⭐⭐⭐
        # TTFS = time from user stops speaking to AI starts speaking
        timings['time_to_first_sound'] = (
            relevant_stt_time +  # Last chunk (or only chunk) transcription
            timings['llm_ttft'] +
            timings['tts_first_audio']
        )
        
        # Calculate parallel processing benefit
        # WITHOUT chunking: Would wait for ALL audio to finish, then transcribe sequentially
        sequential_stt_time = sum(chunk_timings)
        timings['sequential_stt_time'] = sequential_stt_time
        timings['stt_time_saved_by_chunking'] = sequential_stt_time - relevant_stt_time
        
        # What TTFS would be WITHOUT STT chunking
        timings['ttfs_without_stt_chunking'] = (
            sequential_stt_time +
            timings['llm_ttft'] +
            timings['tts_first_audio']
        )
        
        # Calculate TTS parallel benefit
        # WITHOUT TTS chunking: Would wait for full LLM response, then synthesize first chunk
        timings['ttfs_without_tts_chunking'] = (
            relevant_stt_time +
            timings['llm_total'] +  # Full LLM response
            timings['tts_first_audio']
        )
        
        # WITHOUT any chunking at all (completely sequential)
        timings['ttfs_fully_sequential'] = (
            sequential_stt_time +
            timings['llm_total'] +
            timings['tts_first_audio']
        )
        
        timings['total_pipeline'] = (
            timings['stt_total'] +
            timings['llm_total'] +
            timings['tts_total']
        )
        
        timings['benchmark_overhead'] = time.perf_counter() - benchmark_start - timings['total_pipeline']
        timings['audio_duration'] = audio_duration
        
        return {
            'timings': timings,
            'transcription': full_transcription,
            'response': response_text,
            'tts_chunks': tts_chunks,
            'approach': 'chunked'
        }
    
    def analyze_bottlenecks(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Identify which component is the bottleneck.
        
        :param results: Benchmark results
        :return: Bottleneck analysis
        """
        timings = results['timings']
        
        components = {
            'STT': timings['stt_total'],
            'LLM': timings['llm_total'],
            'TTS': timings['tts_total']
        }
        
        total_time = timings['total_pipeline']
        
        # Calculate percentages
        percentages = {
            name: (time_val / total_time * 100) if total_time > 0 else 0
            for name, time_val in components.items()
        }
        
        # Find bottleneck
        bottleneck_component = max(percentages.items(), key=lambda x: x[1])
        
        return {
            'components': components,
            'percentages': percentages,
            'bottleneck': bottleneck_component[0],
            'bottleneck_percentage': bottleneck_component[1]
        }
    
    def print_summary(self, results: Dict[str, Any]):
        """
        Print formatted summary with key metrics.
        
        :param results: Benchmark results
        """
        timings = results['timings']
        analysis = self.analyze_bottlenecks(results)
        
        print("\n" + "="*80)
        print("⭐ KEY METRICS ⭐")
        print("="*80)
        
        # Time to First Sound - THE most important metric
        ttfs = timings['time_to_first_sound'] * 1000
        
        if ttfs < 300:
            ttfs_rating = "🎉 EXCEPTIONAL"
        elif ttfs < 500:
            ttfs_rating = "✅ EXCELLENT"
        elif ttfs < 800:
            ttfs_rating = "👍 GREAT"
        elif ttfs < 1200:
            ttfs_rating = "✓ GOOD"
        else:
            ttfs_rating = "⚠️  NEEDS OPTIMIZATION"
        
        print(f"\n🎯 TIME TO FIRST SOUND: {ttfs:.0f}ms  {ttfs_rating}")
        print(f"   (Time from user stops speaking to AI starts speaking)")
        
        # Show which chunk matters
        if timings['stt_num_chunks'] == 1:
            stt_component = timings['stt_first_chunk']
            print(f"\n   📊 TTFS Breakdown (single chunk):")
        else:
            stt_component = timings.get('stt_last_chunk', timings['stt_first_chunk'])
            print(f"\n   📊 TTFS Breakdown (using last chunk - others transcribed in parallel):")
        
        stt_pct = (stt_component/timings['time_to_first_sound']*100)
        llm_pct = (timings['llm_ttft']/timings['time_to_first_sound']*100)
        tts_pct = (timings['tts_first_audio']/timings['time_to_first_sound']*100)
        
        print(f"   ├─ STT ({timings['stt_relevant_chunk']}):  {stt_component*1000:.0f}ms  ({stt_pct:.0f}%)")
        print(f"   ├─ LLM First Token:  {timings['llm_ttft']*1000:.0f}ms  ({llm_pct:.0f}%)")
        print(f"   └─ TTS First Audio:  {timings['tts_first_audio']*1000:.0f}ms  ({tts_pct:.0f}%)")
        
        # Show STT chunk details
        if timings['stt_num_chunks'] > 1:
            print(f"\n   🔍 STT Chunk Timings (all {timings['stt_num_chunks']} chunks):")
            for i, chunk_time in enumerate(timings['stt_per_chunk'], 1):
                status = " ⭐ (used for TTFS)" if i == len(timings['stt_per_chunk']) else " (parallel)"
                print(f"      Chunk {i}: {chunk_time*1000:.0f}ms{status}")
        
        # Parallel processing benefits
        print(f"\n💰 PARALLEL PROCESSING BENEFITS:")
        
        # STT chunking benefit
        stt_time_saved = timings['stt_time_saved_by_chunking'] * 1000
        if stt_time_saved > 0:
            print(f"   ✅ STT Chunking saved: {stt_time_saved:.0f}ms")
            print(f"      └─ Without chunking: {timings['sequential_stt_time']*1000:.0f}ms (all chunks sequential)")
            print(f"      └─ With chunking:    {stt_component*1000:.0f}ms (only last chunk waits)")
        else:
            print(f"   ℹ️  Single chunk - no STT parallelization opportunity")
        
        # TTS chunking benefit (LLM streaming)
        llm_time_saved = (timings['llm_total'] - timings['llm_ttft']) * 1000
        if llm_time_saved > 0:
            print(f"   ✅ TTS Streaming saved: {llm_time_saved:.0f}ms")
            print(f"      └─ LLM continued generating while TTS synthesized first chunk")
        
        # Overall comparison
        ttfs_no_chunking = timings['ttfs_without_stt_chunking'] * 1000
        ttfs_fully_sequential = timings['ttfs_fully_sequential'] * 1000
        total_saved = ttfs_fully_sequential - ttfs
        
        print(f"\n   📊 TTFS Comparison:")
        print(f"      • Current (with chunking):        {ttfs:.0f}ms  ⭐")
        if stt_time_saved > 0:
            print(f"      • Without STT chunking:           {ttfs_no_chunking:.0f}ms  (+{ttfs_no_chunking-ttfs:.0f}ms)")
        print(f"      • Without TTS streaming:          {timings['ttfs_without_tts_chunking']*1000:.0f}ms  (+{timings['ttfs_without_tts_chunking']*1000-ttfs:.0f}ms)")
        print(f"      • Fully sequential (no chunking): {ttfs_fully_sequential:.0f}ms  (+{total_saved:.0f}ms)")
        
        if total_saved > 0:
            print(f"\n   🎉 Total time saved by parallelization: {total_saved:.0f}ms ({total_saved/1000:.1f}s)")
        
        print(f"\n📊 COMPONENT BREAKDOWN (total time, not TTFS):")
        print(f"   STT Total:            {timings['stt_total']*1000:.0f}ms  ({analysis['percentages']['STT']:.1f}%)")
        print(f"   LLM Total:           {timings['llm_total']*1000:.0f}ms  ({analysis['percentages']['LLM']:.1f}%)")
        print(f"   TTS Total:            {timings['tts_total']*1000:.0f}ms  ({analysis['percentages']['TTS']:.1f}%)")
        print(f"   {'─'*29}")
        print(f"   Total Pipeline:      {timings['total_pipeline']*1000:.0f}ms")
        
        if analysis['bottleneck_percentage'] > 50:
            print(f"\n⚠️  BOTTLENECK: {analysis['bottleneck']} ({analysis['bottleneck_percentage']:.1f}% of total time)")
        
        print(f"\n📈 ADDITIONAL STATS:")
        print(f"   Audio Duration:       {timings['audio_duration']:.2f}s")
        print(f"   STT Chunks:           {timings['stt_num_chunks']}")
        print(f"   LLM Tokens:           {timings['llm_tokens']} ({timings['llm_tokens_per_sec']:.1f} tokens/sec)")
        print(f"   TTS Chunks:           {timings['tts_num_chunks']}")
        
        print("="*80)
    
    def save_to_csv(self, results: Dict[str, Any]):
        """
        Save results to CSV for historical tracking.
        
        :param results: Benchmark results
        """
        csv_path = data_file('benchmark_results.csv')
        file_exists = csv_path.exists()
        
        timings = results['timings']
        analysis = self.analyze_bottlenecks(results)
        
        # Prepare row
        row = {
            'timestamp': datetime.now().isoformat(),
            'test_name': Path(self.audio_file).stem,
            'approach': results['approach'],
            'audio_duration': timings['audio_duration'],
            'stt_first_chunk': timings['stt_first_chunk'],
            'stt_total': timings['stt_total'],
            'stt_num_chunks': timings['stt_num_chunks'],
            'llm_ttft': timings['llm_ttft'],
            'llm_total': timings['llm_total'],
            'llm_tokens': timings['llm_tokens'],
            'llm_tokens_per_sec': timings['llm_tokens_per_sec'],
            'tts_first_audio': timings['tts_first_audio'],
            'tts_total': timings['tts_total'],
            'tts_num_chunks': timings['tts_num_chunks'],
            'time_to_first_sound': timings['time_to_first_sound'],
            'total_pipeline': timings['total_pipeline'],
            'bottleneck_component': analysis['bottleneck'],
            'bottleneck_percentage': analysis['bottleneck_percentage'],
        }
        
        # Write to CSV
        with open(csv_path, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=row.keys())
            
            if not file_exists:
                writer.writeheader()
            
            writer.writerow(row)
        
        print(f"\n💾 Results saved to: {csv_path}")
    
    def run_full_benchmark(self) -> Dict[str, Any]:
        """
        Run complete benchmark suite.
        
        :return: Comprehensive timing data for analysis
        """
        print("\n" + "="*70)
        print(f"🔬 PIPELINE BENCHMARK: {Path(self.audio_file).name}")
        print("="*70)
        
        print("\n📦 Benchmarking CHUNKED transcription...")
        chunked_results = self.benchmark_chunked_pipeline()
        
        # Analysis and output
        self.print_summary(chunked_results)
        
        # Save if requested
        if self.save_results:
            self.save_to_csv(chunked_results)
        
        return chunked_results


def main():
    """Main entry point for benchmark script."""
    parser = argparse.ArgumentParser(
        description='Benchmark AI voice assistant pipeline performance'
    )
    parser.add_argument(
        'audio_file',
        help='Path to test audio file (WAV format)'
    )
    parser.add_argument(
        '--save',
        action='store_true',
    help='Save results to data/benchmark_results.csv'
    )
    
    args = parser.parse_args()
    
    # Validate audio file exists
    if not Path(args.audio_file).exists():
        print(f"❌ Error: Audio file not found: {args.audio_file}")
        print("\nTo record test audio, run: python record_benchmark_audio.py")
        return
    
    # Run benchmark
    benchmark = PipelineBenchmark(args.audio_file, save_results=args.save)
    results = benchmark.run_full_benchmark()
    
    print("\n✅ Benchmark complete!")


if __name__ == "__main__":
    main()
