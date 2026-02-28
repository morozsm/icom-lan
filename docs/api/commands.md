# Commands Module

Low-level CI-V command encoding and decoding. Most users should use the high-level [`IcomRadio`](radio.md) API.

::: icom_lan.commands

## CI-V Frame Format

```
FE FE <to> <from> <cmd> [<sub>] [<data>...] FD
```

- `FE FE` — preamble (2 bytes)
- `<to>` — destination CI-V address (1 byte)
- `<from>` — source CI-V address (1 byte)
- `<cmd>` — command byte (1 byte)
- `<sub>` — optional sub-command (1 byte)
- `<data>` — optional payload (variable length)
- `FD` — terminator (1 byte)

## Constants

```python
from icom_lan import IC_7610_ADDR, CONTROLLER_ADDR

IC_7610_ADDR   # 0x98 — IC-7610's default CI-V address
CONTROLLER_ADDR  # 0xE0 — Controller address (us)
```

## Frame Building

### `build_civ_frame()`

```python
def build_civ_frame(
    to_addr: int,
    from_addr: int,
    command: int,
    sub: int | None = None,
    data: bytes | None = None,
) -> bytes
```

Build a raw CI-V frame.

### `parse_civ_frame()`

```python
def parse_civ_frame(data: bytes) -> CivFrame
```

Parse raw bytes into a `CivFrame` dataclass.

## Command Builders

Each function returns raw CI-V frame bytes ready to send.

### Frequency

```python
get_frequency(to_addr=0x98) -> bytes
set_frequency(freq_hz: int, to_addr=0x98) -> bytes
```

### Mode

```python
get_mode(to_addr=0x98) -> bytes
set_mode(mode: Mode, filter_width: int | None = None, to_addr=0x98) -> bytes
```

### Power

```python
get_power(to_addr=0x98) -> bytes
set_power(level: int, to_addr=0x98) -> bytes
```

### Meters

```python
get_s_meter(to_addr=0x98) -> bytes
get_swr(to_addr=0x98) -> bytes
get_alc(to_addr=0x98) -> bytes
```

### PTT

```python
ptt_on(to_addr=0x98) -> bytes
ptt_off(to_addr=0x98) -> bytes
```

### VFO

```python
select_vfo(vfo: str = "A", to_addr=0x98) -> bytes
vfo_a_equals_b(to_addr=0x98) -> bytes
vfo_swap(to_addr=0x98) -> bytes
set_split(on: bool, to_addr=0x98) -> bytes
```

### RF Controls (Command29-aware)

All RF control commands use `build_cmd29_frame()` for dual-receiver compatibility.

```python
# Frame builder for Command29-wrapped commands
build_cmd29_frame(to_addr, from_addr, command, sub=None, data=None, receiver=RECEIVER_MAIN) -> bytes

# Attenuator
get_attenuator(to_addr=0x98, receiver=RECEIVER_MAIN) -> bytes
set_attenuator_level(db: int, to_addr=0x98, receiver=RECEIVER_MAIN) -> bytes
set_attenuator(on: bool, to_addr=0x98, receiver=RECEIVER_MAIN) -> bytes  # compat

# Preamp
get_preamp(to_addr=0x98, receiver=RECEIVER_MAIN) -> bytes
set_preamp(level: int = 1, to_addr=0x98, receiver=RECEIVER_MAIN) -> bytes

# DIGI-SEL
get_digisel(to_addr=0x98, receiver=RECEIVER_MAIN) -> bytes
set_digisel(on: bool, to_addr=0x98, receiver=RECEIVER_MAIN) -> bytes
```

Constants: `RECEIVER_MAIN = 0x00`, `RECEIVER_SUB = 0x01`

### CW

```python
send_cw(text: str, to_addr=0x98) -> list[bytes]  # Returns multiple frames
stop_cw(to_addr=0x98) -> bytes
```

### Power Control

```python
power_on(to_addr=0x98) -> bytes
power_off(to_addr=0x98) -> bytes
```

## Response Parsers

### `parse_frequency_response()`

```python
def parse_frequency_response(frame: CivFrame) -> int
```

Parse a frequency response to Hz. **Raises** `ValueError` if not a frequency response.

### `parse_mode_response()`

```python
def parse_mode_response(frame: CivFrame) -> tuple[Mode, int | None]
```

Parse a mode response. Returns `(mode, filter_width)`.

### `parse_meter_response()`

```python
def parse_meter_response(frame: CivFrame) -> int
```

Parse a meter response to 0–255 int.

### `parse_ack_nak()`

```python
def parse_ack_nak(frame: CivFrame) -> bool | None
```

Check if frame is ACK (`True`), NAK (`False`), or neither (`None`).

## CI-V Command Codes

| Code | Command |
|------|---------|
| `0x03` | Read frequency |
| `0x04` | Read mode |
| `0x05` | Set frequency |
| `0x06` | Set mode |
| `0x07` | VFO select / equalize / swap |
| `0x0F` | Split on/off |
| `0x11` | Attenuator |
| `0x14` | Levels (RF power, etc.) |
| `0x15` | Meter readings |
| `0x16` | Preamp |
| `0x17` | CW keying |
| `0x18` | Power on/off |
| `0x27` | Scope/waterfall |
| `0x1C` | PTT / transceiver status |
| `0xFB` | ACK (command accepted) |
| `0xFA` | NAK (command rejected) |
