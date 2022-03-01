from typing import Any, Dict, List, cast

from .exceptions import MessageError

ED_APPS_LAUNCH_EVENT = "ed.apps.launch"
ED_EDENTV_UPDATE_EVENT = "ed.edenTV.update"
ED_INSTALLED_APP_EVENT = "ed.installedApp.get"
MS_CHANNEL_CLIENT_CONNECT_EVENT = "ms.channel.clientConnect"
MS_CHANNEL_CLIENT_DISCONNECT_EVENT = "ms.channel.clientDisconnect"
MS_ERROR_EVENT = "ms.error"


def parse_installed_app(event: Dict[str, Any]) -> List[Dict[str, Any]]:
    assert event["event"] == ED_INSTALLED_APP_EVENT
    return cast(List[Dict[str, Any]], event["data"]["data"])


def parse_ms_error(event: Dict[str, Any]) -> MessageError:
    assert event["event"] == MS_ERROR_EVENT
    return MessageError(event["data"]["message"])
