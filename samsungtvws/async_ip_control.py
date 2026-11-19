"""
SamsungTVWS - Samsung Smart TV WS API wrapper

Copyright (C) 2019 DSR! <xchwarze@gmail.com>

SPDX-License-Identifier: LGPL-3.0
"""

from __future__ import annotations

import json
import logging
from typing import Any

import aiohttp

from . import exceptions, helper

_LOGGING = logging.getLogger(__name__)

IP_CONTROL_PORT = 1516

POWER_ON = "powerOn"
POWER_OFF = "powerOff"

ERROR_PARSE = -32700
ERROR_UNKNOWN = -32000
ERROR_NOT_SUPPORTED = -32001
ERROR_FAILED = -32002
ERROR_INVALID_OPERATION = -32003
ERROR_UNAUTHORIZED = -32010

# The TV answers with HTTP 400 without an explicit JSON accept header
_HEADERS = {"Accept": "application/json"}

_DEFAULT_TIMEOUT = 10.0
_PAIRING_TIMEOUT = 60.0


class SamsungTVAsyncIPControl:
    """Client for the local "IP Remote" JSON-RPC service of Samsung TVs.

    The service is disabled by default and must be enabled on the TV
    ("IP Remote" in the expert network settings). It listens on HTTPS port
    1516 with a self-signed certificate and stays reachable in standby.

    The TV keeps a single access token: creating a new one invalidates the
    previous token.
    """

    def __init__(
        self,
        host: str,
        *,
        session: aiohttp.ClientSession,
        port: int = IP_CONTROL_PORT,
        token: str | None = None,
        timeout: float | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.token = token
        self.timeout = _DEFAULT_TIMEOUT if timeout is None else timeout
        self.session = session
        self._request_id = 0

    def _format_url(self) -> str:
        return helper.build_url(
            scheme="https", host=self.host, port=self.port, path="/"
        )

    async def send_request(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        *,
        with_token: bool = True,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """Send a JSON-RPC request and return the content of `result`."""
        payload: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if with_token:
            if not self.token:
                raise exceptions.IPControlUnauthorizedError(
                    "An access token is required, call create_access_token first."
                )
            payload["params"] = {"AccessToken": self.token, **(params or {})}
        elif params:
            payload["params"] = params
        self._request_id += 1
        payload["id"] = self._request_id

        client_timeout = aiohttp.ClientTimeout(
            self.timeout if timeout is None else timeout
        )
        try:
            future = self.session.post(
                self._format_url(),
                json=payload,
                headers=_HEADERS,
                timeout=client_timeout,
                ssl=False,
            )
            async with future as resp:
                status = resp.status
                text = await resp.text()
        except (aiohttp.ClientError, TimeoutError) as err:
            raise exceptions.IPControlConnectionError(
                "TV unreachable or IP Remote not enabled on this model."
            ) from err

        if status != 200:
            raise exceptions.IPControlError(
                f"Unexpected HTTP status {status} for {method}"
            )
        try:
            data = json.loads(text)
        except json.JSONDecodeError as err:
            raise exceptions.IPControlError(
                f"Failed to parse response for {method}"
            ) from err
        if not isinstance(data, dict):
            raise exceptions.IPControlError(f"Unexpected response for {method}")

        # Errors are either a JSON-RPC error object, or, on some firmware,
        # the bare error object without the JSON-RPC envelope.
        error = data.get("error")
        if error is None and "result" not in data and "code" in data:
            error = data
        if error is not None:
            code = error.get("code") if isinstance(error, dict) else None
            message = error.get("message") if isinstance(error, dict) else error
            # A rejected token is answered with a bare "Parse error"
            if code == ERROR_UNAUTHORIZED or (with_token and code == ERROR_PARSE):
                raise exceptions.IPControlUnauthorizedError(
                    f"Access token rejected for {method}: {message}"
                )
            raise exceptions.IPControlResponseError(
                f"{method} failed: {message}", code=code
            )

        result = data.get("result")
        if not isinstance(result, dict):
            raise exceptions.IPControlError(f"Unexpected result for {method}")
        return result

    async def create_access_token(self, timeout: float | None = None) -> str:
        """Pair with the TV, the user must accept the prompt shown on the TV."""
        _LOGGING.debug("Create ip control access token for %s", self.host)
        result = await self.send_request(
            "createAccessToken",
            with_token=False,
            timeout=_PAIRING_TIMEOUT if timeout is None else timeout,
        )
        token = result.get("AccessToken")
        if not isinstance(token, str) or not token:
            raise exceptions.IPControlError("No access token in response")
        self.token = token
        return token

    async def get_tv_states(self) -> dict[str, Any]:
        """Get the states, such as `inputSource`, `volume` and `mute`.

        The TV keeps answering in standby, with the last known values.
        """
        _LOGGING.debug("Get tv states via ip control")
        return await self.send_request("getTVStates")

    async def power_control(self, power: str) -> dict[str, Any]:
        _LOGGING.debug("Set power %s via ip control", power)
        return await self.send_request("powerControl", {"power": power})

    async def power_on(self) -> dict[str, Any]:
        """Wake the TV from standby.

        Some models answer with error code -32002 while still turning on.
        """
        return await self.power_control(POWER_ON)

    async def power_off(self) -> dict[str, Any]:
        return await self.power_control(POWER_OFF)

    async def input_source_control(self, input_source: str) -> dict[str, Any]:
        """Select an input source, for example `HDMI1`."""
        _LOGGING.debug("Set input source %s via ip control", input_source)
        return await self.send_request(
            "inputSourceControl", {"inputSource": input_source}
        )
