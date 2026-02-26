# Audio Streaming

Audio RX/TX via the Icom audio UDP port (default 50003).

## Naming Map

Low-level Opus methods are now explicitly suffixed with `_opus`.
High-level PCM APIs are available for both RX and TX.

| Scope | Preferred method names |
|------|-------------------------|
| Low-level Opus (current) | `start_audio_rx_opus`, `stop_audio_rx_opus`, `start_audio_tx_opus`, `push_audio_tx_opus`, `stop_audio_tx_opus`, `start_audio_opus`, `stop_audio_opus` |
| High-level PCM | `start_audio_rx_pcm`, `stop_audio_rx_pcm`, `start_audio_tx_pcm`, `push_audio_tx_pcm`, `stop_audio_tx_pcm` |

Deprecated aliases still work during the deprecation window (two minor releases):
`start_audio_rx`, `stop_audio_rx`, `start_audio_tx`, `push_audio_tx`, `stop_audio_tx`, `start_audio`, `stop_audio`.

## AudioStream

::: icom_lan.audio.AudioStream

## Runtime Audio Stats (`get_audio_stats`)

Use `get_audio_stats()` on `AudioStream` or `IcomRadio` to retrieve a JSON-friendly
snapshot of live stream quality metrics.

```python
stats = radio.get_audio_stats()
print(stats["packet_loss_percent"], stats["jitter_ms"])
```

### Metrics, Units, Bounds

| Field | Unit | Bounds | Notes |
|------|------|--------|-------|
| `active` | boolean | `true/false` | Whether stream state is not `idle` |
| `state` | string | `idle` / `receiving` / `transmitting` | Current stream state |
| `rx_packets_received` | packets | `>= 0` | Parsed RX audio packets |
| `rx_packets_delivered` | packets | `>= 0` | RX packets delivered to callback |
| `tx_packets_sent` | packets | `>= 0` | TX packets sent |
| `packets_lost` | packets | `>= 0` | Inferred missing RX packets |
| `packet_loss_percent` | percent | `0.0..100.0` | `packets_lost / (delivered + lost)` |
| `jitter_ms` | milliseconds | `>= 0.0` | Smoothed sequence-jitter estimate |
| `jitter_max_ms` | milliseconds | `>= 0.0` | Peak observed jitter estimate |
| `underrun_count` | events | `>= 0` | Jitter-buffer underrun events |
| `overrun_count` | events | `>= 0` | Jitter-buffer overrun events |
| `estimated_latency_ms` | milliseconds | `>= 0.0` | Estimated buffering delay |
| `jitter_buffer_depth_packets` | packets | `>= 0` | Configured jitter depth (`0` when disabled) |
| `jitter_buffer_pending_packets` | packets | `>= 0` | Currently buffered packets |
| `duplicates_dropped` | packets | `>= 0` | Duplicate RX packets dropped |
| `stale_packets_dropped` | packets | `>= 0` | Stale/old RX packets dropped |
| `out_of_order_packets` | packets | `>= 0` | RX packets observed out of sequence |

## AudioPacket

::: icom_lan.audio.AudioPacket

## AudioState

::: icom_lan.audio.AudioState

## JitterBuffer

::: icom_lan.audio.JitterBuffer

## Packet Functions

::: icom_lan.audio.parse_audio_packet

::: icom_lan.audio.build_audio_packet

## Internal Transcoder Layer

`icom_lan` now includes an internal PCM<->Opus transcoder foundation used for
future high-level PCM APIs.

- Module: `icom_lan._audio_transcoder` (internal, no stability guarantee yet)
- Backend: optional `opuslib` (`pip install icom-lan[audio]`)
- Typed failures:
  - `AudioCodecBackendError` for missing backend
  - `AudioFormatError` for invalid PCM/Opus frame formats
  - `AudioTranscodeError` for codec encode/decode failures

## Usage

### RX Audio (callback-based)

