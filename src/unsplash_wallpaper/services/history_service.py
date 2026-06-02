from __future__ import annotations

import logging
from typing import Any

from unsplash_wallpaper.config import Config
from unsplash_wallpaper.constants import DEFAULT_MAX_WALLPAPERS
from unsplash_wallpaper.database import Database
from unsplash_wallpaper.models.wallpaper import Wallpaper
from unsplash_wallpaper.services.storage_service import StorageService

logger = logging.getLogger(__name__)


class HistoryService:
    def __init__(
        self,
        database: Database | None = None,
        storage: StorageService | None = None,
        config: Config | None = None,
    ) -> None:
        self._db = database or Database.get_instance()
        self._storage = storage or StorageService()
        self._config = config or Config()

    def add(self, wallpaper: Wallpaper) -> Wallpaper:
        wp_id = self._db.add_wallpaper(wallpaper)
        wallpaper.id = wp_id
        self._enforce_retention()
        logger.info(
            "Added wallpaper %s to history", wallpaper.unsplash_id
        )
        return wallpaper

    def get_all(
        self, limit: int = 100, offset: int = 0
    ) -> list[Wallpaper]:
        return self._db.get_wallpapers(limit=limit, offset=offset)

    def get_latest(self) -> Wallpaper | None:
        return self._db.get_latest_wallpaper()

    def get(self, wallpaper_id: int) -> Wallpaper | None:
        return self._db.get_wallpaper(wallpaper_id)

    def delete(self, wallpaper_id: int) -> bool:
        wallpaper = self._db.get_wallpaper(wallpaper_id)
        if wallpaper is None:
            return False
        if wallpaper.local_path:
            self._storage.delete_wallpaper_by_path(wallpaper.local_path)
        self._db.delete_wallpaper(wallpaper_id)
        logger.info("Deleted wallpaper %d from history", wallpaper_id)
        return True

    def is_downloaded(self, unsplash_id: str) -> bool:
        return self._db.wallpaper_exists(unsplash_id)

    def count(self) -> int:
        return self._db.count_wallpapers()

    def _enforce_retention(self) -> None:
        max_wallpapers = self._config.get_int(
            "max_wallpapers", DEFAULT_MAX_WALLPAPERS
        )
        current = self._db.count_wallpapers()
        if current <= max_wallpapers:
            return
        excess = current - max_wallpapers
        oldest = self._db.get_oldest_wallpapers(excess)
        for wp in oldest:
            if wp.local_path:
                self._storage.delete_wallpaper_by_path(wp.local_path)
            self._db.delete_wallpaper(wp.id)
            logger.info(
                "Removed old wallpaper %s to enforce retention",
                wp.unsplash_id,
            )

    def get_recent(
        self, days: int = 7
    ) -> list[Wallpaper]:
        all_wallpapers = self._db.get_wallpapers(limit=10000)
        from datetime import datetime, timedelta

        cutoff = datetime.now() - timedelta(days=days)
        return [
            wp
            for wp in all_wallpapers
            if wp.downloaded_at
            and datetime.fromisoformat(wp.downloaded_at) > cutoff
        ]

    def clear_all(self) -> None:
        all_wallpapers = self._db.get_wallpapers(limit=10000)
        for wp in all_wallpapers:
            if wp.local_path:
                self._storage.delete_wallpaper_by_path(wp.local_path)
            self._db.delete_wallpaper(wp.id)
        logger.info("Cleared all wallpaper history")
