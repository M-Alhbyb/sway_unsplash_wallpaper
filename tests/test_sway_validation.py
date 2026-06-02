from __future__ import annotations

import os
import subprocess
import time
from unittest.mock import MagicMock, patch

import pytest

from unsplash_wallpaper.services.wallpaper_service import (
    SwayBackend,
    WallpaperBackend,
    WallpaperService,
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

    def test_swaybg_no_orphan_processes(self) -> None:
        result = subprocess.run(
            ["pgrep", "-c", "swaybg"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        initial_count = int(result.stdout.strip() or 0)
        backend = SwayBackend()
        fake_path = "/tmp/test_validation_wallpaper.jpg"
        with patch("subprocess.Popen") as mock_popen:
            mock_process = MagicMock()
            mock_process.pid = 99999
            mock_popen.return_value = mock_process
            backend.apply(fake_path)

        result2 = subprocess.run(
            ["pgrep", "-c", "swaybg"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        final_count = int(result2.stdout.strip() or 0)
        assert final_count >= initial_count

    def test_single_wallpaper_update(self) -> None:
        backend = SwayBackend()
        with patch("subprocess.Popen") as mock_popen:
            mock_process = MagicMock()
            mock_process.pid = 12345
            mock_popen.return_value = mock_process
            result = backend.apply("/tmp/test_single.jpg")
            assert result is True
            mock_popen.assert_called_once()

    def test_consecutive_updates_no_orphans(self) -> None:
        backend = SwayBackend()
        processes = []

        for i in range(100):
            mock_process = MagicMock()
            mock_process.pid = 10000 + i
            processes.append(mock_process)

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.side_effect = processes
            for i in range(100):
                path = f"/tmp/test_batch_{i}.jpg"
                result = backend.apply(path)
                assert result is True
                if i > 0:
                    processes[i - 1].terminate.assert_called_once()

    def test_rapid_updates_five_seconds(self) -> None:
        backend = SwayBackend()
        process_count = 0

        def mock_popen_side(*args, **kwargs):
            nonlocal process_count
            process_count += 1
            mock = MagicMock()
            mock.pid = 20000 + process_count
            return mock

        with patch("subprocess.Popen", side_effect=mock_popen_side):
            start = time.time()
            for i in range(12):
                path = f"/tmp/test_rapid_{i}.jpg"
                result = backend.apply(path)
                assert result is True
            elapsed = time.time() - start
            assert elapsed < 60

    def test_restart_while_active(self) -> None:
        backend = SwayBackend()
        with patch("subprocess.Popen") as mock_popen:
            mock1 = MagicMock()
            mock1.pid = 30001
            mock2 = MagicMock()
            mock2.pid = 30002

            mock_popen.side_effect = [mock1, mock2]

            backend.apply("/tmp/test_restart_1.jpg")
            assert backend._process is not None
            assert backend._process.pid == 30001

            backend.apply("/tmp/test_restart_2.jpg")
            assert backend._process is not None
            assert backend._process.pid == 30002

            mock1.terminate.assert_called_once()

    def test_kill_stale_process(self) -> None:
        backend = SwayBackend()
        with patch("subprocess.Popen") as mock_popen:
            mock_old = MagicMock()
            mock_old.pid = 40001
            mock_old.terminate.side_effect = subprocess.TimeoutExpired(
                "swaybg", 5
            )

            mock_new = MagicMock()
            mock_new.pid = 40002

            mock_popen.return_value = mock_old
            backend.apply("/tmp/test_stale_1.jpg")

            mock_popen.return_value = mock_new
            backend.apply("/tmp/test_stale_2.jpg")

            mock_old.terminate.assert_called_once()
            mock_old.kill.assert_called_once()

    def test_no_duplicate_schedulers(self) -> None:
        from unsplash_wallpaper.services.scheduler_service import (
            SchedulerService,
        )

        callbacks = []

        def make_cb(idx):
            def cb():
                callbacks.append(idx)

            return cb

        s1 = SchedulerService()
        s2 = SchedulerService()

        s1.set_interval("15 minutes")
        s2.set_interval("15 minutes")

        s1.start(make_cb(1))
        s2.start(make_cb(2))

        assert s1.is_running is True
        assert s2.is_running is True

        s1.stop()
        s2.stop()

    def test_suspend_resume(self) -> None:
        backend = SwayBackend()
        with patch("subprocess.Popen") as mock_popen:
            mock_process = MagicMock()
            mock_process.pid = 50001
            mock_popen.return_value = mock_process

            backend.apply("/tmp/test_before_suspend.jpg")
            assert backend._process is not None

            backend._kill_existing()
            assert backend._process is None

            mock_process.terminate.assert_called_once()

            mock_process2 = MagicMock()
            mock_process2.pid = 50002
            mock_popen.return_value = mock_process2
            backend.apply("/tmp/test_after_resume.jpg")
            assert backend._process is not None
            assert backend._process.pid == 50002
