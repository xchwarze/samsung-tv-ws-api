import json

from samsungtvws import event
from samsungtvws.exceptions import MessageError

from .const import ED_INSTALLED_APP_SAMPLE, MS_ERROR_SAMPLE


def test_parse_installed_app() -> None:
    json_response = json.loads(ED_INSTALLED_APP_SAMPLE)
    assert event.parse_installed_app(json_response) == [
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


def test_parse_ms_error() -> None:
    json_response = json.loads(MS_ERROR_SAMPLE)
    error = event.parse_ms_error(json_response)
    assert isinstance(error, MessageError)
    assert str(error) == "unrecognized method value : ms.application.stop"
