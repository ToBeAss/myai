import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_PATH = PROJECT_ROOT / "src"
if SRC_PATH.exists() and str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from myai.llm.agent import Agent
from myai.llm.llm_wrapper import LLM_Wrapper
from myai.llm.memory import Memory
from myai.llm.prompt_loader import load_prompts
from myai.stt.speech_to_text import SpeechToText
from myai.tts.text_to_speech import TextToSpeech
from myai.tools import (
    google_search_tool_blueprint,
    read_from_memory_tool_blueprint,
    write_to_memory_tool_blueprint,
)

def build_assistant() -> tuple[Agent, SpeechToText, TextToSpeech]:
    """Initialize and wire the agent, STT, and TTS components."""
    prompts = load_prompts()

    llm = LLM_Wrapper(model_name="openai-gpt-4.1-nano")
    memory = Memory()
    agent = Agent(
        llm=llm,
        memory=memory,
        agent_name=prompts["name"],
        description=prompts["description"],
    )

    print("🔧 Initializing speech-to-text system...")
    stt = SpeechToText(model_size="base", track_metrics=False, use_faster_whisper=True)
    stt.enable_chunked_transcription_mode(max_workers=2)
    stt.set_wake_words(["sam", "samantha"])
    stt.set_conversation_timeout(5.0)

    print("🔧 Initializing text-to-speech system...")
    tts = TextToSpeech(
        voice_name="en-GB-Chirp3-HD-Achernar",
        language_code="en-GB",
        speaking_rate=1.1,
        pitch=0.0,
        enforce_free_tier=True,
        fallback_voice="en-GB-Wavenet-A",
    )

    for instruction in prompts["instructions"]:
        agent.add_instruction(instruction)

    agent.add_tool(read_from_memory_tool_blueprint.create_tool())
    agent.add_tool(write_to_memory_tool_blueprint.create_tool())
    agent.add_tool(google_search_tool_blueprint.create_tool())
    return agent, stt, tts


def run_continuous() -> None:
    """Start continuous wake-word listening and hand commands to the assistant."""
    agent, stt, tts = build_assistant()

    def handle_voice_command(command_text: str) -> None:
        # Handle empty or very short commands.
        if not command_text or len(command_text.strip()) < 2:
            print("\n👤: [wake word only]")
            response_text = "Hi! What can I help you with?"
            print(f"🤖: {response_text}")
            tts.speak(response_text)
            stt.enter_conversation_mode()
            stt.start_conversation_timer()
            return

        incomplete_marker = "[INCOMPLETE - Please continue or repeat your question]"
        if incomplete_marker in command_text:
            cleaned_command = command_text.replace(incomplete_marker, "").strip()
            print(f"\n👤: {cleaned_command}")
            response_text = (
                "It looks like your question got cut off. Could you please repeat "
                f"the complete question? I heard '{cleaned_command}'..."
            )
            print(f"🤖: {response_text}")
            tts.speak(response_text)
            stt.enter_conversation_mode()
            stt.start_conversation_timer()
            return

        print(f"\n👤: {command_text}")
        response_generator = agent.invoke(user_input=command_text, is_streaming=True)
        print("🤖: ", end="", flush=True)
        tts.speak_streaming_async(
            response_generator,
            chunk_on=",.!?—",
            print_text=True,
            min_chunk_size=30,
        )
        print()
        stt.enter_conversation_mode()
        stt.start_conversation_timer()

    print("\n🎙️ Voice-activated AI assistant ready!")
    print("\n🎧 Starting continuous listening mode (hands-free)...")
    print("💡 Say one of the wake words followed by your question:")
    print("   - 'Sam, what's the weather?'")
    print("   - 'How is the forecast looking, Sam?'")
    print("   - 'Sam could you help me with something?'")
    print("\n💬 After the AI responds, you have 5 seconds to ask follow-up questions")
    print("   without saying the wake word again!")
    print("\n🛑 Press Ctrl+C to exit\n")

    try:
        stt.start_continuous_listening(handle_voice_command)
        print("✅ Listening for wake words...\n")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🔇 Stopping continuous listening...")
        stt.stop_continuous_listening()
        print("👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        stt.stop_continuous_listening()
        print("👋 Goodbye!")


if __name__ == "__main__":
    run_continuous()
