"""Tests for art module."""

import json
from unittest.mock import Mock, patch

import pytest

from samsungtvws import exceptions
from samsungtvws.art import SamsungTVArt
from samsungtvws.remote import SamsungTVWS

from .const import (
    D2D_SERVICE_MESSAGE_AVAILABLE_SAMPLE,
    D2D_SERVICE_MESSAGE_IMAGE_ADDED_SAMPLE,
    D2D_SERVICE_MESSAGE_OK_SAMPLE,
    D2D_SERVICE_MESSAGE_READY_TO_USE_SAMPLE,
    D2D_SERVICE_MESSAGE_SEND_IMAGE_ERROR,
    D2D_SERVICE_MESSAGE_THUMBNAIL_INLINE_SAMPLE,
    MS_CHANNEL_CONNECT_SAMPLE,
    MS_CHANNEL_READY_SAMPLE,
)

_UUID = "07e72228-7110-4655-aaa6-d81b5188c219"


def test_create_connection_from_remote() -> None:
    connection = Mock()
    with (
        patch("samsungtvws.art.art.uuid.uuid4", return_value=_UUID),
        patch("samsungtvws.connection.websocket.create_connection") as connection_class,
    ):
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
    with (
        patch("samsungtvws.art.art.uuid.uuid4", return_value=_UUID),
        patch("samsungtvws.connection.websocket.create_connection") as connection_class,
    ):
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
    with patch("samsungtvws.art.art.uuid.uuid4", return_value=_UUID):
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
    with patch("samsungtvws.art.art.uuid.uuid4", return_value=_UUID):
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
    with patch("samsungtvws.art.art.uuid.uuid4", return_value=_UUID):
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
    with (
        patch("samsungtvws.art.art.uuid.uuid4", return_value=_UUID),
        patch("samsungtvws.helper.random.randrange", return_value=4091151321),
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
            tv_art.upload(
                b"", file_type="png", matte="none", date="2023:05:02 15:06:39"
            )

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


def test_send_image_success_sends_binary_frame(connection: Mock) -> None:
    """Ensure upload sends header+bytes over D2D socket and returns content_id."""
    file_bytes = b"\x89PNG\r\n\x1a\nFAKEPNGDATA"

    sock = Mock()
    with (
        patch("samsungtvws.art.art.uuid.uuid4", return_value=_UUID),
        patch("samsungtvws.helper.random.randrange", return_value=4091151321),
        patch.object(
            SamsungTVArt,
            "_open_d2d_socket",
            return_value=sock,
        ),
    ):
        # recv order:
        # - connect + ready (open())
        # - ready_to_use (send_image handshake)
        # - send_image (progress / intermediate ack)
        # - image_added (final ack)
        connection.recv.side_effect = [
            MS_CHANNEL_CONNECT_SAMPLE,
            MS_CHANNEL_READY_SAMPLE,
            D2D_SERVICE_MESSAGE_READY_TO_USE_SAMPLE,
            D2D_SERVICE_MESSAGE_IMAGE_ADDED_SAMPLE,
            D2D_SERVICE_MESSAGE_IMAGE_ADDED_SAMPLE,
        ]

        tv_art = SamsungTVArt("127.0.0.1")
        content_id = tv_art.upload(
            file_bytes, file_type="png", matte="none", date="2023:05:02 15:06:39"
        )

        assert content_id == "MY_F0001"

        # Validate D2D send sequence: len(header) + header + data
        assert sock.sendall.call_count == 3

        header_len_bytes = sock.sendall.call_args_list[0].args[0]
        header_bytes = sock.sendall.call_args_list[1].args[0]
        data_bytes = sock.sendall.call_args_list[2].args[0]

        assert isinstance(header_len_bytes, (bytes, bytearray))
        assert isinstance(header_bytes, (bytes, bytearray))
        assert data_bytes == file_bytes

        header_len = int.from_bytes(header_len_bytes, "big")
        assert header_len == len(header_bytes)

        header = json.loads(header_bytes.decode("ascii"))
        assert header["fileType"] == "png"
        assert header["fileLength"] == len(file_bytes)
        assert header["secKey"] == "TESTKEY"


def test_get_thumbnail_inline_binary_skips_socket(connection: Mock) -> None:
    """Art API 0.97: thumbnail is returned inline as WS bytes (JSON + \\n + JPEG)."""
    with patch("samsungtvws.art.art.uuid.uuid4", return_value=_UUID):
        connection.recv.side_effect = [
            MS_CHANNEL_CONNECT_SAMPLE,
            MS_CHANNEL_READY_SAMPLE,
            D2D_SERVICE_MESSAGE_THUMBNAIL_INLINE_SAMPLE,
        ]

        tv_art = SamsungTVArt("127.0.0.1")

        with patch.object(SamsungTVArt, "_open_d2d_socket") as open_sock:
            thumb = tv_art.get_thumbnail("MY_F0073")
            open_sock.assert_not_called()

        assert isinstance(thumb, bytearray)

        # Assert JPEG signature (SOI ... EOI)
        assert bytes(thumb).startswith(b"\xff\xd8")
        assert bytes(thumb).endswith(b"\xff\xd9")
