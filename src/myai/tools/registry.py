"""Tool registry implementation used to manage available tool blueprints."""

from __future__ import annotations

from typing import Dict, Iterable, Iterator, Mapping, Optional

from myai.llm.tool import ToolBlueprint

from .base import ToolConfigError


class ToolRegistry:
    """Collect and retrieve tool blueprints by name."""

    def __init__(self, *, initial_tools: Optional[Iterable[ToolBlueprint]] = None) -> None:
        self._tools: Dict[str, ToolBlueprint] = {}
        if initial_tools:
            for blueprint in initial_tools:
                self.add(blueprint)

    def add(self, blueprint: ToolBlueprint) -> None:
        """Register a blueprint, ensuring unique tool names."""
        name = blueprint.name
        if name in self._tools:
            raise ToolConfigError(f"Tool '{name}' is already registered")
        self._tools[name] = blueprint

    def extend(self, blueprints: Iterable[ToolBlueprint]) -> None:
        """Register multiple blueprints in sequence."""
        for blueprint in blueprints:
            self.add(blueprint)

    def get(self, name: str) -> ToolBlueprint:
        """Return a previously registered blueprint."""
        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(f"Tool '{name}' is not registered") from exc

    def as_mapping(self) -> Mapping[str, ToolBlueprint]:
        """Expose the registered tool mapping as a read-only view."""
        return dict(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def __iter__(self) -> Iterator[ToolBlueprint]:
        return iter(self._tools.values())
