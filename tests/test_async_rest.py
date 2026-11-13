"""Tests for async_rest module."""

import json

import aiohttp
from aiointercept import aiointercept
import pytest
from yarl import URL

from samsungtvws.async_rest import SamsungTVAsyncRest
from samsungtvws.exceptions import HttpApiError

with open("tests/fixtures/async_rest_device_info.json") as file:
    DEVICE_INFO_SAMPLE = file.read()
with open("tests/fixtures/async_rest_app_status.json") as file:
    APP_STATUS_SAMPLE = file.read()

APP_ID = "111299001912"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("port", "url"),
    [
        pytest.param(8001, "http://samsungtv.test:8001/api/v2/", id="http"),
        pytest.param(8002, "https://samsungtv.test:8002/api/v2/", id="https"),
    ],
)
async def test_rest_device_info(
    aiointercept_mock: aiointercept, port: int, url: str
) -> None:
    """Ensure device info is fetched from the right URL and parsed."""
    aiointercept_mock.get(url, body=DEVICE_INFO_SAMPLE)
    async with aiohttp.ClientSession() as session:
        tv = SamsungTVAsyncRest("samsungtv.test", session=session, port=port)
        assert await tv.rest_device_info() == json.loads(DEVICE_INFO_SAMPLE)
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
    aiointercept_mock: aiointercept, method_name: str, http_method: str
) -> None:
    """Ensure each app action uses its HTTP method on the application URL."""
    url = f"http://samsungtv.test:8001/api/v2/applications/{APP_ID}"
    aiointercept_mock.add(url, method=http_method, body=APP_STATUS_SAMPLE)
    async with aiohttp.ClientSession() as session:
        tv = SamsungTVAsyncRest("samsungtv.test", session=session)
        assert await getattr(tv, method_name)(APP_ID) == json.loads(APP_STATUS_SAMPLE)
    assert list(aiointercept_mock.requests) == [(http_method, URL(url))]


@pytest.mark.asyncio
async def test_rest_unreachable(aiointercept_mock: aiointercept) -> None:
    """Ensure connection errors are raised as HttpApiError."""
    aiointercept_mock.get("http://samsungtv.test:8001/api/v2/", exception=True)
    async with aiohttp.ClientSession() as session:
        tv = SamsungTVAsyncRest("samsungtv.test", session=session)
        with pytest.raises(HttpApiError):
            await tv.rest_device_info()
