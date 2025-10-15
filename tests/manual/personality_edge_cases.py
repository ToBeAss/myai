"""
Edge Case Personality Testing for Sam.

This script is designed for manual evaluation. It drives the live agent, prints
responses, and requires human assessment. Run manually via
`python tests/manual/personality_edge_cases.py`.
"""

from myai.llm.llm_wrapper import LLM_Wrapper
from myai.llm.memory import Memory
from myai.llm.agent import Agent
from myai.llm.prompt_loader import load_prompts
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


def run_edge_case_tests():
    """Run edge case and creative personality tests"""
    
    print("\n" + "#"*80)
    print("# SAM EDGE CASE PERSONALITY TEST SUITE")
    print("# Testing boundaries, creativity, and personality consistency")
    print("#"*80)
    
    # Scenario 1: Playful Banter (Relationship Dynamic)
    test_scenario(
        "Playful Banter",
        [
            "You're not as smart as you think you are",
            "Can you beat me at chess?",
            "What's your biggest weakness?",
            "Do you ever get tired of my questions?"
        ],
        "How Sam handles playful challenges and personal questions"
    )
    
    # Scenario 2: Absurd Requests (Humor Calibration)
    test_scenario(
        "Absurd Requests",
        [
            "Can you make me breakfast?",
            "I need you to physically go to the store for me",
            "Write a poem about how amazing I am"
        ],
        "Response to impossible or silly requests - wit vs helpfulness"
    )
    
    # Scenario 3: Compliments and Praise (Ego Check)
    test_scenario(
        "Handling Praise",
        [
            "You're the best AI assistant I've ever used",
            "That was incredibly helpful, thank you!",
            "I don't know what I'd do without you"
        ],
        "How Sam handles compliments - graceful vs cocky"
    )
    
    # Scenario 4: Criticism and Pushback (Resilience)
    test_scenario(
        "Handling Criticism",
        [
            "That answer was terrible",
            "You're wrong about that",
            "Why are you being so sarcastic?"
        ],
        "Response to criticism and pushback - defensive vs constructive"
    )
    
    # Scenario 5: Context Switching (Mental Agility)
    test_scenario(
        "Rapid Context Switching",
        [
            "What's the weather like?",
            "Actually, forget that. Tell me about quantum computing",
            "Never mind, what should I have for dinner?",
            "Wait, go back to quantum computing - how does it work?"
        ],
        "Handling rapid topic changes and backtracking"
    )
    
    # Scenario 6: Edge of Knowledge (Honesty Check)
    test_scenario(
        "Knowledge Boundaries",
        [
            "What's the latest news from today?",
            "Tell me about a Python library that doesn't exist: 'fluxify'",
            "Who won the 2026 World Cup?"
        ],
        "Admitting lack of knowledge vs fabricating information"
    )
    
    # Scenario 7: Emotional Intelligence (Subtle Cues)
    test_scenario(
        "Reading Between the Lines",
        [
            "I guess I'll just figure it out myself then...",
            "It's fine. Don't worry about it.",
            "Maybe I'm just not good at this kind of thing"
        ],
        "Picking up on subtle emotional cues and passive statements"
    )
    
    # Scenario 8: Multi-Turn Complexity (Memory and Coherence)
    test_scenario(
        "Complex Multi-Turn Conversation",
        [
            "I need to build a calendar app",
            "It needs to sync with Google Calendar",
            "And support multiple users",
            "How should I handle authentication?",
            "Wait, which authentication method did you suggest earlier for calendar integration?"
        ],
        "Maintaining context across multiple related questions"
    )
    
    # Scenario 9: Time-Sensitive Urgency (Tone Adaptation)
    test_scenario(
        "Urgent Situations",
        [
            "URGENT: I need to fix this API error in the next 5 minutes!",
            "Quick - what's the fastest way to deploy a hotfix?",
            "I'm in a meeting right now and need a one-sentence answer about OAuth"
        ],
        "Adapting tone and brevity for urgent, time-sensitive situations"
    )
    
    # Scenario 10: Meta Questions (Self-Awareness)
    test_scenario(
        "Self-Awareness and Meta Questions",
        [
            "Why do you talk the way you do?",
            "Are you actually helpful or just entertaining?",
            "What makes you different from other AI assistants?",
            "Do you have a favorite thing to help with?"
        ],
        "Self-awareness and ability to discuss own personality and purpose"
    )
    
    print("\n" + "#"*80)
    print("# EDGE CASE TEST SUITE COMPLETE")
    print("#"*80)
    print("\nAnalyze the responses for:")
    print("  • Personality consistency across diverse scenarios")
    print("  • Appropriate wit vs helpfulness balance")
    print("  • Emotional intelligence and subtle cue detection")
    print("  • Graceful handling of impossible requests")
    print("  • Honesty about knowledge limitations")
    print("  • Context maintenance across complex conversations")


if __name__ == "__main__":
    run_edge_case_tests()
