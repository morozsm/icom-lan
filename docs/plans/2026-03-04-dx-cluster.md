# DX Cluster Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Display real-time DX cluster spots as markers on the waterfall, with click-to-tune.

**Architecture:** Asyncio telnet client connects to DX cluster server, parses spot lines into DXSpot dataclasses, broadcasts to web clients via existing WebSocket control channel. Frontend renders spot markers on waterfall canvas overlay and provides click-to-tune. Feature is opt-in via `--dx-cluster` CLI flag.

**Tech Stack:** Python asyncio (stdlib telnet), existing WebSocket server, Canvas2D overlay

---

## Task 1: DXSpot dataclass + spot parser

**File:** `src/icom_lan/web/dx_cluster.py` (NEW)

1. Write test file `tests/test_dx_cluster.py`:
   ```python
   def test_parse_dxspider_spot():
       line = "DX de K1ABC:     14074.0  JA1XYZ       FT8 +05dB from PM95   1234Z"
       spot = parse_spot(line)
       assert spot.spotter == "K1ABC"
       assert spot.freq == 14074000  # Hz
       assert spot.call == "JA1XYZ"
       assert spot.comment == "FT8 +05dB from PM95"
   ```
   Add 10+ test cases: DXSpider, AR-Cluster, CC Cluster formats, edge cases (no comment, weird spacing, non-spot lines return None).

2. Run tests — verify they fail (RED).

3. Implement in `dx_cluster.py`:
   ```python
   @dataclass(frozen=True, slots=True)
   class DXSpot:
       spotter: str
       freq: int          # Hz
       call: str
       comment: str = ""
       time_utc: str = ""
       timestamp: float = field(default_factory=time.monotonic)
   
   _SPOT_RE = re.compile(r"^DX de\s+(\S+):\s+(\d+\.?\d*)\s+(\S+)\s+(.*?)\s+(\d{4}Z)?\s*$")
   
   def parse_spot(line: str) -> DXSpot | None:
       ...
   ```

4. Run tests — verify they pass (GREEN).

5. Commit: `feat(dx): DXSpot dataclass + spot parser with 10+ test cases`

---

## Task 2: DXClusterClient — asyncio telnet

**File:** `src/icom_lan/web/dx_cluster.py`

1. Write tests in `tests/test_dx_cluster.py`:
   - Test client connects and sends callsign login
   - Test client calls `on_spot` callback for each parsed line
   - Test client ignores non-spot lines
   - Test client reconnects after disconnect (exponential backoff)
   - Test client stop/cleanup
   - Use asyncio mock streams (`asyncio.StreamReader/Writer`)

2. Run tests — RED.

3. Implement:
   ```python
   class DXClusterClient:
       def __init__(self, host: str, port: int, callsign: str,
                    on_spot: Callable[[DXSpot], None]):
           ...
       
       async def start(self) -> None:
           """Connect and read spots in a loop. Auto-reconnects."""
           ...
       
       async def stop(self) -> None:
           """Disconnect and cancel tasks."""
           ...
   ```
   - `asyncio.open_connection(host, port)`
   - Read lines, parse each with `parse_spot()`
   - On disconnect: log, wait `min(2**attempt, 60)` seconds, retry
   - Login: send `callsign\n` after connect

4. Run tests — GREEN.

5. Commit: `feat(dx): DXClusterClient with auto-reconnect`

---

## Task 3: Spot buffer + REST API

**File:** `src/icom_lan/web/dx_cluster.py` + `src/icom_lan/web/server.py`

1. Write tests:
   - SpotBuffer: max 200 spots, oldest dropped on overflow
   - SpotBuffer: `get_spots(band=None)` returns filtered list
   - SpotBuffer: `to_json()` serialization
   - REST endpoint: `GET /api/v1/dx/spots` returns current spots

2. Run tests — RED.

