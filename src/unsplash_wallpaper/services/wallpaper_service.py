from __future__ import annotations

import abc
import logging
import os
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class WallpaperBackend(abc.ABC):
    @abc.abstractmethod
    def apply(self, path: str) -> bool:
        """Apply wallpaper at the given path."""

    @abc.abstractmethod
    def get_name(self) -> str:
        """Return backend name."""

    @classmethod
    def detect(cls) -> type[WallpaperBackend]:
        desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
        session = os.environ.get("DESKTOP_SESSION", "").lower()
        wayland = os.environ.get("WAYLAND_DISPLAY", "")

        if "sway" in desktop or "sway" in session:
            return SwayBackend
        if "hyprland" in desktop or "hyprland" in session:
            return HyprlandBackend
        if "gnome" in desktop or "gnome" in session:
            return GnomeBackend
        if "kde" in desktop or "kde" in session or "plasma" in desktop:
            return KdeBackend
        if wayland:
            return SwayBackend
        return SwayBackend

    @classmethod
    def is_available(cls) -> bool:
        try:
            backend_cls = cls.detect()
            return backend_cls.check_dependencies()
        except Exception:
            return False

    @staticmethod
    def check_dependencies() -> bool:
        return True


class SwayBackend(WallpaperBackend):
    def apply(self, path: str) -> bool:
        logger.info("Entering apply()")
        try:
            self._kill_existing()
            logger.info("Before systemd-run")
            subprocess.Popen(
                [
                    "systemd-run", "--user", "--scope",
                    "--unit", "unsplash-wallpaper-swaybg",
                    "--collect", "--quiet",
                    "swaybg", "-i", path, "-m", "fill",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            logger.info("After systemd-run")
            logger.info("Applied wallpaper via swaybg: %s", path)
            return True
        except FileNotFoundError:
            logger.error(
                "swaybg or systemd-run not found. "
                "Install swaybg and systemd packages."
            )
            return False
        except Exception as e:
            logger.error("Failed to apply wallpaper via swaybg: %s", e)
            return False
        finally:
            logger.info("Leaving apply()")

    def get_name(self) -> str:
        return "Sway"

    @staticmethod
    def _kill_existing() -> None:
        try:
            subprocess.run(
                ["systemctl", "--user", "stop", "unsplash-wallpaper-swaybg.scope"],
                capture_output=True,
                timeout=10,
            )
        except Exception as e:
            logger.debug("Error stopping swaybg scope: %s", e)
        try:
            result = subprocess.run(
                ["pkill", "swaybg"],
                capture_output=True,
                timeout=10,
            )
            if result.returncode == 0:
                logger.info("Terminated stray swaybg processes via pkill")
        except FileNotFoundError:
            logger.debug("pkill not available, skipping")
        except Exception as e:
            logger.debug("Error running pkill: %s", e)

    @staticmethod
    def check_dependencies() -> bool:
        return (
            shutil.which("swaybg") is not None
            and shutil.which("systemd-run") is not None
        )


class HyprlandBackend(WallpaperBackend):
    def apply(self, path: str) -> bool:
        try:
            cmd = ["hyprctl", "hyprpaper", ",", "wallpaper", path]
            subprocess.run(cmd, capture_output=True, timeout=10)
            logger.info("Applied wallpaper via hyprpaper: %s", path)
            return True
        except FileNotFoundError:
            logger.error(
                "hyprctl/hyprpaper not found. Install hyprpaper."
            )
            return False
        except Exception as e:
            logger.error(
                "Failed to apply wallpaper via hyprpaper: %s", e
            )
            return False

    def get_name(self) -> str:
        return "Hyprland"

    @staticmethod
    def check_dependencies() -> bool:
        return (
            shutil.which("hyprctl") is not None
            and shutil.which("hyprpaper") is not None
        )


class GnomeBackend(WallpaperBackend):
    def apply(self, path: str) -> bool:
        try:
            uri = Path(path).as_uri()
            cmd = [
                "gsettings",
                "set",
                "org.gnome.desktop.background",
                "picture-uri",
                uri,
            ]
            subprocess.run(cmd, capture_output=True, timeout=10)
            cmd_dark = [
                "gsettings",
                "set",
                "org.gnome.desktop.background",
                "picture-uri-dark",
                uri,
            ]
            subprocess.run(cmd_dark, capture_output=True, timeout=10)
            logger.info("Applied wallpaper via gsettings: %s", path)
            return True
        except FileNotFoundError:
            logger.error("gsettings not found.")
            return False
        except Exception as e:
            logger.error(
                "Failed to apply wallpaper via gsettings: %s", e
            )
            return False

    def get_name(self) -> str:
        return "GNOME"

    @staticmethod
    def check_dependencies() -> bool:
        return shutil.which("gsettings") is not None


class KdeBackend(WallpaperBackend):
    def apply(self, path: str) -> bool:
        try:
            script = (
                f"var allDesktops = desktops();"
                f"for (var i=0; i<allDesktops.length; i++) {{"
                f"  var d = allDesktops[i];"
                f"  d.wallpaperPlugin = 'org.kde.image';"
                f"  d.currentConfigGroup = ['Wallpaper', "
                f"    'org.kde.image', 'General'];"
                f"  d.writeConfig('Image', 'file://{path}');"
                f"}}"
            )
            cmd = [
                "qdbus",
                "org.kde.plasmashell",
                "/PlasmaShell",
                "org.kde.PlasmaShell.evaluateScript",
                script,
            ]
            subprocess.run(cmd, capture_output=True, timeout=10)
            logger.info("Applied wallpaper via KDE: %s", path)
            return True
        except FileNotFoundError:
            logger.error("qdbus not found.")
            return False
        except Exception as e:
            logger.error("Failed to apply wallpaper via KDE: %s", e)
            return False

    def get_name(self) -> str:
        return "KDE"

    @staticmethod
    def check_dependencies() -> bool:
        return shutil.which("qdbus") is not None


class WallpaperService:
    def __init__(self) -> None:
        self._backend: WallpaperBackend | None = None

    @property
    def backend(self) -> WallpaperBackend:
        if self._backend is None:
            backend_cls = WallpaperBackend.detect()
            self._backend = backend_cls()
            logger.info(
                "Using wallpaper backend: %s",
                self._backend.get_name(),
            )
        return self._backend

    def apply(self, path: str) -> bool:
        return self.backend.apply(path)

    def get_backend_name(self) -> str:
        return self.backend.get_name()

    def is_backend_available(self) -> bool:
        return WallpaperBackend.is_available()
