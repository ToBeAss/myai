from typing import List, Dict, Any, Optional
import json
import uuid
from datetime import datetime
from pathlib import Path

# IMPLEMENT VECTOR STORE IN MEMORY

class Memory:
    """Handles conversation history for an AI agent."""

    def __init__(self, history_limit: int = 20, log_dir: Optional[str] = None, auto_save: bool = True, metadata: Optional[Dict[str, Any]] = None, load_previous: bool = True):
        """
        Initializes the memory with a message history limit and a list to store messages.

        :param history_limit: Maximum number of messages to retain.
        :param log_dir: Base directory for conversation logs. Defaults to 'data/conversations'.
        :param auto_save: Whether to automatically save messages to log file on each add.
        :param metadata: Optional metadata for this session (e.g., user, personality).
        :param load_previous: Whether to automatically load the most recent conversation log.
        """
        if not isinstance(history_limit, int) or history_limit <= 0:
            raise ValueError("history_limit must be a positive integer.")
        
        self._history_limit: int = history_limit
        self._conversation_history: List[Dict[str, Any]] = []
        self._auto_save: bool = auto_save
        self._metadata: Dict[str, Any] = metadata or {}
        self._history_loaded: bool = False
        
        # Session tracking for logging
        self._session_id: str = str(uuid.uuid4())
        self._session_start: datetime = datetime.now()
        
        # Set up logging directory
        if log_dir is None:
            # Default to data/conversations relative to project root
            project_root = Path(__file__).parent.parent.parent.parent
            self._log_dir = project_root / "data" / "conversations"
        else:
            self._log_dir = Path(log_dir)
        
        # Create log file path for this session (created on first message)
        self._current_log_file: Optional[Path] = None
        
        # Load previous conversation if requested
        if load_previous:
            self.load_conversation_history()


    def add_message(self, message: str, role: str) -> None:
        """
        Adds a new message to the conversation history.

        :param message: The message content.
        :param role: The role of the message sender ("human", "ai" or "tool").
        """
        if role not in {"human", "ai", "tool"}:
            raise ValueError("role must be 'human', 'ai' or 'tool'.")
        
        timestamp = datetime.now().isoformat()
        msg_dict = {
            "role": role, 
            "content": message,
            "timestamp": timestamp
        }
        
        # Add to conversation history (for LLM)
        self._conversation_history.append(msg_dict)
    
        # Ensure the history doesn't exceed the limit
        if len(self._conversation_history) > self._history_limit:
            self._conversation_history.pop(0)
        
        # Auto-save if enabled (saves only this message to log)
        if self._auto_save:
            self._auto_save_to_log(msg_dict)


    def retrieve_memory(self, for_llm: bool = True) -> List[Dict[str, Any]]:
        """
        Retrieves stored conversation history, optionally formatted for LLM with temporal context.

        :param for_llm: If True, adds human-readable time context and removes timestamp field.
        :return: The conversation history.
        """
        if not for_llm:
            return self._conversation_history
        
        # Format messages with temporal context for LLM
        now = datetime.now()
        formatted_messages = []
        
        for msg in self._conversation_history:
            msg_time = datetime.fromisoformat(msg["timestamp"])
            time_diff = now - msg_time
            
            # Format time difference in human-readable way
            if time_diff.total_seconds() < 60:
                time_context = "just now"
            elif time_diff.total_seconds() < 3600:
                minutes = int(time_diff.total_seconds() / 60)
                time_context = f"{minutes} minute{'s' if minutes != 1 else ''} ago"
            elif time_diff.total_seconds() < 86400:
                hours = int(time_diff.total_seconds() / 3600)
                time_context = f"{hours} hour{'s' if hours != 1 else ''} ago"
            else:
                days = int(time_diff.total_seconds() / 86400)
                time_context = f"{days} day{'s' if days != 1 else ''} ago"
            
            # Add temporal context to message content
            formatted_messages.append({
                "role": msg["role"],
                "content": f"[{time_context}] {msg['content']}"
            })
        
        return formatted_messages
    

    def _auto_save_to_log(self, new_message: Dict[str, Any]) -> None:
        """
        Internal method to append a single message to the session log file.
        Creates log file on first message, appends to it on subsequent messages.
        
        :param new_message: The message dict to append to the log.
        """
        # Create log file path on first message
        if self._current_log_file is None:
            now = datetime.now()
            month_dir = self._log_dir / now.strftime("%Y-%m")
            month_dir.mkdir(parents=True, exist_ok=True)
            
            # Use session start time for filename to keep it consistent
            filename = self._session_start.strftime("%Y-%m-%d_%H%M%S.json")
            self._current_log_file = month_dir / filename
            
            # Initialize empty log file
            log_data = {
                "session_id": self._session_id,
                "start_time": self._session_start.isoformat(),
                "last_updated": datetime.now().isoformat(),
                "messages": [],
                "metadata": {
                    "message_count": 0,
                    **self._metadata
                }
            }
            with open(self._current_log_file, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, indent=2, ensure_ascii=False)
        
        # Read existing log
        with open(self._current_log_file, 'r', encoding='utf-8') as f:
            log_data = json.load(f)
        
        # Append new message
        log_data["messages"].append(new_message)
        log_data["last_updated"] = datetime.now().isoformat()
        log_data["metadata"]["message_count"] = len(log_data["messages"])
        
        # Write back to file
        with open(self._current_log_file, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
    

    def save_conversation_log(self, metadata: Optional[Dict[str, Any]] = None) -> Optional[Path]:
        """
        Manually updates metadata for the current session log file.
        
        :param metadata: Optional metadata to merge with session metadata.
        :return: Path to the log file, or None if no log file exists yet.
        """
        # Merge any additional metadata
        if metadata:
            self._metadata.update(metadata)
            
            # Update log file if it exists
            if self._current_log_file and self._current_log_file.exists():
                with open(self._current_log_file, 'r', encoding='utf-8') as f:
                    log_data = json.load(f)
                
                log_data["metadata"].update(metadata)
                
                with open(self._current_log_file, 'w', encoding='utf-8') as f:
                    json.dump(log_data, f, indent=2, ensure_ascii=False)
        
        return self._current_log_file
    

    def load_conversation_history(self) -> bool:
        """
        Loads messages from the most recent conversation log to maintain continuity.
        Finds the most recent log file by filename and loads all its messages
        (up to history_limit).
        
        :return: True if messages were loaded, False if no logs exist.
        """
        # Find all log files and get the most recent one
        log_files = sorted(self._log_dir.glob("*/*.json"), reverse=True)
        
        if not log_files:
            self._history_loaded = True
            return False
        
        # Load the most recent log file
        most_recent_log = log_files[0]
        
        try:
            with open(most_recent_log, 'r', encoding='utf-8') as f:
                data = json.load(f)
                messages = data['messages']
                
                # Take up to history_limit messages (all if fewer than limit)
                self._conversation_history = messages[-self._history_limit:]
                self._history_loaded = True
                
                return True
        except (json.JSONDecodeError, KeyError):
            # If most recent file is corrupted, don't load anything
            self._history_loaded = True
            return False
