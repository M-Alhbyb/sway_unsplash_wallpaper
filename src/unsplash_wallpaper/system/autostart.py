from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

from unsplash_wallpaper.constants import (
    APP_ID,
    APP_NAME,
    AUTOSTART_FILE,
    DEFAULT_INTERVAL,
    INTERVALS,
    SYSTEMD_SERVICE_DIR,
    SYSTEMD_SERVICE_FILE,
    SYSTEMD_TIMER_FILE,
)

logger = logging.getLogger(__name__)


def _minutes_to_systemd_time(minutes: int) -> str:
    if minutes < 60:
        return f"{minutes}min"
    hours = minutes // 60
    return f"{hours}h"


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
Exec={python_path}
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
Type=oneshot
ExecStart={python_path} --run-job
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
"""

    @staticmethod
    def get_systemd_timer(interval_label: str | None = None) -> str:
        if interval_label is None:
            interval_label = DEFAULT_INTERVAL
        minutes = INTERVALS.get(interval_label, INTERVALS.get(DEFAULT_INTERVAL, 60))
        systemd_time = _minutes_to_systemd_time(minutes)
        return f"""[Unit]
Description={APP_NAME} Timer

[Timer]
OnBootSec=1min
OnUnitActiveSec={systemd_time}
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
    def update_timer_interval(interval_label: str) -> bool:
        try:
            logger.info(
                "update_timer_interval entered — requested interval: '%s'",
                interval_label,
            )
            SYSTEMD_SERVICE_DIR.mkdir(parents=True, exist_ok=True)
            timer = AutostartManager.get_systemd_timer(interval_label)

            # Extract the generated OnUnitActiveSec value for logging
            for line in timer.splitlines():
                if line.startswith("OnUnitActiveSec="):
                    systemd_value = line.split("=", 1)[1]
                    logger.info(
                        "Generated systemd value: '%s'", systemd_value
                    )
                    break

            logger.info("Timer file path: %s", SYSTEMD_TIMER_FILE)
            SYSTEMD_TIMER_FILE.write_text(timer)

            # Log file contents after write
            written = SYSTEMD_TIMER_FILE.read_text()
            logger.info("Timer file contents after write:\n%s", written)

            result = subprocess.run(
                ["systemctl", "--user", "daemon-reload"],
                capture_output=True,
                timeout=30,
            )
            if result.returncode != 0:
                logger.warning(
                    "daemon-reload failed: %s",
                    result.stderr.decode(),
                )
            else:
                logger.info("systemd daemon reloaded")

            result = subprocess.run(
                ["systemctl", "--user", "restart", f"{APP_ID}.timer"],
                capture_output=True,
                timeout=30,
            )
            if result.returncode != 0:
                logger.warning(
                    "Timer restart failed: %s",
                    result.stderr.decode(),
                )
            else:
                logger.info("systemd timer restarted")

            return True
        except Exception as e:
            logger.error(
                "Failed to update timer interval: %s", e
            )
            return False

    @staticmethod
    def needs_migration() -> bool:
        """Check if the installed service file needs migration to new format."""
        if not SYSTEMD_SERVICE_FILE.exists():
            return False
        try:
            content = SYSTEMD_SERVICE_FILE.read_text()
            return (
                "--daemon" in content
                or "Type=simple" in content
                or "--run-job" not in content
            )
        except Exception:
            return False

    @staticmethod
    def migrate_service_file() -> bool:
        """Upgrade stale service file to new --run-job / Type=oneshot format."""
        try:
            if not AutostartManager.needs_migration():
                return True
            logger.info("Migrating systemd service file to new format")
            AutostartManager.install_systemd_service()
            result = subprocess.run(
                ["systemctl", "--user", "daemon-reload"],
                capture_output=True,
                timeout=30,
            )
            if result.returncode != 0:
                logger.warning(
                    "daemon-reload during migration failed: %s",
                    result.stderr.decode(),
                )
            else:
                logger.info("systemd daemon reloaded after migration")
            logger.info("Systemd service file migrated successfully")
            return True
        except Exception as e:
            logger.error("Failed to migrate service file: %s", e)
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
                logger.info("Systemd service enabled")
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
    def enable_systemd_timer() -> bool:
        try:
            result = subprocess.run(
                [
                    "systemctl",
                    "--user",
                    "enable",
                    "--now",
                    f"{APP_ID}.timer",
                ],
                capture_output=True,
                timeout=30,
            )
            if result.returncode == 0:
                logger.info("Systemd timer enabled and started")
                return True
            logger.warning(
                "Failed to enable systemd timer: %s",
                result.stderr.decode(),
            )
            return False
        except Exception as e:
            logger.error(
                "Failed to enable systemd timer: %s", e
            )
            return False

    @staticmethod
    def disable_systemd_service() -> bool:
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

    @staticmethod
    def disable_systemd_timer() -> bool:
        try:
            subprocess.run(
                [
                    "systemctl",
                    "--user",
                    "disable",
                    "--now",
                    f"{APP_ID}.timer",
                ],
                capture_output=True,
                timeout=30,
            )
            return True
        except Exception as e:
            logger.error(
                "Failed to disable systemd timer: %s", e
            )
            return False


def _find_python_path() -> str:
    entry_point = shutil.which("unsplash-wallpaper")
    if entry_point:
        return entry_point
    python = shutil.which("python3") or "/usr/bin/python3"
    module_path = Path(__file__).parent.parent.parent / "unsplash_wallpaper" / "app.py"
    if module_path.exists():
        return f"{python} {module_path}"
    return f"{python} -m unsplash_wallpaper"
