"""
SamsungTVWS - Samsung Smart TV WS API wrapper

Copyright (C) 2019 Xchwarze

    This library is free software; you can redistribute it and/or
    modify it under the terms of the GNU Lesser General Public
    License as published by the Free Software Foundation; either
    version 2.1 of the License, or (at your option) any later version.

    This library is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
    Lesser General Public License for more details.

    You should have received a copy of the GNU Lesser General Public
    License along with this library; if not, write to the Free Software
    Foundation, Inc., 51 Franklin Street, Fifth Floor,
    Boston, MA  02110-1335  USA

"""
import asyncio
import contextlib
import json
import logging
import ssl
from types import TracebackType
from typing import Any, Awaitable, Callable, Dict, List, Optional, Union

from websockets.client import WebSocketClientProtocol, connect
from websockets.exceptions import ConnectionClosed

from . import connection, exceptions, helper
from .command import SamsungTVCommand, SamsungTVSleepCommand
from .event import IGNORE_EVENTS_AT_STARTUP, MS_CHANNEL_CONNECT_EVENT

_LOGGING = logging.getLogger(__name__)


class SamsungTVWSAsyncConnection(connection.SamsungTVWSBaseConnection):

    connection: Optional[WebSocketClientProtocol]
    _recv_loop: Optional["asyncio.Task[None]"]

    async def __aenter__(self) -> "SamsungTVWSAsyncConnection":
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        await self.close()

    async def open(self) -> WebSocketClientProtocol:
        if self.connection:
            # someone else already created a new connection
            return self.connection

        url = self._format_websocket_url(self.endpoint)

        _LOGGING.debug("WS url %s", url)
        connect_kwargs: Dict[str, Any] = {}
        if self._is_ssl_connection():
            ssl_context = ssl.SSLContext()
            ssl_context.verify_mode = ssl.CERT_NONE
            connect_kwargs["ssl"] = ssl_context
        connection = await connect(url, open_timeout=self.timeout, **connect_kwargs)

        event: Optional[str] = None
        while event is None or event in IGNORE_EVENTS_AT_STARTUP:
            data = await connection.recv()
            response = helper.process_api_response(data)
            event = response.get("event", "*")
            assert event
            self._websocket_event(event, response)

        if event != MS_CHANNEL_CONNECT_EVENT:
            await self.close()
            raise exceptions.ConnectionFailure(response)

        self._check_for_token(response)

        self.connection = connection
        return connection

    async def start_listening(
        self, callback: Optional[Callable[[str, Any], Optional[Awaitable[None]]]] = None
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
        callback: Optional[Callable[[str, Any], Optional[Awaitable[None]]]],
        connection: WebSocketClientProtocol,
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

    async def _send_command_sequence(
        self, commands: List[SamsungTVCommand], key_press_delay: float
    ) -> None:
        assert self.connection
        for command in commands:
            if isinstance(command, SamsungTVSleepCommand):
                await asyncio.sleep(command.delay)
            else:
                payload = command.get_payload()
                await self.connection.send(payload)
                await asyncio.sleep(key_press_delay)

    async def send_command(
        self,
        command: Union[List[SamsungTVCommand], SamsungTVCommand, Dict[str, Any]],
        key_press_delay: Optional[float] = None,
    ) -> None:
        if self.connection is None:
            self.connection = await self.open()

        delay = self.key_press_delay if key_press_delay is None else key_press_delay

        if isinstance(command, list):
            await self._send_command_sequence(command, delay)
            return

        if isinstance(command, SamsungTVCommand):
            await self.connection.send(command.get_payload())
        else:
            await self.connection.send(json.dumps(command))

        await asyncio.sleep(delay)

    def is_alive(self) -> bool:
        return self.connection is not None and not self.connection.closed
