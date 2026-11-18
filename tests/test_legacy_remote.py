"""Tests for the legacy remote."""

from __future__ import annotations

import asyncio
import base64
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from unittest.mock import AsyncMock, Mock, patch

import pytest
import pytest_asyncio

from samsungtvws.exceptions import ConnectionFailure, ResponseError, UnauthorizedError
from samsungtvws.legacy.remote import (
    RESPONSE_ACCESS_DENIED,
    RESPONSE_ACCESS_GRANTED,
    RESPONSE_CONTROL_ACCEPTED,
    SamsungTVLegacyAsyncRemote,
)

TV_NAME = b"iapp.samsung"
WAITING = b"\x0a\x00\x02\x00\x00\x00"
CANCELLED = b"\x65\x00"


def _frame(response: bytes) -> bytes:
    """Frame a response as the TV sends it."""
    return (
        b"\x00"
        + len(TV_NAME).to_bytes(2, "little")
        + TV_NAME
        + len(response).to_bytes(2, "little")
        + response
    )


def _encode_field(value: bytes) -> bytes:
    """Encode a field as the remote sends it."""
    encoded = base64.b64encode(value)
    return len(encoded).to_bytes(2, "little") + encoded


async def _read_field(reader: asyncio.StreamReader) -> bytes:
    length = int.from_bytes(await reader.readexactly(2), "little")
    return await reader.readexactly(length)


