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
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .radio_protocol import Radio

logger = logging.getLogger(__name__)

__all__ = ["AudioBridge", "find_loopback_device"]

# Audio format constants — must match radio PCM settings
SAMPLE_RATE = 48000
CHANNELS = 1
FRAME_MS = 20
SAMPLES_PER_FRAME = SAMPLE_RATE * FRAME_MS // 1000  # 960
BYTES_PER_SAMPLE = 2  # s16le
FRAME_BYTES = SAMPLES_PER_FRAME * CHANNELS * BYTES_PER_SAMPLE  # 1920


def find_loopback_device(name: str | None = None) -> dict | None:
    """Find a virtual loopback audio device by name.

    Args:
        name: Device name substring to match (e.g. "BlackHole").
              If ``None``, searches for common virtual device names.

    Returns:
        A ``sounddevice`` device info dict, or ``None`` if not found.
    """
    try:
        import sounddevice as sd
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
                return dev
    return None


def list_audio_devices() -> list[dict]:
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
    """

    def __init__(
        self,
        radio: Radio,
        *,
        device_name: str | None = None,
        sample_rate: int = SAMPLE_RATE,
        channels: int = CHANNELS,
        frame_ms: int = FRAME_MS,
        tx_enabled: bool = True,
    ) -> None:
        self._radio = radio
        self._device_name = device_name
        self._sample_rate = sample_rate
        self._channels = channels
        self._frame_ms = frame_ms
        self._tx_enabled = tx_enabled

        self._running = False
        self._rx_stream = None  # sounddevice OutputStream (radio → device)
        self._tx_stream = None  # sounddevice InputStream (device → radio)
        self._tx_task: asyncio.Task | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._opus_tap = None
        self._decoder = None
        self._exclusive_pcm = False
        self._samples_per_frame = sample_rate * frame_ms // 1000

        # Stats
        self._rx_frames = 0
        self._tx_frames = 0
        self._rx_drops = 0

    @property
    def running(self) -> bool:
        """Whether the bridge is currently active."""
        return self._running

    @property
    def stats(self) -> dict:
        """Bridge statistics."""
        return {
            "running": self._running,
            "rx_frames": self._rx_frames,
            "tx_frames": self._tx_frames,
            "rx_drops": self._rx_drops,
        }

    async def start(self) -> None:
        """Start the audio bridge.

        Raises:
            ImportError: If sounddevice/numpy not installed.
            RuntimeError: If virtual audio device not found.
            ConnectionError: If radio is not connected.
        """
        import numpy as np
        import sounddevice as sd

        if self._running:
            logger.warning("audio-bridge: already running")
            return

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
        logger.info(
            "audio-bridge: using device %r (index %d)", dev_name, dev_index
        )

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
        self._silence = np.zeros(
            (samples_per_frame, self._channels), dtype=np.int16
        )

        # --- Opus RX tap: decode and write PCM to virtual device ---
        # We use a "tap" mechanism to receive opus packets in parallel with
        # other consumers (e.g. AudioBroadcaster for WebSocket clients).
        try:
            import opuslib
        except ImportError:
            raise ImportError(
                "opuslib is required for audio bridge. "
                "Install with: pip install icom-lan[bridge]"
            ) from None

        self._decoder = opuslib.Decoder(self._sample_rate, self._channels)
        self._samples_per_frame = samples_per_frame

        def _on_opus_packet(packet: Any) -> None:
            """Tap into opus RX stream — decode and write to virtual device."""
            if not self._running:
                return
            if packet is None:
                self._rx_drops += 1
                if self._rx_stream and self._rx_stream.active:
                    self._rx_stream.write(self._silence)
                return

            # packet is AudioPacket with .data attribute (opus bytes)
            opus_data = getattr(packet, "data", None)
            if opus_data is None:
                return

            try:
                pcm_data = self._decoder.decode(opus_data, self._samples_per_frame)
                self._rx_frames += 1
                if self._rx_stream and self._rx_stream.active:
                    frame = np.frombuffer(pcm_data, dtype=np.int16).reshape(
                        -1, self._channels
                    )
                    self._rx_stream.write(frame)
            except Exception:
                self._rx_drops += 1

        self._opus_tap = _on_opus_packet

        # Ensure audio transport is connected, then register tap
        if hasattr(self._radio, "_ensure_audio_transport"):
            await self._radio._ensure_audio_transport()
        # Start RX stream on the radio (needed so packets flow)
        # Use a dummy callback if no other consumer started RX yet
        if hasattr(self._radio, "_audio_stream") and self._radio._audio_stream is not None:
            stream = self._radio._audio_stream
            stream.add_rx_tap(self._opus_tap)
            # If RX not yet active, start it
            if not getattr(stream, "_rx_task", None):
                await self._radio.start_audio_rx_opus(lambda _: None)
        else:
            # Fallback: start full PCM path (single consumer mode)
            logger.warning("audio-bridge: falling back to exclusive PCM mode")
            self._exclusive_pcm = True
            await self._radio.start_audio_rx_pcm(
                self._make_pcm_callback(np),
                sample_rate=self._sample_rate,
                channels=self._channels,
                frame_ms=self._frame_ms,
            )

        # --- TX path: virtual device input → radio ---
        if self._tx_enabled:
            await self._radio.start_audio_tx_pcm(
                sample_rate=self._sample_rate,
                channels=self._channels,
                frame_ms=self._frame_ms,
            )

            # TX uses a blocking InputStream read in a thread
            self._tx_stream = sd.InputStream(
                samplerate=self._sample_rate,
                channels=self._channels,
                dtype="int16",
                device=dev_index,
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

    def _make_pcm_callback(self, np: Any) -> "Callable[[bytes | None], None]":
        """Create a PCM RX callback for exclusive (fallback) mode."""
        def _on_rx_pcm(pcm_data: bytes | None) -> None:
            if not self._running:
                return
            if pcm_data is None:
                self._rx_drops += 1
                if self._rx_stream and self._rx_stream.active:
                    self._rx_stream.write(self._silence)
                return
            self._rx_frames += 1
            if self._rx_stream and self._rx_stream.active:
                frame = np.frombuffer(pcm_data, dtype=np.int16).reshape(
                    -1, self._channels
                )
                self._rx_stream.write(frame)
        return _on_rx_pcm

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
                    None,
                    lambda: self._tx_stream.read(samples_per_frame),
                )
                if overflowed:
                    logger.debug("audio-bridge: TX input overflow")

                # Simple noise gate — don't TX silence
                if np.max(np.abs(data)) < silence_threshold:
                    continue

                pcm_bytes = data.astype(np.int16).tobytes()
                self._tx_frames += 1

                try:
                    await self._radio.push_audio_tx_pcm(pcm_bytes)
                except Exception:
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

        # Stop radio audio tap
        if hasattr(self, "_opus_tap") and self._opus_tap is not None:
            if hasattr(self._radio, "_audio_stream") and self._radio._audio_stream is not None:
                self._radio._audio_stream.remove_rx_tap(self._opus_tap)
            self._opus_tap = None

        if getattr(self, "_exclusive_pcm", False):
            try:
                await self._radio.stop_audio_rx_pcm()
            except Exception:
                logger.debug("audio-bridge: stop RX error", exc_info=True)

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
