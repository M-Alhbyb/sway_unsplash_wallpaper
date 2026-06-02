from __future__ import annotations

import os
import time
from unittest.mock import MagicMock, patch

import pytest

from unsplash_wallpaper.services.wallpaper_service import (
    SwayBackend,
    WallpaperBackend,
)

pytestmark = pytest.mark.skipif(
    not bool(os.environ.get("SWAY_VALIDATION_TESTS")),
    reason="Sway validation tests require SWAY_VALIDATION_TESTS env var",
)


class TestSwayValidation:
    def test_swaybg_installed(self) -> None:
        assert SwayBackend.check_dependencies() is True
        assert WallpaperBackend.is_available() is True

    def test_backend_detection(self) -> None:
        cls = WallpaperBackend.detect()
        assert cls == SwayBackend

    def test_single_wallpaper_update(self) -> None:
        backend = SwayBackend()
        with (
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(returncode=0)
            result = backend.apply("/tmp/test_single.jpg")
            assert result is True
            assert any(
                "swaybg" in str(call) for call in mock_run.call_args_list
            )

    def test_consecutive_updates_no_orphans(self) -> None:
        backend = SwayBackend()
        with (
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(returncode=0)
            for i in range(100):
                path = f"/tmp/test_batch_{i}.jpg"
                result = backend.apply(path)
                assert result is True

    def test_rapid_updates_five_seconds(self) -> None:
        backend = SwayBackend()
        with (
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(returncode=0)
            start = time.time()
            for i in range(12):
                path = f"/tmp/test_rapid_{i}.jpg"
                result = backend.apply(path)
                assert result is True
            elapsed = time.time() - start
            assert elapsed < 60

    def test_kill_stale_process(self) -> None:
        backend = SwayBackend()
        with (
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(returncode=0)
            result = backend.apply("/tmp/test_stale_1.jpg")
            assert result is True
            result = backend.apply("/tmp/test_stale_2.jpg")
            assert result is True

    def test_suspend_resume(self) -> None:
        backend = SwayBackend()
        with (
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(returncode=0)
            result = backend.apply("/tmp/test_before_suspend.jpg")
            assert result is True

            backend._kill_existing()

            result = backend.apply("/tmp/test_after_resume.jpg")
            assert result is True
