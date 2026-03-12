"""Deterministic USB-audio stub contracts for serial-ready regression tests."""

from __future__ import annotations

from dataclasses import dataclass


class AudioDeviceSelectionError(RuntimeError):
    """Raised when no suitable USB audio device can be selected."""


class AudioDriverLifecycleError(RuntimeError):
    """Raised on invalid or failed stub audio lifecycle operations."""


@dataclass(frozen=True, slots=True)
class UsbAudioDevice:
    """Simple USB device descriptor used by stub selection logic."""

    name: str
    input_channels: int
    output_channels: int
    is_default: bool = False

    @property
    def duplex(self) -> bool:
        return self.input_channels > 0 and self.output_channels > 0


def select_usb_audio_device(
    devices: list[UsbAudioDevice],
    *,
    preferred_name: str | None = None,
    require_duplex: bool = False,
) -> UsbAudioDevice:
    """Select a device deterministically for test and backend wiring."""
    candidates = [d for d in devices if (d.duplex or not require_duplex)]
    if not candidates:
        raise AudioDeviceSelectionError(
            "No USB audio device satisfies selection rules."
        )

    if preferred_name is not None:
        for dev in candidates:
            if dev.name == preferred_name:
                return dev
        raise AudioDeviceSelectionError(
            f"Preferred USB audio device not found: {preferred_name!r}"
        )

    for dev in candidates:
        if dev.is_default:
            return dev
    return candidates[0]


class UsbAudioDriverStub:
    """Minimal stateful audio driver stub with deterministic failure injection."""

    def __init__(
        self,
        device: UsbAudioDevice,
        *,
        fail_on_start_rx: bool = False,
        fail_on_start_tx: bool = False,
    ) -> None:
        self.device = device
        self._fail_on_start_rx = fail_on_start_rx
        self._fail_on_start_tx = fail_on_start_tx
        self.rx_running = False
        self.tx_running = False

    async def start_rx(self) -> None:
        if self.rx_running:
            raise AudioDriverLifecycleError("RX stream already started.")
        if self._fail_on_start_rx:
            raise AudioDriverLifecycleError("Injected RX start failure.")
        self.rx_running = True

    async def stop_rx(self) -> None:
        self.rx_running = False

    async def start_tx(self) -> None:
        if self.tx_running:
            raise AudioDriverLifecycleError("TX stream already started.")
        if self._fail_on_start_tx:
            raise AudioDriverLifecycleError("Injected TX start failure.")
        self.tx_running = True

    async def stop_tx(self) -> None:
        self.tx_running = False


__all__ = [
    "AudioDeviceSelectionError",
    "AudioDriverLifecycleError",
    "UsbAudioDevice",
    "UsbAudioDriverStub",
    "select_usb_audio_device",
]
