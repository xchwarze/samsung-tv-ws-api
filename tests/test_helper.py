"""Tests for helper module."""

import ssl
from typing import Any

import pytest

from samsungtvws import helper
from samsungtvws.exceptions import ResponseError
from samsungtvws.helper import get_ssl_context, process_api_response

from .const import ED_APPS_LAUNCH_SAMPLE


def test_data_simple() -> None:
    """Ensure simple data can be parsed."""
    parsed_response = process_api_response(ED_APPS_LAUNCH_SAMPLE)
    assert parsed_response == {"data": 200, "event": "ed.apps.launch", "from": "host"}


def test_data_bytes() -> None:
    """Ensure pure JSON bytes can be parsed."""
    parsed_response = process_api_response(ED_APPS_LAUNCH_SAMPLE.encode())
    assert parsed_response == {"data": 200, "event": "ed.apps.launch", "from": "host"}


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        pytest.param(
            b'{"event": "thumb", "data": {"id": 1}}\n\xff\xd8\xff',
            {
                "event": "thumb",
                "data": {"id": 1},
                "binary": b"\xff\xd8\xff",
                "binary_len": 3,
            },
            id="newline-binary-tail",
        ),
        pytest.param(
            b'\xff{"event": "thumb"}\xd8',
            {"event": "thumb", "binary": b"\xd8", "binary_len": 1},
            id="leading-garbage",
        ),
        pytest.param(
            b'{"event": "thumb"}\n',
            {"event": "thumb"},
            id="newline-only-tail",
        ),
    ],
)
def test_data_json_with_tail(data: bytes, expected: dict[str, Any]) -> None:
    """Ensure JSON followed by a binary tail can be parsed."""
    assert process_api_response(data) == expected


@pytest.mark.parametrize(
    ("data", "match"),
    [
        pytest.param("not json", "Failed to parse response from TV", id="invalid-str"),
        pytest.param(b"\xff\xd8", "JSON start not found", id="no-json-start"),
        pytest.param(b'{"event": "thumb"\xff', "JSON end not found", id="no-json-end"),
        pytest.param(
            b"{invalid}\xff", "Failed to parse response from TV", id="invalid-json"
        ),
    ],
)
def test_data_invalid(data: str | bytes, match: str) -> None:
    """Ensure unparsable data raises ResponseError."""
    with pytest.raises(ResponseError, match=match):
        process_api_response(data)


def test_ssl_context(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure the SSL context skips verification and is cached."""
    monkeypatch.setattr(helper, "_SSL_CONTEXT", None)
    context = get_ssl_context()
    assert context.check_hostname is False
    assert context.verify_mode is ssl.CERT_NONE
    assert get_ssl_context() is context
