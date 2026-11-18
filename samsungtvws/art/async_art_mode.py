"""
SamsungTVWS - Samsung Smart TV WS API wrapper

Copyright (C) 2019 DSR! <xchwarze@gmail.com>

SPDX-License-Identifier: LGPL-3.0
"""

from __future__ import annotations

import json
import sys
from time import monotonic
from typing import Any
from uuid import uuid4

from websockets.asyncio.client import ClientConnection

if sys.version_info >= (3, 11):
    from asyncio import timeout
else:
    from async_timeout import timeout

from .. import exceptions, helper
from ..async_connection import SamsungTVWSAsyncConnection
from ..event import D2D_SERVICE_MESSAGE_EVENT, MS_CHANNEL_READY_EVENT
from .art import ART_ENDPOINT, ArtChannelEmitCommand

STATUS_MAX_AGE = 60


class SamsungTVAsyncArtMode(SamsungTVWSAsyncConnection):
    """Track Art Mode on a connected Art channel."""

    def __init__(
        self,
        host: str,
        token: str | None = None,
        port: int = 8001,
        timeout: float | None = None,
        name: str = "SamsungTvRemote",
    ) -> None:
        super().__init__(
            host,
            endpoint=ART_ENDPOINT,
            token=token,
            port=port,
            timeout=timeout,
            key_press_delay=0,
            name=name,
        )
        self._status: bool | None = None
        self._status_updated_at = 0.0
        self._request_id: str | None = None

    async def open(self) -> ClientConnection:
        """Open the Art channel and wait for it to be ready."""
        if self.connection is not None:
            return self.connection
        ready = False
        try:
            async with timeout(self.timeout):
                connection = await super().open()
                response = helper.process_api_response(await connection.recv())
                if response.get("event") != MS_CHANNEL_READY_EVENT:
                    raise exceptions.ConnectionFailure(response)
                ready = True
        finally:
            if not ready:
                await self.close()
        return connection

    def is_alive(self) -> bool:
        """Return whether the Art channel can still receive updates."""
        return super().is_alive() and not (
            self._recv_loop is not None and self._recv_loop.done()
        )

    @property
    def status(self) -> bool | None:
        """Return a recently confirmed Art Mode state on this connection."""
        if self.is_alive() and monotonic() - self._status_updated_at < STATUS_MAX_AGE:
            return self._status
        return None

    async def request_status(self) -> None:
        """Request an update without waiting for a response."""
        self._request_id = str(uuid4())
        await self.send_command(
            ArtChannelEmitCommand.art_app_request(
                {
                    "request": "get_artmode_status",
                    "id": self._request_id,
                    "request_id": self._request_id,
                }
            )
        )

    async def close(self) -> None:
        """Close the Art channel and discard its status."""
        try:
            await super().close()
        finally:
            self.connection = self._recv_loop = None
            self._status = self._request_id = None

    def _websocket_event(self, event: str, response: dict[str, Any]) -> None:
        super()._websocket_event(event, response)
        if event != D2D_SERVICE_MESSAGE_EVENT or not isinstance(
            data := response.get("data"), str
        ):
            return
        try:
            payload = json.loads(data)
        except json.JSONDecodeError:
            return
        if not isinstance(payload, dict):
            return
        match payload.get("event"):
            case "art_mode_changed":
                status = payload.get("status")
            case "artmode_status":
                if (
                    self._request_id is None
                    or payload.get("request_id", payload.get("id")) != self._request_id
                ):
                    return
                status = payload.get("value")
            case "go_to_standby":
                self._status = self._request_id = None
                return
            case _:
                return
        if status in ("on", "off"):
            self._status = status == "on"
            self._status_updated_at = monotonic()
            # A reply sent before a mode change may arrive after the broadcast.
            self._request_id = None
