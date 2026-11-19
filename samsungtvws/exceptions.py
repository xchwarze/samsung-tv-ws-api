"""
SamsungTVWS - Samsung Smart TV WS API wrapper

Copyright (C) 2019 DSR! <xchwarze@gmail.com>

SPDX-License-Identifier: LGPL-3.0
"""


class ConnectionFailure(Exception):
    """Error during connection."""

    pass


class UnauthorizedError(ConnectionFailure):
    """Error from ms.channel.unauthorized event."""

    pass


class ResponseError(Exception):
    """Error in response."""

    pass


class HttpApiError(Exception):
    """Error using HTTP API."""

    pass


class MessageError(Exception):
    """Error from ms.error event."""

    pass


class IPControlError(Exception):
    """Error using the IP control (IP Remote) API."""

    pass


class IPControlConnectionError(IPControlError):
    """Error connecting to the IP control API."""

    pass


class IPControlUnauthorizedError(IPControlError):
    """Access token for the IP control API is missing or rejected."""

    pass


class IPControlResponseError(IPControlError):
    """Error returned by the IP control API."""

    def __init__(self, message: str, code: int | None = None) -> None:
        super().__init__(message)
        self.code = code
