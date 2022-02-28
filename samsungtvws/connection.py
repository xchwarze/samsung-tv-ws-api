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
import json
import logging
import ssl
import time

import websocket

from . import exceptions, helper
from .command import SamsungTVCommand

_LOGGING = logging.getLogger(__name__)


class SamsungTVWSBaseConnection:
    _URL_FORMAT = "ws://{host}:{port}/api/v2/channels/{app}?name={name}"
    _SSL_URL_FORMAT = (
        "wss://{host}:{port}/api/v2/channels/{app}?name={name}&token={token}"
    )
    _REST_URL_FORMAT = "{protocol}://{host}:{port}/api/v2/{route}"

    def __init__(
        self,
        host,
        *,
        endpoint,
        token=None,
        token_file=None,
        port=8001,
        timeout=None,
        key_press_delay=1,
        name="SamsungTvRemote",
    ):
        self.host = host
        self.token = token
        self.token_file = token_file
        self.port = port
        self.timeout = None if timeout == 0 else timeout
        self.key_press_delay = key_press_delay
        self.name = name
        self.endpoint = endpoint
        self.connection = None

    def _is_ssl_connection(self):
        return self.port == 8002

    def _format_websocket_url(self, app):
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

    def _format_rest_url(self, route=""):
        params = {
            "protocol": "https" if self._is_ssl_connection() else "http",
            "host": self.host,
            "port": self.port,
            "route": route,
        }

        return self._REST_URL_FORMAT.format(**params)

    def _get_token(self):
        if self.token_file is not None:
            try:
                with open(self.token_file) as token_file:
                    return token_file.readline()
            except:
                return ""
        else:
            return self.token

    def _set_token(self, token):
        _LOGGING.info("New token %s", token)
        if self.token_file is not None:
            _LOGGING.debug("Save token to file: %s", token)
            with open(self.token_file, "w") as token_file:
                token_file.write(token)
        else:
            self.token = token

    def _check_for_token(self, response):
        if response.get("data") and response["data"].get("token"):
            token = response["data"].get("token")
            _LOGGING.debug("Got token %s", token)
            self._set_token(token)


class SamsungTVWSConnection(SamsungTVWSBaseConnection):
    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def open(self):
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

        if response["event"] != "ms.channel.connect":
            self.close()
            raise exceptions.ConnectionFailure(response)

        return connection

    def close(self):
        if self.connection:
            self.connection.close()

        self.connection = None
        _LOGGING.debug("Connection closed.")

    def send_command(self, command, key_press_delay=None):
        if self.connection is None:
            self.connection = self.open()

        if isinstance(command, SamsungTVCommand):
            payload = command.get_payload()
        else:
            payload = json.dumps(command)
        self.connection.send(payload)

        delay = self.key_press_delay if key_press_delay is None else key_press_delay
        time.sleep(delay)

    def is_alive(self):
        return self.connection and self.connection.connected
