# Voice Interaction Pipeline - Visual Flow Diagram

## Current System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           USER SPEAKS                                        │
│                  "Hey Sam, what's the weather like?"                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 1: CONTINUOUS AUDIO MONITORING (main thread)                         │
├─────────────────────────────────────────────────────────────────────────────┤
│  • PyAudio stream captures 25ms chunks @ 16kHz                              │
│  • Volume calculation (RMS of audio chunk)                                  │
│  • Circular buffer maintains last 250ms (pre-speech context)                │
│                                                                              │
│  While True:                                                                 │
│    ├─ Read 25ms audio chunk                                                 │
│    ├─ Calculate volume (RMS)                                                │
│    ├─ Add to circular buffer                                                │
│    └─ Continue to STAGE 2 if volume > threshold                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                           volume > silence_threshold?
                                    │
                                    ▼ YES
┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 2: VAD (Voice Activity Detection) VERIFICATION                       │
├─────────────────────────────────────────────────────────────────────────────┤
│  • WebRTC VAD analyzes audio chunk                                          │
│  • Distinguishes speech from non-speech (door slams, keyboard, etc.)        │
│  • Requires 3 consecutive speech frames (~75ms) for confirmation            │
│                                                                              │
│  vad_speech_frames counter:                                                 │
│    ├─ If VAD confirms speech: increment counter                             │
│    ├─ If VAD says not speech: reset counter to 0                            │
│    └─ If counter >= 3: SPEECH CONFIRMED, go to STAGE 3                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                      vad_speech_frames >= 3?
                                    │
                                    ▼ YES
┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 3: ACTIVE RECORDING                                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│  🎤 Speech detected, recording...                                           │
│                                                                              │
│  speech_frames = [pre_speech_buffer + new_chunks]                           │
│  silence_count = 0                                                           │
│                                                                              │
│  While recording:                                                            │
│    ├─ If volume > threshold:                                                │
│    │   ├─ Add chunk to speech_frames                                        │
│    │   └─ Reset silence_count = 0                                           │
│    │                                                                         │
│    └─ If volume < threshold:                                                │
│        ├─ Increment silence_count                                           │
│        ├─ Still add chunk (may be speech pause)                             │
│        └─ If silence_count > 60 (1.5s): STOP RECORDING → STAGE 4            │
│                                                                              │
│  Safety: Max recording duration = 15 seconds                                │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                        silence_count > 60?
                                    │
                                    ▼ YES
┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 4: TRANSCRIPTION (main thread)                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│  🔄 Processing speech...                                                    │
│                                                                              │
│  1. Write speech_frames → temp WAV file                                     │
│  2. Load audio data as numpy array                                          │
│  3. Resample to 16kHz if needed                                             │
│  4. Run Whisper transcription (English only)                                │
│  5. Check for hallucinations (Whisper noise artifacts)                      │
│  6. Parse transcription                                                      │
│                                                                              │
│  Timing: ~500ms - 2000ms (depends on audio length)                          │
│                                                                              │
│  Output: "sam what's the weather like"                                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 5: WAKE WORD DETECTION & CONFIDENCE SCORING                          │
├─────────────────────────────────────────────────────────────────────────────┤
│  Flexible wake word detection with confidence scoring:                      │
│                                                                              │
│  1. Find wake word position in transcription                                │
│  2. Extract command after wake word: "what's the weather like"              │
│  3. Calculate confidence score (0-100):                                     │
│     ├─ Position-based (0-25 pts): Earlier = higher score                    │
│     ├─ Intent signals (20 pts): Questions, commands                         │
│     ├─ Grammar analysis (20 pts): Conversational vs narrative               │
│     ├─ Wake word usage (10 pts): Single mention = good                      │
│     └─ Sentence structure (10 pts): Proper sentences                        │
│                                                                              │
│  4. Compare to threshold (default: 55)                                      │
│     ├─ >= 55: ACCEPT → Continue to STAGE 6                                  │
│     └─ < 55: REJECT → Return to STAGE 1 (false positive)                    │
│                                                                              │
│  Output: "what's the weather like" (confidence: 87)                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                        confidence >= threshold?
                                    │
                                    ▼ YES
┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 6: LLM PROCESSING (streaming)                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  Agent.stream(user_input="what's the weather like")                         │
│                                                                              │
│  1. Structure prompt:                                                        │
│     ├─ System instructions                                                  │
│     ├─ Conversation history (last N messages)                               │
│     ├─ Current query                                                         │
│     └─ Tool results (if any from previous iterations)                       │
│                                                                              │
│  2. Send to OpenAI/Azure API                                                │
│     Network latency: ~100-300ms                                             │
│                                                                              │
│  3. Stream tokens as they arrive:                                           │
│     Time to first token: ~200-600ms                                         │
│     Token rate: ~50-100 tokens/sec                                          │
│                                                                              │
│     Token stream: "I " "don't " "have " "access " "to " "real-time " ...   │
│                                                                              │
│  4. Check for tool calls:                                                   │
│     If tool_calls present: Execute tools, iterate again                     │
│     If no tool_calls: Continue streaming to STAGE 7                         │
│                                                                              │
│  ├──────────────────────────┐                                               │
│  │ PARALLEL: Continue to    │                                               │
│  │ STAGE 7 while streaming  │                                               │
│  └──────────────────────────┘                                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                            First token arrives
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 7: TTS CHUNKING & SYNTHESIS (parallel threads)                       │
├─────────────────────────────────────────────────────────────────────────────┤
│  tts.speak_streaming_async(response_generator)                              │
│                                                                              │
│  ┌─────────────────────────┐  ┌──────────────────────┐  ┌─────────────────┐│
│  │  MAIN THREAD            │  │ SYNTHESIS THREAD     │  │ PLAYBACK THREAD ││
│  │  (Token Buffering)      │  │ (Google TTS API)     │  │ (pygame mixer)  ││
│  └─────────────────────────┘  └──────────────────────┘  └─────────────────┘│
│             │                            │                        │          │
│             ▼                            │                        │          │
│  Accumulate tokens in buffer            │                        │          │
│  "I don't have access..."               │                        │          │
│             │                            │                        │          │
│  Check for sentence boundary            │                        │          │
│  (., , ; ?) AND min 15 chars            │                        │          │
│             │                            │                        │          │
│  Found: "I don't have access."          │                        │          │
│             │                            │                        │          │
│             ├───────────────────────────>│                        │          │
│             │  Queue for synthesis       │                        │          │
│             │                            ▼                        │          │
│  Continue buffering more tokens   Synthesize via Google TTS      │          │
│  "However, I can help..."         (~200-500ms per sentence)      │          │
│             │                            │                        │          │
│             ▼                            ▼                        │          │
│  Found: "However, I can..."       Create temp MP3 file           │          │
│             │                            │                        │          │
│             ├───────────────────────────>├───────────────────────>│          │
│             │  Queue for synthesis       │  Queue for playback   │          │
│             │                            │                        ▼          │
│  Continue...                      Continue...              Play audio       │
│             │                            │                 Wait for finish  │
│             ▼                            ▼                        │          │
│             ·                            ·                        ▼          │
│             ·                            ·                   Cleanup temp    │
│             ·                            ·                   Next audio      │
│                                                                              │
│  3 PARALLEL PROCESSES:                                                      │
│  1. Token buffering (main)    - Continues until LLM done                    │
│  2. TTS synthesis (thread 1)  - Processes queued sentences                  │
│  3. Audio playback (thread 2) - Plays synthesized audio                     │
│                                                                              │
│  KEY BENEFIT: First audio can start playing WHILE LLM still generating      │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                    All tokens processed & audio played
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 8: CONVERSATION MODE                                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│  💬 Conversation mode active - 5s for follow-up questions                   │
│                                                                              │
│  Start conversation timer thread:                                            │
│    ├─ Timer = 5.0 seconds                                                   │
│    ├─ If new speech detected: Pause timer                                   │
│    ├─ After speech processed: Restart timer                                 │
│    └─ If timeout: Exit conversation mode                                    │
│                                                                              │
│  In conversation mode:                                                       │
│    • NO wake word required                                                  │
│    • Any speech → directly to STAGE 6 (LLM)                                 │
│    • Allows natural back-and-forth dialogue                                 │
│                                                                              │
│  If timeout expires without speech:                                         │
│    → Exit conversation mode                                                  │
│    → Return to STAGE 1 (wake word detection)                                │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Parallel Processing Visualization

