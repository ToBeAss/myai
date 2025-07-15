import sys
from src.agents.product_agents import get_orchestrator

# Initialize the orchestrator
agent_prefix = f"Terminal_"
orchestrator = get_orchestrator(agent_prefix=agent_prefix)

# Start the interactive loop with the user.
while True:
    print()
    user_input = input("👤: ")  # Take input from the user

    # Use the agent to process the input and stream a response
    token_index = 0
    for token in orchestrator.stream(user_input=user_input):
        if token_index == 0:
            sys.stdout.write("🤖: ")
        sys.stdout.write(token.content)
        sys.stdout.flush()
        token_index += 1
    print()