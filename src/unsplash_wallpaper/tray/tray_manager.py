from __future__ import annotations

import logging

import gi

gi.require_version("Adw", "1")
gi.require_version("Gtk", "4.0")

from gi.repository import Gtk

logger = logging.getLogger(__name__)


class TrayManager:
    def __init__(self, application: Gtk.Application) -> None:
        self._app = application
        self._indicator = None
        self._AppIndicator = None

    def setup(self) -> bool:
        try:
            from gi.repository import AyatanaAppIndicator3 as AppIndicator

            self._AppIndicator = AppIndicator
            self._indicator = AppIndicator.Indicator.new(
                "com.unsplash.wallpaper",
                "com.unsplash.wallpaper",
                AppIndicator.IndicatorCategory.APPLICATION_STATUS,
            )
            self._indicator.set_status(
                AppIndicator.IndicatorStatus.ACTIVE
            )

            menu = Gtk.Menu()

            change_item = Gtk.MenuItem(label="Change Wallpaper Now")
            change_item.connect("activate", self._on_change)
            menu.append(change_item)

            dash_item = Gtk.MenuItem(label="Open Dashboard")
            dash_item.connect("activate", self._on_open_dashboard)
            menu.append(dash_item)

            settings_item = Gtk.MenuItem(label="Settings")
            settings_item.connect("activate", self._on_open_settings)
            menu.append(settings_item)

            folder_item = Gtk.MenuItem(label="Open Wallpaper Folder")
            folder_item.connect("activate", self._on_open_folder)
            menu.append(folder_item)

            menu.append(Gtk.SeparatorMenuItem())

            quit_item = Gtk.MenuItem(label="Quit")
            quit_item.connect("activate", self._on_quit)
            menu.append(quit_item)

            menu.show_all()
            self._indicator.set_menu(menu)
            return True

        except (ImportError, ValueError) as e:
            logger.debug(
                "Tray support unavailable: %s", e
            )
            return False

    def _on_change(self, _item: Gtk.MenuItem) -> None:
        self._app.activate_action("change-wallpaper", None)

    def _on_open_dashboard(self, _item: Gtk.MenuItem) -> None:
        self._app.activate_action("open-dashboard", None)

    def _on_open_settings(self, _item: Gtk.MenuItem) -> None:
        self._app.activate_action("preferences", None)

    def _on_open_folder(self, _item: Gtk.MenuItem) -> None:
        self._app.activate_action("open-folder", None)

    def _on_quit(self, _item: Gtk.MenuItem) -> None:
        self._app.quit()

    def set_icon(self, icon_name: str) -> None:
        if self._indicator is not None:
            try:
                self._indicator.set_icon(icon_name)
            except Exception:
                pass

    def set_attention(self, active: bool) -> None:
        if self._indicator is not None and self._AppIndicator is not None:
            try:
                if active:
                    self._indicator.set_status(
                        self._AppIndicator.IndicatorStatus.ATTENTION
                    )
                else:
                    self._indicator.set_status(
                        self._AppIndicator.IndicatorStatus.ACTIVE
                    )
            except Exception:
                pass

    def shutdown(self) -> None:
        if self._indicator is not None and self._AppIndicator is not None:
            try:
                self._indicator.set_status(
                    self._AppIndicator.IndicatorStatus.PASSIVE
                )
            except Exception:
                pass
            self._indicator = None
