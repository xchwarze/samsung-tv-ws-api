"""
SamsungTVWS - Samsung Smart TV WS API wrapper

Copyright (C) 2019 Xchwarze
Copyright (C) 2021 Matthew Garrett <mjg59@srcf.ucam.org>

    This library is free software; you can redistribute it and/or
    modify it under the terms of the GNU Lesser General Public
    License as published by the Free Software Foundation; either
    version 2.1 of the License, or (at your option) any later version.

    This library is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
    Lesser General Public License for more details.

    You should have received a copy of the GNU Lesser General Public
    License along with this library; if not, write to the Free Software
    Foundation, Inc., 51 Franklin Street, Fifth Floor,
    Boston, MA  02110-1335  USA

"""
import json
import logging
import random
import socket
import uuid
from datetime import datetime

from . import helper

_LOGGING = logging.getLogger(__name__)


class SamsungTVArt:
    def __init__(self, remote):
        self.remote = remote
        self.art_uuid = str(uuid.uuid4())
        self.art_connection = None

    def _art_ws_send(self, command):
        if self.art_connection is None:
            self.art_connection = self.remote.open("com.samsung.art-app")
            self.art_connection.recv()

        payload = json.dumps(command)
        self.art_connection.send(payload)

    def _send_art_request(self, data, response=False):
        data["id"] = self.art_uuid
        self._art_ws_send(
            {
                "method": "ms.channel.emit",
                "params": {
                    "event": "art_app_request",
                    "to": "host",
                    "data": json.dumps(data),
                },
            }
        )

        if response:
            return helper.process_api_response(self.art_connection.recv())

    def supported(self):
        support = None
        data = self.remote.rest_device_info()
        device = data.get("device")
        if device:
            support = device.get("FrameTVSupport")

        return support == "true"

    def get_api_version(self):
        response = self._send_art_request({"request": "get_api_version"}, response=True)
        data = json.loads(response["data"])

        return data["version"]

    def get_device_info(self):
        response = self._send_art_request({"request": "get_device_info"}, response=True)

        return json.loads(response["data"])

    def available(self, category=None):
        response = self._send_art_request(
            {"request": "get_content_list", "category": category}, response=True
        )
        data = json.loads(response["data"])

        return json.loads(data["content_list"])

    def get_current(self):
        response = self._send_art_request(
            {
                "request": "get_current_artwork",
            },
            response=True,
        )

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
            response=True,
        )
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
            response=True,
        )
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

        response = helper.process_api_response(self.art_connection.recv())
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
            response=True,
        )
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
            {"request": "get_photo_filter_list"}, response=True
        )
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
