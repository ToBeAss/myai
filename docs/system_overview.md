# MyAI Voice Assistant Overview

This document replaces the scattered feature guides, summaries, and quick references that previously lived at the repository root. It captures the essentials of how the assistant works, how to run it, and where to look when you need the gritty details.

## Quick Start

1. Create or activate a Python 3.10+ environment and install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
2. Launch the guided CLI:
   ```powershell
   python main.py
   ```
3. Launch the continuous assistant (hands‑free wake word + TTS):
   ```powershell
   python main_continuous.py
   ```
4. Optional tooling:
   - `scripts/record_test_audio.py` / `scripts/record_benchmark_audio.py` to capture audio samples.
   - `scripts/benchmark_pipeline.py` and `scripts/compare_benchmarks.py` for performance tracking.

## Architecture at a Glance

- **Entry points**: `main.py` (interactive flows) and `main_continuous.py` (always‑listening agent).
- **Speech pipeline**: `speech_to_text.py` orchestrates VAD, chunking, diarization hooks, and ASR provider selection.
- **Wake word & VAD**: `main_continuous.py`, `test_vad.py`, and wakeword utilities gate audio handed to transcription.
- **Context & personality**: prompts under `prompts/` define personas, memory behaviors live in `data/memory.json`, and conversation helpers sit in the `src/myai/tools/` package (memory, search, calendar, email domains).
- **Text-to-speech**: modules in `src/myai/tts/` handle voice synthesis, fallback voices, and stream buffering.
- **Benchmark harness**: `scripts/benchmark_pipeline.py` plus `data/benchmark_results.csv` capture latency/accuracy across configurations.

## Core Features

- **Chunked transcription** with smart buffering to keep partial hypotheses responsive while maintaining accuracy.
- **Context-aware responses** that blend conversation memory, persona prompts, and recent transcripts.
- **Flexible wake word detection** supporting multiple hotword models and a fallback push-to-talk mode.
- **Streaming TTS** that begins playback before synthesis completes, with fallback voices to avoid stalls.
- **Volume boost and normalization** to stabilize microphone gain across devices.

## Key Optimizations

- **Latency tuning**: adjustable chunk sizes, parallel ASR requests, and aggressive VAD trimming.
- **Speculative decoding**: optional context-aware transcription to pre-emptively fetch responses.
- **Resource fallbacks**: graceful degradation when GPU/accelerator features are unavailable.
- **Testing suite**: targeted PyTests for chunking, VAD, flexible wake words, TTS pronunciation, and stress scenarios.

## Maintenance Roadmap

1. **Break down `speech_to_text.py`** into cohesive submodules (e.g., `asr/`, `chunking/`, `monitoring/`).
2. **Unify configuration** via a single `config.py` or `.yaml` to avoid scattered constants.
3. **Automate doc generation** from source (docstrings + architecture diagrams) to keep this file evergreen.
4. **Refine benchmarks** by scripting result aggregation and visualizations into `tools/`.

## Archived Documentation

All legacy Markdown guides now live in `docs/archive/`. They remain searchable for historical details. Start with `docs/archive/ARCHIVE_INDEX.md` for a topic-to-file map.
