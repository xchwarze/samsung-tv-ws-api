"""
SamsungTVWS - Samsung Smart TV WS API wrapper

Copyright (C) 2019 DSR! <xchwarze@gmail.com>
Copyright (C) 2021 Matthew Garrett <mjg59@srcf.ucam.org>

SPDX-License-Identifier: LGPL-3.0
"""

from datetime import datetime
import json
import logging
import os
import socket
from typing import IO, Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union, cast
import uuid

import websocket

from . import exceptions, helper
from .command import SamsungTVCommand
from .connection import SamsungTVWSConnection
from .event import D2D_SERVICE_MESSAGE_EVENT, MS_CHANNEL_READY_EVENT
from .helper import generate_connection_id, get_ssl_context
from .rest import SamsungTVRest

# for typing
JsonObj = Dict[str, Any]
WsFrame = Dict[str, Any]

_LOGGING = logging.getLogger(__name__)
ART_ENDPOINT = "com.samsung.art-app"


class ArtChannelEmitCommand(SamsungTVCommand):
    def __init__(self, params: Dict[str, Any]) -> None:
        super().__init__("ms.channel.emit", params)

    @staticmethod
    def art_app_request(data: Dict[str, Any]) -> "ArtChannelEmitCommand":
        return ArtChannelEmitCommand(
            {
                "event": "art_app_request",
                "to": "host",
                "data": json.dumps(data),
            }
        )


