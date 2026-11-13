"""Tests for art module."""

from collections.abc import Iterator
import io
import json
from pathlib import Path
import re
from typing import Any
from unittest.mock import Mock, patch

import pytest
import websocket

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
_IDS = {"id": _UUID, "request_id": _UUID}
_CONN_INFO = {"ip": "192.168.1.20", "port": 12345, "key": "SECKEY"}


@pytest.fixture(name="mock_uuid")
def mock_uuid_fixture() -> Iterator[None]:
    """Make request ids deterministic."""
    with patch("samsungtvws.art.art.uuid.uuid4", return_value=_UUID):
        yield


@pytest.fixture(name="tv_art")
def tv_art_fixture(connection: Mock, mock_uuid: None) -> SamsungTVArt:
    """Return an art client backed by the mocked websocket."""
    return SamsungTVArt("127.0.0.1")


@pytest.fixture(name="d2d_socket")
def d2d_socket_fixture() -> Iterator[Mock]:
    """Mock the TCP socket used for D2D transfers."""
    with patch("samsungtvws.art.art.socket.socket") as socket_class:
        yield socket_class.return_value


def _d2d(payload: dict[str, Any], request_id: str = _UUID) -> str:
    """Build a d2d_service_message websocket frame."""
    data = {"id": request_id, "request_id": request_id, **payload}
    return json.dumps({"event": "d2d_service_message", "data": json.dumps(data)})


def _error(request_data: str | None = None, **extra: Any) -> str:
    """Build a d2d error frame."""
    payload: dict[str, Any] = {"event": "error", **extra}
    payload.update({"request_data": request_data} if request_data else {})
    return _d2d(payload)


def _respond(connection: Mock, *frames: Any) -> None:
    """Queue the channel handshake followed by the given frames."""
    connection.recv.side_effect = [
        MS_CHANNEL_CONNECT_SAMPLE,
        MS_CHANNEL_READY_SAMPLE,
        *frames,
    ]


def _sent(connection: Mock) -> list[dict[str, Any]]:
    """Return the art requests sent over the websocket, without ids."""
    requests = []
    for sent_call in connection.send.call_args_list:
        inner = json.loads(json.loads(sent_call.args[0])["params"]["data"])
        inner.pop("id")
        inner.pop("request_id")
        requests.append(inner)
    return requests


def _d2d_file(header: dict[str, Any], data: bytes) -> bytes:
    """Encode one D2D file transfer: u32 header length + JSON header + data."""
    raw_header = json.dumps(header).encode()
    return len(raw_header).to_bytes(4, "big") + raw_header + data


def _feed_socket(sock: Mock, data: bytes, chunk: int = 5) -> None:
    """Make the socket return `data` in small chunks, then EOF."""
    stream = io.BytesIO(data)
    sock.recv.side_effect = lambda size: stream.read(min(size, chunk))


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
        patch.object(SamsungTVArt, "get_api_version", return_value="2.01"),
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
        patch.object(SamsungTVArt, "get_api_version", return_value="0.98"),
        patch.object(SamsungTVArt, "_open_d2d_socket", return_value=sock),
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


