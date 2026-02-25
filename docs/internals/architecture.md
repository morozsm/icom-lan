# Architecture

## Overview

```
┌─────────────────────────────────────────────────────┐
│                     icom-lan                         │
│                                                      │
│  ┌─────────┐   ┌──────────┐   ┌──────────────────┐  │
│  │  CLI    │   │  Public  │   │  Raw CI-V        │  │
│  │ (cli.py)│   │   API    │   │  (commands.py)   │  │
│  └────┬────┘   │(radio.py)│   └────────┬─────────┘  │
│       │        └────┬─────┘            │             │
│       └─────────────┤                  │             │
│                     │                  │             │
│            ┌────────┴──────────────────┴──────┐      │
│            │           IcomRadio               │      │
│            │   ┌──────────┐  ┌──────────┐     │      │
│            │   │  Control │  │   CI-V   │     │      │
│            │   │Transport │  │Transport │     │      │
│            │   │ (:50001) │  │ (:50002) │     │      │
│            │   └────┬─────┘  └────┬─────┘     │      │
│            │        ┌──────────────────────┐   │      │
│            │        │ IcomCommander queue  │   │      │
│            │        │ priorities/pacing    │   │      │
│            │        └──────────────────────┘   │      │
│            └────────┼─────────────┼───────────┘      │
│                     │             │                   │
└─────────────────────┼─────────────┼───────────────────┘
                      │   UDP       │   UDP
                      ▼             ▼
              ┌───────────────────────────┐
              │       Icom Radio          │
              │   Control  CI-V   Audio   │
              │   :50001  :50002  :50003  │
              └───────────────────────────┘
```

## Module Responsibilities

### `radio.py` — High-Level API

The central orchestrator. `IcomRadio` manages:

- **Two transport instances**: one for control (port 50001), one for CI-V (port 50002)
- **Full handshake sequence**: discovery → login → token → conninfo → CI-V open
- **Commander integration**: enqueues CI-V operations with priorities and pacing
- **CI-V command wrapping**: takes raw CI-V frames, wraps them in UDP data packets
- **Response filtering**: skips echoes, waterfall data, and control packets to find CI-V responses
- **State guardrails**: snapshot/restore helpers for safe test transactions
- **Public API methods**: `get_frequency()`, `set_mode()`, etc.

### `commander.py` — CI-V Command Queue

Serialized command execution layer inspired by wfview:

- **Priority queue** (`IMMEDIATE` / `NORMAL` / `BACKGROUND`)
- **Pacing/throttling** between commands (`ICOM_CIV_MIN_INTERVAL_MS`)
- **Dedupe** for background polling keys
- **Transaction helper** (`snapshot -> body -> restore`)

### `transport.py` — UDP Transport

Low-level asyncio UDP handler. Each `IcomTransport` instance manages:

- **UDP socket** via `asyncio.DatagramProtocol`
- **Discovery handshake** (Are You There → I Am Here → Are You Ready)
- **Keep-alive pings** (500ms interval)
- **Sequence tracking** with gap detection
- **Retransmit requests** for missing packets
- **Packet queue** for consumers

### `commands.py` — CI-V Encoding/Decoding

Pure functions for building and parsing CI-V frames:

- Frame construction with BCD frequency encoding
- Response parsing (frequency, mode, meters, ACK/NAK)
- No state, no I/O — purely data transformation

### `auth.py` — Authentication

Handles Icom's proprietary credential encoding and packet construction:

- `encode_credentials()` — substitution-table obfuscation
- `build_login_packet()` — 0x80-byte login packet
- `build_conninfo_packet()` — 0x90-byte connection info
- Response parsers for auth and status packets

### `protocol.py` — Packet Parsing

Header serialization/deserialization and packet type identification.

### `types.py` — Data Types

Enums (`PacketType`, `Mode`), dataclasses (`PacketHeader`, `CivFrame`), and BCD helpers.

### `exceptions.py` — Error Hierarchy

Custom exception classes for structured error handling.

### `cli.py` — Command Line Interface

Argparse-based CLI that wraps the async API with `asyncio.run()`.

## Data Flow

### Sending a Command

```
radio.get_frequency()
    → get_frequency() builds CI-V frame: FE FE 98 E0 03 FD
    → IcomCommander.enqueue(priority=normal, key=get_frequency)
    → _wrap_civ() adds UDP header (0x15-byte prefix)
    → _civ_transport.send_tracked() assigns sequence number
    → UDP packet sent to radio:50002
```

### Receiving a Response

```
UDP packet arrives on :50002
    → _UdpProtocol.datagram_received()
    → IcomTransport._handle_packet()
        → Check: retransmit request? ping? → handle internally
        → Otherwise: queue for consumer
    → IcomRadio._send_civ_raw() picks up from queue
        → Skip packets that are too small (control)
        → Scan payload for CI-V frames (FE FE ... FD)
        → Filter: skip echoes (from_addr == CONTROLLER), waterfall (cmd 0x27)
        → Match: response from radio with correct command byte
    → parse_frequency_response() extracts Hz from BCD data
```

## Key Design Decisions

### Dual-Port Architecture

CI-V commands **must** go through port 50002, not 50001. The control port (50001) is only for authentication and session management. This was discovered by tracing that the radio never responds to CI-V on the control port.

### GUID Echo

The radio won't report CI-V/audio ports in its status packet unless the client echoes the radio's GUID (bytes 0x20–0x2F from its conninfo) in the client's own conninfo. Without this, `civ_port` comes back as 0.

### Response Filtering

The CI-V port receives various traffic: our command echoes, waterfall data (cmd 0x27), and actual responses. `_send_civ_raw()` filters through all of this to find the matching response from the radio.

### Sequence Number Management

- `send_seq` — tracked data packets on each transport
- `ping_seq` — keep-alive pings (separate counter)
- `_auth_seq` — authentication sequence in radio.py
- `_civ_send_seq` — CI-V and OpenClose packets (separate from transport seq)

## Dependencies

```
icom-lan (runtime)
└── Python 3.11+ stdlib only
    ├── asyncio
    ├── struct
    ├── socket
    ├── logging
    └── dataclasses

icom-lan[dev] (testing)
├── pytest
└── pytest-asyncio

icom-lan[audio] (future)
└── opuslib
```
