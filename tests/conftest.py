"""Tests for remote module."""

import asyncio
from unittest.mock import Mock, patch

from aioresponses import aioresponses
import pytest
from websockets.asyncio.client import ClientConnection


@pytest.fixture(autouse=True)
def override_time_sleep():
    """Ignore time sleep in tests."""
    with patch("samsungtvws.connection.time.sleep"), patch(
        "samsungtvws.remote.time.sleep"
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
    sleep_future = asyncio.Future()
    sleep_future.set_result(None)
    with patch("samsungtvws.async_connection.asyncio.sleep", return_value=sleep_future):
        yield


@pytest.fixture(name="async_connection")
def get_async_connection():
    """Open a websockets connection."""
    connection = Mock(ClientConnection)
    with patch(
        "samsungtvws.async_connection.connect", return_value=asyncio.Future()
    ) as connection_class:
        connection_class.return_value.set_result(connection)
        yield connection


@pytest.fixture(name="aioresponse")
def mock_aioresponse():
    with aioresponses() as m:
        yield m
