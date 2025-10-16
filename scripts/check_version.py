#!/usr/bin/env python3
"""
Sam Configuration Version Checker
Displays current version information and validates configuration.
"""

import yaml
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROMPTS_DIR = PROJECT_ROOT / "prompts"

def load_config():
    """Load the Sam configuration file."""
    config_path = PROMPTS_DIR / "sam_config.yaml"
    
    if not config_path.exists():
        print("❌ Configuration file not found!")
        return None
    
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def count_instructions(config):
    """Count total instructions across all categories."""
    if 'instructions' not in config:
        return 0
    
    total = 0
    for category, instructions in config['instructions'].items():
        total += len(instructions)
    return total

def estimate_tokens(config):
    """Rough estimate of token count."""
    config_str = yaml.dump(config)
    # Rough estimate: ~4 characters per token
    return len(config_str) // 4

def check_version():
    """Display version information."""
    print("🔍 Sam Configuration Version Checker")
    print("=" * 60)
    
    config = load_config()
    if not config:
        return
    
    # Version info
    version = config.get('version', 'Unknown')
    print(f"\n📦 Current Version: {version}")
    
    # Agent info
    agent_name = config.get('agent', {}).get('name', 'Unknown')
    print(f"🤖 Agent Name: {agent_name}")
    
    # Instruction counts
    instruction_count = count_instructions(config)
    print(f"\n📋 Total Instructions: {instruction_count}")
    
    if 'instructions' in config:
        for category, instructions in config['instructions'].items():
            print(f"   - {category}: {len(instructions)} instructions")
    
    # Token estimate
    token_estimate = estimate_tokens(config)
    print(f"\n🔢 Estimated Tokens: ~{token_estimate}")
    
    # Archived versions
    versions_dir = PROMPTS_DIR / "versions"
    if versions_dir.exists():
        archived = list(versions_dir.glob("sam_config_v*.yaml"))
        print(f"\n📁 Archived Versions: {len(archived)}")
        for version_file in sorted(archived):
            print(f"   - {version_file.name}")
    
    print("\n" + "=" * 60)
    print("✅ Configuration validated successfully!")
    
    # Tips
    print("\n💡 Quick Commands:")
    print("   - View changelog: cat prompts/CHANGELOG.md")
    print("   - Compare versions: diff prompts/versions/sam_config_v1.0.0.yaml prompts/sam_config.yaml")
    print("   - Run tests: python -m pytest tests/test_personality_scenarios.py")
    print()

if __name__ == "__main__":
    check_version()
