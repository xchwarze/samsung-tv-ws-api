import asyncio
import logging

from samsungtvws.async_remote import SamsungTVWSAsyncRemote
from samsungtvws.remote import SendRemoteKey

logging.basicConfig(level=logging.DEBUG)

host = "1.2.3.4"
port = 8002


async def main():
    tv = SamsungTVWSAsyncRemote(host=host, port=port, token_file="token_file")
    await tv.start_listening()

    # Request app_list
    logging.info(await tv.app_list())

    # Turn off
    await tv.send_command(SendRemoteKey.click("KEY_POWER"))

    # Turn off (FrameTV)
    # await tv.send_command(SendRemoteKey.hold_key("KEY_POWER", 3))

    await asyncio.sleep(15)

    await tv.close()


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
