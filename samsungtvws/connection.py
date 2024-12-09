"""
SamsungTVWS - Samsung Smart TV WS API wrapper

Copyright (C) 2019 DSR! <xchwarze@gmail.com>

SPDX-License-Identifier: LGPL-3.0
"""

import json
import logging
import ssl
import threading
import time
from types import TracebackType
from typing import Any, Callable, Dict, List, Optional, Union

import websocket

from . import exceptions, helper
from .command import SamsungTVCommand, SamsungTVSleepCommand
from .event import (
    IGNORE_EVENTS_AT_STARTUP,
    MS_CHANNEL_CONNECT_EVENT,
    MS_CHANNEL_UNAUTHORIZED,
    MS_ERROR_EVENT,
)

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
            message = response.get("data", {}).get("message")
            if message == "unrecognized method value : ms.remote.control":
                _LOGGING.error(
                    "Your TV does not seem to support v2 API, please try v1 API"
                )
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

        event: Optional[str] = None
        while event is None or event in IGNORE_EVENTS_AT_STARTUP:
            data = connection.recv()
            response = helper.process_api_response(data)
            event = response.get("event", "*")
            assert event
            self._websocket_event(event, response)

        if event == MS_CHANNEL_UNAUTHORIZED:
            self.close()
            raise exceptions.UnauthorizedError(response)

        if event != MS_CHANNEL_CONNECT_EVENT:
            # Unexpected event received during connection routine
            self.close()
            raise exceptions.ConnectionFailure(response)

        self._check_for_token(response)

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
        command: Union[List[SamsungTVCommand], SamsungTVCommand, Dict[str, Any]],
        key_press_delay: Optional[float] = None,
    ) -> None:
        if self.connection is None:
            self.connection = self.open()

        delay = self.key_press_delay if key_press_delay is None else key_press_delay

        if isinstance(command, list):
            for sub_command in command:
                self._send_command(self.connection, sub_command, delay)
            return

        self._send_command(self.connection, command, delay)

    @staticmethod
    def _send_command(
        connection: websocket.WebSocket,
        command: Union[SamsungTVCommand, Dict[str, Any]],
        delay: float,
    ) -> None:
        if isinstance(command, SamsungTVSleepCommand):
            time.sleep(command.delay)
            return

        if isinstance(command, SamsungTVCommand):
            payload = command.get_payload()
        else:
            payload = json.dumps(command)
        _LOGGING.debug("SamsungTVWS websocket command: %s", payload)
        connection.send(payload)

        time.sleep(delay)

    def is_alive(self) -> bool:
        return self.connection is not None and self.connection.connected
