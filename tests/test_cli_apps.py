"""Tests for cli apps module."""

from unittest.mock import MagicMock

import pytest

from .const import (
    APP_ID,
    invoke,
)


def test_apps(mock_tv: MagicMock) -> None:
    """Ensure the installed app list is printed."""
    mock_tv.app_list.return_value = [{"appId": APP_ID, "name": "YouTube"}]
    result = invoke("apps")
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
    result = invoke("app-run-ws", APP_ID, *extra_args)
    assert result.exit_code == 0
    mock_tv.run_app.assert_called_once_with(
        APP_ID, app_type=app_type, meta_tag=meta_tag
    )


def test_open_browser(mock_tv: MagicMock) -> None:
    """Ensure a URL is opened in the TV browser."""
    result = invoke("open-browser", "https://example.com")
    assert result.exit_code == 0
    mock_tv.open_browser.assert_called_once_with("https://example.com")
