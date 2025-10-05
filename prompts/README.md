# Agent Prompts Configuration

This directory contains YAML configuration files that define the agent's identity, behavior, and instructions.

## 📦 Current Version: 1.0.0

**Status**: ✅ Production-Ready  
**Last Updated**: 2025-10-05  
**Instructions**: 16 total across 4 categories  
**Token Count**: ~450 tokens

## Structure

### `sam_config.yaml`
The main configuration file for the Sam AI assistant. It contains:

- **agent**: Agent identity settings
  - `name`: The agent's name
  - `description`: Core identity and purpose description
  
- **instructions**: Behavioral instructions organized by category
  - `general`: Core behavior rules
  - `voice_style`: Voice-specific response formatting
  - `voice_clarity`: Pronunciation and clarity guidelines
  - `voice_conciseness`: Audio-optimized brevity rules

## Usage

### Loading Prompts in Python

```python
from lib.prompt_loader import load_prompts

# Load all prompts
prompts = load_prompts()

# Access the data
agent_name = prompts['name']           # "Sam"
description = prompts['description']   # Full description text
instructions = prompts['instructions'] # List of all instruction strings
```

### Loading Instructions by Category

```python
from lib.prompt_loader import load_instructions_by_category

# Get instructions organized by category
instructions = load_instructions_by_category()

# Access specific categories
general_rules = instructions['general']
voice_style = instructions['voice_style']
```

## Benefits of This Approach

✅ **Separation of Concerns**: Prompts are separate from application logic  
✅ **Easy Updates**: Modify agent behavior without touching code  
✅ **Reusability**: Share prompts across multiple entry points  
✅ **Version Control**: Track prompt changes independently  
✅ **Collaboration**: Non-developers can update prompts safely  
✅ **Testing**: Easy to A/B test different prompt variations  

## Customization

To customize the agent's behavior:

1. Edit `sam_config.yaml`
2. Modify existing instructions or add new categories
3. Restart your application

No code changes needed!

## Example: Adding New Instructions

```yaml
instructions:
  general:
    - "Always respond in English."
    - "Your new instruction here."
  
  custom_category:
    - "Instruction in new category."
```

The loader will automatically flatten all categories into a single list.

---

## 📋 Version Control

Sam's personality configuration uses semantic versioning to track changes and enable easy rollbacks.

### Quick Reference

**Check Current Version:**
```bash
python check_version.py
```

**View Changelog:**
```bash
cat prompts/CHANGELOG.md
```

**Compare Versions:**
```bash
diff prompts/versions/sam_config_v1.0.0.yaml prompts/sam_config.yaml
```

### Files

- **`sam_config.yaml`** - Current active configuration
- **`CHANGELOG.md`** - Version history with detailed changes
- **`VERSION_CONTROL.md`** - Complete versioning workflow guide
- **`versions/`** - Archived configuration versions
- **`check_version.py`** - Version checker script (in root)

### Workflow Summary

1. **Before changes**: Archive current version
2. **Make changes**: Edit `sam_config.yaml`
3. **Test**: Run test suites
4. **Bump version**: Update version number
5. **Document**: Update `CHANGELOG.md`
6. **Archive**: Save new version to `versions/`
7. **Commit**: Git commit with version tag

See `VERSION_CONTROL.md` for complete workflow details.

### Versioning Scheme

- **MAJOR** (X.0.0): Fundamental personality changes
- **MINOR** (1.X.0): New instructions, significant refinements
- **PATCH** (1.0.X): Bug fixes, minor tweaks

### Rollback

If something breaks:
```bash
cp prompts/versions/sam_config_v1.0.0.yaml prompts/sam_config.yaml
```
