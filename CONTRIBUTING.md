# Contributing to VIMAR By-Me Hub Integration

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to this project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Documentation](#documentation)

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/version/2/1/code_of_conduct/). By participating, you are expected to uphold this code.

## Getting Started

### Prerequisites

- Home Assistant development environment
- Vimar By-me web server (hardware or test instance)
- Python 3.13 or higher
- Git
- Basic understanding of Home Assistant architecture

### Finding Something to Work On

1. Check [open issues](https://github.com/h4de5/home-assistant-vimar/issues)
2. Look for issues labeled `good first issue` or `help wanted`
3. Review the Silver Quality Roadmap for planned features

## Development Setup

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/YOUR_USERNAME/home-assistant-vimar.git
cd home-assistant-vimar
git remote add upstream https://github.com/h4de5/home-assistant-vimar.git
```

### 2. Create Development Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-description
```

### 3. Install Development Environment

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 4. Link to Home Assistant

```bash
# Create symlink to your HA custom_components directory
ln -s $(pwd)/custom_components/vimar /path/to/homeassistant/custom_components/vimar
```

## Making Changes

### Branch Naming Convention

- `feature/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation updates
- `refactor/description` - Code refactoring
- `test/description` - Test additions/modifications

### Commit Message Format

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): subject

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style (formatting)
- `refactor`: Code refactoring
- `perf`: Performance improvement
- `test`: Adding tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(climate): add support for fan speed control

fix(cover): correct position calculation for shutters

docs(readme): update installation instructions

refactor(vimarlink): split connection logic into separate module
```

### Code Style

#### Python Style Guide

- Follow [PEP 8](https://pep8.org/)
- Use type hints wherever possible
- Maximum line length: 120 characters

```python
# Good
def get_device_status(self, object_id: str) -> dict[str, dict[str, str]] | None:
    """Get attribute status for a single device."""
    pass

# Bad
def get_device_status(self, object_id):
    pass
```

#### Documentation Strings

Use clear, concise docstrings:

```python
def complex_function(param1: str, param2: int) -> bool:
    """Brief description of function.
    
    Args:
        param1: Description of param1
        param2: Description of param2
    
    Returns:
        Description of return value
    """
    pass
```

#### Logging

- Use appropriate log levels: `debug`, `info`, `warning`, `error`
- Include context in log messages
- Avoid logging sensitive information

```python
# Good
_LOGGER.debug("Fetching status for device %s", device_id)
_LOGGER.warning("Device %s unavailable, retrying in %ds", device_id, retry_delay)

# Bad
_LOGGER.debug("Getting stuff")
_LOGGER.error("Error!")  # Too vague
```

## Pull Request Process

### Before Submitting

1. **Update Your Branch**
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Update Documentation**
   - Update README.md if adding features
   - Update CHANGELOG.md following [Keep a Changelog](https://keepachangelog.com/)
   - Add inline code comments for complex logic

3. **Test Thoroughly**
   - Test with real Vimar hardware if possible
   - Verify affected platforms work correctly
   - Check for regressions

### Submitting the PR

1. **Push to Your Fork**
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Create Pull Request**
   - Go to GitHub and create a PR from your branch
   - Fill out the PR template completely
   - Link related issues using "Closes #123"

3. **PR Requirements**
   - [ ] Descriptive title and description
   - [ ] Code follows style guidelines
   - [ ] Documentation updated
   - [ ] CHANGELOG.md updated
   - [ ] Tested on real hardware (if applicable)

## Testing

### Manual Testing Checklist

- [ ] Integration loads without errors
- [ ] Configuration flow works
- [ ] Devices are discovered correctly
- [ ] Entity states update properly
- [ ] Controls work (on/off, set values, etc)
- [ ] No excessive logging
- [ ] Error handling works gracefully
- [ ] Integration can be reloaded

### Test with Debug Logging

```yaml
logger:
  default: info
  logs:
    custom_components.vimar: debug
    custom_components.vimar.vimarlink: debug
```

## Documentation

### CHANGELOG Format

```markdown
## [Version] - YYYY-MM-DD

### Added
- New feature description

### Changed
- Modified behavior description

### Fixed
- Bug fix description
```

## Recognition

All contributors are credited in release notes and the README.

Thank you for contributing! 🚀
