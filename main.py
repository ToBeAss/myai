import sys
from lib.llm_wrapper import LLM_Wrapper
from lib.memory import Memory
from lib.agent import Agent
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
while True:
    print()
    user_input = input("👤: ")  # Take input from the user

    # Use the agent to process the input and stream a response
    token_index = 0
    for token in myai.stream(user_input=user_input):
        if token_index == 0:
            sys.stdout.write("🤖: ")
        sys.stdout.write(token.content)
        sys.stdout.flush()
        token_index += 1
    print()