from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path

from unsplash_wallpaper.constants import WALLPAPERS_DIR

logger = logging.getLogger(__name__)


class StorageService:
    def __init__(self, storage_path: Path = WALLPAPERS_DIR) -> None:
        self.storage_path = storage_path.resolve()
        self.ensure_directories()

    @property
    def root(self) -> Path:
        return self.storage_path

    def ensure_directories(self) -> None:
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def _validate_filename(self, filename: str) -> None:
        if not filename or filename.strip() != filename:
            raise ValueError(f"Invalid filename: {filename!r}")
        if "/" in filename or "\\" in filename or ".." in filename:
            raise ValueError(f"Path traversal detected in filename: {filename!r}")

    def _validate_within_storage(self, filepath: Path) -> None:
        resolved = filepath.resolve()
        if not str(resolved).startswith(str(self.storage_path)):
            raise ValueError(
                f"Path {resolved} is outside storage directory "
                f"{self.storage_path}"
            )

    def save_wallpaper(self, data: bytes, filename: str) -> Path:
        self._validate_filename(filename)
        filepath = (self.storage_path / filename).resolve()
        self._validate_within_storage(filepath)
        filepath.write_bytes(data)
        logger.info("Saved wallpaper to %s", filepath)
        return filepath

    def delete_wallpaper(self, filename: str) -> bool:
        self._validate_filename(filename)
        filepath = (self.storage_path / filename).resolve()
        self._validate_within_storage(filepath)
        if filepath.exists():
            filepath.unlink()
            logger.info("Deleted wallpaper %s", filepath)
            return True
        return False

    def delete_wallpaper_by_path(self, path: str | Path) -> bool:
        filepath = Path(path).resolve()
        self._validate_within_storage(filepath)
        if filepath.exists():
            filepath.unlink()
            logger.info("Deleted wallpaper %s", filepath)
            return True
        return False

    def get_wallpaper_path(self, filename: str) -> Path:
        self._validate_filename(filename)
        return (self.storage_path / filename).resolve()

    def wallpaper_exists(self, filename: str) -> bool:
        self._validate_filename(filename)
        return (self.storage_path / filename).exists()

    def get_storage_size(self) -> int:
        total = 0
        for f in self.storage_path.iterdir():
            if f.is_file():
                total += f.stat().st_size
        return total

    def count_wallpapers(self) -> int:
        if not self.storage_path.exists():
            return 0
        return sum(1 for f in self.storage_path.iterdir() if f.is_file())

    def cleanup_all(self) -> None:
        if self.storage_path.exists():
            shutil.rmtree(self.storage_path)
            self.storage_path.mkdir(parents=True, exist_ok=True)
            logger.info("Cleaned up all wallpapers")
