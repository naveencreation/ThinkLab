"""WebSocket broadcast chat server.

Every message from one client is sent to all connected clients.

Usage:
    python websocket_broadcast_server.py --host 0.0.0.0 --port 9001
"""

import argparse
import asyncio
import signal
from datetime import datetime
from typing import Set

import websockets

CLIENTS: Set[websockets.WebSocketServerProtocol] = set()


async def broadcast(message: str) -> None:
    if CLIENTS:
        await asyncio.gather(*(client.send(message) for client in CLIENTS), return_exceptions=True)


async def handle_client(websocket: websockets.WebSocketServerProtocol) -> None:
    client = websocket.remote_address
    CLIENTS.add(websocket)
    await broadcast(f"[system] client joined: {client}")
    print(f"[connected] {client} (total={len(CLIENTS)})")

    try:
        async for message in websocket:
            stamp = datetime.now().strftime("%H:%M:%S")
            await broadcast(f"[{stamp}] {client}: {message}")
    except websockets.ConnectionClosed:
        pass
    finally:
        CLIENTS.discard(websocket)
        await broadcast(f"[system] client left: {client}")
        print(f"[disconnected] {client} (total={len(CLIENTS)})")


async def main(host: str, port: int) -> None:
    stop = asyncio.get_running_loop().create_future()

    def _stop() -> None:
        if not stop.done():
            stop.set_result(None)

    for sig in (signal.SIGINT, signal.SIGTERM):
        asyncio.get_running_loop().add_signal_handler(sig, _stop)

    async with websockets.serve(handle_client, host, port):
        print(f"WebSocket broadcast server started on ws://{host}:{port}")
        await stop


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WebSocket broadcast server")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host")
    parser.add_argument("--port", type=int, default=9001, help="Bind port")
    args = parser.parse_args()

    asyncio.run(main(args.host, args.port))
