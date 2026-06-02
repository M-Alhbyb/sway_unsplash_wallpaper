from pathlib import Path

APP_ID = "com.unsplash.wallpaper"
APP_NAME = "Unsplash Wallpaper"
VERSION = "1.0.0"

DATA_DIR = Path.home() / ".local" / "share" / "unsplash-wallpaper"
WALLPAPERS_DIR = DATA_DIR / "wallpapers"
DATABASE_PATH = DATA_DIR / "database.db"
LOG_DIR = DATA_DIR / "logs"
LOG_FILE = LOG_DIR / "app.log"
AUTOSTART_FILE = Path.home() / ".config" / "autostart" / f"{APP_ID}.desktop"
SYSTEMD_SERVICE_DIR = Path.home() / ".config" / "systemd" / "user"
SYSTEMD_SERVICE_FILE = SYSTEMD_SERVICE_DIR / f"{APP_ID}.service"
SYSTEMD_TIMER_FILE = SYSTEMD_SERVICE_DIR / f"{APP_ID}.timer"

API_BASE_URL = "https://api.unsplash.com"
API_PHOTOS_RANDOM = "/photos/random"

CATEGORIES: list[str] = [
    "nature",
    "technology",
    "space",
    "cars",
    "architecture",
    "minimal",
    "mountains",
    "forests",
    "city",
    "gaming",
]

CATEGORY_LABELS: dict[str, str] = {
    "nature": "Nature",
    "technology": "Technology",
    "space": "Space",
    "cars": "Cars",
    "architecture": "Architecture",
    "minimal": "Minimal",
    "mountains": "Mountains",
    "forests": "Forests",
    "city": "City",
    "gaming": "Gaming",
}

INTERVALS: dict[str, int] = {
    "15 minutes": 15,
    "30 minutes": 30,
    "1 hour": 60,
    "3 hours": 180,
    "6 hours": 360,
    "12 hours": 720,
    "24 hours": 1440,
}

DEFAULT_INTERVAL = "1 hour"
DEFAULT_MAX_WALLPAPERS = 100
DEFAULT_RESOLUTION = "full_hd"
DEFAULT_RETRY_LIMIT = 20

RESOLUTIONS: dict[str, dict[str, int | str]] = {
    "hd": {"width": 1280, "height": 720, "label": "HD (1280x720)"},
    "full_hd": {"width": 1920, "height": 1080, "label": "Full HD (1920x1080)"},
    "2k": {"width": 2560, "height": 1440, "label": "2K (2560x1440)"},
    "4k": {"width": 3840, "height": 2160, "label": "4K (3840x2160)"},
    "original": {"width": 0, "height": 0, "label": "Original"},
}

RESOLUTION_KEYS = ["hd", "full_hd", "2k", "4k", "original"]

DEFAULT_SETTINGS: dict[str, str] = {
    "unsplash_access_key": "",
    "update_interval": DEFAULT_INTERVAL,
    "max_wallpapers": str(DEFAULT_MAX_WALLPAPERS),
    "autostart": "false",
    "notifications": "true",
    "resolution": DEFAULT_RESOLUTION,
    "dark_mode": "follow_system",
    "categories": "",
    "keywords": "",
}

DB_SCHEMA_VERSION = 1
