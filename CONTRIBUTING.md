# Contributing to Unsplash Wallpaper

Thank you for considering contributing to Unsplash Wallpaper! This document outlines the guidelines for contributing.

## Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).

## How to Contribute

### Reporting Bugs

1. Check the issue tracker to see if the bug has already been reported.
2. If not, open a new issue with:
   - A clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - System information (OS, desktop environment, Python version)
   - Logs from `~/.local/share/unsplash-wallpaper/logs/app.log`

### Suggesting Features

1. Open an issue with the "Feature Request" template.
2. Describe the feature and its use case.
3. Explain how it fits the project's scope.

### Pull Requests

1. Fork the repository.
2. Create a feature branch from `main`.
3. Follow the coding standards (see below).
4. Add tests for your changes.
5. Run all tests before submitting.
6. Update documentation as needed.
7. Submit a pull request with a clear description.

## Development Setup

### Prerequisites

```bash
# Fedora
sudo dnf install python3-devel gtk4-devel libadwaita-devel \
  libappindicator-gtk3-devel libnotify-devel swaybg

# System dependencies
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
pytest

# With coverage
pytest --cov=unsplash_wallpaper

# Run specific test file
pytest tests/test_database.py -v
```

### Code Quality

```bash
# Linting
ruff check src/ tests/

# Type checking
mypy src/unsplash_wallpaper/

# Formatting
ruff format src/ tests/
```

## Coding Standards

- Python 3.13+ required
- Line length: 79 characters
- Type hints required for all functions
- Use `from __future__ import annotations`
- Follow PEP 8 and PEP 484
- No comments unless absolutely necessary
- Use descriptive variable names

## Project Structure

```
src/unsplash_wallpaper/
  __init__.py
  __main__.py
  app.py              # Main application class
  config.py           # Configuration management
  constants.py        # Constants and settings
  database.py         # SQLite database layer
  entry_point.py      # CLI entry point
  models/
    wallpaper.py      # Wallpaper data model
  services/
    history_service.py
    scheduler_service.py
    storage_service.py
    unsplash_service.py
    wallpaper_service.py
  system/
    autostart.py      # Autostart and systemd
  tray/
    tray_manager.py   # System tray
  ui/
    main_window.py
    category_page.py
    history_page.py
    preferences_window.py
```

## Testing Guidelines

- Unit tests go in `tests/` directory
- Mock external services (network, display)
- Test both success and failure paths
- Use pytest fixtures from `conftest.py`
- Aim for >90% code coverage

## Release Process

1. Update version in `constants.py` and `pyproject.toml`
2. Update `CHANGELOG.md`
3. Run full test suite
4. Run linting and type checking
5. Build package: `python -m build`
6. Tag release: `git tag v1.0.0`
7. Push tag and create GitHub release
