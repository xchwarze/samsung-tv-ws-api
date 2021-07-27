import base64
import json
import logging
from . import exceptions

_LOGGING = logging.getLogger(__name__)


def serialize_string(string):
    if isinstance(string, str):
        string = str.encode(string)

    return base64.b64encode(string).decode('utf-8')


def process_api_response(response):
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        _LOGGING.debug('Failed to parse response from TV. response text: %s', response)
        raise exceptions.ResponseError('Failed to parse response from TV. Maybe feature not supported on this model')
