"""WebSocket client with automatic reconnect.

Usage:
    python websocket_reconnect_client.py --url ws://localhost:8765 --interval 2
"""

import argparse
import asyncio

import websockets


async def run_client(url: str, interval: int) -> None:
    while True:
        try:
            print(f"Connecting to {url} ...")
            async with websockets.connect(url) as websocket:
                print("Connected. Sending heartbeat every 5 seconds.")
                count = 0
                while True:
                    count += 1
                    msg = f"heartbeat-{count}"
                    await websocket.send(msg)
                    response = await websocket.recv()
                    print(f"sent={msg} | recv={response}")
                    await asyncio.sleep(5)
        except (OSError, websockets.WebSocketException) as exc:
            print(f"Connection error: {exc}. Retrying in {interval}s...")
            await asyncio.sleep(interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WebSocket reconnecting client")
    parser.add_argument("--url", default="ws://localhost:8765", help="Server WebSocket URL")
    parser.add_argument("--interval", type=int, default=2, help="Reconnect delay in seconds")
    args = parser.parse_args()

    asyncio.run(run_client(args.url, args.interval))
