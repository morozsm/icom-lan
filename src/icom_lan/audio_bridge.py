"""Audio bridge — bidirectional PCM bridge between radio and a system audio device.

Routes decoded PCM audio from the radio to a virtual audio output device
(e.g. BlackHole) and captures PCM from the same device back to the radio
for TX.  This allows applications like WSJT-X, fldigi, or JS8Call to
use the radio without any special configuration — they simply select the
virtual audio device as their sound card.

Architecture::

    Radio ←(LAN/Opus)→ icom-lan ←(PCM)→ sounddevice ←(CoreAudio)→ BlackHole ←→ WSJT-X

Requirements:
    - ``sounddevice`` and ``numpy`` (``pip install icom-lan[bridge]``)
    - A virtual audio loopback driver (e.g. BlackHole 2ch: ``brew install blackhole-2ch``)

Usage::

    bridge = AudioBridge(radio, device_name="BlackHole 2ch")
    await bridge.start()    # begins bidirectional audio flow
    ...
    await bridge.stop()     # clean shutdown
"""

from __future__ import annotations

import asyncio
import logging
import time
from concurrent.futures import Executor
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .radio_protocol import AudioCapable

logger = logging.getLogger(__name__)

__all__ = ["AudioBridge", "find_loopback_device"]

# Audio format constants — must match radio PCM settings
SAMPLE_RATE = 48000
CHANNELS = 1
FRAME_MS = 20
SAMPLES_PER_FRAME = SAMPLE_RATE * FRAME_MS // 1000  # 960
BYTES_PER_SAMPLE = 2  # s16le
FRAME_BYTES = SAMPLES_PER_FRAME * CHANNELS * BYTES_PER_SAMPLE  # 1920


def find_loopback_device(name: str | None = None) -> dict[str, Any] | None:
    """Find a virtual loopback audio device by name.

    Args:
        name: Device name substring to match (e.g. "BlackHole").
              If ``None``, searches for common virtual device names.

    Returns:
        A ``sounddevice`` device info dict, or ``None`` if not found.
    """
    try:
        import sounddevice as sd  # noqa: F401
    except ImportError:
        raise ImportError(
            "sounddevice is required for audio bridge. "
            "Install with: pip install icom-lan[bridge]"
        ) from None

    devices = sd.query_devices()
    candidates = ["BlackHole", "Loopback", "VB-Audio", "Virtual"]
    search_names = [name] if name else candidates

    for dev in devices:
        dev_name = dev.get("name", "")
        for search in search_names:
            if search.lower() in dev_name.lower():
                return dict(dev)
    return None


def list_audio_devices() -> list[dict[str, Any]]:
    """List all available audio devices.

    Returns:
        List of device info dicts from sounddevice.
    """
    try:
        import sounddevice as sd
    except ImportError:
        raise ImportError(
            "sounddevice is required. Install with: pip install icom-lan[bridge]"
        ) from None

    return list(sd.query_devices())


