"""Tests for remote module."""

from collections.abc import Iterator
from unittest.mock import MagicMock, Mock, patch

import aiohttp
from aiointercept import aiointercept
import pytest
import pytest_asyncio
from websockets.asyncio.client import ClientConnection


@pytest.fixture(autouse=True)
def override_time_sleep():
    """Ignore time sleep in tests."""
    with (
        patch("samsungtvws.connection.time.sleep"),
        patch("samsungtvws.remote.time.sleep"),
    ):
        yield


@pytest.fixture(name="connection")
def get_connection():
    """Open a websocket connection."""
    connection = Mock()
    with patch(
        "samsungtvws.connection.websocket.create_connection"
    ) as connection_class:
        connection_class.return_value = connection
        yield connection


@pytest.fixture(autouse=True)
def override_asyncio_sleep():
    """Ignore asyncio sleep in tests."""
    with patch("samsungtvws.async_connection.asyncio.sleep"):
        yield


@pytest.fixture(name="async_connection")
def get_async_connection():
    """Open a websockets connection."""
    connection = Mock(ClientConnection)

    async def _connect(*args, **kwargs):
        return connection

    with patch("samsungtvws.async_connection.connect", _connect):
        yield connection


@pytest_asyncio.fixture(name="aiointercept_mock")
async def mock_aiointercept():
    async with aiointercept(mock_external_urls=True) as m:
        yield m


@pytest_asyncio.fixture(name="web_session")
async def get_web_session():
    """Create an aiohttp client session closed after the test."""
    async with aiohttp.ClientSession() as session:
        yield session


@pytest.fixture(name="mock_tv_class")
def get_mock_tv_class() -> Iterator[MagicMock]:
    """Patch the SamsungTVWS class instantiated by the CLI."""
    with patch("samsungtvws.cli.main.SamsungTVWS", autospec=True) as tv_class:
        tv_class.return_value.token = None
        yield tv_class


@pytest.fixture(name="mock_tv")
def get_mock_tv(mock_tv_class: MagicMock) -> MagicMock:
    """Return the SamsungTVWS instance used by the CLI."""
    return mock_tv_class.return_value
