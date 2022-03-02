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
from asyncio import Task, ensure_future, sleep
import contextlib
import json
import logging
import ssl
from types import TracebackType
from typing import Any, Awaitable, Callable, Dict, Optional, Union

from websockets.client import WebSocketClientProtocol, connect
from websockets.exceptions import ConnectionClosed

from . import connection, exceptions, helper
from .command import SamsungTVCommand
from .event import MS_CHANNEL_CONNECT

_LOGGING = logging.getLogger(__name__)


class SamsungTVWSAsyncConnection(connection.SamsungTVWSBaseConnection):

    connection: Optional[WebSocketClientProtocol]
    _recv_loop: Optional[Task[None]]

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

        ssl_context = ssl.SSLContext()
        ssl_context.verify_mode = ssl.CERT_NONE
        url = self._format_websocket_url(self.endpoint)

        _LOGGING.debug("WS url %s", url)
        connection = await connect(url, open_timeout=self.timeout, ssl=ssl_context)

        response = helper.process_api_response(await connection.recv())
        self._check_for_token(response)

        if response["event"] != MS_CHANNEL_CONNECT:
            await self.close()
            raise exceptions.ConnectionFailure(response)

        self.connection = connection
        return connection

    async def start_listening(
        self, callback: Optional[Callable[[str, Any], Optional[Awaitable[None]]]] = None
    ) -> None:
        """Open, and start listening."""
        if self.connection:
            raise exceptions.ConnectionFailure("Connection already exists")

        self.connection = await self.open()

        self._recv_loop = ensure_future(
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

    async def send_command(
        self,
        command: Union[SamsungTVCommand, Dict[str, Any]],
        key_press_delay: Optional[float] = None,
    ) -> None:
        if self.connection is None:
            self.connection = await self.open()

        if isinstance(command, SamsungTVCommand):
            payload = command.get_payload()
        else:
            payload = json.dumps(command)
        await self.connection.send(payload)

        delay = self.key_press_delay if key_press_delay is None else key_press_delay
        await sleep(delay)

    def is_alive(self) -> bool:
        return self.connection is not None and not self.connection.closed
