"""Tests for yarl-based URL building, specifically IPv6 host with port."""

from typing import Any
from unittest.mock import Mock, patch

import aiohttp
import pytest

from samsungtvws.connection import SamsungTVWSBaseConnection
from samsungtvws.encrypted.remote import SamsungTVEncryptedWSAsyncRemote
from samsungtvws.rest import SamsungTVRest

from .const import (
    ENDPOINT,
    NAME_B64,
    TOKEN,
)

IPV6_HOST = "::1"


@pytest.mark.parametrize(
    ("port", "token", "method", "args", "expected"),
    [
        pytest.param(
            8001,
            None,
            "_format_websocket_url",
            (ENDPOINT,),
            f"ws://[::1]:8001/api/v2/channels/{ENDPOINT}?name={NAME_B64}",
            id="ws",
        ),
        pytest.param(
            8002,
            "tok",
            "_format_websocket_url",
            (ENDPOINT,),
            f"wss://[::1]:8002/api/v2/channels/{ENDPOINT}?name={NAME_B64}&token=tok",
            id="wss-token",
        ),
        pytest.param(
            8001,
            None,
            "_format_rest_url",
            ("device",),
            "http://[::1]:8001/api/v2/device",
            id="http",
        ),
        pytest.param(
            8001,
            None,
            "_format_rest_url",
            ("device", {"t": "123"}),
            "http://[::1]:8001/api/v2/device?t=123",
            id="http-query",
        ),
        pytest.param(
            8002,
            "tok",
            "_format_rest_url",
            ("device",),
            "https://[::1]:8002/api/v2/device",
            id="https",
        ),
    ],
)
def test_base_conn_url_ipv6(
    port: int,
    token: str | None,
    method: str,
    args: tuple[Any, ...],
    expected: str,
) -> None:
    """IPv6 host must be bracketed in all SamsungTVWSBaseConnection URLs."""
    conn = SamsungTVWSBaseConnection(
        IPV6_HOST, endpoint=ENDPOINT, port=port, token=token
    )
    assert getattr(conn, method)(*args) == expected


@pytest.mark.parametrize(
    ("method", "args", "expected"),
    [
        pytest.param(
            "_format_websocket_url",
            ("abc123",),
            "ws://[::1]:8000/socket.io/1/websocket/abc123",
            id="ws",
        ),
        pytest.param(
            "_format_rest_url",
            ("socket.io/1/",),
            "http://[::1]:8000/socket.io/1/",
            id="http",
        ),
        pytest.param(
            "_format_rest_url",
            ("socket.io/1/", {"t": "12345"}),
            "http://[::1]:8000/socket.io/1/?t=12345",
            id="http-query",
        ),
    ],
)
def test_encrypted_url_ipv6(method: str, args: tuple[Any, ...], expected: str) -> None:
    """IPv6 host must be bracketed in all SamsungTVEncryptedWSAsyncRemote URLs."""
    remote = SamsungTVEncryptedWSAsyncRemote(
        IPV6_HOST,
        web_session=Mock(aiohttp.ClientSession),
        token=TOKEN,
        session_id="1",
        port=8000,
    )
    assert getattr(remote, method)(*args) == expected


@pytest.mark.parametrize(
    "host",
    [
        pytest.param("::1", id="unbracketed"),
        pytest.param("[::1]", id="bracketed"),
    ],
)
def test_ipv6_host_with_or_without_brackets(host: str) -> None:
    """An IPv6 host is accepted with or without brackets."""
    conn = SamsungTVWSBaseConnection(host, endpoint=ENDPOINT)
    remote = SamsungTVEncryptedWSAsyncRemote(
        host,
        web_session=Mock(aiohttp.ClientSession),
        token=TOKEN,
        session_id="1",
        port=8000,
    )

    assert conn._format_rest_url("device") == "http://[::1]:8001/api/v2/device"
    assert remote._format_rest_url("socket.io/1/") == "http://[::1]:8000/socket.io/1/"


@pytest.mark.parametrize(
    ("port", "expected_url"),
    [
        pytest.param(
            8001,
            "http://127.0.0.1:8001/api/v2/remoteControl/imeInput/aGk=?token=tok",
            id="http",
        ),
        pytest.param(
            8002,
            "https://127.0.0.1:8002/api/v2/remoteControl/imeInput/aGk=?token=tok",
            id="https",
        ),
    ],
)
def test_rest_ime_input_sends_token_as_query(port: int, expected_url: str) -> None:
    """The IME token must be a query parameter, not part of the path."""
    rest = SamsungTVRest("127.0.0.1", port=port)
    with patch("samsungtvws.rest.requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        assert rest.rest_ime_input("hi", token="tok")
    assert mock_post.call_args.args[0] == expected_url
