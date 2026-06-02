from __future__ import annotations

from unsplash_wallpaper.models.wallpaper import Wallpaper


class TestDatabase:
    def test_initialization(self, db) -> None:
        assert db.get_setting("schema_version") is not None

    def test_settings_get_set(self, db) -> None:
        db.set_setting("test_key", "test_value")
        assert db.get_setting("test_key") == "test_value"

    def test_settings_default(self, db) -> None:
        assert db.get_setting("nonexistent") is None
        assert db.get_setting("nonexistent", "default") == "default"

    def test_get_all_settings(self, db) -> None:
        db.set_setting("key1", "val1")
        db.set_setting("key2", "val2")
        all_settings = db.get_all_settings()
        assert all_settings["key1"] == "val1"
        assert all_settings["key2"] == "val2"

    def test_add_wallpaper(self, db, sample_wallpaper) -> None:
        wp_id = db.add_wallpaper(sample_wallpaper)
        assert wp_id is not None
        assert wp_id > 0

    def test_get_wallpaper_by_id(self, db, sample_wallpaper) -> None:
        wp_id = db.add_wallpaper(sample_wallpaper)
        retrieved = db.get_wallpaper(wp_id)
        assert retrieved is not None
        assert retrieved.unsplash_id == "test123"
        assert retrieved.author == "Test Author"

    def test_get_wallpaper_by_unsplash_id(
        self, db, sample_wallpaper
    ) -> None:
        db.add_wallpaper(sample_wallpaper)
        retrieved = db.get_wallpaper_by_unsplash_id("test123")
        assert retrieved is not None
        assert retrieved.author == "Test Author"

    def test_get_latest_wallpaper(self, db, sample_wallpaper) -> None:
        db.add_wallpaper(sample_wallpaper)
        wp2 = Wallpaper(
            unsplash_id="test456",
            author="Author 2",
            description="Second wallpaper",
            downloaded_at="2025-02-01T00:00:00",
        )
        db.add_wallpaper(wp2)
        latest = db.get_latest_wallpaper()
        assert latest is not None
        assert latest.unsplash_id == "test456"

    def test_get_wallpapers(self, db, sample_wallpaper) -> None:
        for i in range(5):
            wp = Wallpaper(
                unsplash_id=f"test{i}",
                author=f"Author {i}",
                downloaded_at=f"2025-01-0{i + 1}T00:00:00",
            )
            db.add_wallpaper(wp)
        all_wps = db.get_wallpapers(limit=10)
        assert len(all_wps) == 5

    def test_count_wallpapers(self, db) -> None:
        assert db.count_wallpapers() == 0
        for i in range(3):
            wp = Wallpaper(unsplash_id=f"test{i}")
            db.add_wallpaper(wp)
        assert db.count_wallpapers() == 3

    def test_delete_wallpaper(self, db, sample_wallpaper) -> None:
        wp_id = db.add_wallpaper(sample_wallpaper)
        assert db.count_wallpapers() == 1
        db.delete_wallpaper(wp_id)
        assert db.count_wallpapers() == 0

    def test_wallpaper_exists(self, db, sample_wallpaper) -> None:
        assert not db.wallpaper_exists("test123")
        db.add_wallpaper(sample_wallpaper)
        assert db.wallpaper_exists("test123")

    def test_get_oldest_wallpapers(
        self, db, sample_wallpaper
    ) -> None:
        for i in range(3):
            wp = Wallpaper(
                unsplash_id=f"test{i}",
                downloaded_at=f"2025-01-0{i + 1}T00:00:00",
            )
            db.add_wallpaper(wp)
        oldest = db.get_oldest_wallpapers(2)
        assert len(oldest) == 2
        assert oldest[0].unsplash_id == "test0"
        assert oldest[1].unsplash_id == "test1"

    def test_unique_unsplash_id(self, db, sample_wallpaper) -> None:
        db.add_wallpaper(sample_wallpaper)
        import sqlite3

        try:
            db.add_wallpaper(sample_wallpaper)
        except sqlite3.IntegrityError:
            pass
        assert db.count_wallpapers() == 1
