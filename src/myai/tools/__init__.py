"""Unified entry point for tools and registries."""

from __future__ import annotations

from .base import ToolConfigError, ToolDependencyError, ToolProvider
from .registry import ToolRegistry
from .settings import ToolSettings
from .persistence import MemoryStore, MemoryToolProvider, create_memory_tools
from .search import (
    SearchToolProvider,
    SearchToolkit,
    create_search_toolkit,
    create_search_tools,
)

from myai.paths import DATA_DIR


_DEFAULT_SETTINGS = ToolSettings(data_directory=DATA_DIR)
_MEMORY_BLUEPRINTS = tuple(create_memory_tools(_DEFAULT_SETTINGS))
(
    read_from_memory_tool_blueprint,
    write_to_memory_tool_blueprint,
) = _MEMORY_BLUEPRINTS

_SEARCH_TOOLKIT = create_search_toolkit(_DEFAULT_SETTINGS)
_SEARCH_BLUEPRINTS = tuple(create_search_tools(_DEFAULT_SETTINGS, toolkit=_SEARCH_TOOLKIT))
if not _SEARCH_BLUEPRINTS:
    raise ToolConfigError("No search tool blueprints were created")
google_search_tool_blueprint = _SEARCH_BLUEPRINTS[0]

read_from_memory = read_from_memory_tool_blueprint.function
write_to_memory = write_to_memory_tool_blueprint.function

google_search_simple = _SEARCH_TOOLKIT.google_search_simple
search_alternative = _SEARCH_TOOLKIT.search_alternative
fetch_page_content = _SEARCH_TOOLKIT.fetch_page_content
google_search_enhanced = _SEARCH_TOOLKIT.google_search_enhanced
google_search_api = _SEARCH_TOOLKIT.google_search_api

__all__ = [
    "ToolConfigError",
    "ToolDependencyError",
    "ToolProvider",
    "ToolRegistry",
    "ToolSettings",
    "MemoryStore",
    "MemoryToolProvider",
    "SearchToolProvider",
    "SearchToolkit",
    "create_search_toolkit",
    "create_memory_tools",
    "create_search_tools",
    "read_from_memory_tool_blueprint",
    "write_to_memory_tool_blueprint",
    "google_search_tool_blueprint",
    "read_from_memory",
    "write_to_memory",
    "google_search_simple",
    "search_alternative",
    "fetch_page_content",
    "google_search_enhanced",
    "google_search_api",
]
