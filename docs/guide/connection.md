# Connection Lifecycle

Understanding the connection sequence helps with debugging and advanced usage.

## Overview

```
Client                                          Radio
  │                                               │
  │──── Are You There (0x03) ────────────────────>│
  │<─── I Am Here (0x04) ─────────────────────────│
  │──── Are You Ready (0x06) ────────────────────>│
  │<─── I Am Ready (0x06) ────────────────────────│
  │                                               │
  │──── Login (0x80 bytes) ──────────────────────>│
  │<─── Auth Response (0x60 bytes) ───────────────│
  │──── Token Ack (0x40 bytes) ──────────────────>│
  │                                               │
  │<─── Radio Conninfo (0x90 bytes) ──────────────│
  │──── Client Conninfo (0x90 bytes) ────────────>│
  │<─── Status (0x50 bytes, CI-V/audio ports) ────│
  │                                               │
  │════ CI-V Port (50002) ════════════════════════│
  │──── OpenClose (open) ────────────────────────>│
  │                                               │
  │──── CI-V commands... ────────────────────────>│
  │<─── CI-V responses... ────────────────────────│
  │                                               │
  │──── Ping (every 500ms) ──────────────────────>│
  │<─── Pong ─────────────────────────────────────│
```

## Phase 1: Discovery

The client sends **"Are You There"** (type `0x03`) packets until the radio responds with **"I Am Here"** (type `0x04`). This exchange establishes the radio's connection ID.

```python
# Automatic — handled by IcomTransport.connect()
await transport.connect("192.168.1.100", 50001)
```

- Up to 10 retries, 1 second timeout each
- Radio responds with its `remote_id` (4-byte identifier)
- Followed by "Are You Ready" / "I Am Ready" exchange

## Phase 2: Authentication

After discovery, the client sends a **login packet** (0x80 bytes) containing:

- Encoded username (position-dependent substitution cipher)
- Encoded password (same encoding)
- Client computer name

The radio responds with an **auth response** (0x60 bytes) containing:

- Session **token** (4 bytes) — used for all subsequent authenticated packets
- **Token request ID** — must be echoed back
- Connection type string (e.g., "FTTH")
- Error code (0 = success)

The client then sends a **token acknowledgement** (0x40 bytes) to confirm.

!!! note "Credential Encoding"
    Credentials are obfuscated using a substitution table, not encrypted. This is Icom's protocol design. See [Security](../SECURITY.md) for implications.

## Phase 3: Conninfo Exchange

The radio sends its **conninfo** (0x90 bytes) containing its GUID/MAC. The client must:

1. Extract the radio's GUID (bytes 0x20–0x2F)
2. Echo it back in the client's own conninfo packet
3. Include audio codec preferences and port information

This triggers the radio to send a **status packet** (0x50 bytes) containing:

- **CI-V port** number (usually 50002)
- **Audio port** number (usually 50003)

!!! important "GUID is Required"
    If the client doesn't echo the radio's GUID, the status packet will report CI-V port = 0, and commands won't work.

## Phase 4: CI-V Data Stream

The library opens a **second UDP connection** to the CI-V port (50002) and sends an **OpenClose** packet to start the CI-V data stream.

Once open, CI-V commands flow through port 50002 (not the control port 50001).

CI-V calls are then serialized through an internal commander queue (wfview-style), with pacing and retry logic to reduce real-hardware flakiness.

## Keep-Alive

Both ports maintain keep-alive with **ping packets** every 500ms. If the radio doesn't receive pings, it drops the connection after a timeout.

The library also handles:

- **Retransmit requests** — if the radio detects missing packets, it requests retransmission
- **Sequence tracking** — all data packets have sequence numbers for ordering and gap detection

## Disconnection

Clean disconnect sends:

1. **OpenClose(close)** on the CI-V port
2. **Disconnect** control packet on the control port
3. UDP sockets are closed

```python
# Automatic with context manager
async with IcomRadio(...) as radio:
    ...  # Disconnect happens on exit

# Manual
await radio.disconnect()
```

## Connection States

```python
from icom_lan import ConnectionState

# Available states
ConnectionState.DISCONNECTED  # Not connected
ConnectionState.CONNECTING    # Handshake in progress
ConnectionState.CONNECTED     # Ready for commands
```

## Error Handling

```python
from icom_lan import IcomRadio
from icom_lan.exceptions import (
    ConnectionError,
    AuthenticationError,
    TimeoutError,
)

try:
    async with IcomRadio("192.168.1.100", username="u", password="p") as radio:
        freq = await radio.get_frequency()
except ConnectionError as e:
    print(f"Can't reach radio: {e}")
except AuthenticationError as e:
    print(f"Wrong credentials: {e}")
except TimeoutError as e:
    print(f"Radio not responding: {e}")
```
