from datetime import datetime
from typing import Any, Optional, List, Dict

from .llm_wrapper import LLM_Wrapper, Response
from .memory import Memory
from .chroma_wrapper import Chroma_Wrapper
from .tool import Tool

class Agent:
    """A conversational agent that interacts with an LLM, maintains memory and can utilize tools such as database retrieval."""

    # Maximum allowed length for user inputs
    MAX_USER_INPUT_LENGTH = 4096
    # Define possible stages
    STAGE_ORCHESTRATOR = "orchestrator"
    STAGE_THINKING = "thinking"
    STAGE_TOOL = "tool"
    STAGE_CONTENT = "content"

    def __init__(self, llm: LLM_Wrapper, memory: Optional[Memory] = None, chroma: Optional[Chroma_Wrapper] = None, agent_name: str = "Agent", description: str = "You are an AI assistant."):
        """
        Initializes the agent with an LLM instance and an optional memory and chroma module.

        :param llm: An instance of LLM_Wrapper.
        :param memory: An optional instance of Memory.
        :param chroma: An optional instance of Chroma_Wrapper.
        :param agent_name: The name of the agent.
        :param description: A description of the agent's capabilities.
        """
        # Validate input types
        if not isinstance(llm, LLM_Wrapper):
            raise TypeError("llm must be an instance of LLM_Wrapper")
        if memory is not None and not isinstance(memory, Memory):
            raise TypeError("memory must be an instance of Memory or None")
        if chroma is not None and not isinstance(chroma, Chroma_Wrapper):
            raise TypeError("retriever must be an instance of Retriever or None")
        if not isinstance(agent_name, str):
            raise TypeError("agent_name must be a string")
        if not isinstance(description, str):
            raise TypeError("description must be a string")
        
        self._id: int = 0 # Implement uniquie ID generation
        self.name = agent_name
        self.description = description
        self._instructions: List[Dict[str, Any]] = []
        self._tools: Dict[str, Dict] = {}
        self._llm = llm
        self._memory = memory
        self._chroma = chroma

        # Add init instructions to inform the agent of its identity
        self.add_instruction(f"Your name is {self.name}. {self.description}")
    

    def _validate_input(self, user_input: str, search_type: Optional[str] = None, k: Optional[int] = None) -> None:
        """
        Validate the input parameters.
        
        :param user_input: The user input to validate.
        :param search_type: Optional search type to validate.
        :param k: Optional number of results to validate.
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
        
        if search_type is not None and not isinstance(search_type, str):
            raise TypeError("Search type must be a string.")
        if k is not None and not isinstance(k, int):
            raise TypeError("k must be an integer.")
    

    def _retrieve_data(self, query: str, search_type: str = "similarity_scores", k: int = 5, **kwargs) -> List:
        """
        Retrieve data based on the query and search type.

        :param query: The query to search for.
        :param search_type: The type of search to perform.
        :param k: The number of results to return.
        :param kwargs: Additional keyword arguments for the retriever.
        :return: The retrieved data as a list.
        """
        if not self._chroma:
            print("Chroma wrapper is not available.")
            return []
        
        if search_type == "mmr":
            retrieved_data = self._chroma.retrieve_data_using_mmr(query=query, k=k, **kwargs)
        elif search_type == "similarity_scores":
            retrieved_data = self._chroma.retrieve_data_using_similarity_scores(query=query, k=k, **kwargs)
        else:
            retrieved_data = []
        return retrieved_data
        

    def _reprompt(self, user_input: str) -> str:
        """
        Reprompts the user's query based on the previous query and context window.

        :param user_input: The user input query.
        :return: The reprompted query.
        """
        # Handle conversation history if available
        formatted_conversation_history = ""
        if self._memory:
            conversation_history = self._memory.retrieve_memory()
            formatted_conversation_history = Memory.format_messages(conversation_history)

        # Build the prompt for the LLM
        prompt = (
            f"<conversation_history>\n{formatted_conversation_history}</conversation_history>\n\n"
            f"<current_query>{user_input}</current_query>\n\n"
            "<response_guidelines>Rephrase the above question from the user based on the instructions and any available context to better be used in a RAG retrieval search. Include important keywords that could be relevant to the user's question for the retrieval to work better.</response_guidelines>"
        )
        result = self._llm.invoke(prompt)
        return result.content


    def _structure_prompt(self, user_input: str, retrieved_data: Optional[List] = [], tool_results: Optional[List] = [], assistant_message: Optional[Dict] = None) -> List[Dict[str, str]]:
        """
        Structure a prompt for the LLM based on user input and available context.

        :param user_input: The user input query.
        :param retrieved_data: The data retrieved from the Chroma wrapper.
        :param tool_results: The results from the tools used.
        :param assistant_message: The assistant's message containing tool_calls (if any).
        :return: A list of message dictionaries with role and content.
        """
        # Start building the message array
        messages = []
        
        # Add each instruction as a separate system message
        for instruction in self._instructions:
            messages.append({
                "role": "system",
                "content": instruction["message"]
            })
        
        # Add current date/time as system context
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
        
        # Add current user input
        messages.append({
            "role": "user",
            "content": user_input
        })
        
        # Add assistant message with tool_calls if tool results are being provided
        if assistant_message and tool_results:
            messages.append(assistant_message)
        
        # Add tool results if any
        if tool_results:
            for tool_result in tool_results:
                # Format tool result content based on type
                if isinstance(tool_result.get("result"), str):
                    content = tool_result["result"]
                else:
                    content = str(tool_result["result"])
                
                # Add tool message with required fields for OpenAI API
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_result["id"],
                    "content": content
                })
        
        print(f"\n--- Structured Prompt ---\n{messages}\n--- End of Prompt ---\n")  # Debugging purposes
        return messages
    

    def add_instruction(self, instruction: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Adds a system prompt, dubbed instruction.

        :param instruction: Instruction to be stored.
        :param metadata: Optional metadata associated with the instruction.
        """
        if not isinstance(instruction, str):
            raise ValueError("Instruction must be a string.")
        if metadata is not None and not isinstance(metadata, dict):
            raise ValueError("Metadata must be a dictionary or None.")
        
        self._instructions.append({"role": "system", "message": instruction, "metadata": metadata})


    def add_documents(self, path: str = "data", print_statements: bool = False) -> None:
        """
        Adds documents to the Chroma wrapper for retrieval.

        :param path: The path to the directory containing documents.
        :param print_statements: Whether to print statements for debugging.
        """
        if not self._chroma:
            raise ValueError("Chroma wrapper is not available.")
        
        self._chroma.add_documents(path, print_statements)


    def add_tool(self, tool: Tool, **kwargs) -> None:
        """
        Adds a tool to the agent.

        :param tool: An instance of Tool that the agent can use.
        """
        if not isinstance(tool, Tool):
            raise ValueError("Tool must be an instance of Tool.")
        
        # Add instructions for tool usage when the first tool is added
        if not self._tools:
            self.add_instruction(Tool.GENERAL_TOOL_INSTRUCTIONS)

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


    def invoke(self, user_input: str, max_iterations: int = 3) -> Any:
        """
        Processes user input, structures a prompt and invokes the LLM.

        :param user_input: The user input query.
        :param max_iterations: The maximum number of iterations to process tools.
        :return: The LLM's response.
        """
        self._validate_input(user_input)
        if not isinstance(max_iterations, int) or max_iterations <= 0:
            raise ValueError("max_iterations must be a positive integer.")
        
        tool_results = []
        user_input_added_to_memory = False
        assistant_message_with_tool_calls = None
        
        for iteration in range(max_iterations):
            # Get result from LLM
            #print(f"\n--- {self.name} ---\n--- Iteration {iteration + 1} ---")  # Debugging purposes
            prompt = self._structure_prompt(user_input, tool_results=tool_results, assistant_message=assistant_message_with_tool_calls)
            #print(prompt)  # Debugging purposes
            if tool_results: print(Tool.format_tool_calls_short(tool_results))  # Debugging purposes
            result = self._llm.invoke(prompt, use_tools=True)
            # print(f"🤖{self.name}: {result.content}")  # Print the llm's response

            # If no tool calls, this is the final response - store in memory and return
            if not result.additional_kwargs.get("tool_calls"):
                if self._memory and result.content:
                    self._memory.add_message(user_input, "human")
                    self._memory.add_message(result.content, "ai")
                return result
            
            # Tool calls detected - store intermediate AI response in memory
            if result.response_metadata and result.content:
                if self._memory:
                    # Add user input to memory on first iteration only
                    if not user_input_added_to_memory:
                        self._memory.add_message(user_input, "human")
                        user_input_added_to_memory = True
                    self._memory.add_message(result.content, "ai")
            
            # Store the assistant message with tool_calls for the next iteration
            assistant_message_with_tool_calls = {
                "role": "assistant",
                "content": result.content or "",
                "tool_calls": result.additional_kwargs["tool_calls"]
            }
            
            # Print each tool call before calling them
            #for tool_call in result.additional_kwargs["tool_calls"]:
                #print(f"🛠️ Tool call: {tool_call['function']['name']}({tool_call['function']['arguments']})")  # Debugging purposes

            # Process each tool call sequentially
            for tool_call in result.additional_kwargs["tool_calls"]:
                tool_result = Tool.process_tool_call(tool_call, self._tools)
                if tool_result["type"] == "agent_response":
                    tool_result["result"] = tool_result["result"].content
                elif tool_result["type"] == "retriever_response":
                    tool_result["result"] = Chroma_Wrapper.format_data(tool_result["result"])
                tool_results.append(tool_result)
        
        # If max iterations reached, formulate a final response
        #print(f"🤖{self.name}: Maximum iterations ({max_iterations}) reached, formulating final answer...")  # Debugging purposes
        prompt = self._structure_prompt(user_input, tool_results=tool_results, assistant_message=assistant_message_with_tool_calls)
        final_result = self._llm.invoke(prompt, use_tools=False)
        
        # Store final response in memory (user input may already be added if tools were used)
        if self._memory and final_result.content:
            if not user_input_added_to_memory:
                self._memory.add_message(user_input, "human")
            self._memory.add_message(final_result.content, "ai")
        
        return final_result
    

    def stream(self, user_input: str, max_iterations: int = 3) -> Any:
        """
        Processes user input, structures a prompt and streams the LLM.

        :param user_input: The user input query.
        :param max_iterations: The maximum number of iterations to process tools.
        :return: The LLM's response.
        """
        self._validate_input(user_input)
        if not isinstance(max_iterations, int) or max_iterations <= 0:
            raise ValueError("max_iterations must be a positive integer.")

        def update_stage(token: Response, stage: str, tool: Optional[str] = None) -> Response:
            """Helper function to update stage information on tokens"""
            token.stage = stage
            token.tool_name = tool
            return token

        # Start with orchestrator stage
        yield update_stage(Response(""), self.STAGE_ORCHESTRATOR)

        tool_results = []
        user_input_added_to_memory = False
        assistant_message_with_tool_calls = None
        
        for iteration in range(max_iterations):
            # Get result generator from LLM
            #print(f"\n--- {self.name} ---\n--- Iteration {iteration + 1} ---")  # Debugging purposes
            prompt = self._structure_prompt(user_input, tool_results=tool_results, assistant_message=assistant_message_with_tool_calls)
            #print(prompt)  # Debugging purposes
            if tool_results: print(Tool.format_tool_calls_short(tool_results))  # Debugging purposes
            result_generator = self._llm.stream(prompt, use_tools=True)

            # Stream the result token by token and collect tool calls
            result: Optional[Response] = None
            for token in Tool.collect_tool_calls_from_stream(result_generator):
                yield update_stage(token, self.STAGE_THINKING)
                result = token

            # If no tool calls, this is the final response - store in memory and return
            if not result or not result.additional_kwargs or not result.additional_kwargs.get("tool_calls"):
                if self._memory and result and result.response_metadata and result.response_metadata.get("final_response"):
                    self._memory.add_message(user_input, "human")
                    self._memory.add_message(result.response_metadata["final_response"], "ai")
                if result:
                    yield update_stage(result, self.STAGE_CONTENT)
                return result
            
            # Tool calls detected - store intermediate AI response in memory
            if result and result.response_metadata and result.response_metadata["final_response"]:
                if self._memory:
                    # Add user input to memory on first iteration only
                    if not user_input_added_to_memory:
                        self._memory.add_message(user_input, "human")
                        user_input_added_to_memory = True
                    self._memory.add_message(result.response_metadata["final_response"], "ai")
            
            # Store the assistant message with tool_calls for the next iteration
            assistant_message_with_tool_calls = {
                "role": "assistant",
                "content": result.response_metadata.get("final_response", "") if result and result.response_metadata else "",
                "tool_calls": result.additional_kwargs["tool_calls"] if result else []
            }
            
            # Print each tool call before calling them
            #for tool_call in result.additional_kwargs["tool_calls"]:
                #print(f"🛠️ Tool call: {tool_call['function']['name']}({tool_call['function']['arguments']})")  # Debugging purposes
            
            # Process each tool call sequentially
            for tool_call in result.additional_kwargs["tool_calls"]:
                # Enter tool stage for this specific tool
                tool_name = tool_call['function']['name']
                yield update_stage(Response(""), self.STAGE_TOOL, tool_name)
                
                tool_result = Tool.process_tool_call(tool_call, self._tools)
                #print(f"🛠️ Tool result: {tool_result}")  # Debugging purposes
                # Format the tool result based on its type
                if tool_result["type"] == "agent_response":
                    tool_result["result"] = tool_result["result"].content
                elif tool_result["type"] == "retriever_response":
                    tool_result["result"] = Chroma_Wrapper.format_data(tool_result["result"])
                tool_results.append(tool_result)
        
        # If max iterations reached, formulate a final response
        #print(f"🤖{self.name}: Maximum iterations ({max_iterations}) reached, formulating final answer...")  # Debugging purposes
        prompt = self._structure_prompt(user_input, tool_results=tool_results, assistant_message=assistant_message_with_tool_calls)
        
        # Collect final response for memory
        final_response = ""
        for token in self._llm.stream(prompt, use_tools=False):
            final_response += token.content
            yield update_stage(token, self.STAGE_CONTENT)
        
        # Store final response in memory (user input may already be added if tools were used)
        if self._memory and final_response:
            if not user_input_added_to_memory:
                self._memory.add_message(user_input, "human")
            self._memory.add_message(final_response, "ai")
