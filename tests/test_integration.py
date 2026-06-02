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
    UnsplashAuthError,
    UnsplashService,
)
from unsplash_wallpaper.services.wallpaper_service import (
    SwayBackend,
    WallpaperBackend,
)
from unsplash_wallpaper.system.autostart import AutostartManager


class TestFirstLaunch:
    def test_fresh_database_creation(self, temp_dir: Path) -> None:
        db_path = temp_dir / "fresh.db"
        assert not db_path.exists()
        db = Database(db_path)
        db.initialize()
        assert db_path.exists()
        assert db.get_setting("schema_version") is not None
        assert db.count_wallpapers() == 0
        db.close_all()

    def test_default_config_on_first_run(self, db: Database) -> None:
        config = Config(db)
        assert config.get("unsplash_access_key") == ""
        assert config.get("update_interval") == "1 hour"
        assert config.get("notifications") == "true"
        assert config.has_valid_api_key() is False

    def test_empty_history_on_first_run(
        self, db: Database, storage: StorageService, config: Config
    ) -> None:
        history = HistoryService(db, storage, config)
        assert history.count() == 0
        assert history.get_all() == []
        assert history.get_latest() is None


class TestApiKeySetup:
    def test_set_valid_key(self, config: Config) -> None:
        assert config.has_valid_api_key() is False
        config.set("unsplash_access_key", "abcdefghijklmnopqr")
        assert config.has_valid_api_key() is True

    def test_set_invalid_key(self, config: Config) -> None:
        config.set("unsplash_access_key", "")
        assert config.has_valid_api_key() is False
        config.set("unsplash_access_key", "short")
        assert config.has_valid_api_key() is False

    def test_key_persistence(
        self, db: Database, config: Config
    ) -> None:
        config.set("unsplash_access_key", "persistent_key_12345")
        config2 = Config(db)
        assert config2.get("unsplash_access_key") == "persistent_key_12345"

    def test_key_triggers_auth_error(
        self, config: Config
    ) -> None:
        config.set("unsplash_access_key", "")
        svc = UnsplashService(config)
        with pytest.raises(UnsplashAuthError):
            svc.get_random_photo()


class TestWallpaperDownload:
    @patch("requests.Session.get")
    def test_download_and_save(
        self, mock_get, storage: StorageService
    ) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"\xff\xd8" + b"fake_jpeg_data" * 100
        mock_get.return_value = mock_response

        data = mock_response.content
        filepath = storage.save_wallpaper(data, "test_download.jpg")
        assert filepath.exists()
        assert filepath.read_bytes() == data
        assert storage.wallpaper_exists("test_download.jpg")

    @patch("requests.Session.get")
    def test_download_invalid_image_validation(
        self, mock_get, storage: StorageService
    ) -> None:
        from unsplash_wallpaper.app import UnsplashWallpaperApp

        app = UnsplashWallpaperApp()
        assert app._validate_image_data(b"") is False
        assert app._validate_image_data(b"tiny") is False
        assert app._validate_image_data(b"\xff\xd8" + b"x" * 30) is True
        assert app._validate_image_data(b"\x89PNG\r\n\x1a\n" + b"x" * 30) is True
        assert app._validate_image_data(b"GIF89a" + b"x" * 30) is True

    @patch("requests.Session.get")
    def test_full_download_flow(
        self, mock_get, history: HistoryService, storage: StorageService
    ) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"\xff\xd8" + b"fake_jpeg_data" * 100
        mock_get.return_value = mock_response

        data = mock_response.content
        filename = "flow_test.jpg"
        filepath = storage.save_wallpaper(data, filename)

        wallpaper = Wallpaper(
            unsplash_id="flow123",
            author="Integration Tester",
            description="Full flow test",
            local_path=str(filepath),
            download_location="https://api.unsplash.com/photos/flow123/download",
            category="nature",
        )

        result = history.add(wallpaper)
        assert result.id is not None
        assert history.count() == 1
        assert history.is_downloaded("flow123") is True

        retrieved = history.get(result.id)
        assert retrieved is not None
        assert retrieved.author == "Integration Tester"
        assert retrieved.local_path == str(filepath)


