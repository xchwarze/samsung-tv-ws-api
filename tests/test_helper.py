"""Tests for helper module."""
from samsungtvws.helper import process_api_response


def test_data_simple() -> None:
    """Ensure simple data can be parsed."""
    data = '{"data": 200, "event": "ed.apps.launch", "from": "host"}'

    parsed_response = process_api_response(data)
    assert parsed_response == {"data": 200, "event": "ed.apps.launch", "from": "host"}