class SamsungTVArt(SamsungTVWSConnection):
    # -------------------------
    # Lifecycle / connection
    # -------------------------
    def __init__(
        self,
        host,
        token=None,
        token_file=None,
        port=8001,
        timeout=None,
        key_press_delay=1,
        name="SamsungTvRemote",
    ):
        super().__init__(
            host,
            endpoint=ART_ENDPOINT,
            token=token,
            token_file=token_file,
            port=port,
            timeout=timeout,
            key_press_delay=key_press_delay,
            name=name,
        )
        self._rest_api: Optional[SamsungTVRest] = None

    def open(self) -> websocket.WebSocket:
        super().open()

        # Override base class to wait for MS_CHANNEL_READY_EVENT
        event, frame = self._recv_frame()
        if event != MS_CHANNEL_READY_EVENT:
            self.close()
            raise exceptions.ConnectionFailure(frame)

        return self.connection

    def _new_request_uuid(self) -> str:
        """Return a fresh uuid to correlate a single request/response."""
        return str(uuid.uuid4())

    # -------------------------
    # WebSocket primitives
    # -------------------------
    def _recv_frame(self) -> Tuple[str, WsFrame]:
        """Receive one websocket frame, process + emit websocket event."""
        assert self.connection
        try:
            raw = self.connection.recv()
            frame = helper.process_api_response(raw)

            # Always propagate events to keep internal connection state in sync
            event = frame.get("event", "*")
            self._websocket_event(event, frame)

            _LOGGING.debug("event: %s", event)
            return event, frame
        except websocket.WebSocketTimeoutException as e:
            raise exceptions.ConnectionFailure(f"Websocket Time out: {e}") from e

    def _decode_d2d_payload(self, frame: WsFrame) -> Optional[JsonObj]:
        """Decode D2D payload from a frame (if present)."""
        data = frame.get("data")
        if not isinstance(data, str):
            return None
        try:
            return cast(JsonObj, json.loads(data))
        except json.JSONDecodeError:
            return None

    def _parse_conn_info(self, payload: JsonObj) -> JsonObj:
        """Return decoded conn_info dict from a D2D payload."""
        conn_info = payload.get("conn_info", {})
        if isinstance(conn_info, str):
            return cast(JsonObj, json.loads(conn_info))
        if isinstance(conn_info, dict):
            return cast(JsonObj, conn_info)
        return {}

    def _open_d2d_socket(self, conn_info: JsonObj) -> socket.socket:
        """Open a TCP socket to the TV D2D endpoint (optionally TLS-wrapped)."""
        raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Best-effort timeout: avoid hanging forever on connect/recv.
        # Samsung's D2D endpoint can be flaky depending on firmware.
        if self.timeout is not None:
            try:
                raw_sock.settimeout(self.timeout)
            except OSError:
                pass

        sock = (
            get_ssl_context().wrap_socket(raw_sock)
            if conn_info.get("secured", False)
            else raw_sock
        )
        sock.connect((conn_info["ip"], int(conn_info["port"])))

        # Ensure recv/send timeout is applied to the final socket
        if self.timeout is not None:
            try:
                sock.settimeout(self.timeout)
            except OSError:
                pass

        return sock

    def _recv_d2d_file(self, sock: socket.socket) -> Tuple[str, bytearray, int, int]:
        """Receive a single D2D file payload."""
        header_len = int.from_bytes(self._recv_exact(sock, 4), "big")
        header = json.loads(self._recv_exact(sock, header_len))

        size = int(header["fileLength"])
        name = f'{header["fileID"]}.{header["fileType"]}'
        data = self._recv_exact(sock, size)

        return name, bytearray(data), int(header["num"]), int(header["total"])

    def _recv_exact(self, sock: socket.socket, size: int) -> bytes:
        """Receive exactly `size` bytes from socket or fail."""
        buf = bytearray()
        while len(buf) < size:
            chunk = sock.recv(size - len(buf))
            if not chunk:
                raise exceptions.ConnectionFailure({"reason": "socket closed"})
            buf.extend(chunk)
        return bytes(buf)

    def _wait_for_d2d(
        self,
        *,
        request_uuid: Optional[str],
        wait_for_sub_event: Optional[str],
    ) -> Any:
        while True:
            event, frame = self._recv_frame()
            if event != D2D_SERVICE_MESSAGE_EVENT:
                continue

            payload = self._decode_d2d_payload(frame)
            if not payload:
                continue

            msg_uuid = payload.get("request_id", payload.get("id"))
            _LOGGING.debug("request_uuid: %s, message uuid: %s", request_uuid, msg_uuid)

            if request_uuid and msg_uuid != request_uuid:
                continue

            sub_event = payload.get("event", "*")
            _LOGGING.debug(
                "sub_event: %s, wait_for_sub_event: %s", sub_event, wait_for_sub_event
            )

            if sub_event == "error":
                req = "unknown_request"
                try:
                    req = json.loads(payload.get("request_data", "{}")).get(
                        "request", req
                    )
                except json.JSONDecodeError:
                    pass
                raise exceptions.ResponseError(
                    f"`{req}` request failed with error number {payload.get('error_code', 'unknown')}"
                )

            if not wait_for_sub_event or sub_event == wait_for_sub_event:
                return payload

    def _send_art_request(
        self,
        request_data: JsonObj,
        wait_for_event: Optional[str] = D2D_SERVICE_MESSAGE_EVENT,
        wait_for_sub_event: Optional[str] = None,
        *,
        request_uuid: Optional[str] = None,
    ) -> Optional[Any]:
        """
        Send a request and optionally wait for a response.

        Notes:
        - id and request_id are set to a per-request uuid for correct correlation.
        - When waiting for a non-D2D websocket event, the raw frame is returned.
        """
        payload = dict(request_data)

        req_id = request_uuid or self._new_request_uuid()
        payload["id"] = req_id
        payload["request_id"] = req_id

        self.send_command(ArtChannelEmitCommand.art_app_request(payload))

        if not wait_for_event:
            return None

        # Non-D2D waits return the websocket frame as-is.
        if wait_for_event != D2D_SERVICE_MESSAGE_EVENT:
            if wait_for_sub_event:
                raise ValueError(
                    "wait_for_sub_event is only valid for D2D_SERVICE_MESSAGE_EVENT"
                )

            while True:
                event, frame = self._recv_frame()
                if event == wait_for_event:
                    return frame

        return self._wait_for_d2d(
            request_uuid=req_id,
            wait_for_sub_event=wait_for_sub_event,
        )

    # -------------------------
    # Generic getters / setters
    # -------------------------
    def _to_on_off(self, value: Any) -> str:
        """Normalize value to 'on' or 'off'."""
        if isinstance(value, bool):
            return "on" if value else "off"

        if isinstance(value, str):
            correct_value = value.lower()
            if correct_value in ("on", "off"):
                return correct_value

        raise ValueError("Expected bool or 'on'/'off' string")

    def _request_json(
        self, request: str, *, wait_for_sub_event: Optional[str] = None, **params: Any
    ) -> Any:
        """Generic request helper returning decoded D2D payload."""
        return self._send_art_request(
            {"request": request, **params}, wait_for_sub_event=wait_for_sub_event
        )

    def _get_value(self, request: str, key: str = "value", **params: Any) -> Any:
        """Generic getter returning payload[key] when present."""
        data = self._request_json(request, **params)
        if isinstance(data, dict) and key in data:
            return data[key]

        return data

    def _set_value(
        self, request: str, value: Any, key: str = "value", **params: Any
    ) -> Any:
        """Generic setter sending value under payload key."""
        return self._request_json(request, **{key: value, **params})

    # -------------------------
    # REST helpers / capability
    # -------------------------
    def _get_rest_api(self) -> SamsungTVRest:
        if self._rest_api is None:
            self._rest_api = SamsungTVRest(self.host, self.port, self.timeout)

        return self._rest_api

    def supported(self) -> bool:
        support = None
        data = self._get_rest_api().rest_device_info()
        device = data.get("device")
        if device:
            support = device.get("FrameTVSupport")

        return str(support).lower() == "true"

    # -------------------------
    # Art API
    # -------------------------
    def get_api_version(self) -> str:
        """Return Art API version."""
        try:
            # Try new API first
            data = self._request_json("api_version")
        except exceptions.ResponseError:
            # Fallback to legacy API. it may not respond on newer TVs.
            data = self._request_json("get_api_version")
        if not isinstance(data, dict) or "version" not in data:
            raise exceptions.ResponseError("Missing 'version' in response")
        return cast(str, data["version"])

    def get_device_info(self):
        """Return device info payload."""
        return self._request_json("get_device_info")

    def available(self, category=None):
        """Return available content list, optionally filtered by category id."""
        data = self._request_json("get_content_list", category=category)
        content_list = json.loads(data["content_list"])

        if not category:
            return content_list

        result = []
        for item in content_list:
            if item.get("category_id") == category:
                result.append(item)

        return result

    def get_current(self):
        """Return current artwork payload."""
        return self._request_json("get_current_artwork")

    def set_favourite(self, content_id, status="on"):
        """Toggle favourite status for an artwork."""
        return self._request_json(
            "change_favorite",
            wait_for_sub_event="favorite_changed",
            content_id=content_id,
            status=self._to_on_off(status),
        )

    def get_artmode_settings(self, setting=""):
        """
        Return Art Mode settings.

        If `setting` is provided, returns the matching setting entry when the TV
        responds with a nested `data` list; otherwise returns the full payload.
        """
        data = self._request_json("get_artmode_settings")

        nested = data.get("data")
        if isinstance(nested, str):
            try:
                nested_data = json.loads(nested)
            except json.JSONDecodeError:
                return data

            for item in nested_data:
                if item.get("item") == setting:
                    return item

        return data

    def get_auto_rotation_status(self):
        """Return auto-rotation configuration."""
        return self._request_json("get_auto_rotation_status")

    def set_auto_rotation_status(
        self,
        duration: int = 0,
        type: bool = True,
        category: int = 2,
        category_id: Optional[str] = None,
    ) -> Any:
        """
        Configure auto-rotation (slideshow rotation) for a category.
        Category format: 'MY-C0004' where 4 is favourites, 2 is my pictures, and 8 is store.

        duration: minutes (>0) or 0 to disable
        type: True for shuffled slideshow, False for ordered slideshow
        category: numeric suffix used to build category_id (e.g. 2 -> "MY-C0002")
        category_id: explicit category id (preferred when known, e.g. "MY-C0004")
        """
        value = "off"
        if duration > 0:
            value = str(duration)

        slideshow_type = "slideshow"
        if type:
            slideshow_type = "shuffleslideshow"

        resolved_category_id = category_id or f"MY-C000{category}"
        return self._request_json(
            "set_auto_rotation_status",
            value=value,
            category_id=resolved_category_id,
            type=slideshow_type,
        )

    def get_slideshow_status(self):
        """Return slideshow configuration."""
        return self._request_json("get_slideshow_status")

    def set_slideshow_status(
        self,
        duration: int = 0,
        type: bool = True,
        category: int = 2,
        category_id: Optional[str] = None,
    ) -> Any:
        """
        Configure slideshow playback for a category.
        Category format: 'MY-C0004' where 4 is favourites, 2 is my pictures, and 8 is store.

        duration: minutes (>0) or 0 to disable
        type: True for shuffled slideshow, False for ordered slideshow
        category: numeric suffix used to build category_id (e.g. 2 -> "MY-C0002")
        category_id: explicit category id (preferred when known, e.g. "MY-C0004")
        """
        value = "off"
        if duration > 0:
            value = str(duration)

        slideshow_type = "slideshow"
        if type:
            slideshow_type = "shuffleslideshow"

        resolved_category_id = category_id or f"MY-C000{category}"
        return self._request_json(
            "set_slideshow_status",
            value=value,
            category_id=resolved_category_id,
            type=slideshow_type,
        )

    def set_brightness_sensor_setting(self, value: Any) -> Any:
        """Enable or disable brightness sensor."""
        return self._set_value("set_brightness_sensor_setting", self._to_on_off(value))

    def get_brightness(self):
        """Return art mode brightness level."""
        try:
            # Art api v4 support
            data = self.get_artmode_settings("brightness")
            return data.get("value")
        except exceptions.ResponseError:
            return self._get_value("get_brightness")

    def set_brightness(self, value):
        """Set art mode brightness level."""
        # TODO maybe in art api v4.x this command is "brightness"
        return self._set_value("set_brightness", value)

    def get_color_temperature(self):
        """Return art mode color temperature."""
        try:
            # Art api v4 support
            data = self.get_artmode_settings("color_temperature")
            return data.get("value")
        except exceptions.ResponseError:
            return self._get_value("get_color_temperature")

    def set_color_temperature(self, value):
        """Set art mode color temperature."""
        # TODO maybe in art api v4.x this command is "color_temperature"
        return self._set_value("set_color_temperature", value)

    def get_thumbnail_list(
        self, content_id_list: Optional[Union[str, Sequence[str]]] = None
    ) -> Dict[str, bytearray]:
        """Fetch one or more thumbnails via D2D socket."""
        if content_id_list is None:
            content_id_list = []
        if isinstance(content_id_list, str):
            content_id_list = [content_id_list]

        req_list = [{"content_id": cid} for cid in content_id_list]
        d2d_id = self._new_request_uuid()

        payload = self._send_art_request(
            {
                "request": "get_thumbnail_list",
                "content_id_list": req_list,
                "conn_info": {
                    "d2d_mode": "socket",
                    "connection_id": generate_connection_id(),
                    "id": d2d_id,
                },
            },
            request_uuid=d2d_id,
        )

        assert payload
        sock = self._open_d2d_socket(self._parse_conn_info(payload))

        thumbnails: Dict[str, bytearray] = {}
        try:
            total = 1
            current = -1

            while current + 1 < total:
                name, data, current, total = self._recv_d2d_file(sock)
                thumbnails[name] = data
        finally:
            sock.close()

        return thumbnails

    def get_thumbnail(
        self,
        content_id_list: Optional[Union[str, Sequence[str]]] = None,
        as_dict: bool = False,
    ) -> Union[Dict[str, bytearray], List[bytearray], Optional[bytearray]]:
        """Fetch thumbnail(s) via D2D socket."""
        if content_id_list is None:
            content_id_list = []
        if isinstance(content_id_list, str):
            content_id_list = [content_id_list]

        result: Dict[str, bytearray] = {}

        for cid in content_id_list:
            d2d_id = self._new_request_uuid()
            payload = self._send_art_request(
                {
                    "request": "get_thumbnail",
                    "content_id": cid,
                    "conn_info": {
                        "d2d_mode": "socket",
                        "connection_id": generate_connection_id(),
                        "id": d2d_id,
                    },
                },
                request_uuid=d2d_id,
            )

            assert payload
            sock = self._open_d2d_socket(self._parse_conn_info(payload))

            try:
                name, data, _, _ = self._recv_d2d_file(sock)
                result[name] = data
            finally:
                sock.close()

        if as_dict:
            return result
        if len(content_id_list) > 1:
            return list(result.values())
        if result:
            return next(iter(result.values()))

        return None

    def upload(
        self,
        file: Union[str, bytes, bytearray, IO[bytes]],
        matte: str = "shadowbox_polar",
        portrait_matte: str = "shadowbox_polar",
        file_type: str = "png",
        date: Optional[str] = None,
    ) -> str:
        """Upload an image via D2D socket and return content_id."""
        # Load bytes
        if isinstance(file, str):
            _, ext = os.path.splitext(file)
            if ext:
                file_type = ext[1:]
            with open(file, "rb") as f:
                data = f.read()
        elif hasattr(file, "read"):
            # file-like object
            data = file.read()
            if not isinstance(data, (bytes, bytearray)):
                raise ValueError("Expected file-like object returning bytes")
        else:
            data = bytes(file)

        file_size = len(data)
        ft = file_type.lower()
        if ft == "jpeg":
            ft = "jpg"

        if date is None:
            date = datetime.now().strftime("%Y:%m:%d %H:%M:%S")

        upload_id = self._new_request_uuid()

        ready = self._send_art_request(
            {
                "request": "send_image",
                "id": upload_id,
                "request_id": upload_id,
                "file_type": ft,
                "file_size": file_size,
                "image_date": date,
                "matte_id": matte or "none",
                "portrait_matte_id": portrait_matte or "none",
                "conn_info": {
                    "d2d_mode": "socket",
                    "connection_id": generate_connection_id(),
                    "id": upload_id,
                },
            },
            wait_for_sub_event="ready_to_use",
            request_uuid=upload_id,
        )
        assert ready

        conn_info = self._parse_conn_info(ready)
        header = json.dumps(
            {
                "num": 0,
                "total": 1,
                "fileLength": file_size,
                "fileName": "image",
                "fileType": ft,
                "secKey": conn_info["key"],
                "version": "0.0.1",
            }
        ).encode("ascii")

        sock = self._open_d2d_socket(conn_info)
        try:
            sock.sendall(len(header).to_bytes(4, "big"))
            sock.sendall(header)
            sock.sendall(data)
        finally:
            try:
                sock.close()
            except OSError:
                pass

        done = self._wait_for_d2d(
            request_uuid=upload_id,
            wait_for_sub_event="image_added",
        )
        return cast(str, done["content_id"])

    def delete(self, content_id: str) -> bool:
        """Delete a single artwork by content id."""
        return self.delete_list([content_id])

    def delete_list(self, content_ids: Iterable[str]) -> bool:
        """Delete multiple artworks by content id."""
        content_id_list = [{"content_id": cid} for cid in content_ids]
        data = self._request_json("delete_image_list", content_id_list=content_id_list)

        if not isinstance(data, dict):
            return False

        returned = data.get("content_id_list")
        if not returned:
            return False

        if isinstance(returned, str):
            try:
                returned = json.loads(returned)
            except json.JSONDecodeError:
                return False

        if not isinstance(returned, list):
            return False

        return cast(List[object], returned) == cast(List[object], content_id_list)

    def select_image(
        self, content_id: str, category: Optional[str] = None, show: bool = True
    ) -> Any:
        """Select an artwork and optionally show it immediately."""
        return self._request_json(
            "select_image", category_id=category, content_id=content_id, show=show
        )

    def get_artmode(self):
        """Return current art mode state."""
        return self._get_value("get_artmode_status", key="value")

    def set_artmode(self, mode: Union[bool, int, str]) -> Any:
        """Set art mode state."""
        return self._set_value("set_artmode_status", self._to_on_off(mode))

    def get_rotation(self):
        """Return current rotation status."""
        return self._get_value("get_current_rotation", key="current_rotation_status")

    def get_photo_filter_list(self):
        """Return available photo filters."""
        data = self._request_json("get_photo_filter_list")
        return json.loads(data["filter_list"])

    def set_photo_filter(self, content_id, filter_id):
        """Set photo filter for a content id."""
        return self._request_json(
            "set_photo_filter", content_id=content_id, filter_id=filter_id
        )

    def get_matte_list(self):
        """
        Return available matte types and optional colors.

        Normalizes API differences across TV firmware (matte_type_list vs matte_list).
        """
        data = self._request_json("get_matte_list")
        result = {}

        # I understand that in some version of the api this is the new name of the data...
        matte_types = data.get("matte_type_list") or data.get("matte_list")
        if isinstance(matte_types, str):
            result["matte_types"] = json.loads(matte_types)

        matte_colors = data.get("matte_color_list")
        if isinstance(matte_colors, str):
            result["matte_colors"] = json.loads(matte_colors)

        return result

    def change_matte(
        self,
        content_id: str,
        matte_id: Optional[str] = None,
        portrait_matte: Optional[str] = None,
    ) -> Any:
        """Change matte for an artwork (optionally portrait-specific)."""
        params = {
            "content_id": content_id,
            "matte_id": matte_id or "none",
        }
        if portrait_matte:
            params["portrait_matte_id"] = portrait_matte

        return self._request_json("change_matte", **params)

    def set_motion_timer(self, value: str) -> Any:
        """Set motion timer (e.g. 'off', '5', '15', '30', '60', '120', '240')."""
        return self._set_value("set_motion_timer", value)

    def set_motion_sensitivity(self, value: str) -> Any:
        """Set motion sensitivity ('1' to '3')."""
        return self._set_value("set_motion_sensitivity", value)
