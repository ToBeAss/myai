"""Shared abstractions for tool packaging and registration."""

from __future__ import annotations

from typing import Protocol, TYPE_CHECKING


class ToolError(Exception):
    """Base exception for tool related failures."""


class ToolConfigError(ToolError):
    """Raised when a tool receives invalid or incomplete configuration."""


class ToolDependencyError(ToolError):
    """Raised when a runtime dependency required by a tool is missing."""


if TYPE_CHECKING:  # pragma: no cover - avoid circular imports at runtime
    from .registry import ToolRegistry


class ToolProvider(Protocol):
    """Interface for objects that can register one or more tool blueprints."""

    def register_tools(self, registry: "ToolRegistry") -> None:
        """Register the provider's tools with the given registry."""
        ...
