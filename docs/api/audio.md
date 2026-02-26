# Audio Streaming

Audio RX/TX via the Icom audio UDP port (default 50003).

## Naming Map

Low-level Opus methods are now explicitly suffixed with `_opus`.
High-level PCM names are reserved for upcoming APIs.

| Scope | Preferred method names |
|------|-------------------------|
| Low-level Opus (current) | `start_audio_rx_opus`, `stop_audio_rx_opus`, `start_audio_tx_opus`, `push_audio_tx_opus`, `stop_audio_tx_opus`, `start_audio_opus`, `stop_audio_opus` |
| High-level PCM (planned) | `start_audio_rx_pcm`, `stop_audio_rx_pcm`, `start_audio_tx_pcm`, `push_audio_tx_pcm`, `stop_audio_tx_pcm` |

Deprecated aliases still work during the deprecation window (two minor releases):
`start_audio_rx`, `stop_audio_rx`, `start_audio_tx`, `push_audio_tx`, `stop_audio_tx`, `start_audio`, `stop_audio`.

## AudioStream

::: icom_lan.audio.AudioStream

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

### TX Audio (push-based)

```python
async with IcomRadio("192.168.1.100", username="u", password="p") as radio:
    await radio.start_audio_tx_opus()
    await radio.push_audio_tx_opus(opus_frame)
    await radio.stop_audio_tx_opus()
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
