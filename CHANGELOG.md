# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-06-02

### Added

- Initial release of Unsplash Wallpaper Manager
- Automatic wallpaper download from Unsplash API
- Scheduled wallpaper changes (15 min to 24 hours)
- GTK4 + Libadwaita graphical user interface
- System tray support via AyatanaAppIndicator
- Sway wallpaper backend (swaybg)
- Support for GNOME, KDE, and Hyprland backends
- Wallpaper history management with retention limits
- First-run API key setup wizard
- Category-based wallpaper selection (nature, technology, space, cars, etc.)
- Multiple resolution support (HD, Full HD, 2K, 4K, Original)
- Wallpaper preview and dashboard
- Desktop notifications via notify-send
- Autostart configuration (XDG autostart and systemd)
- Systemd service and timer integration
- Daemon mode for headless operation
- Tray mode for background operation
- Crash handler with notification
- Secrets masking in log files
- Image format validation (JPEG, PNG, GIF, WebP, HEIF)
- Database WAL mode for concurrent access
- Comprehensive test suite (56+ unit tests)
- PEP 561 type hints (py.typed marker)
- RPM spec file for Fedora packaging
- Flatpak manifest
- Desktop entry file
- Command-line interface with version and diagnostics flags