def test_send_image_success_binary_payload(connection: Mock) -> None:
    """Art API 0.97: upload is a WS binary frame: u16-len + JSON header + JPEG bytes."""
    file_bytes = b"\xff\xd8\xff\xe0JFIF\x00\x01FAKEJPEGDATA\xff\xd9"

    with (
        patch("samsungtvws.art.art.uuid.uuid4", return_value=_UUID),
        patch.object(SamsungTVArt, "get_api_version", return_value="0.97"),
    ):
        connection.recv.side_effect = [
            MS_CHANNEL_CONNECT_SAMPLE,
            MS_CHANNEL_READY_SAMPLE,
            D2D_SERVICE_MESSAGE_IMAGE_ADDED_SAMPLE,
        ]

        tv_art = SamsungTVArt("127.0.0.1")
        content_id = tv_art.upload(
            file_bytes, file_type="jpg", matte="none", date="2023:05:02 15:06:39"
        )
        assert content_id == "MY_F0001"

        assert connection.send_binary.call_count == 1
        payload = connection.send_binary.call_args.args[0]
        assert isinstance(payload, (bytes, bytearray))

        header_len = int.from_bytes(payload[0:2], "big")
        header_bytes = payload[2 : 2 + header_len]
        img_bytes = payload[2 + header_len :]

        outer = json.loads(header_bytes.decode("utf-8"))
        assert outer["method"] == "ms.channel.emit"
        assert outer["params"]["event"] == "art_app_request"
        assert outer["params"]["to"] == "host"

        inner = json.loads(outer["params"]["data"])
        assert inner["request"] == "send_image"
        assert inner["file_type"] == "JPEG"
        assert inner["matte_id"] == "none"
        assert inner["id"] == str(_UUID)

        assert img_bytes == file_bytes


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


def test_open_unexpected_event(connection: Mock) -> None:
    """Ensure open fails and closes when the channel is not ready."""
    connection.recv.side_effect = [
        MS_CHANNEL_CONNECT_SAMPLE,
        json.dumps({"event": "ms.channel.timeOut"}),
    ]
    tv_art = SamsungTVArt("127.0.0.1")

    with pytest.raises(exceptions.ConnectionFailure):
        tv_art.open()

    connection.close.assert_called_once()
    assert tv_art.connection is None


def test_recv_timeout(connection: Mock, tv_art: SamsungTVArt) -> None:
    """Ensure a websocket timeout is raised as ConnectionFailure."""
    _respond(connection, websocket.WebSocketTimeoutException("timed out"))

    with pytest.raises(exceptions.ConnectionFailure, match="Websocket Time out"):
        tv_art.get_current()


def test_wait_skips_unrelated_frames(connection: Mock, tv_art: SamsungTVArt) -> None:
    """Ensure unrelated or undecodable frames are skipped while waiting."""
    _respond(
        connection,
        json.dumps({"event": "ms.channel.clientConnect", "data": {}}),
        json.dumps({"event": "d2d_service_message", "data": {"not": "a string"}}),
        json.dumps({"event": "d2d_service_message", "data": "not json"}),
        _d2d({"event": "current_artwork", "content_id": "OTHER"}, request_id="x"),
        _d2d({"event": "current_artwork", "content_id": "MY_F0001"}),
    )

    assert tv_art.get_current() == {
        **_IDS,
        "event": "current_artwork",
        "content_id": "MY_F0001",
    }


@pytest.mark.parametrize(
    ("frame", "message"),
    [
        pytest.param(
            _error(json.dumps({"request": "get_current_artwork"}), error_code="-7"),
            "`get_current_artwork` request failed with error number -7",
            id="known-request",
        ),
        pytest.param(
            _error("not json", error_code="-1"),
            "`unknown_request` request failed with error number -1",
            id="invalid-request-data",
        ),
        pytest.param(
            _error(),
            "`unknown_request` request failed with error number unknown",
            id="no-details",
        ),
    ],
)
def test_error_response(
    connection: Mock, tv_art: SamsungTVArt, frame: str, message: str
) -> None:
    """Ensure TV error frames raise ResponseError with request name and code."""
    _respond(connection, frame)

    with pytest.raises(exceptions.ResponseError, match=re.escape(message)):
        tv_art.get_current()


