"""Tests for remote module."""

from collections.abc import Iterator
import json
import threading
from typing import Any
from unittest.mock import Mock, call, patch

import pytest

from samsungtvws.art import SamsungTVArt
from samsungtvws.command import SamsungTVSleepCommand
from samsungtvws.exceptions import ConnectionFailure
from samsungtvws.remote import (
    ChannelEmitCommand,
    SamsungTVWS,
    SendInputEnd,
    SendInputString,
    SendRemoteKey,
)
from samsungtvws.shortcuts import SamsungTVShortcuts

from .const import (
    ED_APPS_LAUNCH_SAMPLE,
    ED_EDENTV_UPDATE_SAMPLE,
    ED_INSTALLED_APP_SAMPLE,
    MS_CHANNEL_CONNECT_SAMPLE,
    MS_ERROR_SAMPLE,
    MS_REMOTE_TOUCH_DISABLE_SAMPLE,
    MS_REMOTE_TOUCH_ENABLE_SAMPLE,
    MS_VOICEAPP_HIDE_SAMPLE,
)


def test_connect(connection: Mock) -> None:
    """Ensure simple data can be parsed."""
    connection.recv = Mock(side_effect=[MS_CHANNEL_CONNECT_SAMPLE])
    tv = SamsungTVWS("127.0.0.1")
    tv.open()
    assert tv.token == 123456789


def test_connect_with_extra_event(connection: Mock) -> None:
    """Ensure simple data can be parsed."""
    connection.recv = Mock(
        side_effect=[
            MS_VOICEAPP_HIDE_SAMPLE,
            ED_EDENTV_UPDATE_SAMPLE,
            MS_CHANNEL_CONNECT_SAMPLE,
        ]
    )
    tv = SamsungTVWS("127.0.0.1")
    tv.open()
    assert tv.token == 123456789


def test_connect_with_touch_events(connection: Mock) -> None:
    """Ensure touch events sent before connect are ignored."""
    connection.recv = Mock(
        side_effect=[
            MS_REMOTE_TOUCH_DISABLE_SAMPLE,
            MS_REMOTE_TOUCH_ENABLE_SAMPLE,
            MS_REMOTE_TOUCH_DISABLE_SAMPLE,
            MS_CHANNEL_CONNECT_SAMPLE,
        ]
    )
    tv = SamsungTVWS("127.0.0.1")
    tv.open()
    assert tv.token == 123456789


def test_connection_failure(connection: Mock) -> None:
    """Ensure simple data can be parsed."""
    connection.recv = Mock(side_effect=[MS_ERROR_SAMPLE])
    tv = SamsungTVWS("127.0.0.1")
    with pytest.raises(ConnectionFailure):
        tv.open()


def test_send_key(connection: Mock) -> None:
    """Ensure simple data can be parsed."""
    connection.recv.side_effect = [MS_CHANNEL_CONNECT_SAMPLE]
    tv = SamsungTVWS("127.0.0.1")
    tv.send_key("KEY_POWER")
    connection.send.assert_called_once_with(
        '{"method": "ms.remote.control", "params": {'
        '"Cmd": "Click", '
        '"DataOfCmd": "KEY_POWER", '
        '"Option": "false", '
        '"TypeOfRemote": "SendRemoteKey"'
        "}}"
    )


def test_app_list(connection: Mock) -> None:
    """Ensure valid app_list data can be parsed."""
    connection.recv.side_effect = [
        MS_CHANNEL_CONNECT_SAMPLE,
        ED_INSTALLED_APP_SAMPLE,
    ]
    tv = SamsungTVWS("127.0.0.1")
    assert tv.app_list() == [
        {
            "appId": "111299001912",
            "app_type": 2,
            "icon": "/opt/share/webappservice/apps_icon/FirstScreen/111299001912/250x250.png",
            "is_lock": 0,
            "name": "YouTube",
        },
        {
            "appId": "3201608010191",
            "app_type": 2,
            "icon": "/opt/share/webappservice/apps_icon/FirstScreen/3201608010191/250x250.png",
            "is_lock": 0,
            "name": "Deezer",
        },
    ]


def test_app_list_invalid(connection: Mock) -> None:
    """Ensure simple data can be parsed."""
    connection.recv.side_effect = [
        MS_CHANNEL_CONNECT_SAMPLE,
        ED_APPS_LAUNCH_SAMPLE,
    ]
    tv = SamsungTVWS("127.0.0.1")
    assert tv.app_list() is None
    connection.send.assert_called_once_with(
        '{"method": "ms.channel.emit", "params": {"event": "ed.installedApp.get", "to": "host"}}'
    )


