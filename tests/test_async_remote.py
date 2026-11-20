"""Tests for the async remote module."""

from collections.abc import Callable
from unittest.mock import AsyncMock, Mock, call

import pytest

from samsungtvws.async_remote import SamsungTVWSAsyncRemote
from samsungtvws.exceptions import ConnectionFailure
from samsungtvws.remote import SendRemoteKey

from .const import (
    ED_APPS_LAUNCH_SAMPLE,
    ED_EDENTV_UPDATE_SAMPLE,
    ED_INSTALLED_APP_SAMPLE,
    INSTALLED_APPS,
    MS_CHANNEL_CONNECT_SAMPLE,
    MS_ERROR_SAMPLE,
    MS_REMOTE_TOUCH_DISABLE_SAMPLE,
    MS_REMOTE_TOUCH_ENABLE_SAMPLE,
    MS_VOICEAPP_HIDE_SAMPLE,
)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "events",
    [
        pytest.param([], id="connect-only"),
        pytest.param(
            [MS_VOICEAPP_HIDE_SAMPLE, ED_EDENTV_UPDATE_SAMPLE], id="extra-events"
        ),
        pytest.param(
            [MS_REMOTE_TOUCH_ENABLE_SAMPLE, MS_REMOTE_TOUCH_DISABLE_SAMPLE],
            id="touch-events",
        ),
    ],
)
async def test_connect(
    block_recv_until_close: Callable[..., None], events: list[str]
) -> None:
    """Ensure events sent before ms.channel.connect are ignored."""
    block_recv_until_close(*events, MS_CHANNEL_CONNECT_SAMPLE)
    async with SamsungTVWSAsyncRemote("127.0.0.1") as tv:
        await tv.start_listening()
        assert tv.token == 123456789


@pytest.mark.asyncio
async def test_connection_failure(async_connection: Mock) -> None:
    """Ensure an error event while listening raises ConnectionFailure."""
    async_connection.recv = AsyncMock(return_value=MS_ERROR_SAMPLE)
    async_connection.send = AsyncMock()
    tv = SamsungTVWSAsyncRemote("127.0.0.1")
    with pytest.raises(ConnectionFailure, match="ms.error"):
        await tv.start_listening()


@pytest.mark.asyncio
async def test_send_key(async_connection: Mock) -> None:
    """Ensure a key is sent as a SendRemoteKey click."""
    async_connection.recv = AsyncMock(return_value=MS_CHANNEL_CONNECT_SAMPLE)
    async_connection.send = AsyncMock()
    tv = SamsungTVWSAsyncRemote("127.0.0.1")
    await tv.send_command(SendRemoteKey.click("KEY_POWER"))
    async_connection.send.assert_called_once_with(
        '{"method": "ms.remote.control", "params": {'
        '"Cmd": "Click", '
        '"DataOfCmd": "KEY_POWER", '
        '"Option": "false", '
        '"TypeOfRemote": "SendRemoteKey"'
        "}}"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "events",
    [
        pytest.param([], id="in-order"),
        pytest.param([ED_APPS_LAUNCH_SAMPLE], id="unrelated-event-first"),
    ],
)
async def test_app_list(
    async_connection: Mock,
    block_recv_until_close: Callable[..., None],
    events: list[str],
) -> None:
    """Ensure app_list data is parsed, even after an unrelated event."""
    block_recv_until_close(MS_CHANNEL_CONNECT_SAMPLE, *events, ED_INSTALLED_APP_SAMPLE)
    async_connection.send = AsyncMock()
    async with SamsungTVWSAsyncRemote("127.0.0.1") as tv:
        await tv.start_listening()
        assert await tv.app_list() == INSTALLED_APPS


@pytest.mark.asyncio
async def test_send_hold_key(
    async_connection: Mock, mock_async_sleep: AsyncMock
) -> None:
    """Ensure holding a key presses, waits and releases it."""
    async_connection.recv = AsyncMock(return_value=MS_CHANNEL_CONNECT_SAMPLE)
    async_connection.send = AsyncMock()

    tv = SamsungTVWSAsyncRemote("127.0.0.1")
    await tv.send_command(SendRemoteKey.hold("KEY_POWER", 3))

    assert mock_async_sleep.call_args_list == [call(1), call(3), call(1)]


@pytest.mark.asyncio
async def test_app_list_timeout(async_connection: Mock) -> None:
    """Ensure app_list returns None when the TV does not answer in time."""
    async_connection.recv = AsyncMock(return_value=MS_CHANNEL_CONNECT_SAMPLE)
    async_connection.send = AsyncMock()
    tv = SamsungTVWSAsyncRemote("127.0.0.1", timeout=0.01)
    assert await tv.app_list() is None
    async_connection.send.assert_called_once_with(
        '{"method": "ms.channel.emit", "params": {'
        '"event": "ed.installedApp.get", "to": "host"}}'
    )
