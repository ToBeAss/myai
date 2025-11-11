from pathlib import Path

import pytest  # type: ignore[import]

from myai.tools.base import ToolDependencyError
from myai.tools.calendar import create_calendar_tools
from myai.tools.email import create_email_tools
from myai.tools.settings import CalendarConfig, EmailConfig, ToolSettings


def _settings(tmp_path: Path, **kwargs) -> ToolSettings:
    return ToolSettings(data_directory=tmp_path, **kwargs)


def test_calendar_tools_absent_without_configuration(tmp_path: Path) -> None:
    tools = tuple(create_calendar_tools(_settings(tmp_path)))
    assert tools == ()


def test_calendar_tool_requires_credentials(tmp_path: Path) -> None:
    settings = _settings(tmp_path, calendar=CalendarConfig())
    tools = tuple(create_calendar_tools(settings))
    assert len(tools) == 1

    with pytest.raises(ToolDependencyError):
        tools[0].function()


def test_email_tools_absent_without_configuration(tmp_path: Path) -> None:
    tools = tuple(create_email_tools(_settings(tmp_path)))
    assert tools == ()


def test_email_tool_requires_credentials(tmp_path: Path) -> None:
    settings = _settings(tmp_path, email=EmailConfig(provider="gmail"))
    tools = tuple(create_email_tools(settings))
    assert len(tools) == 1

    with pytest.raises(ToolDependencyError):
        tools[0].function()
