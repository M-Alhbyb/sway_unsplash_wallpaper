# Unsplash Wallpaper

> Automatic Unsplash wallpaper changer for Linux desktop environments.

[![Tests](https://github.com/unsplash-wallpaper/unsplash-wallpaper/actions/workflows/tests.yml/badge.svg)](https://github.com/unsplash-wallpaper/unsplash-wallpaper/actions/workflows/tests.yml)
[![Release](https://github.com/unsplash-wallpaper/unsplash-wallpaper/actions/workflows/release.yml/badge.svg)](https://github.com/unsplash-wallpaper/unsplash-wallpaper/actions/workflows/release.yml)
[![License: GPL v2](https://img.shields.io/badge/License-GPL%20v2-blue.svg)](LICENSE)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](pyproject.toml)

Unsplash Wallpaper downloads high-resolution photos from [Unsplash](https://unsplash.com) and sets them as your desktop wallpaper on a configurable schedule. It features a modern GTK4 + Libadwaita GUI, system tray support, and full systemd integration.

## Features

| Feature | Description |
|---------|-------------|
| **Automatic Downloads** | Fetches fresh wallpapers from Unsplash on a schedule |
| **Scheduled Changes** | Configurable intervals from 15 minutes to 24 hours |
| **Category Selection** | Choose from 10 curated categories (nature, tech, space, cars, architecture, minimal, mountains, forests, city, gaming) |
| **Custom Keywords** | Search wallpapers by your own keywords |
| **No Repetition** | Tracks download history to avoid duplicate wallpapers |
| **Wallpaper History** | Browse, re-apply, or delete past wallpapers |
| **GTK4 + Libadwaita UI** | Modern, responsive desktop interface with dark/light/system theme |
| **System Tray** | Background operation with AyatanaAppIndicator tray icon |
| **Desktop Notifications** | Native notifications on wallpaper changes |
| **Multiple Resolutions** | HD, Full HD, 2K, 4K, or original resolution |
| **Auto Start** | Optional XDG autostart and systemd user service |
| **Daemon Mode** | Headless operation for servers or minimal setups |
| **First-Run Wizard** | Guided API key setup on first launch |
| **Diagnostics** | Built-in diagnostics report (`--diagnostics`) |
| **Crash Handler** | Desktop notification on unexpected crashes |
| **Secrets Masking** | API keys automatically masked in log files |
| **Sway Support** | Native integration with Sway (swaybg) |

## Demo

![Unsplash Wallpaper Demo](screenshots/demo.gif)

## Installation

### Fedora

```bash
# System dependencies
sudo dnf install python3-gobject gtk4 libadwaita swaybg libnotify xdg-utils

# Install from PyPI or directly
pip install --user unsplash-wallpaper
```

### Generic Linux

```bash
# Runtime dependencies:
#   - Python 3.13+
#   - PyGObject >= 3.48 (python3-gobject)
#   - GTK4 + Libadwaita
#   - swaybg (for Sway/wayland)
#   - libnotify (for notifications)

pip install --user unsplash-wallpaper
```

### Development Installation

```bash
git clone https://github.com/unsplash-wallpaper/unsplash-wallpaper.git
cd unsplash-wallpaper
pip install --user -e ".[dev]"
```

## Configuration

### Unsplash API Key

1. Register an application at [Unsplash Developers](https://unsplash.com/developers)
2. Copy your **Access Key**
3. Launch the application and enter the key in Preferences, or store it directly:

```bash
unsplash-wallpaper
```

### Settings

Settings are stored in `~/.local/share/unsplash-wallpaper/database.db` and include:

| Setting | Options | Default |
|---------|---------|---------|
| Update Interval | 15m, 30m, 1h, 3h, 6h, 12h, 24h | 1 hour |
| Resolution | HD, Full HD, 2K, 4K, Original | Full HD |
| Categories | 10 available categories | All |
| Keywords | Custom search terms | None |
| Dark Mode | Light, Dark, Follow System | Follow System |
| Notifications | On/Off | On |
| Autostart | On/Off | Off |
| Max Wallpapers | Number to retain | 100 |

## Usage

```bash
# GUI mode (default)
unsplash-wallpaper

# Tray mode (background with tray icon)
unsplash-wallpaper --tray

# Daemon mode (headless, no GUI)
unsplash-wallpaper --daemon

# Install systemd user service
unsplash-wallpaper --install-service

# Remove systemd user service
unsplash-wallpaper --remove-service

# Show version
unsplash-wallpaper --version

# Run diagnostics
unsplash-wallpaper --diagnostics
```

### Systemd Integration

To run wallpaper changes on a timer without a desktop session:

```bash
unsplash-wallpaper --install-service
```

This installs and starts a systemd user service and timer. The timer triggers wallpaper changes at your configured interval.

### Tray Mode

Run `unsplash-wallpaper --tray` for background operation. The tray menu provides quick access to:

- Change wallpaper now
- Open dashboard
- Open preferences
- Open wallpaper folder
- Quit

## Architecture

```
src/unsplash_wallpaper/
├── app.py                        # Main application (Adw.Application)
├── config.py                     # Settings management
├── constants.py                  # Constants, defaults, resolutions
├── database.py                   # SQLite database with WAL mode
├── entry_point.py                # CLI entry point
├── __main__.py                   # python -m support
├── models/
│   └── wallpaper.py              # Wallpaper data model
├── services/
│   ├── unsplash_service.py       # Unsplash API client with retry logic
│   ├── wallpaper_service.py      # Wallpaper backends (Sway, GNOME, KDE, Hyprland)
│   ├── scheduler_service.py      # Background scheduling
│   ├── history_service.py        # Wallpaper history management
│   └── storage_service.py        # File storage management
├── ui/
│   ├── main_window.py            # Main dashboard window
│   ├── preferences_window.py     # Settings window
│   ├── category_page.py          # Category selection
│   └── history_page.py           # Wallpaper history view
├── tray/
│   └── tray_manager.py           # System tray (AyatanaAppIndicator)
└── system/
    └── autostart.py              # Autostart and systemd management
```

## Backend Support

| Desktop | Status | Tool |
|---------|--------|------|
| Sway | ✅ Active | `swaybg` |
| Hyprland | ✅ Supported | `hyprctl/hyprpaper` |
| GNOME | ✅ Supported | `gsettings` |
| KDE Plasma | ✅ Supported | `qdbus` |
| Other X11 | ✅ Supported | `feh` |

The appropriate backend is auto-detected at runtime via `WallpaperBackend.detect()`.

## Testing

```bash
# Run all tests
pytest

# With coverage report
pytest --cov=unsplash_wallpaper --cov-report=term-missing

# Run specific tests
pytest tests/test_database.py -v
pytest tests/test_unsplash_service.py -v -k "test_get_random_photo"
```

## Roadmap

- [ ] Hyprland wallpaper backend improvements
- [ ] Flatpak distribution
- [ ] Multiple monitor support
- [ ] Wallpaper collections and playlists
- [ ] CLI for non-interactive use (set, next, info)
- [ ] Online wallpaper gallery browser
- [ ] Config export/import
- [ ] Translations (i18n)

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) and our [Code of Conduct](CODE_OF_CONDUCT.md) before starting.

See [RELEASE_NOTES_v1.0.0.md](RELEASE_NOTES_v1.0.0.md) for the current release.

## License

GNU General Public License v2.0 — see [LICENSE](LICENSE) for details.
