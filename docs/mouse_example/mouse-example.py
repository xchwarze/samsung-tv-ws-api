import asyncio
import concurrent
import json
import os

import websockets

from samsungtvws.remote import SamsungTVWS

TV_IP = "192.168.0.X"

if "X" in TV_IP:
    raise ValueError("Please set the IP address of your TV in the TV_IP variable")

token_file = os.path.dirname(os.path.realpath(__file__)) + "/tv-token.txt"
tv = SamsungTVWS(host=TV_IP, port=8002, token_file=token_file)

loop = asyncio.get_event_loop()
executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)


def move_tv_cursor(move_event):
    print(f"moving: {move_event}")
    tv.move_cursor(move_event["x"], move_event["y"])


def send_click_to_tv(event):
    key = event["key"]
    print(f"Clicked {key}")
    tv.send_key(key)


async def accept_client(websocket, path):
    print("New Web Client Connected")
    await websocket.send("Connected To TV<br/>Drag the ball to move the TV cursor")
    while True:
        msg = await websocket.recv()
        event = json.loads(msg)
        if event["type"] == "move":
            await loop.run_in_executor(executor, move_tv_cursor, event)
        elif event["type"] == "click":
            await loop.run_in_executor(executor, send_click_to_tv, event)


start_server = websockets.serve(accept_client, "localhost", 8888)

loop.run_until_complete(start_server)
loop.run_forever()