class AudioBridge:
    """Bidirectional PCM audio bridge between radio and a system audio device.

    Args:
        radio: A connected radio instance implementing :class:`Radio` +
               :class:`AudioCapable` protocols.
        device_name: Name (or substring) of the audio device to use.
                     Defaults to auto-detection of common virtual devices.
        sample_rate: PCM sample rate (default 48000).
        channels: Number of audio channels (default 1, mono).
        frame_ms: PCM frame duration in milliseconds (default 20).
        tx_enabled: Whether to bridge TX audio (device → radio). Default True.
        tx_executor: Optional executor for blocking TX reads (device → radio).
            The TX path runs ``sounddevice.InputStream.read()`` in a thread to avoid
            blocking the event loop. If ``None`` (default), the loop's default
            thread pool is used. For heavy usage or multiple bridge instances,
            pass a dedicated :class:`concurrent.futures.ThreadPoolExecutor` (e.g.
            ``max_workers=1`` or ``2``) to isolate TX I/O and avoid contention.
    """

    def __init__(
        self,
        radio: "AudioCapable",
        *,
        device_name: str | None = None,
        tx_device_name: str | None = None,
        sample_rate: int = SAMPLE_RATE,
        channels: int = CHANNELS,
        frame_ms: int = FRAME_MS,
        tx_enabled: bool = True,
        tx_executor: Executor | None = None,
    ) -> None:
        self._radio = radio
        self._device_name = device_name
        self._tx_device_name = (
            tx_device_name  # separate TX device (if None, same as RX)
        )
        self._sample_rate = sample_rate
        self._channels = channels
        self._frame_ms = frame_ms
        self._tx_enabled = tx_enabled
        self._tx_executor = tx_executor

        self._running = False
        self._rx_stream: Any = None  # sounddevice OutputStream (radio → device)
        self._tx_stream: Any = None  # sounddevice InputStream (device → radio)
        self._rx_task: asyncio.Task[None] | None = None
        self._tx_task: asyncio.Task[None] | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._decoder: Any = None
        self._subscription: Any = None
        self._samples_per_frame = sample_rate * frame_ms // 1000

        # Stats
        self._rx_frames = 0
        self._tx_frames = 0
        self._rx_drops = 0
        # Timing
        self._rx_latency_samples: list[float] = []
        self._tx_latency_samples: list[float] = []
        self._last_rx_time: float = 0.0
        self._last_tx_time: float = 0.0
        self._start_time: float = 0.0

    @property
    def running(self) -> bool:
        """Whether the bridge is currently active."""
        return self._running

    @property
    def stats(self) -> dict[str, Any]:
        """Bridge statistics."""
        uptime = time.monotonic() - self._start_time if self._running else 0.0
        rx_avg = (
            sum(self._rx_latency_samples) / len(self._rx_latency_samples)
            if self._rx_latency_samples
            else 0.0
        )
        tx_avg = (
            sum(self._tx_latency_samples) / len(self._tx_latency_samples)
            if self._tx_latency_samples
            else 0.0
        )
        return {
            "running": self._running,
            "rx_frames": self._rx_frames,
            "tx_frames": self._tx_frames,
            "rx_drops": self._rx_drops,
            "uptime_seconds": round(uptime, 1),
            "rx_interval_ms": round(rx_avg * 1000, 1),
            "tx_interval_ms": round(tx_avg * 1000, 1),
            "buffer_size": len(self._rx_latency_samples),
        }

    async def start(self) -> None:
        """Start the audio bridge.

        Raises:
            ImportError: If sounddevice/numpy not installed.
            RuntimeError: If virtual audio device not found.
            ConnectionError: If radio is not connected.
        """
        import numpy as np
        import sounddevice as sd  # noqa: F401

        if self._running:
            logger.warning("audio-bridge: already running")
            return

        self._start_time = time.monotonic()
        self._loop = asyncio.get_running_loop()

        # Find the device
        dev = find_loopback_device(self._device_name)
        if dev is None:
            searched = self._device_name or "BlackHole/Loopback/VB-Audio"
            raise RuntimeError(
                f"Virtual audio device not found (searched: {searched}). "
                f"Install one, e.g.: brew install blackhole-2ch"
            )

        dev_index = dev["index"]
        dev_name = dev["name"]
        logger.info("audio-bridge: using device %r (index %d)", dev_name, dev_index)

        samples_per_frame = self._sample_rate * self._frame_ms // 1000

        # --- RX path: radio → virtual device output ---
        # We open an OutputStream and write decoded PCM into it.
        self._rx_stream = sd.OutputStream(
            samplerate=self._sample_rate,
            channels=self._channels,
            dtype="int16",
            device=dev_index,
            blocksize=samples_per_frame,
            latency="low",
        )
        self._rx_stream.start()

        # Silence frame for gap filling
        self._silence = np.zeros((samples_per_frame, self._channels), dtype=np.int16)

        # --- RX: subscribe to AudioBus for audio packets ---
        # Detect codec to decide if we need opus decoding
        from .types import AudioCodec

        _codec = getattr(self._radio, "audio_codec", None)
        self._is_opus = isinstance(_codec, AudioCodec) and _codec in (
            AudioCodec.OPUS_1CH,
            AudioCodec.OPUS_2CH,
        )

        if self._is_opus:
            try:
                import opuslib
            except ImportError:
                raise ImportError(
                    "opuslib is required for audio bridge with Opus codec. "
                    "Install with: pip install icom-lan[bridge]"
                ) from None
            self._decoder = opuslib.Decoder(self._sample_rate, self._channels)
            logger.info("audio-bridge: using Opus decoder")
        else:
            self._decoder = None
            logger.info("audio-bridge: PCM mode (no decode needed)")

        bus = self._radio.audio_bus
        self._subscription = bus.subscribe(name="audio-bridge")
        await self._subscription.start()
        self._rx_task = asyncio.create_task(self._rx_loop(np))

        # --- TX path: virtual device input → radio ---
        if self._tx_enabled:
            await self._radio.start_audio_tx_pcm(
                sample_rate=self._sample_rate,
                channels=self._channels,
                frame_ms=self._frame_ms,
            )

            # Use separate TX device if specified, otherwise same as RX
            tx_dev_index = dev_index
            if self._tx_device_name:
                tx_dev = find_loopback_device(self._tx_device_name)
                if tx_dev is None:
                    logger.warning(
                        "audio-bridge: TX device %r not found, using RX device",
                        self._tx_device_name,
                    )
                else:
                    tx_dev_index = tx_dev["index"]
                    logger.info(
                        "audio-bridge: TX device %r (index %d)",
                        tx_dev["name"],
                        tx_dev_index,
                    )

            # TX uses a blocking InputStream read in a thread
            self._tx_stream = sd.InputStream(
                samplerate=self._sample_rate,
                channels=self._channels,
                dtype="int16",
                device=tx_dev_index,
                blocksize=samples_per_frame,
                latency="low",
            )
            self._tx_stream.start()

            self._tx_task = asyncio.create_task(self._tx_loop())

        self._running = True
        direction = "RX+TX" if self._tx_enabled else "RX only"
        logger.info(
            "audio-bridge: started (%s, %dHz, %dch, %dms frames)",
            direction,
            self._sample_rate,
            self._channels,
            self._frame_ms,
        )

    async def _rx_loop(self, np: Any) -> None:
        """Read opus packets from AudioBus subscription, decode, write to device."""
        try:
            async for packet in self._subscription:
                if not self._running:
                    break
                if packet is None:
                    self._rx_drops += 1
                    if self._rx_drops <= 3:
                        logger.debug(
                            "audio-bridge: None packet (gap) #%d", self._rx_drops
                        )
                    if self._rx_stream and self._rx_stream.active:
                        self._rx_stream.write(self._silence)
                    continue

                opus_data = getattr(packet, "data", None)
                if opus_data is None:
                    continue

                try:
                    if self._is_opus:
                        pcm_data = self._decoder.decode(
                            opus_data, self._samples_per_frame
                        )
                    else:
                        # PCM — data is already raw PCM bytes
                        pcm_data = opus_data
                    now = time.monotonic()
                    if self._last_rx_time > 0:
                        delta = now - self._last_rx_time
                        self._rx_latency_samples.append(delta)
                        if len(self._rx_latency_samples) > 100:
                            self._rx_latency_samples.pop(0)
                    self._last_rx_time = now
                    self._rx_frames += 1
                    if self._rx_stream and self._rx_stream.active:
                        frame = np.frombuffer(pcm_data, dtype=np.int16).reshape(
                            -1, self._channels
                        )
                        self._rx_stream.write(frame)
                except Exception as exc:
                    self._rx_drops += 1
                    if self._rx_drops <= 5 or self._rx_drops % 1000 == 0:
                        logger.warning(
                            "audio-bridge: decode error #%d: %s (data=%d bytes)",
                            self._rx_drops,
                            exc,
                            len(opus_data),
                        )
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.error("audio-bridge: RX loop error", exc_info=True)
            # Try to restart after a brief pause
            await asyncio.sleep(1.0)
            if self._running and self._subscription:
                logger.info("audio-bridge: restarting RX loop")
                self._rx_task = asyncio.create_task(self._rx_loop(np))

    async def _tx_loop(self) -> None:
        """Read audio from the virtual device and push to the radio."""
        import numpy as np

        loop = asyncio.get_running_loop()
        samples_per_frame = self._sample_rate * self._frame_ms // 1000

        # Threshold: skip silent frames (noise gate)
        silence_threshold = 10  # ~-70dB for int16

        try:
            while self._running and self._tx_stream and self._tx_stream.active:
                # Read from sounddevice in a thread to avoid blocking the loop
                data, overflowed = await loop.run_in_executor(
                    self._tx_executor,
                    lambda: self._tx_stream.read(samples_per_frame),
                )
                if overflowed:
                    logger.debug("audio-bridge: TX input overflow")

                # Simple noise gate — don't TX silence
                if np.max(np.abs(data)) < silence_threshold:
                    continue

                pcm_bytes = data.astype(np.int16).tobytes()
                now = time.monotonic()
                if self._last_tx_time > 0:
                    delta = now - self._last_tx_time
                    self._tx_latency_samples.append(delta)
                    if len(self._tx_latency_samples) > 100:
                        self._tx_latency_samples.pop(0)
                self._last_tx_time = now
                self._tx_frames += 1

                if self._tx_frames <= 3 or self._tx_frames % 1000 == 0:
                    peak = int(np.max(np.abs(data)))
                    logger.info(
                        "audio-bridge: TX frame #%d, %d bytes, peak=%d",
                        self._tx_frames,
                        len(pcm_bytes),
                        peak,
                    )

                try:
                    if self._is_opus:
                        # PCM → Opus transcode, then send
                        await self._radio.push_audio_tx_pcm(pcm_bytes)
                    else:
                        # PCM codec — send raw PCM directly (no transcode)
                        await self._radio.push_audio_tx_opus(pcm_bytes)
                except Exception:
                    if self._tx_frames <= 5:
                        logger.warning("audio-bridge: TX push error", exc_info=True)
                    else:
                        logger.debug("audio-bridge: TX push error", exc_info=True)

        except asyncio.CancelledError:
            pass
        except Exception:
            logger.error("audio-bridge: TX loop error", exc_info=True)

    async def stop(self) -> None:
        """Stop the audio bridge and release resources."""
        if not self._running:
            return

        self._running = False

        # Stop RX subscription
        if self._rx_task and not self._rx_task.done():
            self._rx_task.cancel()
            try:
                await self._rx_task
            except asyncio.CancelledError:
                pass
        self._rx_task = None

        if self._subscription is not None:
            self._subscription.stop()
            self._subscription = None

        # Stop TX
        if self._tx_task and not self._tx_task.done():
            self._tx_task.cancel()
            try:
                await self._tx_task
            except asyncio.CancelledError:
                pass
        self._tx_task = None

        if self._tx_stream:
            self._tx_stream.stop()
            self._tx_stream.close()
            self._tx_stream = None

        # Stop RX
        if self._rx_stream:
            self._rx_stream.stop()
            self._rx_stream.close()
            self._rx_stream = None

        # No need to stop radio RX — AudioBus handles that automatically
        # when last subscriber disconnects

        if self._tx_enabled:
            try:
                await self._radio.stop_audio_tx_pcm()
            except Exception:
                logger.debug("audio-bridge: stop TX error", exc_info=True)

        logger.info(
            "audio-bridge: stopped (rx=%d frames, tx=%d frames, drops=%d)",
            self._rx_frames,
            self._tx_frames,
            self._rx_drops,
        )
