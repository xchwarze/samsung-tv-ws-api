"""
SamsungTVWS - Samsung Smart TV WS API wrapper

Copyright (C) 2019 DSR! <xchwarze@gmail.com>

SPDX-License-Identifier: LGPL-3.0
"""

from typing import Any, Dict, List

from .exceptions import MessageError

D2D_SERVICE_MESSAGE_EVENT = "d2d_service_message"
ED_APPS_LAUNCH_EVENT = "ed.apps.launch"
ED_EDENTV_UPDATE_EVENT = "ed.edenTV.update"
ED_INSTALLED_APP_EVENT = "ed.installedApp.get"
MS_CHANNEL_CONNECT_EVENT = "ms.channel.connect"
MS_CHANNEL_CLIENT_CONNECT_EVENT = "ms.channel.clientConnect"
MS_CHANNEL_CLIENT_DISCONNECT_EVENT = "ms.channel.clientDisconnect"
MS_CHANNEL_READY_EVENT = "ms.channel.ready"
MS_CHANNEL_UNAUTHORIZED = "ms.channel.unauthorized"
MS_ERROR_EVENT = "ms.error"
MS_VOICEAPP_HIDE_EVENT = "ms.voiceApp.hide"

IGNORE_EVENTS_AT_STARTUP = (ED_EDENTV_UPDATE_EVENT, MS_VOICEAPP_HIDE_EVENT)


def parse_installed_app(event: Dict[str, Any]) -> List[Dict[str, Any]]:
    assert event["event"] == ED_INSTALLED_APP_EVENT
    return event["data"]["data"]  # type:ignore[no-any-return]


def parse_ms_error(event: Dict[str, Any]) -> MessageError:
    assert event["event"] == MS_ERROR_EVENT
    return MessageError(event["data"]["message"])
