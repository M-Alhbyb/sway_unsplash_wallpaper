from __future__ import annotations

import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest

from unsplash_wallpaper.config import Config
from unsplash_wallpaper.database import Database
from unsplash_wallpaper.models.wallpaper import Wallpaper
from unsplash_wallpaper.services.history_service import HistoryService
from unsplash_wallpaper.services.storage_service import StorageService


@pytest.fixture
def temp_dir() -> Generator[Path, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


@pytest.fixture
def db(temp_dir: Path) -> Generator[Database, Any]:
    db_path = temp_dir / "test.db"
    database = Database(db_path)
    database.initialize()
    yield database
    database.close_all()


@pytest.fixture
def config(db: Database) -> Config:
    return Config(db)


@pytest.fixture
def storage(temp_dir: Path) -> StorageService:
    storage_path = temp_dir / "wallpapers"
    return StorageService(storage_path)


@pytest.fixture
def history(
    db: Database, storage: StorageService, config: Config
) -> HistoryService:
    return HistoryService(db, storage, config)


@pytest.fixture
def sample_wallpaper(storage: StorageService) -> Wallpaper:
    storage_path = storage.root / "test123.jpg"
    return Wallpaper(
        unsplash_id="test123",
        author="Test Author",
        description="A test wallpaper",
        local_path=str(storage_path),
        download_location="https://api.unsplash.com/photos/test123/download",
        category="nature",
        downloaded_at="2025-01-01T00:00:00",
    )



