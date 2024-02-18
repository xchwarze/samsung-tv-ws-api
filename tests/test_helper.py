"""Tests for helper module."""

from samsungtvws.helper import process_api_response

from .const import ED_APPS_LAUNCH_SAMPLE


def test_data_simple() -> None:
    """Ensure simple data can be parsed."""
    parsed_response = process_api_response(ED_APPS_LAUNCH_SAMPLE)
    assert parsed_response == {"data": 200, "event": "ed.apps.launch", "from": "host"}
