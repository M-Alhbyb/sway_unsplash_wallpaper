from __future__ import annotations

from unsplash_wallpaper.config import Config
from unsplash_wallpaper.constants import DEFAULT_SETTINGS


class TestConfig:
    def test_default_values(self, config: Config) -> None:
        for key, default in DEFAULT_SETTINGS.items():
            assert config.get(key) == default

    def test_set_and_get(self, config: Config) -> None:
        config.set("test_key", "test_value")
        assert config.get("test_key") == "test_value"

    def test_get_bool(self, config: Config) -> None:
        config.set("flag", "true")
        assert config.get_bool("flag") is True
        config.set("flag", "false")
        assert config.get_bool("flag") is False

    def test_set_bool(self, config: Config) -> None:
        config.set_bool("flag", True)
        assert config.get("flag") == "true"
        config.set_bool("flag", False)
        assert config.get("flag") == "false"

    def test_get_int(self, config: Config) -> None:
        config.set("number", "42")
        assert config.get_int("number") == 42
        assert config.get_int("nonexistent", 10) == 10

    def test_categories(self, config: Config) -> None:
        assert config.get_categories() == []
        config.set_categories(["nature", "space"])
        assert config.get_categories() == ["nature", "space"]
        config.set_categories([])
        assert config.get_categories() == []

    def test_has_valid_api_key(self, config: Config) -> None:
        assert config.has_valid_api_key() is False
        config.set(
            "unsplash_access_key", "short"
        )
        assert config.has_valid_api_key() is False
        config.set(
            "unsplash_access_key",
            "abcdefghijklmnopqr",
        )
        assert config.has_valid_api_key() is True

    def test_to_dict(self, config: Config) -> None:
        config.set("key1", "val1")
        config.set("key2", "val2")
        d = config.to_dict()
        assert d["key1"] == "val1"
        assert d["key2"] == "val2"
        assert "unsplash_access_key" in d

    def test_reload(self, config: Config) -> None:
        config.set("key", "original")
        config2 = Config(config._db)
        assert config2.get("key") == "original"
