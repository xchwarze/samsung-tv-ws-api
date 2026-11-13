"""Tests for the REST API wrappers."""

from __future__ import annotations

from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import threading

import aiohttp
import pytest

from samsungtvws.async_rest import SamsungTVAsyncRest
from samsungtvws.exceptions import HttpApiError
from samsungtvws.rest import SamsungTVRest

_NOT_FOUND: dict[str, object] = {
    "code": 404,
    "message": "Not found error.",
    "status": 404,
}
_DEVICE_INFO: dict[str, object] = {"device": {"name": "TV"}}


class _Handler(BaseHTTPRequestHandler):
    def _reply(self) -> None:
        if self.path == "/api/v2/":
            status, payload = 200, _DEVICE_INFO
        else:
            status, payload = 404, _NOT_FOUND
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    do_GET = do_POST = do_PUT = do_DELETE = _reply

    def log_message(self, *args: object) -> None:
        pass


@pytest.fixture(name="tv_port")
def tv_port_fixture() -> Iterator[int]:
    server = HTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server.server_address[1]
    server.shutdown()
    server.server_close()
    thread.join()


def test_rest_request_returns_body_on_success(tv_port: int) -> None:
    rest = SamsungTVRest("127.0.0.1", port=tv_port, timeout=2)
    assert rest.rest_device_info() == _DEVICE_INFO


@pytest.mark.parametrize(
    "method", ["rest_app_status", "rest_app_run", "rest_app_close", "rest_app_install"]
)
def test_rest_request_raises_on_http_error(tv_port: int, method: str) -> None:
    rest = SamsungTVRest("127.0.0.1", port=tv_port, timeout=2)
    with pytest.raises(HttpApiError, match="HTTP 404: .*Not found error"):
        getattr(rest, method)("no.such.app")


@pytest.mark.asyncio
async def test_async_rest_request_returns_body_on_success(tv_port: int) -> None:
    async with aiohttp.ClientSession() as session:
        rest = SamsungTVAsyncRest("127.0.0.1", session=session, port=tv_port, timeout=2)
        assert await rest.rest_device_info() == _DEVICE_INFO


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method", ["rest_app_status", "rest_app_run", "rest_app_close", "rest_app_install"]
)
async def test_async_rest_request_raises_on_http_error(
    tv_port: int, method: str
) -> None:
    async with aiohttp.ClientSession() as session:
        rest = SamsungTVAsyncRest("127.0.0.1", session=session, port=tv_port, timeout=2)
        with pytest.raises(HttpApiError, match="HTTP 404: .*Not found error"):
            await getattr(rest, method)("no.such.app")
