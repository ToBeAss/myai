import sys
from lib.llm_wrapper import LLM_Wrapper
from lib.memory import Memory
from lib.agent import Agent
from lib.prompt_loader import load_prompts
from tools import (
    read_from_memory_tool_blueprint, 
    write_to_memory_tool_blueprint,
    google_search_tool_blueprint
)

# CREATE THE AGENT
myai_prompts = load_prompts("prompts/sam_config.yaml")
myai_llm = LLM_Wrapper(model_name="openai-gpt-4.1-mini")
myai_memory = Memory(history_limit=10)
myai_agent = Agent(llm=myai_llm, memory=myai_memory, agent_name=myai_prompts['name'], description=myai_prompts['description'])
for instruction in myai_prompts['instructions']:
    myai_agent.add_instruction(instruction)
myai_agent.add_tool(read_from_memory_tool_blueprint.create_tool())
myai_agent.add_tool(write_to_memory_tool_blueprint.create_tool())
myai_agent.add_tool(google_search_tool_blueprint.create_tool())

# CREATE THE TESTER
tester_prompts = load_prompts("prompts/tobias_config.yaml")
tester_llm = LLM_Wrapper(model_name="openai-gpt-4.1-mini")
tester_memory = Memory(history_limit=10)
tester_agent = Agent(llm=tester_llm, memory=tester_memory, agent_name=tester_prompts['name'], description=tester_prompts['description'])
for instruction in tester_prompts['instructions']:
    tester_agent.add_instruction(instruction)

# START THE TEST
myai_response = """
You are interested in integrating your Google calendar with your AI assistant. 
You will be given 10 iterations to ask her about this.
Do not cut straigth to the chase, but ease her into the conversation with some small-talk first.
Use your first iteration to wake her up (e.g. "Hey Sam!").
"""

print("\nSTARTING TEST\n")
for i in range(10):
    print(f"ITERATION {i+1}/10")
    tester_request = tester_agent.invoke(myai_response).content
    print(f"Tester: {tester_request}")
    myai_response = myai_agent.invoke(tester_request).content
    print(f"Agent: {myai_response}")
print("\nTEST COMPLETE\n")
    