```
TIME AXIS (milliseconds) ───────────────────────────────────────────────────>

0ms                    Speech Detection Begins
├─────────────────────>
75ms                   VAD Confirms Speech (3 frames)
├─────────────────────>
2000ms                 User Stops Speaking (1.5s silence begins)
├─────────────────────>
3500ms                 Recording Stops (silence threshold reached)
├─────────────────────>
                       Transcription Begins
├─────────────────────>
4500ms                 Transcription Complete ("sam what's the weather like")
├─────────────────────>
                       Wake Word Detection (87% confidence)
├─────────────────────>
                       LLM Request Sent
├─────────────────────>
5000ms                 First LLM Token Arrives ("I")
├─────────────────────>
5200ms                 More tokens: "I don't have access"
├─────────────────────>
5700ms                 First sentence complete: "I don't have access."
                       ┌───────────────────────────────────────────────┐
                       │ TTS SYNTHESIS STARTS (parallel thread)        │
                       │ Synthesizing: "I don't have access."          │
├─────────────────────>├──────────────────────────────────────────────>
6000ms                 Second sentence: "However, I can help..."       │
                       │                                               │
                       │ TTS SYNTHESIS CONTINUES (200-500ms)           │
├─────────────────────>├──────────────────────────────────────────────>
6200ms                 More LLM tokens arriving...                     │
                       │                                               ▼
6400ms                 │                              FIRST AUDIO STARTS PLAYING!
                       │                              ┌───────────────────────┐
├─────────────────────>├──────────────────────────────┤ Playback thread       │
6700ms                 Third sentence ready...        │ Playing: "I don't..." │
                       │                              │                       │
                       │ Second synthesis starts      │                       │
                       │ "However, I can help..."     │                       │
├─────────────────────>├──────────────────────────────┤──────────────────────>
7000ms                 More tokens...                 │                       │
                       │                              │ Audio continues...    │
├─────────────────────>├──────────────────────────────┤──────────────────────>
7500ms                 │                              ▼ First audio done      │
                       │                              Queue next audio...     │
├─────────────────────>├─────────────────────────────────────────────────────>
8000ms                 LLM stream complete            Second audio plays...
                       ▼
                       Final sentence synthesis
├─────────────────────>
10000ms                All synthesis complete
                       ├─────────────────────────────>
                       All audio playback complete
                       ▼
                       Conversation mode activated (5s timer)


KEY OBSERVATIONS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ PARALLEL PROCESSING PROOF:
   • First audio starts at 6400ms
   • LLM still generating tokens until 8000ms
   • 1600ms of overlap = 1.6 seconds saved!

⚠️  POTENTIAL PERCEPTION ISSUE:
   • User speaks at 0ms
   • First audio at 6400ms
   • Feels like 6.4 seconds delay
   • Parallel processing is working, but cumulative latency is high

💡 WHY IT MIGHT NOT "FEEL" PARALLEL:
   1. Long transcription phase (1000ms)
   2. LLM first token delay (500-700ms)
   3. Buffer accumulation time (700ms to first sentence)
   4. TTS synthesis time (400ms)
   → Total: ~3s from recording stop to audio start
```

## Bottleneck Analysis

```
┌─────────────────────────────────────────────────────────────────┐
│ PHASE                   │ DURATION  │ % OF TOTAL │ OPTIMIZATION │
├─────────────────────────┼───────────┼────────────┼──────────────┤
│ Speech Detection        │   75ms    │    1.2%    │    LOW       │
│ User Speaking           │  2000ms   │   31.3%    │   N/A        │
│ Silence Detection       │  1500ms   │   23.4%    │   HIGH ⚠️    │
│ Transcription           │  1000ms   │   15.6%    │   HIGH ⚠️    │
│ Wake Word Analysis      │   20ms    │    0.3%    │    LOW       │
│ LLM First Token         │   500ms   │    7.8%    │   MEDIUM     │
│ Buffer to Sentence      │   700ms   │   10.9%    │   HIGH ⚠️    │
│ TTS Synthesis           │   400ms   │    6.3%    │   MEDIUM     │
│ Playback Start          │   100ms   │    1.6%    │    LOW       │
├─────────────────────────┼───────────┼────────────┼──────────────┤
│ TOTAL (to first audio)  │  6395ms   │   100%     │              │
└─────────────────────────────────────────────────────────────────┘

HIGH PRIORITY TARGETS:
⚠️  Silence Detection (1500ms → 1000ms): Save 500ms
⚠️  Transcription (1000ms → 500ms): Save 500ms  
⚠️  Buffer to Sentence (700ms → 400ms): Save 300ms

Total potential saving: ~1300ms (20% improvement)
```

## Data Flow Diagram

```
┌─────────┐       ┌──────────┐       ┌─────────┐       ┌──────┐
│ Microphone─────>│ PyAudio  ├──────>│ VAD     ├──────>│ WAV  │
└─────────┘       └──────────┘       └─────────┘       └──────┘
                                                            │
                                                            ▼
                                                       ┌────────┐
                                                       │ Whisper│
                                                       └────────┘
                                                            │
                                                            ▼
                                                  ┌──────────────────┐
                                                  │ Wake Word Scorer │
                                                  └──────────────────┘
                                                            │
                                                            ▼
┌─────────┐       ┌──────────┐       ┌─────────┐       ┌──────┐
│ Speakers│<──────┤ pygame   │<──────┤Google TTS<──────┤ LLM  │
└─────────┘       └──────────┘       └─────────┘       └──────┘
   ▲                   ▲                   ▲                │
   │                   │                   │                │
   └───────────────────┴───────────────────┴────────────────┘
              PARALLEL PROCESSING PIPELINE
```

This visualization shows exactly where time is spent and where parallel processing helps!
