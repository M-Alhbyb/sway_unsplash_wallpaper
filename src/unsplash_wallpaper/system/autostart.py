from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any

from unsplash_wallpaper.constants import (
    APP_ID,
    APP_NAME,
    AUTOSTART_FILE,
    SYSTEMD_SERVICE_DIR,
    SYSTEMD_SERVICE_FILE,
    SYSTEMD_TIMER_FILE,
)

logger = logging.getLogger(__name__)


class AutostartManager:
    @staticmethod
    def get_desktop_entry(python_path: str | None = None) -> str:
        if python_path is None:
            python_path = shutil.which("unsplash-wallpaper") or str(
                Path.home()
                / ".local"
                / "bin"
                / "unsplash-wallpaper"
            )
        return f"""[Desktop Entry]
Type=Application
Name={APP_NAME}
Exec={python_path} --tray
Icon={APP_ID}
Terminal=false
Categories=Utility;
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-Delay=5
"""

    @staticmethod
    def enable_autostart() -> bool:
        try:
            AUTOSTART_FILE.parent.mkdir(parents=True, exist_ok=True)
            python_path = _find_python_path()
            content = AutostartManager.get_desktop_entry(python_path)
            AUTOSTART_FILE.write_text(content)
            logger.info("Autostart enabled at %s", AUTOSTART_FILE)
            return True
        except Exception as e:
            logger.error("Failed to enable autostart: %s", e)
            return False

    @staticmethod
    def disable_autostart() -> bool:
        try:
            if AUTOSTART_FILE.exists():
                AUTOSTART_FILE.unlink()
                logger.info("Autostart disabled")
            return True
        except Exception as e:
            logger.error("Failed to disable autostart: %s", e)
            return False

    @staticmethod
    def is_autostart_enabled() -> bool:
        return AUTOSTART_FILE.exists()

    @staticmethod
    def get_systemd_service(python_path: str | None = None) -> str:
        if python_path is None:
            python_path = shutil.which("unsplash-wallpaper") or str(
                Path.home()
                / ".local"
                / "bin"
                / "unsplash-wallpaper"
            )
        return f"""[Unit]
Description={APP_NAME} - Automatic wallpaper changer
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart={python_path} --daemon
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
"""

    @staticmethod
    def get_systemd_timer() -> str:
        return f"""[Unit]
Description={APP_NAME} Timer

[Timer]
OnBootSec=1min
OnUnitActiveSec=1h
Persistent=true

[Install]
WantedBy=timers.target
"""

    @staticmethod
    def install_systemd_service() -> bool:
        try:
            SYSTEMD_SERVICE_DIR.mkdir(parents=True, exist_ok=True)
            python_path = _find_python_path()
            service = AutostartManager.get_systemd_service(python_path)
            SYSTEMD_SERVICE_FILE.write_text(service)
            logger.info(
                "Systemd service installed at %s",
                SYSTEMD_SERVICE_FILE,
            )
            return True
        except Exception as e:
            logger.error(
                "Failed to install systemd service: %s", e
            )
            return False

    @staticmethod
    def install_systemd_timer() -> bool:
        try:
            SYSTEMD_SERVICE_DIR.mkdir(parents=True, exist_ok=True)
            timer = AutostartManager.get_systemd_timer()
            SYSTEMD_TIMER_FILE.write_text(timer)
            logger.info(
                "Systemd timer installed at %s",
                SYSTEMD_TIMER_FILE,
            )
            return True
        except Exception as e:
            logger.error(
                "Failed to install systemd timer: %s", e
            )
            return False

    @staticmethod
    def remove_systemd_service() -> bool:
        try:
            if SYSTEMD_SERVICE_FILE.exists():
                SYSTEMD_SERVICE_FILE.unlink()
            if SYSTEMD_TIMER_FILE.exists():
                SYSTEMD_TIMER_FILE.unlink()
            logger.info("Systemd service files removed")
            return True
        except Exception as e:
            logger.error(
                "Failed to remove systemd service: %s", e
            )
            return False

    @staticmethod
    def enable_systemd_service() -> bool:
        import subprocess

        try:
            result = subprocess.run(
                [
                    "systemctl",
                    "--user",
                    "enable",
                    "--now",
                    f"{APP_ID}.service",
                ],
                capture_output=True,
                timeout=30,
            )
            if result.returncode == 0:
                logger.info("Systemd service enabled and started")
                return True
            logger.warning(
                "Failed to enable systemd service: %s",
                result.stderr.decode(),
            )
            return False
        except Exception as e:
            logger.error(
                "Failed to enable systemd service: %s", e
            )
            return False

    @staticmethod
    def disable_systemd_service() -> bool:
        import subprocess

        try:
            subprocess.run(
                [
                    "systemctl",
                    "--user",
                    "disable",
                    "--now",
                    f"{APP_ID}.service",
                ],
                capture_output=True,
                timeout=30,
            )
            return True
        except Exception as e:
            logger.error(
                "Failed to disable systemd service: %s", e
            )
            return False


def _find_python_path() -> str:
    import sys
    import shutil

    entry_point = shutil.which("unsplash-wallpaper")
    if entry_point:
        return entry_point
    python = sys.executable
    module_path = Path(__file__).parent.parent.parent / "unsplash_wallpaper" / "app.py"
    if module_path.exists():
        return f"{python} {module_path}"
    return f"{python} -m unsplash_wallpaper"