@pytest.mark.parametrize(
    ("method", "args", "expected_request"),
    [
        pytest.param(
            "get_device_info", (), {"request": "get_device_info"}, id="device-info"
        ),
        pytest.param(
            "get_current", (), {"request": "get_current_artwork"}, id="current"
        ),
        pytest.param(
            "get_auto_rotation_status",
            (),
            {"request": "get_auto_rotation_status"},
            id="get-auto-rotation",
        ),
        pytest.param(
            "get_slideshow_status",
            (),
            {"request": "get_slideshow_status"},
            id="get-slideshow",
        ),
        pytest.param(
            "set_auto_rotation_status",
            (),
            {
                "request": "set_auto_rotation_status",
                "value": "off",
                "category_id": "MY-C0002",
                "type": "shuffleslideshow",
            },
            id="set-auto-rotation-off",
        ),
        pytest.param(
            "set_auto_rotation_status",
            (15, False, 4),
            {
                "request": "set_auto_rotation_status",
                "value": "15",
                "category_id": "MY-C0004",
                "type": "slideshow",
            },
            id="set-auto-rotation-ordered",
        ),
        pytest.param(
            "set_slideshow_status",
            (),
            {
                "request": "set_slideshow_status",
                "value": "off",
                "category_id": "MY-C0002",
                "type": "shuffleslideshow",
            },
            id="set-slideshow-off",
        ),
        pytest.param(
            "set_slideshow_status",
            (30, False, 2, "MY-C0008"),
            {
                "request": "set_slideshow_status",
                "value": "30",
                "category_id": "MY-C0008",
                "type": "slideshow",
            },
            id="set-slideshow-explicit-category",
        ),
        pytest.param(
            "set_brightness_sensor_setting",
            (True,),
            {"request": "set_brightness_sensor_setting", "value": "on"},
            id="brightness-sensor",
        ),
        pytest.param(
            "set_brightness",
            (7,),
            {"request": "set_brightness", "value": 7},
            id="set-brightness",
        ),
        pytest.param(
            "set_color_temperature",
            (-2,),
            {"request": "set_color_temperature", "value": -2},
            id="set-color-temperature",
        ),
        pytest.param(
            "set_motion_timer",
            ("15",),
            {"request": "set_motion_timer", "value": "15"},
            id="motion-timer",
        ),
        pytest.param(
            "set_motion_sensitivity",
            ("2",),
            {"request": "set_motion_sensitivity", "value": "2"},
            id="motion-sensitivity",
        ),
        pytest.param(
            "set_artmode",
            (False,),
            {"request": "set_artmode_status", "value": "off"},
            id="artmode-bool",
        ),
        pytest.param(
            "set_artmode",
            ("ON",),
            {"request": "set_artmode_status", "value": "on"},
            id="artmode-string",
        ),
        pytest.param(
            "select_image",
            ("MY_F0001",),
            {
                "request": "select_image",
                "category_id": None,
                "content_id": "MY_F0001",
                "show": True,
            },
            id="select-image",
        ),
        pytest.param(
            "select_image",
            ("MY_F0001", "MY-C0002", False),
            {
                "request": "select_image",
                "category_id": "MY-C0002",
                "content_id": "MY_F0001",
                "show": False,
            },
            id="select-image-category",
        ),
        pytest.param(
            "set_photo_filter",
            ("MY_F0001", "ink"),
            {
                "request": "set_photo_filter",
                "content_id": "MY_F0001",
                "filter_id": "ink",
            },
            id="photo-filter",
        ),
        pytest.param(
            "change_matte",
            ("MY_F0001", None, "flexible_black"),
            {
                "request": "change_matte",
                "content_id": "MY_F0001",
                "matte_id": "none",
                "portrait_matte_id": "flexible_black",
            },
            id="change-matte-portrait",
        ),
    ],
)
def test_request_returns_payload(
    connection: Mock,
    tv_art: SamsungTVArt,
    method: str,
    args: tuple[Any, ...],
    expected_request: dict[str, Any],
) -> None:
    """Ensure thin wrappers send one request and return the decoded payload."""
    _respond(connection, _d2d({"event": "ok", "value": "x"}))

    result = getattr(tv_art, method)(*args)

    assert _sent(connection) == [expected_request]
    assert result == {**_IDS, "event": "ok", "value": "x"}


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("maybe", id="unknown-string"),
        pytest.param(1, id="int"),
    ],
)
def test_set_artmode_invalid_value(
    connection: Mock, tv_art: SamsungTVArt, value: Any
) -> None:
    """Ensure invalid on/off values are rejected before sending."""
    with pytest.raises(ValueError, match="Expected bool or 'on'/'off' string"):
        tv_art.set_artmode(value)

    connection.send.assert_not_called()


