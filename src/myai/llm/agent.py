from datetime import datetime
from typing import Any, Optional, List, Dict, Union, Generator
from langchain_core.messages import AIMessage

from .llm_wrapper import LLM_Wrapper, Response
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


    def get_messages(self) -> List[Dict[str, str]]:
        """
        Retrieves the current list of messages, containing instructions and conversation history if available.

        :return: A list of message dictionaries.
        """
        
        # Add static instructions
        messages = self._instructions.copy()

        # Add dynamic instructions
        messages.append({
            "role": "system",
            "content": f"Today is {datetime.now().strftime('%A %d. %B %Y and the time is %H:%M')}."
        })

        # Add conversation history if available
        if self._memory:
            conversation_history = self._memory.retrieve_memory()
            for msg in conversation_history:
                # Map internal roles to standard message roles
                role = "assistant" if msg["role"] == "ai" else "user"
                messages.append({
                    "role": role,
                    "content": msg["message"]
                })

        return messages


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
        if not isinstance(is_streaming, bool):
            raise TypeError("is_streaming must be a boolean value.")
        
        messages = self.get_messages()
        current_query = [{"role": "user", "content": user_input}]

        for iteration in range(max_iterations):
            is_last_iteration = (iteration == max_iterations - 1)
            prompt = messages + current_query
            result: Optional[Response] = None

            # Use stream or invoke based on is_streaming flag
            if is_streaming:
                content = ""
                result_generator = self._llm.stream(prompt, use_tools=not is_last_iteration)
                # Collect result while streaming
                for token in Tool.collect_tool_calls_from_stream(result_generator):
                    content += token.content
                    yield token  # Yield each token as it is received
                    result = token
            else:
                result = self._llm.invoke(prompt, use_tools=not is_last_iteration)
                content = result.content

            if result.additional_kwargs.get("tool_calls"):
                tool_calls = result.additional_kwargs["tool_calls"]
                current_query.append({"role": "ai", "content": content, "tool_calls": tool_calls})
                
                for tool_call in tool_calls:
                    print(f"🛠️ {tool_call['function']['name']}({tool_call['function']['arguments']})")
                    tool_result = Tool.process_tool_call(tool_call, self._tools)
                    current_query.append({"role": "tool", "tool_call_id": tool_result["id"], "content": tool_result["result"]})
            else:
                if self._memory:
                    # Don't store tool calls and results in memory?
                    self._memory.add_message(user_input, "human")
                    self._memory.add_message(content, "ai")
                return result
