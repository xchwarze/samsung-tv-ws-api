"""Tests for remote module."""

import asyncio
from collections.abc import Callable, Iterator
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import aiohttp
from aiointercept import aiointercept
import pytest
import pytest_asyncio
from websockets.asyncio.client import ClientConnection
from websockets.exceptions import ConnectionClosed


@pytest.fixture(name="mock_sleep", autouse=True)
def get_mock_sleep() -> Iterator[Mock]:
    """Skip time.sleep, which the library modules share."""
    with patch("samsungtvws.connection.time.sleep") as sleep:
        yield sleep


@pytest.fixture(name="mock_create_connection")
def get_mock_create_connection() -> Iterator[Mock]:
    """Patch websocket.create_connection used by the sync connection."""
    with patch(
        "samsungtvws.connection.websocket.create_connection", return_value=Mock()
    ) as create_connection:
        yield create_connection


@pytest.fixture(name="connection")
def get_connection(mock_create_connection: Mock) -> Mock:
    """Return the websocket connection opened by the sync connection."""
    connection: Mock = mock_create_connection.return_value
    return connection


@pytest.fixture(name="mock_async_sleep", autouse=True)
def get_mock_async_sleep() -> Iterator[AsyncMock]:
    """Skip asyncio.sleep, which the library modules share."""
    with patch("samsungtvws.async_connection.asyncio.sleep") as sleep:
        yield sleep


@pytest.fixture(name="mock_connect")
def get_mock_connect() -> Iterator[AsyncMock]:
    """Patch websockets connect used by the async connection."""
    with patch(
        "samsungtvws.async_connection.connect",
        AsyncMock(return_value=Mock(ClientConnection)),
    ) as connect:
        yield connect


@pytest.fixture(name="async_connection")
def get_async_connection(mock_connect: AsyncMock) -> Mock:
    """Return the websockets connection opened by the async connection."""
    connection: Mock = mock_connect.return_value
    return connection


@pytest.fixture(name="block_recv_until_close")
def get_block_recv_until_close(async_connection: Mock) -> Callable[..., None]:
    """Return a helper making recv return messages, then block until close()."""

    def _setup(*messages: str) -> None:
        closed = asyncio.Event()

        async def _close() -> None:
            closed.set()

        pending = list(messages)

        async def _recv() -> str:
            if pending:
                return pending.pop(0)
            await closed.wait()
            raise ConnectionClosed(None, None)

        async_connection.recv = AsyncMock(side_effect=_recv)
        async_connection.close = AsyncMock(side_effect=_close)

    return _setup


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