@pytest.mark.parametrize(
    ("method", "request_name", "response", "expected"),
    [
        pytest.param(
            "get_artmode",
            "get_artmode_status",
            {"value": "on"},
            "on",
            id="artmode",
        ),
        pytest.param(
            "get_artmode",
            "get_artmode_status",
            {"event": "artmode_status"},
            {**_IDS, "event": "artmode_status"},
            id="artmode-missing-value",
        ),
        pytest.param(
            "get_rotation",
            "get_current_rotation",
            {"current_rotation_status": 1},
            1,
            id="rotation",
        ),
        pytest.param(
            "get_photo_filter_list",
            "get_photo_filter_list",
            {"filter_list": json.dumps([{"filter_id": "ink"}])},
            [{"filter_id": "ink"}],
            id="photo-filter-list",
        ),
        pytest.param(
            "get_matte_list",
            "get_matte_list",
            {
                "matte_type_list": json.dumps([{"matte_type": "modern"}]),
                "matte_color_list": json.dumps([{"color": "black"}]),
            },
            {
                "matte_types": [{"matte_type": "modern"}],
                "matte_colors": [{"color": "black"}],
            },
            id="matte-type-and-color-list",
        ),
        pytest.param(
            "get_matte_list",
            "get_matte_list",
            {"matte_list": json.dumps([{"matte_type": "flexible"}])},
            {"matte_types": [{"matte_type": "flexible"}]},
            id="matte-list-legacy-name",
        ),
        pytest.param(
            "get_matte_list",
            "get_matte_list",
            {"event": "matte_list"},
            {},
            id="matte-list-empty",
        ),
        pytest.param(
            "get_api_version",
            "api_version",
            {"version": "4.3.4.0"},
            "4.3.4.0",
            id="api-version",
        ),
    ],
)
def test_request_returns_value(
    connection: Mock,
    tv_art: SamsungTVArt,
    method: str,
    request_name: str,
    response: dict[str, Any],
    expected: Any,
) -> None:
    """Ensure getters extract their value from the response payload."""
    _respond(connection, _d2d(response))

    assert getattr(tv_art, method)() == expected
    assert _sent(connection) == [{"request": request_name}]


def test_get_api_version_legacy_fallback(
    connection: Mock, tv_art: SamsungTVArt
) -> None:
    """Ensure the legacy request is used when api_version fails."""
    _respond(connection, _error(error_code="-1"), _d2d({"version": "2.03"}))

    assert tv_art.get_api_version() == "2.03"
    assert _sent(connection) == [
        {"request": "api_version"},
        {"request": "get_api_version"},
    ]


def test_get_api_version_missing(connection: Mock, tv_art: SamsungTVArt) -> None:
    """Ensure a response without version raises ResponseError."""
    _respond(connection, _d2d({"event": "api_version"}))

    with pytest.raises(exceptions.ResponseError, match="Missing 'version'"):
        tv_art.get_api_version()


@pytest.mark.parametrize(
    ("category", "expected"),
    [
        pytest.param(None, ["MY_F0001", "SAM-F0122"], id="all"),
        pytest.param("MY-C0002", ["MY_F0001"], id="filtered"),
    ],
)
def test_available(
    connection: Mock,
    tv_art: SamsungTVArt,
    category: str | None,
    expected: list[str],
) -> None:
    """Ensure available returns the content list, optionally filtered."""
    content = [
        {"category_id": "MY-C0002", "content_id": "MY_F0001"},
        {"category_id": "MY-C0004", "content_id": "SAM-F0122"},
    ]
    _respond(connection, _d2d({"content_list": json.dumps(content)}))

    result = tv_art.available(category)

    assert [item["content_id"] for item in result] == expected
    assert _sent(connection) == [{"request": "get_content_list", "category": category}]


