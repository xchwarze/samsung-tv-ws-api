"""
SamsungTVWS - Samsung Smart TV WS API wrapper

Copyright (C) 2019 DSR! <xchwarze@gmail.com>

SPDX-License-Identifier: LGPL-3.0
"""

import logging
import time
from typing import Any, Dict, List, Optional, Union
import warnings

from samsungtvws.event import ED_INSTALLED_APP_EVENT, parse_installed_app

from . import art, connection, helper, rest, shortcuts
from .command import SamsungTVCommand, SamsungTVSleepCommand

_LOGGING = logging.getLogger(__name__)

REMOTE_ENDPOINT = "samsung.remote.control"


class RemoteControlCommand(SamsungTVCommand):
    def __init__(self, params: Dict[str, Any]) -> None:
        super().__init__("ms.remote.control", params)


class ChannelEmitCommand(SamsungTVCommand):
    def __init__(self, params: Dict[str, Any]) -> None:
        super().__init__("ms.channel.emit", params)

    @staticmethod
    def get_installed_app() -> "ChannelEmitCommand":
        return ChannelEmitCommand(
            {
                "event": "ed.installedApp.get",
                "to": "host",
            }
        )

    @staticmethod
    def launch_app(
        app_id: str, app_type: str = "DEEP_LINK", meta_tag: str = ""
    ) -> "ChannelEmitCommand":
        return ChannelEmitCommand(
            {
                "event": "ed.apps.launch",
                "to": "host",
                "data": {
                    # action_type: NATIVE_LAUNCH / DEEP_LINK
                    # app_type == 2 ? 'DEEP_LINK' : 'NATIVE_LAUNCH',
                    "action_type": app_type,
                    "appId": app_id,
                    "metaTag": meta_tag,
                },
            }
        )


