"""Tests for async_connection module."""

import asyncio
from unittest.mock import AsyncMock, Mock, call, patch

import pytest
from websockets.exceptions import ConnectionClosed
from websockets.protocol import State

from samsungtvws.async_connection import SamsungTVWSAsyncConnection
from samsungtvws.command import SamsungTVCommand, SamsungTVSleepCommand
from samsungtvws.exceptions import ConnectionFailure, UnauthorizedError

from .const import (
    ED_APPS_LAUNCH_SAMPLE,
    MS_CHANNEL_CONNECT_SAMPLE,
    MS_CHANNEL_READY_SAMPLE,
)

with open("tests/fixtures/async_connection_ms_channel_unauthorized.json") as file:
    MS_CHANNEL_UNAUTHORIZED_SAMPLE = file.read()

ENDPOINT = "samsung.remote.control"


def _create_tv(port: int = 8001) -> SamsungTVWSAsyncConnection:
    return SamsungTVWSAsyncConnection("127.0.0.1", endpoint=ENDPOINT, port=port)


def _block_recv_until_close(async_connection: Mock, *messages: str) -> None:
    """Return messages, then block recv until close() is called."""
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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("port", "url", "ssl"),
    [
        pytest.param(
            8001,
            "ws://127.0.0.1:8001/api/v2/channels/samsung.remote.control"
            "?name=U2Ftc3VuZ1R2UmVtb3Rl",
            False,
            id="ws",
        ),
        pytest.param(
            8002,
            "wss://127.0.0.1:8002/api/v2/channels/samsung.remote.control"
            "?name=U2Ftc3VuZ1R2UmVtb3Rl",
            True,
            id="wss",
        ),
    ],
)
async def test_open(port: int, url: str, ssl: bool) -> None:
    """Ensure open connects to the right URL, with SSL context on port 8002."""
    connection = Mock()
    connection.recv = AsyncMock(return_value=MS_CHANNEL_CONNECT_SAMPLE)
    connect = AsyncMock(return_value=connection)
    tv = _create_tv(port)
    with patch("samsungtvws.async_connection.connect", connect):
        assert await tv.open() is connection
    assert connect.call_args.args == (url,)
    assert ("ssl" in connect.call_args.kwargs) is ssl
    assert tv.token == 123456789


@pytest.mark.asyncio
async def test_open_reuses_existing_connection(async_connection: Mock) -> None:
    """Ensure open returns the existing connection without reconnecting."""
    async_connection.recv = AsyncMock(return_value=MS_CHANNEL_CONNECT_SAMPLE)
    tv = _create_tv()
    tv.connection = await tv.open()
    assert await tv.open() is async_connection
    async_connection.recv.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("sample", "exception"),
    [
        pytest.param(
            MS_CHANNEL_UNAUTHORIZED_SAMPLE, UnauthorizedError, id="unauthorized"
        ),
        pytest.param(MS_CHANNEL_READY_SAMPLE, ConnectionFailure, id="unexpected"),
    ],
)
async def test_open_failure(
    async_connection: Mock, sample: str, exception: type[Exception]
) -> None:
    """Ensure an unexpected first event raises and leaves no connection."""
    async_connection.recv = AsyncMock(return_value=sample)
    tv = _create_tv()
    with pytest.raises(exception):
        await tv.open()
    assert tv.connection is None
    assert tv.is_alive() is False


@pytest.mark.asyncio
async def test_start_listening_already_connected(async_connection: Mock) -> None:
    """Ensure start_listening refuses to open a second connection."""
    tv = _create_tv()
    tv.connection = async_connection
    with pytest.raises(ConnectionFailure, match="Connection already exists"):
        await tv.start_listening()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "callback_class",
    [
        pytest.param(Mock, id="sync"),
        pytest.param(AsyncMock, id="async"),
    ],
)
async def test_start_listening_callback(
    async_connection: Mock, callback_class: type[Mock]
) -> None:
    """Ensure received events are passed to sync and async callbacks."""
    callback = callback_class(return_value=None)
    _block_recv_until_close(
        async_connection, MS_CHANNEL_CONNECT_SAMPLE, ED_APPS_LAUNCH_SAMPLE
    )
    async with _create_tv() as tv:
        await tv.start_listening(callback)
        await asyncio.sleep(0)
        assert tv.is_alive() is True
    callback.assert_called_once_with(
        "ed.apps.launch",
        {"data": 200, "event": "ed.apps.launch", "from": "host"},
    )
    async_connection.close.assert_awaited_once()
    assert tv.connection is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("state", "alive"),
    [
        pytest.param(State.OPEN, True, id="open"),
        pytest.param(State.CLOSING, True, id="closing"),
        pytest.param(State.CLOSED, False, id="closed"),
    ],
)
async def test_is_alive(async_connection: Mock, state: State, alive: bool) -> None:
    """Ensure is_alive reflects the websocket state."""
    tv = _create_tv()
    tv.connection = async_connection
    async_connection.state = state
    assert tv.is_alive() is alive


@pytest.mark.asyncio
async def test_send_commands(async_connection: Mock) -> None:
    """Ensure commands, raw dicts and sleep commands are sent in order."""
    async_connection.recv = AsyncMock(return_value=MS_CHANNEL_CONNECT_SAMPLE)
    async_connection.send = AsyncMock()
    tv = _create_tv()
    with patch(
        "samsungtvws.async_connection.asyncio.sleep", new=AsyncMock()
    ) as patch_sleep:
        await tv.send_commands(
            [
                SamsungTVCommand("ms.test", {"key": "value"}),
                SamsungTVSleepCommand(5),
                {"method": "ms.raw", "params": {}},
            ],
            key_press_delay=0.5,
        )
    assert async_connection.send.await_args_list == [
        call('{"method": "ms.test", "params": {"key": "value"}}'),
        call('{"method": "ms.raw", "params": {}}'),
    ]
    assert patch_sleep.await_args_list == [call(0.5), call(5), call(0.5)]


@pytest.mark.asyncio
async def test_send_command_list_deprecated(
    async_connection: Mock, caplog: pytest.LogCaptureFixture
) -> None:
    """Ensure send_command still accepts a list but warns it is deprecated."""
    async_connection.recv = AsyncMock(return_value=MS_CHANNEL_CONNECT_SAMPLE)
    async_connection.send = AsyncMock()
    tv = _create_tv()
    await tv.send_command(
        [SamsungTVCommand("ms.one", {}), SamsungTVCommand("ms.two", {})]
    )
    assert async_connection.send.await_args_list == [
        call('{"method": "ms.one", "params": {}}'),
        call('{"method": "ms.two", "params": {}}'),
    ]
    assert "please use send_commands" in caplog.text


@pytest.mark.asyncio
async def test_send_command(async_connection: Mock) -> None:
    """Ensure send_command sends a single command."""
    async_connection.recv = AsyncMock(return_value=MS_CHANNEL_CONNECT_SAMPLE)
    async_connection.send = AsyncMock()
    tv = _create_tv()
    await tv.send_command(SamsungTVCommand("ms.one", {}))
    async_connection.send.assert_awaited_once_with('{"method": "ms.one", "params": {}}')
