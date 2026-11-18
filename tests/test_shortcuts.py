"""Tests for shortcuts module."""

from unittest.mock import Mock, call

import pytest

from samsungtvws.remote import SamsungTVWS
from samsungtvws.shortcuts import SamsungTVShortcuts


@pytest.fixture(name="remote")
def get_remote() -> Mock:
    """Return a mocked remote."""
    return Mock(spec=SamsungTVWS)


@pytest.mark.parametrize(
    ("method", "key"),
    [
        pytest.param("power", "KEY_POWER", id="power"),
        pytest.param("home", "KEY_HOME", id="home"),
        pytest.param("menu", "KEY_MENU", id="menu"),
        pytest.param("source", "KEY_SOURCE", id="source"),
        pytest.param("guide", "KEY_GUIDE", id="guide"),
        pytest.param("tools", "KEY_TOOLS", id="tools"),
        pytest.param("info", "KEY_INFO", id="info"),
        pytest.param("up", "KEY_UP", id="up"),
        pytest.param("down", "KEY_DOWN", id="down"),
        pytest.param("left", "KEY_LEFT", id="left"),
        pytest.param("right", "KEY_RIGHT", id="right"),
        pytest.param("enter", "KEY_ENTER", id="enter"),
        pytest.param("back", "KEY_RETURN", id="back"),
        pytest.param("channel_list", "KEY_CH_LIST", id="channel-list"),
        pytest.param("channel_up", "KEY_CHUP", id="channel-up"),
        pytest.param("channel_down", "KEY_CHDOWN", id="channel-down"),
        pytest.param("volume_up", "KEY_VOLUP", id="volume-up"),
        pytest.param("volume_down", "KEY_VOLDOWN", id="volume-down"),
        pytest.param("mute", "KEY_MUTE", id="mute"),
        pytest.param("red", "KEY_RED", id="red"),
        pytest.param("green", "KEY_GREEN", id="green"),
        pytest.param("yellow", "KEY_YELLOW", id="yellow"),
        pytest.param("blue", "KEY_BLUE", id="blue"),
    ],
)
def test_shortcut_sends_key(remote: Mock, method: str, key: str) -> None:
    """Ensure each shortcut sends its key."""
    getattr(SamsungTVShortcuts(remote), method)()
    remote.send_key.assert_called_once_with(key)


def test_digit(remote: Mock) -> None:
    """Ensure a digit sends the matching key."""
    SamsungTVShortcuts(remote).digit("7")
    remote.send_key.assert_called_once_with("KEY_7")


@pytest.mark.parametrize(
    ("channel", "keys"),
    [
        pytest.param(5, ["KEY_5", "KEY_ENTER"], id="int"),
        pytest.param("102", ["KEY_1", "KEY_0", "KEY_2", "KEY_ENTER"], id="str"),
    ],
)
def test_channel(remote: Mock, channel: int | str, keys: list[str]) -> None:
    """Ensure a channel sends each digit followed by enter."""
    SamsungTVShortcuts(remote).channel(channel)
    assert remote.send_key.call_args_list == [call(key) for key in keys]
