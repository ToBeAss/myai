"""
Prompt configuration loader for the AI agent.
Loads agent descriptions and instructions from YAML configuration files.
"""

import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
PROMPTS_DIR = REPO_ROOT / "prompts"


def _format_section_name(name: str) -> str:
    """Convert config keys like 'emotional_calibration' into readable headers."""
    return name.replace("_", " ").strip()


def _stringify_value(value: Any) -> str:
    """Render arbitrary YAML values into deterministic, readable text."""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float, bool)) or value is None:
        return str(value)
    if isinstance(value, list):
        return "\n".join(f"- {_stringify_value(item)}" for item in value)
    if isinstance(value, dict):
        lines: List[str] = []
        for key, item in value.items():
            pretty_key = _format_section_name(str(key))
            rendered_item = _stringify_value(item)
            if "\n" in rendered_item:
                lines.append(f"{pretty_key}:\n{rendered_item}")
            else:
                lines.append(f"{pretty_key}: {rendered_item}")
        return "\n".join(lines)
    return str(value)


def _build_instruction_block(section_name: str, section_value: Any) -> str:
    """Create a headed system-prompt block from one instruction subsection."""
    header = _format_section_name(section_name)
    body = _stringify_value(section_value)
    return f"[{header}]\n{body}" if body else f"[{header}]"


def load_prompts(config_path: Optional[Union[Path, str]] = None) -> Dict[str, Any]:
    """
    Load agent prompts and configuration from a YAML file.
    
    Args:
        config_path: Path to the YAML configuration file. 
                    If None, uses the default 'prompts/sam_config.yaml'
    
    Returns:
        Dictionary containing:
            - 'name': Agent name
            - 'description': Agent description
            - 'instructions': List of all instruction strings
    
    Raises:
        FileNotFoundError: If the configuration file doesn't exist
        yaml.YAMLError: If the YAML file is malformed
    """
    # Default to sam_config.yaml in the prompts directory
    if config_path is None:
        config_path = PROMPTS_DIR / "sam_config.yaml"
    
    config_path = Path(config_path)

    # Check if file exists
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    # Load YAML file
    try:
        with config_path.open('r', encoding='utf-8') as file:
            config = yaml.safe_load(file)
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Error parsing YAML configuration: {e}")
    
    # Extract agent information
    agent_config = config.get('agent', {})
    instructions_config = config.get('instructions', {})
    
    # Convert each instruction subsection into a headed string block.
    all_instructions: List[str] = []
    for section_name, section_value in instructions_config.items():
        all_instructions.append(_build_instruction_block(str(section_name), section_value))
    
    return {
        'name': agent_config.get('name', 'Agent'),
        'description': agent_config.get('description', 'You are an AI assistant.'),
        'instructions': all_instructions
    }


def load_instructions_by_category(config_path: Optional[Union[Path, str]] = None) -> Dict[str, Any]:
    """
    Load instructions organized by category for more granular control.
    
    Args:
        config_path: Path to the YAML configuration file.
    
    Returns:
        Dictionary with category names as keys and instruction lists as values.
    """
    if config_path is None:
        config_path = PROMPTS_DIR / "sam_config.yaml"

    config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with config_path.open('r', encoding='utf-8') as file:
        config = yaml.safe_load(file)
    
    return config.get('instructions', {})
