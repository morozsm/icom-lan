"""Production USB audio driver for IC-7610 serial backend (macOS-first)."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Callable

logger = logging.getLogger(__name__)

_DEPENDENCY_HINT = (
    "USB audio backend requires optional dependencies sounddevice and numpy. "
    "Install with: pip install icom-lan[bridge]"
)
_USB_NAME_PATTERNS: tuple[str, ...] = (
    "ic-7610",
    "ic 7610",
    "icom",
    "usb audio codec",
    "usb audio",
)


class AudioDeviceSelectionError(RuntimeError):
    """Raised when no suitable USB audio device can be selected."""


class AudioDriverLifecycleError(RuntimeError):
    """Raised on invalid USB audio lifecycle operations."""


@dataclass(frozen=True, slots=True)
class UsbAudioDevice:
    """Normalized USB audio device descriptor."""

    index: int
    name: str
    input_channels: int
    output_channels: int
    default_samplerate: int = 48_000
    is_default_input: bool = False
    is_default_output: bool = False

    @property
    def supports_rx(self) -> bool:
        """Whether the device can capture RX audio from radio (input channels)."""
        return self.input_channels > 0

    @property
    def supports_tx(self) -> bool:
        """Whether the device can play TX audio to radio (output channels)."""
        return self.output_channels > 0

    @property
    def duplex(self) -> bool:
        """Whether the device supports both capture and playback."""
        return self.supports_rx and self.supports_tx


def _safe_int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _name_score(name: str) -> int:
    lowered = name.lower()
    for idx, pattern in enumerate(_USB_NAME_PATTERNS):
        if pattern in lowered:
            return idx
    return 99


def _find_by_override(
    devices: list[UsbAudioDevice],
    *,
    override: str,
    direction: str,
) -> UsbAudioDevice:
    if not override.strip():
        raise AudioDeviceSelectionError(
            f"{direction.upper()} device override must be a non-empty string."
        )
    exact = [dev for dev in devices if dev.name == override]
    if len(exact) == 1:
        return exact[0]
    exact_ci = [dev for dev in devices if dev.name.lower() == override.lower()]
    if len(exact_ci) == 1:
        return exact_ci[0]
    partial = [dev for dev in devices if override.lower() in dev.name.lower()]
    if len(partial) == 1:
        return partial[0]
    available = ", ".join(sorted(dev.name for dev in devices)) or "<none>"
    raise AudioDeviceSelectionError(
        f"Unknown {direction.upper()} device override {override!r}. "
        f"Available {direction.upper()} devices: {available}"
    )


def _auto_pick(
    devices: list[UsbAudioDevice],
    *,
    direction: str,
) -> UsbAudioDevice:
    if direction == "rx":
        default_attr = "is_default_input"
    else:
        default_attr = "is_default_output"
    ranked = sorted(
        devices,
        key=lambda dev: (
            _name_score(dev.name),
            0 if getattr(dev, default_attr) else 1,
            dev.index,
            dev.name.lower(),
        ),
    )
    return ranked[0]


def select_usb_audio_devices(
    devices: list[UsbAudioDevice],
    *,
    rx_device: str | None = None,
    tx_device: str | None = None,
) -> tuple[UsbAudioDevice, UsbAudioDevice]:
    """Select RX/TX devices deterministically with override precedence."""
    rx_candidates = [dev for dev in devices if dev.supports_rx]
    tx_candidates = [dev for dev in devices if dev.supports_tx]
    duplex_candidates = [dev for dev in devices if dev.duplex]

    if not rx_candidates:
        raise AudioDeviceSelectionError("No suitable RX USB audio device was found.")
    if not tx_candidates:
        raise AudioDeviceSelectionError("No suitable TX USB audio device was found.")

    if rx_device is None and tx_device is None and duplex_candidates:
        selected = _auto_pick(duplex_candidates, direction="rx")
        return selected, selected

    selected_rx: UsbAudioDevice
    selected_tx: UsbAudioDevice

    if rx_device is not None:
        selected_rx = _find_by_override(rx_candidates, override=rx_device, direction="rx")
    elif tx_device is not None:
        selected_tx = _find_by_override(tx_candidates, override=tx_device, direction="tx")
        selected_rx = selected_tx if selected_tx.supports_rx else _auto_pick(
            rx_candidates, direction="rx"
        )
    else:
        selected_rx = _auto_pick(rx_candidates, direction="rx")

    if tx_device is not None:
        selected_tx = _find_by_override(tx_candidates, override=tx_device, direction="tx")
    elif rx_device is not None and selected_rx.supports_tx:
        selected_tx = selected_rx
    else:
        selected_tx = selected_rx if selected_rx.supports_tx else _auto_pick(
            tx_candidates, direction="tx"
        )

    return selected_rx, selected_tx


def list_usb_audio_devices(sounddevice_module: Any) -> list[UsbAudioDevice]:
    """Return normalized system audio devices."""
    raw_devices = list(sounddevice_module.query_devices())
    default_input_idx: int | None = None
    default_output_idx: int | None = None
    default_raw = getattr(getattr(sounddevice_module, "default", None), "device", None)
    if isinstance(default_raw, (list, tuple)) and len(default_raw) >= 2:
        default_input_idx = _safe_int(default_raw[0], default=-1)
        default_output_idx = _safe_int(default_raw[1], default=-1)

    normalized: list[UsbAudioDevice] = []
    for idx, raw in enumerate(raw_devices):
        index = _safe_int(raw.get("index", idx), default=idx)
        normalized.append(
            UsbAudioDevice(
                index=index,
                name=str(raw.get("name", f"device-{index}")),
                input_channels=_safe_int(raw.get("max_input_channels")),
                output_channels=_safe_int(raw.get("max_output_channels")),
                default_samplerate=_safe_int(raw.get("default_samplerate"), default=48_000),
                is_default_input=(default_input_idx is not None and index == default_input_idx),
                is_default_output=(
                    default_output_idx is not None and index == default_output_idx
                ),
            )
        )
    return normalized


class UsbAudioDriver:
    """Stateful USB audio driver with deterministic device selection."""

    _BYTES_PER_SAMPLE = 2  # s16le

    def __init__(
        self,
        *,
        rx_device: str | None = None,
        tx_device: str | None = None,
        sample_rate: int = 48_000,
        channels: int = 1,
        frame_ms: int = 20,
        dependency_loader: Callable[[], tuple[Any, Any]] | None = None,
    ) -> None:
        self._rx_device_override = rx_device
        self._tx_device_override = tx_device
        self._sample_rate = sample_rate
        self._channels = channels
        self._frame_ms = frame_ms
        self._dependency_loader = dependency_loader

        self._sd: Any = None
        self._np: Any = None
        self._selected_rx: UsbAudioDevice | None = None
        self._selected_tx: UsbAudioDevice | None = None

        self._rx_stream: Any = None
        self._tx_stream: Any = None
        self._rx_callback: Callable[[bytes], None] | None = None
        self._rx_task: asyncio.Task[None] | None = None
        self._tx_task: asyncio.Task[None] | None = None
        self._tx_queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=64)

        self._rx_lock = asyncio.Lock()
        self._tx_lock = asyncio.Lock()

    @property
    def rx_running(self) -> bool:
        return self._rx_task is not None and not self._rx_task.done()

    @property
    def tx_running(self) -> bool:
        return self._tx_task is not None and not self._tx_task.done()

    @property
    def selected_rx_device(self) -> UsbAudioDevice | None:
        return self._selected_rx

    @property
    def selected_tx_device(self) -> UsbAudioDevice | None:
        return self._selected_tx

    def _ensure_dependencies(self) -> tuple[Any, Any]:
        if self._sd is not None and self._np is not None:
            return self._sd, self._np

        if self._dependency_loader is not None:
            try:
                sounddevice_module, numpy_module = self._dependency_loader()
            except ImportError as exc:
                raise ImportError(_DEPENDENCY_HINT) from exc
        else:
            try:
                import sounddevice as sounddevice_module
            except ImportError as exc:
                raise ImportError(_DEPENDENCY_HINT) from exc
            try:
                import numpy as numpy_module
            except ImportError as exc:
                raise ImportError(_DEPENDENCY_HINT) from exc

        self._sd = sounddevice_module
        self._np = numpy_module
        return self._sd, self._np

    def _ensure_selected_devices(self) -> tuple[UsbAudioDevice, UsbAudioDevice]:
        sounddevice_module, _ = self._ensure_dependencies()
        devices = list_usb_audio_devices(sounddevice_module)
        selected_rx, selected_tx = select_usb_audio_devices(
            devices,
            rx_device=self._rx_device_override,
            tx_device=self._tx_device_override,
        )
        self._selected_rx = selected_rx
        self._selected_tx = selected_tx
        return selected_rx, selected_tx

    def list_devices(self) -> list[UsbAudioDevice]:
        """List normalized devices from the active audio backend."""
        sounddevice_module, _ = self._ensure_dependencies()
        return list_usb_audio_devices(sounddevice_module)

    async def start_rx(
        self,
        callback: Callable[[bytes], None] | None = None,
        *,
        sample_rate: int | None = None,
        channels: int | None = None,
        frame_ms: int | None = None,
    ) -> None:
        """Start capture loop and deliver PCM frames to callback."""
        if callback is None:
            raise AudioDriverLifecycleError("Audio RX callback is required.")
        if not callable(callback):
            raise TypeError("Audio RX callback must be callable.")

        async with self._rx_lock:
            if self.rx_running:
                raise AudioDriverLifecycleError("RX stream already started.")

            sounddevice_module, _ = self._ensure_dependencies()
            selected_rx, _ = self._ensure_selected_devices()
            sr = self._sample_rate if sample_rate is None else sample_rate
            ch = self._channels if channels is None else channels
            fm = self._frame_ms if frame_ms is None else frame_ms
            if (sr * fm) % 1000 != 0:
                raise AudioDriverLifecycleError(
                    "Invalid RX frame format: sample_rate * frame_ms must be divisible by 1000."
                )
            blocksize = (sr * fm) // 1000
            self._rx_callback = callback
            self._rx_stream = sounddevice_module.InputStream(
                samplerate=sr,
                channels=ch,
                dtype="int16",
                device=selected_rx.index,
                blocksize=blocksize,
                latency="low",
            )
            self._rx_stream.start()
            self._rx_task = asyncio.create_task(
                self._rx_loop(blocksize),
                name="usb-audio-rx-loop",
            )

    async def stop_rx(self) -> None:
        """Stop capture loop and close RX stream."""
        async with self._rx_lock:
            task = self._rx_task
            stream = self._rx_stream
            self._rx_task = None
            self._rx_stream = None
            self._rx_callback = None

        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        if stream is not None:
            try:
                stream.stop()
            except Exception:
                logger.debug("usb-audio: RX stream stop failed", exc_info=True)
            try:
                stream.close()
            except Exception:
                logger.debug("usb-audio: RX stream close failed", exc_info=True)

    async def start_tx(
        self,
        *,
        sample_rate: int | None = None,
        channels: int | None = None,
        frame_ms: int | None = None,
    ) -> None:
        """Start playback loop for outgoing PCM frames."""
        async with self._tx_lock:
            if self.tx_running:
                raise AudioDriverLifecycleError("TX stream already started.")

            sounddevice_module, _ = self._ensure_dependencies()
            _, selected_tx = self._ensure_selected_devices()
            sr = self._sample_rate if sample_rate is None else sample_rate
            ch = self._channels if channels is None else channels
            fm = self._frame_ms if frame_ms is None else frame_ms
            if (sr * fm) % 1000 != 0:
                raise AudioDriverLifecycleError(
                    "Invalid TX frame format: sample_rate * frame_ms must be divisible by 1000."
                )
            blocksize = (sr * fm) // 1000
            self._tx_stream = sounddevice_module.OutputStream(
                samplerate=sr,
                channels=ch,
                dtype="int16",
                device=selected_tx.index,
                blocksize=blocksize,
                latency="low",
            )
            self._tx_stream.start()
            self._tx_queue = asyncio.Queue(maxsize=64)
            self._tx_task = asyncio.create_task(
                self._tx_loop(ch),
                name="usb-audio-tx-loop",
            )

    async def push_tx_pcm(self, frame: bytes) -> None:
        """Queue one PCM frame for playback."""
        if not self.tx_running:
            raise AudioDriverLifecycleError("Audio TX stream is not started.")
        if not isinstance(frame, (bytes, bytearray, memoryview)):
            raise TypeError("PCM TX frame must be bytes-like.")
        await self._tx_queue.put(bytes(frame))

    async def stop_tx(self) -> None:
        """Stop playback loop and close TX stream."""
        async with self._tx_lock:
            task = self._tx_task
            stream = self._tx_stream
            self._tx_task = None
            self._tx_stream = None
            self._tx_queue = asyncio.Queue(maxsize=64)

        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        if stream is not None:
            try:
                stream.stop()
            except Exception:
                logger.debug("usb-audio: TX stream stop failed", exc_info=True)
            try:
                stream.close()
            except Exception:
                logger.debug("usb-audio: TX stream close failed", exc_info=True)

    async def _rx_loop(self, blocksize: int) -> None:
        assert self._rx_stream is not None
        stream = self._rx_stream
        try:
            while True:
                data, _overflowed = await asyncio.to_thread(stream.read, blocksize)
                callback = self._rx_callback
                if callback is None:
                    continue
                if hasattr(data, "tobytes"):
                    pcm_frame = bytes(data.tobytes())
                else:
                    pcm_frame = bytes(data)
                callback(pcm_frame)
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.warning("usb-audio: RX loop failed", exc_info=True)

    async def _tx_loop(self, channels: int) -> None:
        assert self._tx_stream is not None
        stream = self._tx_stream
        _, np_module = self._ensure_dependencies()
        try:
            while True:
                pcm_frame = await self._tx_queue.get()
                frame_array = np_module.frombuffer(pcm_frame, dtype=np_module.int16)
                frame_array = frame_array.reshape(-1, channels)
                await asyncio.to_thread(stream.write, frame_array)
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.warning("usb-audio: TX loop failed", exc_info=True)


__all__ = [
    "AudioDeviceSelectionError",
    "AudioDriverLifecycleError",
    "UsbAudioDevice",
    "UsbAudioDriver",
    "list_usb_audio_devices",
    "select_usb_audio_devices",
]
