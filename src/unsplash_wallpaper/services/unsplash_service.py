from __future__ import annotations

import logging
import random
import time
from typing import Any

import requests

from unsplash_wallpaper.config import Config
from unsplash_wallpaper.constants import (
    API_BASE_URL,
    API_PHOTOS_RANDOM,
    DEFAULT_RETRY_LIMIT,
    RESOLUTIONS,
)

logger = logging.getLogger(__name__)


class UnsplashAPIError(Exception):
    pass


class UnsplashRateLimitError(UnsplashAPIError):
    pass


class UnsplashAuthError(UnsplashAPIError):
    pass


class UnsplashNetworkError(UnsplashAPIError):
    pass


class UnsplashService:
    def __init__(self, config: Config | None = None) -> None:
        self._config = config or Config()
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Accept-Version": "v1",
                "User-Agent": "UnsplashWallpaperManager/1.0",
            }
        )
        self._remaining_requests: int = 50
        self._reset_time: float = 0.0

    def _get_access_key(self) -> str:
        key = self._config.get("unsplash_access_key", "")
        if not key:
            raise UnsplashAuthError("Unsplash access key is not configured")
        return key

    def _handle_rate_limits(self, response: requests.Response) -> None:
        remaining = response.headers.get("X-Ratelimit-Remaining")
        if remaining is not None:
            self._remaining_requests = int(remaining)
        reset = response.headers.get("X-Ratelimit-Reset")
        if reset is not None:
            self._reset_time = float(reset)
        if self._remaining_requests <= 0:
            wait = max(self._reset_time - time.time(), 0)
            logger.warning("Rate limit reached. Resets in %d seconds", wait)
            if wait > 0 and wait < 3600:
                time.sleep(wait + 1)

    def get_random_photo(
        self,
        categories: list[str] | None = None,
        resolution: str = "full_hd",
        retries: int = DEFAULT_RETRY_LIMIT,
        query: str | None = None,
    ) -> dict[str, Any]:
        access_key = self._get_access_key()
        used_ids: set[str] = set()

        for attempt in range(retries):
            try:
                params: dict[str, Any] = {
                    "client_id": access_key,
                    "count": 1,
                }
                if query is not None:
                    params["query"] = query
                elif categories:
                    query = random.choice(categories)
                    params["query"] = query

                res = self._config.get_resolution()
                if res != "original":
                    res_config = RESOLUTIONS.get(res)
                    if res_config:
                        params["w"] = res_config["width"]
                        params["h"] = res_config["height"]

                response = self._session.get(
                    f"{API_BASE_URL}{API_PHOTOS_RANDOM}",
                    params=params,
                    timeout=30,
                )
                self._handle_rate_limits(response)

                if response.status_code == 401:
                    raise UnsplashAuthError("Invalid Unsplash access key")
                if response.status_code == 403:
                    raise UnsplashRateLimitError("API rate limit exceeded")
                if response.status_code == 404:
                    raise UnsplashAPIError("API endpoint not found")
                if response.status_code != 200:
                    raise UnsplashAPIError(
                        f"API returned status {response.status_code}"
                    )

                data = response.json()
                if isinstance(data, list):
                    if not data:
                        if attempt < retries - 1:
                            continue
                        raise UnsplashAPIError("No photos returned from API")
                    photo = data[0]
                else:
                    photo = data

                photo_id = photo.get("id", "")
                if photo_id in used_ids:
                    continue
                used_ids.add(photo_id)

                urls = photo.get("urls", {})
                user = photo.get("user", {})

                result = {
                    "id": photo_id,
                    "author": user.get("name", "Unknown"),
                    "description": photo.get(
                        "description",
                        photo.get("alt_description", ""),
                    )
                    or "",
                    "url": urls.get("full", ""),
                    "download_location": photo.get("links", {}).get(
                        "download_location", ""
                    ),
                    "category": params.get("query", ""),
                    "raw_data": photo,
                }
                logger.info(
                    "Fetched photo %s by %s",
                    photo_id,
                    result["author"],
                )
                return result

            except requests.exceptions.ConnectionError as e:
                logger.error(
                    "Network error on attempt %d/%d: %s",
                    attempt + 1,
                    retries,
                    e,
                )
                if attempt < retries - 1:
                    time.sleep(2**attempt)
                else:
                    raise UnsplashNetworkError(
                        f"Network request failed after {retries} attempts: {e}"
                    ) from e
            except requests.exceptions.Timeout as e:
                logger.error(
                    "Timeout on attempt %d/%d: %s",
                    attempt + 1,
                    retries,
                    e,
                )
                if attempt < retries - 1:
                    time.sleep(2**attempt)
                else:
                    raise UnsplashNetworkError(
                        f"Request timed out after {retries} attempts"
                    ) from e
            except requests.exceptions.RequestException as e:
                logger.error(
                    "Request error on attempt %d/%d: %s",
                    attempt + 1,
                    retries,
                    e,
                )
                if attempt < retries - 1:
                    time.sleep(2**attempt)
                else:
                    raise UnsplashNetworkError(
                        f"Request failed after {retries} attempts: {e}"
                    ) from e

        raise UnsplashAPIError(
            f"Failed to get unique photo after {retries} attempts"
        )

    def download_image(self, url: str) -> bytes:
        try:
            response = self._session.get(url, timeout=60)
            response.raise_for_status()
            logger.info("Downloaded image from %s", url)
            return response.content
        except requests.exceptions.RequestException as e:
            raise UnsplashNetworkError(f"Failed to download image: {e}") from e

    def track_download(self, download_location: str) -> None:
        if not download_location:
            return
        try:
            access_key = self._get_access_key()
            response = self._session.get(
                download_location,
                params={"client_id": access_key},
                timeout=10,
            )
            if response.status_code == 200:
                logger.info("Tracked download at %s", download_location)
            else:
                logger.warning(
                    "Download tracking returned %d for %s",
                    response.status_code,
                    download_location,
                )
        except requests.exceptions.RequestException as e:
            logger.error("Download tracking failed: %s", e)

    @property
    def remaining_requests(self) -> int:
        return self._remaining_requests

    def close(self) -> None:
        self._session.close()

    def __enter__(self) -> UnsplashService:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
