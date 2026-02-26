# Audio Recipes (copy/paste)

Ниже — практические сценарии для текущего API `icom-lan`.
Все примеры используют **PCM 16-bit mono 48kHz** (`AudioCodec.PCM_1CH_16BIT`), чтобы избежать внешних кодеков.

## Prerequisites

```bash
export ICOM_HOST=192.168.1.100
export ICOM_USER=YOUR_USER
export ICOM_PASS=YOUR_PASS
```

```bash
pip install icom-lan
```

---

## 1) RX -> WAV file (10 seconds)

Сохраняет входящий аудиопоток с радио в `rx.wav`.

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
        await radio.start_audio_rx(on_audio)
        await asyncio.sleep(SECONDS)
        await radio.stop_audio_rx()

    with wave.open("rx.wav", "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(b"".join(frames))


asyncio.run(main())
```

---

## 2) WAV file -> TX

Читает `tx.wav` (16-bit mono 48kHz PCM) и отправляет на TX.

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
        await radio.start_audio_tx()
        try:
            for i in range(0, len(pcm), BYTES_PER_FRAME):
                chunk = pcm[i : i + BYTES_PER_FRAME]
                if not chunk:
                    break
                await radio.push_audio_tx(chunk)
                await asyncio.sleep(FRAME_MS / 1000)
        finally:
            await radio.stop_audio_tx()


asyncio.run(main())
```

---

## 3) Full-duplex loopback test (dry-run style)

Одновременно:
- запускает RX и считает входящие пакеты,
- отправляет 10 секунд тестового тона в TX.

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
        await radio.start_audio_rx(on_audio)
        await radio.start_audio_tx()

        phase = 0.0
        frames = int(SECONDS * 1000 / FRAME_MS)
        for _ in range(frames):
            chunk, phase = make_tone_frame(phase)
            await radio.push_audio_tx(chunk)
            await asyncio.sleep(FRAME_MS / 1000)

        await radio.stop_audio_tx()
        await radio.stop_audio_rx()

    print({"rx_packets": rx_packets})


asyncio.run(main())
```

---

## Troubleshooting (audio)

См. отдельный плейбук:

- [Troubleshooting](troubleshooting.md)

Особенно полезные разделы:
- handshake/port negotiation (CI-V/audio port = 0),
- timeout/retry/reconnect recovery,
- structured logging для интеграционных тестов.
