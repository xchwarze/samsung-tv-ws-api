"""Tests for asynchronous Art Mode status."""

import asyncio
import json
from unittest.mock import AsyncMock, Mock

import pytest
from websockets.exceptions import ConnectionClosedOK
from websockets.protocol import State

from samsungtvws.art.async_art_mode import SamsungTVAsyncArtMode

from .const import MS_CHANNEL_CONNECT_SAMPLE


@pytest.mark.asyncio
async def test_art_mode_updates(
    async_connection: Mock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Track unsolicited changes and expire an unconfirmed status."""
    clock = Mock(return_value=100.0)
    monkeypatch.setattr("samsungtvws.art.async_art_mode.monotonic", clock)
    frames: asyncio.Queue[str | None] = asyncio.Queue()
    frames.put_nowait(MS_CHANNEL_CONNECT_SAMPLE)
    frames.put_nowait('{"event":"ms.channel.ready"}')

    async def receive() -> str:
        frame = await frames.get()
        frames.task_done()
        if frame is None:
            raise ConnectionClosedOK(None, None)
        return frame

    async def close() -> None:
        async_connection.state = State.CLOSED
        frames.put_nowait(None)

    async def send_event(**data: str) -> None:
        frames.put_nowait(
            json.dumps({"event": "d2d_service_message", "data": json.dumps(data)})
        )
        await frames.join()

    async_connection.recv = AsyncMock(side_effect=receive)
    async_connection.close = AsyncMock(side_effect=close)
    async_connection.state = State.OPEN

    async with SamsungTVAsyncArtMode("127.0.0.1") as art:
        await art.start_listening()
        await art.request_status()
        request = json.loads(async_connection.send.call_args.args[0])
        request_id = json.loads(request["params"]["data"])["request_id"]
        await send_event(event="artmode_status", value="on", request_id=request_id)
        assert art.status is True

        await art.request_status()
        request = json.loads(async_connection.send.call_args.args[0])
        request_id = json.loads(request["params"]["data"])["request_id"]
        await send_event(event="art_mode_changed", status="off")
        await send_event(event="artmode_status", value="on", request_id=request_id)
        assert art.status is False

        clock.return_value = 135.0
        await art.request_status()
        assert art.status is False
        clock.return_value = 160.0
        assert art.status is None
        await send_event(event="art_mode_changed", status="on")
        assert art.status is True
        await send_event(event="go_to_standby")
        assert art.status is None

    assert art.status is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "frames", [[], [MS_CHANNEL_CONNECT_SAMPLE]], ids=["connect", "ready"]
)
async def test_art_mode_handshake_timeout(
    async_connection: Mock, frames: list[str]
) -> None:
    """Close the socket if either part of the Art channel handshake times out."""
    async_connection.recv = AsyncMock(side_effect=[*frames, TimeoutError])
    art = SamsungTVAsyncArtMode("127.0.0.1")
    with pytest.raises(TimeoutError):
        await art.start_listening()
    async_connection.close.assert_awaited_once()
    assert art.status is None
