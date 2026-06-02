from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import gi

gi.require_version("Adw", "1")
gi.require_version("Gtk", "4.0")

from gi.repository import Adw, GdkPixbuf, Gio, GObject, Gtk

from unsplash_wallpaper.constants import (
    APP_NAME,
    CATEGORY_LABELS,
    VERSION,
)
from unsplash_wallpaper.models.wallpaper import Wallpaper
from unsplash_wallpaper.ui.category_page import CategoryPage
from unsplash_wallpaper.ui.history_page import HistoryPage

logger = logging.getLogger(__name__)


class MainWindow(Adw.ApplicationWindow):
    __gsignals__ = {
        "change-wallpaper": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (),
        ),
        "open-settings": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (),
        ),
        "open-folder": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (),
        ),
        "categories-changed": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (GObject.TYPE_PYOBJECT,),
        ),
        "apply-history-wallpaper": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (GObject.TYPE_PYOBJECT,),
        ),
        "delete-history-wallpaper": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (GObject.TYPE_PYOBJECT,),
        ),
    }

    def __init__(
        self,
        application: Adw.Application,
        **kwargs: Any,
    ) -> None:
        super().__init__(application=application, **kwargs)
        self.set_title(APP_NAME)
        self.set_default_size(800, 600)

        self._current_wallpaper_path: str | None = None
        self._last_update: str = ""
        self._next_update: str = ""
        self._current_category: str = ""
        self._history_page: HistoryPage | None = None
        self._loading_overlay: Gtk.Overlay | None = None
        self._loading_spinner: Gtk.Spinner | None = None
        self._first_run_overlay: Gtk.Box | None = None

        self._build_ui()

    def _build_ui(self) -> None:
        overlay = Gtk.Overlay()
        self.set_content(overlay)
        self._loading_overlay = overlay

        toolbar_view = Adw.ToolbarView()
        overlay.set_child(toolbar_view)

        header = Adw.HeaderBar()
        toolbar_view.add_top_bar(header)

        menu = Gio.Menu()
        menu.append("Preferences", "app.preferences")
        menu.append("About", "app.about")
        menu.append("Quit", "app.quit")

        burger = Gtk.MenuButton()
        burger.set_icon_name("open-menu-symbolic")
        burger.set_menu_model(menu)
        header.pack_end(burger)

        change_btn = Gtk.Button(label="Change Now")
        change_btn.add_css_class("suggested-action")
        change_btn.connect("clicked", self._on_change_now)
        header.pack_start(change_btn)

        self._stack = Adw.ViewStack()
        toolbar_view.set_content(self._stack)

        dashboard = self._build_dashboard()
        self._stack.add_titled(dashboard, "dashboard", "Dashboard")

        self._category_page = CategoryPage()
        self._category_page.connect(
            "categories-changed", self._on_categories_changed
        )
        self._stack.add_titled(
            self._category_page, "categories", "Categories"
        )

        self._history_page = HistoryPage()
        self._history_page.connect(
            "apply-wallpaper", self._on_apply_history
        )
        self._history_page.connect(
            "delete-wallpaper", self._on_delete_history
        )
        self._stack.add_titled(
            self._history_page, "history", "History"
        )

        switcher = Adw.ViewSwitcher()
        switcher.set_stack(self._stack)
        switcher.set_policy(Adw.ViewSwitcherPolicy.WIDE)
        header.set_title_widget(switcher)

        # Loading spinner overlay
        spinner_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            halign=Gtk.Align.CENTER,
            valign=Gtk.Align.CENTER,
        )
        spinner_box.add_css_class("loading-overlay")
        spinner_box.set_visible(False)
        self._loading_spinner = Gtk.Spinner()
        self._loading_spinner.set_size_request(32, 32)
        spinner_box.append(self._loading_spinner)
        loading_label = Gtk.Label(label="Downloading wallpaper...")
        spinner_box.append(loading_label)
        overlay.add_overlay(spinner_box)
        self._spinner_box = spinner_box

    def _build_dashboard(self) -> Gtk.Widget:
        page = Adw.Bin()
        clamp = Adw.Clamp()
        page.set_child(clamp)

        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
            margin_start=24,
            margin_end=24,
            margin_top=24,
            margin_bottom=24,
        )
        clamp.set_child(box)

        # First-run prompt (hidden by default)
        first_run_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
            margin_top=24,
            margin_bottom=12,
            hexpand=True,
            css_classes=["card"],
        )
        first_run_box.set_margin_start(12)
        first_run_box.set_margin_end(12)
        first_run_box.set_margin_top(12)
        first_run_box.set_margin_bottom(12)

        first_run_icon = Gtk.Image()
        first_run_icon.set_from_icon_name("preferences-system-symbolic")
        first_run_icon.set_pixel_size(48)
        first_run_box.append(first_run_icon)

        first_run_title = Gtk.Label()
        first_run_title.set_markup("<b>Welcome to Unsplash Wallpaper</b>")
        first_run_box.append(first_run_title)

        first_run_desc = Gtk.Label(
            label="To get started, you need to configure your Unsplash API access key.",
            wrap=True,
            max_width_chars=50,
        )
        first_run_box.append(first_run_desc)

        first_run_btn = Gtk.Button(label="Configure API Key")
        first_run_btn.add_css_class("suggested-action")
        first_run_btn.connect("clicked", self._on_open_settings)
        first_run_box.append(first_run_btn)

        first_run_help = Gtk.Label(
            label="Get your key at unsplash.com/developers",
            css_classes=["caption"],
        )
        first_run_box.append(first_run_help)

        box.append(first_run_box)
        self._first_run_box = first_run_box

        # Current wallpaper preview
        preview_frame = Gtk.Frame(css_classes=["card"])
        preview_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=6
        )
        preview_box.set_margin_start(12)
        preview_box.set_margin_end(12)
        preview_box.set_margin_top(12)
        preview_box.set_margin_bottom(12)
        preview_frame.set_child(preview_box)

        preview_title = Gtk.Label()
        preview_title.set_markup("<b>Current Wallpaper</b>")
        preview_title.set_xalign(0.0)
        preview_box.append(preview_title)

        self._preview_image = Gtk.Image()
        self._preview_image.set_size_request(320, 200)
        self._preview_image.set_from_icon_name("image-x-generic")
        self._preview_image.set_pixel_size(64)
        preview_box.append(self._preview_image)

        self._preview_info = Gtk.Label(
            label="No wallpaper set. Click 'Change Now' to get started.",
            xalign=0.0,
            wrap=True,
        )
        preview_box.append(self._preview_info)

        self._preview_status = Gtk.Label(
            xalign=0.0,
            css_classes=["caption"],
        )
        preview_box.append(self._preview_status)

        box.append(preview_frame)

        # Info grid
        info_frame = Gtk.Frame(css_classes=["card"])
        info_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=6
        )
        info_box.set_margin_start(12)
        info_box.set_margin_end(12)
        info_box.set_margin_top(12)
        info_box.set_margin_bottom(12)
        info_frame.set_child(info_box)

        info_title = Gtk.Label()
        info_title.set_markup("<b>Information</b>")
        info_title.set_xalign(0.0)
        info_box.append(info_title)

        info_grid = Gtk.Grid(
            column_spacing=12, row_spacing=6, margin_top=6
        )
        info_grid.attach(
            Gtk.Label(label="Current Category:", xalign=1.0), 0, 0, 1, 1
        )
        self._category_label = Gtk.Label(
            label="None", xalign=0.0, hexpand=True
        )
        info_grid.attach(self._category_label, 1, 0, 1, 1)

        info_grid.attach(
            Gtk.Label(label="Last Update:", xalign=1.0), 0, 1, 1, 1
        )
        self._last_update_label = Gtk.Label(
            label="Never", xalign=0.0, hexpand=True
        )
        info_grid.attach(self._last_update_label, 1, 1, 1, 1)

        info_grid.attach(
            Gtk.Label(label="Next Update:", xalign=1.0), 0, 2, 1, 1
        )
        self._next_update_label = Gtk.Label(
            label="Not scheduled", xalign=0.0, hexpand=True
        )
        info_grid.attach(self._next_update_label, 1, 2, 1, 1)

        info_box.append(info_grid)
        box.append(info_frame)

        # Action buttons
        btn_box = Gtk.Box(spacing=6, homogeneous=True)
        btn_box.set_margin_top(6)

        folder_btn = Gtk.Button(label="Open Wallpaper Folder")
        folder_btn.connect("clicked", self._on_open_folder)
        btn_box.append(folder_btn)

        history_btn = Gtk.Button(label="Open History")
        history_btn.connect("clicked", self._on_open_history)
        btn_box.append(history_btn)

        settings_btn = Gtk.Button(label="Settings")
        settings_btn.connect("clicked", self._on_open_settings)
        btn_box.append(settings_btn)

        box.append(btn_box)

        version_label = Gtk.Label(label=f"v{VERSION}")
        version_label.add_css_class("dim-label")
        version_label.set_margin_top(12)
        box.append(version_label)

        return page

    def show_first_run_prompt(self) -> None:
        if self._first_run_box:
            self._first_run_box.set_visible(True)
        if self._preview_info:
            self._preview_info.set_label(
                "No API key configured. Click 'Configure API Key' above to get started."
            )

    def show_loading(self, active: bool) -> None:
        if not self._spinner_box:
            return
        self._spinner_box.set_visible(active)
        if active:
            self._loading_spinner.start()
        else:
            self._loading_spinner.stop()

    # --- Signal handlers ---

    def _on_change_now(self, _btn: Gtk.Button) -> None:
        self.emit("change-wallpaper")

    def _on_open_folder(self, _btn: Gtk.Button) -> None:
        self.emit("open-folder")

    def _on_open_history(self, _btn: Gtk.Button) -> None:
        self._stack.set_visible_child_name("history")

    def _on_open_settings(self, _btn: Gtk.Button) -> None:
        self.emit("open-settings")

    def _on_categories_changed(
        self, _page: CategoryPage, categories: list[str]
    ) -> None:
        self.emit("categories-changed", categories)

    def _on_apply_history(
        self, _page: HistoryPage, wp: Wallpaper
    ) -> None:
        self.emit("apply-history-wallpaper", wp)

    def _on_delete_history(
        self, _page: HistoryPage, wp: Wallpaper
    ) -> None:
        self.emit("delete-history-wallpaper", wp)

    # --- Public API ---

    def update_preview(
        self,
        wallpaper_path: str | None = None,
        category: str = "",
        last_update: str = "",
        next_update: str = "",
    ) -> None:
        if wallpaper_path:
            self._current_wallpaper_path = wallpaper_path
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    wallpaper_path, 320, 200, True
                )
                if pixbuf:
                    self._preview_image.set_from_pixbuf(pixbuf)
                else:
                    self._preview_image.set_from_icon_name(
                        "image-x-generic"
                    )
            except Exception:
                self._preview_image.set_from_icon_name(
                    "image-x-generic"
                )
            self._preview_info.set_label(
                f"Path: {Path(wallpaper_path).name}"
            )
            self._preview_status.set_label("")

        if category:
            self._current_category = category
            self._category_label.set_label(
                CATEGORY_LABELS.get(category, category.title())
            )
        self._last_update = last_update or self._last_update
        if self._last_update:
            self._last_update_label.set_label(self._last_update)
        self._next_update = next_update or self._next_update
        if self._next_update:
            self._next_update_label.set_label(self._next_update)

        if self._first_run_box:
            self._first_run_box.set_visible(False)

    def update_history(
        self, wallpapers: list[Wallpaper]
    ) -> None:
        if self._history_page:
            self._history_page.set_wallpapers(wallpapers)

    def append_to_history(self, wp: Wallpaper) -> None:
        if self._history_page:
            self._history_page.append_wallpaper(wp)

    def remove_from_history(self, wallpaper_id: int) -> None:
        if self._history_page:
            self._history_page.remove_wallpaper(wallpaper_id)

    def set_categories(self, categories: list[str]) -> None:
        self._category_page.set_selected(categories)
