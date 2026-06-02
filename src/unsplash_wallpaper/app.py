#!/usr/bin/env python3
"""Unsplash Wallpaper Manager - Main application entry point."""

from __future__ import annotations

import logging
import logging.handlers
import os
import shutil
import subprocess
import sys
import threading
import traceback
from pathlib import Path
from typing import Any


import gi

gi.require_version("Adw", "1")
gi.require_version("Gtk", "4.0")

from gi.repository import Adw, Gio, GLib, Gtk

from unsplash_wallpaper.config import Config
from unsplash_wallpaper.constants import (
    APP_ID,
    APP_NAME,
    CATEGORIES,
    CATEGORY_LABELS,
    DATA_DIR,
    INTERVALS,
    LOG_DIR,
    LOG_FILE,
    VERSION,
    WALLPAPERS_DIR,
)
from unsplash_wallpaper.database import Database
from unsplash_wallpaper.models.wallpaper import Wallpaper
from unsplash_wallpaper.services.history_service import HistoryService
from unsplash_wallpaper.services.scheduler_service import SchedulerService
from unsplash_wallpaper.services.storage_service import StorageService
from unsplash_wallpaper.services.unsplash_service import (
    UnsplashAuthError,
    UnsplashNetworkError,
    UnsplashRateLimitError,
    UnsplashService,
)
from unsplash_wallpaper.services.wallpaper_service import WallpaperService
from unsplash_wallpaper.system.autostart import AutostartManager
from unsplash_wallpaper.tray.tray_manager import TrayManager
from unsplash_wallpaper.ui.main_window import MainWindow
from unsplash_wallpaper.ui.preferences_window import PreferencesWindow

logger = logging.getLogger(__name__)


class SecretsMaskingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        msg = str(record.msg)
        if isinstance(record.args, dict):
            args = {k: str(v) for k, v in record.args.items()}
        elif isinstance(record.args, tuple):
            args = tuple(str(a) for a in record.args)
        else:
            args = record.args
        msg = msg % args if isinstance(args, (tuple, dict)) else msg
        for secret_attr in ("access_key", "client_id", "api_key", "secret", "token"):
            if secret_attr in msg.lower():
                record.msg = record.msg.replace(
                    str(record.args[0]), "***MASKED***"
                ) if record.args else record.msg
        return True


