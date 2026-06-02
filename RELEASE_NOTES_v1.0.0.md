# Release Notes — v1.0.0

**Release Date:** 2026-06-02

This is the initial stable release of Unsplash Wallpaper, a production-quality Linux desktop application for automatic wallpaper management via the Unsplash API.

## Features

- **Unsplash Integration** — Fetches high-quality, curated wallpapers from Unsplash with proper API rate-limit handling, retry logic, and download tracking
- **Scheduled Wallpaper Changes** — Configurable intervals (15 min, 30 min, 1h, 3h, 6h, 12h, 24h)
- **Category Selection** — Choose from 10 categories: nature, technology, space, cars, architecture, minimal, mountains, forests, city, gaming
- **Custom Keywords** — Search by arbitrary keywords for more control
- **GTK4 + Libadwaita GUI** — Modern responsive interface with dark/light/system theme support
- **System Tray Integration** — Background operation via AyatanaAppIndicator with quick-action menu
- **Multiple Resolutions** — HD (1280×720), Full HD (1920×1080), 2K (2560×1440), 4K (3840×2160), and original
- **Wallpaper History** — Browse, re-apply, or delete past wallpapers; configurable retention limit
- **Multi-Backend Support** — Automatic detection for Sway (swaybg), Hyprland (hyprctl), GNOME (gsettings), KDE (qdbus), and generic X11 (feh)
- **Desktop Notifications** — Native notifications via `notify-send` with toggle
- **Systemd Integration** — One-command install/removal of user-scope systemd service and timer
- **Autostart** — XDG autostart .desktop file management
- **Daemon Mode** — Headless operation for servers or minimal setups
- **First-Run Wizard** — Onboarding dialog for API key configuration
- **Crash Handler** — Desktop notification with error details on unexpected crashes
- **Secrets Masking** — Automatic masking of API keys in log output
- **Image Format Validation** — Validates JPEG, PNG, GIF, WebP, and HEIF signatures

## Improvements

- **Defensive Programming** — Comprehensive error handling across all services with typed exception hierarchy
- **Logging** — Rotating file handler (1 MB max, 5 backups) with structured log format
- **Database Safety** — WAL journal mode for safe concurrent access; parameterized queries throughout
- **Thread Safety** — Thread-safe database singleton with per-thread connections
- **Network Resilience** — Exponential backoff retry for network failures; rate-limit awareness
- **Type Safety** — Complete PEP 484 type hints with py.typed marker
- **Code Quality** — Strict ruff linting, 79-character line limit

## Stability Work

- 56+ unit tests covering all services, database, config, storage, and integration paths
- 24-hour stress test: zero resource leaks, stable memory usage (~19 MB RSS)
- Recovery tests: graceful handling of network failures, API errors, corrupt data
- Sway validation: complete end-to-end lifecycle tested on Sway (Wayland)
- Packaging validation: source install, editable install, entry points verified

## Testing Statistics

| Metric | Value |
|--------|-------|
| Total tests | 56+ |
| Code coverage | >90% |
| Stress test duration | 24 hours |
| Stress test memory | ~19 MB RSS steady-state |
| Test environments | Fedora 41, Sway (Wayland) |

## Known Limitations

- Sway (swaybg) is the primary tested backend; others are implemented but need real-environment validation
- Flatpak/Flathub distribution is planned but not yet available
- No CLI subcommands for one-off operations (`set`, `next`, `info`)
- Single-monitor support only (multi-monitor is planned)
- No wallpaper collections or playlists

## Installation

```bash
pip install --user unsplash-wallpaper
```

See [README.md](README.md) for detailed installation and configuration instructions.
