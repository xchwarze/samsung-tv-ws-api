import base64
import json
import logging
from typing import Any, Dict, Union

from . import exceptions

_LOGGING = logging.getLogger(__name__)


def serialize_string(string: Union[str, bytes]) -> str:
    if isinstance(string, str):
        string = str.encode(string)

    return base64.b64encode(string).decode("utf-8")


def process_api_response(response: Union[str, bytes]) -> Dict[str, Any]:
    _LOGGING.debug("Processing API response: %s", response)
    try:
        return json.loads(response)  # type:ignore[no-any-return]
    except json.JSONDecodeError:
        print(f"Failed to parse response from TV, {response=}"
        )
