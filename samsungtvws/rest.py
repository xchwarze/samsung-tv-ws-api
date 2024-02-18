"""
SamsungTVWS - Samsung Smart TV WS API wrapper

Copyright (C) 2019 DSR! <xchwarze@gmail.com>

SPDX-License-Identifier: LGPL-3.0
"""

import logging
from typing import Any, Dict, Optional

import requests

from . import connection, exceptions, helper

_LOGGING = logging.getLogger(__name__)


class SamsungTVRest(connection.SamsungTVWSBaseConnection):
    def __init__(
        self,
        host: str,
        port: int = 8001,
        timeout: Optional[float] = None,
    ) -> None:
        super().__init__(
            host,
            endpoint="",
            port=port,
            timeout=timeout,
        )

    def _rest_request(self, target: str, method: str = "GET") -> Dict[str, Any]:
        url = self._format_rest_url(target)
        try:
            if method == "POST":
                response = requests.post(url, timeout=self.timeout, verify=False)
            elif method == "PUT":
                response = requests.put(url, timeout=self.timeout, verify=False)
            elif method == "DELETE":
                response = requests.delete(url, timeout=self.timeout, verify=False)
            else:
                response = requests.get(url, timeout=self.timeout, verify=False)
            return helper.process_api_response(response.text)
        except requests.ConnectionError as err:
            raise exceptions.HttpApiError(
                "TV unreachable or feature not supported on this model."
            ) from err

    def rest_device_info(self) -> Dict[str, Any]:
        _LOGGING.debug("Get device info via rest api")
        return self._rest_request("")

    def rest_app_status(self, app_id: str) -> Dict[str, Any]:
        _LOGGING.debug("Get app %s status via rest api", app_id)
        return self._rest_request("applications/" + app_id)

    def rest_app_run(self, app_id: str) -> Dict[str, Any]:
        _LOGGING.debug("Run app %s via rest api", app_id)
        return self._rest_request("applications/" + app_id, "POST")

    def rest_app_close(self, app_id: str) -> Dict[str, Any]:
        _LOGGING.debug("Close app %s via rest api", app_id)
        return self._rest_request("applications/" + app_id, "DELETE")

    def rest_app_install(self, app_id: str) -> Dict[str, Any]:
        _LOGGING.debug("Install app %s via rest api", app_id)
        return self._rest_request("applications/" + app_id, "PUT")
