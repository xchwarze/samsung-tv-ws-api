"""Tests for cli shortcuts module."""

from collections.abc import Iterator
from unittest.mock import MagicMock, call, patch

import pytest
from typer.testing import CliRunner

from samsungtvws.cli import cli
from samsungtvws.shortcuts import SamsungTVShortcuts

BASE_ARGS = ["--host", "127.0.0.1", "--token", "abc"]


@pytest.fixture(name="mock_tv")
def get_mock_tv() -> Iterator[MagicMock]:
    """Patch the SamsungTVWS instance used by the CLI, keeping real shortcuts."""
    with patch("samsungtvws.cli.main.SamsungTVWS", autospec=True) as tv_class:
        tv = tv_class.return_value
        tv.shortcuts.return_value = SamsungTVShortcuts(tv)
        yield tv


@pytest.mark.parametrize(
    ("command", "keys"),
    [
        pytest.param(["power"], ["KEY_POWER"], id="power"),
        pytest.param(["home"], ["KEY_HOME"], id="home"),
        pytest.param(["menu"], ["KEY_MENU"], id="menu"),
        pytest.param(["source"], ["KEY_SOURCE"], id="source"),
        pytest.param(["back"], ["KEY_RETURN"], id="back"),
        pytest.param(["up"], ["KEY_UP"], id="up"),
        pytest.param(["down"], ["KEY_DOWN"], id="down"),
        pytest.param(["left"], ["KEY_LEFT"], id="left"),
        pytest.param(["right"], ["KEY_RIGHT"], id="right"),
        pytest.param(["enter"], ["KEY_ENTER"], id="enter"),
        pytest.param(["volume-up"], ["KEY_VOLUP"], id="volume-up"),
        pytest.param(["volume-down"], ["KEY_VOLDOWN"], id="volume-down"),
        pytest.param(["mute"], ["KEY_MUTE"], id="mute"),
        pytest.param(["channel-up"], ["KEY_CHUP"], id="channel-up"),
        pytest.param(["channel-down"], ["KEY_CHDOWN"], id="channel-down"),
        pytest.param(["channel", "42"], ["KEY_4", "KEY_2", "KEY_ENTER"], id="channel"),
    ],
)
def test_shortcut(mock_tv: MagicMock, command: list[str], keys: list[str]) -> None:
    """Ensure each shortcut command sends its keys."""
    result = CliRunner().invoke(cli, [*BASE_ARGS, *command])
    assert result.exit_code == 0
    assert mock_tv.send_key.call_args_list == [call(key) for key in keys]
