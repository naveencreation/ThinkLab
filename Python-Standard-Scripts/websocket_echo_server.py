"""Simple WebSocket echo server.

Usage:
    python websocket_echo_server.py --host 0.0.0.0 --port 8765
"""

import argparse
import asyncio
import signal
from datetime import datetime

import websockets


async def handle_client(websocket: websockets.WebSocketServerProtocol) -> None:
    client = websocket.remote_address
    print(f"[connected] {client}")

    try:
        async for message in websocket:
            timestamp = datetime.now().strftime("%H:%M:%S")
            response = f"[{timestamp}] echo: {message}"
            await websocket.send(response)
    except websockets.ConnectionClosed:
        pass
    finally:
        print(f"[disconnected] {client}")


async def main(host: str, port: int) -> None:
    stop = asyncio.get_running_loop().create_future()

    def _stop() -> None:
        if not stop.done():
            stop.set_result(None)

    for sig in (signal.SIGINT, signal.SIGTERM):
        asyncio.get_running_loop().add_signal_handler(sig, _stop)

    async with websockets.serve(handle_client, host, port):
        print(f"WebSocket echo server started on ws://{host}:{port}")
        await stop


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WebSocket echo server")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host")
    parser.add_argument("--port", type=int, default=8765, help="Bind port")
    args = parser.parse_args()

    asyncio.run(main(args.host, args.port))
