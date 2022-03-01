import json

from samsungtvws import event
from samsungtvws.exceptions import MessageError


def test_parse_installed_app() -> None:
    with open("tests/fixtures/event_ed_installedApp_get.json") as file:
        json_response = json.load(file)
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
    with open("tests/fixtures/event_ms_error.json") as file:
        json_response = json.load(file)
    error = event.parse_ms_error(json_response)
    assert isinstance(error, MessageError)
    assert str(error) == "unrecognized method value : ms.application.stop"
