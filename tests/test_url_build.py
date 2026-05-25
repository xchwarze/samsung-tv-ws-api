"""Tests for yarl-based URL building, specifically IPv6 host with port."""

from typing import Optional
from unittest.mock import Mock

import aiohttp
import pytest

from samsungtvws.connection import SamsungTVWSBaseConnection
from samsungtvws.encrypted.remote import SamsungTVEncryptedWSAsyncRemote

IPV6_HOST = "::1"


# ---------------------------------------------------------------------------
# SamsungTVWSBaseConnection
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "port, token, method, args, expected_prefix, extra_in",
    [
        (8001, None, "_format_websocket_url", ("samsung.remote.control",), "ws://[::1]:8001/", None),
        (8002, "tok", "_format_websocket_url", ("samsung.remote.control",), "wss://[::1]:8002/", "token=tok"),
        (8001, None, "_format_rest_url", ("device",), "http://[::1]:8001/", None),
        (8002, "tok", "_format_rest_url", ("device",), "https://[::1]:8002/", None),
    ],
)
def test_base_conn_url_ipv6(
    port: int,
    token: Optional[str],
    method: str,
    args: tuple,
    expected_prefix: str,
    extra_in: Optional[str],
) -> None:
    """IPv6 host must be bracketed in all SamsungTVWSBaseConnection URLs."""
    conn = SamsungTVWSBaseConnection(
        IPV6_HOST, endpoint="samsung.remote.control", port=port, token=token
    )
    url = getattr(conn, method)(*args)
    assert url.startswith(expected_prefix)
    assert "[::1]" in url
    if extra_in is not None:
        assert extra_in in url


# ---------------------------------------------------------------------------
# SamsungTVEncryptedWSAsyncRemote
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "method, args, expected_prefix, extra_in",
    [
        ("_format_websocket_url", ("abc123",), "ws://[::1]:8000/", None),
        ("_format_rest_url", ("socket.io/1/",), "http://[::1]:8000/", None),
        ("_format_rest_url", ("socket.io/1/?t=12345",), "http://[::1]:8000/", "t=12345"),
    ],
)
def test_encrypted_url_ipv6(
    method: str,
    args: tuple,
    expected_prefix: str,
    extra_in: Optional[str],
) -> None:
    """IPv6 host must be bracketed in all SamsungTVEncryptedWSAsyncRemote URLs."""
    remote = SamsungTVEncryptedWSAsyncRemote(
        IPV6_HOST,
        web_session=Mock(aiohttp.ClientSession),
        token="037739871315caef138547b03e348b72",
        session_id="1",
        port=8000,
    )
    url = getattr(remote, method)(*args)
    assert url.startswith(expected_prefix)
    assert "[::1]" in url
    if extra_in is not None:
        assert extra_in in url