class TestWallpaperApplication:
    @patch("subprocess.Popen")
    def test_sway_backend_apply(self, mock_popen) -> None:
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process

        backend = SwayBackend()
        result = backend.apply("/tmp/test_wallpaper.jpg")
        assert result is True
        mock_popen.assert_called_once_with(
            ["swaybg", "-i", "/tmp/test_wallpaper.jpg", "-m", "fill"],
            stdout=-3,
            stderr=-3,
            start_new_session=True,
        )

    @patch("subprocess.Popen")
    def test_sway_backend_kill_existing(
        self, mock_popen
    ) -> None:
        old_process = MagicMock()
        old_process.pid = 11111
        mock_popen.return_value = old_process

        backend = SwayBackend()
        backend.apply("/tmp/first.jpg")
        assert mock_popen.call_count == 1

        new_process = MagicMock()
        new_process.pid = 22222
        mock_popen.return_value = new_process
        backend.apply("/tmp/second.jpg")
        assert mock_popen.call_count == 2
        old_process.terminate.assert_called_once()

    @patch("shutil.which")
    def test_backend_detection_sway(self, mock_which) -> None:
        mock_which.return_value = "/usr/bin/swaybg"
        with patch.dict(
            os.environ,
            {"XDG_CURRENT_DESKTOP": "sway", "WAYLAND_DISPLAY": "wayland-0"},
            clear=True,
        ):
            cls = WallpaperBackend.detect()
            assert cls == SwayBackend


class TestHistoryPersistence:
    def test_history_survives_reload(
        self, temp_dir: Path, storage: StorageService
    ) -> None:
        db_path = temp_dir / "persist_test.db"
        db = Database(db_path)
        db.initialize()
        config = Config(db)
        history = HistoryService(db, storage, config)

        for i in range(5):
            wp = Wallpaper(
                unsplash_id=f"persist_{i}",
                author=f"Author {i}",
                local_path=str(storage.root / f"p_{i}.jpg"),
                downloaded_at=f"2025-0{i+1}-01T00:00:00",
            )
            history.add(wp)

        assert history.count() == 5

        db2 = Database(db_path)
        db2.initialize()
        history2 = HistoryService(db2, storage, config)
        assert history2.count() == 5
        all_wp = history2.get_all()
        assert len(all_wp) == 5

        db.close_all()
        db2.close_all()

    def test_history_limit(
        self, history: HistoryService, storage: StorageService
    ) -> None:
        history._config.set("max_wallpapers", "3")
        for i in range(10):
            wp = Wallpaper(
                unsplash_id=f"limit_{i}",
                local_path=str(storage.root / f"l_{i}.jpg"),
                downloaded_at=f"2025-01-{i+1:02d}T00:00:00",
            )
            history.add(wp)
        assert history.count() <= 3


class TestSchedulerExecution:
    def test_scheduler_integration(self) -> None:
        sched = SchedulerService()
        assert sched.is_running is False
        assert sched.get_interval() == "1 hour"

        call_log: list[str] = []

        def on_tick() -> None:
            call_log.append("tick")

        sched.set_interval("15 minutes")
        sched.start(on_tick)
        assert sched.is_running is True

        sched.stop()
        assert sched.is_running is False

    def test_scheduler_restart(self) -> None:
        sched = SchedulerService()

        def cb() -> None:
            pass

        sched.start(cb)
        assert sched.is_running is True
        sched.set_interval("30 minutes")
        assert sched.is_running is True
        assert sched.get_interval_minutes() == 30
        sched.stop()
        assert sched.is_running is False


class TestTrayFunctionality:
    def test_tray_init_no_indicator(self) -> None:
        from unsplash_wallpaper.tray.tray_manager import TrayManager

        app = MagicMock()
        tray = TrayManager(app)
        assert tray.setup() is False

    def test_tray_shutdown(self) -> None:
        from unsplash_wallpaper.tray.tray_manager import TrayManager

        app = MagicMock()
        tray = TrayManager(app)
        tray.shutdown()


class TestApplicationRestart:
    def test_database_reconnect(
        self, temp_dir: Path, storage: StorageService
    ) -> None:
        db_path = temp_dir / "restart.db"
        db = Database(db_path)
        db.initialize()
        config = Config(db)
        history = HistoryService(db, storage, config)

        wp = Wallpaper(
            unsplash_id="restart1",
            author="Restart Tester",
            local_path=str(storage.root / "restart1.jpg"),
        )
        history.add(wp)
        assert history.count() == 1

        db.close_all()

        db2 = Database(db_path)
        db2.initialize()
        config2 = Config(db2)
        history2 = HistoryService(db2, storage, config2)
        assert history2.count() == 1

        retrieved = history2.get_latest()
        assert retrieved is not None
        assert retrieved.unsplash_id == "restart1"

        db2.close_all()

    def test_scheduler_cleanup_and_restart(self) -> None:
        sched = SchedulerService()
        logs: list[str] = []

        def cb() -> None:
            logs.append("exec")

        sched.start(cb)
        assert sched.is_running is True
        sched.cleanup()
        assert sched.is_running is False
        assert sched._timer_id is None

        sched.start(cb)
        assert sched.is_running is True
        sched.stop()


