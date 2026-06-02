from __future__ import annotations

import datetime
from dataclasses import dataclass, field


@dataclass
class Wallpaper:
    id: int | None = field(default=None)
    unsplash_id: str = field(default="")
    author: str = field(default="")
    description: str = field(default="")
    local_path: str = field(default="")
    download_location: str = field(default="")
    category: str = field(default="")
    url: str = field(default="")
    downloaded_at: str = field(default_factory=lambda: datetime.datetime.now().isoformat())

    @property
    def filename(self) -> str:
        return f"{self.unsplash_id}.jpg"

    @classmethod
    def from_row(cls, row: tuple) -> Wallpaper:
        return cls(
            id=row[0],
            unsplash_id=row[1],
            author=row[2],
            description=row[3],
            local_path=row[4],
            download_location=row[5],
            category=row[6],
            url=row[7],
            downloaded_at=row[8],
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "unsplash_id": self.unsplash_id,
            "author": self.author,
            "description": self.description,
            "local_path": self.local_path,
            "download_location": self.download_location,
            "category": self.category,
            "url": self.url,
            "downloaded_at": self.downloaded_at,
        }
