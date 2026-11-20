"""Tests for rest module."""

from unittest.mock import Mock, patch

import pytest
import requests

from samsungtvws.exceptions import HttpApiError
from samsungtvws.rest import SamsungTVRest

from .const import (
    APP_ID,
    REST_APP_STATUS_SAMPLE,
    REST_DEVICE_INFO_SAMPLE,
)

APP_URL = f"http://127.0.0.1:8001/api/v2/applications/{APP_ID}"


@pytest.mark.parametrize(
    ("port", "timeout", "url"),
    [
        pytest.param(8001, 5, "http://127.0.0.1:8001/api/v2/", id="http"),
        pytest.param(8002, None, "https://127.0.0.1:8002/api/v2/", id="https"),
    ],
)
def test_device_info(port: int, timeout: float | None, url: str) -> None:
    """Ensure device info is fetched from the right URL and parsed."""
    rest = SamsungTVRest("127.0.0.1", port=port, timeout=timeout)
    with patch(
        "samsungtvws.rest.requests.get", return_value=Mock(text=REST_DEVICE_INFO_SAMPLE)
    ) as mock_get:
        info = rest.rest_device_info()

    mock_get.assert_called_once_with(url, timeout=timeout, verify=False)
    assert info["device"]["modelName"] == "QE55Q60TAU"


@pytest.mark.parametrize(
    ("method", "http_method"),
    [
        pytest.param("rest_app_status", "get", id="status"),
        pytest.param("rest_app_run", "post", id="run"),
        pytest.param("rest_app_close", "delete", id="close"),
        pytest.param("rest_app_install", "put", id="install"),
    ],
)
def test_app_requests(method: str, http_method: str) -> None:
    """Ensure each app action uses the matching HTTP method."""
    rest = SamsungTVRest("127.0.0.1")
    with patch(
        f"samsungtvws.rest.requests.{http_method}",
        return_value=Mock(text=REST_APP_STATUS_SAMPLE),
    ) as mock_request:
        result = getattr(rest, method)(APP_ID)

    mock_request.assert_called_once_with(APP_URL, timeout=None, verify=False)
    assert result == {
        "id": APP_ID,
        "name": "YouTube",
        "running": True,
        "version": "1.0.0",
        "visible": True,
    }


def test_request_connection_error() -> None:
    """Ensure an unreachable TV raises HttpApiError."""
    rest = SamsungTVRest("127.0.0.1")
    with (
        patch(
            "samsungtvws.rest.requests.get",
            side_effect=requests.ConnectionError,
        ),
        pytest.raises(HttpApiError, match="TV unreachable"),
    ):
        rest.rest_device_info()


@pytest.mark.parametrize(
    ("status_code", "expected"),
    [
        pytest.param(200, True, id="ok"),
        pytest.param(401, False, id="rejected"),
    ],
)
def test_ime_input(status_code: int, expected: bool) -> None:
    """Ensure IME input posts the encoded text with the token."""
    rest = SamsungTVRest("127.0.0.1", port=8002)
    with patch(
        "samsungtvws.rest.requests.post", return_value=Mock(status_code=status_code)
    ) as mock_post:
        assert rest.rest_ime_input("pässword", token="abc") is expected

    mock_post.assert_called_once_with(
        "https://127.0.0.1:8002/api/v2/remoteControl/imeInput/cMOkc3N3b3Jk?token=abc",
        timeout=None,
        verify=False,
    )


def test_ime_input_empty_text() -> None:
    """Ensure empty text is not sent."""
    rest = SamsungTVRest("127.0.0.1")
    with patch("samsungtvws.rest.requests.post") as mock_post:
        assert rest.rest_ime_input("", token="abc") is False

    mock_post.assert_not_called()


@pytest.mark.parametrize(
    "token",
    [pytest.param(None, id="none"), pytest.param("", id="empty")],
)
def test_ime_input_without_token(token: str | None) -> None:
    """Ensure IME input requires a token."""
    rest = SamsungTVRest("127.0.0.1")
    with (
        patch("samsungtvws.rest.requests.post") as mock_post,
        pytest.raises(ValueError, match="requires a valid security token"),
    ):
        rest.rest_ime_input("secret", token=token)

    mock_post.assert_not_called()


@pytest.mark.parametrize(
    ("method", "http_method"),
    [
        pytest.param("rest_device_info", "get", id="device_info"),
        pytest.param("rest_app_status", "get", id="status"),
        pytest.param("rest_app_run", "post", id="run"),
        pytest.param("rest_app_close", "delete", id="close"),
        pytest.param("rest_app_install", "put", id="install"),
    ],
)
def test_request_http_error(method: str, http_method: str) -> None:
    """Ensure an HTTP error status raises HttpApiError with the status and body."""
    rest = SamsungTVRest("127.0.0.1")
    body = '{"code": 404, "message": "Not found error.", "status": 404}'
    args = () if method == "rest_device_info" else (APP_ID,)
    with (
        patch(
            f"samsungtvws.rest.requests.{http_method}",
            return_value=Mock(ok=False, status_code=404, text=body),
        ),
        pytest.raises(HttpApiError, match="HTTP 404: .*Not found error"),
    ):
        getattr(rest, method)(*args)