def test_send_hold_key(connection: Mock) -> None:
    """Ensure simple data can be parsed."""
    connection.recv.side_effect = [MS_CHANNEL_CONNECT_SAMPLE]

    tv = SamsungTVWS("127.0.0.1")
    with patch("samsungtvws.connection.time.sleep") as patch_sleep:
        tv.hold_key("KEY_POWER", 3)

    assert patch_sleep.call_count == 3
    assert patch_sleep.call_args_list == [call(1), call(3), call(1)]


with open("tests/fixtures/remote_ms_remote_ime_start.json") as file:
    MS_REMOTE_IME_START_SAMPLE = file.read()
with open("tests/fixtures/remote_ms_remote_ime_end.json") as file:
    MS_REMOTE_IME_END_SAMPLE = file.read()
with open("tests/fixtures/remote_rest_device_info.json") as file:
    REST_DEVICE_INFO_SAMPLE = file.read()

TEXT_RECEIVED_PAYLOAD = (
    '{"method": "ms.channel.emit", "params": '
    '{"event": "custom.remote.textReceived", "to": "broadcast"}}'
)


def _key_params(cmd: str, key: str) -> dict[str, str]:
    return {
        "Cmd": cmd,
        "DataOfCmd": key,
        "Option": "false",
        "TypeOfRemote": "SendRemoteKey",
    }


def _input_payload(encoded: str) -> str:
    return json.dumps(
        {
            "method": "ms.remote.control",
            "params": {
                "Cmd": encoded,
                "DataOfCmd": "base64",
                "TypeOfRemote": "SendInputString",
            },
        }
    )


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
        pytest.param("factory", "KEY_FACTORY", id="factory"),
    ],
)
def test_send_remote_key_shortcut(method: str, key: str) -> None:
    """Ensure each SendRemoteKey shortcut clicks its key."""
    command = getattr(SendRemoteKey, method)()
    assert command.as_dict() == {
        "method": "ms.remote.control",
        "params": _key_params("Click", key),
    }


def test_send_remote_key_digit() -> None:
    """Ensure a digit clicks the matching key."""
    assert SendRemoteKey.digit(7).params == _key_params("Click", "KEY_7")


@pytest.mark.parametrize(
    "method",
    [
        pytest.param("hold", id="hold"),
        pytest.param("hold_key", id="hold-key-deprecated"),
    ],
)
@pytest.mark.filterwarnings("ignore::DeprecationWarning")
def test_send_remote_key_hold(method: str) -> None:
    """Ensure holding a key presses, sleeps and releases it."""
    press, sleep, release = getattr(SendRemoteKey, method)("KEY_POWER", 2)
    assert press.params == _key_params("Press", "KEY_POWER")
    assert isinstance(sleep, SamsungTVSleepCommand)
    assert sleep.delay == 2
    assert release.params == _key_params("Release", "KEY_POWER")


def test_send_remote_key_hold_key_deprecated() -> None:
    """Ensure hold_key warns about its deprecation."""
    with pytest.warns(DeprecationWarning, match="use SendRemoteKey.hold instead"):
        SendRemoteKey.hold_key("KEY_POWER", 2)


def test_input_commands() -> None:
    """Ensure input string and input end commands are built."""
    assert SendInputString.send("hi").get_payload() == _input_payload("aGk=")
    assert SendInputEnd().as_dict() == {
        "method": "ms.remote.control",
        "params": {"TypeOfRemote": "SendInputEnd"},
    }


def test_send_key_times(connection: Mock) -> None:
    """Ensure a key can be sent several times with a custom command."""
    connection.recv.side_effect = [MS_CHANNEL_CONNECT_SAMPLE]
    tv = SamsungTVWS("127.0.0.1")
    tv.send_key("KEY_VOLUP", times=2, key_press_delay=0, cmd="Press")
    expected = json.dumps(
        {"method": "ms.remote.control", "params": _key_params("Press", "KEY_VOLUP")}
    )
    assert connection.send.call_args_list == [call(expected), call(expected)]


