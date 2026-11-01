"""SamsungTV Legacy (pre-2014, port 55000)."""

from __future__ import annotations

import asyncio
import base64
import logging
from types import TracebackType

from ..exceptions import ConnectionFailure, ResponseError, UnauthorizedError

LOGGER = logging.getLogger(__name__)

RESPONSE_ACCESS_GRANTED = b"\x64\x00\x01\x00"
RESPONSE_ACCESS_DENIED = b"\x64\x00\x00\x00"
RESPONSE_CONTROL_ACCEPTED = b"\x00\x00\x00\x00"
RESPONSE_WAITING_PREFIX = b"\x0a"
RESPONSE_CANCELLED_PREFIX = b"\x65"


def _serialize(data: str | bytes, *, raw: bool = False) -> bytes:
    """Serialize a field as a little-endian length prefix and the payload."""
    if isinstance(data, str):
        data = data.encode()
    if not raw:
        data = base64.b64encode(data)
    return len(data).to_bytes(2, "little") + data


class SamsungTVLegacyAsyncRemote:
    """Remote speaking the legacy binary protocol on port 55000.

    The TV asks the user to allow a remote the first time it connects and
    remembers it by ``name``. ``timeout`` also bounds that wait.
    """

    _reader: asyncio.StreamReader | None
    _writer: asyncio.StreamWriter | None

    def __init__(
        self,
        host: str,
        *,
        port: int = 55000,
        name: str = "SamsungTvRemote",
        description: str = "SamsungTvRemote",
        remote_id: str = "",
        timeout: float = 10,
    ) -> None:
        self._host = host
        self._port = port
        self._name = name
        self._description = description
        self._remote_id = remote_id
        self._timeout = timeout
        self._reader = None
        self._writer = None
        self._tv_name: str | None = None

    async def __aenter__(self) -> SamsungTVLegacyAsyncRemote:
        await self.open()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.close()

    @property
    def is_connected(self) -> bool:
        return self._writer is not None and not self._writer.is_closing()

    async def open(self) -> None:
        """Connect and wait for the user to allow the remote on the TV."""
        if self.is_connected:
            return

        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self._host, self._port), self._timeout
            )
        except (OSError, asyncio.TimeoutError) as err:
            raise ConnectionFailure(
                f"Cannot connect to {self._host}:{self._port}: {err!r}"
            ) from err

        payload = (
            b"\x64\x00"
            + _serialize(self._description)
            + _serialize(self._remote_id)
            + _serialize(self._name)
        )
        LOGGER.debug("Sending handshake to %s", self._host)
        try:
            await self._send(payload)
            await self._read_response(handshake=True)
        except BaseException:
            await self.close()
            raise

    async def close(self) -> None:
        writer, self._reader, self._writer = self._writer, None, None
        if writer is None:
            return
        writer.close()
        try:
            await writer.wait_closed()
        except OSError:
            LOGGER.debug("Error closing connection to %s", self._host)

    async def control(self, key: str) -> None:
        """Send a key press."""
        if not self.is_connected:
            raise ConnectionFailure("Connection is not open")

        LOGGER.debug("Sending control command %s to %s", key, self._host)
        await self._send(b"\x00\x00\x00" + _serialize(key))
        await self._read_response()

    async def _send(self, payload: bytes) -> None:
        if self._writer is None:
            raise ConnectionFailure("Connection is not open")
        # Frame: type byte, empty application string, then the payload.
        self._writer.write(
            b"\x00" + _serialize(b"", raw=True) + _serialize(payload, raw=True)
        )
        try:
            await self._writer.drain()
        except OSError as err:
            await self.close()
            raise ConnectionFailure(repr(err)) from err

    async def _read_response(self, *, handshake: bool = False) -> None:
        while True:
            response = await self._read_frame()

            if response == RESPONSE_ACCESS_GRANTED:
                LOGGER.debug("Access granted by %s", self._tv_name)
                return
            if response == RESPONSE_CONTROL_ACCEPTED:
                return
            if response == RESPONSE_ACCESS_DENIED:
                raise UnauthorizedError("Access denied by the TV")
            if response.startswith(RESPONSE_CANCELLED_PREFIX):
                raise UnauthorizedError("Authorization cancelled on the TV")
            if response.startswith(RESPONSE_WAITING_PREFIX):
                if handshake:
                    LOGGER.info("Waiting for authorization on %s", self._tv_name)
                continue
            raise ResponseError(f"Unhandled response: {response.hex()}")

    async def _read_frame(self) -> bytes:
        try:
            # The timeout also bounds how long the user has to allow the remote.
            response = await asyncio.wait_for(self._read_frame_payload(), self._timeout)
        except asyncio.TimeoutError as err:
            await self.close()
            raise ConnectionFailure("Timed out waiting for the TV") from err
        except (asyncio.IncompleteReadError, OSError) as err:
            await self.close()
            raise ConnectionFailure("Connection closed by the TV") from err

        if not response:
            await self.close()
            raise ConnectionFailure("Connection closed by the TV")
        return response

    async def _read_frame_payload(self) -> bytes:
        if self._reader is None:
            raise ConnectionFailure("Connection is not open")
        reader = self._reader
        header = await reader.readexactly(3)
        tv_name_length = int.from_bytes(header[1:3], "little")
        self._tv_name = (await reader.readexactly(tv_name_length)).decode(
            errors="replace"
        )
        length = int.from_bytes(await reader.readexactly(2), "little")
        return await reader.readexactly(length)
