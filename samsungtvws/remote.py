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
import logging
import time
from typing import overload

import requests

from . import art, connection, exceptions, helper, shortcuts

_LOGGING = logging.getLogger(__name__)


class SamsungTVWS(connection.SamsungTVWSConnection):
    _REST_URL_FORMAT = "{protocol}://{host}:{port}/api/v2/{route}"

    def __init__(
        self,
        host,
        token=None,
        token_file=None,
        port=8001,
        timeout=None,
        key_press_delay=1,
        name="SamsungTvRemote",
    ):
        super().__init__(
            host,
            token=token,
            token_file=token_file,
            port=port,
            timeout=timeout,
            key_press_delay=key_press_delay,
            name=name,
        )

    def _format_rest_url(self, route=""):
        params = {
            "protocol": "https" if self._is_ssl_connection() else "http",
            "host": self.host,
            "port": self.port,
            "route": route,
        }

        return self._REST_URL_FORMAT.format(**params)

    def _ws_send(self, command, key_press_delay=None):
        return super().send_command(command, key_press_delay)

    def _rest_request(self, target, method="GET"):
        url = self._format_rest_url(target)
        try:
            if method == "POST":
                return requests.post(url, timeout=self.timeout, verify=False)
            elif method == "PUT":
                return requests.put(url, timeout=self.timeout, verify=False)
            elif method == "DELETE":
                return requests.delete(url, timeout=self.timeout, verify=False)
            else:
                return requests.get(url, timeout=self.timeout, verify=False)
        except requests.ConnectionError:
            raise exceptions.HttpApiError(
                "TV unreachable or feature not supported on this model."
            )

    # endpoint is kept here for compatibility - can be removed in v2
    @overload
    def open(self, endpoint):
        return super().open()

    # required for overloading - can be removed in v2
    def open(self):
        return super().open()

    def send_key(self, key, times=1, key_press_delay=None, cmd="Click"):
        for _ in range(times):
            _LOGGING.debug("Sending key %s", key)
            self._ws_send(
                {
                    "method": "ms.remote.control",
                    "params": {
                        "Cmd": cmd,
                        "DataOfCmd": key,
                        "Option": "false",
                        "TypeOfRemote": "SendRemoteKey",
                    },
                },
                key_press_delay,
            )

    def hold_key(self, key, seconds):
        self.send_key(key, cmd="Press")
        time.sleep(seconds)
        self.send_key(key, cmd="Release")

    def move_cursor(self, x, y, duration=0):
        self._ws_send(
            {
                "method": "ms.remote.control",
                "params": {
                    "Cmd": "Move",
                    "Position": {"x": x, "y": y, "Time": str(duration)},
                    "TypeOfRemote": "ProcessMouseDevice",
                },
            },
            key_press_delay=0,
        )

    def run_app(self, app_id, app_type="DEEP_LINK", meta_tag=""):
        _LOGGING.debug(
            "Sending run app app_id: %s app_type: %s meta_tag: %s",
            app_id,
            app_type,
            meta_tag,
        )
        self._ws_send(
            {
                "method": "ms.channel.emit",
                "params": {
                    "event": "ed.apps.launch",
                    "to": "host",
                    "data": {
                        # action_type: NATIVE_LAUNCH / DEEP_LINK
                        # app_type == 2 ? 'DEEP_LINK' : 'NATIVE_LAUNCH',
                        "action_type": app_type,
                        "appId": app_id,
                        "metaTag": meta_tag,
                    },
                },
            }
        )

    def open_browser(self, url):
        _LOGGING.debug("Opening url in browser %s", url)
        self.run_app("org.tizen.browser", "NATIVE_LAUNCH", url)

    def app_list(self):
        _LOGGING.debug("Get app list")
        self._ws_send(
            {
                "method": "ms.channel.emit",
                "params": {"event": "ed.installedApp.get", "to": "host"},
            }
        )

        response = helper.process_api_response(self.connection.recv())
        if response.get("data"):
            data = response["data"]
            if isinstance(data, dict) and data.get("data"):
                return data["data"]
            return data
        else:
            return response

    def rest_device_info(self):
        _LOGGING.debug("Get device info via rest api")
        response = self._rest_request("")

        return helper.process_api_response(response.text)

    def rest_app_status(self, app_id):
        _LOGGING.debug("Get app %s status via rest api", app_id)
        response = self._rest_request("applications/" + app_id)

        return helper.process_api_response(response.text)

    def rest_app_run(self, app_id):
        _LOGGING.debug("Run app %s via rest api", app_id)
        response = self._rest_request("applications/" + app_id, "POST")

        return helper.process_api_response(response.text)

    def rest_app_close(self, app_id):
        _LOGGING.debug("Close app %s via rest api", app_id)
        response = self._rest_request("applications/" + app_id, "DELETE")

        return helper.process_api_response(response.text)

    def rest_app_install(self, app_id):
        _LOGGING.debug("Install app %s via rest api", app_id)
        response = self._rest_request("applications/" + app_id, "PUT")

        return helper.process_api_response(response.text)

    def shortcuts(self):
        return shortcuts.SamsungTVShortcuts(self)

    def art(self):
        return art.SamsungTVArt(self)
