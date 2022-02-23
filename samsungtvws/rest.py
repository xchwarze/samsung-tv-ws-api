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

import requests

from . import connection, exceptions, helper

_LOGGING = logging.getLogger(__name__)


class SamsungTVRest(connection.SamsungTVWSBaseConnection):
    _REST_URL_FORMAT = "{protocol}://{host}:{port}/api/v2/{route}"

    def __init__(
        self,
        host,
        port=8001,
        timeout=None,
    ):
        super().__init__(
            host,
            port=port,
            timeout=timeout,
        )

    def _format_rest_url(self, route=""):
        params = {
            "protocol": "https" if self._is_ssl_connection() else "http",
            "host": self.host,
            "port": self.port,
            "route": route,
        }

        return self._REST_URL_FORMAT.format(**params)

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
