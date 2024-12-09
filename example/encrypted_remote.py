import asyncio
import logging

import aiohttp

from samsungtvws.encrypted.remote import (
    SamsungTVEncryptedWSAsyncRemote,
    SendRemoteKey,
)

logging.basicConfig(level=logging.DEBUG)

HOST = "1.2.3.4"
PORT = 8000  # Warning: this can be different from the authenticator port

TOKEN = "b231074ae524245f4dd581154c112936"
SESSION_ID = "1"


async def main() -> None:
    """Get token."""
    async with aiohttp.ClientSession() as web_session:
        remote = SamsungTVEncryptedWSAsyncRemote(
            host=HOST,
            web_session=web_session,
            token=TOKEN,
            session_id=SESSION_ID,
            port=PORT,
        )
        await remote.start_listening()

        # Turn off
        await remote.send_command(SendRemoteKey.click("KEY_POWEROFF"))

        await asyncio.sleep(15)

        await remote.close()


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
