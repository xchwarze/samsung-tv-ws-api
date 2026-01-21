"""
SamsungTVWS - Samsung Smart TV WS API wrapper

Copyright (C) 2019 DSR! <xchwarze@gmail.com>

SPDX-License-Identifier: LGPL-3.0
"""

import base64
import json
import logging
import random
import ssl
from typing import Any, Optional, Union, cast

from . import exceptions

_LOGGING = logging.getLogger(__name__)
_SSL_CONTEXT: Optional[ssl.SSLContext] = None


def serialize_string(string: Union[str, bytes]) -> str:
    if isinstance(string, str):
        string = str.encode(string)

    return base64.b64encode(string).decode("utf-8")


def _split_json_and_tail(buf: bytes) -> tuple[bytes, bytes]:
    """Split WS bytes payload into (json_bytes, tail_bytes)."""
    start = buf.find(b"{")
    if start < 0:
        raise exceptions.ResponseError("Failed to parse response: JSON start not found")

    depth = 0
    end: Optional[int] = None
    for i in range(start, len(buf)):
        b = buf[i]
        if b == 0x7B:  # {
            depth += 1
        elif b == 0x7D:  # }
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    if end is None:
        raise exceptions.ResponseError("Failed to parse response: JSON end not found")

    json_bytes = buf[start:end]
    tail = buf[end:]
    if tail.startswith(b"\n"):
        tail = tail[1:]
    return json_bytes, tail


def process_api_response(response: Union[str, bytes]) -> dict[str, Any]:
    _LOGGING.debug("Processing API response: %s", response)
    try:
        if isinstance(response, str):
            return cast(dict[str, Any], json.loads(response))

        # in old ART api
        # bytes: could be pure JSON or JSON + binary tail
        try:
            return cast(dict[str, Any], json.loads(response.decode("utf-8")))
        except (UnicodeDecodeError, json.JSONDecodeError):
            json_bytes, tail = _split_json_and_tail(response)
            frame = json.loads(json_bytes.decode("utf-8"))

            # Attach binary tail (e.g., thumbnail JPEG)
            if tail:
                frame["binary"] = tail
                frame["binary_len"] = len(tail)

            return cast(dict[str, Any], frame)

    except (UnicodeDecodeError, json.JSONDecodeError) as err:
        raise exceptions.ResponseError(
            "Failed to parse response from TV. Maybe feature not supported on this model"
        ) from err


def get_ssl_context() -> ssl.SSLContext:
    global _SSL_CONTEXT
    if not _SSL_CONTEXT:
        _SSL_CONTEXT = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        _SSL_CONTEXT.check_hostname = False
        _SSL_CONTEXT.verify_mode = ssl.CERT_NONE
    return _SSL_CONTEXT


def generate_connection_id() -> int:
    """Return a per-connection id used by the D2D socket handshake."""
    return random.randrange(4 * 1024 * 1024 * 1024)
