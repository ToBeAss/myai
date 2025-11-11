"""Email tool implementations and factories."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional

from myai.llm.tool import ToolBlueprint

from .base import ToolConfigError, ToolDependencyError, ToolProvider
from .registry import ToolRegistry
from .settings import EmailConfig, ToolSettings


@dataclass(frozen=True)
class _ResolvedEmailConfig:
    provider: str
    credentials_path: Optional[str]
    mailbox: str
    label_filters: List[str]


class EmailToolkit:
    """Placeholder email helper until API bindings are supplied."""

    def __init__(self, config: _ResolvedEmailConfig) -> None:
        self._config = config

    def list_recent_messages(self, *, limit: int = 20) -> dict:
        """Retrieve recent messages or raise if auth is unavailable."""
        if not self._config.credentials_path:
            raise ToolDependencyError(
                "Email integration is not yet configured. Provide account credentials to enable message access."
            )

        return {
            "status": "placeholder",
            "message": "Email access is configured but retrieval logic is pending implementation.",
            "limit": limit,
            "mailbox": self._config.mailbox,
            "provider": self._config.provider,
        }


def _resolve_email_config(settings: ToolSettings) -> Optional[_ResolvedEmailConfig]:
    email = settings.email
    if email is None:
        return None

    provider = email.provider.lower()
    if provider not in {"gmail", "icloud", "imap"}:
        raise ToolConfigError(f"Unsupported email provider '{email.provider}'")

    return _ResolvedEmailConfig(
        provider=provider,
        credentials_path=str(email.credentials_path) if email.credentials_path else None,
        mailbox=email.mailbox,
        label_filters=list(email.label_filters),
    )


def create_email_toolkit(settings: ToolSettings) -> Optional[EmailToolkit]:
    config = _resolve_email_config(settings)
    if config is None:
        return None
    return EmailToolkit(config)


def create_email_tools(
    settings: ToolSettings, *, toolkit: Optional[EmailToolkit] = None
) -> Iterable[ToolBlueprint]:
    toolkit = toolkit or create_email_toolkit(settings)
    if toolkit is None:
        return ()

    return (
        ToolBlueprint(
            name="list_recent_email",
            base_description=(
                "List recent messages from the configured mailbox across supported providers.\n\n"
                ":param limit: Maximum number of messages to fetch (optional, defaults to 20)."
            ),
            function=toolkit.list_recent_messages,
        ),
    )


class EmailToolProvider(ToolProvider):
    """Register email tools with a registry when configured."""

    def __init__(self, settings: ToolSettings) -> None:
        self._settings = settings

    def register_tools(self, registry: ToolRegistry) -> None:
        registry.extend(create_email_tools(self._settings))
