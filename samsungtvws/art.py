"""
SamsungTVWS - Samsung Smart TV WS API wrapper

Copyright (C) 2019 DSR! <xchwarze@gmail.com>
Copyright (C) 2021 Matthew Garrett <mjg59@srcf.ucam.org>

SPDX-License-Identifier: LGPL-3.0
"""

from datetime import datetime
import json
import logging
import random
import socket
from typing import Any, Dict, Optional
import uuid

import websocket

from . import exceptions, helper
from .command import SamsungTVCommand
from .connection import SamsungTVWSConnection
from .event import D2D_SERVICE_MESSAGE_EVENT, MS_CHANNEL_READY_EVENT
from .rest import SamsungTVRest

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
        self.art_uuid = str(uuid.uuid4())
        self._rest_api: Optional[SamsungTVRest] = None

    def open(self) -> websocket.WebSocket:
        super().open()

        # Override base class to wait for MS_CHANNEL_READY_EVENT
        assert self.connection
        data = self.connection.recv()
        response = helper.process_api_response(data)
        event = response.get("event", "*")
        self._websocket_event(event, response)

        if event != MS_CHANNEL_READY_EVENT:
            self.close()
            raise exceptions.ConnectionFailure(response)

        return self.connection

    def _send_art_request(
        self,
        request_data: Dict[str, Any],
        wait_for_event: Optional[str] = None,
        wait_for_sub_event: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        request_data["id"] = self.art_uuid
        self.send_command(ArtChannelEmitCommand.art_app_request(request_data))

        if not wait_for_event:
            return None

        assert self.connection
        event: Optional[str] = None
        sub_event: Optional[str] = None
        while event != wait_for_event:
            data = self.connection.recv()
            response = helper.process_api_response(data)
            event = response.get("event", "*")
            assert event
            self._websocket_event(event, response)
            if event == wait_for_event and wait_for_sub_event:
                # Check sub event, reset event if it doesn't match
                data = json.loads(response["data"])
                sub_event = data.get("event", "*")
                if sub_event == "error":
                    raise exceptions.ResponseError(
                        f"`{request_data['request']}` request failed "
                        f"with error number {data['error_code']}"
                    )
                if sub_event != wait_for_sub_event:
                    event = None

        return response

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

        return support == "true"

    def get_api_version(self):
        response = self._send_art_request(
            {"request": "get_api_version"},
            wait_for_event=D2D_SERVICE_MESSAGE_EVENT,
        )
        assert response
        data = json.loads(response["data"])
        assert response
        return data["version"]

    def get_device_info(self):
        response = self._send_art_request(
            {"request": "get_device_info"},
            wait_for_event=D2D_SERVICE_MESSAGE_EVENT,
        )
        assert response
        return json.loads(response["data"])

    def available(self, category=None):
        response = self._send_art_request(
            {"request": "get_content_list", "category": category},
            wait_for_event=D2D_SERVICE_MESSAGE_EVENT,
        )
        assert response
        data = json.loads(response["data"])

        return json.loads(data["content_list"])

    def get_current(self):
        response = self._send_art_request(
            {"request": "get_current_artwork"},
            wait_for_event=D2D_SERVICE_MESSAGE_EVENT,
        )
        assert response
        return json.loads(response["data"])

    def get_thumbnail(self, content_id):
        response = self._send_art_request(
            {
                "request": "get_thumbnail",
                "content_id": content_id,
                "conn_info": {
                    "d2d_mode": "socket",
                    "connection_id": random.randrange(4 * 1024 * 1024 * 1024),
                    "id": self.art_uuid,
                },
            },
            wait_for_event=D2D_SERVICE_MESSAGE_EVENT,
        )
        assert response
        data = json.loads(response["data"])
        conn_info = json.loads(data["conn_info"])

        art_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        art_socket.connect((conn_info["ip"], int(conn_info["port"])))
        header_len = int.from_bytes(art_socket.recv(4), "big")
        header = json.loads(art_socket.recv(header_len))

        thumbnail_data_len = int(header["fileLength"])
        thumbnail_data = bytearray()
        while len(thumbnail_data) < thumbnail_data_len:
            packet = art_socket.recv(thumbnail_data_len - len(thumbnail_data))
            thumbnail_data.extend(packet)

        return thumbnail_data

    def upload(self, file, matte="shadowbox_polar", file_type="png", date=None):
        file_size = len(file)

        file_type = file_type.lower()
        if file_type == "jpeg":
            file_type = "jpg"

        if date is None:
            date = datetime.now().strftime("%Y:%m:%d %H:%M:%S")

        response = self._send_art_request(
            {
                "request": "send_image",
                "file_type": file_type,
                "conn_info": {
                    "d2d_mode": "socket",
                    "connection_id": random.randrange(4 * 1024 * 1024 * 1024),
                    "id": self.art_uuid,
                },
                "image_date": date,
                "matte_id": matte,
                "file_size": file_size,
            },
            wait_for_event=D2D_SERVICE_MESSAGE_EVENT,
            wait_for_sub_event="ready_to_use",
        )
        assert response
        data = json.loads(response["data"])
        conn_info = json.loads(data["conn_info"])

        header = json.dumps(
            {
                "num": 0,
                "total": 1,
                "fileLength": file_size,
                "fileName": "dummy",
                "fileType": file_type,
                "secKey": conn_info["key"],
                "version": "0.0.1",
            }
        )

        art_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        art_socket.connect((conn_info["ip"], int(conn_info["port"])))
        art_socket.send(len(header).to_bytes(4, "big"))
        art_socket.send(header.encode("ascii"))
        art_socket.send(file)

        wait_for_sub_event = "image_added"
        wait_for_event = "d2d_service_message"

        assert self.connection
        event: Optional[str] = None
        sub_event: Optional[str] = None

        while event != wait_for_event:
            data = self.connection.recv()
            response = helper.process_api_response(data)
            event = response.get("event", "*")
            assert event
            self._websocket_event(event, response)
            if event == wait_for_event and wait_for_sub_event:
                # Check sub event, reset event if it doesn't match
                data = json.loads(response["data"])
                sub_event = data.get("event", "*")
                if sub_event != wait_for_sub_event:
                    event = None

        data = json.loads(response["data"])

        return data["content_id"]

    def delete(self, content_id):
        self.delete_list([content_id])

    def delete_list(self, content_ids):
        content_id_list = []
        for item in content_ids:
            content_id_list.append({"content_id": item})

        self._send_art_request(
            {"request": "delete_image_list", "content_id_list": content_id_list}
        )

    def select_image(self, content_id, category=None, show=True):
        self._send_art_request(
            {
                "request": "select_image",
                "category_id": category,
                "content_id": content_id,
                "show": show,
            }
        )

    def get_artmode(self):
        response = self._send_art_request(
            {
                "request": "get_artmode_status",
            },
            wait_for_event=D2D_SERVICE_MESSAGE_EVENT,
        )
        assert response
        data = json.loads(response["data"])

        return data["value"]

    def set_artmode(self, mode):
        self._send_art_request(
            {
                "request": "set_artmode_status",
                "value": mode,
            }
        )

    def get_photo_filter_list(self):
        response = self._send_art_request(
            {"request": "get_photo_filter_list"},
            wait_for_event=D2D_SERVICE_MESSAGE_EVENT,
        )
        assert response
        data = json.loads(response["data"])

        return json.loads(data["filter_list"])

    def set_photo_filter(self, content_id, filter_id):
        self._send_art_request(
            {
                "request": "set_photo_filter",
                "content_id": content_id,
                "filter_id": filter_id,
            }
        )

    def get_matte_list(self):
        response = self._send_art_request(
            {"request": "get_matte_list"},
            wait_for_event=D2D_SERVICE_MESSAGE_EVENT,
        )
        assert response
        data = json.loads(response["data"])

        return json.loads(data["matte_type_list"])

    def change_matte(self, content_id, matte_id):
        self._send_art_request(
            {
                "request": "change_matte",
                "content_id": content_id,
                "matte_id": matte_id,
            }
        )
