# Audio Streaming

Audio RX/TX via the Icom audio UDP port (default 50003).

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

## Usage

### RX Audio (callback-based)

```python
async with IcomRadio("192.168.1.100", username="u", password="p") as radio:
    received = []

    def on_audio(pkt):
        if pkt is not None:  # None = gap (missing packet)
            received.append(pkt.data)

    await radio.start_audio_rx(on_audio)
    await asyncio.sleep(10)
    await radio.stop_audio_rx()
```

### TX Audio (push-based)

```python
async with IcomRadio("192.168.1.100", username="u", password="p") as radio:
    await radio.start_audio_tx()
    await radio.push_audio_tx(opus_frame)
    await radio.stop_audio_tx()
```

### Full-Duplex

```python
async with IcomRadio("192.168.1.100", username="u", password="p") as radio:
    await radio.start_audio(rx_callback=on_audio, tx_enabled=True)
    # ... push TX frames, receive RX via callback ...
    await radio.stop_audio()
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
