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
