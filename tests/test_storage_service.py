from __future__ import annotations

from pathlib import Path

from unsplash_wallpaper.services.storage_service import StorageService


class TestStorageService:
    def test_ensure_directories(self, temp_dir: Path) -> None:
        storage_path = temp_dir / "test_wallpapers"
        svc = StorageService(storage_path)
        assert storage_path.exists()
        assert storage_path.is_dir()

    def test_save_wallpaper(self, storage: StorageService) -> None:
        data = b"fake_image_data"
        filepath = storage.save_wallpaper(data, "test.jpg")
        assert filepath.exists()
        assert filepath.read_bytes() == data

    def test_wallpaper_exists(self, storage: StorageService) -> None:
        assert not storage.wallpaper_exists("test.jpg")
        storage.save_wallpaper(b"data", "test.jpg")
        assert storage.wallpaper_exists("test.jpg")

    def test_delete_wallpaper(self, storage: StorageService) -> None:
        storage.save_wallpaper(b"data", "test.jpg")
        assert storage.wallpaper_exists("test.jpg")
        assert storage.delete_wallpaper("test.jpg") is True
        assert not storage.wallpaper_exists("test.jpg")

    def test_delete_wallpaper_by_path(
        self, storage: StorageService
    ) -> None:
        filepath = storage.save_wallpaper(b"data", "test.jpg")
        assert storage.delete_wallpaper_by_path(filepath) is True

    def test_delete_nonexistent(
        self, storage: StorageService
    ) -> None:
        assert storage.delete_wallpaper("nonexistent.jpg") is False

    def test_count_wallpapers(
        self, storage: StorageService
    ) -> None:
        assert storage.count_wallpapers() == 0
        storage.save_wallpaper(b"data1", "test1.jpg")
        storage.save_wallpaper(b"data2", "test2.jpg")
        assert storage.count_wallpapers() == 2

    def test_get_storage_size(
        self, storage: StorageService
    ) -> None:
        initial = storage.get_storage_size()
        storage.save_wallpaper(b"X" * 100, "test.jpg")
        assert storage.get_storage_size() >= 100
