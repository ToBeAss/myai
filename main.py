import sys
import os
import warnings
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_PATH = PROJECT_ROOT / "src"
if SRC_PATH.exists() and str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

# Suppress pygame warnings before pygame is imported (via text_to_speech)
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "1"  # Hide pygame greeting message
warnings.filterwarnings("ignore", category=DeprecationWarning)  # Suppress all deprecation warnings
warnings.filterwarnings("ignore", message=".*pkg_resources.*")  # Suppress pkg_resources warning

from myai.llm.llm_wrapper import LLM_Wrapper
from myai.llm.memory import Memory
from myai.llm.agent import Agent
from myai.tts.text_to_speech import TextToSpeech
from myai.llm.prompt_loader import load_prompts
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

# Load and apply all instructions from configuration
for instruction in prompts['instructions']:
    myai.add_instruction(instruction)

# Add text-specific instructions
#myai.add_instruction("Use emojis to make the conversation more engaging.")

# Give the agent tools to work with
myai.add_tool(read_from_memory_tool_blueprint.create_tool())
myai.add_tool(write_to_memory_tool_blueprint.create_tool())
myai.add_tool(google_search_tool_blueprint.create_tool())

# Ask user to choose response mode
print("\n🎯 Choose your interaction mode:")
print("1. Text only (type and read)")
print("2. Voice responses (type and listen)")
print()

while True:
    mode_choice = input("Enter your choice (1 or 2): ").strip()
    if mode_choice in ['1', '2']:
        break
    print("❌ Invalid choice. Please enter 1 or 2.")

voice_mode = (mode_choice == '2')
tts = None

# Initialize text-to-speech if voice mode is selected
if voice_mode:
    print("\n🔧 Initializing text-to-speech system...")
    tts = TextToSpeech(
        voice_name="en-GB-Chirp3-HD-Achernar",  # Premium voice (100k free chars/month)
        language_code="en-GB",
        speaking_rate=1.1,
        pitch=0.0,
        enforce_free_tier=True,  # Stay within free tier
        fallback_voice="en-GB-Wavenet-A"  # Fallback to Wavenet voice (4M free chars/month)
    )
    print("✅ Voice mode enabled! You'll hear responses in your earphones.")
else:
    print("✅ Text-only mode enabled!")

while True:
    print()
    user_input = input("👤: ").strip()

    if user_input.lower() == 'quit':
        print("👋 Goodbye!")
        break
    
    if not user_input:
        continue
    
    # Use the agent to process the input and stream a response
    if voice_mode:
        # Voice mode: collect response and speak it
        response_generator = myai.stream(user_input=user_input)
        print("🤖: ", end="", flush=True)
        tts.speak_streaming_async(response_generator, chunk_on=",.!?—", print_text=True, min_chunk_size=30)
        print()
    else:
        # Text-only mode: stream to console
        token_index = 0
        for token in myai.stream(user_input=user_input):
            if token_index == 0:
                sys.stdout.write("🤖: ")
            sys.stdout.write(token.content)
            sys.stdout.flush()
            token_index += 1
        print()