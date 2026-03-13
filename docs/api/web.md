# Web Server

Built-in web UI and REST API.

## Modules

- `server.py` — HTTP server (Starlette/Uvicorn)
- `handlers.py` — WebSocket command handlers
- `radio_poller.py` — State polling for /api/v1/state endpoint
- `websocket.py` — WebSocket connection management
- `protocol.py` — Web protocol types and messages
- `dx_cluster.py` — DX cluster integration

## REST API

See [Web UI Guide](../guide/web-ui.md) for endpoint documentation.

## See Also

- [Audio](audio.md)
- [Scope](scope.md)
