"""
SamsungTVWS - Samsung Smart TV WS API wrapper

Copyright (C) 2019 Xchwarze

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
from asyncio import Future, TimeoutError as AsyncioTimeoutError
import logging
from typing import Any, Dict, List, Optional, Set

import async_timeout

from . import async_connection, remote, rest
from .event import ED_INSTALLED_APP_EVENT, parse_installed_app

_LOGGING = logging.getLogger(__name__)


class SamsungTVWSAsyncRemote(async_connection.SamsungTVWSAsyncConnection):
    def __init__(
        self,
        host: str,
        token: Optional[str] = None,
        token_file: Optional[str] = None,
        port: int = 8001,
        timeout: Optional[float] = None,
        key_press_delay: float = 1,
        name: str = "SamsungTvRemote",
    ) -> None:
        super().__init__(
            host,
            endpoint=remote.REMOTE_ENDPOINT,
            token=token,
            token_file=token_file,
            port=port,
            timeout=timeout,
            key_press_delay=key_press_delay,
            name=name,
        )
        self._rest_api: Optional[rest.SamsungTVRest] = None
        self._app_list_futures: Set[Future[Dict[str, Any]]] = set()

    async def app_list(self) -> Optional[List[Dict[str, Any]]]:
        _LOGGING.debug("Get app list (not available on all TVs)")
        # See https://github.com/xchwarze/samsung-tv-ws-api/issues/23
        app_list_future: Future[Dict[str, Any]] = Future()
        self._app_list_futures.add(app_list_future)
        await self.send_command(remote.ChannelEmitCommand.get_installed_app())

        try:
            async with async_timeout.timeout(self.timeout):
                response = await app_list_future
        except AsyncioTimeoutError as err:
            _LOGGING.debug("Failed to get app list: %s", err)
            return None
        return parse_installed_app(response)

    def _websocket_event(self, event: str, response: Dict[str, Any]) -> None:
        """Handle websocket event."""
        super()._websocket_event(event, response)
        if event == ED_INSTALLED_APP_EVENT:
            while self._app_list_futures:
                self._app_list_futures.pop().set_result(response)
