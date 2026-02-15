"""Interactive WebSocket client.

Usage:
    python websocket_interactive_client.py --url ws://localhost:8765
"""

import argparse
import asyncio

import websockets


async def sender(websocket: websockets.WebSocketClientProtocol) -> None:
    print("Type messages and press Enter. Type '/quit' to exit.")
    while True:
        text = await asyncio.to_thread(input, "> ")
        if text.strip().lower() in {"/quit", "exit", "q"}:
            await websocket.close()
            break
        await websocket.send(text)


async def receiver(websocket: websockets.WebSocketClientProtocol) -> None:
    try:
        async for msg in websocket:
            print(f"server: {msg}")
    except websockets.ConnectionClosed:
        print("Connection closed.")


async def main(url: str) -> None:
    async with websockets.connect(url) as websocket:
        await asyncio.gather(sender(websocket), receiver(websocket))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Interactive WebSocket client")
    parser.add_argument("--url", default="ws://localhost:8765", help="Server WebSocket URL")
    args = parser.parse_args()

    asyncio.run(main(args.url))
