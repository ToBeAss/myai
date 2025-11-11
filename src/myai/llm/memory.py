from typing import List, Dict, Any, Optional

class Memory:
    """Handles conversation history for an AI agent."""

    def __init__(self, history_limit: int = 10):
        """
        Initializes the memory with a message history limit and a list to store messages.

        :param history_limit: Maximum number of messages to retain.
        """
        if not isinstance(history_limit, int) or history_limit <= 0:
            raise ValueError("history_limit must be a positive integer.")
        
        self._history_limit: int = history_limit
        self._conversation_history: List[Dict[str, str]] = []


    def add_message(self, message: str, role: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Adds a new message to the conversation history.

        :param message: The message content.
        :param role: The role of the message sender ("human", "ai" or "tool").
        """
        if role not in {"human", "ai", "tool"}:
            raise ValueError("role must be 'human', 'ai' or 'tool'.")
        if role == "tool" and not metadata:
            raise ValueError("Tool messages require metadata.")
        
        self._conversation_history.append({"role": role, "message": message, "metadata": metadata})

        # Ensure the history doesn't exceed the limit
        if len(self._conversation_history) > self._history_limit:
            self._conversation_history.pop(0)


    def retrieve_memory(self) -> List[Dict[str, str]]:
        """
        Retrieves stored conversation history.

        :return: A list of dictionaries containing role and message string content.
        """
        return self._conversation_history
    

    @staticmethod
    def format_messages(messages: List[Dict[str, str]]) -> str:
        """
        Formats a list of messages into a string. Also works for instructions.

        :param messages: A list of messages with role and content.
        :return: A formatted string containing the messages.
        """
        formatted_messages = ""
        for msg in messages:
            if msg.get("metadata"):
                formatted_messages += f"  <message role='{msg['role']}' metadata='{msg['metadata']}'>{msg['message']}</message>\n"
            else:
                formatted_messages += f"  <message role='{msg['role']}'>{msg['message']}</message>\n"
        return formatted_messages