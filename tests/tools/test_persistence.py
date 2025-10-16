from pathlib import Path

import pytest  # type: ignore[import]

from myai.tools.base import ToolDependencyError
from myai.tools.persistence import create_memory_tools
from myai.tools.settings import ToolSettings


def _build_memory_blueprints(tmp_path: Path):
    settings = ToolSettings(data_directory=tmp_path)
    return tuple(create_memory_tools(settings))


def test_read_from_memory_returns_empty_payload_when_file_missing(tmp_path):
    read_blueprint, _ = _build_memory_blueprints(tmp_path)

    payload = read_blueprint.function()

    assert payload == {"memories": []}


def test_write_to_memory_appends_entries_and_increments_ids(tmp_path):
    read_blueprint, write_blueprint = _build_memory_blueprints(tmp_path)

    confirmation = write_blueprint.function(content="First entry", memory_type="project")
    assert confirmation.startswith("Memory saved with ID 1")

    second_confirmation = write_blueprint.function(content="Second entry")
    assert second_confirmation.startswith("Memory saved with ID 2")

    payload = read_blueprint.function()

    assert "memories" in payload
    assert len(payload["memories"]) == 2
    assert payload["memories"][0]["content"] == "First entry"
    assert payload["memories"][0]["type"] == "project"
    assert payload["memories"][1]["content"] == "Second entry"
    assert {entry["id"] for entry in payload["memories"]} == {1, 2}


def test_read_from_memory_raises_on_invalid_json(tmp_path):
    memory_file = tmp_path / "memory.json"
    memory_file.write_text("{invalid json}")

    read_blueprint, _ = _build_memory_blueprints(tmp_path)

    with pytest.raises(ToolDependencyError):
        read_blueprint.function()
