from typing import List, Dict, Any, Optional

# IMPLEMENT VECTOR STORE IN MEMORY

class Memory:
    """Handles conversation history for an AI agent."""

    def __init__(self, history_limit: int = 20):
        """
        Initializes the memory with a message history limit and a list to store messages.

        :param history_limit: Maximum number of messages to retain.
        """
        if not isinstance(history_limit, int) or history_limit <= 0:
            raise ValueError("history_limit must be a positive integer.")
        
        self._history_limit: int = history_limit
        self._conversation_history: List[Dict[str, Any]] = []


    def add_message(self, message: str, role: str) -> None:
        """
        Adds a new message to the conversation history.

        :param message: The message content.
        :param role: The role of the message sender ("human", "ai" or "tool").
        """
        if role not in {"human", "ai", "tool"}:
            raise ValueError("role must be 'human', 'ai' or 'tool'.")
        
        self._conversation_history.append({"role": role, "content": message})
    
        # Ensure the history doesn't exceed the limit
        if len(self._conversation_history) > self._history_limit:
            self._conversation_history.pop(0)


    def retrieve_memory(self) -> List[Dict[str, Any]]:
        """
        Retrieves stored conversation history.

        :return: The conversation history.
        """
        return self._conversation_history
