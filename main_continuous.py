import sys
import time
from lib.llm_wrapper import LLM_Wrapper
from lib.memory import Memory
from lib.agent import Agent
from lib.speech_to_text import SpeechToText
from lib.text_to_speech import TextToSpeech
from tools import (
    read_from_memory_tool_blueprint, 
    write_to_memory_tool_blueprint,
    google_search_tool_blueprint
)

# Description of the agent's purpose
description = """
You are a clever, helpful AI assistant designed to assist the user, Tobias, with various tasks.
"""

# Initialize the agent
llm = LLM_Wrapper(model_name="openai-gpt-4.1-mini")
memory = Memory(history_limit=10)
myai = Agent(llm=llm, memory=memory, agent_name="MyAI", description=description)

# Initialize speech-to-text system
print("🔧 Initializing speech-to-text system...")
stt = SpeechToText(model_size="base")  # Upgraded from "tiny" to "base" for better Norwegian accuracy

# Optional: Configure language preferences
# Restrict to only English and Norwegian (includes all Norwegian variants)
stt.set_language_preference(language=None, task="transcribe", allowed_languages=['en', 'no', 'nb', 'nn'])

# Initialize text-to-speech system with automatic fallback
print("🔧 Initializing text-to-speech system...")
tts = TextToSpeech(
    voice_name="en-GB-Chirp3-HD-Achernar",  # Premium voice (100k free chars/month) (Alternative: Enceladus)
    language_code="en-GB",
    speaking_rate=1.1,
    pitch=0.0,
    enforce_free_tier=True,  # Stay within free tier
    fallback_voice="en-GB-Standard-A"  # Fallback to Standard voice (4M free chars/month)
)

# Configure wake words (you can customize these)
stt.set_wake_words(["hey myai", "hey assistant", "computer", "jarvis"])

# Set conversation timeout (how long to wait for follow-up questions)
stt.set_conversation_timeout(5.0)  # 5 seconds to ask follow-up questions

# Give the agent instructions on how to behave
myai.add_instruction("Always respond in english.")
myai.add_instruction("Be concise and to the point.")
myai.add_instruction("Use any available tools to assist with tasks.")
myai.add_instruction("If you don't know the answer, say 'I don't know' instead of making up an answer.")
myai.add_instruction("Use emojis to make the conversation more engaging.")

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
    
    # Stream the response with real-time TTS (speaks as it generates)
    print("🤖: ", end="", flush=True)
    tts.speak_streaming_async(myai.stream(user_input=command_text), print_text=True)
    print()
    
    # Enter conversation mode to allow follow-up questions
    stt.enter_conversation_mode()
    stt.start_conversation_timer()

# Choose operation mode
print("\n🎙️ Voice-activated AI assistant ready!")
print("Choose your mode:")
print("1. 👂 Continuous listening (hands-free)")
print("2. 🎤 Manual recording (press-to-talk)")

while True:
    try:
        mode = input("\nEnter choice (1 or 2): ").strip()
        
        if mode == "1":
            # Continuous listening mode
            print("\n🚀 Starting continuous listening mode...")
            print("💡 Say one of the wake words followed by your question:")
            print(f"   - 'Hey MyAI, what's the weather?'")
            print(f"   - 'Hey Assistant, help me with something'")
            print(f"   - 'Computer, search for Python tutorials'")
            print("\n� After the AI responds, you have 5 seconds to ask follow-up questions")
            print("   without saying the wake word again!")
            print("\n�� Press Ctrl+C to exit")

            stt.start_continuous_listening(handle_voice_command)
            
            # Keep the main thread alive
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n🔇 Stopping continuous listening...")
                stt.stop_continuous_listening()
                print("👋 Goodbye!")
                break
        
        elif mode == "2":
            # Manual recording mode (original functionality)
            print("\n🎤 Manual recording mode selected")
            print("💡 Instructions:")
            print("   - Press ENTER to start recording")
            print("   - Speak clearly and loudly into your microphone")
            print("   - Watch the volume indicator (aim for 3-5 bars)")
            print("   - Press SPACE to stop recording (minimum 1 second)")
            print("   - Type 'quit' and press ENTER to exit")
            print("-" * 60)
            
            while True:
                print()
                # Wait for user to press Enter to start recording
                user_action = input("🎤 Press ENTER to start recording (or type 'quit' to exit): ").strip().lower()
                
                if user_action == 'quit':
                    print("👋 Goodbye!")
                    break
                
                # Record and transcribe speech
                user_input = stt.listen_and_transcribe(max_duration=30)
                
                if not user_input:
                    print("🔇 No speech detected. Please try again.")
                    continue
                
                # Stream the response with real-time TTS (speaks as it generates)
                print("🤖: ", end="", flush=True)
                tts.speak_streaming_async(myai.stream(user_input=user_input), print_text=True)
                print()
            break
        
        else:
            print("❌ Please enter 1 or 2")
            
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        break
    except Exception as e:
        print(f"❌ Error: {e}")
        break
