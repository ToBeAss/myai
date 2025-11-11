"""Calendar tool implementations and factories."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable, List, Optional

from myai.llm.tool import ToolBlueprint

from .base import ToolConfigError, ToolDependencyError, ToolProvider
from .registry import ToolRegistry
from .settings import CalendarConfig, ToolSettings


@dataclass(frozen=True)
class _ResolvedCalendarConfig:
    credentials_path: Optional[str]
    default_timezone: str
    max_results: int
    scopes: List[str]


class CalendarToolkit:
    """Lightweight calendar helper that will expand once credentials are provided."""

    def __init__(self, config: _ResolvedCalendarConfig) -> None:
        self._config = config

    def list_upcoming_events(self, *, lookahead_hours: int = 24) -> dict:
        """Return upcoming events or an informative placeholder until auth is configured."""
        if not self._config.credentials_path:
            raise ToolDependencyError(
                "Calendar integration is not yet configured. Provide Google credentials to enable queries."
            )

        # Placeholder implementation – actual Google Calendar API integration pending.
        now = datetime.utcnow()
        window_end = now + timedelta(hours=lookahead_hours)
        return {
            "status": "placeholder",
            "message": "Calendar access is configured but retrieval logic is pending implementation.",
            "window_start": now.isoformat() + "Z",
            "window_end": window_end.isoformat() + "Z",
        }


def _resolve_calendar_config(settings: ToolSettings) -> Optional[_ResolvedCalendarConfig]:
    calendar = settings.calendar
    if calendar is None:
        return None

    scopes = list(calendar.scopes)
    if not scopes:
        raise ToolConfigError("Calendar configuration must specify at least one OAuth scope")

    return _ResolvedCalendarConfig(
        credentials_path=str(calendar.credentials_path) if calendar.credentials_path else None,
        default_timezone=calendar.default_timezone,
        max_results=calendar.max_results,
        scopes=scopes,
    )


def create_calendar_toolkit(settings: ToolSettings) -> Optional[CalendarToolkit]:
    config = _resolve_calendar_config(settings)
    if config is None:
        return None
    return CalendarToolkit(config)


def create_calendar_tools(
    settings: ToolSettings, *, toolkit: Optional[CalendarToolkit] = None
) -> Iterable[ToolBlueprint]:
    toolkit = toolkit or create_calendar_toolkit(settings)
    if toolkit is None:
        return ()

    return (
        ToolBlueprint(
            name="list_upcoming_events",
            base_description=(
                "Fetch upcoming calendar events. Requires authenticated Google Calendar credentials.\n\n"
                ":param lookahead_hours: Time window in hours (optional, defaults to 24)."
            ),
            function=toolkit.list_upcoming_events,
        ),
    )


class CalendarToolProvider(ToolProvider):
    """Register calendar tools with a registry when configured."""

    def __init__(self, settings: ToolSettings) -> None:
        self._settings = settings

    def register_tools(self, registry: ToolRegistry) -> None:
        registry.extend(create_calendar_tools(self._settings))
