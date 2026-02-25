# IcomRadio

The main entry point for controlling an Icom transceiver over LAN.

## Class: `IcomRadio`

```python
from icom_lan import IcomRadio
```

### Constructor

```python
IcomRadio(
    host: str,
    port: int = 50001,
    username: str = "",
    password: str = "",
    radio_addr: int = 0x98,
    timeout: float = 5.0,
    audio_codec: AudioCodec | int = AudioCodec.PCM_1CH_16BIT,
    audio_sample_rate: int = 48000,
    auto_reconnect: bool = False,
    reconnect_delay: float = 2.0,
    reconnect_max_delay: float = 60.0,
    watchdog_timeout: float = 30.0,
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `host` | `str` | *required* | Radio IP address or hostname |
| `port` | `int` | `50001` | Control port number |
| `username` | `str` | `""` | Authentication username |
| `password` | `str` | `""` | Authentication password |
| `radio_addr` | `int` | `0x98` | CI-V address of the radio |
| `timeout` | `float` | `5.0` | Default timeout for all operations (seconds) |

Additional optional parameters:

- `audio_codec`, `audio_sample_rate` — audio stream configuration
- `auto_reconnect`, `reconnect_delay`, `reconnect_max_delay`, `watchdog_timeout` — reconnect/watchdog behavior

### Context Manager

`IcomRadio` supports `async with` for automatic connection management:

```python
async with IcomRadio("192.168.1.100", username="u", password="p") as radio:
    freq = await radio.get_frequency()
# Disconnect happens automatically
```

Equivalent to:

```python
radio = IcomRadio("192.168.1.100", username="u", password="p")
await radio.connect()
try:
    freq = await radio.get_frequency()
finally:
    await radio.disconnect()
