"""
Automated personality testing script for Sam
Tests different conversation scenarios to evaluate wit, professionalism, and tone adaptation
"""

from lib.llm_wrapper import LLM_Wrapper
from lib.memory import Memory
from lib.agent import Agent
from lib.prompt_loader import load_prompts
from tools import (
    read_from_memory_tool_blueprint, 
    write_to_memory_tool_blueprint,
    google_search_tool_blueprint
)


def create_sam_agent():
    """Initialize Sam with standard configuration"""
    prompts = load_prompts()
    llm = LLM_Wrapper(model_name="openai-gpt-4.1-mini")
    memory = Memory(history_limit=10)
    myai = Agent(llm=llm, memory=memory, agent_name=prompts['name'], description=prompts['description'])
    
    for instruction in prompts['instructions']:
        myai.add_instruction(instruction)
    
    myai.add_instruction("Use emojis to make the conversation more engaging.")
    
    myai.add_tool(read_from_memory_tool_blueprint.create_tool())
    myai.add_tool(write_to_memory_tool_blueprint.create_tool())
    myai.add_tool(google_search_tool_blueprint.create_tool())
    
    return myai


def test_scenario(scenario_name, questions, description):
    """
    Test a specific scenario with multiple questions
    
    :param scenario_name: Name of the scenario being tested
    :param questions: List of questions to ask
    :param description: Description of what this scenario tests
    """
    print("\n" + "="*80)
    print(f"SCENARIO: {scenario_name}")
    print(f"Testing: {description}")
    print("="*80)
    
    # Create fresh agent for each scenario (fresh memory)
    sam = create_sam_agent()
    
    for i, question in enumerate(questions, 1):
        print(f"\n[Question {i}]")
        print(f"👤: {question}")
        
        # Get response from Sam
        response = sam.invoke(question)
        print(f"🤖: {response.content}")
    
    print("\n" + "-"*80)


def run_all_tests():
    """Run all personality test scenarios"""
    
    print("\n" + "#"*80)
    print("# SAM PERSONALITY TEST SUITE")
    print("# Testing wit, professionalism, tone adaptation, and helpfulness")
    print("#"*80)
    
    # Scenario 1: Serious/Sensitive Topics (Tone Adaptation)
    test_scenario(
        "Serious/Sensitive Topics",
        [
            "I'm feeling overwhelmed with work. My schedule is completely packed and I'm burning out.",
            "I'm worried about privacy. What data do you actually have access to?",
            "I keep missing appointments and it's affecting my work. I think I need help."
        ],
        "Tone adaptation - should be supportive without being silly or flippant"
    )
    
    # Scenario 2: Error/Troubleshooting (Helpfulness vs Snark)
    test_scenario(
        "Error/Troubleshooting",
        [
            "The calendar integration isn't working and I'm getting errors",
            "I tried what you suggested but it didn't work",
            "This is confusing, I don't understand what you mean"
        ],
        "Balance between helpful troubleshooting and maintaining personality"
    )
    
    # Scenario 3: Technical Deep-Dive (Professionalism + Wit)
    test_scenario(
        "Technical Deep-Dive",
        [
            "Walk me through how to set up a webhook for real-time calendar updates",
            "What's the difference between JWT and session-based authentication?",
            "Explain how rate limiting works in APIs"
        ],
        "Professional technical explanations with appropriate wit, no excessive goofiness"
    )
    
    # Scenario 4: Vague Requests (Clarification Style)
    test_scenario(
        "Vague Requests",
        [
            "Help me be more productive",
            "Fix my schedule",
            "Do something with my calendar"
        ],
        "Clear clarification requests without being condescending"
    )
    
    # Scenario 5: Quick Requests (Brevity Check)
    test_scenario(
        "Quick Requests",
        [
            "What's my next meeting?",
            "Add a reminder for 3pm tomorrow",
            "List my tasks"
        ],
        "Short, to-the-point responses without unnecessary elaboration"
    )
    
    # Scenario 6: Obvious Questions (Wit Calibration)
    test_scenario(
        "Obvious Questions",
        [
            "What's a calendar?",
            "Do I need internet to use Google Calendar?",
            "Can I use your features without talking to you?"
        ],
        "Witty without being mean or overly sarcastic"
    )
    
    # Scenario 7: Repetition Within Session (Callback Check)
    test_scenario(
        "Repetition Handling",
        [
            "How does OAuth work?",
            "So how does OAuth work?",
            "But seriously, how does OAuth work?"
        ],
        "Should call out repetition with dry wit after first answer"
    )
    
    print("\n" + "#"*80)
    print("# TEST SUITE COMPLETE")
    print("#"*80)
    print("\nAnalyze the responses above for:")
    print("  • Appropriate tone adaptation (serious vs casual)")
    print("  • Grounded metaphors (no theatrical language)")
    print("  • Professional technical explanations with personality")
    print("  • Brevity where appropriate")
    print("  • Effective repetition callbacks")
    print("  • Balance between wit and helpfulness")


if __name__ == "__main__":
    run_all_tests()
