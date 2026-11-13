"""Tests for cli main module."""

from collections.abc import Iterator
import logging
from unittest.mock import MagicMock, Mock, patch

import pytest
import typer
from typer.testing import CliRunner

from samsungtvws.cli import cli
from samsungtvws.cli.main import bootstrap_token_if_needed

HOST = "127.0.0.1"


@pytest.fixture(name="mock_tv")
def get_mock_tv() -> Iterator[MagicMock]:
    """Patch the SamsungTVWS class instantiated by the CLI."""
    with patch("samsungtvws.cli.main.SamsungTVWS", autospec=True) as tv_class:
        tv_class.return_value.token = None
        yield tv_class


@pytest.fixture(name="mock_basic_config")
def get_mock_basic_config() -> Iterator[Mock]:
    """Patch logging configuration done by the CLI."""
    with patch("samsungtvws.cli.main.logging.basicConfig") as basic_config:
        yield basic_config


def test_no_args_shows_help() -> None:
    """Ensure running without arguments prints the help."""
    result = CliRunner().invoke(cli, [])
    assert result.exit_code == 2
    assert "Usage:" in result.output


def test_commands_sorted() -> None:
    """Ensure commands are listed in alphabetical order."""
    group = typer.main.get_command(cli)
    commands = group.list_commands(typer.Context(group))
    assert commands == sorted(commands)
    assert {"end-text", "power", "wol"} <= set(commands)


@pytest.mark.usefixtures("mock_basic_config")
def test_options_passed_to_tv(mock_tv: MagicMock) -> None:
    """Ensure global options are passed to SamsungTVWS."""
    result = CliRunner().invoke(
        cli,
        [
            "--host",
            HOST,
            "--port",
            "8001",
            "--token",
            "abc",
            "--token-file",
            "token.txt",
            "--timeout",
            "5",
            "--key-press-delay",
            "0.5",
            "--name",
            "MyCli",
            "end-text",
        ],
    )
    assert result.exit_code == 0
    mock_tv.assert_called_once_with(
        host=HOST,
        port=8001,
        token="abc",
        token_file="token.txt",
        timeout=5.0,
        key_press_delay=0.5,
        name="MyCli",
    )
    mock_tv.return_value.end_text.assert_called_once_with()


@pytest.mark.usefixtures("mock_basic_config")
def test_defaults_and_zero_timeout(mock_tv: MagicMock) -> None:
    """Ensure defaults are used and a zero timeout disables the timeout."""
    result = CliRunner().invoke(
        cli, ["--host", HOST, "--token", "abc", "--timeout", "0", "end-text"]
    )
    assert result.exit_code == 0
    mock_tv.assert_called_once_with(
        host=HOST,
        port=8002,
        token="abc",
        token_file=None,
        timeout=None,
        key_press_delay=1.0,
        name="SamsungTvRemoteCli",
    )


@pytest.mark.parametrize(
    ("verbose_args", "level"),
    [
        pytest.param([], logging.WARNING, id="default"),
        pytest.param(["-v"], logging.INFO, id="verbose"),
        pytest.param(["-vv"], logging.DEBUG, id="very-verbose"),
        pytest.param(["-v", "-v", "-v"], logging.DEBUG, id="more-verbose"),
    ],
)
@pytest.mark.usefixtures("mock_tv")
def test_logging_level(
    mock_basic_config: Mock, verbose_args: list[str], level: int
) -> None:
    """Ensure the verbosity flag sets the logging level."""
    result = CliRunner().invoke(
        cli, ["--host", HOST, "--token", "abc", *verbose_args, "end-text"]
    )
    assert result.exit_code == 0
    mock_basic_config.assert_called_once_with(
        level=level, format="%(levelname)s: %(message)s"
    )


@pytest.mark.usefixtures("mock_basic_config")
def test_bootstrap_token(mock_tv: MagicMock) -> None:
    """Ensure a new token is fetched, printed and used by the command."""
    tv = mock_tv.return_value
    tv.token = "new-token"
    result = CliRunner().invoke(cli, ["--host", HOST, "end-text"])
    assert result.exit_code == 0
    assert result.stderr == "[*] Auth token (not saved): new-token\n"
    tv.open.assert_called_once_with()
    tv.close.assert_called_once_with()
    assert mock_tv.call_args_list[0].kwargs["token"] is None
    assert mock_tv.call_args_list[1].kwargs["token"] == "new-token"


@pytest.mark.usefixtures("mock_basic_config")
def test_bootstrap_no_token(mock_tv: MagicMock) -> None:
    """Ensure nothing is printed when the TV returns no token."""
    tv = mock_tv.return_value
    result = CliRunner().invoke(cli, ["--host", HOST, "end-text"])
    assert result.exit_code == 0
    assert result.stderr == ""
    tv.open.assert_called_once_with()
    tv.close.assert_called_once_with()
    assert mock_tv.call_args_list[1].kwargs["token"] is None


@pytest.mark.usefixtures("mock_basic_config")
def test_bootstrap_open_failure_closes(mock_tv: MagicMock) -> None:
    """Ensure the connection is closed when opening it fails."""
    tv = mock_tv.return_value
    tv.open.side_effect = OSError("unreachable")
    result = CliRunner().invoke(cli, ["--host", HOST, "end-text"])
    assert isinstance(result.exception, OSError)
    tv.close.assert_called_once_with()
    tv.end_text.assert_not_called()


@pytest.mark.parametrize(
    "extra_args",
    [
        pytest.param(["--no-print-token"], id="no-print-token"),
        pytest.param(["--token-file", "token.txt"], id="token-file"),
        pytest.param(["--token", "abc"], id="token"),
    ],
)
@pytest.mark.usefixtures("mock_basic_config")
def test_bootstrap_skipped(mock_tv: MagicMock, extra_args: list[str]) -> None:
    """Ensure no token is fetched when it is not needed."""
    tv = mock_tv.return_value
    result = CliRunner().invoke(cli, ["--host", HOST, *extra_args, "end-text"])
    assert result.exit_code == 0
    tv.open.assert_not_called()
    tv.close.assert_not_called()
    mock_tv.assert_called_once()


def test_bootstrap_without_subcommand(mock_tv: MagicMock) -> None:
    """Ensure no token is fetched when no subcommand is invoked."""
    ctx = Mock(invoked_subcommand=None, obj={})
    bootstrap_token_if_needed(ctx)
    mock_tv.assert_not_called()
