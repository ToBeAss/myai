# Sam Configuration Version Control Guide

## 📋 Overview

This guide explains how to manage versions of Sam's personality configuration.

---

## 🔢 Versioning Scheme

We use **Semantic Versioning** (MAJOR.MINOR.PATCH):

### When to Bump Versions

**MAJOR (X.0.0)** - Breaking changes:
- Complete personality rewrite
- Fundamental trait changes (e.g., removing sarcasm)
- Incompatible configuration structure changes
- Target model change (GPT-4o-mini → Claude Sonnet)

**MINOR (1.X.0)** - Backward-compatible additions:
- Adding new instruction categories
- Significant refinements to existing traits
- New features or capabilities
- Token optimization >10%

**PATCH (1.0.X)** - Bug fixes and tweaks:
- Wording improvements
- Minor guard strengthening
- Fixing false positives/negatives
- Documentation updates

---

## 📁 File Structure

```
prompts/
├── sam_config.yaml           # Current active configuration
├── CHANGELOG.md              # Version history and changes
├── VERSION_CONTROL.md        # This file
└── versions/                 # Archived versions
    ├── sam_config_v1.0.0.yaml
    ├── sam_config_v1.1.0.yaml
    └── ...
```

---

## 🔄 Workflow for Making Changes

### 1. Before Making Changes

```bash
# Create a backup of current version
cp prompts/sam_config.yaml prompts/versions/sam_config_v$(grep '^version:' prompts/sam_config.yaml | cut -d'"' -f2).yaml

# Create a git branch for your changes (optional but recommended)
git checkout -b personality/feature-name
```

### 2. Make Your Changes

Edit `prompts/sam_config.yaml` with your improvements.

### 3. Test Thoroughly

```bash
# Run test suites
python test_personality_scenarios.py
python test_personality_edge_cases.py

# Manual testing with both modes
python main.py  # Test in both text and voice modes
```

### 4. Update Version Number

Decide on version bump (MAJOR, MINOR, or PATCH) and update in `sam_config.yaml`:

```yaml
version: "1.1.0"  # Example: MINOR version bump
```

### 5. Document Changes

Update `prompts/CHANGELOG.md`:

```markdown
## [1.1.0] - 2025-10-XX

### Added
- New instruction for handling X scenario

### Changed
- Refined Y instruction for better clarity

### Fixed
- False positive issue with Z feature
```

### 6. Archive the New Version

```bash
# Save the new version
cp prompts/sam_config.yaml prompts/versions/sam_config_v1.1.0.yaml
```

### 7. Commit and Tag

```bash
# Commit changes
git add prompts/sam_config.yaml prompts/CHANGELOG.md prompts/versions/
git commit -m "feat: Sam personality v1.1.0 - [brief description]"

# Tag the version
git tag -a v1.1.0 -m "Sam personality configuration v1.1.0"

# Push changes and tags
git push origin main
git push origin v1.1.0
```

---

## ⏪ Rolling Back to Previous Version

If a version causes issues, roll back quickly:

### Method 1: From Archive

```bash
# Copy archived version back
cp prompts/versions/sam_config_v1.0.0.yaml prompts/sam_config.yaml

# Update changelog
# Add rollback note to CHANGELOG.md

# Commit the rollback
git add prompts/sam_config.yaml prompts/CHANGELOG.md
git commit -m "revert: Rollback to Sam personality v1.0.0"
```

### Method 2: From Git Tag

```bash
# Checkout specific version from git
git checkout v1.0.0 -- prompts/sam_config.yaml

# Commit the rollback
git commit -m "revert: Rollback to Sam personality v1.0.0"
```

---

## 📊 Version Comparison

To compare versions:

```bash
# Compare two archived versions
diff prompts/versions/sam_config_v1.0.0.yaml prompts/versions/sam_config_v1.1.0.yaml

# Compare current with specific version
diff prompts/versions/sam_config_v1.0.0.yaml prompts/sam_config.yaml

# Compare using git tags
git diff v1.0.0..v1.1.0 -- prompts/sam_config.yaml
```

---

## 🧪 Testing Checklist Before Release

Before bumping to a new version, ensure:

- [ ] All test suites pass (`test_personality_scenarios.py`, `test_personality_edge_cases.py`)
- [ ] Manual testing in both text and voice modes
- [ ] No false positives or hallucinations
- [ ] Token count documented
- [ ] Personality score assessed
- [ ] CHANGELOG.md updated
- [ ] Version number updated in `sam_config.yaml`
- [ ] New version archived in `versions/` folder
- [ ] Git commit and tag created

---

## 📈 Tracking Metrics Across Versions

Keep track of key metrics in CHANGELOG.md:

- **Token Count**: Monitor configuration size
- **Instruction Count**: Track complexity
- **Test Pass Rate**: Ensure quality
- **Personality Score**: Subjective quality assessment
- **False Positive Rate**: Critical trust metric

---

## 🔍 Version History Quick Reference

```bash
# List all versions
git tag -l "v*"

# Show version details
git show v1.0.0

# List archived versions
ls -lh prompts/versions/
```

---

## 💡 Best Practices

1. **Never skip testing** - Always run full test suite before release
2. **Document everything** - Future you will thank present you
3. **Archive before changes** - Can't roll back what wasn't saved
4. **Use descriptive commits** - Makes git history useful
5. **Test in production-like conditions** - Voice mode is the primary use case
6. **Version incrementally** - Small, tested changes are safer
7. **Keep metrics** - Track token count, personality score, test results

---

## 🚨 Emergency Rollback

If production breaks:

```bash
# Quick rollback to last known good version
cp prompts/versions/sam_config_v1.0.0.yaml prompts/sam_config.yaml

# Restart the application
# No git commit needed until you're sure it's fixed
```

---

## 📝 Notes

- The `version` field in `sam_config.yaml` is informational only (not parsed by code)
- Git tags are the source of truth for version history
- Keep at least 3 previous versions in the archive
- Consider creating release notes for MAJOR versions

---

*Last Updated: 2025-10-05*
