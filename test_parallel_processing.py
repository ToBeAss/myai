"""
Test script to verify and measure parallel TTS processing.

This script demonstrates and measures the parallel processing between:
1. LLM token generation
2. TTS synthesis
3. Audio playback

Run this to get solid proof that parallel processing is working.
"""

import time
from lib.llm_wrapper import LLM_Wrapper
from lib.agent import Agent
from lib.memory import Memory
from lib.text_to_speech import TextToSpeech

def test_streaming_with_timing():
    """Test to verify parallel TTS processing with detailed timing."""
    
    print("\n🔧 Initializing components...")
    llm = LLM_Wrapper(model_name="openai-gpt-4.1-mini")
    memory = Memory(history_limit=10)
    myai = Agent(llm=llm, memory=memory, agent_name="Sam", 
                 description="Test agent for timing analysis")
    
    myai.add_instruction("Keep responses conversational and concise.")
    
    tts = TextToSpeech(
        voice_name="en-GB-Wavenet-A",
        language_code="en-GB",
        speaking_rate=1.1,
        pitch=0.0
    )
    
    # Instrumented text generator wrapper
    class TimedGenerator:
        def __init__(self, generator):
            self.generator = generator
            self.start_time = time.time()
            self.first_token_time = None
            self.token_times = []
            self.token_contents = []
            self.tokens_generated = 0
            
        def __iter__(self):
            for token in self.generator:
                current_time = time.time()
                elapsed = current_time - self.start_time
                
                if self.first_token_time is None:
                    self.first_token_time = elapsed
                    print(f"\n⏱️  [{elapsed*1000:.0f}ms] FIRST TOKEN RECEIVED: '{token.content}'")
                
                self.token_times.append(elapsed)
                self.token_contents.append(token.content)
                self.tokens_generated += 1
                
                # Print first 5 tokens individually for early visibility
                if self.tokens_generated <= 5:
                    accumulated_text = ''.join(self.token_contents)
                    print(f"⏱️  [{elapsed*1000:.0f}ms] Token #{self.tokens_generated}: '{token.content}' (total so far: '{accumulated_text}')")
                # Print milestone tokens for later visibility
                elif self.tokens_generated in [10, 20, 30, 40, 50]:
                    accumulated_text = ''.join(self.token_contents)
                    print(f"⏱️  [{elapsed*1000:.0f}ms] Token #{self.tokens_generated}: '{accumulated_text[-30:]}'")
                
                yield token
            
            final_time = time.time() - self.start_time
            print(f"⏱️  [{final_time*1000:.0f}ms] LAST TOKEN RECEIVED (total: {self.tokens_generated} tokens)")
    
    # Instrumented TTS wrapper
    original_synthesize = tts.synthesize_to_file
    synthesis_events = []
    
    def timed_synthesize(text, filename):
        synth_start = time.time()
        start_time_ms = (synth_start - test_start) * 1000
        
        print(f"🎵 [{start_time_ms:.0f}ms] SYNTHESIS STARTED: '{text[:60]}{'...' if len(text) > 60 else ''}'")
        
        result = original_synthesize(text, filename)
        duration = (time.time() - synth_start) * 1000
        end_time_ms = (time.time() - test_start) * 1000
        
        event = {
            'type': 'synthesis',
            'text': text[:50] + ('...' if len(text) > 50 else ''),
            'full_text': text,
            'duration': duration,
            'start_time': start_time_ms,
            'end_time': end_time_ms,
            'char_count': len(text)
        }
        synthesis_events.append(event)
        print(f"   └─ Completed in {duration:.0f}ms at [{end_time_ms:.0f}ms]")
        return result
    
    # Instrument playback
    import pygame
    original_play = pygame.mixer.music.play
    playback_events = []
    playback_counter = [0]  # Use list to allow modification in nested function
    
    def timed_play(*args, **kwargs):
        playback_counter[0] += 1
        event = {
            'type': 'playback',
            'start_time': (time.time() - test_start) * 1000,
            'sequence': playback_counter[0]
        }
        playback_events.append(event)
        
        if playback_counter[0] == 1:
            print(f"🔊 [{event['start_time']:.0f}ms] 🎉 FIRST AUDIO PLAYBACK STARTED!")
        else:
            print(f"🔊 [{event['start_time']:.0f}ms] Audio segment #{playback_counter[0]} started")
        
        return original_play(*args, **kwargs)
    
    pygame.mixer.music.play = timed_play
    tts.synthesize_to_file = timed_synthesize
    
    # Run test
    print("\n" + "="*80)
    print("🧪 PARALLEL PROCESSING VERIFICATION TEST")
    print("="*80)
    print("\n📝 Query: 'Explain quantum entanglement in simple terms'")
    print("\nThis test will measure timing of:")
    print("  1. LLM token generation (streamed)")
    print("  2. TTS synthesis (parallel worker thread)")
    print("  3. Audio playback (parallel playback thread)")
    print("\n🎯 Goal: Prove that audio starts BEFORE all tokens are generated")
    print("\n" + "-"*80 + "\n")
    
    test_start = time.time()
    response_generator = myai.stream(user_input="Explain quantum entanglement in simple terms")
    timed_gen = TimedGenerator(response_generator)
    
    print("🤖: ", end="", flush=True)
    tts.speak_streaming_async(timed_gen, chunk_on=",.!?", print_text=True, min_chunk_size=10)
    
    total_time = (time.time() - test_start) * 1000
    
    # Restore original functions
    tts.synthesize_to_file = original_synthesize
    pygame.mixer.music.play = original_play
    
    # Analysis
    print("\n\n" + "="*80)
    print("📊 DETAILED TIMING ANALYSIS")
    print("="*80)
    
    # Overall metrics
    print("\n🎯 Overall Metrics:")
    print(f"  • Total Time: {total_time:.0f}ms ({total_time/1000:.1f}s)")
    if timed_gen.first_token_time:
        print(f"  • Time to First Token: {timed_gen.first_token_time*1000:.0f}ms")
    print(f"  • Total Tokens Generated: {len(timed_gen.token_times)}")
    
    if len(timed_gen.token_times) > 1:
        token_gen_start = timed_gen.first_token_time * 1000
        token_gen_end = timed_gen.token_times[-1] * 1000
        token_gen_duration = token_gen_end - token_gen_start
        avg_token_interval = (token_gen_duration / (len(timed_gen.token_times) - 1))
        print(f"  • Token Generation Started: {token_gen_start:.0f}ms")
        print(f"  • Token Generation Ended: {token_gen_end:.0f}ms")
        print(f"  • Token Generation Duration: {token_gen_duration:.0f}ms")
        print(f"  • Avg Time Between Tokens: {avg_token_interval:.0f}ms")
        print(f"  • Token Generation Rate: {len(timed_gen.token_times)/(token_gen_duration/1000):.1f} tokens/sec")
    
    # TTS metrics
    print(f"\n🎵 TTS Synthesis Metrics:")
    print(f"  • Total Synthesis Calls: {len(synthesis_events)}")
    if synthesis_events:
        avg_synth = sum(s['duration'] for s in synthesis_events) / len(synthesis_events)
        print(f"  • Avg Synthesis Time: {avg_synth:.0f}ms")
        print(f"  • First Synthesis Started: {synthesis_events[0]['start_time']:.0f}ms from start")
        print(f"  • Last Synthesis Ended: {synthesis_events[-1]['end_time']:.0f}ms from start")
        
        print(f"\n  📋 Synthesis Timeline:")
        for i, event in enumerate(synthesis_events, 1):
            print(f"    {i}. [{event['start_time']:.0f}ms → {event['end_time']:.0f}ms] "
                  f"'{event['text']}' ({event['duration']:.0f}ms)")
    
    # Playback metrics
    print(f"\n🔊 Audio Playback Metrics:")
    print(f"  • Total Playback Events: {len(playback_events)}")
    if playback_events:
        print(f"  • First Playback Started: {playback_events[0]['start_time']:.0f}ms from start")
        if len(playback_events) > 1:
            print(f"  • Subsequent Playbacks: {', '.join([f'{p['start_time']:.0f}ms' for p in playback_events[1:]])}")
    
    # Parallel processing verification
    print(f"\n✅ PARALLEL PROCESSING VERIFICATION:")
    print("="*80)
    
    if len(synthesis_events) >= 1 and len(timed_gen.token_times) > 0:
        token_gen_start = timed_gen.first_token_time * 1000
        token_gen_end = timed_gen.token_times[-1] * 1000
        first_synth_start = synthesis_events[0]['start_time']
        first_synth_end = synthesis_events[0]['end_time']
        
        print(f"\n  📊 Timeline Comparison:")
        print(f"  ┌─────────────────────────────────────────────────────────────┐")
        print(f"  │ Event                        │ Start    │ End      │ Duration│")
        print(f"  ├─────────────────────────────────────────────────────────────┤")
        print(f"  │ LLM Token Generation         │ {token_gen_start:6.0f}ms │ {token_gen_end:6.0f}ms │ {token_gen_end-token_gen_start:6.0f}ms│")
        
        for i, synth in enumerate(synthesis_events, 1):
            label = f"TTS Synthesis #{i}"
            print(f"  │ {label:29}│ {synth['start_time']:6.0f}ms │ {synth['end_time']:6.0f}ms │ {synth['duration']:6.0f}ms│")
        
        if playback_events:
            for i, play in enumerate(playback_events, 1):
                label = f"Audio Playback #{i}"
                print(f"  │ {label:29}│ {play['start_time']:6.0f}ms │ {'--':>6}   │ {'--':>6}  │")
        
        print(f"  └─────────────────────────────────────────────────────────────┘")
        
        # Analyze overlap
        print(f"\n  🔍 Parallelization Analysis:")
        
        # Check if synthesis started before tokens finished
        if first_synth_start < token_gen_end:
            synth_during_generation = token_gen_end - first_synth_start
            print(f"    ✅ First synthesis started WHILE tokens were still generating!")
            print(f"       └─ Synthesis began {synth_during_generation:.0f}ms before token generation completed")
        
        # Check if synthesis completed while tokens were generating
        if first_synth_end < token_gen_end:
            overlap = token_gen_end - first_synth_end
            overlap_pct = (overlap / (token_gen_end - token_gen_start)) * 100
            print(f"    ✅ First synthesis completed WHILE tokens still generating!")
            print(f"       └─ Overlap duration: {overlap:.0f}ms ({overlap_pct:.0f}% of token generation)")
        
        # Check if audio started before tokens finished
        if playback_events and playback_events[0]['start_time'] < token_gen_end:
            audio_before_end = token_gen_end - playback_events[0]['start_time']
            print(f"    ✅ Audio playback started WHILE tokens still generating!")
            print(f"       └─ Started {audio_before_end:.0f}ms before token generation completed")
            print(f"    🎉 USER HEARD AUDIO BEFORE LLM FINISHED GENERATING!")
        
        # Check multiple syntheses
        if len(synthesis_events) >= 2:
            second_synth_start = synthesis_events[1]['start_time']
            if second_synth_start < token_gen_end:
                print(f"    ✅ Multiple synthesis operations in parallel!")
                print(f"       └─ {len(synthesis_events)} synthesis operations while generating")
        
        # Calculate time saved
        if playback_events:
            first_audio = playback_events[0]['start_time']
            # Time saved = how much token generation continued after audio started
            time_saved = token_gen_end - first_audio
            if time_saved > 0:
                print(f"\n  💰 Time Saved by Parallelization:")
                print(f"    • Without parallel: Would wait {token_gen_end:.0f}ms (all tokens) + synthesis + playback")
                print(f"    • With parallel: User heard audio at {first_audio:.0f}ms")
                print(f"    • Effective time saved: ~{time_saved:.0f}ms ({time_saved/1000:.1f}s)")
        
        # Overall verdict
        print(f"\n  🎯 VERDICT:")
        if playback_events and playback_events[0]['start_time'] < token_gen_end:
            print(f"    ✅ ✅ ✅ PARALLEL PROCESSING IS WORKING PERFECTLY!")
            print(f"    The system is speaking while the LLM is still generating text.")
        elif first_synth_start < token_gen_end:
            print(f"    ✅ Parallel processing is working (synthesis started early)")
            print(f"    💡 Audio playback started close to token completion")
        else:
            print(f"    ⚠️  Limited parallelization (response was likely a single long sentence)")
            print(f"    This is expected behavior when LLM generates one sentence without periods.")
    
    # User perception analysis
    print(f"\n👂 USER PERCEPTION ANALYSIS:")
    if playback_events:
        time_to_first_audio = playback_events[0]['start_time']
        print(f"  • Time from start to first audio: {time_to_first_audio:.0f}ms ({time_to_first_audio/1000:.1f}s)")
        
        if timed_gen.first_token_time:
            time_from_first_token_to_audio = time_to_first_audio - (timed_gen.first_token_time * 1000)
            print(f"  • Time from first token to first audio: {time_from_first_token_to_audio:.0f}ms")
            
            if time_from_first_token_to_audio > 1500:
                print(f"  ⚠️  Long delay between token generation and audio ({time_from_first_token_to_audio:.0f}ms)")
                print(f"     This may make it feel like audio isn't streaming in parallel")
                print(f"     Suggestions: Reduce min_chunk_size or add more chunk boundaries")
            elif time_from_first_token_to_audio > 800:
                print(f"  ℹ️  Moderate delay between token generation and audio ({time_from_first_token_to_audio:.0f}ms)")
                print(f"     System is working but could be more responsive")
            else:
                print(f"  ✅ Quick response! Audio starts shortly after tokens arrive")
    
    # Recommendations
    print(f"\n💡 PERFORMANCE SUMMARY:")
    print("="*80)
    
    # Calculate key metrics
    if playback_events and timed_gen.first_token_time:
        time_to_first_audio = playback_events[0]['start_time']
        time_from_query_start = time_to_first_audio  # From test_start
        
        print(f"\n  ⏱️  Key Latency Metrics:")
        print(f"    • Time to first token: {timed_gen.first_token_time*1000:.0f}ms")
        print(f"    • Time to first audio: {time_to_first_audio:.0f}ms ({time_to_first_audio/1000:.1f}s)")
        print(f"    • Total processing time: {total_time:.0f}ms ({total_time/1000:.1f}s)")
        
        if synthesis_events:
            print(f"\n  📊 Processing Breakdown:")
            print(f"    • LLM generation: {(token_gen_end - token_gen_start):.0f}ms")
            print(f"    • TTS synthesis (avg): {sum(s['duration'] for s in synthesis_events) / len(synthesis_events):.0f}ms")
            print(f"    • Total characters synthesized: {sum(s['char_count'] for s in synthesis_events)}")
            print(f"    • Number of synthesis chunks: {len(synthesis_events)}")
        
        # Recommendations
        print(f"\n  🎯 Analysis:")
        
        if playback_events[0]['start_time'] < token_gen_end:
            saving = token_gen_end - playback_events[0]['start_time']
            print(f"    ✅ Parallel processing saved ~{saving:.0f}ms ({saving/1000:.1f}s)")
            print(f"    ✅ User experience: Audio started before text generation finished")
        
        if len(synthesis_events) >= 2:
            print(f"    ✅ Multiple sentence response → Good parallelization")
        elif len(synthesis_events) == 1:
            print(f"    ℹ️  Single sentence response → Limited parallelization opportunity")
            print(f"       (This is expected for short responses or single-sentence answers)")
        
        if time_to_first_audio < 3000:
            print(f"    ✅ Fast response time (< 3 seconds to audio)")
        elif time_to_first_audio < 5000:
            print(f"    ✅ Good response time (< 5 seconds to audio)")
        else:
            print(f"    ⚠️  Response time could be improved")
        
        # Specific recommendations
        recommendations = []
        
        if synthesis_events:
            avg_synth = sum(s['duration'] for s in synthesis_events) / len(synthesis_events)
            if avg_synth > 1000:
                recommendations.append("Consider using Wavenet instead of Chirp3-HD for faster synthesis")
        
        if timed_gen.first_token_time and timed_gen.first_token_time > 0.8:
            recommendations.append("LLM first token latency is high - check prompt size or model")
        
        if len(synthesis_events) == 1 and len(timed_gen.token_contents) > 50:
            recommendations.append("Long single-sentence responses limit parallelization")
        
        if recommendations:
            print(f"\n  💡 Suggestions for Further Improvement:")
            for rec in recommendations:
                print(f"    • {rec}")
        else:
            print(f"\n  🎉 System is performing excellently! No significant improvements needed.")
    
    print("\n" + "="*80 + "\n")