def test_set_favourite_waits_for_sub_event(
    connection: Mock, tv_art: SamsungTVArt
) -> None:
    """Ensure set_favourite waits for the favorite_changed sub event."""
    _respond(
        connection,
        _d2d({"event": "image_selected"}),
        _d2d({"event": "favorite_changed", "status": "off"}),
    )

    assert tv_art.set_favourite("MY_F0001", status=False) == {
        **_IDS,
        "event": "favorite_changed",
        "status": "off",
    }
    assert _sent(connection) == [
        {"request": "change_favorite", "content_id": "MY_F0001", "status": "off"}
    ]


_SETTINGS = json.dumps(
    [
        {"item": "brightness", "value": "5"},
        {"item": "color_temperature", "value": "-2"},
    ]
)


@pytest.mark.parametrize(
    ("setting", "data", "expected"),
    [
        pytest.param(
            "brightness",
            _SETTINGS,
            {"item": "brightness", "value": "5"},
            id="match",
        ),
        pytest.param(
            "motion_timer",
            _SETTINGS,
            {**_IDS, "data": _SETTINGS},
            id="no-match",
        ),
        pytest.param(
            "brightness",
            "not json",
            {**_IDS, "data": "not json"},
            id="invalid-json",
        ),
        pytest.param(
            "brightness",
            None,
            {**_IDS, "data": None},
            id="not-a-string",
        ),
    ],
)
def test_get_artmode_settings(
    connection: Mock,
    tv_art: SamsungTVArt,
    setting: str,
    data: Any,
    expected: dict[str, Any],
) -> None:
    """Ensure a matching setting is extracted, else the full payload is returned."""
    _respond(connection, _d2d({"data": data}))

    assert tv_art.get_artmode_settings(setting) == expected


@pytest.mark.parametrize(
    ("method", "expected"),
    [
        pytest.param("get_brightness", "5", id="brightness"),
        pytest.param("get_color_temperature", "-2", id="color-temperature"),
    ],
)
def test_get_setting_from_artmode_settings(
    connection: Mock, tv_art: SamsungTVArt, method: str, expected: str
) -> None:
    """Ensure Art API v4 settings are read from get_artmode_settings."""
    _respond(connection, _d2d({"data": _SETTINGS}))

    assert getattr(tv_art, method)() == expected
    assert _sent(connection) == [{"request": "get_artmode_settings"}]


@pytest.mark.parametrize(
    ("method", "legacy_request"),
    [
        pytest.param("get_brightness", "get_brightness", id="brightness"),
        pytest.param(
            "get_color_temperature", "get_color_temperature", id="color-temperature"
        ),
    ],
)
def test_get_setting_legacy_fallback(
    connection: Mock, tv_art: SamsungTVArt, method: str, legacy_request: str
) -> None:
    """Ensure the legacy getter is used when get_artmode_settings fails."""
    _respond(connection, _error(error_code="-1"), _d2d({"value": "3"}))

    assert getattr(tv_art, method)() == "3"
    assert _sent(connection) == [
        {"request": "get_artmode_settings"},
        {"request": legacy_request},
    ]


@pytest.mark.parametrize(
    ("device_info", "expected"),
    [
        pytest.param({"device": {"FrameTVSupport": "true"}}, True, id="frame"),
        pytest.param({"device": {"FrameTVSupport": "false"}}, False, id="not-frame"),
        pytest.param({}, False, id="no-device"),
    ],
)
def test_supported(device_info: dict[str, Any], expected: bool) -> None:
    """Ensure Frame TV support is read from the REST device info."""
    tv_art = SamsungTVArt("127.0.0.1", timeout=3)
    with patch("samsungtvws.rest.requests.get") as get:
        get.return_value.text = json.dumps(device_info)

        assert tv_art.supported() is expected
        assert tv_art.supported() is expected

    assert get.call_count == 2
    get.assert_called_with("http://127.0.0.1:8001/api/v2/", timeout=3, verify=False)


