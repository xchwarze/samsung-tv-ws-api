"""Tests for cli apps module."""

from collections.abc import Iterator
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from samsungtvws.cli import cli

BASE_ARGS = ["--host", "127.0.0.1", "--token", "abc"]


@pytest.fixture(name="mock_tv")
def get_mock_tv() -> Iterator[MagicMock]:
    """Patch the SamsungTVWS instance used by the CLI."""
    with patch("samsungtvws.cli.main.SamsungTVWS", autospec=True) as tv_class:
        yield tv_class.return_value


def test_apps(mock_tv: MagicMock) -> None:
    """Ensure the installed app list is printed."""
    mock_tv.app_list.return_value = [{"appId": "111299001912", "name": "YouTube"}]
    result = CliRunner().invoke(cli, [*BASE_ARGS, "apps"])
    assert result.exit_code == 0
    assert result.stdout == "[{'appId': '111299001912', 'name': 'YouTube'}]\n"
    mock_tv.app_list.assert_called_once_with()


@pytest.mark.parametrize(
    ("extra_args", "app_type", "meta_tag"),
    [
        pytest.param([], "DEEP_LINK", "", id="defaults"),
        pytest.param(
            ["--type", "NATIVE_LAUNCH", "--meta-tag", "watch?v=1"],
            "NATIVE_LAUNCH",
            "watch?v=1",
            id="options",
        ),
    ],
)
def test_app_run_ws(
    mock_tv: MagicMock, extra_args: list[str], app_type: str, meta_tag: str
) -> None:
    """Ensure an app is launched over the websocket."""
    result = CliRunner().invoke(
        cli, [*BASE_ARGS, "app-run-ws", "111299001912", *extra_args]
    )
    assert result.exit_code == 0
    mock_tv.run_app.assert_called_once_with(
        "111299001912", app_type=app_type, meta_tag=meta_tag
    )


def test_open_browser(mock_tv: MagicMock) -> None:
    """Ensure a URL is opened in the TV browser."""
    result = CliRunner().invoke(
        cli, [*BASE_ARGS, "open-browser", "https://example.com"]
    )
    assert result.exit_code == 0
    mock_tv.open_browser.assert_called_once_with("https://example.com")
