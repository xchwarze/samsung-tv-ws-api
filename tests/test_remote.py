"""Tests for remote module."""
from unittest.mock import Mock

from samsungtvws.remote import SamsungTVWS


def test_send_key(connection: Mock) -> None:
    """Ensure simple data can be parsed."""
    open_response = (
        '{"data": {"token": 123456789}, "event": "ms.channel.connect", "from": "host"}'
    )

    connection.recv.side_effect = [open_response]
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
    open_response = (
        '{"data": {"token": 123456789}, "event": "ms.channel.connect", "from": "host"}'
    )
    app_list_response = '{"data":{"data":[{"appId":"111299001912","app_type":2,"icon":"/opt/share/webappservice/apps_icon/FirstScreen/111299001912/250x250.png","is_lock":0,"name":"YouTube"},{"appId":"3201608010191","app_type":2,"icon":"/opt/share/webappservice/apps_icon/FirstScreen/3201608010191/250x250.png","is_lock":0,"name":"Deezer"}]},"event":"ed.installedApp.get","from":"host"}'

    connection.recv.side_effect = [open_response, app_list_response]
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
    open_response = (
        '{"data": {"token": 123456789}, "event": "ms.channel.connect", "from": "host"}'
    )
    app_list_response = '{"data": 200, "event": "ed.apps.launch", "from": "host"}'

    connection.recv.side_effect = [open_response, app_list_response]
    tv = SamsungTVWS("127.0.0.1")
    assert tv.app_list() is None
    connection.send.assert_called_once_with(
        '{"method": "ms.channel.emit", "params": {"event": "ed.installedApp.get", "to": "host"}}'
    )
