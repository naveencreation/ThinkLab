# Python Standard WebSocket Scripts

This folder contains ready-to-run WebSocket scripts you can reuse and extend.

## Files

- `websocket_echo_server.py` - basic echo server.
- `websocket_interactive_client.py` - terminal client for manual testing.
- `websocket_broadcast_server.py` - multi-client broadcast chat server.
- `websocket_reconnect_client.py` - client with auto-reconnect + heartbeat.

## Install

```bash
pip install websockets
```

## Quick run

```bash
python websocket_echo_server.py --host 0.0.0.0 --port 8765
python websocket_interactive_client.py --url ws://localhost:8765
```