@pytest.mark.parametrize(
    ("content_id_list", "expected_request_ids"),
    [
        pytest.param("MY_F0001", [{"content_id": "MY_F0001"}], id="single"),
        pytest.param(
            ["MY_F0001", "MY_F0002"],
            [{"content_id": "MY_F0001"}, {"content_id": "MY_F0002"}],
            id="list",
        ),
    ],
)
@pytest.mark.usefixtures("mock_uuid")
def test_get_thumbnail_list(
    connection: Mock,
    d2d_socket: Mock,
    content_id_list: str | list[str],
    expected_request_ids: list[dict[str, str]],
) -> None:
    """Ensure all thumbnails are read from the D2D socket."""
    _respond(connection, _d2d({"conn_info": json.dumps(_CONN_INFO)}))
    _feed_socket(
        d2d_socket,
        _d2d_file(
            {
                "fileID": "MY_F0001",
                "fileType": "jpg",
                "fileLength": 3,
                "num": 0,
                "total": 2,
            },
            b"one",
        )
        + _d2d_file(
            {
                "fileID": "MY_F0002",
                "fileType": "png",
                "fileLength": 3,
                "num": 1,
                "total": 2,
            },
            b"two",
        ),
    )
    tv_art = SamsungTVArt("127.0.0.1", timeout=5)

    with patch("samsungtvws.helper.random.randrange", return_value=42):
        result = tv_art.get_thumbnail_list(content_id_list)

    assert result == {"MY_F0001.jpg": b"one", "MY_F0002.png": b"two"}
    assert _sent(connection) == [
        {
            "request": "get_thumbnail_list",
            "content_id_list": expected_request_ids,
            "conn_info": {"d2d_mode": "socket", "connection_id": 42, "id": _UUID},
        }
    ]
    d2d_socket.connect.assert_called_once_with(("192.168.1.20", 12345))
    d2d_socket.settimeout.assert_called_with(5)
    d2d_socket.close.assert_called_once()


def test_get_thumbnail_list_socket_closed(
    connection: Mock, tv_art: SamsungTVArt, d2d_socket: Mock
) -> None:
    """Ensure a truncated D2D transfer raises and still closes the socket."""
    _respond(connection, _d2d({"conn_info": _CONN_INFO}))
    _feed_socket(d2d_socket, b"\x00\x00")

    with pytest.raises(exceptions.ConnectionFailure):
        tv_art.get_thumbnail_list()

    assert _sent(connection)[0]["content_id_list"] == []
    d2d_socket.close.assert_called_once()


def test_get_thumbnail_list_invalid_conn_info(
    connection: Mock, tv_art: SamsungTVArt, d2d_socket: Mock
) -> None:
    """Ensure an unusable conn_info fails when opening the D2D socket."""
    _respond(connection, _d2d({"conn_info": 5}))

    with pytest.raises(KeyError, match="ip"):
        tv_art.get_thumbnail_list("MY_F0001")

    d2d_socket.connect.assert_not_called()


@pytest.mark.usefixtures("mock_uuid")
def test_d2d_socket_secured_and_settimeout_errors(
    connection: Mock, d2d_socket: Mock
) -> None:
    """Ensure secured D2D connections are TLS-wrapped and settimeout errors ignored."""
    _respond(connection, _d2d({"conn_info": {**_CONN_INFO, "secured": True}}))
    d2d_socket.settimeout.side_effect = OSError
    ssl_context = Mock()
    tls_socket = ssl_context.wrap_socket.return_value
    tls_socket.settimeout.side_effect = OSError
    _feed_socket(
        tls_socket,
        _d2d_file(
            {
                "fileID": "MY_F0001",
                "fileType": "jpg",
                "fileLength": 2,
                "num": 0,
                "total": 1,
            },
            b"ok",
        ),
    )
    tv_art = SamsungTVArt("127.0.0.1", timeout=5)

    with patch("samsungtvws.art.art.get_ssl_context", return_value=ssl_context):
        assert tv_art.get_thumbnail_list("MY_F0001") == {"MY_F0001.jpg": b"ok"}

    ssl_context.wrap_socket.assert_called_once_with(d2d_socket)
    tls_socket.connect.assert_called_once_with(("192.168.1.20", 12345))
    tls_socket.close.assert_called_once()


