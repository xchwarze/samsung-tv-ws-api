"""Tests for connection module."""

from collections.abc import Iterator
import logging
from pathlib import Path
import ssl
import threading
from unittest.mock import Mock, patch

import pytest

from samsungtvws.command import SamsungTVSleepCommand
from samsungtvws.connection import SamsungTVWSConnection
from samsungtvws.exceptions import ConnectionFailure, UnauthorizedError

from .const import MS_CHANNEL_CONNECT_SAMPLE, MS_ERROR_SAMPLE

with open("tests/fixtures/connection_ms_channel_connect_token.json") as file:
    MS_CHANNEL_CONNECT_TOKEN_SAMPLE = file.read()
with open("tests/fixtures/connection_ms_channel_unauthorized.json") as file:
    MS_CHANNEL_UNAUTHORIZED_SAMPLE = file.read()
with open("tests/fixtures/connection_ms_error_remote_control.json") as file:
    MS_ERROR_REMOTE_CONTROL_SAMPLE = file.read()

ENDPOINT = "samsung.remote.control"
NAME_B64 = "U2Ftc3VuZ1R2UmVtb3Rl"


def _connection(**kwargs: object) -> SamsungTVWSConnection:
    return SamsungTVWSConnection("127.0.0.1", endpoint=ENDPOINT, **kwargs)


def test_open_url() -> None:
    """Ensure the plain websocket URL is used on port 8001."""
    connection = Mock()
    connection.recv.side_effect = [MS_CHANNEL_CONNECT_SAMPLE]
    with patch(
        "samsungtvws.connection.websocket.create_connection",
        return_value=connection,
    ) as create_connection:
        tv = _connection(timeout=0)
        assert tv.open() is connection

    create_connection.assert_called_once_with(
        f"ws://127.0.0.1:8001/api/v2/channels/{ENDPOINT}?name={NAME_B64}",
        None,
        sslopt={},
        connection="Connection: Upgrade",
    )


def test_open_ssl_url_with_token() -> None:
    """Ensure the secure URL carries the token and disables cert checks."""
    connection = Mock()
    connection.recv.side_effect = [MS_CHANNEL_CONNECT_SAMPLE]
    with patch(
        "samsungtvws.connection.websocket.create_connection",
        return_value=connection,
    ) as create_connection:
        tv = _connection(port=8002, token="abc", timeout=5)
        tv.open()

    create_connection.assert_called_once_with(
        f"wss://127.0.0.1:8002/api/v2/channels/{ENDPOINT}?name={NAME_B64}&token=abc",
        5,
        sslopt={"cert_reqs": ssl.CERT_NONE},
        connection="Connection: Upgrade",
    )
    assert tv.token == 123456789


def test_open_reuses_connection(connection: Mock) -> None:
    """Ensure open returns the existing connection."""
    connection.recv.side_effect = [MS_CHANNEL_CONNECT_SAMPLE]
    tv = _connection()
    first = tv.open()
    with patch(
        "samsungtvws.connection.websocket.create_connection"
    ) as create_connection:
        assert tv.open() is first

    create_connection.assert_not_called()


def test_open_unauthorized(connection: Mock) -> None:
    """Ensure an unauthorized event raises UnauthorizedError."""
    connection.recv.side_effect = [MS_CHANNEL_UNAUTHORIZED_SAMPLE]
    tv = _connection()
    with pytest.raises(UnauthorizedError):
        tv.open()
    assert tv.connection is None


@pytest.mark.parametrize(
    ("sample", "log_error"),
    [
        pytest.param(MS_ERROR_SAMPLE, False, id="other-error"),
        pytest.param(MS_ERROR_REMOTE_CONTROL_SAMPLE, True, id="v1-only-tv"),
    ],
)
def test_open_error_event(
    connection: Mock,
    caplog: pytest.LogCaptureFixture,
    sample: str,
    log_error: bool,
) -> None:
    """Ensure an error event fails the connection and hints at the v1 API."""
    connection.recv.side_effect = [sample]
    tv = _connection()
    with caplog.at_level(logging.ERROR), pytest.raises(ConnectionFailure):
        tv.open()
    assert (
        "Your TV does not seem to support v2 API, please try v1 API" in caplog.text
    ) is log_error


def test_token_file_read(connection: Mock, tmp_path: Path) -> None:
    """Ensure the token is read from the token file."""
    token_file = tmp_path / "token.txt"
    token_file.write_text("filetoken")
    connection.recv.side_effect = [MS_CHANNEL_CONNECT_TOKEN_SAMPLE]
    with patch(
        "samsungtvws.connection.websocket.create_connection",
        return_value=connection,
    ) as create_connection:
        _connection(port=8002, token_file=str(token_file)).open()

    assert create_connection.call_args.args[0].endswith("&token=filetoken")


