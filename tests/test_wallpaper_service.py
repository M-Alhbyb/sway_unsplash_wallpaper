from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

from unsplash_wallpaper.services.wallpaper_service import (
    GnomeBackend,
    HyprlandBackend,
    KdeBackend,
    SwayBackend,
    WallpaperBackend,
    WallpaperService,
)


class TestWallpaperBackendDetection:
    @patch.dict(
        os.environ,
        {"XDG_CURRENT_DESKTOP": "sway", "WAYLAND_DISPLAY": "wayland-0"},
        clear=True,
    )
    def test_detect_sway(self) -> None:
        cls = WallpaperBackend.detect()
        assert cls == SwayBackend

    @patch.dict(
        os.environ,
        {"XDG_CURRENT_DESKTOP": "Hyprland", "WAYLAND_DISPLAY": "wayland-0"},
        clear=True,
    )
    def test_detect_hyprland(self) -> None:
        cls = WallpaperBackend.detect()
        assert cls == HyprlandBackend

    @patch.dict(
        os.environ,
        {"XDG_CURRENT_DESKTOP": "GNOME", "WAYLAND_DISPLAY": "wayland-0"},
        clear=True,
    )
    def test_detect_gnome(self) -> None:
        cls = WallpaperBackend.detect()
        assert cls == GnomeBackend

    @patch.dict(
        os.environ,
        {"XDG_CURRENT_DESKTOP": "KDE", "WAYLAND_DISPLAY": ""},
        clear=True,
    )
    def test_detect_kde(self) -> None:
        cls = WallpaperBackend.detect()
        assert cls == KdeBackend

    @patch.dict(
        os.environ,
        {"XDG_CURRENT_DESKTOP": "sway", "WAYLAND_DISPLAY": "wayland-0"},
        clear=True,
    )
    def test_detect_sway_by_env_fallback(self) -> None:
        with patch.dict(os.environ, {"DESKTOP_SESSION": "sway"}):
            cls = WallpaperBackend.detect()
            assert cls == SwayBackend

    def test_wallpaper_service_initialization(self) -> None:
        service = WallpaperService()
        assert service._backend is None

    def test_backend_is_available(self) -> None:
        with patch("shutil.which", return_value="/usr/bin/swaybg"):
            assert WallpaperBackend.is_available() is True

    def test_backend_not_available(self) -> None:
        with patch("shutil.which", return_value=None):
            assert WallpaperBackend.is_available() is False


class TestSwayBackend:
    def test_get_name(self) -> None:
        backend = SwayBackend()
        assert backend.get_name() == "Sway"

    def test_check_dependencies_found(self) -> None:
        with patch("shutil.which", return_value="/usr/bin/swaybg"):
            assert SwayBackend.check_dependencies() is True

    def test_check_dependencies_not_found(self) -> None:
        with patch("shutil.which", return_value=None):
            assert SwayBackend.check_dependencies() is False

    @patch("subprocess.run")
    @patch("subprocess.Popen")
    def test_apply_success(
        self, mock_popen, mock_run
    ) -> None:
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process

        backend = SwayBackend()
        result = backend.apply("/tmp/test.jpg")
        assert result is True

    @patch("subprocess.run")
    @patch("subprocess.Popen")
    def test_apply_kills_previous(
        self, mock_popen, mock_run
    ) -> None:
        old_process = MagicMock()
        old_process.pid = 11111
        new_process = MagicMock()
        new_process.pid = 22222

        mock_popen.side_effect = [old_process, new_process]

        backend = SwayBackend()
        backend.apply("/tmp/first.jpg")
        backend.apply("/tmp/second.jpg")

        old_process.terminate.assert_called_once()

    @patch("subprocess.run")
    @patch("subprocess.Popen")
    def test_apply_file_not_found(self, mock_popen, mock_run) -> None:
        mock_popen.side_effect = FileNotFoundError("swaybg not found")
        backend = SwayBackend()
        result = backend.apply("/tmp/test.jpg")
        assert result is False

    @patch("subprocess.run")
    def test_terminate_timeout_triggers_kill(self, mock_run) -> None:
        from subprocess import TimeoutExpired

        backend = SwayBackend()
        mock_process = MagicMock()
        mock_process.pid = 33333
        mock_process.wait.side_effect = TimeoutExpired("swaybg", 5)
        backend._process = mock_process

        backend._kill_existing()
        mock_process.terminate.assert_called_once()
        mock_process.kill.assert_called_once()

    @patch("subprocess.run")
    def test_process_lookup_error(self, mock_run) -> None:
        backend = SwayBackend()
        mock_process = MagicMock()
        mock_process.pid = 44444
        mock_process.terminate.side_effect = ProcessLookupError()
        backend._process = mock_process

        backend._kill_existing()
        assert backend._process is None

    @patch("subprocess.run")
    def test_kill_by_pkill_called(self, mock_run) -> None:
        mock_run.return_value = MagicMock(returncode=0)
        backend = SwayBackend()
        backend._kill_existing()
        mock_run.assert_called_once_with(
            ["pkill", "swaybg"],
            capture_output=True,
            timeout=10,
        )

    @patch("subprocess.run")
    def test_kill_by_pkill_not_available(self, mock_run) -> None:
        mock_run.side_effect = FileNotFoundError()
        backend = SwayBackend()
        backend._kill_existing()

    @patch("subprocess.run")
    def test_no_orphan_after_twenty_apply_calls(
        self, mock_run
    ) -> None:
        backend = SwayBackend()
        processes = []

        for i in range(20):
            mock_process = MagicMock()
            mock_process.pid = 50000 + i
            processes.append(mock_process)

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.side_effect = processes
            for i in range(20):
                path = f"/tmp/test_batch_{i}.jpg"
                result = backend.apply(path)
                assert result is True
                if i > 0:
                    processes[i - 1].terminate.assert_called_once()

            assert backend._process is not None
            assert backend._process.pid == 50019


