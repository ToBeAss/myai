import sys
import time
import os
import warnings

# Suppress pygame warnings before pygame is imported (via text_to_speech)
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "1"  # Hide pygame greeting message
warnings.filterwarnings("ignore", category=DeprecationWarning)  # Suppress all deprecation warnings
warnings.filterwarnings("ignore", message=".*pkg_resources.*")  # Suppress pkg_resources warning

from lib.llm_wrapper import LLM_Wrapper
from lib.memory import Memory
from lib.agent import Agent
from lib.speech_to_text import SpeechToText
from lib.text_to_speech import TextToSpeech
from lib.prompt_loader import load_prompts
from tools import (
    read_from_memory_tool_blueprint, 
    write_to_memory_tool_blueprint,
    google_search_tool_blueprint
)

# Load agent configuration from prompts file
prompts = load_prompts()

# Initialize the agent with loaded configuration
llm = LLM_Wrapper(model_name="openai-gpt-4.1-mini")
memory = Memory(history_limit=10)
myai = Agent(llm=llm, memory=memory, agent_name=prompts['name'], description=prompts['description'])

# Initialize speech-to-text system
print("🔧 Initializing speech-to-text system...")
# Disable metrics tracking in production - should only be enabled in training environment
# Using 'base' model for better accuracy with faster-whisper optimization (4-5x faster)
stt = SpeechToText(model_size="base", track_metrics=False, use_faster_whisper=True)

# Enable chunked transcription for faster response times
stt.enable_chunked_transcription_mode(max_workers=2)

# Initialize text-to-speech system with automatic fallback
print("🔧 Initializing text-to-speech system...")
tts = TextToSpeech(
    voice_name="en-GB-Chirp3-HD-Achernar",  # Premium voice (100k free chars/month) (Alternative: Enceladus)
    language_code="en-GB",
    speaking_rate=1.1,
    pitch=0.0,
    enforce_free_tier=True,  # Stay within free tier
    fallback_voice="en-GB-Wavenet-A"  # Fallback to Wavenet voice (4M free chars/month)
)

# Configure wake words (you can customize these)
wake_words = ["sam", "samantha"]
stt.set_wake_words(wake_words)

# Set conversation timeout (how long to wait for follow-up questions)
stt.set_conversation_timeout(5.0)  # 5 seconds to ask follow-up questions

# Load and apply all instructions from configuration
for instruction in prompts['instructions']:
    myai.add_instruction(instruction)

# Give the agent tools to work with
myai.add_tool(read_from_memory_tool_blueprint.create_tool())
myai.add_tool(write_to_memory_tool_blueprint.create_tool())
myai.add_tool(google_search_tool_blueprint.create_tool())

def handle_voice_command(command_text):
    """Handle voice commands triggered by wake words."""
    
    # Handle empty or very short commands
    if not command_text or len(command_text.strip()) < 2:
        print("\n👤: [wake word only]")
        response_text = "Hi! What can I help you with?"
        print(f"🤖: {response_text}")
        tts.speak(response_text)
        
        # Enter conversation mode for follow-up
        stt.enter_conversation_mode()
        stt.start_conversation_timer()
        return
    
    # Check if this looks like an incomplete command
    if "[INCOMPLETE - Please continue or repeat your question]" in command_text:
        cleaned_command = command_text.replace("[INCOMPLETE - Please continue or repeat your question]", "").strip()
        print(f"\n👤: {cleaned_command}")
        response_text = f"It looks like your question got cut off. Could you please repeat the complete question? I heard '{cleaned_command}'..."
        print(f"🤖: {response_text}")
        tts.speak(response_text)
        
        # Enter conversation mode for the complete question
        stt.enter_conversation_mode()
        stt.start_conversation_timer()
        return
    
    print(f"\n👤: {command_text}")
    
    # Generate the response
    response_generator = myai.stream(user_input=command_text)
    
    # Stream the response with real-time TTS (speaks as it generates)
    # Using optimized parameters for faster response with natural pauses at commas
    print("🤖: ", end="", flush=True)
    tts.speak_streaming_async(response_generator, chunk_on=",.!?—", print_text=True, min_chunk_size=30)
    print()
    
    # Enter conversation mode to allow follow-up questions
    stt.enter_conversation_mode()
    stt.start_conversation_timer()

# Start continuous listening mode
print("\n🎙️ Voice-activated AI assistant ready!")
print("\n🎧 Starting continuous listening mode (hands-free)...")
print("💡 Say one of the wake words followed by your question:")
print(f"   - 'Sam, what's the weather?'")
print(f"   - 'How is the forecast looking, Sam?'")
print(f"   - 'Sam could you help me with something?'")
print("\n💬 After the AI responds, you have 5 seconds to ask follow-up questions")
print("   without saying the wake word again!")
print("\n🛑 Press Ctrl+C to exit\n")

try:
    stt.start_continuous_listening(handle_voice_command)
    print("✅ Listening for wake words...\n")
    
    # Keep the main thread alive
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