@pytest.mark.parametrize(
    ("content_id_list", "as_dict", "expected", "transfers"),
    [
        pytest.param("MY_F0001", False, b"one", 1, id="single"),
        pytest.param(["MY_F0001", "MY_F0002"], False, [b"one", b"two"], 2, id="list"),
        pytest.param(
            ["MY_F0001", "MY_F0002"],
            True,
            {"MY_F0001.jpg": b"one", "MY_F0002.jpg": b"two"},
            2,
            id="as-dict",
        ),
    ],
)
def test_get_thumbnail_socket(
    connection: Mock,
    tv_art: SamsungTVArt,
    d2d_socket: Mock,
    content_id_list: str | list[str],
    as_dict: bool,
    expected: Any,
    transfers: int,
) -> None:
    """Ensure thumbnails are read from one D2D socket transfer per content id."""
    ready = _d2d({"conn_info": _CONN_INFO})
    _respond(connection, ready, ready)
    files = [
        _d2d_file(
            {"fileID": cid, "fileType": "jpg", "fileLength": 3, "num": 0, "total": 1},
            data,
        )
        for cid, data in (("MY_F0001", b"one"), ("MY_F0002", b"two"))
    ]
    streams = [io.BytesIO(file) for file in files]
    d2d_socket.recv.side_effect = lambda size: streams[
        d2d_socket.close.call_count
    ].read(size)

    assert tv_art.get_thumbnail(content_id_list, as_dict=as_dict) == expected
    assert d2d_socket.close.call_count == transfers
    assert len(_sent(connection)) == transfers


def test_get_thumbnail_none(connection: Mock, tv_art: SamsungTVArt) -> None:
    """Ensure no request is sent and None is returned without content ids."""
    assert tv_art.get_thumbnail() is None

    connection.send.assert_not_called()


@pytest.mark.parametrize(
    ("content_ids", "returned", "expected"),
    [
        pytest.param(
            ["MY_F0001"],
            [{"content_id": "MY_F0001"}],
            True,
            id="list-match",
        ),
        pytest.param(
            ["MY_F0001", "MY_F0002"],
            json.dumps([{"content_id": "MY_F0001"}, {"content_id": "MY_F0002"}]),
            True,
            id="json-string-match",
        ),
        pytest.param(
            ["MY_F0001", "MY_F0002"],
            [{"content_id": "MY_F0001"}],
            False,
            id="partial",
        ),
        pytest.param(["MY_F0001"], None, False, id="missing"),
        pytest.param(["MY_F0001"], "not json", False, id="invalid-json"),
        pytest.param(
            ["MY_F0001"], json.dumps({"content_id": "MY_F0001"}), False, id="not-a-list"
        ),
    ],
)
def test_delete_list(
    connection: Mock,
    tv_art: SamsungTVArt,
    content_ids: list[str],
    returned: Any,
    expected: bool,
) -> None:
    """Ensure delete_list reports whether the TV deleted exactly the requested ids."""
    _respond(connection, _d2d({"content_id_list": returned}))

    assert tv_art.delete_list(content_ids) is expected
    assert _sent(connection) == [
        {
            "request": "delete_image_list",
            "content_id_list": [{"content_id": cid} for cid in content_ids],
        }
    ]


def test_delete(connection: Mock, tv_art: SamsungTVArt) -> None:
    """Ensure delete removes a single content id."""
    _respond(connection, _d2d({"content_id_list": [{"content_id": "MY_F0001"}]}))

    assert tv_art.delete("MY_F0001") is True
    assert _sent(connection) == [
        {
            "request": "delete_image_list",
            "content_id_list": [{"content_id": "MY_F0001"}],
        }
    ]


def _upload_frames() -> list[str]:
    """Frames for a D2D socket upload on a non-0.97 TV."""
    return [
        _d2d({"version": "4.3.4.0"}),
        _d2d({"event": "ready_to_use", "conn_info": json.dumps(_CONN_INFO)}),
        _d2d({"event": "image_added", "content_id": "MY_F0099"}, request_id="other"),
    ]


