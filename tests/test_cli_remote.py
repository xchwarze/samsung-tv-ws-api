"""Tests for cli remote module."""

from collections.abc import Iterator
import re
from unittest.mock import MagicMock, call, patch

import pytest
from typer.testing import CliRunner

from samsungtvws.cli import cli

BASE_ARGS = ["--host", "127.0.0.1", "--token", "abc"]

# CI forces rich terminal output: colored and wrapped in a box
_RICH_MARKUP = re.compile(r"\x1b\[[0-9;]*m|[\u2500-\u257f]")


def plain_text(text: str) -> str:
    """Return CLI output without rich markup, on a single line."""
    return " ".join(_RICH_MARKUP.sub("", text).split())


@pytest.fixture(name="mock_tv")
def get_mock_tv() -> Iterator[MagicMock]:
    """Patch the SamsungTVWS instance used by the CLI."""
    with patch("samsungtvws.cli.main.SamsungTVWS", autospec=True) as tv_class:
        yield tv_class.return_value


@pytest.mark.parametrize(
    ("extra_args", "times", "cmd", "delay"),
    [
        pytest.param([], 1, "Click", None, id="defaults"),
        pytest.param(
            ["--times", "3", "--cmd", " press ", "--delay", "0.2"],
            3,
            "Press",
            0.2,
            id="press-repeated",
        ),
        pytest.param(["--cmd", "RELEASE"], 1, "Release", None, id="release"),
    ],
)
def test_send_key(
    mock_tv: MagicMock,
    extra_args: list[str],
    times: int,
    cmd: str,
    delay: float | None,
) -> None:
    """Ensure a key is sent with a normalized command."""
    result = CliRunner().invoke(cli, [*BASE_ARGS, "send-key", "KEY_UP", *extra_args])
    assert result.exit_code == 0
    mock_tv.send_key.assert_called_once_with(
        key="KEY_UP", times=times, cmd=cmd, key_press_delay=delay
    )


def test_send_key_invalid_cmd(mock_tv: MagicMock) -> None:
    """Ensure an unknown key command is rejected."""
    result = CliRunner().invoke(cli, [*BASE_ARGS, "send-key", "KEY_UP", "--cmd", "Tap"])
    assert result.exit_code == 2
    assert "Invalid --cmd. Use: Click|Press|Release" in plain_text(result.stderr)
    mock_tv.send_key.assert_not_called()


def test_hold_key(mock_tv: MagicMock) -> None:
    """Ensure a key is held for the given duration."""
    result = CliRunner().invoke(cli, [*BASE_ARGS, "hold-key", "KEY_VOLUP", "1.5"])
    assert result.exit_code == 0
    mock_tv.hold_key.assert_called_once_with("KEY_VOLUP", 1.5)


def test_move_cursor(mock_tv: MagicMock) -> None:
    """Ensure the cursor is moved to the coordinates."""
    result = CliRunner().invoke(cli, [*BASE_ARGS, "move-cursor", "100", "200"])
    assert result.exit_code == 0
    mock_tv.move_cursor.assert_called_once_with(100, 200)


@pytest.mark.parametrize(
    ("command", "key"),
    [
        pytest.param(["mouse-click"], "KEY_ENTER", id="mouse-click"),
        pytest.param(
            ["factory", "--i-know-what-im-doing"], "KEY_FACTORY", id="factory"
        ),
    ],
)
def test_single_key_commands(mock_tv: MagicMock, command: list[str], key: str) -> None:
    """Ensure single key commands send their key."""
    result = CliRunner().invoke(cli, [*BASE_ARGS, *command])
    assert result.exit_code == 0
    mock_tv.send_key.assert_called_once_with(key)


def test_factory_requires_ack(mock_tv: MagicMock) -> None:
    """Ensure the factory menu is not opened without acknowledgement."""
    result = CliRunner().invoke(cli, [*BASE_ARGS, "factory"])
    assert result.exit_code == 1
    assert "Re-run with --i-know-what-im-doing to proceed." in result.stderr
    mock_tv.send_key.assert_not_called()


@pytest.mark.parametrize(
    ("extra_args", "expected_calls"),
    [
        pytest.param([], [call.send_text("hello")], id="text-only"),
        pytest.param(
            ["--end"], [call.send_text("hello"), call.end_text()], id="with-end"
        ),
    ],
)
def test_send_text(
    mock_tv: MagicMock, extra_args: list[str], expected_calls: list[object]
) -> None:
    """Ensure text is sent, optionally ending the input session."""
    result = CliRunner().invoke(cli, [*BASE_ARGS, "send-text", "hello", *extra_args])
    assert result.exit_code == 0
    assert mock_tv.mock_calls == expected_calls


def test_end_text(mock_tv: MagicMock) -> None:
    """Ensure the text input session is ended."""
    result = CliRunner().invoke(cli, [*BASE_ARGS, "end-text"])
    assert result.exit_code == 0
    mock_tv.end_text.assert_called_once_with()
