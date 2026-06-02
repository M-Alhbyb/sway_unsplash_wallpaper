from __future__ import annotations

import logging
import subprocess
from typing import Any

import gi
gi.require_version("Adw", "1")
gi.require_version("Gtk", "4.0")

from gi.repository import Adw, GObject, Gtk

from unsplash_wallpaper.constants import (
    CATEGORIES,
    CATEGORY_LABELS,
    DEFAULT_INTERVAL,
    INTERVALS,
    RESOLUTION_KEYS,
    RESOLUTIONS,
)

logger = logging.getLogger(__name__)


class PreferencesWindow(Adw.PreferencesWindow):
    __gsignals__ = {
        "settings-changed": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (GObject.TYPE_PYOBJECT,),
        ),
    }

    def __init__(self, settings: dict[str, str], parent: Gtk.Window | None = None) -> None:
        super().__init__()
        self.set_transient_for(parent)
        self.set_modal(True)
        self.set_title("Preferences")
        self.set_default_size(500, 600)

        self._settings = dict(settings)
        self._build_ui()

    def _build_ui(self) -> None:
        # Wrap groups in pages
        api_page = Adw.PreferencesPage()
        api_page.set_title("API")
        self.add(api_page)

        api_group = Adw.PreferencesGroup(title="Unsplash API")
        api_page.add(api_group)

        self._api_key_row = Adw.PasswordEntryRow(title="Access Key")
        self._api_key_row.set_text(self._settings.get("unsplash_access_key", ""))
        self._api_key_row.connect("notify::text", self._on_key_changed)
        api_group.add(self._api_key_row)

        self._key_status = Adw.ActionRow()
        self._key_status.set_subtitle("Not validated")
        api_group.add(self._key_status)

        api_help = Adw.ActionRow()
        api_help.set_subtitle(
            "Get your access key from https://unsplash.com/developers"
        )
        open_btn = Gtk.Button(label="Open", css_classes=["flat"])
        open_btn.connect("clicked", self._on_open_unsplash)
        api_help.add_suffix(open_btn)
        api_group.add(api_help)

        # General page
        general_page = Adw.PreferencesPage()
        general_page.set_title("General")
        self.add(general_page)

        general_group = Adw.PreferencesGroup(title="General Settings")
        general_page.add(general_group)

        self._interval_row = Adw.ComboRow(title="Update Interval")
        interval_list = Gtk.StringList.new(list(INTERVALS.keys()))
        self._interval_row.set_model(interval_list)
        current_interval = self._settings.get(
            "update_interval", DEFAULT_INTERVAL
        )
        interval_keys = list(INTERVALS.keys())
        if current_interval in interval_keys:
            self._interval_row.set_selected(interval_keys.index(current_interval))
        self._interval_row.connect("notify::selected", self._on_setting_changed)
        general_group.add(self._interval_row)

        self._resolution_row = Adw.ComboRow(title="Preferred Resolution")
        res_list = Gtk.StringList.new(
            [RESOLUTIONS[r]["label"] for r in RESOLUTION_KEYS]
        )
        self._resolution_row.set_model(res_list)
        current_res = self._settings.get("resolution", "full_hd")
        if current_res in RESOLUTION_KEYS:
            self._resolution_row.set_selected(RESOLUTION_KEYS.index(current_res))
        self._resolution_row.connect("notify::selected", self._on_setting_changed)
        general_group.add(self._resolution_row)

        self._max_count_row = Adw.SpinRow(
            title="Max Stored Wallpapers",
            adjustment=Gtk.Adjustment(
                value=float(self._settings.get("max_wallpapers", "100")),
                lower=10,
                upper=500,
                step_increment=10,
            ),
        )
        self._max_count_row.connect("notify::value", self._on_setting_changed)
        general_group.add(self._max_count_row)

        # Options page
        options_page = Adw.PreferencesPage()
        options_page.set_title("Options")
        self.add(options_page)

        toggles_group = Adw.PreferencesGroup(title="Options")
        options_page.add(toggles_group)

        self._autostart_row = Adw.SwitchRow(title="Auto Start")
        self._autostart_row.set_active(
            self._settings.get("autostart", "false").lower() == "true"
        )
        self._autostart_row.set_subtitle("Start automatically after login")
        self._autostart_row.connect("notify::active", self._on_setting_changed)
        toggles_group.add(self._autostart_row)

        self._notifications_row = Adw.SwitchRow(title="Notifications")
        self._notifications_row.set_active(
            self._settings.get("notifications", "true").lower() == "true"
        )
        self._notifications_row.connect("notify::active", self._on_setting_changed)
        toggles_group.add(self._notifications_row)

        categories_group = Adw.PreferencesGroup(title="Categories")
        categories_group.set_description("Select wallpaper categories")
        options_page.add(categories_group)

        categories_flow = Gtk.FlowBox(
            homogeneous=True,
            max_children_per_line=4,
            min_children_per_line=2,
            selection_mode=Gtk.SelectionMode.NONE,
            column_spacing=6,
            row_spacing=6,
            margin_top=6,
        )
        categories_group.add(categories_flow)

        from unsplash_wallpaper.constants import CATEGORIES, CATEGORY_LABELS
        self._cat_toggles: dict[str, Gtk.ToggleButton] = {}
        current_cats = self._settings.get("categories", "").split(",") if self._settings.get("categories") else []
        for cat in CATEGORIES:
            label = CATEGORY_LABELS.get(cat, cat.title())
            btn = Gtk.ToggleButton(label=label)
            btn.set_active(cat in current_cats)
            btn.connect("toggled", self._on_cat_toggled, cat)
            self._cat_toggles[cat] = btn
            categories_flow.append(btn)

        dark_group = Adw.PreferencesGroup(title="Appearance")
        options_page.add(dark_group)

        self._dark_mode_row = Adw.ComboRow(title="Dark Mode")
        dark_modes = Gtk.StringList.new(
            ["Follow System", "Light", "Dark"]
        )
        self._dark_mode_row.set_model(dark_modes)
        current_dark = self._settings.get("dark_mode", "follow_system")
        mapping = {"follow_system": 0, "light": 1, "dark": 2}
        self._dark_mode_row.set_selected(
            mapping.get(current_dark, 0)
        )
        self._dark_mode_row.connect(
            "notify::selected", self._on_setting_changed
        )
        dark_group.add(self._dark_mode_row)

    def _on_cat_toggled(self, btn: Gtk.ToggleButton, cat: str) -> None:
        self._on_setting_changed(btn)

    def _on_key_changed(self, *args: Any) -> None:
        key = self._api_key_row.get_text()
        if not key:
            self._key_status.set_subtitle("Required for API access")
        elif len(key) < 10:
            self._key_status.set_subtitle("Key seems too short")
        else:
            self._key_status.set_subtitle("Key looks valid (validated on use)")
        self._on_setting_changed(*args)

    def _on_open_unsplash(self, _btn: Gtk.Button) -> None:
        try:
            subprocess.Popen(
                ["xdg-open", "https://unsplash.com/developers"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass

    def _on_setting_changed(self, _widget: Gtk.Widget, *args: Any) -> None:
        self._collect_settings()
        self.emit("settings-changed", self._settings)

    def _collect_settings(self) -> None:
        self._settings["unsplash_access_key"] = self._api_key_row.get_text()

        interval_idx = self._interval_row.get_selected()
        interval_keys = list(INTERVALS.keys())
        if 0 <= interval_idx < len(interval_keys):
            self._settings["update_interval"] = interval_keys[interval_idx]

        res_idx = self._resolution_row.get_selected()
        if 0 <= res_idx < len(RESOLUTION_KEYS):
            self._settings["resolution"] = RESOLUTION_KEYS[res_idx]

        self._settings["categories"] = ",".join(
            cat for cat, btn in self._cat_toggles.items() if btn.get_active()
        )
        self._settings["max_wallpapers"] = str(
            int(self._max_count_row.get_value())
        )
        self._settings["autostart"] = (
            "true" if self._autostart_row.get_active() else "false"
        )
        self._settings["notifications"] = (
            "true" if self._notifications_row.get_active() else "false"
        )

        dark_idx = self._dark_mode_row.get_selected()
        dark_mapping = {0: "follow_system", 1: "light", 2: "dark"}
        self._settings["dark_mode"] = dark_mapping.get(dark_idx, "follow_system")

    def get_settings(self) -> dict[str, str]:
        self._collect_settings()
        return dict(self._settings)

    def update_settings(self, settings: dict[str, str]) -> None:
        self._settings.update(settings)
        self._api_key_row.set_text(
            self._settings.get("unsplash_access_key", "")
        )
        interval_keys = list(INTERVALS.keys())
        interval = self._settings.get("update_interval", DEFAULT_INTERVAL)
        if interval in interval_keys:
            self._interval_row.set_selected(interval_keys.index(interval))
        res = self._settings.get("resolution", "full_hd")
        if res in RESOLUTION_KEYS:
            self._resolution_row.set_selected(RESOLUTION_KEYS.index(res))
        self._max_count_row.set_value(
            float(self._settings.get("max_wallpapers", "100"))
        )
        self._autostart_row.set_active(
            self._settings.get("autostart", "false").lower() == "true"
        )
        self._notifications_row.set_active(
            self._settings.get("notifications", "true").lower() == "true"
        )
        current_cats = self._settings.get("categories", "").split(",") if self._settings.get("categories") else []
        for cat, btn in self._cat_toggles.items():
            btn.set_active(cat in current_cats)
        dark_mapping_rev = {
            "follow_system": 0,
            "light": 1,
            "dark": 2,
        }
        self._dark_mode_row.set_selected(
            dark_mapping_rev.get(
                self._settings.get("dark_mode", "follow_system"), 0
            )
        )
