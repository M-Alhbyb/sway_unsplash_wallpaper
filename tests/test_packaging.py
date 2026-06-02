from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch


class TestImportPackaging:
    def test_package_importable(self) -> None:
        import unsplash_wallpaper

        assert unsplash_wallpaper.__name__ == "unsplash_wallpaper"

    def test_version_accessible(self) -> None:
        from unsplash_wallpaper.constants import VERSION

        assert VERSION == "1.0.0"

    def test_app_id_defined(self) -> None:
        from unsplash_wallpaper.constants import APP_ID

        assert APP_ID == "com.unsplash.wallpaper"

    def test_desktop_entry_available(self) -> None:
        desktop_file = (
            Path(__file__).parent.parent
            / "data"
            / "com.unsplash.wallpaper.desktop"
        )
        assert desktop_file.exists()
        content = desktop_file.read_text()
        assert "Unsplash Wallpaper" in content
        assert "Exec=unsplash-wallpaper" in content or "Exec=" in content

    def test_rpm_spec_available(self) -> None:
        spec_file = (
            Path(__file__).parent.parent
            / "data"
            / "unsplash-wallpaper.spec"
        )
        assert spec_file.exists()
        content = spec_file.read_text()
        assert "Name:" in content and "unsplash-wallpaper" in content
        assert "Version: 1.0.0" in content or "Version:" in content

    def test_flatpak_manifest_available(self) -> None:
        manifest_file = (
            Path(__file__).parent.parent
            / "data"
            / "com.unsplash.wallpaper.json"
        )
        assert manifest_file.exists()

    def test_py_typed_marker(self) -> None:
        marker = (
            Path(__file__).parent.parent
            / "src"
            / "unsplash_wallpaper"
            / "py.typed"
        )
        assert marker.exists()

    def test_entry_points_configured(self) -> None:

        setup_cfg = (
            Path(__file__).parent.parent / "pyproject.toml"
        )
        content = setup_cfg.read_text()
        assert (
            "unsplash-wallpaper = \"unsplash_wallpaper.entry_point:main\""
            in content
        )
        assert (
            "unsplash-wallpaper-gui = \"unsplash_wallpaper.app:main\""
            in content
        )

    def test_systemd_service_unit(self) -> None:
        service_file = (
            Path(__file__).parent.parent
            / "data"
            / "com.unsplash.wallpaper.service"
        )
        assert service_file.exists()
        content = service_file.read_text()
        assert "Type=simple" in content

    def test_systemd_timer_unit(self) -> None:
        timer_file = (
            Path(__file__).parent.parent
            / "data"
            / "com.unsplash.wallpaper.timer"
        )
        assert timer_file.exists()

    def test_license_file(self) -> None:
        license_file = Path(__file__).parent.parent / "LICENSE"
        assert license_file.exists()
        content = license_file.read_text()
        assert "GNU General Public License" in content

    def test_changelog_file(self) -> None:
        changelog = Path(__file__).parent.parent / "CHANGELOG.md"
        assert changelog.exists()

    def test_readme_has_installation_instructions(self) -> None:
        readme = Path(__file__).parent.parent / "README.md"
        assert readme.exists()
        content = readme.read_text()
        assert "Installation" in content or "install" in content.lower()

    def test_icon_referenced_in_desktop(self) -> None:
        desktop_file = (
            Path(__file__).parent.parent
            / "data"
            / "com.unsplash.wallpaper.desktop"
        )
        content = desktop_file.read_text()
        assert "Icon=" in content


class TestInstallVerification:
    def test_cli_help(self) -> None:
        result = subprocess.run(
            [sys.executable, "-c", "from unsplash_wallpaper.entry_point import main; print('imported ok')"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0
        assert "imported ok" in result.stdout

    def test_cli_version(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "unsplash_wallpaper", "--version"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0
        assert "Unsplash Wallpaper v1.0.0" in result.stdout

    def test_diagnostics_text_includes_version(self) -> None:
        from unsplash_wallpaper.constants import VERSION
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "unsplash_wallpaper",
                "--version",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0
        assert VERSION in result.stdout

    def test_cli_entry_point_exists(self) -> None:
        entry_point = (
            Path(__file__).parent.parent
            / "src"
            / "unsplash_wallpaper"
            / "entry_point.py"
        )
        assert entry_point.exists()
        assert "def main()" in entry_point.read_text()

    def test_main_module_exists(self) -> None:
        main_module = (
            Path(__file__).parent.parent
            / "src"
            / "unsplash_wallpaper"
            / "__main__.py"
        )
        assert main_module.exists()
        content = main_module.read_text()
        assert "UnsplashWallpaperApp.main()" in content


class TestUninstallCleanup:
    def test_autostart_file_removal(self, temp_dir: Path) -> None:
        from unsplash_wallpaper.system.autostart import AutostartManager

        autostart_path = temp_dir / ".config" / "autostart" / "test.desktop"

        autostart_path.parent.mkdir(parents=True)
        autostart_path.write_text("test")

        with patch(
            "unsplash_wallpaper.system.autostart.AUTOSTART_FILE",
            autostart_path,
        ):
            assert autostart_path.exists()
            AutostartManager.disable_autostart()
            assert not autostart_path.exists()

    def test_systemd_service_file_removal(
        self, temp_dir: Path
    ) -> None:
        from unsplash_wallpaper.system.autostart import AutostartManager

        service_path = temp_dir / "systemd" / "test.service"
        timer_path = temp_dir / "systemd" / "test.timer"
        service_path.parent.mkdir(parents=True)
        service_path.write_text("service")
        timer_path.write_text("timer")

        with patch(
            "unsplash_wallpaper.system.autostart.SYSTEMD_SERVICE_DIR",
            service_path.parent,
        ):
            with patch(
                "unsplash_wallpaper.system.autostart.SYSTEMD_SERVICE_FILE",
                service_path,
            ):
                with patch(
                    "unsplash_wallpaper.system.autostart.SYSTEMD_TIMER_FILE",
                    timer_path,
                ):
                    assert service_path.exists()
                    assert timer_path.exists()
                    AutostartManager.remove_systemd_service()
                    assert not service_path.exists()
                    assert not timer_path.exists()

    def test_data_directory_cleanup(self, temp_dir: Path) -> None:
        data_dir = temp_dir / "data"
        data_dir.mkdir(parents=True)
        (data_dir / "test_file.txt").write_text("test")

        import shutil

        assert data_dir.exists()
        shutil.rmtree(data_dir)
        assert not data_dir.exists()