@dataclass
class FakeLegacyTV:
    """Fake legacy TV answering each packet with the next scripted responses."""

    replies: list[list[bytes]]
    hold_open: bool = False
    packets: list[bytes] = field(default_factory=list)
    port: int = 0

    async def handle(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Serve one connection."""
        try:
            while self.replies:
                assert await reader.readexactly(1) == b"\x00"
                assert await _read_field(reader) == b""
                self.packets.append(await _read_field(reader))
                for response in self.replies.pop(0):
                    writer.write(_frame(response))
                await writer.drain()
            if self.hold_open:
                await reader.read()
        except asyncio.IncompleteReadError:
            pass
        finally:
            writer.close()


StartFakeTV = Callable[..., Awaitable[FakeLegacyTV]]


@pytest_asyncio.fixture
async def fake_tv() -> AsyncIterator[StartFakeTV]:
    """Start fake legacy TVs on random ports, answering the scripted replies."""
    servers: list[asyncio.Server] = []

    async def _start(*replies: list[bytes], hold_open: bool = False) -> FakeLegacyTV:
        tv = FakeLegacyTV(list(replies), hold_open)
        server = await asyncio.start_server(tv.handle, "127.0.0.1", 0)
        tv.port = server.sockets[0].getsockname()[1]
        servers.append(server)
        return tv

    yield _start
    for server in servers:
        server.close()
        await server.wait_closed()


@pytest_asyncio.fixture(name="tv_writer")
async def get_tv_writer() -> AsyncIterator[Mock]:
    """Patch open_connection: the TV grants access, and return the stream writer."""
    reader = asyncio.StreamReader()
    reader.feed_data(_frame(RESPONSE_ACCESS_GRANTED))
    writer = Mock(asyncio.StreamWriter)
    writer.is_closing.return_value = False
    with patch(
        "samsungtvws.legacy.remote.asyncio.open_connection",
        AsyncMock(return_value=(reader, writer)),
    ):
        yield writer


def _remote(port: int) -> SamsungTVLegacyAsyncRemote:
    return SamsungTVLegacyAsyncRemote(
        "127.0.0.1",
        port=port,
        name="SamsungTvRemote",
        description="test-host",
        remote_id="remote-id",
        timeout=2,
    )


@pytest.mark.asyncio
async def test_handshake_and_control(fake_tv: StartFakeTV) -> None:
    """Test the handshake waits for authorization and keys are sent."""
    tv = await fake_tv([WAITING, RESPONSE_ACCESS_GRANTED], [RESPONSE_CONTROL_ACCEPTED])

    async with _remote(tv.port) as remote:
        connected = remote.is_connected
        await remote.control("KEY_VOLUP")

    assert connected
    assert not remote.is_connected
    assert tv.packets == [
        b"\x64\x00"
        + _encode_field(b"test-host")
        + _encode_field(b"remote-id")
        + _encode_field(b"SamsungTvRemote"),
        b"\x00\x00\x00" + _encode_field(b"KEY_VOLUP"),
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("replies", "error", "match"),
    [
        pytest.param(
            [RESPONSE_ACCESS_DENIED], UnauthorizedError, "Access denied", id="denied"
        ),
        pytest.param(
            [WAITING, CANCELLED],
            UnauthorizedError,
            "Authorization cancelled",
            id="cancelled",
        ),
        pytest.param(
            [b"\x01\x02"], ResponseError, "Unhandled response: 0102", id="unhandled"
        ),
        pytest.param([], ConnectionFailure, "Connection closed", id="closed"),
        pytest.param([b""], ConnectionFailure, "Connection closed", id="empty"),
    ],
)
async def test_handshake_errors(
    fake_tv: StartFakeTV,
    replies: list[bytes],
    error: type[Exception],
    match: str,
) -> None:
    """Test handshake failures raise and leave the remote disconnected."""
    tv = await fake_tv(replies)
    remote = _remote(tv.port)

    with pytest.raises(error, match=match):
        await remote.open()

    assert not remote.is_connected


@pytest.mark.asyncio
async def test_several_keys(fake_tv: StartFakeTV) -> None:
    """Test several keys are sent over the same connection."""
    tv = await fake_tv(
        [RESPONSE_ACCESS_GRANTED],
        [RESPONSE_CONTROL_ACCEPTED],
        [RESPONSE_CONTROL_ACCEPTED],
    )

    async with _remote(tv.port) as remote:
        await remote.control("KEY_1")
        await remote.control("KEY_2")

    assert tv.packets[1:] == [
        b"\x00\x00\x00" + _encode_field(b"KEY_1"),
        b"\x00\x00\x00" + _encode_field(b"KEY_2"),
    ]


@pytest.mark.asyncio
async def test_control_after_tv_closes(fake_tv: StartFakeTV) -> None:
    """Test a key sent after the TV hangs up raises ConnectionFailure."""
    tv = await fake_tv([RESPONSE_ACCESS_GRANTED], [])
    remote = _remote(tv.port)
    await remote.open()

    with pytest.raises(ConnectionFailure, match="Connection closed"):
        await remote.control("KEY_MUTE")
    assert not remote.is_connected

    with pytest.raises(ConnectionFailure, match="not open"):
        await remote.control("KEY_MUTE")


@pytest.mark.asyncio
async def test_cannot_connect() -> None:
    """Test connecting to a closed port."""
    server = await asyncio.start_server(lambda _r, _w: None, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    server.close()
    await server.wait_closed()

    with pytest.raises(ConnectionFailure, match="Cannot connect"):
        await _remote(port).open()


@pytest.mark.asyncio
async def test_authorization_timeout(fake_tv: StartFakeTV) -> None:
    """Test the wait for the user to allow the remote is bounded by the timeout."""
    tv = await fake_tv([WAITING], hold_open=True)
    remote = SamsungTVLegacyAsyncRemote("127.0.0.1", port=tv.port, timeout=0.1)

    with pytest.raises(ConnectionFailure, match="Timed out"):
        await remote.open()

    assert not remote.is_connected


@pytest.mark.asyncio
async def test_open_when_connected(fake_tv: StartFakeTV) -> None:
    """Test opening an open remote keeps the connection."""
    tv = await fake_tv([RESPONSE_ACCESS_GRANTED], hold_open=True)

    async with _remote(tv.port) as remote:
        await remote.open()

        assert remote.is_connected
    assert len(tv.packets) == 1


@pytest.mark.asyncio
async def test_close_ignores_os_error(tv_writer: Mock) -> None:
    """Test an error while waiting for the socket to close is ignored."""
    tv_writer.wait_closed.side_effect = OSError
    remote = _remote(55000)
    await remote.open()

    await remote.close()

    tv_writer.close.assert_called_once_with()
    assert not remote.is_connected


@pytest.mark.asyncio
async def test_send_os_error(tv_writer: Mock) -> None:
    """Test a write error closes the connection and raises ConnectionFailure."""
    tv_writer.drain.side_effect = BrokenPipeError
    remote = _remote(55000)

    with pytest.raises(ConnectionFailure, match="BrokenPipeError"):
        await remote.open()

    tv_writer.close.assert_called_once_with()
    assert not remote.is_connected


@pytest.mark.asyncio
async def test_control_closed_while_sending(tv_writer: Mock) -> None:
    """Test a key press fails if the connection is closed while it is being sent."""
    remote = _remote(55000)
    await remote.open()
    tv_writer.drain.side_effect = remote.close

    with pytest.raises(ConnectionFailure, match="Connection is not open"):
        await remote.control("KEY_MUTE")
