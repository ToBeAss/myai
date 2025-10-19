#!/usr/bin/env python3
"""
Analyze speech pause patterns to optimize STT timing thresholds.

This script records your speech, uses WebRTC VAD to detect pauses,
and calculates statistics to recommend optimal SHORT_PAUSE_MS and LONG_PAUSE_MS values.

Usage:
    python scripts/analyze_speech_pauses.py
    
The script will:
1. Record 5-10 sample utterances from you
2. Detect all pauses in your speech using VAD
3. Classify pauses as "phrase boundaries" vs "end of turn"
4. Recommend optimal timing values for your speaking style
"""

import pyaudio
import wave
import numpy as np
import webrtcvad
from pathlib import Path
from collections import defaultdict
import statistics
import time

class SpeechPauseAnalyzer:
    """Analyze pause patterns in speech to optimize timing thresholds."""
    
    def __init__(self):
        self.rate = 16000
        self.chunk = 320  # 20ms frames
        self.format = pyaudio.paInt16
        self.channels = 1
        self.vad = webrtcvad.Vad(1)  # Mode 1 (moderate)
        
        # Pause detection
        self.pause_threshold_ms = 100  # Minimum pause to record
        self.pause_data = []  # List of (pause_duration_ms, is_end_of_turn)
        
    def record_utterance(self, utterance_num: int, total: int) -> list:
        """
        Record one utterance and return audio frames.
        
        :param utterance_num: Current utterance number
        :param total: Total utterances to record
        :return: List of audio frames
        """
        print(f"\n{'='*60}")
        print(f"📝 UTTERANCE {utterance_num}/{total}")
        print(f"{'='*60}")
        print("\n💡 Instructions:")
        print("   1. Press ENTER to start recording")
        print("   2. Speak naturally (multiple phrases/sentences)")
        print("   3. Press SPACE to stop when completely done")
        print("\n📋 Example utterances:")
        print("   - 'Hey Sam, what's the weather today?'")
        print("   - 'I need to schedule a meeting... hmm... for tomorrow at 3pm'")
        print("   - 'Search for Italian restaurants nearby... no wait... make that pizza places'")
        
        input("\n▶️  Press ENTER to start recording...")
        
        audio = pyaudio.PyAudio()
        stream = audio.open(
            format=self.format,
            channels=self.channels,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk
        )
        
        print("\n🎤 RECORDING... (Press SPACE to stop)")
        frames = []
        
        try:
            while True:
                data = stream.read(self.chunk, exception_on_overflow=False)
                frames.append(data)
                
                # Calculate volume for feedback
                audio_chunk = np.frombuffer(data, dtype=np.int16)
                volume = np.sqrt(np.mean(audio_chunk.astype(np.float32)**2))
                volume_bars = int(volume / 1000)
                volume_indicator = "█" * min(volume_bars, 20)
                print(f"\r🔊 [{volume_indicator:<20}] {len(frames)*20}ms", end="", flush=True)
                
                # Check for spacebar
                import keyboard
                if keyboard.is_pressed('space'):
                    print("\n⏹️  Recording stopped")
                    break
                    
        finally:
            stream.stop_stream()
            stream.close()
            audio.terminate()
        
        print(f"✅ Recorded {len(frames)*20}ms of audio\n")
        return frames
    
    def analyze_pauses(self, frames: list) -> list:
        """
        Analyze pause patterns in recorded audio.
        
        :param frames: List of audio frames
        :return: List of pause durations in milliseconds
        """
        pauses = []
        current_pause_frames = 0
        in_speech = False
        
        for frame in frames:
            is_speech = self.vad.is_speech(frame, self.rate)
            
            if is_speech:
                # End of pause
                if current_pause_frames > 0:
                    pause_ms = current_pause_frames * 20
                    if pause_ms >= self.pause_threshold_ms:
                        pauses.append(pause_ms)
                current_pause_frames = 0
                in_speech = True
            else:
                # In pause
                if in_speech:  # Only count pauses after speech started
                    current_pause_frames += 1
        
        return pauses
    
    def record_and_analyze_session(self, num_utterances: int = 5):
        """
        Record multiple utterances and analyze pause patterns.
        
        :param num_utterances: Number of utterances to record
        """
        print("\n" + "="*60)
        print("🎙️  SPEECH PAUSE PATTERN ANALYZER")
        print("="*60)
        print(f"\nℹ️  We'll record {num_utterances} utterances to analyze your speech patterns")
        print("   Each utterance should be a complete thought/command")
        print("   Speak naturally - include thinking pauses, corrections, etc.")
        
        all_pauses = []
        
        for i in range(1, num_utterances + 1):
            frames = self.record_utterance(i, num_utterances)
            pauses = self.analyze_pauses(frames)
            
            if pauses:
                print(f"📊 Detected {len(pauses)} pauses: {[f'{p}ms' for p in pauses]}")
                all_pauses.extend(pauses)
                
                # Ask user to classify the longest pause (likely end-of-turn)
                longest_pause = max(pauses)
                print(f"\n❓ The longest pause in this utterance was {longest_pause}ms")
                is_end = input("   Was this at the END of your complete thought? (y/n): ").lower().strip() == 'y'
                
                # Store all pauses with classification
                for pause in pauses:
                    is_this_end = (pause == longest_pause and is_end)
                    self.pause_data.append((pause, is_this_end))
            else:
                print("⚠️  No pauses detected (you spoke very continuously!)")
        
        self.generate_report(all_pauses)
    
    def generate_report(self, all_pauses: list):
        """
        Generate analysis report with recommendations.
        
        :param all_pauses: List of all detected pause durations
        """
        if not all_pauses:
            print("\n❌ No pauses detected. Try recording longer utterances with natural pauses.")
            return
        
        # Separate phrase pauses from end-of-turn pauses
        phrase_pauses = [p for p, is_end in self.pause_data if not is_end]
        end_pauses = [p for p, is_end in self.pause_data if is_end]
        
        print("\n" + "="*60)
        print("📊 ANALYSIS RESULTS")
        print("="*60)
        
        # Overall statistics
        print(f"\n📈 Overall Pause Statistics:")
        print(f"   Total pauses detected: {len(all_pauses)}")
        print(f"   Shortest pause: {min(all_pauses)}ms")
        print(f"   Longest pause: {max(all_pauses)}ms")
        print(f"   Average pause: {statistics.mean(all_pauses):.0f}ms")
        print(f"   Median pause: {statistics.median(all_pauses):.0f}ms")
        
        # Phrase boundary pauses
        if phrase_pauses:
            print(f"\n🔤 Phrase Boundary Pauses (within utterance):")
            print(f"   Count: {len(phrase_pauses)}")
            print(f"   Average: {statistics.mean(phrase_pauses):.0f}ms")
            print(f"   Median: {statistics.median(phrase_pauses):.0f}ms")
            print(f"   Range: {min(phrase_pauses)}-{max(phrase_pauses)}ms")
            
            # Calculate percentiles
            sorted_phrase = sorted(phrase_pauses)
            p25 = sorted_phrase[len(sorted_phrase)//4] if len(sorted_phrase) >= 4 else min(phrase_pauses)
            p75 = sorted_phrase[3*len(sorted_phrase)//4] if len(sorted_phrase) >= 4 else max(phrase_pauses)
            print(f"   25th percentile: {p25}ms")
            print(f"   75th percentile: {p75}ms")
        
        # End-of-turn pauses
        if end_pauses:
            print(f"\n🛑 End-of-Turn Pauses:")
            print(f"   Count: {len(end_pauses)}")
            print(f"   Average: {statistics.mean(end_pauses):.0f}ms")
            print(f"   Median: {statistics.median(end_pauses):.0f}ms")
            print(f"   Range: {min(end_pauses)}-{max(end_pauses)}ms")
        
        # Generate recommendations
        print("\n" + "="*60)
        print("🎯 RECOMMENDATIONS")
        print("="*60)
        
        if phrase_pauses:
            # Recommend SHORT_PAUSE based on median phrase pause
            median_phrase = statistics.median(phrase_pauses)
            
            # Safety margin: use slightly less than median to catch most pauses
            recommended_short = int(median_phrase * 0.8)  # 80% of median
            recommended_short = max(300, min(600, recommended_short))  # Clamp to reasonable range
            
            print(f"\n📍 SHORT_PAUSE_MS (chunk boundaries):")
            print(f"   Current value: 500ms")
            print(f"   Your median phrase pause: {median_phrase:.0f}ms")
            print(f"   Recommended: {recommended_short}ms")
            print(f"   Rationale: Set to 80% of your median phrase pause")
            print(f"              This creates chunks at natural boundaries")
            print(f"              Low risk - just affects chunk size, not accuracy")
        
        if end_pauses:
            # Recommend LONG_PAUSE based on minimum end pause + safety margin
            min_end = min(end_pauses)
            
            # Safety margin: add 200ms buffer to avoid cutting off
            recommended_long = int(min_end + 200)
            recommended_long = max(1200, min(2000, recommended_long))  # Clamp to reasonable range
            
            print(f"\n📍 LONG_PAUSE_MS (end of turn detection):")
            print(f"   Current value: 1500ms")
            print(f"   Your shortest end-of-turn: {min_end:.0f}ms")
            print(f"   Recommended: {recommended_long}ms")
            print(f"   Rationale: Shortest end pause + 200ms safety buffer")
            print(f"              Conservative to avoid cutting you off")
            print(f"              High risk if too short - frustrating interruptions!")
        
        # Combined recommendation
        if phrase_pauses and end_pauses:
            print(f"\n💡 SUGGESTED CONFIGURATION:")
            print(f"   In speech_to_text.py, update _process_speech_with_chunking():")
            print(f"   ")
            print(f"   SHORT_PAUSE_MS = {recommended_short}  # Chunk boundaries (low risk)")
            print(f"   LONG_PAUSE_MS = {recommended_long}   # End of turn (high risk)")
            
            # Validate recommendations make sense
            if recommended_long <= recommended_short + 500:
                print(f"\n   ⚠️  WARNING: Long pause should be significantly longer than short pause")
                print(f"      Consider increasing LONG_PAUSE_MS to at least {recommended_short + 800}ms")
        
        print("\n" + "="*60)
        print("✅ Analysis complete!")
        print("="*60)
        print("\n💡 TIP: Run this script multiple times in different contexts")
        print("   (morning, evening, tired, energized) to see how your")
        print("   speech patterns vary throughout the day.")
        print("\n📝 Consider using the SHORTEST values from multiple sessions")
        print("   to ensure the system works even when you speak fastest.")


def main():
    """Main entry point."""
    analyzer = SpeechPauseAnalyzer()
    
    print("\n" + "="*60)
    print("🎙️  Welcome to the Speech Pause Pattern Analyzer!")
    print("="*60)
    
    num_utterances = 5
    try:
        custom = input(f"\n📊 Record {num_utterances} utterances? (or enter custom number): ").strip()
        if custom.isdigit():
            num_utterances = int(custom)
    except:
        pass
    
    try:
        analyzer.record_and_analyze_session(num_utterances)
    except KeyboardInterrupt:
        print("\n\n⏹️  Analysis interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
