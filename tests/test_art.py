"""Tests for art module."""

from unittest.mock import Mock, patch

import pytest
import json

from samsungtvws import exceptions
from samsungtvws.art import SamsungTVArt
from samsungtvws.remote import SamsungTVWS

from .const import (
    D2D_SERVICE_MESSAGE_AVAILABLE_SAMPLE,
    D2D_SERVICE_MESSAGE_OK_SAMPLE,
    D2D_SERVICE_MESSAGE_SEND_IMAGE_ERROR,
    MS_CHANNEL_CONNECT_SAMPLE,
    MS_CHANNEL_READY_SAMPLE,
)


_UUID = "07e72228-7110-4655-aaa6-d81b5188c219"


def test_create_connection_from_remote() -> None:
    connection = Mock()
    with patch("samsungtvws.art.uuid.uuid4", return_value=_UUID), patch(
        "samsungtvws.connection.websocket.create_connection"
    ) as connection_class:
        connection_class.return_value = connection
        connection.recv.side_effect = [
            MS_CHANNEL_CONNECT_SAMPLE,
            MS_CHANNEL_READY_SAMPLE,
            D2D_SERVICE_MESSAGE_OK_SAMPLE,
        ]

        tv_art = SamsungTVWS("127.0.0.1").art()
        tv_art.set_artmode(True)

        connection_class.assert_called_once_with(
            "ws://127.0.0.1:8001/api/v2/channels/com.samsung.art-app?name=U2Ftc3VuZ1R2UmVtb3Rl",
            None,
            sslopt={},
            connection="Connection: Upgrade",
        )


def test_create_connection_direct() -> None:
    connection = Mock()
    with patch("samsungtvws.art.uuid.uuid4", return_value=_UUID), patch(
        "samsungtvws.connection.websocket.create_connection"
    ) as connection_class:
        connection_class.return_value = connection
        connection.recv.side_effect = [
            MS_CHANNEL_CONNECT_SAMPLE,
            MS_CHANNEL_READY_SAMPLE,
            D2D_SERVICE_MESSAGE_OK_SAMPLE,
        ]

        tv_art = SamsungTVArt("127.0.0.1")
        tv_art.set_artmode(True)

        connection_class.assert_called_once_with(
            "ws://127.0.0.1:8001/api/v2/channels/com.samsung.art-app?name=U2Ftc3VuZ1R2UmVtb3Rl",
            None,
            sslopt={},
            connection="Connection: Upgrade",
        )


def test_set_artmode(connection: Mock) -> None:
    """Ensure simple data can be parsed."""
    with patch("samsungtvws.art.uuid.uuid4", return_value=_UUID):
        connection.recv.side_effect = [
            MS_CHANNEL_CONNECT_SAMPLE,
            MS_CHANNEL_READY_SAMPLE,
            D2D_SERVICE_MESSAGE_OK_SAMPLE,
        ]

        tv_art = SamsungTVArt("127.0.0.1")
        tv_art.set_artmode(True)

        connection.send.assert_called_once_with(
            '{"method": "ms.channel.emit", "params": {"event": "art_app_request", "to": "host", "data": "{\\"request\\": \\"set_artmode_status\\", \\"value\\": \\"on\\", \\"id\\": \\"07e72228-7110-4655-aaa6-d81b5188c219\\", \\"request_id\\": \\"07e72228-7110-4655-aaa6-d81b5188c219\\"}"}}'
        )


def test_set_available(connection: Mock) -> None:
    """Ensure simple data can be parsed."""
    with patch("samsungtvws.art.uuid.uuid4", return_value=_UUID):
        connection.recv.side_effect = [
            MS_CHANNEL_CONNECT_SAMPLE,
            MS_CHANNEL_READY_SAMPLE,
            D2D_SERVICE_MESSAGE_AVAILABLE_SAMPLE,
        ]

        tv_art = SamsungTVArt("127.0.0.1")
        tv_art.available()

        connection.send.assert_called_once_with(
            '{"method": "ms.channel.emit", "params": {"event": "art_app_request", "to": "host", "data": "{\\"request\\": \\"get_content_list\\", \\"category\\": null, \\"id\\": \\"07e72228-7110-4655-aaa6-d81b5188c219\\", \\"request_id\\": \\"07e72228-7110-4655-aaa6-d81b5188c219\\"}"}}'
        )


def test_change_matte(connection: Mock) -> None:
    with patch("samsungtvws.art.uuid.uuid4", return_value=_UUID):
        connection.recv.side_effect = [
            MS_CHANNEL_CONNECT_SAMPLE,
            MS_CHANNEL_READY_SAMPLE,
            D2D_SERVICE_MESSAGE_OK_SAMPLE,
        ]

        tv_art = SamsungTVArt("127.0.0.1")
        tv_art.change_matte("test", "none")

        connection.send.assert_called_once_with(
            '{"method": "ms.channel.emit", "params": {"event": "art_app_request", "to": "host", "data": "{\\"request\\": \\"change_matte\\", \\"content_id\\": \\"test\\", \\"matte_id\\": \\"none\\", \\"id\\": \\"07e72228-7110-4655-aaa6-d81b5188c219\\", \\"request_id\\": \\"07e72228-7110-4655-aaa6-d81b5188c219\\"}"}}'
        )


def test_send_image_failure(connection: Mock) -> None:
    """Ensure send_image failure raises error and doesn't hang indefinitely."""
    with patch("samsungtvws.art.uuid.uuid4", return_value=_UUID), patch(
        "samsungtvws.helper.random.randrange", return_value=4091151321
    ):
        connection.recv.side_effect = [
            MS_CHANNEL_CONNECT_SAMPLE,
            MS_CHANNEL_READY_SAMPLE,
            D2D_SERVICE_MESSAGE_SEND_IMAGE_ERROR,
        ]

        tv_art = SamsungTVArt("127.0.0.1")

        with pytest.raises(
            exceptions.ResponseError,
            match=r"`send_image` request failed with error number -1",
        ):
            tv_art.upload(b"", file_type="png", matte="none", date="2023:05:02 15:06:39")

        # Assert structurally, not via exact string match
        assert connection.send.call_count == 1
        sent = connection.send.call_args.args[0]

        outer = json.loads(sent)
        assert outer["method"] == "ms.channel.emit"

        params = outer["params"]
        assert params["event"] == "art_app_request"
        assert params["to"] == "host"

        inner = json.loads(params["data"])
        assert inner["request"] == "send_image"
        assert inner["file_type"] == "png"
        assert inner["request_id"] == str(_UUID)

        assert inner["conn_info"] == {
            "d2d_mode": "socket",
            "connection_id": 4091151321,
            "id": str(_UUID),
        }

        assert inner["image_date"] == "2023:05:02 15:06:39"
        assert inner["matte_id"] == "none"
        assert inner["file_size"] == 0
        assert inner["id"] == str(_UUID)
        assert inner["portrait_matte_id"] == "shadowbox_polar"

