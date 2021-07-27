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
import random
import logging
import socket
import uuid
from datetime import datetime
from . import helper

_LOGGING = logging.getLogger(__name__)


class SamsungTVArt:
    def __init__(self, remote):
        self.remote = remote
        self.art_uuid = uuid.uuid4()
        self.art_connection = None

    def _art_ws_send(self, command):
        if self.art_connection is None:
            self.art_connection = self.open('com.samsung.art-app')
            self.art_connection.recv()

        payload = json.dumps(command)
        self.art_connection.send(payload)

    def _send_art_request(self, data, response=False):
        data['id'] = str(self.art_uuid)
        self._art_ws_send({
            'method': 'ms.channel.emit',
            'params': {
                'event': 'art_app_request',
                'to': 'host',
                'data': json.dumps(data)
            }
        })

        if response:
            return helper.process_api_response(self.art_connection.recv())

    def supported(self):
        support = None
        data = self.remote.rest_device_info()
        device = data.get('device')
        if device:
            support = device.get('FrameTVSupport')

        if support == 'true':
            return True

        return False

    def get_api_version(self):
        response = self._send_art_request(
            {
                'request': 'get_api_version'
            },
            response=True
        )
        data = json.loads(response['data'])

        return data['version']

    def get_device_info(self):
        response = self._send_art_request(
            {
                'request': 'get_device_info'
            },
            response=True
        )
        data = json.loads(response['data'])

        return data

    def available(self, category=None):
        response = self._send_art_request(
            {
                'request': 'get_content_list',
                'category': category
            },
            response=True
        )
        data = json.loads(response['data'])
        content_list = json.loads(data['content_list'])

        return content_list

    def get_current(self):
        response = self._send_art_request(
            {
                'request': 'get_current_artwork',
            },
            response=True
        )
        data = json.loads(response['data'])

        return data

    def get_thumbnail(self, art):
        response = self._send_art_request(
            {
                'request': 'get_thumbnail',
                'content_id': art,
                'conn_info': {
                    'd2d_mode': 'socket',
                    'connection_id': random.randrange(4 * 1024 * 1024 * 1024),
                    'id': str(self.art_uuid)
                }
            },
            response=True
        )
        data = json.loads(response['data'])
        conn_info = json.loads(data['conn_info'])

        art_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        art_socket.connect((conn_info['ip'], int(conn_info['port'])))
        header_len = int.from_bytes(art_socket.recv(4), 'big')
        header = json.loads(art_socket.recv(header_len))

        return art_socket.recv(int(header['fileLength']))

    def upload(self, art, matte='shadowbox_polar', filetype='png', date=None):
        filetype = filetype.lower()
        if filetype == 'jpeg':
            header_filetype = 'jpg'

        if date is None:
            date = datetime.now().strftime('%Y:%m:%d %H:%M:%S')

        response = self._send_art_request(
            {
                'request': 'send_image',
                'file_type': filetype,
                'conn_info': {
                    'd2d_mode': 'socket',
                    'connection_id': random.randrange(4 * 1024 * 1024 * 1024),
                    'id': str(self.art_uuid),
                },
                'image_date': date,
                'matte_id': matte,
                'file_size': len(art)
            },
            response=True
        )
        data = json.loads(response['data'])
        conn_info = json.loads(data['conn_info'])

        header_string = json.dumps({
            'num': 0,
            'total': 1,
            'fileLength': len(art),
            'fileName': 'dummy',
            'fileType': filetype,
            'secKey': conn_info['key'],
            'version': '0.0.1'
        })
        header_len = len(header_string).to_bytes(4, 'big')

        art_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        art_socket.connect((conn_info['ip'], int(conn_info['port'])))
        art_socket.send(header_len)
        art_socket.send(header_string.encode('ascii'))
        art_socket.send(art)

        response = helper.process_api_response(self.art_connection.recv())
        data = json.loads(response['data'])

        return data['content_id']

    def delete(self, art):
        self.delete_list([art])

    def delete_list(self, art):
        art_list = []
        for entry in art:
            art_list.append({'content_id': entry})

        self._send_art_request({
            'request': 'delete_image_list',
            'content_id_list': art_list
        })

    def set(self, art, category=None, show=True):
        self._send_art_request({
            'request': 'select_image',
            'category_id': category,
            'content_id': art,
            'show': show,
        })

    def get_artmode(self):
        response = self._send_art_request(
            {
                'request': 'get_artmode_status',
            },
            response=True
        )
        data = json.loads(response['data'])

        return data['value']

    def set_artmode(self, mode):
        self._send_art_request({
            'request': 'set_artmode_status',
            'value': mode,
        })

    def get_photo_filter_list(self):
        response = self._send_art_request(
            {
                'request': 'get_photo_filter_list'
            },
            response=True
        )
        data = json.loads(response['data'])
        filter_list = json.loads(data['filter_list'])

        return filter_list

    def set_photo_filter(self, art, filter_id):
        self._send_art_request({
            'request': 'set_photo_filter',
            'content_id': art,
            'filter_id': filter_id
        })
