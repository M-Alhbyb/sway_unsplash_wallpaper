from __future__ import annotations

import gi

gi.require_version("Adw", "1")
gi.require_version("Gtk", "4.0")

from gi.repository import Adw, GObject, Gtk

from unsplash_wallpaper.constants import CATEGORIES, CATEGORY_LABELS


class CategoryPage(Adw.Bin):
    __gsignals__ = {
        "categories-changed": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (GObject.TYPE_PYOBJECT,),
        ),
    }

    def __init__(self, selected_categories: list[str] | None = None) -> None:
        super().__init__()
        self._selected: set[str] = set(selected_categories or [])
        self._loading = False
        self._build_ui()

    def _build_ui(self) -> None:
        clamp = Adw.Clamp()
        self.set_child(clamp)

        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
            margin_start=12,
            margin_end=12,
            margin_top=12,
            margin_bottom=12,
        )
        clamp.set_child(box)

        title = Gtk.Label()
        title.set_markup("<b>Wallpaper Categories</b>")
        title.set_xalign(0.0)
        box.append(title)

        subtitle = Gtk.Label(label="Select categories to include")
        subtitle.add_css_class("caption")
        subtitle.set_xalign(0.0)
        box.append(subtitle)

        grid = Gtk.Grid(
            column_spacing=6,
            row_spacing=6,
            margin_top=6,
            column_homogeneous=True,
        )
        box.append(grid)

        self._toggle_buttons: dict[str, Gtk.ToggleButton] = {}
        for i, cat in enumerate(CATEGORIES):
            label_text = CATEGORY_LABELS.get(cat, cat.title())
            btn = Gtk.ToggleButton(label=label_text)
            btn.add_css_class("category-btn")
            btn.set_active(cat in self._selected)
            btn.connect("toggled", self._on_toggle, cat)
            self._toggle_buttons[cat] = btn
            grid.attach(btn, i % 3, i // 3, 1, 1)

        self._select_all_btn = Gtk.Button(label="Select All")
        self._select_all_btn.connect("clicked", self._on_select_all)
        self._clear_btn = Gtk.Button(label="Clear")
        self._clear_btn.connect("clicked", self._on_clear)

        btn_box = Gtk.Box(spacing=6, margin_top=12)
        btn_box.append(self._select_all_btn)
        btn_box.append(self._clear_btn)
        box.append(btn_box)

    def _on_toggle(self, button: Gtk.ToggleButton, category: str) -> None:
        if button.get_active():
            self._selected.add(category)
        else:
            self._selected.discard(category)
        if not self._loading:
            self._emit_changed()

    def _on_select_all(self, _button: Gtk.Button) -> None:
        self._loading = True
        for cat in CATEGORIES:
            self._toggle_buttons[cat].set_active(True)
            self._selected.add(cat)
        self._loading = False
        self._emit_changed()

    def _on_clear(self, _button: Gtk.Button) -> None:
        self._loading = True
        for cat in CATEGORIES:
            self._toggle_buttons[cat].set_active(False)
            self._selected.clear()
        self._loading = False
        self._emit_changed()

    def _emit_changed(self) -> None:
        self.emit("categories-changed", list(self._selected))

    def get_selected(self) -> list[str]:
        return list(self._selected)

    def set_selected(self, categories: list[str]) -> None:
        self._selected = set(categories)
        self._loading = True
        for cat in CATEGORIES:
            if cat in self._toggle_buttons:
                self._toggle_buttons[cat].set_active(cat in self._selected)
        self._loading = False
        self._emit_changed()
