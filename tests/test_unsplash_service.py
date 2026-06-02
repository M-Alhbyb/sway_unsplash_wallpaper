from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

from unsplash_wallpaper.config import Config
from unsplash_wallpaper.services.unsplash_service import (
    UnsplashAuthError,
    UnsplashNetworkError,
    UnsplashRateLimitError,
    UnsplashService,
)


@pytest.fixture
def service() -> UnsplashService:
    config = MagicMock(spec=Config)
    config.get.return_value = "test_access_key_12345"
    config.has_valid_api_key.return_value = True
    config.get_resolution.return_value = "full_hd"
    return UnsplashService(config)


class TestUnsplashService:
    def test_init(self, service: UnsplashService) -> None:
        assert service is not None

    def test_get_access_key_missing(self) -> None:
        config = MagicMock(spec=Config)
        config.get.return_value = ""
        svc = UnsplashService(config)
        with pytest.raises(UnsplashAuthError):
            svc._get_access_key()

    @patch("requests.Session.get")
    def test_get_random_photo_success(
        self, mock_get, service: UnsplashService
    ) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "id": "photo123",
                "user": {"name": "Test Photographer"},
                "description": "A beautiful landscape",
                "alt_description": "landscape",
                "urls": {"full": "https://example.com/photo.jpg"},
                "links": {
                    "download_location": "https://api.unsplash.com/photos/photo123/download"
                },
            }
        ]
        mock_response.headers = {
            "X-Ratelimit-Remaining": "49",
            "X-Ratelimit-Reset": "0",
        }
        mock_get.return_value = mock_response

        result = service.get_random_photo(
            categories=["nature"]
        )
        assert result["id"] == "photo123"
        assert result["author"] == "Test Photographer"
        assert result["category"] == "nature"

    @patch("requests.Session.get")
    def test_rate_limit_handling(
        self, mock_get, service: UnsplashService
    ) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.headers = {
            "X-Ratelimit-Remaining": "0",
            "X-Ratelimit-Reset": "9999999999",
        }
        mock_get.return_value = mock_response

        with pytest.raises(UnsplashRateLimitError):
            service.get_random_photo()

    @patch("requests.Session.get")
    def test_auth_error(
        self, mock_get, service: UnsplashService
    ) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.headers = {}
        mock_get.return_value = mock_response

        with pytest.raises(UnsplashAuthError):
            service.get_random_photo()

    @patch("requests.Session.get")
    def test_get_random_photo_with_query(
        self, mock_get, service: UnsplashService
    ) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "id": "photo123",
                "user": {"name": "Test Photographer"},
                "description": "A beautiful landscape",
                "alt_description": "landscape",
                "urls": {"full": "https://example.com/photo.jpg"},
                "links": {
                    "download_location": "https://api.unsplash.com/photos/photo123/download"
                },
            }
        ]
        mock_response.headers = {
            "X-Ratelimit-Remaining": "49",
            "X-Ratelimit-Reset": "0",
        }
        mock_get.return_value = mock_response

        result = service.get_random_photo(query="sunset")
        assert result["id"] == "photo123"
        assert result["category"] == "sunset"
        call_kwargs = mock_get.call_args[1]
        assert call_kwargs["params"]["query"] == "sunset"

    @patch("requests.Session.get")
    def test_get_random_photo_query_overrides_categories(
        self, mock_get, service: UnsplashService
    ) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "id": "photo123",
                "user": {"name": "Test Photographer"},
                "description": "",
                "alt_description": "",
                "urls": {"full": "https://example.com/photo.jpg"},
                "links": {"download_location": ""},
            }
        ]
        mock_response.headers = {
            "X-Ratelimit-Remaining": "49",
            "X-Ratelimit-Reset": "0",
        }
        mock_get.return_value = mock_response

        result = service.get_random_photo(
            categories=["nature", "space"],
            query="sunset",
        )
        assert result["category"] == "sunset"
        call_kwargs = mock_get.call_args[1]
        assert call_kwargs["params"]["query"] == "sunset"

    @patch("requests.Session.get")
    def test_network_retry(
        self, mock_get, service: UnsplashService
    ) -> None:
        mock_get.side_effect = requests.exceptions.ConnectionError(
            "Connection refused"
        )

        with pytest.raises(UnsplashNetworkError):
            service.get_random_photo(retries=2)
        assert mock_get.call_count == 2

    @patch("requests.Session.get")
    def test_download_image(
        self, mock_get, service: UnsplashService
    ) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"fake_image_data"
        mock_get.return_value = mock_response

        data = service.download_image("https://example.com/image.jpg")
        assert data == b"fake_image_data"

    @patch("requests.Session.get")
    def test_download_image_failure(
        self, mock_get, service: UnsplashService
    ) -> None:
        mock_get.side_effect = requests.exceptions.RequestException(
            "Download failed"
        )

        with pytest.raises(UnsplashNetworkError):
            service.download_image("https://example.com/image.jpg")

    @patch("requests.Session.get")
    def test_track_download(
        self, mock_get, service: UnsplashService
    ) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        service.track_download(
            "https://api.unsplash.com/photos/photo123/download"
        )
        assert mock_get.called

    @patch("requests.Session.get")
    def test_remaining_requests_property(
        self, mock_get, service: UnsplashService
    ) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "id": "photo123",
                "user": {"name": "T"},
                "description": "",
                "alt_description": "",
                "urls": {"full": ""},
                "links": {"download_location": ""},
            }
        ]
        mock_response.headers = {
            "X-Ratelimit-Remaining": "45",
            "X-Ratelimit-Reset": "0",
        }
        mock_get.return_value = mock_response

        try:
            service.get_random_photo()
        except Exception:
            pass

        assert service.remaining_requests == 45

    def test_close(self, service: UnsplashService) -> None:
        with patch.object(service._session, "close") as mock_close:
            service.close()
            mock_close.assert_called_once()
