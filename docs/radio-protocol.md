# Radio Protocol — Multi-Backend Architecture

## Overview

The Radio Protocol defines a vendor-neutral interface for controlling amateur radio transceivers. Any backend that implements the `Radio` protocol can be used with the Web UI, rigctld server, and CLI without modification.

```
┌──────────────────────────────────────────────┐
│          Web UI  /  rigctld  /  CLI           │
├──────────────────────────────────────────────┤
│          Radio Protocol (core)                │
│  ┌──────────────┬─────────────┬────────────┐ │
│  │ AudioCapable │ ScopeCapable│ DualRxCap. │ │
│  └──────────────┴─────────────┴────────────┘ │
├────────┬──────────┬──────────┬───────────────┤
│IcomLAN │IcomSerial│ YaesuCAT │  Future...    │
└────────┴──────────┴──────────┴───────────────┘
```

## Core Protocol: `Radio`

Every backend **must** implement this. It covers the essentials that any transceiver supports.

```python
from icom_lan.radio_protocol import Radio

class MyRadio:
    """Implements Radio protocol."""

    async def connect(self) -> None: ...
    async def disconnect(self) -> None: ...
    
    @property
    def connected(self) -> bool: ...

    # Frequency (Hz)
    async def get_frequency(self, receiver: int = 0) -> int: ...
    async def set_frequency(self, freq: int, receiver: int = 0) -> None: ...

    # Mode → ("USB", filter_num_or_None)
    async def get_mode(self, receiver: int = 0) -> tuple[str, int | None]: ...
    async def set_mode(self, mode: str, filter_width: int | None = None, receiver: int = 0) -> None: ...

    # DATA mode (USB-D, LSB-D for digital modes)
    async def get_data_mode(self) -> bool: ...
    async def set_data_mode(self, on: bool) -> None: ...

    # TX
    async def set_ptt(self, on: bool) -> None: ...

    # Meters
    async def get_s_meter(self, receiver: int = 0) -> int: ...
    async def get_swr(self) -> float: ...

    # Power (0-255 normalised)
    async def get_power(self) -> int: ...
    async def set_power(self, level: int) -> None: ...

    # Levels (0-255 normalised)
    async def set_af_level(self, level: int) -> None: ...
    async def set_rf_gain(self, level: int) -> None: ...
    async def set_squelch(self, level: int) -> None: ...

    # State
    @property
    def radio_state(self) -> RadioState: ...
    @property
    def model(self) -> str: ...
    @property
    def capabilities(self) -> set[str]: ...

    # Server integration
    def set_state_change_callback(self, callback) -> None: ...
    def set_reconnect_callback(self, callback) -> None: ...
```

### Standard Mode Names

Cross-vendor mode strings used in `get_mode()` / `set_mode()`:

| Mode | Description |
|------|-------------|
| `USB` | Upper Sideband |
| `LSB` | Lower Sideband |
| `CW` | CW (normal) |
| `CWR` | CW Reverse |
| `AM` | Amplitude Modulation |
| `FM` | Frequency Modulation |
| `RTTY` | RTTY (normal) |
| `RTTYR` | RTTY Reverse |
| `PSK` | PSK |
| `DV` | D-STAR Digital Voice |
| `DD` | D-STAR Data |

### Standard Capability Tags

Returned by `radio.capabilities`:

| Tag | Meaning |
|-----|---------|
| `audio` | Audio streaming (RX/TX) |
| `scope` | Spectrum scope / panadapter |
| `dual_rx` | Dual independent receivers |
| `meters` | S-meter, SWR, power readings |
| `tx` | Transmit capability |
| `cw` | CW keyer |
| `attenuator` | Attenuator control |
| `preamp` | Preamplifier control |
| `rf_gain` | RF gain control |
| `af_level` | AF output level control |
| `squelch` | Squelch control |
| `nb` | Noise blanker |
| `nr` | Noise reduction |

## Optional Protocols

### `AudioCapable`

For radios that support audio streaming — either over LAN (Icom) or via USB audio device (serial-connected radios, Digirig).

```python
from icom_lan.radio_protocol import AudioCapable

if isinstance(radio, AudioCapable):
    await radio.start_audio_rx_opus(callback)
    await radio.push_audio_tx_opus(opus_data)
    await radio.stop_audio_rx_opus()
```

### `ScopeCapable`

For radios with spectrum/panadapter output.

```python
from icom_lan.radio_protocol import ScopeCapable

if isinstance(radio, ScopeCapable):
    await radio.enable_scope(span=100_000)
    await radio.disable_scope()
```

### `DualReceiverCapable`

For radios with two independent receivers (e.g. IC-7610 Main/Sub).

```python
from icom_lan.radio_protocol import DualReceiverCapable

if isinstance(radio, DualReceiverCapable):
    await radio.vfo_exchange()   # swap Main ↔ Sub
    await radio.vfo_equalize()   # Sub = Main
```

## Implementing a New Backend

1. Create a class that implements `Radio` (and optional protocols as needed)
2. Register it in the radio factory
3. The Web UI, rigctld, and CLI will work automatically

```python
from icom_lan.radio_protocol import Radio
from icom_lan.radio_state import RadioState, ReceiverState

class YaesuRadio:
    """Yaesu CAT protocol backend."""

    def __init__(self, port: str, model: str = "FTX-1"):
        self._port = port
        self._model = model
        self._state = RadioState()
        self._connected = False

    @property
    def model(self) -> str:
        return self._model

    @property
    def capabilities(self) -> set[str]:
        return {"meters", "tx"}  # no audio/scope over CAT

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def radio_state(self) -> RadioState:
        return self._state

    async def connect(self) -> None:
        # Open serial port, configure baud rate...
        self._connected = True

    async def disconnect(self) -> None:
        # Close serial port...
        self._connected = False

    async def get_frequency(self, receiver: int = 0) -> int:
        # Send "FA;" CAT command, parse response
        ...

    async def set_frequency(self, freq: int, receiver: int = 0) -> None:
        # Send "FA{freq:011d};" CAT command
        ...

    # ... implement remaining Radio methods ...

# Protocol compliance check:
assert isinstance(YaesuRadio("/dev/ttyUSB0"), Radio)
```

## Backend Comparison

| Feature | Icom LAN | Icom Serial | Yaesu CAT | Digirig |
|---------|----------|-------------|-----------|---------|
| **Transport** | UDP | USB Serial | USB Serial | USB Serial |
| **Protocol** | CI-V | CI-V | CAT | CAT/CI-V |
| **Audio** | LAN (Opus/PCM) | USB Audio Device | USB Audio Device | USB Audio Device |
| **Scope** | LAN | ❌ | ❌ | ❌ |
| **Dual RX** | ✅ (IC-7610) | ❌ | ❌ | ❌ |
| **Radios** | IC-7610, IC-7851 | IC-7300, IC-705 | FTX-1, FT-710, etc. | Any + 3.5mm |