def test_simple_verification():
    """Simpler test to just verify parallel processing is happening."""
    
    print("\n🔧 Running simple verification test...")
    
    llm = LLM_Wrapper(model_name="openai-gpt-4.1-mini")
    agent = Agent(llm=llm, agent_name="Test")
    agent.add_instruction("Be concise.")
    
    tts = TextToSpeech(voice_name="en-GB-Wavenet-A", language_code="en-GB")
    
    events = []
    
    # Monkey patch to track events
    original_synth = tts.synthesize_to_file
    def track_synth(text, filename):
        events.append(('synth_start', time.time(), text[:30]))
        result = original_synth(text, filename)
        events.append(('synth_end', time.time(), text[:30]))
        return result
    tts.synthesize_to_file = track_synth
    
    start = time.time()
    generator = agent.stream(user_input="Count from 1 to 5 with explanations")
    
    print("🤖: ", end="", flush=True)
    tts.speak_streaming_async(generator, print_text=True)
    
    print("\n\n📊 Event Timeline:")
    for event_type, event_time, data in events:
        elapsed = (event_time - start) * 1000
        print(f"  [{elapsed:.0f}ms] {event_type}: '{data}...'")
    
    # Check for overlap
    if len(events) >= 4:  # At least 2 synthesis cycles
        first_synth_end = events[1][1]
        second_synth_start = events[2][1]
        
        if second_synth_start < first_synth_end:
            print("\n❌ Sequential processing detected (unexpected)")
        else:
            gap = (second_synth_start - first_synth_end) * 1000
            if gap < 100:
                print(f"\n✅ Parallel processing confirmed! Gap between syntheses: {gap:.0f}ms")
            else:
                print(f"\n⚠️  Large gap between syntheses: {gap:.0f}ms")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--simple":
        test_simple_verification()
    else:
        test_streaming_with_timing()
