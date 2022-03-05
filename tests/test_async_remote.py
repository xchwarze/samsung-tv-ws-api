"""Tests for remote module."""
import asyncio
from unittest.mock import Mock, call, patch

import pytest

from samsungtvws.async_remote import SamsungTVWSAsyncRemote
from samsungtvws.remote import SendRemoteKey


@pytest.mark.asyncio
async def test_send_key(async_connection: Mock) -> None:
    """Ensure simple data can be parsed."""
    open_response = (
        '{"data": {"token": 123456789}, "event": "ms.channel.connect", "from": "host"}'
    )
    open_response_future = asyncio.Future()
    open_response_future.set_result(open_response)

    send_command_future = asyncio.Future()
    send_command_future.set_result(None)

    async_connection.recv = Mock(side_effect=[open_response_future])
    async_connection.send = Mock(return_value=send_command_future)
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
async def test_send_hold_key(async_connection: Mock) -> None:
    """Ensure simple data can be parsed."""
    open_response = (
        '{"data": {"token": 123456789}, "event": "ms.channel.connect", "from": "host"}'
    )
    open_response_future = asyncio.Future()
    open_response_future.set_result(open_response)

    send_command_future = asyncio.Future()
    send_command_future.set_result(None)

    async_connection.recv = Mock(side_effect=[open_response_future])
    async_connection.send = Mock(return_value=send_command_future)

    sleep_future = asyncio.Future()
    sleep_future.set_result(None)

    tv = SamsungTVWSAsyncRemote("127.0.0.1")
    with patch(
        "samsungtvws.async_connection.asyncio.sleep", return_value=sleep_future
    ) as patch_sleep:
        await tv.send_command(SendRemoteKey.hold_key("KEY_POWER", 3))

    assert patch_sleep.call_count == 3
    assert patch_sleep.call_args_list == [call(1), call(3), call(1)]