class TestHyprlandBackend:
    def test_get_name(self) -> None:
        backend = HyprlandBackend()
        assert backend.get_name() == "Hyprland"

    @patch("subprocess.run")
    def test_apply_success(self, mock_run) -> None:
        mock_run.return_value = MagicMock(returncode=0)
        backend = HyprlandBackend()
        result = backend.apply("/tmp/test.jpg")
        assert result is True

    @patch("subprocess.run")
    def test_apply_file_not_found(self, mock_run) -> None:
        mock_run.side_effect = FileNotFoundError("hyprctl not found")
        backend = HyprlandBackend()
        result = backend.apply("/tmp/test.jpg")
        assert result is False

    def test_check_dependencies_found(self) -> None:
        with patch("shutil.which", side_effect=["/usr/bin/hyprctl", "/usr/bin/hyprpaper"]):
            assert HyprlandBackend.check_dependencies() is True

    def test_check_dependencies_not_found(self) -> None:
        with patch("shutil.which", return_value=None):
            assert HyprlandBackend.check_dependencies() is False


class TestGnomeBackend:
    def test_get_name(self) -> None:
        backend = GnomeBackend()
        assert backend.get_name() == "GNOME"

    @patch("subprocess.run")
    def test_apply_success(self, mock_run) -> None:
        mock_run.return_value = MagicMock(returncode=0)
        backend = GnomeBackend()
        result = backend.apply("/tmp/test.jpg")
        assert result is True

    @patch("subprocess.run")
    def test_apply_file_not_found(self, mock_run) -> None:
        mock_run.side_effect = FileNotFoundError("gsettings not found")
        backend = GnomeBackend()
        result = backend.apply("/tmp/test.jpg")
        assert result is False

    def test_check_dependencies_found(self) -> None:
        with patch("shutil.which", return_value="/usr/bin/gsettings"):
            assert GnomeBackend.check_dependencies() is True

    def test_check_dependencies_not_found(self) -> None:
        with patch("shutil.which", return_value=None):
            assert GnomeBackend.check_dependencies() is False


class TestKdeBackend:
    def test_get_name(self) -> None:
        backend = KdeBackend()
        assert backend.get_name() == "KDE"

    @patch("subprocess.run")
    def test_apply_success(self, mock_run) -> None:
        mock_run.return_value = MagicMock(returncode=0)
        backend = KdeBackend()
        result = backend.apply("/tmp/test.jpg")
        assert result is True

    @patch("subprocess.run")
    def test_apply_file_not_found(self, mock_run) -> None:
        mock_run.side_effect = FileNotFoundError("qdbus not found")
        backend = KdeBackend()
        result = backend.apply("/tmp/test.jpg")
        assert result is False

    def test_check_dependencies_found(self) -> None:
        with patch("shutil.which", return_value="/usr/bin/qdbus"):
            assert KdeBackend.check_dependencies() is True

    def test_check_dependencies_not_found(self) -> None:
        with patch("shutil.which", return_value=None):
            assert KdeBackend.check_dependencies() is False


class TestWallpaperServiceIntegration:
    def test_apply_delegates_to_backend(self) -> None:
        service = WallpaperService()
        mock_backend = MagicMock()
        mock_backend.apply.return_value = True
        service._backend = mock_backend
        result = service.apply("/tmp/test.jpg")
        assert result is True
        mock_backend.apply.assert_called_once_with("/tmp/test.jpg")

    def test_get_backend_name(self) -> None:
        service = WallpaperService()
        mock_backend = MagicMock()
        mock_backend.get_name.return_value = "KDE"
        service._backend = mock_backend
        assert service.get_backend_name() == "KDE"

    def test_backend_lazy_initialization(self) -> None:
        service = WallpaperService()
        assert service._backend is None
        _ = service.backend
        assert service._backend is not None
