# Unsplash Wallpaper Manager

A production-quality Linux desktop application that automatically downloads wallpapers from Unsplash and applies them to your desktop environment.

## Features

- **Automatic Wallpaper Download** - Fetches high-quality wallpapers from Unsplash
- **Scheduled Changes** - Update wallpapers on configurable intervals (15min to 24h)
- **Category Selection** - Choose from 10 curated categories
- **No Repetition** - Tracks download history to avoid duplicate wallpapers
- **Wallpaper History** - Browse, re-apply, or delete past wallpapers
- **GTK4 + Libadwaita UI** - Modern, responsive desktop interface
- **System Tray** - Background operation with tray icon
- **Notifications** - Desktop notifications for wallpaper changes
- **Auto Start** - Optional autostart with systemd user service

## Requirements

### Runtime
- Python 3.13+
- Fedora Linux (or similar)
- Sway (Wayland compositor)
- GTK4 + Libadwaita
- `swaybg` for wallpaper display
- `libnotify` for desktop notifications

### Python Packages
- PyGObject >= 3.48
- Requests >= 2.31

## Installation

### From Source
```bash
git clone https://github.com/unsplash-wallpaper/unsplash-wallpaper.git
cd unsplash-wallpaper
pip install --user .
```

### Fedora RPM
```bash
sudo dnf install unsplash-wallpaper
```

### System Dependencies (Fedora)
```bash
sudo dnf install python3-gobject gtk4 libadwaita swaybg libnotify xdg-utils
```

## Quick Start

1. Get an Unsplash API access key from https://unsplash.com/developers
2. Launch the application:
   ```bash
   unsplash-wallpaper
   ```
3. Go to Preferences and enter your Unsplash Access Key
4. Select wallpaper categories
5. Click "Change Now" to download your first wallpaper

## Usage

### GUI Mode
```bash
unsplash-wallpaper
```

### Tray Mode (background)
```bash
unsplash-wallpaper --tray
```

### Daemon Mode (headless)
```bash
unsplash-wallpaper --daemon
```

### Install systemd Service
```bash
unsplash-wallpaper --install-service
```

### Remove systemd Service
```bash
unsplash-wallpaper --remove-service
```

## Configuration

Settings are stored in `~/.local/share/unsplash-wallpaper/database.db`.

### Unsplash Access Key
Required. Get from [Unsplash Developers](https://unsplash.com/developers).

### Update Intervals
- 15 minutes
- 30 minutes
- 1 hour (default)
- 3 hours
- 6 hours
- 12 hours
- 24 hours

### Resolutions
- HD (1280x720)
- Full HD (1920x1080) - default
- 2K (2560x1440)
- 4K (3840x2160)
- Original

## Wallpaper Storage

Wallpapers are stored in `~/.local/share/unsplash-wallpaper/wallpapers/`.
The last 100 wallpapers are kept by default (configurable).

## History

All downloaded wallpapers are tracked in the SQLite database:
- Unsplash photo ID
- Author name
- Download date
- Local file path
- Category

## Backend Support

### Current
- Sway (via swaybg)

### Planned
- Hyprland (via hyprpaper)
- GNOME (via gsettings)
- KDE Plasma (via qdbus)

## Project Structure

```
src/
├── app.py                  # Main application entry point
├── constants.py            # Constants and configuration defaults
├── config.py               # Settings management
├── database.py             # SQLite database operations
├── models/
│   └── wallpaper.py        # Wallpaper data model
├── services/
│   ├── unsplash_service.py  # Unsplash API client
│   ├── wallpaper_service.py # Wallpaper backends (Sway, etc.)
│   ├── scheduler_service.py # Background scheduling
│   ├── history_service.py   # Wallpaper history management
│   └── storage_service.py   # File storage management
├── ui/
│   ├── main_window.py       # Main application window
│   ├── preferences_window.py# Settings window
│   ├── category_page.py     # Category selection
│   └── history_page.py      # Wallpaper history view
├── tray/
│   └── tray_manager.py      # System tray integration
└── system/
    └── autostart.py         # Autostart and systemd management
```

## Testing

```bash
pytest
```

With coverage:
```bash
pytest --cov=src --cov-report=term-missing
```

## Development

### Setup
```bash
pip install --user -e ".[dev]"
```

### Code Quality
```bash
ruff check src/
mypy src/
```

## License

MIT
