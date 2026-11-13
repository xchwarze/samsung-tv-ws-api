"""Tests for cli rest module."""

from collections.abc import Iterator
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from samsungtvws.cli import cli

BASE_ARGS = ["--host", "127.0.0.1", "--token", "abc"]
APP_ID = "111299001912"


@pytest.fixture(name="mock_tv")
def get_mock_tv() -> Iterator[MagicMock]:
    """Patch the SamsungTVWS instance used by the CLI."""
    with patch("samsungtvws.cli.main.SamsungTVWS", autospec=True) as tv_class:
        yield tv_class.return_value


def test_device_info(mock_tv: MagicMock) -> None:
    """Ensure the device info is printed."""
    mock_tv.rest_device_info.return_value = {"device": {"modelName": "QE55"}}
    result = CliRunner().invoke(cli, [*BASE_ARGS, "device-info"])
    assert result.exit_code == 0
    assert result.stdout == "{'device': {'modelName': 'QE55'}}\n"
    mock_tv.rest_device_info.assert_called_once_with()


@pytest.mark.parametrize(
    ("command", "method"),
    [
        pytest.param("app-status", "rest_app_status", id="app-status"),
        pytest.param("app-run", "rest_app_run", id="app-run"),
        pytest.param("app-close", "rest_app_close", id="app-close"),
        pytest.param("app-install", "rest_app_install", id="app-install"),
    ],
)
def test_app_commands(mock_tv: MagicMock, command: str, method: str) -> None:
    """Ensure each REST app command calls the API and prints its result."""
    getattr(mock_tv, method).return_value = {"id": APP_ID, "running": True}
    result = CliRunner().invoke(cli, [*BASE_ARGS, command, APP_ID])
    assert result.exit_code == 0
    assert result.stdout == f"{{'id': '{APP_ID}', 'running': True}}\n"
    getattr(mock_tv, method).assert_called_once_with(APP_ID)