class UnsplashWallpaperApp(Adw.Application):
    def __init__(self) -> None:
        super().__init__(
            application_id=APP_ID,
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        self.set_resource_base_path("/com/unsplash/wallpaper")

        self._setup_crash_handler()
        self._setup_logging()
        self._init_services()

        self._window: MainWindow | None = None
        self._tray: TrayManager | None = None
        self._daemon_mode = False
        self._tray_mode = False
        self._shutting_down = False

        self._setup_actions()
        self._log_startup_diagnostics()

    def _setup_crash_handler(self) -> None:
        def handle_exception(exc_type, exc_value, exc_tb) -> None:
            if issubclass(exc_type, KeyboardInterrupt):
                sys.__excepthook__(exc_type, exc_value, exc_tb)
                return
            logger.critical(
                "Unhandled exception: %s\n%s",
                exc_value,
                "".join(traceback.format_tb(exc_tb)),
            )
            try:
                import notify2  # optional
            except ImportError:
                try:
                    subprocess.run(
                        [
                            "notify-send",
                            "--app-name", APP_NAME,
                            "--icon", "dialog-error",
                            "--urgency", "critical",
                            f"{APP_NAME} crashed",
                            str(exc_value),
                        ],
                        capture_output=True,
                        timeout=5,
                    )
                except Exception:
                    pass

        sys.excepthook = handle_exception

    def _setup_logging(self) -> None:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        handler = logging.handlers.RotatingFileHandler(
            LOG_FILE,
            maxBytes=1024 * 1024,
            backupCount=5,
        )
        formatter = logging.Formatter(
            "%(asctime)s.%(msecs)03d - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        handler.addFilter(SecretsMaskingFilter())

        root = logging.getLogger()
        root.setLevel(logging.INFO)
        root.addHandler(handler)

        console = logging.StreamHandler()
        console.setFormatter(formatter)
        root.addHandler(console)

        logger.info("Logging initialized")

    def _log_startup_diagnostics(self) -> None:
        logger.info("--- Startup Diagnostics ---")
        logger.info("Python version: %s", sys.version)
        logger.info("Platform: %s", sys.platform)
        logger.info("Data directory: %s", DATA_DIR)
        logger.info("Wallpapers directory: %s", WALLPAPERS_DIR)
        logger.info("Database path: %s", DATA_DIR / "database.db")
        logger.info("Log file: %s", LOG_FILE)
        logger.info("Sway available: %s", shutil.which("swaybg") is not None)
        logger.info(
            "XDG_CURRENT_DESKTOP: %s",
            os.environ.get("XDG_CURRENT_DESKTOP", "not set"),
        )
        logger.info(
            "WAYLAND_DISPLAY: %s",
            os.environ.get("WAYLAND_DISPLAY", "not set"),
        )
        logger.info(
            "DESKTOP_SESSION: %s",
            os.environ.get("DESKTOP_SESSION", "not set"),
        )
        wallpapers_count = 0
        if WALLPAPERS_DIR.exists():
            wallpapers_count = len(list(WALLPAPERS_DIR.iterdir()))
        logger.info("Stored wallpapers: %d", wallpapers_count)
        db_size = 0
        db_path = DATA_DIR / "database.db"
        if db_path.exists():
            db_size = db_path.stat().st_size
        logger.info("Database size: %d bytes", db_size)
        logger.info("--- End Diagnostics ---")

    def _init_services(self) -> None:
        self._db = Database.get_instance()
        self._config = Config(self._db)
        self._storage = StorageService()
        self._history = HistoryService(self._db, self._storage, self._config)
        self._unsplash = UnsplashService(self._config)
        self._wallpaper_service = WallpaperService()
        self._scheduler = SchedulerService()

    def _setup_actions(self) -> None:
        actions: list[tuple[str, Callable, list[str]]] = [
            ("change-wallpaper", self._on_change_wallpaper, []),
            ("preferences", self._on_open_preferences, []),
            ("open-folder", self._on_open_folder, []),
            ("open-dashboard", self._on_open_dashboard, []),
            ("about", self._on_about, []),
            ("quit", self._on_quit, []),
        ]

        for name, callback, param_types in actions:
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", callback)
            self.add_action(action)

        self.set_accels_for_action("app.quit", ["<primary>q"])
        self.set_accels_for_action(
            "app.preferences", ["<primary>comma"]
        )

    def _on_change_wallpaper(self, *args: Any) -> None:
        if self._window:
            self._window.show_loading(True)
        threading.Thread(
            target=self._download_and_apply_wallpaper,
            daemon=True,
        ).start()

    def _on_open_preferences(self, *args: Any) -> None:
        self._show_preferences()

    def _on_open_folder(self, *args: Any) -> None:
        self._open_wallpaper_folder()

    def _on_open_dashboard(self, *args: Any) -> None:
        if self._window:
            self._window.present()
            self._window._stack.set_visible_child_name("dashboard")

    def _on_about(self, *args: Any) -> None:
        about = Adw.AboutWindow(
            transient_for=self._window,
            application_name=APP_NAME,
            application_icon=APP_ID,
            version=VERSION,
            developer_name="Unsplash Wallpaper Team",
            license_type=Gtk.License.MIT,
            website="https://github.com/unsplash-wallpaper",
            issue_url="https://github.com/unsplash-wallpaper/issues",
            support_url="https://github.com/unsplash-wallpaper/discussions",
            copyright="© 2026 Unsplash Wallpaper Team",
        )
        about.present()

    def _on_quit(self, *args: Any) -> None:
        self._shutting_down = True
        self._scheduler.stop()
        self._unsplash.close()
        if self._tray:
            self._tray.shutdown()
        if self._window:
            self._window = None
        self._db.close_all()
        self.quit()

    def do_startup(self) -> None:
        Adw.Application.do_startup(self)
        self._apply_style()
        self._setup_tray()
        self._start_scheduler()
        if self._daemon_mode:
            logger.info("Running in daemon mode (no window)")

    def do_activate(self) -> None:
        if self._daemon_mode:
            logger.debug("Daemon mode: skipping window activation")
            return
        if self._window is None:
            self._window = MainWindow(application=self)

            self._window.connect(
                "change-wallpaper", self._on_change_wallpaper
            )
            self._window.connect(
                "open-settings", self._on_open_preferences
            )
            self._window.connect("open-folder", self._on_open_folder)
            self._window.connect(
                "categories-changed", self._on_categories_changed
            )
            self._window.connect(
                "apply-history-wallpaper",
                self._on_apply_history_wallpaper,
            )
            self._window.connect(
                "delete-history-wallpaper",
                self._on_delete_history_wallpaper,
            )

            if self._config.has_valid_api_key():
                self._load_categories()
                self._load_history()
                self._update_dashboard()
            else:
                self._show_first_run_wizard()

            self._window.connect("close-request", self._on_close_request)

        self._window.present()

    def _show_first_run_wizard(self) -> None:
        if not self._window:
            return
        GLib.idle_add(self._window.show_first_run_prompt)

    def _on_close_request(self, *args: Any) -> bool:
        if self._tray and not self._daemon_mode:
            self._window.hide()
            return True
        return False

    def _setup_tray(self) -> None:
        if self._tray_mode or not self._daemon_mode:
            self._tray = TrayManager(self)
            if self._tray.setup():
                logger.info("Tray icon initialized")
            else:
                self._tray = None
                logger.info("Tray icon not available")

    def _start_scheduler(self) -> None:
        interval = self._config.get("update_interval", "1 hour")
        self._scheduler.set_interval(interval)
        self._scheduler.start(self._on_scheduled_update)

    def _on_scheduled_update(self) -> None:
        logger.info("Scheduled wallpaper update triggered")
        threading.Thread(
            target=self._download_and_apply_wallpaper,
            daemon=True,
        ).start()

    def _download_and_apply_wallpaper(self) -> None:
        try:
            categories = self._config.get_categories()
            resolution = self._config.get("resolution", "full_hd")

            photo = self._unsplash.get_random_photo(
                categories=categories if categories else None,
                resolution=resolution,
            )

            if self._history.is_downloaded(photo["id"]):
                logger.info(
                    "Photo %s already downloaded, skipping",
                    photo["id"],
                )
                GLib.idle_add(self._finish_download, None)
                return

            image_data = self._unsplash.download_image(photo["url"])

            if not self._validate_image_data(image_data):
                logger.error("Downloaded image data is not a valid image")
                GLib.idle_add(self._finish_download, None)
                return

            wallpaper = Wallpaper(
                unsplash_id=photo["id"],
                author=photo["author"],
                description=photo["description"],
                local_path="",
                download_location=photo["download_location"],
                category=photo.get("category", ""),
                url=photo["url"],
            )
            filename = wallpaper.filename
            filepath = self._storage.save_wallpaper(image_data, filename)
            wallpaper.local_path = str(filepath)

            self._history.add(wallpaper)

            GLib.idle_add(self._apply_wallpaper, wallpaper)

            threading.Thread(
                target=self._unsplash.track_download,
                args=(photo["download_location"],),
                daemon=True,
            ).start()

        except UnsplashAuthError as e:
            logger.error("Auth error: %s", e)
            self._show_notification(
                "Unsplash API Error",
                "Invalid or missing API key. Please check settings.",
            )
            GLib.idle_add(self._finish_download, None)
        except UnsplashRateLimitError as e:
            logger.error("Rate limit: %s", e)
            self._show_notification(
                "API Rate Limit", "Unsplash API rate limit exceeded."
            )
            GLib.idle_add(self._finish_download, None)
        except UnsplashNetworkError as e:
            logger.error("Network error: %s", e)
            self._show_notification(
                "Network Error",
                "Failed to download wallpaper. Check your connection.",
            )
            GLib.idle_add(self._finish_download, None)
        except Exception as e:
            logger.error(
                "Failed to download wallpaper: %s", e, exc_info=True
            )
            self._show_notification(
                "Error", f"Failed to change wallpaper: {e}"
            )
            GLib.idle_add(self._finish_download, None)

    def _validate_image_data(self, data: bytes) -> bool:
        if not data or len(data) < 32:
            return False
        if data.startswith(b"\xff\xd8"):
            return True
        if data.startswith(b"\x89PNG\r\n\x1a\n"):
            return True
        if data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
            return True
        if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
            return True
        if data.startswith(b"\x00\x00\x00") and b"ftyp" in data[4:12]:
            return True
        logger.warning(
            "Downloaded data does not match known image format signatures"
        )
        return False

    def _finish_download(self, _result: Any) -> None:
        if self._window:
            self._window.show_loading(False)

    def _apply_wallpaper(self, wallpaper: Wallpaper) -> None:
        if not wallpaper.local_path:
            return
        success = self._wallpaper_service.apply(wallpaper.local_path)
        if success:
            self._show_notification(
                "Wallpaper Changed",
                f"By {wallpaper.author}",
            )
            self._update_dashboard()
            self._append_history(wallpaper)
        self._update_tray()
        if self._tray:
            self._tray.set_attention(not success)
        self._finish_download(None)

    def _show_notification(
        self, title: str, body: str
    ) -> None:
        if not self._config.get_bool("notifications"):
            return
        try:
            subprocess.run(
                [
                    "notify-send",
                    "--app-name", APP_NAME,
                    "--icon", APP_ID,
                    title,
                    body,
                ],
                capture_output=True,
                timeout=5,
            )
        except Exception as e:
            logger.debug("Notification failed: %s", e)

    def _update_dashboard(self) -> None:
        if not self._window:
            return
        latest = self._history.get_latest()
        if latest:
            interval = self._config.get("update_interval", "1 hour")
            from datetime import datetime, timedelta

            next_time = ""
            if latest.downloaded_at:
                try:
                    dt = datetime.fromisoformat(latest.downloaded_at)
                    mins = INTERVALS.get(interval, 60)
                    next_dt = dt + timedelta(minutes=mins)
                    next_time = next_dt.strftime("%Y-%m-%d %H:%M")
                except Exception:
                    pass

            GLib.idle_add(
                self._window.update_preview,
                latest.local_path,
                latest.category,
                latest.downloaded_at or "",
                next_time,
            )

    def _append_history(self, wallpaper: Wallpaper) -> None:
        if self._window:
            GLib.idle_add(self._window.append_to_history, wallpaper)

    def _load_history(self) -> None:
        wallpapers = self._history.get_all(limit=100)
        if self._window:
            GLib.idle_add(self._window.update_history, wallpapers)

    def _load_categories(self) -> None:
        cats = self._config.get_categories()
        if self._window:
            GLib.idle_add(self._window.set_categories, cats)

    def _on_categories_changed(
        self, _window: MainWindow, categories: list[str]
    ) -> None:
        self._config.set_categories(categories)

    def _on_apply_history_wallpaper(
        self, _window: MainWindow, wp: Wallpaper
    ) -> None:
        if wp.local_path and Path(wp.local_path).exists():
            success = self._wallpaper_service.apply(wp.local_path)
            if success:
                self._show_notification(
                    "Wallpaper Applied",
                    f"By {wp.author}",
                )
                self._update_dashboard()

    def _on_delete_history_wallpaper(
        self, _window: MainWindow, wp: Wallpaper
    ) -> None:
        self._history.delete(wp.id)
        if self._window:
            GLib.idle_add(self._window.remove_from_history, wp.id)

    def _show_preferences(self) -> None:
        if not self._window:
            return
        settings = self._config.to_dict()
        prefs = PreferencesWindow(settings, self._window)
        prefs.connect("settings-changed", self._on_settings_changed)
        prefs.present()

    def _on_settings_changed(
        self, _prefs: PreferencesWindow, settings: dict[str, str]
    ) -> None:
        for key, value in settings.items():
            if key == "categories":
                continue
            current = self._config.get(key)
            if current != value:
                self._config.set(key, value)

        if "update_interval" in settings:
            self._scheduler.set_interval(
                settings["update_interval"]
            )

        if "autostart" in settings:
            if settings["autostart"] == "true":
                AutostartManager.enable_autostart()
            else:
                AutostartManager.disable_autostart()

        if "dark_mode" in settings:
            self._apply_style()

        logger.info("Settings updated")

    def _apply_style(self) -> None:
        style = self._config.get("dark_mode", "follow_system")
        manager = Adw.StyleManager.get_default()
        if style == "dark":
            manager.set_color_scheme(
                Adw.ColorScheme.FORCE_DARK
            )
        elif style == "light":
            manager.set_color_scheme(
                Adw.ColorScheme.FORCE_LIGHT
            )
        else:
            manager.set_color_scheme(
                Adw.ColorScheme.PREFER_LIGHT
            )

    def _open_wallpaper_folder(self) -> None:
        path = str(WALLPAPERS_DIR)
        try:
            WALLPAPERS_DIR.mkdir(parents=True, exist_ok=True)
            subprocess.Popen(
                ["xdg-open", path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as e:
            logger.error(
                "Failed to open wallpaper folder: %s", e
            )

    def _update_tray(self) -> None:
        if self._tray:
            self._tray.set_icon(APP_ID)

    def run(self, args: list[str] | None = None) -> None:
        if args is None:
            args = sys.argv[1:]

        if "--daemon" in args:
            self._daemon_mode = True
        if "--tray" in args:
            self._tray_mode = True

        if "--install-service" in args:
            AutostartManager.install_systemd_service()
            AutostartManager.install_systemd_timer()
            AutostartManager.enable_systemd_service()
            print("Systemd service installed and started")
            return

        if "--remove-service" in args:
            AutostartManager.disable_systemd_service()
            AutostartManager.remove_systemd_service()
            print("Systemd service removed")
            return

        if "--version" in args:
            print(f"{APP_NAME} v{VERSION}")
            return

        if "--diagnostics" in args:
            self._setup_logging()
            self._log_startup_diagnostics()
            return

        super().run(args)

    @staticmethod
    def main() -> None:
        app = UnsplashWallpaperApp()
        app.run()
