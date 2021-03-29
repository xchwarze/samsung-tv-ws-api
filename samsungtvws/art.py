"""
SamsungTVWS - Samsung Smart TV WS API wrapper

Copyright 2021 Matthew Garrett <mjg59@srcf.ucam.org>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

"""

import json
import random
import requests
import socket
import uuid

from datetime import datetime

class SamsungTVArt:
    def __init__(self, remote):
        self.remote = remote
        self._art_uuid = uuid.uuid4()

    def supported(self):
        data =  self.remote.rest_device_info()
        device = data.get('device')
        if device:
            support = device.get('FrameTVSupport')
        else:
            support = None

        if support == 'true':
            return True
        return False

    def _send_art_request(self, data, response=False):
        data['id'] = str(self._art_uuid)
        self.remote._art_ws_send({
            'method': 'ms.channel.emit',
            'params': {
                'event': 'art_app_request',
                'to': 'host',
                'data': json.dumps(data)
            }
        })

        if response == True:
            response = self.remote._process_api_response(self.remote.art_connection.recv())
            return response

    def get_api_version(self):
        data = {
            'request': 'get_api_version'
        }

        response = self._send_art_request(data, response=True)
        data = json.loads(response['data'])
        return data['version']

    def get_device_info(self):
        data = {
            'request': 'get_device_info'
        }

        response = self._send_art_request(data, response=True)
        data = json.loads(response['data'])
        return data

    def available(self, category=None):
        data = {
            'request': 'get_content_list',
            'category': category
        }

        response = self._send_art_request(data, response=True)
        data = json.loads(response['data'])
        content_list = json.loads(data['content_list'])
        return content_list

    def get_current(self):
        data = {
            'request': 'get_current_artwork',
        }

        response = self._send_art_request(data, response=True)
        data = json.loads(response['data'])
        return data

    def get_thumbnail(self, art):
        data = {
            'request': 'get_thumbnail',
            'content_id': art,
            'conn_info': {
                'd2d_mode': 'socket',
                'connection_id': '1616911254067',
                'id': str(self._art_uuid)
            }
        }

        response = self._send_art_request(data, response=True)
        data = json.loads(response['data'])
        conn_info = json.loads(data['conn_info'])
        ip = conn_info['ip']
        port = int(conn_info['port'])
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((ip, port))
        header_len = int.from_bytes(s.recv(4), 'big')
        header = json.loads(s.recv(header_len))
        data = s.recv(int(header['fileLength']))
        return data

    def upload(self, art, matte='shadowbox_polar', date=None, filetype='PNG'):
        if date == None:
            now = datetime.now()
            date = now.strftime("%Y:%m:%d %H:%M:%S")
        connection_id = random.randrange(4*1024*1024*1024)
        data = {
            'request': 'send_image',
            'file_type': filetype,
            'conn_info': {
                'd2d_mode': 'socket',
                'connection_id': connection_id,
                'id': str(self._art_uuid),
            },
            'image_date': date,
            'matte_id': matte,
            'file_size': len(art)
        }
        
        response = self._send_art_request(data, response=True)
        data = json.loads(response['data'])
        conn_info = json.loads(data['conn_info'])
        ip = conn_info['ip']
        port = int(conn_info['port'])
        key = conn_info['key']
        header_filetype = 'png'
        if filetype == 'JPEG':
            header_filetype = 'jpg'

        header = {
            'num': 0,
            'total': 1,
            'fileLength': len(art),
            'fileName': 'dummy',
            'fileType': header_filetype,
            'secKey': key,
            'version': '0.0.1'
        }
        header_string = json.dumps(header)
        header_len = len(header_string).to_bytes(4, 'big')
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((ip, port))
        s.send(header_len)
        s.send(header_string.encode('ascii'))
        s.send(art)
        response = self.remote._process_api_response(self.remote.art_connection.recv())
        data = json.loads(response['data'])
        return data['content_id']

    def delete(self, art):
        self.delete_list([art])

    def delete_list(self, art):
        artlist = []
        for entry in art:
            artlist.append({'content_id': entry})
        data = {
            'request': 'delete_image_list',
            'content_id_list': artlist
        }
        self._send_art_request(data, response=True)

    def set(self, art, category=None, show=True):
        data = {
            'request': 'select_image',
            'category_id': category,
            'content_id': art,
            'show': show,
        }

        self._send_art_request(data)

    def get_artmode(self):
        data = {
            'request': 'get_artmode_status',
        }

        response = self._send_art_request(data, response=True)
        data = json.loads(response['data'])
        return data['value']

    def set_artmode(self, mode):
        data = {
            'request': 'set_artmode_status',
            'value': mode,
        }

        self._send_art_request(data)

    def get_photo_filter_list(self):
        data = {
            'request': 'get_photo_filter_list'
        }

        response = self._send_art_request(data, response=True)
        data = json.loads(response['data'])
        filter_list = json.loads(data['filter_list'])
        return filter_list

    def set_photo_filter(self, art, filter_id):
        data = {
            'request': 'set_photo_filter',
            'content_id': art,
            'filter_id': filter_id
        }

        self._send_art_request(data)

