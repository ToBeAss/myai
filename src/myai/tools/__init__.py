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
from .calendar import (
    CalendarToolProvider,
    CalendarToolkit,
    create_calendar_toolkit,
    create_calendar_tools,
)
from .email import EmailToolProvider, EmailToolkit, create_email_toolkit, create_email_tools

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

_CALENDAR_TOOLKIT = create_calendar_toolkit(_DEFAULT_SETTINGS)
_CALENDAR_BLUEPRINTS = (
    tuple(create_calendar_tools(_DEFAULT_SETTINGS, toolkit=_CALENDAR_TOOLKIT))
    if _CALENDAR_TOOLKIT
    else ()
)
list_upcoming_events_tool_blueprint = (
    _CALENDAR_BLUEPRINTS[0] if _CALENDAR_BLUEPRINTS else None
)

_EMAIL_TOOLKIT = create_email_toolkit(_DEFAULT_SETTINGS)
_EMAIL_BLUEPRINTS = (
    tuple(create_email_tools(_DEFAULT_SETTINGS, toolkit=_EMAIL_TOOLKIT))
    if _EMAIL_TOOLKIT
    else ()
)
list_recent_email_tool_blueprint = _EMAIL_BLUEPRINTS[0] if _EMAIL_BLUEPRINTS else None

read_from_memory = read_from_memory_tool_blueprint.function
write_to_memory = write_to_memory_tool_blueprint.function

google_search_simple = _SEARCH_TOOLKIT.google_search_simple
search_alternative = _SEARCH_TOOLKIT.search_alternative
fetch_page_content = _SEARCH_TOOLKIT.fetch_page_content
google_search_enhanced = _SEARCH_TOOLKIT.google_search_enhanced
google_search_api = _SEARCH_TOOLKIT.google_search_api

list_upcoming_events = (
    list_upcoming_events_tool_blueprint.function
    if list_upcoming_events_tool_blueprint is not None
    else None
)
list_recent_email = (
    list_recent_email_tool_blueprint.function
    if list_recent_email_tool_blueprint is not None
    else None
)

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
    "CalendarToolProvider",
    "CalendarToolkit",
    "EmailToolProvider",
    "EmailToolkit",
    "create_search_toolkit",
    "create_memory_tools",
    "create_search_tools",
    "create_calendar_toolkit",
    "create_calendar_tools",
    "create_email_toolkit",
    "create_email_tools",
    "read_from_memory_tool_blueprint",
    "write_to_memory_tool_blueprint",
    "google_search_tool_blueprint",
    "list_upcoming_events_tool_blueprint",
    "list_recent_email_tool_blueprint",
    "read_from_memory",
    "write_to_memory",
    "google_search_simple",
    "search_alternative",
    "fetch_page_content",
    "google_search_enhanced",
    "google_search_api",
    "list_upcoming_events",
    "list_recent_email",
]
