import sys
from lib.llm_wrapper import LLM_Wrapper
from lib.memory import Memory
from lib.agent import Agent
from lib.speech_to_text import SpeechToText
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
# Restrict to only English and Norwegian (excludes Swedish, Danish, etc.)
stt.set_language_preference(language=None, task="transcribe", allowed_languages=['en', 'no'])

# Other options:
# stt.set_language_preference(language=None, task="transcribe")  # Auto-detect, all languages
# stt.set_language_preference(language="en", task="transcribe")  # Force English
# stt.set_language_preference(language="no", task="transcribe")  # Force Norwegian
# stt.set_language_preference(language=None, task="translate")   # Auto-detect, translate to English

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

# Start the interactive loop with the user.
print("\n🎙️ Voice-activated AI assistant ready!")
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
        print("� Goodbye!")
        break
    
    # Record and transcribe speech
    user_input = stt.listen_and_transcribe(max_duration=30)
    
    if not user_input:
        print("🔇 No speech detected. Please try again.")
        continue
    
    # Use the agent to process the input and stream a response
    token_index = 0
    for token in myai.stream(user_input=user_input):
        if token_index == 0:
            sys.stdout.write("🤖: ")
        sys.stdout.write(token.content)
        sys.stdout.flush()
        token_index += 1
    print()