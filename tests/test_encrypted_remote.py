"""Tests for the encrypted remote."""

from __future__ import annotations

from collections.abc import Iterator
import re
from unittest.mock import AsyncMock, Mock, call, patch

import aiohttp
from aiointercept import aiointercept
import pytest
from websockets.asyncio.client import ClientConnection
from websockets.exceptions import ConnectionClosedOK
from websockets.protocol import State

from samsungtvws.encrypted.command import SamsungTVEncryptedCommand
from samsungtvws.encrypted.remote import SamsungTVEncryptedWSAsyncRemote, SendRemoteKey
from samsungtvws.encrypted.session import SamsungTVEncryptedSession
from samsungtvws.exceptions import ConnectionFailure

TOKEN = "037739871315caef138547b03e348b72"
SESSION_ID = "1"
STEP4_URL = re.compile(r"http://samsungtv\.test:8000/socket\.io/1/\?t=\d+$")
WS_URL = "ws://samsungtv.test:8000/socket.io/1/websocket/abcdef"
HANDSHAKE = "1::/com.samsung.companion"


@pytest.fixture(name="ws_connect")
def get_ws_connect() -> Iterator[AsyncMock]:
    """Mock websockets connect as used by the encrypted remote."""
    connection = Mock(ClientConnection)
    connection.state = State.OPEN
    with patch(
        "samsungtvws.encrypted.remote.connect", AsyncMock(return_value=connection)
    ) as connect:
        yield connect


@pytest.fixture(name="encrypted_connection")
def get_encrypted_connection(ws_connect: AsyncMock) -> Mock:
    """Return the websockets connection opened by the encrypted remote."""
    connection: Mock = ws_connect.return_value
    return connection


@pytest.fixture(name="sleep")
def get_sleep() -> Iterator[AsyncMock]:
    """Skip the delay between key presses."""
    with patch("samsungtvws.encrypted.remote.asyncio.sleep") as sleep:
        yield sleep


def _encrypt(command: SamsungTVEncryptedCommand) -> str:
    return SamsungTVEncryptedSession(TOKEN, SESSION_ID).encrypt_command(command)


def _mock_step4(aiointercept_mock: aiointercept) -> None:
    aiointercept_mock.get(STEP4_URL, body="abcdef:60:60:websocket,xhr-polling")


def _remote(
    session: aiohttp.ClientSession,
    *,
    timeout: float | None = None,
    key_press_delay: float = 1,
) -> SamsungTVEncryptedWSAsyncRemote:
    return SamsungTVEncryptedWSAsyncRemote(
        "samsungtv.test",
        web_session=session,
        token=TOKEN,
        session_id=SESSION_ID,
        timeout=timeout,
        key_press_delay=key_press_delay,
    )


def test_click_command() -> None:
    """Test the remote key click command body."""
    command = SendRemoteKey.click("KEY_POWER")

    assert command.as_dict() == {
        "method": "POST",
        "body": {
            "plugin": "RemoteControl",
            "param1": "uuid:12345",
            "param2": "Click",
            "param3": "KEY_POWER",
            "param4": False,
            "api": "SendRemoteKey",
            "version": "1.000",
        },
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("timeout", "open_timeout"),
    [
        pytest.param(5, 5, id="timeout"),
        pytest.param(0, None, id="no-timeout"),
    ],
)
async def test_send_command(
    aiointercept_mock: aiointercept,
    ws_connect: AsyncMock,
    encrypted_connection: Mock,
    sleep: AsyncMock,
    timeout: float,
    open_timeout: float | None,
) -> None:
    """Test a command opens the websocket and is sent encrypted."""
    _mock_step4(aiointercept_mock)
    command = SendRemoteKey.click("KEY_POWER")

    async with aiohttp.ClientSession() as session:
        async with _remote(session, timeout=timeout) as remote:
            assert not remote.is_alive()
            await remote.send_command(command)
            assert remote.is_alive()

    assert not remote.is_alive()
    ws_connect.assert_awaited_once_with(WS_URL, open_timeout=open_timeout)
    assert encrypted_connection.send.await_args_list == [
        call(HANDSHAKE),
        call(_encrypt(command)),
    ]
    encrypted_connection.close.assert_awaited_once()
    sleep.assert_awaited_once_with(1)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("remote_delay", "call_delay", "expected_delay"),
    [
        pytest.param(0.5, None, 0.5, id="remote-delay"),
        pytest.param(0.5, 2, 2, id="call-delay"),
    ],
)
async def test_send_commands_reuses_connection(
    aiointercept_mock: aiointercept,
    ws_connect: AsyncMock,
    encrypted_connection: Mock,
    sleep: AsyncMock,
    remote_delay: float,
    call_delay: float | None,
    expected_delay: float,
) -> None:
    """Test several commands go over one connection with the key press delay."""
    _mock_step4(aiointercept_mock)
    commands = [SendRemoteKey.click("KEY_VOLUP"), SendRemoteKey.click("KEY_VOLDOWN")]

    async with aiohttp.ClientSession() as session:
        remote = _remote(session, key_press_delay=remote_delay)
        await remote.send_commands(commands, call_delay)
        await remote.send_command(commands[0], call_delay)

    ws_connect.assert_awaited_once()
    assert encrypted_connection.send.await_args_list == [
        call(HANDSHAKE),
        call(_encrypt(commands[0])),
        call(_encrypt(commands[1])),
        call(_encrypt(commands[0])),
    ]
    assert sleep.await_args_list == [call(expected_delay)] * 3


@pytest.mark.asyncio
async def test_start_listening(
    aiointercept_mock: aiointercept, encrypted_connection: Mock
) -> None:
    """Test listening reads events until the connection closes."""
    _mock_step4(aiointercept_mock)
    encrypted_connection.recv.side_effect = [
        "1::",
        ConnectionClosedOK(None, None),
    ]

    async with aiohttp.ClientSession() as session:
        remote = _remote(session)
        await remote.start_listening()

        with pytest.raises(ConnectionFailure, match="already exists"):
            await remote.start_listening()

        await remote.close()

    assert encrypted_connection.recv.await_count == 2
    assert encrypted_connection.send.await_args_list == [call(HANDSHAKE)]
    encrypted_connection.close.assert_awaited_once()
    assert not remote.is_alive()


@pytest.mark.asyncio
async def test_is_alive_closed_by_tv(
    aiointercept_mock: aiointercept, encrypted_connection: Mock, sleep: AsyncMock
) -> None:
    """Test the remote is not alive once the TV closed the websocket."""
    _mock_step4(aiointercept_mock)

    async with aiohttp.ClientSession() as session:
        remote = _remote(session)
        await remote.send_command(SendRemoteKey.click("KEY_POWER"))
        encrypted_connection.state = State.CLOSED

        assert not remote.is_alive()
