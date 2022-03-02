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
import contextlib
import json
import logging
import ssl
import threading
import time
from types import TracebackType
from typing import Any, Callable, Dict, Optional, Union

import websocket

from . import exceptions, helper
from .command import SamsungTVCommand
from .event import MS_CHANNEL_CONNECT, MS_ERROR_EVENT

_LOGGING = logging.getLogger(__name__)


class SamsungTVWSBaseConnection:
    _URL_FORMAT = "ws://{host}:{port}/api/v2/channels/{app}?name={name}"
    _SSL_URL_FORMAT = (
        "wss://{host}:{port}/api/v2/channels/{app}?name={name}&token={token}"
    )
    _REST_URL_FORMAT = "{protocol}://{host}:{port}/api/v2/{route}"

    def __init__(
        self,
        host: str,
        *,
        endpoint: str,
        token: Optional[str] = None,
        token_file: Optional[str] = None,
        port: int = 8001,
        timeout: Optional[float] = None,
        key_press_delay: float = 1,
        name: str = "SamsungTvRemote",
    ):
        self.host = host
        self.token = token
        self.token_file = token_file
        self.port = port
        self.timeout = None if timeout == 0 else timeout
        self.key_press_delay = key_press_delay
        self.name = name
        self.endpoint = endpoint
        self.connection: Optional[Any] = None
        self._recv_loop: Optional[Any] = None

    def _is_ssl_connection(self) -> bool:
        return self.port == 8002

    def _format_websocket_url(self, app: str) -> str:
        params = {
            "host": self.host,
            "port": self.port,
            "app": app,
            "name": helper.serialize_string(self.name),
            "token": self._get_token(),
        }

        if self._is_ssl_connection():
            return self._SSL_URL_FORMAT.format(**params)
        else:
            return self._URL_FORMAT.format(**params)

    def _format_rest_url(self, route: str = "") -> str:
        params = {
            "protocol": "https" if self._is_ssl_connection() else "http",
            "host": self.host,
            "port": self.port,
            "route": route,
        }

        return self._REST_URL_FORMAT.format(**params)

    def _get_token(self) -> Optional[str]:
        if self.token_file is not None:
            try:
                with open(self.token_file) as token_file:
                    return token_file.readline()
            except OSError:
                return None
        else:
            return self.token

    def _set_token(self, token: str) -> None:
        _LOGGING.info("New token %s", token)
        if self.token_file is not None:
            _LOGGING.debug("Save token to file: %s", token)
            with open(self.token_file, "w") as token_file:
                token_file.write(token)
        else:
            self.token = token

    def _check_for_token(self, response: Dict[str, Any]) -> None:
        token = response.get("data", {}).get("token")
        if token:
            _LOGGING.debug("Got token %s", token)
            self._set_token(token)

    def _websocket_event(self, event: str, response: Dict[str, Any]) -> None:
        """Handle websocket event."""
        if event == MS_ERROR_EVENT:
            _LOGGING.warning("SamsungTVWS websocket error message: %s", response)
        else:
            _LOGGING.debug("SamsungTVWS websocket event: %s", response)


class SamsungTVWSConnection(SamsungTVWSBaseConnection):

    connection: Optional[websocket.WebSocket]
    _recv_loop: Optional[threading.Thread]

    def __enter__(self) -> "SamsungTVWSConnection":
        return self

    def __exit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.close()

    def open(self) -> websocket.WebSocket:
        if self.connection:
            # someone else already created a new connection
            return self.connection

        url = self._format_websocket_url(self.endpoint)
        sslopt = {"cert_reqs": ssl.CERT_NONE} if self._is_ssl_connection() else {}

        _LOGGING.debug("WS url %s", url)
        # Only for debug use!
        # websocket.enableTrace(True)
        connection = websocket.create_connection(
            url,
            self.timeout,
            sslopt=sslopt,
            # Use 'connection' for fix websocket-client 0.57 bug
            # header={'Connection': 'Upgrade'}
            connection="Connection: Upgrade",
        )

        response = helper.process_api_response(connection.recv())
        self._check_for_token(response)

        if response["event"] != MS_CHANNEL_CONNECT:
            self.close()
            raise exceptions.ConnectionFailure(response)

        self.connection = connection
        return connection

    def start_listening(
        self, callback: Optional[Callable[[str, Any], None]] = None
    ) -> None:
        """Open, and start listening."""
        if self.connection:
            raise exceptions.ConnectionFailure("Connection already exists")

        self.connection = self.open()

        self._recv_loop = threading.Thread(
            target=self._do_start_listening, args=(callback, self.connection)
        )
        self._recv_loop.start()

    def _do_start_listening(
        self,
        callback: Optional[Callable[[str, Any], None]],
        connection: websocket.WebSocket,
    ) -> None:
        """Do start listening."""
        while True:
            data = connection.recv()
            if not data:
                return
            response = helper.process_api_response(data)
            event = response.get("event", "*")
            self._websocket_event(event, response)
            if callback:
                callback(event, response)

    def close(self) -> None:
        if self.connection:
            self.connection.close()
            if self._recv_loop:
                self._recv_loop.join()
                self._recv_loop = None

        self.connection = None
        _LOGGING.debug("Connection closed.")

    def send_command(
        self,
        command: Union[SamsungTVCommand, Dict[str, Any]],
        key_press_delay: Optional[float] = None,
    ) -> None:
        if self.connection is None:
            self.connection = self.open()

        if isinstance(command, SamsungTVCommand):
            payload = command.get_payload()
        else:
            payload = json.dumps(command)
        self.connection.send(payload)

        delay = self.key_press_delay if key_press_delay is None else key_press_delay
        time.sleep(delay)

    def is_alive(self) -> bool:
        return self.connection is not None and self.connection.connected
