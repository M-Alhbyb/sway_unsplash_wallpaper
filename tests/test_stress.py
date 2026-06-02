from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from unsplash_wallpaper.config import Config
from unsplash_wallpaper.database import Database
from unsplash_wallpaper.models.wallpaper import Wallpaper
from unsplash_wallpaper.services.history_service import HistoryService
from unsplash_wallpaper.services.scheduler_service import SchedulerService
from unsplash_wallpaper.services.storage_service import StorageService
from unsplash_wallpaper.services.unsplash_service import (
    UnsplashNetworkError,
    UnsplashService,
)

STRESS_ITERATIONS = int(os.environ.get("STRESS_ITERATIONS", "10"))


class TestContinuousRotation:
    def test_repeated_download_cycle(
        self, temp_dir: Path
    ) -> None:
        db_path = temp_dir / "stress.db"
        storage_path = temp_dir / "wallpapers"
        storage = StorageService(storage_path)
        db = Database(db_path)
        db.initialize()
        config = Config(db)
        history = HistoryService(db, storage, config)

        with patch("requests.Session.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.content = b"\xff\xd8" + b"x" * 5000
            mock_get.return_value = mock_response

            for i in range(STRESS_ITERATIONS):
                wp = Wallpaper(
                    unsplash_id=f"stress_{i}",
                    author=f"Stress Author {i}",
                    local_path=str(storage_path / f"s_{i}.jpg"),
                    downloaded_at=f"2025-01-{i % 28 + 1:02d}T00:00:00",
                )
                history.add(wp)

            assert history.count() == STRESS_ITERATIONS

        db.close_all()

    def test_retention_enforcement(
        self, temp_dir: Path
    ) -> None:
        storage_path = temp_dir / "retention_wp"
        storage = StorageService(storage_path)
        db_path = temp_dir / "retention.db"
        db = Database(db_path)
        db.initialize()
        config = Config(db)
        config.set("max_wallpapers", "5")
        history = HistoryService(db, storage, config)

        for i in range(STRESS_ITERATIONS * 2):
            wp = Wallpaper(
                unsplash_id=f"ret_{i}",
                author=f"Ret Auth {i}",
                local_path=str(storage_path / f"r_{i}.jpg"),
                downloaded_at=f"2025-01-{i % 28 + 1:02d}T00:00:00",
            )
            history.add(wp)

        assert history.count() <= 5
        db.close_all()


class TestSchedulerStress:
    def test_scheduler_restart_cycles(self) -> None:
        sched = SchedulerService()
        call_count = 0

        def cb():
            nonlocal call_count
            call_count += 1

        for _ in range(STRESS_ITERATIONS):
            sched.set_interval("15 minutes")
            sched.start(cb)
            assert sched.is_running is True
            sched.stop()
            assert sched.is_running is False
            sched.cleanup()

        assert sched.is_running is False
        assert sched._timer_id is None

    def test_rapid_interval_changes(self) -> None:
        sched = SchedulerService()

        def cb():
            pass

        intervals = [
            "15 minutes",
            "30 minutes",
            "1 hour",
            "3 hours",
            "6 hours",
            "12 hours",
            "24 hours",
        ]

        sched.start(cb)
        for _ in range(STRESS_ITERATIONS):
            for interval in intervals:
                sched.set_interval(interval)

        sched.stop()


class TestAPIFailureStress:
    @patch("requests.Session.get")
    def test_repeated_api_failures(
        self, mock_get, temp_dir: Path
    ) -> None:
        db_path = temp_dir / "api_fail.db"
        storage_path = temp_dir / "api_fail_wp"
        db = Database(db_path)
        db.initialize()
        config = Config(db)
        config.set("unsplash_access_key", "test_key_12345")
        storage = StorageService(storage_path)
        history = HistoryService(db, storage, config)

        mock_get.side_effect = UnsplashNetworkError(
            "Simulated network failure"
        )

        unsplash = UnsplashService(config)
        for i in range(STRESS_ITERATIONS):
            with pytest.raises(UnsplashNetworkError):
                unsplash.get_random_photo(retries=2)

        assert history.count() == 0
        db.close_all()

    @patch("requests.Session.get")
    def test_repeated_network_disconnects(
        self, mock_get, temp_dir: Path
    ) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"\xff\xd8" + b"x" * 1000
        from requests.exceptions import ConnectionError

        mock_get.side_effect = [
            ConnectionError("No connection")
        ] * STRESS_ITERATIONS + [mock_response]

        db_path = temp_dir / "net_fail.db"
        storage_path = temp_dir / "net_fail_wp"
        db = Database(db_path)
        db.initialize()
        config = Config(db)
        config.set("unsplash_access_key", "test_key_12345")
        storage = StorageService(storage_path)
        history = HistoryService(db, storage, config)

        unsplash = UnsplashService(config)

        for i in range(STRESS_ITERATIONS):
            with pytest.raises(UnsplashNetworkError):
                unsplash.get_random_photo(retries=1)

        mock_get.side_effect = None
        mock_get.return_value = mock_response
        data = unsplash.download_image("https://example.com/photo.jpg")
        assert len(data) > 0

        db.close_all()


class TestDatabaseGrowth:
    def test_database_growth_pattern(
        self, temp_dir: Path
    ) -> None:
        storage_path = temp_dir / "growth_wp"
        storage = StorageService(storage_path)
        db_path = temp_dir / "growth.db"
        db = Database(db_path)
        db.initialize()
        config = Config(db)
        history = HistoryService(db, storage, config)

        initial_size = db_path.stat().st_size

        for i in range(STRESS_ITERATIONS * 5):
            wp = Wallpaper(
                unsplash_id=f"growth_{i}",
                author=f"Growth {i}",
                local_path=str(storage_path / f"g_{i}.jpg"),
                downloaded_at="2025-01-01T00:00:00",
            )
            history.add(wp)

        final_size = db_path.stat().st_size
        growth = final_size - initial_size
        per_record = growth / (STRESS_ITERATIONS * 5) if growth > 0 else 0
        assert per_record < 1000

        db.close_all()

    def test_database_after_deletes(
        self, temp_dir: Path
    ) -> None:
        storage_path = temp_dir / "delete_wp"
        storage = StorageService(storage_path)
        db_path = temp_dir / "delete.db"
        db = Database(db_path)
        db.initialize()
        config = Config(db)
        history = HistoryService(db, storage, config)

        wallpapers = []
        for i in range(STRESS_ITERATIONS * 3):
            wp = Wallpaper(
                unsplash_id=f"del_{i}",
                author=f"Del {i}",
                local_path=str(storage_path / f"d_{i}.jpg"),
            )
            result = history.add(wp)
            wallpapers.append(result)

        assert history.count() == STRESS_ITERATIONS * 3

        for wp in wallpapers:
            if wp.id:
                history.delete(wp.id)

        assert history.count() == 0
        db.close_all()