```python
async with IcomRadio("192.168.1.100", username="u", password="p") as radio:
    received = []

    def on_audio(pkt):
        if pkt is not None:  # None = gap (missing packet)
            received.append(pkt.data)

    await radio.start_audio_rx_opus(on_audio)
    await asyncio.sleep(10)
    await radio.stop_audio_rx_opus()
```

### RX Audio (high-level PCM)

```python
async with IcomRadio("192.168.1.100", username="u", password="p") as radio:
    def on_pcm(frame: bytes | None) -> None:
        if frame is None:
            return  # gap placeholder from jitter buffer
        # frame is 16-bit little-endian PCM for configured format
        process_pcm(frame)

    await radio.start_audio_rx_pcm(
        on_pcm,
        sample_rate=48000,
        channels=1,
        frame_ms=20,
        jitter_depth=5,
    )
    await asyncio.sleep(10)
    await radio.stop_audio_rx_pcm()
```

### TX Audio (push-based)

```python
async with IcomRadio("192.168.1.100", username="u", password="p") as radio:
    await radio.start_audio_tx_opus()
    await radio.push_audio_tx_opus(opus_frame)
    await radio.stop_audio_tx_opus()
```

### TX Audio (high-level PCM)

```python
async with IcomRadio("192.168.1.100", username="u", password="p") as radio:
    await radio.start_audio_tx_pcm(sample_rate=48000, channels=1, frame_ms=20)
    await radio.push_audio_tx_pcm(pcm_frame)  # one 20ms PCM frame (1920 bytes)
    await radio.stop_audio_tx_pcm()
```

### Full-Duplex

```python
async with IcomRadio("192.168.1.100", username="u", password="p") as radio:
    await radio.start_audio_opus(rx_callback=on_audio, tx_enabled=True)
    # ... push TX frames, receive RX via callback ...
    await radio.stop_audio_opus()
```

### Codec Selection

```python
from icom_lan import IcomRadio, AudioCodec

radio = IcomRadio(
    "192.168.1.100",
    audio_codec=AudioCodec.PCM_1CH_16BIT,  # default
    audio_sample_rate=48000,
)
```

### Capability Introspection

Use the capability API to inspect negotiated client-side audio options and defaults:

```python
from icom_lan import IcomRadio

caps = IcomRadio.audio_capabilities()
print(caps.supported_codecs)
print(caps.supported_sample_rates_hz)
print(caps.supported_channels)
print(caps.default_codec, caps.default_sample_rate_hz, caps.default_channels)
```

Deterministic default selection rules:

1. Codec: first supported codec in icom-lan preference order.
2. Sample rate: highest supported sample rate.
3. Channels: the channel count implied by default codec (fallback: minimum supported channels).

!!! note "Opus codecs"
    `OPUS_1CH` (0x40) and `OPUS_2CH` (0x41) are only supported when
    the radio reports `connection_type == "WFVIEW"`. Standard connections
    use LPCM16 (0x04).

## Migration

Use the explicit `_opus` methods now:

| Deprecated alias | Replacement |
|------------------|-------------|
| `start_audio_rx` | `start_audio_rx_opus` |
| `stop_audio_rx` | `stop_audio_rx_opus` |
| `start_audio_tx` | `start_audio_tx_opus` |
| `push_audio_tx` | `push_audio_tx_opus` |
| `stop_audio_tx` | `stop_audio_tx_opus` |
| `start_audio` | `start_audio_opus` |
| `stop_audio` | `stop_audio_opus` |

For RX PCM, migrate callback-side decoding to the built-in API:

- Before: `start_audio_rx_opus()` + manual Opus decode in callback.
- Now: `start_audio_rx_pcm()` and receive `bytes | None` directly.

For TX PCM, migrate manual Opus encoding to the built-in API:

- Before: encode PCM to Opus yourself, then `push_audio_tx_opus()`.
- Now: `start_audio_tx_pcm()` and `push_audio_tx_pcm()` with fixed-size PCM frames.
