"""Configuration containers shared across tool domains."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True)
class ToolSettings:
    """Global settings passed into tool factories."""

    data_directory: Path
    http_timeout: float = 10.0
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    extra_http_headers: Mapping[str, str] = field(default_factory=dict)
