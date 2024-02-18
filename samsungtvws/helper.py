"""
SamsungTVWS - Samsung Smart TV WS API wrapper

Copyright (C) 2019 DSR! <xchwarze@gmail.com>

SPDX-License-Identifier: LGPL-3.0
"""

import base64
import json
import logging
import ssl
from typing import Any, Dict, Optional, Union

from . import exceptions

_LOGGING = logging.getLogger(__name__)
_SSL_CONTEXT: Optional[ssl.SSLContext] = None


def serialize_string(string: Union[str, bytes]) -> str:
    if isinstance(string, str):
        string = str.encode(string)

    return base64.b64encode(string).decode("utf-8")


def process_api_response(response: Union[str, bytes]) -> Dict[str, Any]:
    _LOGGING.debug("Processing API response: %s", response)
    try:
        return json.loads(response)  # type:ignore[no-any-return]
    except json.JSONDecodeError as err:
        raise exceptions.ResponseError(
            "Failed to parse response from TV. Maybe feature not supported on this model"
        ) from err


def get_ssl_context() -> ssl.SSLContext:
    global _SSL_CONTEXT
    if not _SSL_CONTEXT:
        _SSL_CONTEXT = ssl.SSLContext()
        _SSL_CONTEXT.verify_mode = ssl.CERT_NONE
    return _SSL_CONTEXT