3. Implement:
   ```python
   class SpotBuffer:
       def __init__(self, maxlen: int = 200):
           self._spots: deque[DXSpot] = deque(maxlen=maxlen)
       
       def add(self, spot: DXSpot) -> None: ...
       def get_spots(self, band: str | None = None) -> list[dict]: ...
       def expire(self, max_age_s: float = 1800) -> None: ...
   ```
   
   In `server.py`:
   - Add `SpotBuffer` instance
   - Add `GET /api/v1/dx/spots` route
   - On spot callback: add to buffer + broadcast via control WS

4. Run tests — GREEN.

5. Commit: `feat(dx): SpotBuffer + REST endpoint`

---

## Task 4: WebSocket broadcast

**File:** `src/icom_lan/web/server.py` + `src/icom_lan/web/handlers.py`

1. Write tests:
   - New spot → JSON message `{"type": "dx_spot", "spot": {...}}` sent to all control WS clients
   - Client connect → receives current spot buffer as `{"type": "dx_spots", "spots": [...]}`

2. Run tests — RED.

3. Implement:
   - `server._broadcast_dx_spot(spot)` — sends to all ControlHandler clients
   - `ControlHandler._send_state_snapshot()` — include current spots if DX cluster active
   - Message format: `{"type": "dx_spot", "spot": {"call": "JA1XYZ", "freq": 14074000, "spotter": "K1ABC", ...}}`

4. Run tests — GREEN.

5. Commit: `feat(dx): WebSocket spot broadcast`

---

## Task 5: CLI flags

**File:** `src/icom_lan/cli.py`

1. Write tests:
   - `--dx-cluster` flag parsed correctly (host:port)
   - `--callsign` flag parsed
   - Without `--dx-cluster` → no DX client started
   - Invalid format → clear error

2. Run tests — RED.

3. Implement:
   - `web` command: add `--dx-cluster HOST:PORT` and `--callsign CALL`
   - Pass to WebServer → start DXClusterClient if configured
   - Graceful shutdown: stop DX client on server stop

4. Run tests — GREEN.

5. Commit: `feat(dx): CLI --dx-cluster and --callsign flags`

---

## Task 6: Frontend — spot overlay on waterfall

**File:** `src/icom_lan/web/static/index.html`

1. No automated tests (canvas rendering). Manual testing.

2. Implement:
   - Listen for `dx_spot` / `dx_spots` WS messages
   - Store spots in `state.dxSpots[]`
   - In `renderLoop()`: draw spot markers on spectrum canvas
     - Only spots within current scope freq range
     - Marker: small triangle `▼` + callsign text
     - Color by age: bright cyan (fresh) → dim gray (>15 min) → remove (>30 min)
   - Click handler on spectrum canvas: if click near spot marker → `sendCommand('set_freq', {freq: spot.freq})`
   - DX toggle button in toolbar (shows/hides overlay + connects/disconnects)

3. Commit: `feat(dx): frontend spot overlay + click-to-tune`

---

## Task 7: Integration test + docs

1. Manual integration test:
   - Start server with `--dx-cluster dxc.nc7j.com:7373 --callsign KN4KYD`
   - Verify spots appear on waterfall
   - Click spot → radio tunes to frequency
   - Toggle DX off → spots disappear, telnet disconnects
   - Toggle DX on → reconnects, spots reappear

2. Update docs:
   - `docs/guide/cli.md` — add `--dx-cluster` and `--callsign` flags
   - `docs/guide/web-ui.md` — DX cluster section
   - `README.md` — mention DX cluster feature

3. Update issue #108 with implementation status

4. Commit: `docs: DX cluster setup guide`

5. Run full test suite: `uv run python -m pytest tests/ -q --tb=short`

---

## Agent Assignment (tmux)

| Agent | Tasks | Window |
|-------|-------|--------|
| **claude:dx-backend** | Tasks 1-3 (parser, client, buffer) | `agents:backend` |
| **claude:dx-frontend** | Task 6 (overlay, click-to-tune) | `agents:frontend` |
| **sequential** | Tasks 4-5, 7 (integration, CLI, docs) | after backend done |

Backend and frontend can run in parallel (no file conflicts).
