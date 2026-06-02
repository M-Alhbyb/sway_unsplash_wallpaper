from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from unsplash_wallpaper.config import Config
from unsplash_wallpaper.database import Database
from unsplash_wallpaper.models.wallpaper import Wallpaper
from unsplash_wallpaper.services.history_service import HistoryService
from unsplash_wallpaper.services.storage_service import StorageService
from unsplash_wallpaper.services.unsplash_service import (
    UnsplashAuthError,
    UnsplashNetworkError,
    UnsplashRateLimitError,
    UnsplashService,
)
from unsplash_wallpaper.services.wallpaper_service import (
    SwayBackend,
    WallpaperBackend,
)


class TestCorruptedSettings:
    def test_corrupted_database_handling(
        self, temp_dir: Path
    ) -> None:
        db_path = temp_dir / "corrupted.db"
        db_path.write_text("NOT A VALID SQLITE DATABASE")
        db = Database(db_path)
        with pytest.raises(Exception):
            db.initialize()

    def test_empty_setting_values(
        self, temp_dir: Path
    ) -> None:
        db_path = temp_dir / "empty_settings.db"
        db = Database(db_path)
        db.initialize()

        db.set_setting("unsplash_access_key", "   ")
        config = Config(db)
        assert config.has_valid_api_key() is False
        db.close_all()

    def test_missing_setting_defaults(
        self, temp_dir: Path
    ) -> None:
        db_path = temp_dir / "missing_settings.db"
        db = Database(db_path)
        db.initialize()
        config = Config(db)
        assert config.get("nonexistent_key", "default_val") == "default_val"
        db.close_all()


class TestCorruptedHistoryDatabase:
    def test_missing_history_table(
        self, temp_dir: Path
    ) -> None:
        db_path = temp_dir / "no_history.db"
        db = Database(db_path)
        db.initialize()
        conn = db._get_connection()
        conn.execute("DROP TABLE IF EXISTS wallpapers")
        conn.commit()
        with pytest.raises(Exception):
            db.count_wallpapers()
        db.close_all()

    def test_corrupted_wallpaper_entry(
        self, temp_dir: Path, storage: StorageService
    ) -> None:
        db_path = temp_dir / "corrupted_history.db"
        db = Database(db_path)
        db.initialize()
        wp = Wallpaper(
            unsplash_id="valid_entry",
            author="Valid Author",
            local_path=str(storage.root / "valid.jpg"),
        )
        wp_id = db.add_wallpaper(wp)
        retrieved = db.get_wallpaper(wp_id)
        assert retrieved is not None
        assert retrieved.unsplash_id == "valid_entry"
        db.close_all()


class TestMissingWallpaperFiles:
    def test_missing_wallpaper_file(
        self, temp_dir: Path
    ) -> None:
        storage_path = temp_dir / "wallpapers"
        storage = StorageService(storage_path)
        result = storage.delete_wallpaper("nonexistent.jpg")
        assert result is False

    def test_history_references_deleted_file(
        self, temp_dir: Path, storage: StorageService
    ) -> None:
        db_path = temp_dir / "ref_deleted.db"
        db = Database(db_path)
        db.initialize()
        config = Config(db)
        history = HistoryService(db, storage, config)

        wp = Wallpaper(
            unsplash_id="ghost_ref",
            author="Ghost",
            local_path=str(storage.root / "ghost.jpg"),
        )
        history.add(wp)

        wp_path = Path(wp.local_path)
        if wp_path.exists():
            wp_path.unlink()

        assert not wp_path.exists()

        retrieved = history.get_latest()
        assert retrieved is not None
        assert retrieved.unsplash_id == "ghost_ref"

        db.close_all()


class TestDeletedStorageDirectories:
    def test_recreate_storage_directory(
        self, temp_dir: Path
    ) -> None:
        storage_path = temp_dir / "deleted" / "wallpapers"
        storage = StorageService(storage_path)
        assert storage_path.exists()

        import shutil

        shutil.rmtree(storage_path)
        assert not storage_path.exists()

        storage.ensure_directories()
        assert storage_path.exists()

        filepath = storage.save_wallpaper(b"test_data", "recovered.jpg")
        assert filepath.exists()

    def test_missing_data_directory(self, tmp_path: Path) -> None:

        class MockConfig:
            def get(self, *args, **kwargs):
                return ""

            def get_bool(self, *args, **kwargs):
                return False

            def get_categories(self):
                return []

            def has_valid_api_key(self):
                return False

        with patch(
            "unsplash_wallpaper.constants.DATA_DIR", tmp_path / "nonexistent"
        ):

            data_dir = tmp_path / "nonexistent"
            assert not data_dir.exists()
            data_dir.mkdir(parents=True)
            assert data_dir.exists()


