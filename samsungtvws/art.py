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
from typing import Any, Dict, Optional
import uuid
import websocket

from . import exceptions, helper
from .command import SamsungTVCommand
from .connection import SamsungTVWSConnection
from .event import D2D_SERVICE_MESSAGE_EVENT, MS_CHANNEL_READY_EVENT
from .helper import get_ssl_context, generate_connection_id
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
        self.art_uuid = None
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

        self._send_update_status()

        return self.connection
    
    def get_or_generate_uuid(self) -> str:
        if not self.art_uuid:
            self.art_uuid = str(uuid.uuid4())
        return self.art_uuid

    def _send_art_request(
        self,
        request_data: Dict[str, Any],
        wait_for_event: Optional[str] = None,
        wait_for_sub_event: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        request_data["id"] = self.get_or_generate_uuid()

        # this is for support new api (v ?????)
        request_data["request_id"] = request_data["id"]

        self.send_command(ArtChannelEmitCommand.art_app_request(request_data))
        if not wait_for_event:
            return None

        assert self.connection
        response = None
        event: Optional[str] = None
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

    def _send_update_status(self):
        self.get_api_version()
        self.get_artmode()

    def supported(self) -> bool:
        support = None
        data = self._get_rest_api().rest_device_info()
        device = data.get("device")
        if device:
            support = device.get("FrameTVSupport")

        return support == "true"

    def get_api_version(self):
        response = self._send_art_request(
            # TODO maybe in art api v4.x this command is "api_version"
            {"request": "get_api_version"},
            wait_for_event=D2D_SERVICE_MESSAGE_EVENT,
        )
        assert response
        data = json.loads(response["data"])
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
        content_list = json.loads(data["content_list"])
        result = []
        if category:
            for item in content_list:
                if item["category_id"] == category:
                    result.append(item)
        else:
            result = content_list

        return result

    def get_current(self):
        response = self._send_art_request(
            {"request": "get_current_artwork"},
            wait_for_event=D2D_SERVICE_MESSAGE_EVENT,
        )
        assert response
        return json.loads(response["data"])

    def set_favourite(self, content_id, status="on"):
        response = self._send_art_request(
            {"request": "change_favorite", "content_id": content_id, "status": status},
            wait_for_event=D2D_SERVICE_MESSAGE_EVENT,
            wait_for_sub_event="favorite_changed",
        )
        assert response
        return json.loads(response["data"])

    def get_artmode_settings(self, setting=""):
        """
        setting can be any of 'brightness', 'color_temperature', 'motion_sensitivity',
        'motion_timer', or 'brightness_sensor_setting'
        """
        response = self._send_art_request(
            {"request": "get_artmode_settings"},
            wait_for_event=D2D_SERVICE_MESSAGE_EVENT,
        )
        assert response

        data = json.loads(response["data"])
        assert data

        if "data" in data:
            nested_data = json.loads(data["data"])
            for item in nested_data:
                if item.get("item") == setting:
                    return item

        return data

    def get_auto_rotation_status(self):
        response = self._send_art_request(
            {"request": "get_auto_rotation_status"},
            wait_for_event=D2D_SERVICE_MESSAGE_EVENT,
        )
        assert response
        return json.loads(response["data"])

    def set_auto_rotation_status(self, duration=0, type=True, category=2):
        """
        duration is "off" or "number" where number is duration in minutes. set 0 for 'off'
        slide show type can be "slideshow" or "shuffleslideshow", set True for shuffleslideshow
        category is 'MY-C0004' or 'MY-C0002' where 4 is favourites, 2 is my pictures, and 8 is store
        """
        response = self._send_art_request(
            {
                "request": "set_auto_rotation_status",
                "value": str(duration) if duration > 0 else "off",
                "category_id": f"MY-C000{category}",
                "type": "shuffleslideshow" if type else "slideshow",
            },
            wait_for_event=D2D_SERVICE_MESSAGE_EVENT,
        )
        assert response
        return json.loads(response["data"])

    def get_slideshow_status(self):
        response = self._send_art_request(
            {"request": "get_slideshow_status"},
            wait_for_event=D2D_SERVICE_MESSAGE_EVENT,
        )
        assert response
        return json.loads(response["data"])

    def set_slideshow_status(self, duration=0, type=True, category=2):
        """
        duration is "off" or "number" where number is duration in minutes. set 0 for 'off'
        slide show type can be "slideshow" or "shuffleslideshow", set True for shuffleslideshow
        category is 'MY-C0004' or 'MY-C0002' where 4 is favourites, 2 is my pictures, and 8 is store
        """
        response = self._send_art_request(
            {
                "request": "set_slideshow_status",
                "value": str(duration) if duration > 0 else "off",
                "category_id": f"MY-C000{category}",
                "type": "shuffleslideshow" if type else "slideshow",
            },
            wait_for_event=D2D_SERVICE_MESSAGE_EVENT,
        )
        assert response
        return json.loads(response["data"])

    def get_brightness(self):
        response = self._send_art_request(
            # TODO maybe in art api v4.x this command is "brightness"
            {"request": "get_brightness"},
        )
        assert response
        return response

    def set_brightness(self, value):
        response = self._send_art_request(
            {"request": "set_brightness", "value": value},
            wait_for_event=D2D_SERVICE_MESSAGE_EVENT,
        )
        assert response
        return json.loads(response["data"])

    def get_color_temperature(self):
        response = self._send_art_request(
            # TODO maybe in art api v4.x this command is "color_temperature"
            {"request": "get_color_temperature"},
        )
        assert response
        return response

    def set_color_temperature(self, value):
        response = self._send_art_request(
            {"request": "set_color_temperature", "value": value},
            wait_for_event=D2D_SERVICE_MESSAGE_EVENT,
        )
        assert response
        return json.loads(response["data"])

    def get_thumbnail_list(self, content_id_list=None):
        if content_id_list is None:
            content_id_list = []
        if isinstance(content_id_list, str):
            content_id_list = [content_id_list]
        content_id_list = [{"content_id": id} for id in content_id_list]
        response = self._send_art_request(
            {
                "request": "get_thumbnail_list",
                "content_id_list": content_id_list,
                "conn_info": {
                    "d2d_mode": "socket",
                    "connection_id": generate_connection_id(),
                    "id": self.get_or_generate_uuid(),
                },
            },
            wait_for_event=D2D_SERVICE_MESSAGE_EVENT,
        )
        assert response
        data = json.loads(response["data"])
        conn_info = json.loads(data["conn_info"])
        art_socket_raw = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        art_socket = (
            get_ssl_context().wrap_socket(art_socket_raw)
            if conn_info.get("secured", False)
            else art_socket_raw
        )
        art_socket.connect((conn_info["ip"], int(conn_info["port"])))
        total_num_thumbnails = 1
        current_thumb = -1
        thumbnail_data_dict = {}
        while current_thumb + 1 < total_num_thumbnails:
            header_len = int.from_bytes(art_socket.recv(4), "big")
            header = json.loads(art_socket.recv(header_len))
            thumbnail_data_len = int(header["fileLength"])
            current_thumb = int(header["num"])
            total_num_thumbnails = int(header["total"])
            filename = "{}.{}".format(header["fileID"], header["fileType"])
            thumbnail_data = bytearray()
            while len(thumbnail_data) < thumbnail_data_len:
                packet = art_socket.recv(thumbnail_data_len - len(thumbnail_data))
                thumbnail_data.extend(packet)
            thumbnail_data_dict[filename] = thumbnail_data
        return thumbnail_data_dict

    def get_thumbnail(self, content_id_list=None, as_dict=False):
        if content_id_list is None:
            content_id_list = []
        if isinstance(content_id_list, str):
            content_id_list = [content_id_list]
        thumbnail_data_dict = {}
        thumbnail_data = None
        for content_id in content_id_list:
            response = self._send_art_request(
                {
                    "request": "get_thumbnail",
                    "content_id": content_id,
                    "conn_info": {
                        "d2d_mode": "socket",
                        "connection_id": generate_connection_id(),
                        "id": self.get_or_generate_uuid(),
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
            filename = "{}.{}".format(header["fileID"], header["fileType"])
            thumbnail_data_dict[filename] = thumbnail_data

        return (
            thumbnail_data_dict
            if as_dict
            else list(thumbnail_data_dict.values())
            if len(content_id_list) > 1
            else thumbnail_data
        )

    def upload(
        self,
        file,
        matte="shadowbox_polar",
        portrait_matte="shadowbox_polar",
        file_type="png",
        date=None,
    ):
        if isinstance(file, str):
            file_name, file_extension = os.path.splitext(file)
            file_type = file_extension[1:]
            with open(file, "rb") as f:
                file = f.read()

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
                    "connection_id": generate_connection_id(),
                    "id": self.get_or_generate_uuid(),
                },
                "image_date": date,
                "matte_id": matte or "none",
                "portrait_matte_id": portrait_matte or "none",
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

        art_socket_raw = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        art_socket = (
            get_ssl_context().wrap_socket(art_socket_raw)
            if conn_info.get("secured", False)
            else art_socket_raw
        )
        art_socket.connect((conn_info["ip"], int(conn_info["port"])))
        art_socket.send(len(header).to_bytes(4, "big"))
        art_socket.send(header.encode("ascii"))
        art_socket.send(file)

        wait_for_event = D2D_SERVICE_MESSAGE_EVENT
        wait_for_sub_event = "image_added"

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
        content_id_list = [{"content_id": item} for item in content_ids]
        self._send_art_request({
            "request": "delete_image_list",
            "content_id_list": content_id_list
        })

    def select_image(self, content_id, category=None, show=True):
        self._send_art_request({
            "request": "select_image",
            "category_id": category,
            "content_id": content_id,
            "show": show,
        })

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

    def get_rotation(self):
        response = self._send_art_request(
            {"request": "get_current_rotation"},
            wait_for_event=D2D_SERVICE_MESSAGE_EVENT,
        )
        assert response
        data = json.loads(response["data"])

        return data.get("current_rotation_status", 0)

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

        result = {}
        if "matte_type_list" in data:
            result["matte_types"] = json.loads(data["matte_type_list"])

        # I understand that in some version of the api this is the new name of the data...
        if "matte_list" in data:
            result["matte_types"] = json.loads(data["matte_list"])

        if "matte_color_list" in data:
            result["matte_colors"] = json.loads(data["matte_color_list"])

        return result

    def change_matte(self, content_id, matte_id=None, portrait_matte=None):
        """
        matte is name_color eg flexible_polar or none
        NOTE: Not all mattes can be set for all image sizes!
        """
        request = {
            "request": "change_matte",
            "content_id": content_id,
            "matte_id": matte_id or "none",
        }
        if portrait_matte:
            request["portrait_matte_id"] = portrait_matte

        self._send_art_request(request)
