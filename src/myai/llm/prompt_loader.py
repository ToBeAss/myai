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
    
    # Flatten all instruction categories into a single list
    all_instructions = []
    for category, instruction_list in instructions_config.items():
        if isinstance(instruction_list, list):
            all_instructions.extend(instruction_list)
    
    return {
        'name': agent_config.get('name', 'Agent'),
        'description': agent_config.get('description', 'You are an AI assistant.'),
        'instructions': all_instructions
    }


def load_instructions_by_category(config_path: Optional[Union[Path, str]] = None) -> Dict[str, List[str]]:
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
