"""
SamsungTVWS - Samsung Smart TV WS API wrapper

Copyright (C) 2019 DSR! <xchwarze@gmail.com>

SPDX-License-Identifier: LGPL-3.0
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Sequence
import contextlib
import json
import logging
from types import TracebackType
from typing import (
    Any,
)

from websockets.asyncio.client import ClientConnection, connect
from websockets.exceptions import ConnectionClosed
from websockets.protocol import State

from . import connection, exceptions, helper
from .command import SamsungTVCommand, SamsungTVSleepCommand
from .event import (
    IGNORE_EVENTS_AT_STARTUP,
    MS_CHANNEL_CONNECT_EVENT,
    MS_CHANNEL_UNAUTHORIZED,
)
from .helper import get_ssl_context

_LOGGING = logging.getLogger(__name__)


class SamsungTVWSAsyncConnection(connection.SamsungTVWSBaseConnection):
    connection: ClientConnection | None
    _recv_loop: asyncio.Task[None] | None

    async def __aenter__(self) -> SamsungTVWSAsyncConnection:
        return self

    async def __aexit__(
        self,
        exc_type: type | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.close()

    async def open(self) -> ClientConnection:
        if self.connection:
            # someone else already created a new connection
            return self.connection

        url = self._format_websocket_url(self.endpoint)

        _LOGGING.debug("WS url %s", url)
        connect_kwargs: dict[str, Any] = {}
        if self._is_ssl_connection():
            connect_kwargs["ssl"] = get_ssl_context()
        connection = await connect(url, open_timeout=self.timeout, **connect_kwargs)

        event: str | None = None
        while event is None or event in IGNORE_EVENTS_AT_STARTUP:
            data = await connection.recv()
            response = helper.process_api_response(data)
            event = response.get("event", "*")
            assert event
            self._websocket_event(event, response)

        if event == MS_CHANNEL_UNAUTHORIZED:
            await self.close()
            raise exceptions.UnauthorizedError(response)

        if event != MS_CHANNEL_CONNECT_EVENT:
            # Unexpected event received during connection routine
            await self.close()
            raise exceptions.ConnectionFailure(response)

        self._check_for_token(response)

        self.connection = connection
        return connection

    async def start_listening(
        self, callback: Callable[[str, Any], Awaitable[None] | None] | None = None
    ) -> None:
        """Open, and start listening."""
        if self.connection:
            raise exceptions.ConnectionFailure("Connection already exists")

        self.connection = await self.open()

        self._recv_loop = asyncio.ensure_future(
            self._do_start_listening(callback, self.connection)
        )

    async def _do_start_listening(
        self,
        callback: Callable[[str, Any], Awaitable[None] | None] | None,
        connection: ClientConnection,
    ) -> None:
        """Do start listening."""
        with contextlib.suppress(ConnectionClosed):
            while True:
                data = await connection.recv()
                response = helper.process_api_response(data)
                event = response.get("event", "*")
                self._websocket_event(event, response)
                if callback:
                    awaitable = callback(event, response)
                    if awaitable:
                        await awaitable

    async def close(self) -> None:
        if self.connection:
            await self.connection.close()
            if self._recv_loop:
                await self._recv_loop

        self.connection = None
        _LOGGING.debug("Connection closed.")

    async def send_commands(
        self,
        commands: Sequence[SamsungTVCommand | dict[str, Any]],
        key_press_delay: float | None = None,
    ) -> None:
        if self.connection is None:
            self.connection = await self.open()

        delay = self.key_press_delay if key_press_delay is None else key_press_delay

        for command in commands:
            await self._send_command(self.connection, command, delay)

    async def send_command(
        self,
        command: list[SamsungTVCommand] | SamsungTVCommand | dict[str, Any],
        key_press_delay: float | None = None,
    ) -> None:
        if isinstance(command, list):
            _LOGGING.warning(
                "Using send_command to send multiple commands is deprecated, "
                "please use send_commands."
            )
            await self.send_commands(command, key_press_delay)
            return

        await self.send_commands([command], key_press_delay)

    @staticmethod
    async def _send_command(
        connection: ClientConnection,
        command: SamsungTVCommand | dict[str, Any],
        delay: float,
    ) -> None:
        if isinstance(command, SamsungTVSleepCommand):
            await asyncio.sleep(command.delay)
            return

        if isinstance(command, SamsungTVCommand):
            payload = command.get_payload()
        else:
            payload = json.dumps(command)
        _LOGGING.debug("SamsungTVWS websocket command: %s", payload)
        await connection.send(payload)

        await asyncio.sleep(delay)

    def is_alive(self) -> bool:
        return self.connection is not None and self.connection.state is not State.CLOSED