```

---

## Properties

### `connected`

```python
@property
def connected(self) -> bool
```

Whether the radio is currently connected and ready for commands.

---

## Connection Methods

### `connect()`

```python
async def connect(self) -> None
```

Open connection to the radio and authenticate. Performs the full handshake:

1. Discovery (Are You There → I Am Here)
2. Login with credentials
3. Token acknowledgement
4. Conninfo exchange
5. CI-V data stream open

**Raises:**

| Exception | When |
|-----------|------|
| `ConnectionError` | UDP connection failed |
| `AuthenticationError` | Login rejected |
| `TimeoutError` | Radio didn't respond |

### `disconnect()`

```python
async def disconnect(self) -> None
```

Cleanly disconnect from the radio. Closes the CI-V data stream and both UDP connections.

---

## Frequency

### `get_frequency()`

```python
async def get_frequency(self) -> int
```

Get the current operating frequency in **Hz**.

**Returns:** `int` — frequency in Hz (e.g., `14074000`)

### `set_frequency()`

```python
async def set_frequency(self, freq_hz: int) -> None
```

Set the operating frequency.

| Parameter | Type | Description |
|-----------|------|-------------|
| `freq_hz` | `int` | Frequency in Hz |

**Raises:** `CommandError` if the radio rejects the frequency.

---

## Mode

### `get_mode()`

```python
async def get_mode(self) -> Mode
```

Get the current operating mode.

**Returns:** `Mode` enum value (e.g., `Mode.USB`)

### `get_mode_info()`

```python
async def get_mode_info(self) -> tuple[Mode, int | None]
```

Get current mode and filter number (if radio reports filter in response).

### `get_filter()` / `set_filter()`

```python
async def get_filter(self) -> int | None
async def set_filter(self, filter_width: int) -> None
```

Read/set current filter number (1-3) while preserving mode.

### `set_mode()`

```python
async def set_mode(self, mode: Mode | str, filter_width: int | None = None) -> None
```

Set the operating mode.

| Parameter | Type | Description |
|-----------|------|-------------|
| `mode` | `Mode \| str` | Mode enum or name string (`"USB"`, `"CW"`, etc.) |

**Raises:** `CommandError` if the radio rejects the mode.

---

## Power

### `get_power()`

```python
async def get_power(self) -> int
```

Get the RF power level.

**Returns:** `int` — power level (0–255)

### `set_power()`

```python
async def set_power(self, level: int) -> None
```

Set the RF power level.

| Parameter | Type | Description |
|-----------|------|-------------|
| `level` | `int` | Power level 0–255 |

---

## Meters

### `get_s_meter()`

```python
async def get_s_meter(self) -> int
```

Read the S-meter value. **Returns:** `int` (0–255)

### `get_swr()`

```python
async def get_swr(self) -> int
```

Read the SWR meter value (TX only). **Returns:** `int` (0–255)

**Raises:** `TimeoutError` if not transmitting.

### `get_alc()`

```python
async def get_alc(self) -> int
```

Read the ALC meter value (TX only). **Returns:** `int` (0–255)

**Raises:** `TimeoutError` if not transmitting.

---

## PTT

### `set_ptt()`

```python
async def set_ptt(self, on: bool) -> None
```

Toggle Push-To-Talk.

| Parameter | Type | Description |
|-----------|------|-------------|
| `on` | `bool` | `True` = TX, `False` = RX |

---

## VFO & Split

### `select_vfo()`

```python
async def select_vfo(self, vfo: str = "A") -> None
```

Select the active VFO.

| Value | Description |
|-------|-------------|
| `"A"` | VFO A |
| `"B"` | VFO B |
| `"MAIN"` | Main receiver (IC-7610) |
| `"SUB"` | Sub receiver (IC-7610) |

### `vfo_equalize()`

```python
async def vfo_equalize(self) -> None
```

Send the CI-V A=B command. On MAIN/SUB radios (e.g. IC-7610), practical semantics can differ from a literal MAIN→SUB copy depending on rig state.

### `vfo_exchange()`

```python
async def vfo_exchange(self) -> None
```

Swap VFO A and VFO B.

### `set_split_mode()`

```python
async def set_split_mode(self, on: bool) -> None
```

Enable or disable split mode (TX on VFO B, RX on VFO A).

---

## Attenuator & Preamp

All attenuator and preamp methods use **Command29 framing** for dual-receiver
radio compatibility (IC-7610). The `receiver` parameter defaults to `RECEIVER_MAIN` (0).

### `get_attenuator_level()`

```python
async def get_attenuator_level(self, receiver: int = RECEIVER_MAIN) -> int
```

Read attenuator level in dB (0, 3, 6, ..., 45).

### `get_attenuator()`

```python
async def get_attenuator(self) -> bool
```

Read attenuator state as boolean (compatibility wrapper).

### `set_attenuator_level()`

```python
async def set_attenuator_level(self, db: int, receiver: int = RECEIVER_MAIN) -> None
```

Set attenuator level in dB. IC-7610 supports 0–45 in 3 dB steps.

**Raises:** `ValueError` if `db` is not a valid step.

### `set_attenuator()`

```python
async def set_attenuator(self, on: bool, receiver: int = RECEIVER_MAIN) -> None
```

Toggle attenuator (compatibility wrapper: on=18 dB, off=0 dB).

### `get_preamp()`

```python
async def get_preamp(self, receiver: int = RECEIVER_MAIN) -> int
```

Read preamp level.

### `set_preamp()`

```python
async def set_preamp(self, level: int = 1, receiver: int = RECEIVER_MAIN) -> None
```

Set the preamp level.

| Level | Description |
|-------|-------------|
| `0` | Off |
| `1` | PREAMP 1 |
| `2` | PREAMP 2 |

| Receiver | Constant | Value |
|----------|----------|-------|
| Main | `RECEIVER_MAIN` | `0x00` |
| Sub | `RECEIVER_SUB` | `0x01` |

---

## CW

### `send_cw_text()`

```python
async def send_cw_text(self, text: str) -> None
```

Send CW text via the radio's built-in keyer. Long messages are automatically split into 30-character chunks.

### `stop_cw_text()`

```python
async def stop_cw_text(self) -> None
```

Stop CW sending in progress.

---

## Power Control

### `power_control()`

```python
async def power_control(self, on: bool) -> None
```

Remote power on/off. Requires the radio to maintain network connectivity in standby.

---

## State Guardrails

### `snapshot_state()` / `restore_state()`

```python
async def snapshot_state(self) -> dict[str, object]
async def restore_state(self, state: dict[str, object]) -> None
```

Best-effort helpers for preserving and restoring rig state in integration workflows.

### `run_state_transaction()`

```python
async def run_state_transaction(self, body: Callable[[], Awaitable[None]]) -> None
```

Run an operation with automatic snapshot/restore guard.

## Raw CI-V

### `send_civ()`

```python
async def send_civ(
    self,
    command: int,
    sub: int | None = None,
    data: bytes | None = None,
) -> CivFrame
```

Send an arbitrary CI-V command and return the response.

| Parameter | Type | Description |
|-----------|------|-------------|
| `command` | `int` | CI-V command byte |
| `sub` | `int \| None` | Optional sub-command byte |
| `data` | `bytes \| None` | Optional payload data |

**Returns:** `CivFrame` with the radio's response.