def test_token_file_missing(connection: Mock, tmp_path: Path) -> None:
    """Ensure a missing token file is ignored and created with the new token."""
    token_file = tmp_path / "token.txt"
    connection.recv.side_effect = [MS_CHANNEL_CONNECT_TOKEN_SAMPLE]
    with patch(
        "samsungtvws.connection.websocket.create_connection",
        return_value=connection,
    ) as create_connection:
        tv = _connection(port=8002, token_file=str(token_file))
        tv.open()

    assert "token=" not in create_connection.call_args.args[0]
    assert tv.token is None
    assert token_file.read_text() == "12345678"


def test_start_listening(connection: Mock) -> None:
    """Ensure received events are passed to the callback until the socket ends."""
    sent = threading.Event()

    def _recv() -> Iterator[str]:
        yield MS_CHANNEL_CONNECT_SAMPLE
        sent.wait(5)
        yield MS_ERROR_SAMPLE
        yield '{"data": 1}'
        yield ""

    messages = _recv()
    connection.recv.side_effect = lambda: next(messages)
    callback = Mock()
    tv = _connection()
    tv.start_listening(callback)
    sent.set()
    tv.close()

    assert [c.args[0] for c in callback.call_args_list] == ["ms.error", "*"]
    assert callback.call_args_list[1].args[1] == {"data": 1}
    connection.close.assert_called_once_with()
    assert tv.connection is None


def test_start_listening_without_callback(connection: Mock) -> None:
    """Ensure listening works without a callback."""
    connection.recv.side_effect = [MS_CHANNEL_CONNECT_SAMPLE, MS_ERROR_SAMPLE, ""]
    tv = _connection()
    tv.start_listening()
    tv.close()

    assert connection.recv.call_count == 3


def test_start_listening_already_connected(connection: Mock) -> None:
    """Ensure listening twice raises ConnectionFailure."""
    connection.recv.side_effect = [MS_CHANNEL_CONNECT_SAMPLE]
    tv = _connection()
    tv.open()
    with pytest.raises(ConnectionFailure, match="Connection already exists"):
        tv.start_listening()


def test_context_manager_closes(connection: Mock) -> None:
    """Ensure leaving the context closes the connection."""
    connection.recv.side_effect = [MS_CHANNEL_CONNECT_SAMPLE]
    with _connection() as tv:
        tv.open()
        assert tv.connection is connection

    connection.close.assert_called_once_with()
    assert tv.connection is None


def test_send_command_dict(connection: Mock) -> None:
    """Ensure a dict command is sent as JSON followed by the key press delay."""
    connection.recv.side_effect = [MS_CHANNEL_CONNECT_SAMPLE]
    tv = _connection(key_press_delay=0.5)
    with patch("samsungtvws.connection.time.sleep") as mock_sleep:
        tv.send_command({"method": "ms.test", "params": {}})

    connection.send.assert_called_once_with('{"method": "ms.test", "params": {}}')
    mock_sleep.assert_called_once_with(0.5)


def test_send_command_list(connection: Mock) -> None:
    """Ensure a list of commands is sent in order, honoring sleep commands."""
    connection.recv.side_effect = [MS_CHANNEL_CONNECT_SAMPLE]
    tv = _connection()
    with patch("samsungtvws.connection.time.sleep") as mock_sleep:
        tv.send_command(
            [{"method": "a"}, SamsungTVSleepCommand(3), {"method": "b"}],
            key_press_delay=0,
        )

    assert [c.args[0] for c in connection.send.call_args_list] == [
        '{"method": "a"}',
        '{"method": "b"}',
    ]
    assert [c.args[0] for c in mock_sleep.call_args_list] == [0, 3, 0]


@pytest.mark.parametrize(
    ("connected", "expected"),
    [
        pytest.param(True, True, id="connected"),
        pytest.param(False, False, id="disconnected"),
    ],
)
def test_is_alive(connection: Mock, connected: bool, expected: bool) -> None:
    """Ensure is_alive reflects the socket state."""
    connection.recv.side_effect = [MS_CHANNEL_CONNECT_SAMPLE]
    connection.connected = connected
    tv = _connection()
    tv.open()
    assert tv.is_alive() is expected


def test_is_alive_without_connection() -> None:
    """Ensure is_alive is False before opening."""
    assert _connection().is_alive() is False
