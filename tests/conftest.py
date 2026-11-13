"""Tests for remote module."""

from unittest.mock import Mock, patch

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