class TestDatabaseRecovery:
    def test_recover_missing_database(
        self, temp_dir: Path
    ) -> None:
        db_path = temp_dir / "missing" / "database.db"
        assert not db_path.parent.exists()
        db = Database(db_path)
        db.initialize()
        assert db_path.exists()
        assert db.get_setting("schema_version") is not None
        db.close_all()

    def test_recover_empty_database(
        self, temp_dir: Path
    ) -> None:
        db_path = temp_dir / "empty.db"
        db_path.write_text("")
        db = Database(db_path)
        db.initialize()
        assert db.get_setting("schema_version") is not None
        db.close_all()

    def test_database_wal_mode(self, temp_dir: Path) -> None:
        db_path = temp_dir / "wal.db"
        db = Database(db_path)
        db.initialize()
        conn = db._get_connection()
        cur = conn.execute("PRAGMA journal_mode")
        assert cur.fetchone()[0].lower() == "wal"
        db.close_all()

    def test_concurrent_operations(
        self, temp_dir: Path, storage: StorageService
    ) -> None:
        db_path = temp_dir / "concurrent.db"
        db = Database(db_path)
        db.initialize()
        config = Config(db)
        history = HistoryService(db, storage, config)

        import threading

        errors: list[Exception] = []

        def add_wallpaper(idx: int) -> None:
            try:
                wp = Wallpaper(
                    unsplash_id=f"concurrent_{idx}",
                    author=f"Thread {idx}",
                    local_path=str(storage.root / f"c_{idx}.jpg"),
                )
                history.add(wp)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=add_wallpaper, args=(i,))
            for i in range(20)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert history.count() == 20
        db.close_all()


class TestAutostart:
    def test_autostart_desktop_entry(self) -> None:
        entry = AutostartManager.get_desktop_entry(
            python_path="/usr/bin/unsplash-wallpaper"
        )
        assert "Type=Application" in entry
        assert "Unsplash Wallpaper" in entry
        assert "/usr/bin/unsplash-wallpaper --tray" in entry

    def test_systemd_service_content(self) -> None:
        service = AutostartManager.get_systemd_service(
            python_path="/usr/bin/unsplash-wallpaper"
        )
        assert "Type=simple" in service
        assert "/usr/bin/unsplash-wallpaper --daemon" in service
        assert "Restart=on-failure" in service

    def test_systemd_timer_content(self) -> None:
        timer = AutostartManager.get_systemd_timer()
        assert "OnBootSec=1min" in timer
        assert "OnUnitActiveSec=1h" in timer


class TestFullFlow:
    def test_complete_download_apply_flow(
        self, temp_dir: Path
    ) -> None:
        db_path = temp_dir / "full_flow.db"
        storage_path = temp_dir / "wallpapers"

        db = Database(db_path)
        db.initialize()
        config = Config(db)
        storage = StorageService(storage_path)
        history = HistoryService(db, storage, config)

        config.set("unsplash_access_key", "test_key_12345")
        config.set_categories(["nature"])
        config.set("resolution", "full_hd")
        config.set("update_interval", "1 hour")

        assert config.has_valid_api_key() is True
        assert config.get_categories() == ["nature"]
        assert config.get_resolution() == "full_hd"

        wallpaper = Wallpaper(
            unsplash_id="full_flow_test",
            author="Full Flow Author",
            description="Complete integration test",
            local_path=str(storage_path / "full_flow_test.jpg"),
            download_location="https://api.unsplash.com/photos/full_flow_test/download",
            category="nature",
            url="https://unsplash.com/photos/full_flow_test",
        )

        result = history.add(wallpaper)
        assert result.id is not None

        latest = history.get_latest()
        assert latest is not None
        assert latest.unsplash_id == "full_flow_test"
        assert latest.author == "Full Flow Author"
        assert latest.category == "nature"

        assert history.count() == 1

        history.delete(result.id)
        assert history.count() == 0

        db.close_all()