class SendRemoteKey(RemoteControlCommand):
    @staticmethod
    def click(key: str) -> "SendRemoteKey":
        return SendRemoteKey(
            {
                "Cmd": "Click",
                "DataOfCmd": key,
                "Option": "false",
                "TypeOfRemote": "SendRemoteKey",
            }
        )

    @staticmethod
    def press(key: str) -> "SendRemoteKey":
        return SendRemoteKey(
            {
                "Cmd": "Press",
                "DataOfCmd": key,
                "Option": "false",
                "TypeOfRemote": "SendRemoteKey",
            }
        )

    @staticmethod
    def release(key: str) -> "SendRemoteKey":
        return SendRemoteKey(
            {
                "Cmd": "Release",
                "DataOfCmd": key,
                "Option": "false",
                "TypeOfRemote": "SendRemoteKey",
            }
        )

    @staticmethod
    def hold(key: str, seconds: float) -> List["SamsungTVCommand"]:
        return [
            SendRemoteKey.press(key),
            SamsungTVSleepCommand(seconds),
            SendRemoteKey.release(key),
        ]

    @staticmethod
    def hold_key(key: str, seconds: float) -> List["SamsungTVCommand"]:
        warnings.warn(
            "SendRemoteKey.hold_key is deprecated, please use SendRemoteKey.hold instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return SendRemoteKey.hold(key, seconds)

    # power
    @staticmethod
    def power() -> "SendRemoteKey":
        return SendRemoteKey.click("KEY_POWER")

    # menu
    @staticmethod
    def home() -> "SendRemoteKey":
        return SendRemoteKey.click("KEY_HOME")

    @staticmethod
    def menu() -> "SendRemoteKey":
        return SendRemoteKey.click("KEY_MENU")

    @staticmethod
    def source() -> "SendRemoteKey":
        return SendRemoteKey.click("KEY_SOURCE")

    @staticmethod
    def guide() -> "SendRemoteKey":
        return SendRemoteKey.click("KEY_GUIDE")

    @staticmethod
    def tools() -> "SendRemoteKey":
        return SendRemoteKey.click("KEY_TOOLS")

    @staticmethod
    def info() -> "SendRemoteKey":
        return SendRemoteKey.click("KEY_INFO")

    # navigation
    @staticmethod
    def up() -> "SendRemoteKey":
        return SendRemoteKey.click("KEY_UP")

    @staticmethod
    def down() -> "SendRemoteKey":
        return SendRemoteKey.click("KEY_DOWN")

    @staticmethod
    def left() -> "SendRemoteKey":
        return SendRemoteKey.click("KEY_LEFT")

    @staticmethod
    def right() -> "SendRemoteKey":
        return SendRemoteKey.click("KEY_RIGHT")

    @staticmethod
    def enter() -> "SendRemoteKey":
        return SendRemoteKey.click("KEY_ENTER")

    @staticmethod
    def back() -> "SendRemoteKey":
        return SendRemoteKey.click("KEY_RETURN")

    # channel
    @staticmethod
    def channel_list() -> "SendRemoteKey":
        return SendRemoteKey.click("KEY_CH_LIST")

    @staticmethod
    def digit(d: int) -> "SendRemoteKey":
        return SendRemoteKey.click(f"KEY_{d}")

    @staticmethod
    def channel_up() -> "SendRemoteKey":
        return SendRemoteKey.click("KEY_CHUP")

    @staticmethod
    def channel_down() -> "SendRemoteKey":
        return SendRemoteKey.click("KEY_CHDOWN")

    # volume
    @staticmethod
    def volume_up() -> "SendRemoteKey":
        return SendRemoteKey.click("KEY_VOLUP")

    @staticmethod
    def volume_down() -> "SendRemoteKey":
        return SendRemoteKey.click("KEY_VOLDOWN")

    @staticmethod
    def mute() -> "SendRemoteKey":
        return SendRemoteKey.click("KEY_MUTE")

    # extra
    @staticmethod
    def red() -> "SendRemoteKey":
        return SendRemoteKey.click("KEY_RED")

    @staticmethod
    def green() -> "SendRemoteKey":
        return SendRemoteKey.click("KEY_GREEN")

    @staticmethod
    def yellow() -> "SendRemoteKey":
        return SendRemoteKey.click("KEY_YELLOW")

    @staticmethod
    def blue() -> "SendRemoteKey":
        return SendRemoteKey.click("KEY_BLUE")

    @staticmethod
    def factory() -> "SendRemoteKey":
        return SendRemoteKey.click("KEY_FACTORY")


class SamsungTVWS(connection.SamsungTVWSConnection):
    def __init__(
        self,
        host: str,
        token: Optional[str] = None,
        token_file: Optional[str] = None,
        port: int = 8001,
        timeout: Optional[float] = None,
        key_press_delay: float = 1,
        name: str = "SamsungTvRemote",
    ) -> None:
        super().__init__(
            host,
            endpoint=REMOTE_ENDPOINT,
            token=token,
            token_file=token_file,
            port=port,
            timeout=timeout,
            key_press_delay=key_press_delay,
            name=name,
        )
        self._rest_api: Optional[rest.SamsungTVRest] = None
        self._app_list: Optional[List[Dict[str, Any]]] = None

    def _ws_send(
        self,
        command: Union[SamsungTVCommand, Dict[str, Any]],
        key_press_delay: Optional[float] = None,
    ) -> None:
        return super().send_command(command, key_press_delay)

    def _websocket_event(self, event: str, response: Dict[str, Any]) -> None:
        """Handle websocket event."""
        super()._websocket_event(event, response)
        if event == ED_INSTALLED_APP_EVENT:
            self._app_list = parse_installed_app(response)

    def send_key(
        self,
        key: str,
        times: int = 1,
        key_press_delay: Optional[float] = None,
        cmd: str = "Click",
    ) -> None:
        for _ in range(times):
            _LOGGING.debug("Sending key %s", key)
            self._ws_send(
                RemoteControlCommand(
                    {
                        "Cmd": cmd,
                        "DataOfCmd": key,
                        "Option": "false",
                        "TypeOfRemote": "SendRemoteKey",
                    }
                ),
                key_press_delay,
            )

    def hold_key(self, key: str, seconds: float) -> None:
        self.send_command(SendRemoteKey.hold(key, seconds))

    def move_cursor(self, x: int, y: int, duration: int = 0) -> None:
        self._ws_send(
            RemoteControlCommand(
                {
                    "Cmd": "Move",
                    "Position": {"x": x, "y": y, "Time": str(duration)},
                    "TypeOfRemote": "ProcessMouseDevice",
                }
            ),
            key_press_delay=0,
        )

    def run_app(
        self, app_id: str, app_type: str = "DEEP_LINK", meta_tag: str = ""
    ) -> None:
        _LOGGING.debug(
            "Sending run app app_id: %s app_type: %s meta_tag: %s",
            app_id,
            app_type,
            meta_tag,
        )
        self._ws_send(ChannelEmitCommand.launch_app(app_id, app_type, meta_tag))

    def open_browser(self, url: str) -> None:
        _LOGGING.debug("Opening url in browser %s", url)
        self.run_app("org.tizen.browser", "NATIVE_LAUNCH", url)

    def app_list(self) -> Optional[List[Dict[str, Any]]]:
        _LOGGING.debug("Get app list (not available on all TVs)")
        # See https://github.com/xchwarze/samsung-tv-ws-api/issues/23
        self._app_list = None
        self._ws_send(ChannelEmitCommand.get_installed_app())

        if self._recv_loop:
            attempts_left = 10
            while attempts_left and not self._app_list:
                time.sleep(1)
                attempts_left -= 1
        else:
            assert self.connection
            response = helper.process_api_response(self.connection.recv())
            if response.get("event") == ED_INSTALLED_APP_EVENT:
                self._app_list = parse_installed_app(response)
            else:
                _LOGGING.debug("Failed to get app list: %s", response)

        return self._app_list

    def _get_rest_api(self) -> rest.SamsungTVRest:
        if self._rest_api is None:
            self._rest_api = rest.SamsungTVRest(self.host, self.port, self.timeout)
        return self._rest_api

    def rest_device_info(self) -> Dict[str, Any]:
        return self._get_rest_api().rest_device_info()

    def rest_app_status(self, app_id: str) -> Dict[str, Any]:
        return self._get_rest_api().rest_app_status(app_id)

    def rest_app_run(self, app_id: str) -> Dict[str, Any]:
        return self._get_rest_api().rest_app_run(app_id)

    def rest_app_close(self, app_id: str) -> Dict[str, Any]:
        return self._get_rest_api().rest_app_close(app_id)

    def rest_app_install(self, app_id: str) -> Dict[str, Any]:
        return self._get_rest_api().rest_app_install(app_id)

    def shortcuts(self) -> shortcuts.SamsungTVShortcuts:
        return shortcuts.SamsungTVShortcuts(self)

    def art(self) -> art.SamsungTVArt:
        return art.SamsungTVArt(
            self.host,
            token=self.token,
            token_file=self.token_file,
            port=self.port,
            timeout=self.timeout,
            key_press_delay=self.key_press_delay,
            name=self.name,
        )
