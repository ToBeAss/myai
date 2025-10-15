import os, time
from dotenv import load_dotenv
from typing import Any, Optional, Dict, List
from langchain_openai import AzureChatOpenAI, ChatOpenAI
from openai import BadRequestError, APIConnectionError
# You can import other models here in the future (e.g., OpenAI, HuggingFace)


class Response:
    """
    A simple wrapper class to standardize responses from the model.

    This class ensures that both successful responses and error messages
    have a `content` attribute, preventing attribute errors in downstream processing.

    :param content: The text content of the response, either from the model or an error message.
    """
    def __init__(self, content: str, response_metadata: Optional[Dict] = None, additional_kwargs: Optional[Dict] = None):
        self.content = content
        self.response_metadata = response_metadata
        self.additional_kwargs = additional_kwargs


class LLM_Wrapper:
    """A wrapper class for interacting with various language models."""

    def __init__(self, model_name: str = "openai-gpt-4.1-mini", **kwargs):
        """
        Initializes the LLM Wrapper.

        :param model_name: The given name of the desired language model.
        :param model: An instance of a language model.
        """
        if not isinstance(model_name, str):
            raise TypeError("Model name must be a string")
        
        load_dotenv(override=True) # Load environment variables from .env file, overriding existing ones

        self._model_name = model_name
        self._model = self._init_model(model_name, **kwargs)
        self._model_with_tools = None


    def _init_model(self, model_name: str, **kwargs) -> Any:
        """
        Initialize the language model based on the given model name.
        
        :param model_name: The given name of the desired language model.
        :return: The initialized language model.
        """
        if model_name == "azure-gpt-4o":
            return AzureChatOpenAI(
                azure_deployment = "gpt-4o",
                api_version = "2024-10-21",
                api_key = os.getenv("AZURE_OPENAI_API_KEY"),
                azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT"),
                **kwargs # Pass additional parameters
            )
        elif model_name == "openai-gpt-4.1":
            return ChatOpenAI(
                model_name = "gpt-4.1",
                api_key = os.getenv("OPENAI_API_KEY"),
                **kwargs # Pass additional parameters
            )
        elif model_name == "openai-gpt-4.1-mini":
            return ChatOpenAI(
                model_name = "gpt-4.1-mini",
                api_key = os.getenv("OPENAI_API_KEY"),
                **kwargs # Pass additional parameters
            )
        elif model_name == "openai-gpt-4.1-nano":
            return ChatOpenAI(
                model_name = "gpt-4.1-nano",
                api_key = os.getenv("OPENAI_API_KEY"),
                **kwargs # Pass additional parameters
            )
        else: 
            raise ValueError(f"Unsupported language model: {model_name}")
        

    def _handle_error(self, error: Exception) -> Response:
        """
        Handle the error and return a standardized response.

        :param error: The error that occurred.
        :return: A standardized response.
        """
        if isinstance(error, APIConnectionError):
            print(f"APIConnectionError: {error}")
            return Response("Unable to connect to the model. Make sure you have the required API key and endpoint.")
        elif isinstance(error, BadRequestError):
            print(f"BadRequestError: {error}")
            # Attempt to extract content filtering details
            try:
                error_data = error.response.json()
                content_filter_result = error_data.get("error", {}).get("innererror", {}).get("content_filter_result", {})

                # Identify which filters were triggered
                filters_triggered = [category for category, details in content_filter_result.items() if details.get("filtered", False)]

                if filters_triggered:
                    return Response(f"Request blocked due to content filtering in the following categories: {', '.join(filters_triggered)}.")
            except Exception:
                pass # Fallback to generic message if parsing fails

            return Response("Request blocked by content filtering. Modify the prompt and try again.")
        else:
            print(f"Unexpected error: {error}")
            return Response("An unexpected error occurred. Please try again later.")


    def bind_tools(self, tools: List[callable], **kwargs) -> None:
        """
        Bind a list of tools to the language model.
        
        :param tools: A list of tool functions.
        :return: The language model with the bound tools.
        """
        if not isinstance(tools, list):
            raise TypeError("Tools must be a list of functions")
        self._model_with_tools = self._model.bind_tools(tools, **kwargs)
        

    def invoke(self, prompt: str, use_tools: bool = True) -> Any:
        """
        Invoke the model with a given prompt.

        :param prompt: The given prompt.
        :return: The LLM's response.
        """
        try:
            if use_tools and self._model_with_tools:
                return self._model_with_tools.invoke(prompt)
            else:
                return self._model.invoke(prompt)
        except Exception as e:
            return self._handle_error(e)
        

    def stream(self, prompt: str, use_tools: bool = True) -> Any:
        """
        Stream tokens from the model with a given prompt.

        :param prompt: The given prompt.
        :return: Generator yielding tokens.
        """
        try:
            final_response = ""
            start_time = time.time()

            if use_tools and self._model_with_tools:
                generator = self._model_with_tools.stream(prompt)
            else:
                generator = self._model.stream(prompt)

            for token in generator:
                final_response += token.content
                if token.response_metadata:
                    token.response_metadata['response_time'] = time.time() - start_time
                    token.response_metadata['final_response'] = final_response
                    #token.content += "\n\n"
                yield token
                
        except Exception as e:
            yield self._handle_error(e)
        
    def stream_with_tools(self, prompt: str) -> Any:
        """
        Stream tokens from the model with a given prompt and bound tools.

        :param prompt: The given prompt.
        :return: Generator yielding tokens.
        """
        try:
            final_response = ""
            start_time = time.time()
            for token in self._model_with_tools.stream(prompt):
                final_response += token.content
                if token.response_metadata:
                    token.response_metadata['response_time'] = time.time() - start_time
                    token.response_metadata['final_response'] = final_response
                    #token.content += "\n\n"
                yield token
        except Exception as e:
            yield self._handle_error(e)


    def stream_error_message(self, error_message: str):
        """
        Stream an error message.

        :param error_message: The error message to stream.
        :return: A generator yielding the error message.
        """
        for word in error_message.split():
            yield Response(word + " ")