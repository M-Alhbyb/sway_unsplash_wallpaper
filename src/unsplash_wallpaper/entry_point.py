#!/usr/bin/env python3
"""Console script entry point for unsplash-wallpaper."""

from unsplash_wallpaper.app import UnsplashWallpaperApp


def main() -> None:
    import sys

    # Default to daemon mode unless a specific action flag is given
    recognized = frozenset({
        "--version", "--diagnostics",
        "--install-service", "--remove-service",
        "--daemon",
    })
    if not any(a in recognized for a in sys.argv[1:]):
        sys.argv.append("--daemon")
    UnsplashWallpaperApp.main()

if __name__ == "__main__":
    main()
