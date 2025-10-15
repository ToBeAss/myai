import argparse
from typing import List, Tuple

from lib.llm_wrapper import LLM_Wrapper
from lib.memory import Memory
from lib.agent import Agent
from lib.prompt_loader import load_prompts
from tools import (
    read_from_memory_tool_blueprint,
    write_to_memory_tool_blueprint,
    google_search_tool_blueprint,
)


def build_agent(config_path: str, with_tools: bool = True) -> Agent:
    """Create an agent from a YAML config path."""
    prompts = load_prompts(config_path)
    llm = LLM_Wrapper(model_name="openai-gpt-4.1-mini")
    memory = Memory(history_limit=10)
    agent = Agent(
        llm=llm,
        memory=memory,
        agent_name=prompts["name"],
        description=prompts["description"],
    )
    for instruction in prompts["instructions"]:
        agent.add_instruction(instruction)
    if with_tools:
        agent.add_tool(read_from_memory_tool_blueprint.create_tool())
        agent.add_tool(write_to_memory_tool_blueprint.create_tool())
        agent.add_tool(google_search_tool_blueprint.create_tool())
    return agent


def run_dialog(
    assistant: Agent, tester: Agent, seed_prompt: str, turns: int
) -> List[Tuple[str, str]]:
    """Simulate a dialog and capture the turns for later comparison."""
    dialog: List[Tuple[str, str]] = []
    assistant_reply = seed_prompt
    for _ in range(turns):
        tester_request = tester.invoke(assistant_reply).content
        assistant_reply = assistant.invoke(tester_request).content
        dialog.append((tester_request, assistant_reply))
    return dialog


def print_dialog(transcript: List[Tuple[str, str]], header: str) -> None:
    print(f"\n{header}\n")
    for idx, (tester_turn, agent_turn) in enumerate(transcript, start=1):
        print(f"ITERATION {idx}")
        print(f"Tester: {tester_turn}")
        print(f"Agent: {agent_turn}\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run scripted conversations to evaluate prompt configs."
    )
    parser.add_argument(
        "--config",
        default="prompts/sam_config.yaml",
        help="Primary assistant config to evaluate.",
    )
    parser.add_argument(
        "--compare-config",
        dest="compare_config",
        help="Optional second config for side-by-side comparison.",
    )
    parser.add_argument(
        "--turns",
        type=int,
        default=10,
        help="Number of interaction turns to simulate.",
    )
    parser.add_argument(
        "--seed",
        default=(
            "You are interested in integrating your Google calendar with your AI assistant.\n"
            "You will be given 10 iterations to ask her about this.\n"
            "Do not cut straight to the chase; ease her into the conversation with small talk first.\n"
            "Use your first iteration to wake her up (e.g. 'Hey Sam!')."
        ),
        help="Seed instructions for the tester agent.",
    )
    args = parser.parse_args()

    assistant = build_agent(args.config)
    tester = build_agent("prompts/tobias_config.yaml", with_tools=False)

    primary_transcript = run_dialog(assistant, tester, args.seed, args.turns)
    print_dialog(primary_transcript, "PRIMARY CONFIG RESULTS")

    if args.compare_config:
        comparison_assistant = build_agent(args.compare_config)
        comparison_transcript = run_dialog(
            comparison_assistant, tester, args.seed, args.turns
        )
        print_dialog(comparison_transcript, "COMPARISON CONFIG RESULTS")


if __name__ == "__main__":
    main()
