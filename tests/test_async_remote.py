"""Tests for remote module."""

import asyncio
from unittest.mock import Mock, call, patch

import pytest

from samsungtvws.async_remote import SamsungTVWSAsyncRemote
from samsungtvws.exceptions import ConnectionFailure
from samsungtvws.remote import SendRemoteKey

from .const import (
    ED_APPS_LAUNCH_SAMPLE,
    ED_EDENTV_UPDATE_SAMPLE,
    ED_INSTALLED_APP_SAMPLE,
    MS_CHANNEL_CONNECT_SAMPLE,
    MS_ERROR_SAMPLE,
    MS_VOICEAPP_HIDE_SAMPLE,
)


def create_future_with_result(result) -> asyncio.Future:
    future = asyncio.Future()
    future.set_result(result)
    return future


ED_APPS_LAUNCH_FUTURE = create_future_with_result(ED_APPS_LAUNCH_SAMPLE)
ED_EDENTV_UPDATE_FUTURE = create_future_with_result(ED_EDENTV_UPDATE_SAMPLE)
ED_INSTALLED_APP_FUTURE = create_future_with_result(ED_INSTALLED_APP_SAMPLE)
MS_CHANNEL_CONNECT_FUTURE = create_future_with_result(MS_CHANNEL_CONNECT_SAMPLE)
MS_ERROR_EVENT_FUTURE = create_future_with_result(MS_ERROR_SAMPLE)
MS_VOICEAPP_HIDE_FUTURE = create_future_with_result(MS_VOICEAPP_HIDE_SAMPLE)
NONE_FUTURE = create_future_with_result(None)


@pytest.mark.asyncio
async def test_connect(async_connection: Mock) -> None:
    """Ensure simple data can be parsed."""
    async_connection.recv = Mock(side_effect=[MS_CHANNEL_CONNECT_FUTURE])
    async_connection.send = Mock(return_value=NONE_FUTURE)
    tv = SamsungTVWSAsyncRemote("127.0.0.1")
    await tv.start_listening()
    assert tv.token == 123456789


@pytest.mark.asyncio
async def test_connect_with_extra_event(async_connection: Mock) -> None:
    """Ensure simple data can be parsed."""
    async_connection.recv = Mock(
        side_effect=[
            MS_VOICEAPP_HIDE_FUTURE,
            ED_EDENTV_UPDATE_FUTURE,
            MS_CHANNEL_CONNECT_FUTURE,
        ]
    )
    async_connection.send = Mock(return_value=NONE_FUTURE)
    tv = SamsungTVWSAsyncRemote("127.0.0.1")
    await tv.start_listening()
    assert tv.token == 123456789


@pytest.mark.asyncio
async def test_connection_failure(async_connection: Mock) -> None:
    """Ensure simple data can be parsed."""
    async_connection.recv = Mock(side_effect=[MS_ERROR_EVENT_FUTURE])
    async_connection.send = Mock(return_value=NONE_FUTURE)
    tv = SamsungTVWSAsyncRemote("127.0.0.1")
    with pytest.raises(ConnectionFailure):
        await tv.start_listening()


@pytest.mark.asyncio
async def test_send_key(async_connection: Mock) -> None:
    """Ensure simple data can be parsed."""
    async_connection.recv = Mock(side_effect=[MS_CHANNEL_CONNECT_FUTURE])
    async_connection.send = Mock(return_value=NONE_FUTURE)
    tv = SamsungTVWSAsyncRemote("127.0.0.1")
    await tv.send_command(SendRemoteKey.click("KEY_POWER"))
    async_connection.send.assert_called_once_with(
        '{"method": "ms.remote.control", "params": {'
        '"Cmd": "Click", '
        '"DataOfCmd": "KEY_POWER", '
        '"Option": "false", '
        '"TypeOfRemote": "SendRemoteKey"'
        "}}"
    )


@pytest.mark.asyncio
async def test_app_list(async_connection: Mock) -> None:
    """Ensure valid app_list data can be parsed."""
    async_connection.recv = Mock(
        side_effect=[
            MS_CHANNEL_CONNECT_FUTURE,
            ED_INSTALLED_APP_FUTURE,
        ]
    )
    async_connection.send = Mock(return_value=NONE_FUTURE)
    tv = SamsungTVWSAsyncRemote("127.0.0.1")
    await tv.start_listening()
    assert await tv.app_list() == [
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


@pytest.mark.asyncio
async def test_app_list_bad_order(async_connection: Mock) -> None:
    """Ensure valid app_list data can be parsed, even if we get events in the wrong order."""
    async_connection.recv = Mock(
        side_effect=[
            MS_CHANNEL_CONNECT_FUTURE,
            ED_APPS_LAUNCH_FUTURE,
            ED_INSTALLED_APP_FUTURE,
        ]
    )
    async_connection.send = Mock(return_value=NONE_FUTURE)
    tv = SamsungTVWSAsyncRemote("127.0.0.1")
    await tv.start_listening()
    assert await tv.app_list() == [
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


@pytest.mark.asyncio
async def test_send_hold_key(async_connection: Mock) -> None:
    """Ensure simple data can be parsed."""
    async_connection.recv = Mock(side_effect=[MS_CHANNEL_CONNECT_FUTURE])
    async_connection.send = Mock(return_value=NONE_FUTURE)

    tv = SamsungTVWSAsyncRemote("127.0.0.1")
    with patch(
        "samsungtvws.async_connection.asyncio.sleep", return_value=NONE_FUTURE
    ) as patch_sleep:
        await tv.send_command(SendRemoteKey.hold("KEY_POWER", 3))

    assert patch_sleep.call_count == 3
    assert patch_sleep.call_args_list == [call(1), call(3), call(1)]
