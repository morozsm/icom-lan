# Audio Recipes (copy/paste)

Practical scenarios for the current `icom-lan` audio API.
All examples use **PCM 16-bit mono 48 kHz** (`AudioCodec.PCM_1CH_16BIT`) to avoid external codec dependencies.

## Prerequisites

```bash
export ICOM_HOST=192.168.1.100
export ICOM_USER=YOUR_USER
export ICOM_PASS=YOUR_PASS
```

```bash
pip install "icom-lan[audio]"
```

---

## 1) RX → WAV file (10 seconds)

Saves the incoming audio stream from the radio to `rx.wav`.

```python
import asyncio
import wave

from icom_lan import IcomRadio, AudioCodec

SAMPLE_RATE = 48000
CHANNELS = 1
SECONDS = 10


async def main() -> None:
    frames: list[bytes] = []

    radio = IcomRadio(
        host="192.168.1.100",
        username="YOUR_USER",
        password="YOUR_PASS",
        audio_codec=AudioCodec.PCM_1CH_16BIT,
        audio_sample_rate=SAMPLE_RATE,
    )

    def on_audio(pkt) -> None:
        # For PCM codec, pkt.data contains raw PCM bytes.
        frames.append(pkt.data)

    async with radio:
        await radio.start_audio_rx_opus(on_audio)
        await asyncio.sleep(SECONDS)
        await radio.stop_audio_rx_opus()

    with wave.open("rx.wav", "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(b"".join(frames))


asyncio.run(main())
```

---

## 2) WAV file → TX (high-level PCM API)

Reads `tx.wav` (16-bit mono 48 kHz PCM) and transmits it.

```python
import asyncio
import wave

from icom_lan import IcomRadio, AudioCodec

SAMPLE_RATE = 48000
CHANNELS = 1
SAMPLE_WIDTH = 2
FRAME_MS = 20
BYTES_PER_FRAME = SAMPLE_RATE * CHANNELS * SAMPLE_WIDTH * FRAME_MS // 1000  # 1920


async def main() -> None:
    radio = IcomRadio(
        host="192.168.1.100",
        username="YOUR_USER",
        password="YOUR_PASS",
        audio_codec=AudioCodec.PCM_1CH_16BIT,
        audio_sample_rate=SAMPLE_RATE,
    )

    with wave.open("tx.wav", "rb") as wf:
        assert wf.getnchannels() == CHANNELS, "tx.wav must be mono"
        assert wf.getframerate() == SAMPLE_RATE, "tx.wav must be 48kHz"
        assert wf.getsampwidth() == SAMPLE_WIDTH, "tx.wav must be 16-bit"
        pcm = wf.readframes(wf.getnframes())

    async with radio:
        await radio.start_audio_tx_pcm(
            sample_rate=SAMPLE_RATE,
            channels=CHANNELS,
            frame_ms=FRAME_MS,
        )
        try:
            for i in range(0, len(pcm), BYTES_PER_FRAME):
                chunk = pcm[i : i + BYTES_PER_FRAME]
                if not chunk:
                    break
                await radio.push_audio_tx_pcm(chunk)
                await asyncio.sleep(FRAME_MS / 1000)
        finally:
            await radio.stop_audio_tx_pcm()


asyncio.run(main())
```

---

## 3) Full-duplex loopback test (dry-run style)

Simultaneously:
- starts RX and counts incoming packets,
- sends a 10-second test tone on TX.

```python
import asyncio
import math
import struct

from icom_lan import IcomRadio, AudioCodec

SAMPLE_RATE = 48000
CHANNELS = 1
SAMPLE_WIDTH = 2
FRAME_MS = 20
BYTES_PER_FRAME = SAMPLE_RATE * CHANNELS * SAMPLE_WIDTH * FRAME_MS // 1000
FREQ = 1000.0
SECONDS = 10


def make_tone_frame(phase: float) -> tuple[bytes, float]:
    samples = int(SAMPLE_RATE * FRAME_MS / 1000)
    out = bytearray()
    step = 2 * math.pi * FREQ / SAMPLE_RATE
    for _ in range(samples):
        v = int(0.2 * 32767 * math.sin(phase))
        out += struct.pack("<h", v)
        phase += step
    return bytes(out), phase


async def main() -> None:
    rx_packets = 0

    radio = IcomRadio(
        host="192.168.1.100",
        username="YOUR_USER",
        password="YOUR_PASS",
        audio_codec=AudioCodec.PCM_1CH_16BIT,
        audio_sample_rate=SAMPLE_RATE,
    )

    def on_audio(_pkt) -> None:
        nonlocal rx_packets
        rx_packets += 1

    async with radio:
        await radio.start_audio_rx_opus(on_audio)
        await radio.start_audio_tx_pcm(
            sample_rate=SAMPLE_RATE,
            channels=CHANNELS,
            frame_ms=FRAME_MS,
        )

        phase = 0.0
        frames = int(SECONDS * 1000 / FRAME_MS)
        for _ in range(frames):
            chunk, phase = make_tone_frame(phase)
            await radio.push_audio_tx_pcm(chunk)
            await asyncio.sleep(FRAME_MS / 1000)

        await radio.stop_audio_tx_pcm()
        await radio.stop_audio_rx_opus()

    print({"rx_packets": rx_packets})


asyncio.run(main())
```

---

## Troubleshooting (audio)

See the dedicated playbook:

- [Troubleshooting](troubleshooting.md)

Especially useful sections:
- Handshake / port negotiation (CI-V/audio port = 0)
- Timeout / retry / reconnect recovery
- Structured logging for integration tests
