"""
SamsungTVWS - Samsung Smart TV WS API wrapper

Copyright (C) 2019 DSR! <xchwarze@gmail.com>
Copyright (C) 2021 Matthew Garrett <mjg59@srcf.ucam.org>
Copyright (C) 2024 Nick Waterton <n.waterton@outlook.com>

SPDX-License-Identifier: LGPL-3.0
"""

from datetime import datetime
import os
import json
import logging
import random
import asyncio
import aiohttp
from typing import Any, Dict, List, Optional, Union, Callable, Awaitable
import uuid

from . import exceptions, helper
from .command import SamsungTVCommand
from .async_connection import SamsungTVWSAsyncConnection
from .event import D2D_SERVICE_MESSAGE_EVENT, MS_CHANNEL_READY_EVENT
from .async_rest import SamsungTVAsyncRest
from .helper import get_ssl_context

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


class SamsungTVAsyncArt(SamsungTVWSAsyncConnection):
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
        self._rest_api: Optional[SamsungTVAsyncRest] = None
        self.art_mode = None
        self.session = None
        self.pending_requests = {}
        self.callbacks = {}

    async def open(self):
        await super().open()

        # Override base class to wait for MS_CHANNEL_READY_EVENT
        assert self.connection
        data = await self.connection.recv()
        response = helper.process_api_response(data)
        event = response.get("event", "*")
        self._websocket_event(event, response)

        if event != MS_CHANNEL_READY_EVENT:
            await self.close()
            raise exceptions.ConnectionFailure(response)

        return self.connection
        
    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()
        await super().close()
        
    async def start_listening(self) -> None:
        # Override base class to process events
        await super().start_listening(self.process_event)
        try:
            await self.get_artmode()
        except AssertionError:
            pass
            
    def get_uuid(self):
        self.art_uuid = str(uuid.uuid4())
        return self.art_uuid
        
    async def wait_for_response(self, request_uuid, timeout=2):
        data = None
        try:
            if request_uuid not in self.pending_requests.keys():
                self.pending_requests[request_uuid] = asyncio.Future()
            response = await asyncio.wait_for(self.pending_requests[request_uuid], timeout)
            data = json.loads(response["data"])
        except asyncio.exceptions.TimeoutError:
            pass
        self.pending_requests.pop(request_uuid, None)
        if data and data.get("event", "*") == "error":
            raise exceptions.ResponseError(
                f"{json.loads(data['request_data'])['request']} request failed "
                f"with error number {data['error_code']}"
            )
        return data

    async def _send_art_request(
        self,
        request_data: Dict[str, Any],
        wait_for_event: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        if not request_data.get("id"):
            request_data["id"] = self.get_uuid()            #old api
        request_data["request_id"] = request_data["id"]     #new api
        self.pending_requests[wait_for_event or request_data["id"]] = asyncio.Future()
        await self.send_command(ArtChannelEmitCommand.art_app_request(request_data))
        return await self.wait_for_response(wait_for_event or request_data["id"])
        
    async def process_event(self, event=None, response=None):
        if event == D2D_SERVICE_MESSAGE_EVENT:
            data = json.loads(response["data"])
            sub_event = data.get("event", "*")
            if 'artmode_status' in sub_event:
                self.art_mode = data['value'] == 'on'
            elif sub_event == 'art_mode_changed':
                self.art_mode = data['status'] == 'on'
            elif sub_event == 'go_to_standby':
                self.art_mode = False
            elif 'wakeup' in sub_event:
                asyncio.create_task(self.get_artmode())
                
            if sub_event in self.callbacks.keys():
                awaitable = self.callbacks[sub_event](event, response)
                if awaitable:
                    asyncio.create_task(awaitable)
                
            request_id = data.get('request_id', data.get('id'))
            try:
                if request_id in self.pending_requests.keys():
                    self.pending_requests[request_id].set_result(response)
                elif sub_event in self.pending_requests.keys():
                    self.pending_requests[sub_event].set_result(response)
            except asyncio.exceptions.InvalidStateError:    #already completed
                pass
                
    def set_callback(self, trigger, callback=None):
        if not callback:
            self.callbacks.pop(trigger, None)
        else:
            self.callbacks[trigger] = callback
            
    def get_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
            self._rest_api = None
        return self.session

    def _get_rest_api(self) -> SamsungTVAsyncRest:
        self.get_session()
        if self._rest_api is None:
            self._rest_api = SamsungTVAsyncRest(host=self.host, port=self.port, session=self.session)
        return self._rest_api

    async def supported(self) -> bool:
        try:
            await asyncio.sleep(0.1)    #do not hit rest api to frequently
            data = await self._get_rest_api().rest_device_info()
            return data.get("device", {}).get("FrameTVSupport") == "true"
        except Exception as e:
            pass
        return False
        
    async def on(self) -> bool:
        try:
            await asyncio.sleep(0.1)    #do not hit rest api to frequently
            data = await self._get_rest_api().rest_device_info()
            return data.get("device", {}).get('PowerState', 'off') == 'on'
        except Exception as e:
            pass
        return False
        
    async def is_artmode(self) -> bool:
        return await self.on() and self.art_mode
        
    async def get_api_version(self):
        data = await self._send_art_request(
            {"request": "get_api_version"}
        )
        if not data:
            data = await self._send_art_request(
                {"request": "api_version"}
            )
        assert data
        return data["version"]

    async def get_device_info(self):
        data = await self._send_art_request(
            {"request": "get_device_info"}
        )
        assert data
        return data

    async def available(self, category=None):
        '''
        category is 'MY-C0004' or 'MY-C0002' where 4 is favourites, 2 is my pictures, and 8 is store
        '''
        data = await self._send_art_request(
            {"request": "get_content_list", "category": category}
        )
        assert data
        return [ v for v in json.loads(data["content_list"]) if v['category_id'] == category] if category else json.loads(data["content_list"])

    async def get_current(self):
        data = await self._send_art_request(
            {"request": "get_current_artwork"}
        )
        assert data
        return data
        
    async def set_favourite(self, content_id, status='on'):
        data = await self._send_art_request(
            {   "request": "change_favorite",
                "content_id": content_id,
                "status": status},
            wait_for_event = "favorite_changed"
        )
        assert data
        return data
        
    async def get_artmode_settings(self, setting=''):
        '''
        setting can be any of 'brightness', 'color_temperature', 'motion_sensitivity',
        'motion_timer', or 'brightness_sensor_setting'
        '''
        data = await self._send_art_request(
            {"request": "get_artmode_settings"}
        )
        assert data
        data = json.loads(data['data'])
        return next(iter(item for item in data if item['item'] == setting), data)

    async def get_auto_rotation_status(self):
        data = await self._send_art_request(
            {"request": "get_auto_rotation_status"}
        )
        assert data
        return data
 
    async def set_auto_rotation_status(self, duration=0, type=True, category=2):
        '''
        duration is "off" or "number" where number is duration in minutes. set 0 for 'off'
        slide show type can be "slideshow" or "shuffleslideshow", set True for shuffleslideshow
        category is 'MY-C0004' or 'MY-C0002' where 4 is favourites, 2 is my pictures, and 8 is store
        '''
        data = await self._send_art_request(
            {   "request": "set_auto_rotation_status",
                "value": str(duration) if duration > 0 else "off",
                "category_id": "MY-C000{}".format(category),
                "type": "shuffleslideshow" if type else "slideshow"
            }
        )
        assert data
        return data

    async def get_slideshow_status(self):
        data = await self._send_art_request(
            {"request": "get_slideshow_status"}
        )
        assert data
        return data

    async def set_slideshow_status(self, duration=0, type=True, category=2):
        '''
        duration is "off" or "number" where number is duration in minutes. set 0 for 'off'
        slide show type can be "slideshow" or "shuffleslideshow", set True for shuffleslideshow
        category is 'MY-C0004' or 'MY-C0002' where 4 is favourites, 2 is my pictures, and 8 is store
        '''
        data = await self._send_art_request(
            {   "request": "set_slideshow_status",
                "value": str(duration) if duration > 0 else "off",
                "category_id": "MY-C000{}".format(category),
                "type": "shuffleslideshow" if type else "slideshow"
            }
        )
        assert data
        return data

    async def get_brightness(self):
        data = await self._send_art_request(
            {"request": "get_brightness"}
        )
        if not data:
            data = await self.get_artmode_settings('brightness')
        assert data
        return data

    async def set_brightness(self, value):
        data = await self._send_art_request(
            {"request": "set_brightness", "value": value}
        )
        assert data
        return data
        
    async def get_color_temperature(self):
        data = await self._send_art_request(
            {"request": "get_color_temperature"}
        )
        if not data:
            data = await self.get_artmode_settings('color_temperature')
        assert data
        return data

    async def set_color_temperature(self, value):
        data = await self._send_art_request(
            {"request": "set_color_temperature", "value": value}
        )
        assert data
        return data
 
    async def get_thumbnail_list(self, content_id_list=[]):
        if isinstance(content_id_list, str):
            content_id_list=[content_id_list]
        content_id_list=[{"content_id": id} for id in content_id_list]
        data = await self._send_art_request(
            {
                "request": "get_thumbnail_list",
                "content_id_list": content_id_list,
                "conn_info": {
                    "d2d_mode": "socket",
                    "connection_id": random.randrange(4 * 1024 * 1024 * 1024),
                    "id": self.get_uuid(),#self.art_uuid,
                }
            }
        )
        assert data
        conn_info = json.loads(data["conn_info"])
        ssl_context = get_ssl_context() if conn_info.get('secured', False) else None
        reader, writer = await asyncio.open_connection(conn_info['ip'], int(conn_info['port']), ssl=ssl_context)
        total_num_thumbnails = 1
        current_thumb = -1
        thumbnail_data_dict = {}
        while current_thumb+1 < total_num_thumbnails:
            header_len = int.from_bytes(await reader.readexactly(4), "big")
            header = json.loads(await reader.readexactly(header_len))
            thumbnail_data_len = int(header["fileLength"])
            current_thumb = int(header["num"])
            total_num_thumbnails = int(header["total"])
            filename = "{}.{}".format(header["fileID"], header["fileType"])
            thumbnail_data_dict[filename] = await reader.readexactly(thumbnail_data_len)
        writer.close()
        return thumbnail_data_dict

    async def get_thumbnail(self, content_id_list=[], as_dict=False):
        if isinstance(content_id_list, str):
            content_id_list=[content_id_list]
        thumbnail_data_dict = {}
        thumbnail_data = None
        for content_id in content_id_list:
            data = await self._send_art_request(
                {
                    "request": "get_thumbnail",
                    "content_id": content_id,
                    "conn_info": {
                        "d2d_mode": "socket",
                        "connection_id": random.randrange(4 * 1024 * 1024 * 1024),
                        "id": self.get_uuid()
                    }
                }
            )
            assert data
            conn_info = json.loads(data["conn_info"])
            reader, writer = await asyncio.open_connection(conn_info['ip'], int(conn_info['port']))
            header_len = int.from_bytes(await reader.readexactly(4), "big")
            header = json.loads(await reader.readexactly(header_len))
            thumbnail_data_len = int(header["fileLength"])
            thumbnail_data = await reader.readexactly(thumbnail_data_len)
            writer.close()
            filename = "{}.{}".format(header["fileID"], header["fileType"])
            thumbnail_data_dict[filename] = thumbnail_data
        return thumbnail_data_dict if as_dict else list(thumbnail_data_dict.values()) if len(content_id_list) > 1 else thumbnail_data

    async def upload(self, file, matte="shadowbox_polar", portrait_matte="shadowbox_polar", file_type="png", date=None, timeout=10):
        '''
        NOTE: both id's and request_id have to be the same
        '''
        if isinstance(file, str):
            file_name, file_extension = os.path.splitext(file)
            file_type = file_extension[1:]
            with open(file, 'rb') as f:
                file = f.read()
                
        file_size = len(file)
        file_type = file_type.lower()
        if file_type == "jpeg":
            file_type = "jpg"
            
        if date is None:
            date = datetime.now().strftime("%Y:%m:%d %H:%M:%S")
        data = await self._send_art_request(
            {
                "request": "send_image",
                "file_type": file_type,
                "request_id" : self.get_uuid(),
                "id": self.art_uuid,
                "conn_info": {
                    "d2d_mode": "socket",
                    "connection_id": random.randrange(4 * 1024 * 1024 * 1024),
                    "id": self.art_uuid,
                },
                "image_date": date,
                "matte_id": matte or 'none',
                "portrait_matte_id": portrait_matte or 'none',
                "file_size": file_size,
            }
        )
        assert data
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

        ssl_context = get_ssl_context() if conn_info.get('secured', False) else None
        reader, writer = await asyncio.open_connection(conn_info['ip'], int(conn_info['port']), ssl=ssl_context)  
        writer.write(len(header).to_bytes(4, "big"))
        writer.write(header.encode("ascii"))
        writer.write(file)
        await writer.drain()
        writer.close()
        data = await self.wait_for_response("image_added", timeout=timeout)
        return data["content_id"] if data else None

    async def delete(self, content_id):
        await self.delete_list([content_id])

    async def delete_list(self, content_ids):
        content_id_list = [{"content_id": item} for item in content_ids]
        await self._send_art_request(
            {   "request": "delete_image_list",
                "content_id_list": content_id_list
            }
        )

    async def select_image(self, content_id, category=None, show=True):
        await self._send_art_request(
            {
                "request": "select_image",
                "category_id": category,
                "content_id": content_id,
                "show": show,
            }
        )

    async def get_artmode(self):
        data = await self._send_art_request(
            {
                "request": "get_artmode_status",
            }
        )
        assert data
        return data["value"]

    async def set_artmode(self, mode):
        await self._send_art_request(
            {
                "request": "set_artmode_status",
                "value": mode,
            }
        )
        
    async def get_rotation(self):
        data = await self._send_art_request(
            {"request": "get_current_rotation"}
        )
        assert data
        return data.get("current_rotation_status",0)

    async def get_photo_filter_list(self):
        data = await self._send_art_request(
            {"request": "get_photo_filter_list"}
        )
        assert data
        return json.loads(data["filter_list"])

    async def set_photo_filter(self, content_id, filter_id):
        await self._send_art_request(
            {
                "request": "set_photo_filter",
                "content_id": content_id,
                "filter_id": filter_id,
            }
        )

    async def get_matte_list(self, include_colour=False):
        data = await self._send_art_request(
            {"request": "get_matte_list"}
        )
        assert data
        return (json.loads(data["matte_type_list"]), json.loads(data.get("matte_color_list"))) if include_colour else json.loads(data["matte_type_list"])

    async def change_matte(self, content_id, matte_id=None, portrait_matte=None):
        '''
        matte is name_color eg flexible_polar or none
        NOTE: Not all mattes can be set for all image sizes!
        '''
        art_request = {
                        "request": "change_matte",
                        "content_id": content_id,
                        "matte_id": matte_id or 'none',
                      }
        if portrait_matte:
            art_request["portrait_matte_id"] = portrait_matte
        await self._send_art_request(art_request)
