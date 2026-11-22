"""Tests for async_rest module."""

import json

import aiohttp
from aiointercept import aiointercept
import pytest
from yarl import URL

from samsungtvws.async_rest import SamsungTVAsyncRest
from samsungtvws.exceptions import HttpApiError, HttpApiStatusError

from .const import (
    APP_ID,
    REST_APP_STATUS_SAMPLE,
    REST_DEVICE_INFO_SAMPLE,
)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("port", "url"),
    [
        pytest.param(8001, "http://samsungtv.test:8001/api/v2/", id="http"),
        pytest.param(8002, "https://samsungtv.test:8002/api/v2/", id="https"),
    ],
)
async def test_rest_device_info(
    aiointercept_mock: aiointercept,
    web_session: aiohttp.ClientSession,
    port: int,
    url: str,
) -> None:
    """Ensure device info is fetched from the right URL and parsed."""
    aiointercept_mock.get(url, body=REST_DEVICE_INFO_SAMPLE)
    tv = SamsungTVAsyncRest("samsungtv.test", session=web_session, port=port)
    assert await tv.rest_device_info() == json.loads(REST_DEVICE_INFO_SAMPLE)
    aiointercept_mock.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method_name", "http_method"),
    [
        pytest.param("rest_app_status", "GET", id="status"),
        pytest.param("rest_app_run", "POST", id="run"),
        pytest.param("rest_app_close", "DELETE", id="close"),
        pytest.param("rest_app_install", "PUT", id="install"),
    ],
)
async def test_rest_app_request(
    aiointercept_mock: aiointercept,
    web_session: aiohttp.ClientSession,
    method_name: str,
    http_method: str,
) -> None:
    """Ensure each app action uses its HTTP method on the application URL."""
    url = f"http://samsungtv.test:8001/api/v2/applications/{APP_ID}"
    aiointercept_mock.add(url, method=http_method, body=REST_APP_STATUS_SAMPLE)
    tv = SamsungTVAsyncRest("samsungtv.test", session=web_session)
    assert await getattr(tv, method_name)(APP_ID) == json.loads(REST_APP_STATUS_SAMPLE)
    assert list(aiointercept_mock.requests) == [(http_method, URL(url))]


@pytest.mark.asyncio
async def test_rest_unreachable(
    aiointercept_mock: aiointercept, web_session: aiohttp.ClientSession
) -> None:
    """Ensure connection errors are raised as HttpApiError."""
    aiointercept_mock.get("http://samsungtv.test:8001/api/v2/", exception=True)
    tv = SamsungTVAsyncRest("samsungtv.test", session=web_session)
    with pytest.raises(HttpApiError, match="TV unreachable"):
        await tv.rest_device_info()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method_name", "http_method", "path", "args"),
    [
        pytest.param("rest_device_info", "GET", "", (), id="device_info"),
        pytest.param(
            "rest_app_status", "GET", f"applications/{APP_ID}", (APP_ID,), id="status"
        ),
        pytest.param(
            "rest_app_run", "POST", f"applications/{APP_ID}", (APP_ID,), id="run"
        ),
        pytest.param(
            "rest_app_close", "DELETE", f"applications/{APP_ID}", (APP_ID,), id="close"
        ),
        pytest.param(
            "rest_app_install", "PUT", f"applications/{APP_ID}", (APP_ID,), id="install"
        ),
    ],
)
async def test_rest_http_error(
    aiointercept_mock: aiointercept,
    web_session: aiohttp.ClientSession,
    method_name: str,
    http_method: str,
    path: str,
    args: tuple[str, ...],
) -> None:
    """Ensure an HTTP error status raises HttpApiStatusError with the status and body."""
    body = '{"code": 404, "message": "Not found error.", "status": 404}'
    aiointercept_mock.add(
        f"http://samsungtv.test:8001/api/v2/{path}",
        method=http_method,
        status=404,
        body=body,
    )
    tv = SamsungTVAsyncRest("samsungtv.test", session=web_session)
    with pytest.raises(HttpApiStatusError, match="HTTP 404: .*Not found error") as err:
        await getattr(tv, method_name)(*args)
    assert err.value.status == 404
    assert err.value.body == body