def test_move_cursor(connection: Mock) -> None:
    """Ensure moving the cursor sends a mouse command without delay."""
    connection.recv.side_effect = [MS_CHANNEL_CONNECT_SAMPLE]
    tv = SamsungTVWS("127.0.0.1")
    with patch("samsungtvws.connection.time.sleep") as mock_sleep:
        tv.move_cursor(10, 20, 5)

    connection.send.assert_called_once_with(
        '{"method": "ms.remote.control", "params": {'
        '"Cmd": "Move", '
        '"Position": {"x": 10, "y": 20, "Time": "5"}, '
        '"TypeOfRemote": "ProcessMouseDevice"'
        "}}"
    )
    mock_sleep.assert_called_once_with(0)


@pytest.mark.parametrize(
    ("args", "expected_data"),
    [
        pytest.param(
            ("111299001912",),
            {"action_type": "DEEP_LINK", "appId": "111299001912", "metaTag": ""},
            id="default",
        ),
        pytest.param(
            ("111299001912", "NATIVE_LAUNCH", "tag"),
            {"action_type": "NATIVE_LAUNCH", "appId": "111299001912", "metaTag": "tag"},
            id="native-launch",
        ),
    ],
)
def test_run_app(
    connection: Mock, args: tuple[str, ...], expected_data: dict[str, str]
) -> None:
    """Ensure running an app emits the launch event."""
    connection.recv.side_effect = [MS_CHANNEL_CONNECT_SAMPLE]
    tv = SamsungTVWS("127.0.0.1")
    tv.run_app(*args)
    connection.send.assert_called_once_with(
        json.dumps(
            {
                "method": "ms.channel.emit",
                "params": {
                    "event": "ed.apps.launch",
                    "to": "host",
                    "data": expected_data,
                },
            }
        )
    )


def test_open_browser(connection: Mock) -> None:
    """Ensure opening a URL launches the browser app."""
    connection.recv.side_effect = [MS_CHANNEL_CONNECT_SAMPLE]
    tv = SamsungTVWS("127.0.0.1")
    tv.open_browser("https://www.home-assistant.io")
    connection.send.assert_called_once_with(
        ChannelEmitCommand.launch_app(
            "org.tizen.browser", "NATIVE_LAUNCH", "https://www.home-assistant.io"
        ).get_payload()
    )


def test_app_list_while_listening(connection: Mock) -> None:
    """Ensure the app list is filled by the listening thread."""
    sent = threading.Event()

    def _recv() -> Iterator[str]:
        yield MS_CHANNEL_CONNECT_SAMPLE
        sent.wait(5)
        yield ED_INSTALLED_APP_SAMPLE
        yield ""

    messages = _recv()
    connection.recv.side_effect = lambda: next(messages)
    connection.send.side_effect = lambda payload: sent.set()
    received = threading.Event()
    tv = SamsungTVWS("127.0.0.1")
    tv.start_listening(lambda event, response: received.set())
    with patch("samsungtvws.remote.time.sleep", side_effect=lambda _: received.wait(5)):
        app_list = tv.app_list()
    tv.close()

    assert app_list is not None
    assert [app["name"] for app in app_list] == ["YouTube", "Deezer"]


def test_app_list_while_listening_no_reply(connection: Mock) -> None:
    """Ensure the app list gives up after ten attempts without a reply."""
    connection.recv.side_effect = [MS_CHANNEL_CONNECT_SAMPLE, ""]
    tv = SamsungTVWS("127.0.0.1", key_press_delay=0)
    tv.start_listening()
    with patch("samsungtvws.remote.time.sleep") as mock_sleep:
        assert tv.app_list() is None
    tv.close()

    # one key press delay after sending, then ten one-second polls
    assert mock_sleep.call_args_list == [call(0)] + [call(1)] * 10


def test_send_text(connection: Mock) -> None:
    """Ensure the text received broadcast is only sent before the first text."""
    connection.recv.side_effect = [MS_CHANNEL_CONNECT_SAMPLE]
    tv = SamsungTVWS("127.0.0.1")
    tv.send_text("")
    tv.send_text("hi")
    tv.send_text("hi")
    tv.end_text()
    tv.send_text("hi")

    assert [c.args[0] for c in connection.send.call_args_list] == [
        TEXT_RECEIVED_PAYLOAD,
        _input_payload("aGk="),
        _input_payload("aGk="),
        SendInputEnd().get_payload(),
        TEXT_RECEIVED_PAYLOAD,
        _input_payload("aGk="),
    ]


