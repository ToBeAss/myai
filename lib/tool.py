import json
import re
from typing import Dict, List, Any, Optional

class Tool:
    """ A class to represent a tool in the assistant. """

    # Instructions for the LLM to follow when using tools
    GENERAL_TOOL_INSTRUCTIONS = """
    You have access to tools that help you perform tasks. Follow these rules carefully:

    - 📌 Choose tool: ALWAYS explain BEFORE you call a tool WHY you plan to use it. DO NOT write more than 1 sentence.

    - 📞 Tool call: ALWAYS create a tool call when you say you are going to use a tool.

    - 🛠 Use tools: If a parameter is MARKED as REQUIRED, you MUST fill it out. If you don't have a value, you should ask the user first.

    - 🔁 Sequential tools: If one tool needs output from another, use them *in two steps*. Call the first tool and wait for the result BEFORE you call the next tool.

    - 🚫 Do not assume results if you have tools available that can answer the question – not even simple calculations like 5 * 5.

    - 🔗 Parallel use: If the tools are not dependent on each other, you can use them simultaneously.

    - 🗣 No tools: If you don't need to use a tool, respond directly without using it.
    """

    # Maximum description length allowed by OpenAI
    MAX_DESCRIPTION_LENGTH = 1024

    # Regex pattern for valid tool names
    VALID_NAME_PATTERN = r'^[a-zA-Z0-9_\.-]+$'

    def __init__(self, name: str, function: callable, description: str):
        """
        Initialize a tool with a name, description, and function.

        :param name: The name of the tool.
        :param function: The function to execute when the tool is called.
        :param description: The description of the function. Include the parameters and their types.
        :raises ValueError: If the resulting description would exceed maximum allowed length.
        """
        self.name = self._validate_name(name)
        self.function = function
        self.description = self._validate_description(description)

    
    def _validate_name(self, name: str) -> str:
        """
        Validates the tool name against the required pattern.
        
        :param name: The name to validate
        :raises ValueError: If the name doesn't match the required pattern
        """
        # Replace spaces with underscores
        name = name.replace(' ', '_')

        # Check if the sanitized name matches the pattern
        if not re.match(self.VALID_NAME_PATTERN, name):
            raise ValueError(
                f"Invalid tool name: '{name}'. Tool names must match pattern '{self.VALID_NAME_PATTERN}'. "
                f"Names can only contain alphanumeric characters, underscores, dots, and hyphens with no spaces."
            )
        return name
    

    def _validate_description(self, description: str) -> str:
        """
        Validates the tool description against the maximum length.
        
        :param description: The description to validate
        :raises ValueError: If the description exceeds the maximum length
        """
        if len(description) > self.MAX_DESCRIPTION_LENGTH:
            raise ValueError(
                f"Tool description of {self.name} exceeds maximum length of {self.MAX_DESCRIPTION_LENGTH} characters. "
                f"Current length: {len(description)}. Please shorten the description."
            )
        return description
    

    def get_tool(self) -> Dict[str, Any]:
        """
        Get the tool details in a dictionary format for the llm to use.
        :return: A dictionary containing the tool's name, description, and function.
        """
        return {
            "name": self.name,
            "description": self.description,
            "function": self.function,
        }
    

    def add_description(self, description: str) -> None:
        """
        Add a description to the tool.
        :param description: The description of the function.
        :raises ValueError: If the resulting description would exceed maximum allowed length.
        """
        new_description = f"{self.description}\n{description}"
        if len(new_description) > self.MAX_DESCRIPTION_LENGTH:
            remaining = self.MAX_DESCRIPTION_LENGTH - len(self.description)
            raise ValueError(
                f"Adding this description to the tool {self.name} would exceed the maximum length of {self.MAX_DESCRIPTION_LENGTH} characters. "
                f"Current length: {len(self.description)}. Remaining characters: {remaining}. "
                f"New content length: {len(description)}."
            )
        self.description = new_description


    @staticmethod
    def _classify_tool_result(tool_result: Any) -> str:
        """
        Classify a tool result based on its origin.
        It can either be a response from an agent, a list of Documents from a retriever, or other results.

        :param tool_result: The result from a tool.
        :return: A string indicating the type of result.
        """
        # Check if the result is from an agent
        if hasattr(tool_result, 'response_metadata') and tool_result.response_metadata:
            # If the result has response metadata, it's likely from an agent
            return "agent_response"
        
        # Check if the result is from a retriever
        elif isinstance(tool_result, list) and len(tool_result) > 0:
            # If the result is a list, check if it contains Document objects
            item = tool_result[0]
            if hasattr(item, "page_content"):
                # Item is a Document object
                return "retriever_response"
            elif isinstance(item, tuple) and len(item) > 0 and hasattr(item[0], 'page_content'):
                # Item is a tuple containing a Document object as first element
                return "retriever_response"
            
        # Otherwise, treat it as a generic result
        return "generic_response"
    

    @staticmethod
    def process_tool_call(tool_call: Dict[str, Any], available_tools: Dict[str, Any]) -> Dict:
        """
        Process a tool call and execute the corresponding function.
        :param tool_call: The tool call to process.
        :param available_tools: The available tools.
        :return: The result of the tool call.
        """
        function_name = tool_call["function"]["name"]
        args = json.loads(tool_call["function"]["arguments"])

        # Execute tool function
        if function_name in available_tools:
            tool_result = available_tools[function_name]["function"](**args)
            result_type = Tool._classify_tool_result(tool_result)
        else:
            tool_result = f"Tool {function_name} not found"
            result_type = "error"
            raise ValueError(f"Function '{function_name}' not found in available tools.")
            
        return {
            "id": tool_call["id"],
            "result": tool_result,
            "function": {
                "name": function_name,
                "arguments": json.dumps(args)
            },
            "type": result_type
        }
    

    @staticmethod
    def collect_tool_calls_from_stream(token_generator: Any):
        """
        Process a token generator from an LLM stream, collecting tool call information.
        
        :param token_generator: Generator yielding tokens from an LLM stream
        :yields: Each token from the original generator
        :returns: The last token with additional tool_calls information attached
        """
        collected_tool_calls = []
        current_tool_call = {}
        current_index = None
        accumulated_args = ""
        final_token = None

        for token in token_generator:
            yield token
            final_token = token

            # Check if token contains tool call chunks
            if not hasattr(token, 'tool_call_chunks') or not token.tool_call_chunks:
                continue
                
            chunk = token.tool_call_chunks[0]
            chunk_index = chunk['index']
            
            # If new tool call detected, finalize previous one
            if chunk_index != current_index:
                if current_index is not None:
                    current_tool_call['function']['arguments'] = accumulated_args
                    collected_tool_calls.append(current_tool_call)
                    accumulated_args = ""
                    
                # Initialize new tool call
                current_tool_call = {
                    "id": chunk['id'],
                    "type": "function",
                    "function": {
                        "name": chunk['name'],
                        "arguments": None,
                    },
                    "index": chunk_index,
                }
                current_index = chunk_index
                
            # Accumulate arguments for current tool call
            accumulated_args += chunk['args']

        # Finalize the last tool call if any
        if current_index is not None:
            current_tool_call['function']['arguments'] = accumulated_args
            collected_tool_calls.append(current_tool_call)
            
            # Attach tool calls to the final token for later processing
            if final_token:
                final_token.additional_kwargs["tool_calls"] = collected_tool_calls

    
    @staticmethod
    def format_tool_calls(tool_calls: List[Dict[str, str]]) -> str:
        """
        Formats a list of tool calls into a string.

        :param tool_calls: A list of tool calls.
        :return: A formatted string containing the tool calls.
        """
        formatted_tool_calls = ""
        for tool_call in tool_calls:
            formatted_tool_calls += f"  <tool_call id='{tool_call['id']}' type='{tool_call['type']}' function='{tool_call['function']}'>\n    {tool_call['result']}\n  </tool_call>\n"
        return formatted_tool_calls
    
    @staticmethod
    def format_tool_calls_short(tool_calls: List[Dict[str, str]]) -> str:
        """
        Formats a list of tool calls into a string.

        :param tool_calls: A list of tool calls.
        :return: A formatted string containing the tool calls.
        """
        formatted_tool_calls = ""
        for tool_call in tool_calls:
            # Parse the arguments from JSON string to dictionary
            args = json.loads(tool_call['function']['arguments'])
            args_str = ", ".join(f"{key}={value}" for key, value in args.items())
            formatted_tool_calls += f"🛠️ {tool_call['function']['name']}({args_str})\n"
        return formatted_tool_calls
    


