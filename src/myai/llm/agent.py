from datetime import datetime
from typing import Any, Optional, List, Dict, Union, Generator
from langchain_core.messages import AIMessage

from .llm_wrapper import LLM_Wrapper
from .memory import Memory
from .chroma_wrapper import Chroma_Wrapper
from .tool import Tool

class Agent:
    """A conversational agent that interacts with an LLM, maintains memory and can utilize tools such as database retrieval."""

    # Maximum allowed length for user inputs
    MAX_USER_INPUT_LENGTH = 4096

    def __init__(self, llm: LLM_Wrapper, memory: Optional[Memory] = None, agent_name: str = "Agent", description: str = "You are an AI assistant."):
        """
        Initializes the agent with an LLM instance and an optional memory and chroma module.

        :param llm: An instance of LLM_Wrapper.
        :param memory: An optional instance of Memory.
        :param agent_name: The name of the agent.
        :param description: A description of the agent's capabilities.
        """
        # Validate input types
        if not isinstance(llm, LLM_Wrapper):
            raise TypeError("llm must be an instance of LLM_Wrapper")
        if memory is not None and not isinstance(memory, Memory):
            raise TypeError("memory must be an instance of Memory or None")
        if not isinstance(agent_name, str):
            raise TypeError("agent_name must be a string")
        if not isinstance(description, str):
            raise TypeError("description must be a string")
        
        self._id: int = 0 # Implement uniquie ID generation
        self.name = agent_name
        self.description = description
        self._instructions: List[Dict[str, str]] = []
        self._tools: Dict[str, Dict] = {}
        self._llm = llm
        self._memory = memory

        # Add init instructions to inform the agent of its identity
        self.add_instruction(self.description)
    

    def _validate_input(self, user_input: str) -> None:
        """
        Validate the input parameters.
        
        :param user_input: The user input to validate.
        :raises ValueError: If any of the inputs are invalid.
        :raises TypeError: If any of the inputs are of incorrect type.
        """
        if not isinstance(user_input, str):
            raise TypeError("User input must be a string.")
        
        # Add character limit validation
        if len(user_input) > self.MAX_USER_INPUT_LENGTH:
            current_length = len(user_input)
            raise ValueError(
                f"User input exceeds maximum length of {self.MAX_USER_INPUT_LENGTH} characters. "
                f"Current length: {current_length}. Please shorten your input by "
                f"{current_length - self.MAX_USER_INPUT_LENGTH} characters."
            )
    

    def add_instruction(self, instruction: str) -> None:
        """
        Adds a system prompt, dubbed instruction.

        :param instruction: Instruction to be stored.
        """
        if not isinstance(instruction, str):
            raise ValueError("Instruction must be a string.")
        
        self._instructions.append({"role": "system", "content": instruction})


    def add_tool(self, tool: Tool, **kwargs) -> None:
        """
        Adds a tool to the agent.

        :param tool: An instance of Tool that the agent can use.
        """
        if not isinstance(tool, Tool):
            raise ValueError("Tool must be an instance of Tool.")
        
        # Add instructions for tool usage when the first tool is added
        """
        if not self._tools:
            self.add_instruction(Tool.GENERAL_TOOL_INSTRUCTIONS)
        """

        self._tools[tool.name] = tool.get_tool()
        self._llm.bind_tools(list(self._tools.values()), **kwargs)


    def add_agent_as_tool(self, agent: 'Agent', description: Optional[str] = None, **kwargs) -> None:
        """
        Adds another agent as a tool to the current agent.

        :param agent: An instance of Agent to be added as a tool.
        :param description: A description of the agent's capabilities, expertise and use case.
        """
        if not isinstance(agent, Agent):
            raise ValueError("Agent must be an instance of Agent.")
        
        # If no description is provided, use the agent's description from initialization
        if description is None:
            description = agent.description

        # Initialize the agent as a tool
        agent_tool = Tool(
            name=f"Agent_{agent.name}",
            function=agent.invoke,
            description=f"""
            This is a tool that allows you to use another agent as a tool.
            :param user_input: The query to ask the agent. This parameter is REQUIRED.
            :return: The agent's response.

            The agent is named {agent.name} and has the following capabilities:
            {description}
            """
        )
        self.add_tool(agent_tool, **kwargs)


    def _get_instructions(self) -> List[Dict[str, str]]:
        """
        Get static system instructions.
        
        :return: List of system instruction messages.
        """
        return self._instructions


    def _get_conversation_history(self) -> List[Dict[str, Any]]:
        """
        Get past conversation messages from memory.
        
        :return: List of user/assistant message pairs from conversation history.
        """
        return self._memory.retrieve_memory() if self._memory else []
    

    def _build_current_turn(self, user_input: str) -> Dict[str, str]:
        """
        Build current turn message with dynamic context and user query.
        
        Wraps user input with dynamic contextual information such as:
        - Current datetime
        - Future: Upcoming events, retrieved memories, etc.
        
        :param user_input: The user's query.
        :return: Single user message dictionary with [CONTEXT] block and query.
        """
        query_parts = [
            "[CONTEXT]",
            f"Current datetime: {datetime.now().strftime('%A, %B %d, %Y at %H:%M')}",
            "[/CONTEXT]",
            "",
            "Use the context above and any available tools to respond to the following:",
            "",
            user_input
        ]
        
        return {
            "role": "user",
            "content": "\n".join(query_parts)
        }


    def build_prompt(self, user_input: str) -> List[Dict[str, str]]:
        """
        Build complete prompt by combining all message parts.
        
        Order optimized for prompt caching:
        1. Static instructions (cacheable)
        2. Conversation history (mostly cacheable)
        3. Current turn with dynamic context (changes frequently)
        
        :param user_input: The user's query.
        :return: Complete list of messages ready for LLM invocation.
        """
        return (
            self._get_instructions() +
            self._get_conversation_history() +
            [self._build_current_turn(user_input)]
        )


    def _handle_tool_calls(self, tool_calls: List[Dict[str, Any]], ai_content: str) -> List[Dict[str, Any]]:
        """Process tool calls and append results to current query."""
        tool_messages = [{"role": "ai", "content": ai_content, "tool_calls": tool_calls}]
        
        for tool_call in tool_calls:
            print(f"🛠️ {tool_call['function']['name']}({tool_call['function']['arguments']})")
            tool_result = Tool.process_tool_call(tool_call, self._tools)
            tool_messages.append({"role": "tool", "tool_call_id": tool_result["id"], "content": tool_result["result"]})

        return tool_messages


    def _save_conversation(self, user_input: str, ai_content: str) -> None:
        """Save user input and AI response to memory."""
        if self._memory:
            self._memory.add_message(user_input, "human")
            self._memory.add_message(ai_content, "ai")


    def invoke(self, user_input: str, max_iterations: int = 3, is_streaming: bool = False) -> Any:
        """
        Invokes the agent to process user input.

        :param user_input: The user input query.
        :param max_iterations: The maximum number of iterations to process tools.
        :param is_streaming: Whether to stream the response or not.
        :return: The LLM's response or a generator yielding streamed responses.
        """
        # Validate inputs
        self._validate_input(user_input)
        if not isinstance(max_iterations, int) or max_iterations <= 0:
            raise ValueError("max_iterations must be a positive integer.")
        
        # Route to appropriate implementation based on streaming flag
        if is_streaming:
            return self._stream(user_input, max_iterations)
        else:
            return self._invoke(user_input, max_iterations)
    

    def _invoke(self, user_input: str, max_iterations: int = 3) -> AIMessage:
        """
        Invokes the agent to process user input (non-streaming).

        :param user_input: The user input query.
        :param max_iterations: The maximum number of iterations to process tools.
        :return: The LLM's response.
        """
        
        prompt_messages = self.build_prompt(user_input)

        for iteration in range(max_iterations):
            is_last_iteration = (iteration == max_iterations - 1)
            
            result = self._llm.invoke(prompt_messages, use_tools=not is_last_iteration)

            # Convert content to string if it's a list
            content_str = result.content if isinstance(result.content, str) else str(result.content)

            if result.additional_kwargs.get("tool_calls"):
                prompt_messages.extend(self._handle_tool_calls(tool_calls=result.additional_kwargs["tool_calls"], ai_content=content_str))
            else:
                self._save_conversation(user_input, ai_content=content_str)
                return result
        
        # If we've exhausted iterations, return the last result
        raise RuntimeError("Max iterations reached without a final response")
    

    def _stream(self, user_input: str, max_iterations: int = 3) -> Generator[AIMessage, None, None]:
        """
        Invokes the agent to process user input (streaming).

        :param user_input: The user input query.
        :param max_iterations: The maximum number of iterations to process tools.
        :return: A generator yielding streamed responses.
        """

        prompt_messages = self.build_prompt(user_input)

        for iteration in range(max_iterations):
            is_last_iteration = (iteration == max_iterations - 1)
            
            result_generator = self._llm.stream(prompt_messages, use_tools=not is_last_iteration)
            result: Optional[AIMessage] = None
            content = ""
            
            # Collect result while streaming
            for token in Tool.collect_tool_calls_from_stream(result_generator):
                content += token.content
                yield token
                result = token
            
            # Convert content to string if it's a list
            content_str = content if isinstance(content, str) else str(content)

            if result and result.additional_kwargs.get("tool_calls"):
                prompt_messages.extend(self._handle_tool_calls(tool_calls=result.additional_kwargs["tool_calls"], ai_content=content_str))
            else:
                self._save_conversation(user_input, ai_content=content_str)
                return