class TestInvalidApiKey:
    def test_empty_api_key_rejected(self) -> None:
        config = MagicMock()
        config.get.return_value = ""
        svc = UnsplashService(config)
        with pytest.raises(UnsplashAuthError):
            svc._get_access_key()

    def test_short_api_key_rejected(self) -> None:
        config = MagicMock()
        config.get.return_value = "short"
        config.has_valid_api_key.return_value = False
        assert config.has_valid_api_key() is False

    def test_api_key_401_handling(self) -> None:
        config = MagicMock()
        config.get.return_value = "invalid_key_but_long_enough"

        with patch("requests.Session.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.headers = {}
            mock_get.return_value = mock_response

            svc = UnsplashService(config)
            with pytest.raises(UnsplashAuthError):
                svc.get_random_photo()

    def test_api_key_403_rate_limit(self) -> None:
        config = MagicMock()
        config.get.return_value = "valid_key"

        with patch("requests.Session.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 403
            mock_response.headers = {}
            mock_get.return_value = mock_response

            svc = UnsplashService(config)
            with pytest.raises(UnsplashRateLimitError):
                svc.get_random_photo()


class TestExpiredNetwork:
    @patch("requests.Session.get")
    def test_network_timeout(self, mock_get) -> None:
        import requests

        config = MagicMock()
        config.get.return_value = "test_key"
        mock_get.side_effect = requests.exceptions.Timeout("Timed out")

        svc = UnsplashService(config)
        with pytest.raises(UnsplashNetworkError):
            svc.get_random_photo(retries=2)

    @patch("requests.Session.get")
    def test_network_connection_refused(
        self, mock_get
    ) -> None:
        import requests

        config = MagicMock()
        config.get.return_value = "test_key"
        mock_get.side_effect = requests.exceptions.ConnectionError(
            "Connection refused"
        )

        svc = UnsplashService(config)
        with pytest.raises(UnsplashNetworkError):
            svc.get_random_photo(retries=2)

    @patch("requests.Session.get")
    def test_network_dns_failure(self, mock_get) -> None:
        import requests

        config = MagicMock()
        config.get.return_value = "test_key"
        mock_get.side_effect = requests.exceptions.ConnectionError(
            "Name or service not known"
        )

        svc = UnsplashService(config)
        with pytest.raises(UnsplashNetworkError):
            svc.get_random_photo(retries=2)


class TestBackendRecovery:
    def test_swaybg_not_found(self) -> None:
        with patch("subprocess.Popen") as mock_popen:
            mock_popen.side_effect = FileNotFoundError(
                "systemd-run not found"
            )
            backend = SwayBackend()
            result = backend.apply("/tmp/test.jpg")
            assert result is False

    def test_backend_auto_fallback(self) -> None:
        with patch.dict(
            os.environ,
            {
                "XDG_CURRENT_DESKTOP": "",
                "WAYLAND_DISPLAY": "",
                "DESKTOP_SESSION": "",
            },
            clear=True,
        ):
            with patch("shutil.which", return_value="/usr/bin/swaybg"):
                cls = WallpaperBackend.detect()
                assert cls == SwayBackend


class TestConcurrentRecovery:
    def test_concurrent_database_access(
        self, temp_dir: Path, storage: StorageService
    ) -> None:
        db_path = temp_dir / "concurrent_recovery.db"
        db = Database(db_path)
        db.initialize()
        config = Config(db)
        history = HistoryService(db, storage, config)

        import threading

        barrier = threading.Barrier(10)

        def add_and_delete(idx: int) -> None:
            try:
                barrier.wait()
                wp = Wallpaper(
                    unsplash_id=f"concur_{idx}",
                    author=f"Concurrent {idx}",
                    local_path=str(storage.root / f"co_{idx}.jpg"),
                )
                history.add(wp)
                latest = history.get_latest()
                assert latest is not None
            except Exception:
                pass

        threads = [
            threading.Thread(target=add_and_delete, args=(i,))
            for i in range(10)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert history.count() == 10
        db.close_all()

    def test_database_cleanup_on_exit(
        self, temp_dir: Path
    ) -> None:
        db_path = temp_dir / "cleanup.db"
        db = Database(db_path)
        db.initialize()
        db.set_setting("test", "value")
        db.close_all()

        db2 = Database(db_path)
        db2.initialize()
        assert db2.get_setting("test") == "value"
        db2.close_all()