@pytest.mark.parametrize(
    ("file_name", "file_type", "expected_type"),
    [
        pytest.param("image.jpeg", "png", "jpg", id="extension-overrides-type"),
        pytest.param("image", "PNG", "png", id="no-extension"),
    ],
)
def test_upload_from_path(
    connection: Mock,
    tv_art: SamsungTVArt,
    d2d_socket: Mock,
    tmp_path: Path,
    file_name: str,
    file_type: str,
    expected_type: str,
) -> None:
    """Ensure a file path is read and sent over the D2D socket."""
    path = tmp_path / file_name
    path.write_bytes(b"IMAGEDATA")
    _respond(connection, *_upload_frames())

    assert tv_art.upload(str(path), file_type=file_type, matte="") == "MY_F0099"

    send_image = _sent(connection)[1]
    assert send_image["file_type"] == expected_type
    assert send_image["file_size"] == 9
    assert send_image["matte_id"] == "none"
    assert re.fullmatch(r"\d{4}:\d\d:\d\d \d\d:\d\d:\d\d", send_image["image_date"])
    header = json.loads(d2d_socket.sendall.call_args_list[1].args[0])
    assert header["fileType"] == expected_type
    assert header["secKey"] == "SECKEY"
    assert d2d_socket.sendall.call_args_list[2].args[0] == b"IMAGEDATA"


def test_upload_file_object_after_api_version_failure(
    connection: Mock, tv_art: SamsungTVArt, d2d_socket: Mock
) -> None:
    """Ensure a file object is uploaded via socket when api version is unknown."""
    d2d_socket.close.side_effect = OSError
    _respond(
        connection,
        _error(error_code="-1"),
        _d2d({"event": "api_version"}),
        *_upload_frames()[1:],
    )

    content_id = tv_art.upload(
        io.BytesIO(b"JPEGDATA"), file_type="jpeg", portrait_matte=""
    )

    assert content_id == "MY_F0099"
    requests = _sent(connection)
    assert [request["request"] for request in requests] == [
        "api_version",
        "get_api_version",
        "send_image",
    ]
    assert requests[2]["file_type"] == "jpg"
    assert requests[2]["portrait_matte_id"] == "none"
    assert d2d_socket.sendall.call_args_list[2].args[0] == b"JPEGDATA"


def test_upload_file_object_not_bytes(tv_art: SamsungTVArt) -> None:
    """Ensure a text file object is rejected."""
    with pytest.raises(ValueError, match="Expected file-like object returning bytes"):
        tv_art.upload(io.StringIO("text"))


def test_upload_ws_binary_png(connection: Mock, tv_art: SamsungTVArt) -> None:
    """Ensure Art API 0.97 binary upload upper-cases non-JPEG file types."""
    _respond(
        connection,
        _d2d({"version": "0.97"}),
        _d2d({"event": "image_added", "content_id": "MY_F0100"}),
    )

    assert tv_art.upload(b"PNGDATA", file_type="png") == "MY_F0100"

    payload = connection.send_binary.call_args.args[0]
    header_len = int.from_bytes(payload[:2], "big")
    inner = json.loads(json.loads(payload[2 : 2 + header_len])["params"]["data"])
    assert inner == {
        "request": "send_image",
        "file_type": "PNG",
        "matte_id": "shadowbox_polar",
        "id": _UUID,
    }
    assert payload[2 + header_len :] == b"PNGDATA"


def test_upload_ws_binary_header_too_large(
    connection: Mock, tv_art: SamsungTVArt
) -> None:
    """Ensure an oversized binary upload header is rejected."""
    _respond(connection, _d2d({"version": "0.97"}))

    with pytest.raises(ValueError, match="Upload header too large"):
        tv_art.upload(b"PNGDATA", matte="x" * 0x10000)

    connection.send_binary.assert_not_called()