@pytest.mark.parametrize(
    "ime_event",
    [
        pytest.param(MS_REMOTE_IME_START_SAMPLE, id="ime-start"),
        pytest.param(MS_REMOTE_IME_END_SAMPLE, id="ime-end"),
    ],
)
def test_send_text_after_ime_event(connection: Mock, ime_event: str) -> None:
    """Ensure IME events make the next text resend the broadcast."""
    first_text_sent = threading.Event()

    def _recv() -> Iterator[str]:
        yield MS_CHANNEL_CONNECT_SAMPLE
        first_text_sent.wait(5)
        yield ime_event
        yield ""

    messages = _recv()
    connection.recv.side_effect = lambda: next(messages)
    received = threading.Event()
    tv = SamsungTVWS("127.0.0.1")
    tv.start_listening(lambda event, response: received.set())
    tv.send_text("hi")
    first_text_sent.set()
    assert received.wait(5)
    tv.send_text("hi")
    tv.close()

    assert [c.args[0] for c in connection.send.call_args_list] == [
        TEXT_RECEIVED_PAYLOAD,
        _input_payload("aGk="),
        TEXT_RECEIVED_PAYLOAD,
        _input_payload("aGk="),
    ]


def test_send_password() -> None:
    """Ensure the password is sent through the REST IME endpoint with the token."""
    tv = SamsungTVWS("127.0.0.1", token="abc", port=8002)
    with patch(
        "samsungtvws.rest.requests.post", return_value=Mock(status_code=200)
    ) as mock_post:
        assert tv.send_password("secret") is True

    mock_post.assert_called_once_with(
        "https://127.0.0.1:8002/api/v2/remoteControl/imeInput/c2VjcmV0?token=abc",
        timeout=None,
        verify=False,
    )


def test_rest_device_info() -> None:
    """Ensure device info is fetched through the REST API."""
    tv = SamsungTVWS("127.0.0.1", timeout=5)
    with patch(
        "samsungtvws.rest.requests.get",
        return_value=Mock(text=REST_DEVICE_INFO_SAMPLE),
    ) as mock_get:
        info = tv.rest_device_info()
        tv.rest_device_info()

    assert info["device"]["modelName"] == "QE55Q60TAU"
    assert mock_get.call_args_list == [
        call("http://127.0.0.1:8001/api/v2/", timeout=5, verify=False),
        call("http://127.0.0.1:8001/api/v2/", timeout=5, verify=False),
    ]


@pytest.mark.parametrize(
    ("method", "http_method"),
    [
        pytest.param("rest_app_status", "get", id="status"),
        pytest.param("rest_app_run", "post", id="run"),
        pytest.param("rest_app_close", "delete", id="close"),
        pytest.param("rest_app_install", "put", id="install"),
    ],
)
def test_rest_app(method: str, http_method: str) -> None:
    """Ensure app actions use the matching REST call."""
    tv = SamsungTVWS("127.0.0.1")
    with patch(
        f"samsungtvws.rest.requests.{http_method}",
        return_value=Mock(text='{"id": "111299001912", "running": true}'),
    ) as mock_request:
        result: dict[str, Any] = getattr(tv, method)("111299001912")

    assert result == {"id": "111299001912", "running": True}
    mock_request.assert_called_once_with(
        "http://127.0.0.1:8001/api/v2/applications/111299001912",
        timeout=None,
        verify=False,
    )


def test_shortcuts(connection: Mock) -> None:
    """Ensure shortcuts send keys through this remote."""
    connection.recv.side_effect = [MS_CHANNEL_CONNECT_SAMPLE]
    tv = SamsungTVWS("127.0.0.1")
    shortcuts = tv.shortcuts()
    assert isinstance(shortcuts, SamsungTVShortcuts)
    shortcuts.power()
    connection.send.assert_called_once_with(SendRemoteKey.power().get_payload())


def test_art() -> None:
    """Ensure the art client inherits the remote settings."""
    tv = SamsungTVWS(
        "127.0.0.1", token="abc", port=8002, timeout=5, key_press_delay=2, name="Test"
    )
    art = tv.art()
    assert isinstance(art, SamsungTVArt)
    assert (art.host, art.token, art.port, art.timeout, art.key_press_delay) == (
        "127.0.0.1",
        "abc",
        8002,
        5,
        2,
    )
    assert art.name == "Test"
