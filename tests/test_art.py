"""Tests for art module."""

from unittest.mock import Mock, patch

import pytest

from samsungtvws import exceptions
from samsungtvws.art import SamsungTVArt
from samsungtvws.remote import SamsungTVWS

from .const import (
    D2D_SERVICE_MESSAGE_AVAILABLE_SAMPLE,
    D2D_SERVICE_MESSAGE_SEND_IMAGE_ERROR,
    MS_CHANNEL_CONNECT_SAMPLE,
    MS_CHANNEL_DISCONNECT_SAMPLE,
    MS_CHANNEL_READY_SAMPLE,
)


def test_create_connection_from_remote() -> None:
    connection = Mock()
    with patch(
        "samsungtvws.connection.websocket.create_connection"
    ) as connection_class:
        connection_class.return_value = connection
        connection.recv.side_effect = [
            MS_CHANNEL_CONNECT_SAMPLE,
            MS_CHANNEL_READY_SAMPLE,
        ]

        tv_art = SamsungTVWS("127.0.0.1").art()
        tv_art.set_artmode("test")

        connection_class.assert_called_once_with(
            "ws://127.0.0.1:8001/api/v2/channels/com.samsung.art-app?name=U2Ftc3VuZ1R2UmVtb3Rl",
            None,
            sslopt={},
            connection="Connection: Upgrade",
        )


def test_create_connection_direct() -> None:
    connection = Mock()
    with patch(
        "samsungtvws.connection.websocket.create_connection"
    ) as connection_class:
        connection_class.return_value = connection
        connection.recv.side_effect = [
            MS_CHANNEL_CONNECT_SAMPLE,
            MS_CHANNEL_READY_SAMPLE,
        ]

        tv_art = SamsungTVArt("127.0.0.1")
        tv_art.set_artmode("test")

        connection_class.assert_called_once_with(
            "ws://127.0.0.1:8001/api/v2/channels/com.samsung.art-app?name=U2Ftc3VuZ1R2UmVtb3Rl",
            None,
            sslopt={},
            connection="Connection: Upgrade",
        )


def test_set_artmode(connection: Mock) -> None:
    """Ensure simple data can be parsed."""
    with patch(
        "samsungtvws.art.uuid.uuid4",
        return_value="07e72228-7110-4655-aaa6-d81b5188c219",
    ):
        connection.recv.side_effect = [
            MS_CHANNEL_CONNECT_SAMPLE,
            MS_CHANNEL_READY_SAMPLE,
        ]
        tv_art = SamsungTVArt("127.0.0.1")
        tv_art.set_artmode("test")

        connection.send.assert_called_once_with(
            '{"method": "ms.channel.emit", "params": {"event": "art_app_request", "to": "host", "data": "{\\"request\\": \\"set_artmode_status\\", \\"value\\": \\"test\\", \\"id\\": \\"07e72228-7110-4655-aaa6-d81b5188c219\\"}"}}'
        )


def test_set_available(connection: Mock) -> None:
    """Ensure simple data can be parsed."""
    with patch(
        "samsungtvws.art.uuid.uuid4",
        return_value="07e72228-7110-4655-aaa6-d81b5188c219",
    ):
        connection.recv.side_effect = [
            MS_CHANNEL_CONNECT_SAMPLE,
            MS_CHANNEL_READY_SAMPLE,
            MS_CHANNEL_DISCONNECT_SAMPLE,
            D2D_SERVICE_MESSAGE_AVAILABLE_SAMPLE,
        ]
        tv_art = SamsungTVArt("127.0.0.1")
        tv_art.available()

        connection.send.assert_called_once_with(
            '{"method": "ms.channel.emit", "params": {"event": "art_app_request", "to": "host", "data": "{\\"request\\": \\"get_content_list\\", \\"category\\": null, \\"id\\": \\"07e72228-7110-4655-aaa6-d81b5188c219\\"}"}}'
        )


def test_change_matte(connection: Mock) -> None:
    with patch(
        "samsungtvws.art.uuid.uuid4",
        return_value="07e72228-7110-4655-aaa6-d81b5188c219",
    ):
        connection.recv.side_effect = [
            MS_CHANNEL_CONNECT_SAMPLE,
            MS_CHANNEL_READY_SAMPLE,
            D2D_SERVICE_MESSAGE_AVAILABLE_SAMPLE,
        ]
        tv_art = SamsungTVArt("127.0.0.1")
        tv_art.change_matte("test", "none")

        connection.send.assert_called_once_with(
            '{"method": "ms.channel.emit", "params": {"event": "art_app_request", "to": "host", "data": "{\\"request\\": \\"change_matte\\", \\"content_id\\": \\"test\\", \\"matte_id\\": \\"none\\", \\"id\\": \\"07e72228-7110-4655-aaa6-d81b5188c219\\"}"}}'
        )


def test_send_image_failure(connection: Mock) -> None:
    """Ensure send_image failure raises error and doesn't hang indefinitely."""
    with patch(
        "samsungtvws.art.uuid.uuid4",
        return_value="07e72228-7110-4655-aaa6-d81b5188c219",
    ), patch("samsungtvws.art.random.randrange", return_value=4091151321):
        connection.recv.side_effect = [
            MS_CHANNEL_CONNECT_SAMPLE,
            MS_CHANNEL_READY_SAMPLE,
            D2D_SERVICE_MESSAGE_SEND_IMAGE_ERROR,
        ]
        tv_art = SamsungTVArt("127.0.0.1")

        with pytest.raises(
            exceptions.ResponseError,
            match="`send_image` request failed with error number -1",
        ):
            tv_art.upload(
                b"", file_type="png", matte="none", date="2023:05:02 15:06:39"
            )

        connection.send.assert_called_once_with(
            '{"method": "ms.channel.emit", "params": {"event": "art_app_request", "to": "host", "data": "{\\"request\\": \\"send_image\\", \\"file_type\\": \\"png\\", \\"conn_info\\": {\\"d2d_mode\\": \\"socket\\", \\"connection_id\\": 4091151321, \\"id\\": \\"07e72228-7110-4655-aaa6-d81b5188c219\\"}, \\"image_date\\": \\"2023:05:02 15:06:39\\", \\"matte_id\\": \\"none\\", \\"file_size\\": 0, \\"id\\": \\"07e72228-7110-4655-aaa6-d81b5188c219\\"}"}}'
        )
