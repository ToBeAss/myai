"""Persistence-focused tool factories."""

from __future__ import annotations

import json
from collections.abc import MutableMapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, TypedDict

from myai.llm.tool import ToolBlueprint

from .base import ToolConfigError, ToolDependencyError, ToolProvider
from .registry import ToolRegistry
from .settings import ToolSettings

MEMORY_FILENAME = "memory.json"
TIMESTAMP_FORMAT = "%d.%m.%Y %H:%M"
READ_MEMORY_DESCRIPTION = """
    Use this tool to gather memories from previous conversations.
    The memories are summaries of Tobias's past interactions and experiences, made by you, the AI.
    In any situation where you need to recall past interactions or information about Tobias, or if you think it might be relevant, you can use this tool to access the relevant memories.

    :return: A JSON object containing the memories.
    """
WRITE_MEMORY_DESCRIPTION = """
    Use this tool to save important information or memories from the current conversation.
    Store significant facts, preferences, decisions, experiences, or insights about Tobias that should be remembered for future interactions.
    Examples: personal preferences, project updates, important decisions, or noteworthy experiences.

    :param content: The memory content to store (required)
    :param memory_type: The type of memory - 'personal', 'project', 'preference', etc. (optional, defaults to 'general')
    :return: Confirmation message with the saved memory ID
    """


class MemoryEntry(TypedDict):
    """Representation of a single memory entry."""

    id: int
    timestamp: str
    type: str
    content: str


MemoryPayload = Dict[str, Any]


def _ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


@dataclass
class MemoryStore:
    """Persist and retrieve conversation memories."""

    data_directory: Path

    def __post_init__(self) -> None:
        if not isinstance(self.data_directory, Path):
            raise ToolConfigError("data_directory must be a pathlib.Path instance")
        _ensure_directory(self.data_directory)
        self._memory_file = self.data_directory / MEMORY_FILENAME

    def read(self) -> MemoryPayload:
        """Return the full memory payload from disk."""
        try:
            with self._memory_file.open("r", encoding="utf-8") as handle:
                data: Any = json.load(handle)
        except FileNotFoundError:
            return {"memories": []}
        except json.JSONDecodeError as exc:
            raise ToolDependencyError(
                f"Memory file '{self._memory_file}' contains invalid JSON"
            ) from exc

        if not isinstance(data, MutableMapping):
            raise ToolDependencyError(
                f"Memory file '{self._memory_file}' must contain a JSON object"
            )

        memories = data.get("memories")
        if memories is None:
            data["memories"] = []
        elif not isinstance(memories, list):
            raise ToolDependencyError(
                f"Memory file '{self._memory_file}' has an invalid 'memories' section"
            )

        return dict(data)

    def write(self, content: str, memory_type: str = "general") -> str:
        """Persist a new memory entry to disk and return a confirmation message."""
        payload = dict(self.read())
        memories = payload.get("memories", [])
        if not isinstance(memories, list):
            raise ToolDependencyError(
                f"Memory file '{self._memory_file}' has an invalid 'memories' section"
            )

        next_id = self._next_id(memories)
        new_entry: MemoryEntry = {
            "id": next_id,
            "timestamp": datetime.now().strftime(TIMESTAMP_FORMAT),
            "type": memory_type,
            "content": content,
        }

        memories.append(new_entry)
        payload["memories"] = memories
        _ensure_directory(self.data_directory)
        with self._memory_file.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=4)

        return f"Memory saved with ID {next_id}: {content}"

    @staticmethod
    def _next_id(memories: List[Any]) -> int:
        candidate_ids = [
            entry["id"]
            for entry in memories
            if isinstance(entry, dict) and isinstance(entry.get("id"), int)
        ]
        return (max(candidate_ids) if candidate_ids else 0) + 1


def create_memory_tools(settings: ToolSettings) -> Iterable[ToolBlueprint]:
    """Construct tool blueprints responsible for memory persistence."""
    store = MemoryStore(settings.data_directory)

    def read_from_memory() -> MemoryPayload:
        """Load saved conversation memories."""
        return store.read()

    def write_to_memory(content: str, memory_type: str = "general") -> str:
        """Store a new conversation memory."""
        return store.write(content=content, memory_type=memory_type)

    return (
        ToolBlueprint(
            name="read_from_memory",
            base_description=READ_MEMORY_DESCRIPTION.strip(),
            function=read_from_memory,
        ),
        ToolBlueprint(
            name="write_to_memory",
            base_description=WRITE_MEMORY_DESCRIPTION.strip(),
            function=write_to_memory,
        ),
    )


class MemoryToolProvider(ToolProvider):
    """Register memory related tools with a registry."""

    def __init__(self, settings: ToolSettings) -> None:
        self._settings = settings

    def register_tools(self, registry: ToolRegistry) -> None:
        registry.extend(create_memory_tools(self._settings))
