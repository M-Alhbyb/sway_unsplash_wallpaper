from __future__ import annotations

import logging
from typing import Any

from unsplash_wallpaper.constants import DEFAULT_SETTINGS
from unsplash_wallpaper.database import Database

logger = logging.getLogger(__name__)


class Config:
    def __init__(self, database: Database | None = None) -> None:
        self._db = database or Database.get_instance()
        self._cache: dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        stored = self._db.get_all_settings()
        for key, default in DEFAULT_SETTINGS.items():
            self._cache[key] = stored.get(key, default)
        for key, value in stored.items():
            if key not in self._cache:
                self._cache[key] = value

    def get(self, key: str, default: str | None = None) -> str:
        return self._cache.get(
            key, DEFAULT_SETTINGS.get(key, default or "")
        )

    def set(self, key: str, value: str) -> None:
        self._cache[key] = value
        self._db.set_setting(key, value)

    def get_bool(self, key: str) -> bool:
        return self.get(key, "false").lower() in ("true", "1", "yes")

    def set_bool(self, key: str, value: bool) -> None:
        self.set(key, "true" if value else "false")

    def get_int(self, key: str, default: int = 0) -> int:
        val = self.get(key)
        try:
            return int(val)
        except (ValueError, TypeError):
            return default

    def get_categories(self) -> list[str]:
        cats = self.get("categories", "")
        if not cats:
            return []
        return [c.strip() for c in cats.split(",") if c.strip()]

    def set_categories(self, categories: list[str]) -> None:
        self.set("categories", ",".join(categories))

    def get_resolution(self) -> str:
        return self.get("resolution", "full_hd")

    def get_interval(self) -> str:
        return self.get("update_interval", "1 hour")

    def has_valid_api_key(self) -> bool:
        key = self.get("unsplash_access_key", "")
        return bool(key) and len(key) > 10

    def reload(self) -> None:
        self._cache.clear()
        self._load()

    def to_dict(self) -> dict[str, str]:
        return dict(self._cache)
