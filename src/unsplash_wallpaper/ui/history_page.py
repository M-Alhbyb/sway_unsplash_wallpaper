from __future__ import annotations

import logging
import threading
from pathlib import Path

import gi

gi.require_version("Adw", "1")
gi.require_version("Gtk", "4.0")

from gi.repository import Adw, GdkPixbuf, GLib, GObject, Gtk

from unsplash_wallpaper.models.wallpaper import Wallpaper

logger = logging.getLogger(__name__)


_THUMBNAIL_SEM = threading.BoundedSemaphore(4)


class HistoryPage(Adw.Bin):
    __gsignals__ = {
        "apply-wallpaper": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (GObject.TYPE_PYOBJECT,),
        ),
        "delete-wallpaper": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (GObject.TYPE_PYOBJECT,),
        ),
    }

    def __init__(
        self,
        wallpapers: list[Wallpaper] | None = None,
    ) -> None:
        super().__init__()
        self._wallpapers: list[Wallpaper] = wallpapers or []
        self._thumbnail_cache: dict[int, GdkPixbuf.Pixbuf | None] = {}
        self._cache_lock = threading.Lock()
        self._build_ui()

    def _build_ui(self) -> None:
        self._main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_child(self._main_box)

        header = Gtk.Label()
        header.set_markup("<b>Wallpaper History</b>")
        header.set_xalign(0.0)
        header.set_margin_start(12)
        header.set_margin_top(12)
        header.set_margin_bottom(6)
        self._main_box.append(header)

        scrolled = Gtk.ScrolledWindow(vexpand=True)
        scrolled.set_policy(
            Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC
        )
        self._main_box.append(scrolled)

        self._list_box = Gtk.ListBox()
        self._list_box.add_css_class("boxed-list")
        scrolled.set_child(self._list_box)

        self._empty_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
            halign=Gtk.Align.CENTER,
            valign=Gtk.Align.CENTER,
            margin_top=48,
            margin_bottom=48,
        )
        empty_icon = Gtk.Image()
        empty_icon.set_from_icon_name("image-x-generic")
        empty_icon.set_pixel_size(48)
        self._empty_box.append(empty_icon)
        empty_label = Gtk.Label(
            label="No wallpapers in history yet.\nClick 'Change Now' to "
                  "download your first wallpaper.",
            justify=Gtk.Justification.CENTER,
        )
        empty_label.add_css_class("dim-label")
        self._empty_box.append(empty_label)

        self._refresh_list()

    def _refresh_list(self) -> None:
        while True:
            child = self._list_box.get_first_child()
            if child is None:
                break
            self._list_box.remove(child)

        if not self._wallpapers:
            self._list_box.append(self._empty_box)
            return

        for wp in self._wallpapers:
            row = self._create_wallpaper_row(wp)
            self._list_box.append(row)

    def _load_thumbnail_async(
        self, wp: Wallpaper, image_widget: Gtk.Image
    ) -> None:
        if wp.id is not None:
            with self._cache_lock:
                cached = self._thumbnail_cache.get(wp.id)
                if cached is not None:
                    self._set_thumbnail(image_widget, cached)
                    return

        def load() -> None:
            with _THUMBNAIL_SEM:
                if wp.id is not None:
                    with self._cache_lock:
                        cached = self._thumbnail_cache.get(wp.id)
                        if cached is not None:
                            GLib.idle_add(
                                self._set_thumbnail, image_widget, cached
                            )
                            return

                pixbuf = None
                if wp.local_path and Path(wp.local_path).exists():
                    try:
                        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                            wp.local_path, 80, 60, True
                        )
                    except Exception as e:
                        logger.debug(
                            "Failed to load thumbnail for %s: %s",
                            wp.unsplash_id, e,
                        )
                if wp.id is not None and pixbuf is not None:
                    with self._cache_lock:
                        self._thumbnail_cache[wp.id] = pixbuf
                GLib.idle_add(
                    self._set_thumbnail, image_widget, pixbuf
                )

        threading.Thread(target=load, daemon=True).start()

    def _set_thumbnail(
        self, image: Gtk.Image, pixbuf: GdkPixbuf.Pixbuf | None
    ) -> None:
        if pixbuf:
            image.set_from_pixbuf(pixbuf)
        else:
            image.set_from_icon_name("image-x-generic")

    def _create_wallpaper_row(self, wp: Wallpaper) -> Gtk.Widget:
        box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=12,
            margin_start=12,
            margin_end=12,
            margin_top=6,
            margin_bottom=6,
        )

        thumb = Gtk.Image()
        thumb.set_size_request(80, 60)
        thumb.set_from_icon_name("image-x-generic")
        box.append(thumb)

        self._load_thumbnail_async(wp, thumb)

        info_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=3
        )
        info_box.set_hexpand(True)

        author_label = Gtk.Label(
            label=wp.author or "Unknown Author"
        )
        author_label.set_xalign(0.0)
        author_label.add_css_class("heading")
        info_box.append(author_label)

        if wp.category:
            cat_label = Gtk.Label(label=wp.category)
            cat_label.set_xalign(0.0)
            cat_label.add_css_class("caption")
            info_box.append(cat_label)

        date_label = Gtk.Label(label=wp.downloaded_at or "")
        date_label.set_xalign(0.0)
        date_label.add_css_class("caption")
        info_box.append(date_label)

        box.append(info_box)

        apply_btn = Gtk.Button(label="Apply")
        apply_btn.add_css_class("flat")
        apply_btn.connect("clicked", self._on_apply, wp)
        box.append(apply_btn)

        delete_btn = Gtk.Button(label="Delete")
        delete_btn.add_css_class("flat")
        delete_btn.add_css_class("destructive-action")
        delete_btn.connect("clicked", self._on_delete, wp)
        box.append(delete_btn)

        return box

    def _on_apply(self, _btn: Gtk.Button, wp: Wallpaper) -> None:
        self.emit("apply-wallpaper", wp)

    def _on_delete(self, _btn: Gtk.Button, wp: Wallpaper) -> None:
        self.emit("delete-wallpaper", wp)

    def set_wallpapers(self, wallpapers: list[Wallpaper]) -> None:
        self._wallpapers = wallpapers
        self._thumbnail_cache.clear()
        self._refresh_list()

    def append_wallpaper(self, wp: Wallpaper) -> None:
        self._wallpapers.insert(0, wp)
        self._refresh_list()

    def remove_wallpaper(self, wallpaper_id: int) -> None:
        self._wallpapers = [
            wp for wp in self._wallpapers if wp.id != wallpaper_id
        ]
        self._thumbnail_cache.pop(wallpaper_id, None)
        self._refresh_list()
