from __future__ import annotations

import logging
import sqlite3
import threading
from pathlib import Path

from unsplash_wallpaper.constants import DATABASE_PATH, DB_SCHEMA_VERSION
from unsplash_wallpaper.models.wallpaper import Wallpaper

logger = logging.getLogger(__name__)


class Database:
    _instance: Database | None = None
    _lock: threading.Lock = threading.Lock()

    def __init__(self, db_path: Path = DATABASE_PATH) -> None:
        self.db_path = db_path
        self.conn: sqlite3.Connection | None = None
        self._local = threading.local()

    @classmethod
    def get_instance(cls, db_path: Path = DATABASE_PATH) -> Database:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(db_path)
                    cls._instance.initialize()
        return cls._instance

    def _get_connection(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            self._local.conn = conn
        return self._local.conn

    def initialize(self) -> None:
        conn = self._get_connection()
        conn.executescript(self._schema_sql())
        conn.commit()
        self._migrate()
        logger.info("Database initialized at %s", self.db_path)

    def _schema_sql(self) -> str:
        return """
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS wallpapers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            unsplash_id TEXT NOT NULL UNIQUE,
            author TEXT NOT NULL DEFAULT '',
            description TEXT NOT NULL DEFAULT '',
            local_path TEXT NOT NULL DEFAULT '',
            download_location TEXT NOT NULL DEFAULT '',
            category TEXT NOT NULL DEFAULT '',
            url TEXT NOT NULL DEFAULT '',
            downloaded_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_wallpapers_unsplash_id
            ON wallpapers(unsplash_id);
        CREATE INDEX IF NOT EXISTS idx_wallpapers_downloaded_at
            ON wallpapers(downloaded_at);
        CREATE INDEX IF NOT EXISTS idx_wallpapers_category
            ON wallpapers(category);
        """

    def _migrate(self) -> None:
        conn = self._get_connection()
        cur = conn.execute("SELECT value FROM meta WHERE key = 'schema_version'")
        row = cur.fetchone()
        version = int(row[0]) if row else 0
        if version < DB_SCHEMA_VERSION:
            conn.execute(
                "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                ("schema_version", str(DB_SCHEMA_VERSION)),
            )
            conn.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                ("schema_version", str(DB_SCHEMA_VERSION)),
            )
            conn.commit()
            logger.info("Schema migrated to version %d", DB_SCHEMA_VERSION)

    # --- Settings ---

    def get_setting(self, key: str, default: str | None = None) -> str | None:
        conn = self._get_connection()
        cur = conn.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cur.fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        conn = self._get_connection()
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, value),
        )
        conn.commit()

    def get_all_settings(self) -> dict[str, str]:
        conn = self._get_connection()
        cur = conn.execute("SELECT key, value FROM settings")
        return {row["key"]: row["value"] for row in cur.fetchall()}

    # --- Wallpapers ---

    def add_wallpaper(self, wallpaper: Wallpaper) -> int:
        conn = self._get_connection()
        cur = conn.execute(
            """INSERT INTO wallpapers
               (unsplash_id, author, description, local_path,
                download_location, category, url, downloaded_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                wallpaper.unsplash_id,
                wallpaper.author,
                wallpaper.description,
                wallpaper.local_path,
                wallpaper.download_location,
                wallpaper.category,
                wallpaper.url,
                wallpaper.downloaded_at,
            ),
        )
        conn.commit()
        return cur.lastrowid

    def get_wallpaper(self, wallpaper_id: int) -> Wallpaper | None:
        conn = self._get_connection()
        cur = conn.execute("SELECT * FROM wallpapers WHERE id = ?", (wallpaper_id,))
        row = cur.fetchone()
        return Wallpaper.from_row(row) if row else None

    def get_wallpaper_by_unsplash_id(self, unsplash_id: str) -> Wallpaper | None:
        conn = self._get_connection()
        cur = conn.execute(
            "SELECT * FROM wallpapers WHERE unsplash_id = ?", (unsplash_id,)
        )
        row = cur.fetchone()
        return Wallpaper.from_row(row) if row else None

    def get_latest_wallpaper(self) -> Wallpaper | None:
        conn = self._get_connection()
        cur = conn.execute(
            "SELECT * FROM wallpapers ORDER BY downloaded_at DESC LIMIT 1"
        )
        row = cur.fetchone()
        return Wallpaper.from_row(row) if row else None

    def get_wallpapers(
        self, limit: int = 100, offset: int = 0
    ) -> list[Wallpaper]:
        conn = self._get_connection()
        cur = conn.execute(
            "SELECT * FROM wallpapers ORDER BY downloaded_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        return [Wallpaper.from_row(row) for row in cur.fetchall()]

    def count_wallpapers(self) -> int:
        conn = self._get_connection()
        cur = conn.execute("SELECT COUNT(*) as cnt FROM wallpapers")
        return cur.fetchone()["cnt"]

    def delete_wallpaper(self, wallpaper_id: int) -> None:
        conn = self._get_connection()
        conn.execute("DELETE FROM wallpapers WHERE id = ?", (wallpaper_id,))
        conn.commit()

    def get_oldest_wallpapers(self, count: int) -> list[Wallpaper]:
        conn = self._get_connection()
        cur = conn.execute(
            "SELECT * FROM wallpapers ORDER BY downloaded_at ASC LIMIT ?",
            (count,),
        )
        return [Wallpaper.from_row(row) for row in cur.fetchall()]

    def wallpaper_exists(self, unsplash_id: str) -> bool:
        conn = self._get_connection()
        cur = conn.execute(
            "SELECT COUNT(*) as cnt FROM wallpapers WHERE unsplash_id = ?",
            (unsplash_id,),
        )
        return cur.fetchone()["cnt"] > 0

    def search_wallpapers(self, query: str) -> list[Wallpaper]:
        conn = self._get_connection()
        cur = conn.execute(
            "SELECT * FROM wallpapers WHERE author LIKE ? OR description LIKE ? OR category LIKE ? ORDER BY downloaded_at DESC",
            (f"%{query}%", f"%{query}%", f"%{query}%"),
        )
        return [Wallpaper.from_row(row) for row in cur.fetchall()]

    def close(self) -> None:
        if hasattr(self._local, "conn") and self._local.conn:
            self._local.conn.close()
            self._local.conn = None

    def close_all(self) -> None:
        if self.conn:
            self.conn.close()
            self.conn = None
