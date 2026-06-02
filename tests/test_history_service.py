from __future__ import annotations

from pathlib import Path

from unsplash_wallpaper.models.wallpaper import Wallpaper


class TestHistoryService:
    def test_add_and_count(
        self, history, sample_wallpaper
    ) -> None:
        assert history.count() == 0
        history.add(sample_wallpaper)
        assert history.count() == 1

    def test_get_all(self, history, sample_wallpaper) -> None:
        history.add(sample_wallpaper)
        wp2 = Wallpaper(
            unsplash_id="test456",
            category="space",
        )
        history.add(wp2)
        all_wps = history.get_all()
        assert len(all_wps) == 2

    def test_get_latest(self, history, sample_wallpaper) -> None:
        history.add(sample_wallpaper)
        latest = history.get_latest()
        assert latest is not None
        assert latest.unsplash_id == "test123"

    def test_get_by_id(self, history, sample_wallpaper) -> None:
        added = history.add(sample_wallpaper)
        assert added.id is not None
        retrieved = history.get(added.id)
        assert retrieved is not None
        assert retrieved.unsplash_id == "test123"

    def test_delete(self, history, sample_wallpaper) -> None:
        added = history.add(sample_wallpaper)
        assert history.count() == 1
        result = history.delete(added.id)
        assert result is True
        assert history.count() == 0

    def test_delete_nonexistent(self, history) -> None:
        result = history.delete(9999)
        assert result is False

    def test_is_downloaded(
        self, history, sample_wallpaper
    ) -> None:
        assert not history.is_downloaded("test123")
        history.add(sample_wallpaper)
        assert history.is_downloaded("test123")
        assert not history.is_downloaded("nonexistent")

    def test_enforce_retention(
        self, history, temp_dir: Path
    ) -> None:
        max_wp = 3
        from unsplash_wallpaper.config import Config

        history._config.set("max_wallpapers", str(max_wp))
        for i in range(5):
            wp = Wallpaper(
                unsplash_id=f"retention_test_{i}",
                local_path=str(temp_dir / f"test_{i}.jpg"),
                downloaded_at=f"2025-01-0{i + 1}T00:00:00",
            )
            history.add(wp)
        assert history.count() <= max_wp

    def test_clear_all(
        self, history, sample_wallpaper
    ) -> None:
        history.add(sample_wallpaper)
        history.add(
            Wallpaper(unsplash_id="test456", category="space")
        )
        assert history.count() == 2
        history.clear_all()
        assert history.count() == 0
