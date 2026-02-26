"""Synchronous (blocking) wrapper around :class:`~icom_lan.radio.IcomRadio`.

Provides the same API as the async version but runs an internal event loop
so callers don't need ``async/await``.

Example::

    from icom_lan.sync import IcomRadio

    with IcomRadio("192.168.1.100", username="u", password="p") as radio:
        print(radio.get_frequency())
        radio.set_frequency(14_074_000)
"""

import asyncio
import warnings
from typing import Callable

from .audio import AudioPacket
from .radio import IcomRadio as _AsyncIcomRadio
from .types import AudioCapabilities, AudioCodec, Mode

__all__ = ["IcomRadio"]


class IcomRadio:
    """Synchronous (blocking) wrapper for Icom radio LAN control.

    Wraps the async :class:`~icom_lan.radio.IcomRadio` with a dedicated
    event loop. All methods block until the operation completes.

    Args:
        host: Radio IP address or hostname.
        port: Control port (default 50001).
        username: Authentication username.
        password: Authentication password.
        radio_addr: CI-V address of the radio (default IC-7610 = 0x98).
        timeout: Operation timeout in seconds.
        audio_codec: Audio codec (default PCM 1ch 16-bit).
        audio_sample_rate: Audio sample rate in Hz.
    """

    def __init__(
        self,
        host: str,
        port: int = 50001,
        username: str = "",
        password: str = "",
        radio_addr: int = 0x98,
        timeout: float = 5.0,
        audio_codec: AudioCodec | int = AudioCodec.PCM_1CH_16BIT,
        audio_sample_rate: int = 48000,
    ) -> None:
        self._loop = asyncio.new_event_loop()
        self._radio = _AsyncIcomRadio(
            host,
            port=port,
            username=username,
            password=password,
            radio_addr=radio_addr,
            timeout=timeout,
            audio_codec=audio_codec,
            audio_sample_rate=audio_sample_rate,
        )

    def _run(self, coro):  # type: ignore[no-untyped-def]
        """Run a coroutine on the internal event loop."""
        return self._loop.run_until_complete(coro)

    @staticmethod
    def _warn_audio_alias(old_name: str, replacement: str) -> None:
        warnings.warn(
            (
                f"icom_lan.sync.IcomRadio.{old_name}() is deprecated and will be "
                f"removed after two minor releases; use {replacement}() instead."
            ),
            DeprecationWarning,
            stacklevel=2,
        )

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def connect(self) -> None:
        """Connect to the radio (blocking)."""
        self._run(self._radio.connect())

    def disconnect(self) -> None:
        """Disconnect from the radio (blocking)."""
        self._run(self._radio.disconnect())

    @property
    def connected(self) -> bool:
        """Whether the radio is currently connected."""
        return self._radio.connected

    def __enter__(self) -> "IcomRadio":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # type: ignore[no-untyped-def]
        self.disconnect()
        self._loop.close()

    # ------------------------------------------------------------------
    # Frequency
    # ------------------------------------------------------------------

    def get_frequency(self) -> int:
        """Get the current operating frequency in Hz."""
        return self._run(self._radio.get_frequency())

    def set_frequency(self, freq_hz: int) -> None:
        """Set the operating frequency in Hz."""
        self._run(self._radio.set_frequency(freq_hz))

    # ------------------------------------------------------------------
    # Mode
    # ------------------------------------------------------------------

    def get_mode(self) -> Mode:
        """Get the current operating mode."""
        return self._run(self._radio.get_mode())

    def get_mode_info(self) -> tuple[Mode, int | None]:
        """Get current mode and filter number (if reported)."""
        return self._run(self._radio.get_mode_info())

    def get_filter(self) -> int | None:
        """Get current filter number (1-3) when available."""
        return self._run(self._radio.get_filter())

    def set_filter(self, filter_width: int) -> None:
        """Set filter number (1-3) while keeping current mode."""
        self._run(self._radio.set_filter(filter_width))

    def set_mode(self, mode: str | Mode, filter_width: int | None = None) -> None:
        """Set the operating mode."""
        self._run(self._radio.set_mode(mode, filter_width))

    # ------------------------------------------------------------------
    # Power
    # ------------------------------------------------------------------

    def get_power(self) -> int:
        """Get the RF power level (0-255)."""
        return self._run(self._radio.get_power())

    def set_power(self, level: int) -> None:
        """Set the RF power level (0-255)."""
        self._run(self._radio.set_power(level))

    # ------------------------------------------------------------------
    # Meters
    # ------------------------------------------------------------------

    def get_s_meter(self) -> int:
        """Read the S-meter value (0-255)."""
        return self._run(self._radio.get_s_meter())

    def get_swr(self) -> int:
        """Read the SWR meter (0-255)."""
        return self._run(self._radio.get_swr())

    def get_alc(self) -> int:
        """Read the ALC meter (0-255)."""
        return self._run(self._radio.get_alc())

    # ------------------------------------------------------------------
    # PTT
    # ------------------------------------------------------------------

    def set_ptt(self, on: bool) -> None:
        """Enable or disable PTT."""
        self._run(self._radio.set_ptt(on))

    # ------------------------------------------------------------------
    # VFO / Split
    # ------------------------------------------------------------------

    def select_vfo(self, vfo: str = "A") -> None:
        """Select VFO (A, B, MAIN, SUB)."""
        self._run(self._radio.select_vfo(vfo))

    def vfo_equalize(self) -> None:
        """Copy VFO A to VFO B."""
        self._run(self._radio.vfo_equalize())

    def vfo_exchange(self) -> None:
        """Swap VFO A and B."""
        self._run(self._radio.vfo_exchange())

    def set_split_mode(self, on: bool) -> None:
        """Enable or disable split mode."""
        self._run(self._radio.set_split_mode(on))

    # ------------------------------------------------------------------
    # Attenuator / Preamp
    # ------------------------------------------------------------------

    def get_attenuator_level(self) -> int:
        """Read attenuator level in dB."""
        return self._run(self._radio.get_attenuator_level())

    def get_attenuator(self) -> bool:
        """Read attenuator state."""
        return self._run(self._radio.get_attenuator())

    def set_attenuator_level(self, db: int) -> None:
        """Set attenuator level in dB."""
        self._run(self._radio.set_attenuator_level(db))

    def set_attenuator(self, on: bool) -> None:
        """Enable or disable the attenuator."""
        self._run(self._radio.set_attenuator(on))

    def get_preamp(self) -> int:
        """Read preamp level (0=off, 1=PREAMP1, 2=PREAMP2)."""
        return self._run(self._radio.get_preamp())

    def set_preamp(self, level: int = 1) -> None:
        """Set preamp level (0=off, 1=PREAMP1, 2=PREAMP2)."""
        self._run(self._radio.set_preamp(level))

    def get_digisel(self) -> bool:
        """Read DIGI-SEL status."""
        return self._run(self._radio.get_digisel())

    def set_digisel(self, on: bool) -> None:
        """Set DIGI-SEL status."""
        self._run(self._radio.set_digisel(on))

    # ------------------------------------------------------------------
    # State snapshot/restore
    # ------------------------------------------------------------------

    def snapshot_state(self) -> dict[str, object]:
        """Best-effort snapshot of core rig state."""
        return self._run(self._radio.snapshot_state())

    def restore_state(self, state: dict[str, object]) -> None:
        """Best-effort restore of snapshot_state()."""
        self._run(self._radio.restore_state(state))

    # ------------------------------------------------------------------
    # CW
    # ------------------------------------------------------------------

    def send_cw_text(self, text: str) -> None:
        """Send CW text."""
        self._run(self._radio.send_cw_text(text))

    def stop_cw_text(self) -> None:
        """Stop CW sending."""
        self._run(self._radio.stop_cw_text())

    # ------------------------------------------------------------------
    # Power control
    # ------------------------------------------------------------------

    def power_control(self, on: bool) -> None:
        """Power on/off the radio."""
        self._run(self._radio.power_control(on))

    # ------------------------------------------------------------------
    # Audio
    # ------------------------------------------------------------------

    def start_audio_rx_opus(
        self,
        callback: Callable[[AudioPacket | None], None],
        *,
        jitter_depth: int = 5,
    ) -> None:
        """Start receiving Opus audio from the radio (blocking setup)."""
        self._run(self._radio.start_audio_rx_opus(callback, jitter_depth=jitter_depth))

    def stop_audio_rx_opus(self) -> None:
        """Stop Opus RX audio."""
        self._run(self._radio.stop_audio_rx_opus())

    def start_audio_tx_opus(self) -> None:
        """Start Opus TX audio."""
        self._run(self._radio.start_audio_tx_opus())

    def push_audio_tx_opus(self, opus_data: bytes) -> None:
        """Send an Opus audio frame to the radio."""
        self._run(self._radio.push_audio_tx_opus(opus_data))

    def stop_audio_tx_opus(self) -> None:
        """Stop Opus TX audio."""
        self._run(self._radio.stop_audio_tx_opus())

    def start_audio_rx(self, callback: Callable[[AudioPacket | None], None]) -> None:
        """Deprecated alias for :meth:`start_audio_rx_opus`."""
        self._warn_audio_alias("start_audio_rx", "start_audio_rx_opus")
        self.start_audio_rx_opus(callback)

    def stop_audio_rx(self) -> None:
        """Deprecated alias for :meth:`stop_audio_rx_opus`."""
        self._warn_audio_alias("stop_audio_rx", "stop_audio_rx_opus")
        self.stop_audio_rx_opus()

    def start_audio_tx(self) -> None:
        """Deprecated alias for :meth:`start_audio_tx_opus`."""
        self._warn_audio_alias("start_audio_tx", "start_audio_tx_opus")
        self.start_audio_tx_opus()

    def push_audio_tx(self, opus_data: bytes) -> None:
        """Deprecated alias for :meth:`push_audio_tx_opus`."""
        self._warn_audio_alias("push_audio_tx", "push_audio_tx_opus")
        self.push_audio_tx_opus(opus_data)

    def stop_audio_tx(self) -> None:
        """Deprecated alias for :meth:`stop_audio_tx_opus`."""
        self._warn_audio_alias("stop_audio_tx", "stop_audio_tx_opus")
        self.stop_audio_tx_opus()

    def get_audio_stats(self) -> dict[str, bool | int | float | str]:
        """Return runtime audio stats for the active stream."""
        return self._radio.get_audio_stats()

    @property
    def audio_codec(self) -> AudioCodec:
        """Configured audio codec."""
        return self._radio.audio_codec

    @property
    def audio_sample_rate(self) -> int:
        """Configured audio sample rate."""
        return self._radio.audio_sample_rate

    @staticmethod
    def audio_capabilities() -> AudioCapabilities:
        """Return icom-lan audio capabilities and deterministic defaults."""
        return _AsyncIcomRadio.audio_capabilities()