class ToolBlueprint:
    """
    A blueprint for creating tool instances.
    
    This class provides a factory pattern for creating multiple instances of a similar tool
    with different descriptions for different agents or use cases.
    """

    def __init__(self, name: str, function: callable, base_description: str):
        """
        Initialize a tool blueprint.

        :param name: The base name of the tool.
        :param function: The function to execute when the tool is called.
        :param base_description: The base description of the function.
        """
        self.name = name
        self.function = function
        self.base_description = base_description
    
    def create_tool(self, name_suffix: Optional[str] = "", additional_description: Optional[str] = "", custom_function: Optional[callable] = None) -> Tool:
        """
        Create a new Tool instance from this blueprint.
        
        :param name_suffix: Optional suffix to add to the base name
        :param additional_description: Optional description to add to the base description
        :param custom_function: Optional function to override the blueprint's default function
        :return: A new Tool instance
        """
        # Create a new name with optional suffix
        new_name = self.name
        if name_suffix:
            new_name = f"{new_name}_{name_suffix}"
            
        # Combine descriptions if additional description provided
        description = self.base_description
        if additional_description:
            description = f"{description}\n{additional_description}"
            
        # Use custom function if provided, otherwise use the blueprint's function
        function = custom_function if custom_function is not None else self.function
        
        # Create and return a new Tool instance
        return Tool(new_name, function, description)