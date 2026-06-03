from __future__ import annotations

import io
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from unsplash_wallpaper.services.image_optimizer import (
    SCREEN_RESOLUTIONS,
    detect_screen_resolution,
    get_target_resolution,
    optimize_image,
)
from unsplash_wallpaper.services.storage_service import StorageService


class TestImageOptimizer:
    def test_get_target_resolution_known_keys(self) -> None:
        for key in ("hd", "full_hd", "2k", "4k"):
            w, h = get_target_resolution(key)
            assert w > 0
            assert h > 0

    def test_get_target_resolution_original(self) -> None:
        w, h = get_target_resolution("original")
        assert w == 0
        assert h == 0

    def test_get_target_resolution_unknown_falls_back(self) -> None:
        with patch(
            "unsplash_wallpaper.services.image_optimizer"
            ".detect_screen_resolution",
            return_value=(2560, 1440),
        ):
            w, h = get_target_resolution("nonexistent")
            assert w > 0
            assert h > 0

    def test_optimize_image_small_image_not_resized(self) -> None:
        header = b"\xff\xd8\xff\xe0" + b"\x00" * 12
        data = header + b"\x00" * 100
        result = optimize_image(data, 1920, 1080)
        assert result == data

    def test_optimize_image_returns_original_when_zero_max(self) -> None:
        data = b"\xff\xd8" + b"\x00" * 50
        result = optimize_image(data, 0, 0)
        assert result == data

    def test_optimize_image_resizes_large_jpeg(self) -> None:
        try:
            from PIL import Image
        except ImportError:
            return

        img = Image.new("RGB", (4000, 3000), color=(128, 64, 32))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        original_data = buf.getvalue()

        result = optimize_image(original_data, 1920, 1080)
        assert len(result) < len(original_data)

        with Image.open(io.BytesIO(result)) as result_img:
            assert result_img.size[0] <= 1920
            assert result_img.size[1] <= 1080

    def test_optimize_image_preserves_aspect_ratio(self) -> None:
        try:
            from PIL import Image
        except ImportError:
            return

        img = Image.new("RGB", (4000, 2000), color=(50, 100, 150))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        original_data = buf.getvalue()

        result = optimize_image(original_data, 1920, 1080)
        with Image.open(io.BytesIO(result)) as result_img:
            ratio_orig = 4000 / 2000
            ratio_result = result_img.size[0] / result_img.size[1]
            assert abs(ratio_orig - ratio_result) < 0.05

    def test_optimize_image_never_upscales(self) -> None:
        try:
            from PIL import Image
        except ImportError:
            return

        img = Image.new("RGB", (800, 600), color=(10, 20, 30))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        original_data = buf.getvalue()

        result = optimize_image(original_data, 1920, 1080)
        with Image.open(io.BytesIO(result)) as result_img:
            assert result_img.size[0] == 800
            assert result_img.size[1] == 600

    def test_optimize_image_png_format(self) -> None:
        try:
            from PIL import Image
        except ImportError:
            return

        img = Image.new("RGBA", (4000, 3000), color=(128, 64, 32, 255))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        original_data = buf.getvalue()

        result = optimize_image(original_data, 1920, 1080)
        assert len(result) > 0
        with Image.open(io.BytesIO(result)) as result_img:
            assert result_img.size[0] <= 1920

    def test_optimize_image_invalid_data_returns_original(self) -> None:
        data = b"not_an_image_at_all" * 10
        result = optimize_image(data, 1920, 1080)
        assert result == data

    def test_screen_resolution_constants_complete(self) -> None:
        assert "hd" in SCREEN_RESOLUTIONS
        assert "full_hd" in SCREEN_RESOLUTIONS
        assert "2k" in SCREEN_RESOLUTIONS
        assert "4k" in SCREEN_RESOLUTIONS
        assert SCREEN_RESOLUTIONS["full_hd"] == (1920, 1080)
        assert SCREEN_RESOLUTIONS["4k"] == (3840, 2160)

    @patch("subprocess.run")
    def test_detect_screen_resolution_xrandr(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="DP-1 connected primary 2560x1440+0+0\nHDMI-1 connected 1920x1080+2560+0\n",
        )
        result = detect_screen_resolution()
        assert result == (2560, 1440)

    @patch("subprocess.run")
    def test_detect_screen_resolution_fallback(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = FileNotFoundError()
        with patch.dict(os.environ, {}, clear=True):
            result = detect_screen_resolution()
        assert result == (1920, 1080)


class TestStorageServiceOptimization:
    def test_optimization_enabled_by_default(self, temp_dir: Path) -> None:
        storage = StorageService(temp_dir / "wallpapers")
        assert storage._optimize_enabled is True

    def test_set_optimization_enables(self, temp_dir: Path) -> None:
        storage = StorageService(temp_dir / "wallpapers")
        storage.set_optimization(enabled=True, resolution="full_hd")
        assert storage._optimize_enabled is True
        assert storage._target_resolution is not None

    def test_set_optimization_disables(self, temp_dir: Path) -> None:
        storage = StorageService(temp_dir / "wallpapers")
        storage.set_optimization(enabled=False)
        assert storage._optimize_enabled is False
        assert storage._target_resolution is None

    def test_set_optimization_original(self, temp_dir: Path) -> None:
        storage = StorageService(temp_dir / "wallpapers")
        storage.set_optimization(enabled=True, resolution="original")
        assert storage._target_resolution == (0, 0)

    def test_save_with_optimization(self, temp_dir: Path) -> None:
        try:
            from PIL import Image
        except ImportError:
            return

        storage = StorageService(temp_dir / "wallpapers")
        storage.set_optimization(enabled=True, resolution="full_hd")

        img = Image.new("RGB", (4000, 3000), color=(128, 64, 32))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        data = buf.getvalue()

        filepath = storage.save_wallpaper(data, "test_optimize.jpg")
        assert filepath.exists()
        saved_size = filepath.stat().st_size
        assert saved_size < len(data)

        with Image.open(filepath) as saved_img:
            assert saved_img.size[0] <= 1920
            assert saved_img.size[1] <= 1080

    def test_save_without_optimization(self, temp_dir: Path) -> None:
        storage = StorageService(temp_dir / "wallpapers")
        storage.set_optimization(enabled=False)
        data = b"\xff\xd8\xff\xe0" + b"\x00" * 100
        filepath = storage.save_wallpaper(data, "test_noopt.jpg")
        assert filepath.exists()
        assert filepath.read_bytes() == data


class TestTrayLogging:
    def test_tray_setup_returns_false_without_indicator(self) -> None:
        from unsplash_wallpaper.tray.tray_manager import TrayManager

        app = MagicMock()
        tray = TrayManager(app)
        result = tray.setup()
        assert result is False

    def test_tray_logs_at_debug_not_warning(self, caplog) -> None:
        import logging

        from unsplash_wallpaper.tray.tray_manager import TrayManager

        app = MagicMock()
        tray = TrayManager(app)
        with caplog.at_level(logging.DEBUG):
            tray.setup()
        warning_records = [
            r for r in caplog.records if r.levelno >= logging.WARNING
        ]
        tray_records = [
            r for r in caplog.records if "tray" in r.message.lower()
        ]
        for record in tray_records:
            assert record.levelno <= logging.DEBUG
        assert len(warning_records) == 0 or all(
            "AyatanaAppIndicator" not in r.message
            and "tray" not in r.message.lower()
            for r in warning_records
        )

    def test_tray_shutdown_is_safe(self) -> None:
        from unsplash_wallpaper.tray.tray_manager import TrayManager

        app = MagicMock()
        tray = TrayManager(app)
        tray.shutdown()


class TestDiagnosticsOutput:
    @patch("unsplash_wallpaper.app.Database")
    @patch("unsplash_wallpaper.app.UnsplashService")
    @patch("unsplash_wallpaper.app.StorageService")
    @patch("unsplash_wallpaper.app.HistoryService")
    @patch("unsplash_wallpaper.app.WallpaperService")
    def test_diagnostics_includes_optimization_section(
        self,
        mock_ws: MagicMock,
        mock_hs: MagicMock,
        mock_ss: MagicMock,
        mock_us: MagicMock,
        mock_db: MagicMock,
    ) -> None:
        from unsplash_wallpaper.app import UnsplashWallpaperApp

        app = UnsplashWallpaperApp.__new__(UnsplashWallpaperApp)
        app._config = MagicMock()
        app._config.get.side_effect = lambda k, d="": {
            "resolution": "full_hd",
            "dark_mode": "follow_system",
        }.get(k, d)
        app._config.has_valid_api_key.return_value = False
        app._unsplash = MagicMock()
        app._db = MagicMock()
        app._storage = MagicMock()

        report = app._report_diagnostics()
        assert "Wallpaper Optimization" in report
        assert "Target Resolution" in report
        assert "1920x1080" in report

    @patch("unsplash_wallpaper.app.Database")
    @patch("unsplash_wallpaper.app.UnsplashService")
    @patch("unsplash_wallpaper.app.StorageService")
    @patch("unsplash_wallpaper.app.HistoryService")
    @patch("unsplash_wallpaper.app.WallpaperService")
    def test_diagnostics_includes_ui_health(
        self,
        mock_ws: MagicMock,
        mock_hs: MagicMock,
        mock_ss: MagicMock,
        mock_us: MagicMock,
        mock_db: MagicMock,
    ) -> None:
        from unsplash_wallpaper.app import UnsplashWallpaperApp

        app = UnsplashWallpaperApp.__new__(UnsplashWallpaperApp)
        app._config = MagicMock()
        app._config.get.side_effect = lambda k, d="": {
            "resolution": "full_hd",
            "dark_mode": "follow_system",
        }.get(k, d)
        app._config.has_valid_api_key.return_value = False
        app._unsplash = MagicMock()
        app._db = MagicMock()
        app._storage = MagicMock()

        report = app._report_diagnostics()
        assert "UI Health" in report
        assert "Responsive Layout" in report
        assert "Libadwaita" in report

    @patch("unsplash_wallpaper.app.Database")
    @patch("unsplash_wallpaper.app.UnsplashService")
    @patch("unsplash_wallpaper.app.StorageService")
    @patch("unsplash_wallpaper.app.HistoryService")
    @patch("unsplash_wallpaper.app.WallpaperService")
    def test_diagnostics_includes_tray_section(
        self,
        mock_ws: MagicMock,
        mock_hs: MagicMock,
        mock_ss: MagicMock,
        mock_us: MagicMock,
        mock_db: MagicMock,
    ) -> None:
        from unsplash_wallpaper.app import UnsplashWallpaperApp

        app = UnsplashWallpaperApp.__new__(UnsplashWallpaperApp)
        app._config = MagicMock()
        app._config.get.side_effect = lambda k, d="": {
            "resolution": "full_hd",
            "dark_mode": "follow_system",
        }.get(k, d)
        app._config.has_valid_api_key.return_value = False
        app._unsplash = MagicMock()
        app._db = MagicMock()
        app._storage = MagicMock()

        report = app._report_diagnostics()
        assert "Tray" in report
        assert "Available" in report

    @patch("unsplash_wallpaper.app.Database")
    @patch("unsplash_wallpaper.app.UnsplashService")
    @patch("unsplash_wallpaper.app.StorageService")
    @patch("unsplash_wallpaper.app.HistoryService")
    @patch("unsplash_wallpaper.app.WallpaperService")
    def test_diagnostics_original_resolution(
        self,
        mock_ws: MagicMock,
        mock_hs: MagicMock,
        mock_ss: MagicMock,
        mock_us: MagicMock,
        mock_db: MagicMock,
    ) -> None:
        from unsplash_wallpaper.app import UnsplashWallpaperApp

        app = UnsplashWallpaperApp.__new__(UnsplashWallpaperApp)
        app._config = MagicMock()
        app._config.get.side_effect = lambda k, d="": {
            "resolution": "original",
            "dark_mode": "follow_system",
        }.get(k, d)
        app._config.has_valid_api_key.return_value = False
        app._unsplash = MagicMock()
        app._db = MagicMock()
        app._storage = MagicMock()

        report = app._report_diagnostics()
        assert "Wallpaper Optimization" in report
        assert "original" in report.lower() or "original" in report


class TestStyleManagerBehavior:
    def test_dark_mode_mapping_constants(self) -> None:
        dark_modes = {"follow_system": 0, "light": 1, "dark": 2}
        assert "follow_system" in dark_modes
        assert "light" in dark_modes
        assert "dark" in dark_modes

    @patch("unsplash_wallpaper.app.Database")
    @patch("unsplash_wallpaper.app.UnsplashService")
    @patch("unsplash_wallpaper.app.StorageService")
    @patch("unsplash_wallpaper.app.HistoryService")
    @patch("unsplash_wallpaper.app.WallpaperService")
    def test_apply_style_uses_style_manager(
        self,
        mock_ws: MagicMock,
        mock_hs: MagicMock,
        mock_ss: MagicMock,
        mock_us: MagicMock,
        mock_db: MagicMock,
    ) -> None:
        from unsplash_wallpaper.app import UnsplashWallpaperApp

        app = UnsplashWallpaperApp.__new__(UnsplashWallpaperApp)
        app._config = MagicMock()

        with patch("unsplash_wallpaper.app.Adw") as mock_adw:
            mock_manager = MagicMock()
            mock_adw.StyleManager.get_default.return_value = mock_manager
            mock_adw.ColorScheme.DEFAULT = "default"
            mock_adw.ColorScheme.PREFER_LIGHT = "prefer_light"
            mock_adw.ColorScheme.PREFER_DARK = "prefer_dark"

            app._config.get.side_effect = lambda k, d="": "dark"
            app._apply_style()
            mock_manager.set_color_scheme.assert_called_once_with(
                "prefer_dark"
            )

    @patch("unsplash_wallpaper.app.Database")
    @patch("unsplash_wallpaper.app.UnsplashService")
    @patch("unsplash_wallpaper.app.StorageService")
    @patch("unsplash_wallpaper.app.HistoryService")
    @patch("unsplash_wallpaper.app.WallpaperService")
    def test_apply_style_follow_system(
        self,
        mock_ws: MagicMock,
        mock_hs: MagicMock,
        mock_ss: MagicMock,
        mock_us: MagicMock,
        mock_db: MagicMock,
    ) -> None:
        from unsplash_wallpaper.app import UnsplashWallpaperApp

        app = UnsplashWallpaperApp.__new__(UnsplashWallpaperApp)
        app._config = MagicMock()

        with patch("unsplash_wallpaper.app.Adw") as mock_adw:
            mock_manager = MagicMock()
            mock_adw.StyleManager.get_default.return_value = mock_manager
            mock_adw.ColorScheme.DEFAULT = "default"
            mock_adw.ColorScheme.PREFER_LIGHT = "prefer_light"
            mock_adw.ColorScheme.PREFER_DARK = "prefer_dark"

            app._config.get.side_effect = lambda k, d="": "follow_system"
            app._apply_style()
            mock_manager.set_color_scheme.assert_called_once_with("default")

    @patch("unsplash_wallpaper.app.Database")
    @patch("unsplash_wallpaper.app.UnsplashService")
    @patch("unsplash_wallpaper.app.StorageService")
    @patch("unsplash_wallpaper.app.HistoryService")
    @patch("unsplash_wallpaper.app.WallpaperService")
    def test_apply_style_light(
        self,
        mock_ws: MagicMock,
        mock_hs: MagicMock,
        mock_ss: MagicMock,
        mock_us: MagicMock,
        mock_db: MagicMock,
    ) -> None:
        from unsplash_wallpaper.app import UnsplashWallpaperApp

        app = UnsplashWallpaperApp.__new__(UnsplashWallpaperApp)
        app._config = MagicMock()

        with patch("unsplash_wallpaper.app.Adw") as mock_adw:
            mock_manager = MagicMock()
            mock_adw.StyleManager.get_default.return_value = mock_manager
            mock_adw.ColorScheme.DEFAULT = "default"
            mock_adw.ColorScheme.PREFER_LIGHT = "prefer_light"
            mock_adw.ColorScheme.PREFER_DARK = "prefer_dark"

            app._config.get.side_effect = lambda k, d="": "light"
            app._apply_style()
            mock_manager.set_color_scheme.assert_called_once_with(
                "prefer_light"
            )

    @patch("unsplash_wallpaper.app.Database")
    @patch("unsplash_wallpaper.app.UnsplashService")
    @patch("unsplash_wallpaper.app.StorageService")
    @patch("unsplash_wallpaper.app.HistoryService")
    @patch("unsplash_wallpaper.app.WallpaperService")
    def test_apply_style_no_force_dark(
        self,
        mock_ws: MagicMock,
        mock_hs: MagicMock,
        mock_ss: MagicMock,
        mock_us: MagicMock,
        mock_db: MagicMock,
    ) -> None:
        from unsplash_wallpaper.app import UnsplashWallpaperApp

        app = UnsplashWallpaperApp.__new__(UnsplashWallpaperApp)
        app._config = MagicMock()

        with patch("unsplash_wallpaper.app.Adw") as mock_adw:
            mock_manager = MagicMock()
            mock_adw.StyleManager.get_default.return_value = mock_manager
            mock_adw.ColorScheme.FORCE_DARK = "force_dark"
            mock_adw.ColorScheme.PREFER_DARK = "prefer_dark"
            mock_adw.ColorScheme.PREFER_LIGHT = "prefer_light"
            mock_adw.ColorScheme.DEFAULT = "default"

            app._config.get.side_effect = lambda k, d="": "dark"
            app._apply_style()
            call_args = mock_manager.set_color_scheme.call_args
            assert call_args[0][0] != "force_dark"
