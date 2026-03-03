"""Abstract Radio Protocol — multi-backend radio control interface.

Defines :class:`Radio` (core) and optional capability Protocols
(:class:`AudioCapable`, :class:`ScopeCapable`, :class:`DualReceiverCapable`)
so that the Web UI, rigctld server, and CLI can work with **any** radio
backend — Icom LAN, Icom serial, Yaesu CAT, etc.

Quick start::

    from icom_lan.radio_protocol import Radio, AudioCapable

    async def tune(radio: Radio) -> None:
        await radio.set_frequency(14_074_000)
        mode, filt = await radio.get_mode()
        print(f"Mode: {mode}, filter: {filt}")

    # Check optional capabilities at runtime:
    if isinstance(radio, AudioCapable):
        await radio.start_audio_rx(callback)

Architecture::

    ┌──────────────────────────────────────────────┐
    │          Web UI  /  rigctld  /  CLI           │
    ├──────────────────────────────────────────────┤
    │          Radio Protocol (core)                │
    │  ┌──────────────┬─────────────┬────────────┐ │
    │  │ AudioCapable │ ScopeCapable│ DualRxCap. │ │
    │  └──────────────┴─────────────┴────────────┘ │
    ├────────┬──────────┬──────────┬───────────────┤
    │IcomLAN │IcomSerial│ YaesuCAT │  Future...    │
    └────────┴──────────┴──────────┴───────────────┘

Standard mode names (cross-vendor):
    USB, LSB, CW, CWR, AM, FM, RTTY, RTTYR, PSK, PSKR, DV, DD

Standard capability tags:
    audio, scope, dual_rx, meters, tx, cw,
    attenuator, preamp, rf_gain, af_level, squelch, nb, nr
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Protocol, runtime_checkable

from .radio_state import RadioState

__all__ = [
    "Radio",
    "AudioCapable",
    "ScopeCapable",
    "DualReceiverCapable",
]


# ---------------------------------------------------------------------------
# Core Protocol — every backend MUST implement this
# ---------------------------------------------------------------------------


@runtime_checkable
class Radio(Protocol):
    """Core interface for a controllable radio transceiver.

    Every radio backend must implement this protocol.  Optional features
    (audio streaming, spectrum scope, dual receivers) are expressed as
    separate protocols that a backend may additionally implement.
    """

    # -- Lifecycle ---------------------------------------------------------

    async def connect(self) -> None:
        """Establish connection to the radio."""
        ...

    async def disconnect(self) -> None:
        """Disconnect from the radio, releasing all resources."""
        ...

    @property
    def connected(self) -> bool:
        """Whether the radio is currently connected and healthy."""
        ...

    # -- Frequency ---------------------------------------------------------

    async def get_frequency(self, receiver: int = 0) -> int:
        """Get the current frequency in Hz.

        Args:
            receiver: 0 = main (default), 1 = sub.
        """
        ...

    async def set_frequency(self, freq: int, receiver: int = 0) -> None:
        """Set the frequency in Hz.

        Args:
            freq: Frequency in Hz (e.g. 14_074_000).
            receiver: 0 = main (default), 1 = sub.
        """
        ...

    # -- Mode --------------------------------------------------------------

    async def get_mode(self, receiver: int = 0) -> tuple[str, int | None]:
        """Get the current operating mode.

        Returns:
            Tuple of (mode_name, filter_number_or_None).
            Mode names are standardised strings: USB, LSB, CW, AM, FM, etc.
        """
        ...

    async def set_mode(
        self, mode: str, filter_width: int | None = None, receiver: int = 0,
    ) -> None:
        """Set the operating mode.

        Args:
            mode: Mode name string (e.g. "USB", "CW", "FT8").
            filter_width: Optional filter number (1-3 on Icom, varies by vendor).
            receiver: 0 = main, 1 = sub.
        """
        ...

    async def get_data_mode(self) -> bool:
        """Whether DATA mode is active (e.g. USB-D for FT8/FT4)."""
        ...

    async def set_data_mode(self, on: bool) -> None:
        """Enable or disable DATA mode."""
        ...

    # -- TX ----------------------------------------------------------------

    async def set_ptt(self, on: bool) -> None:
        """Key or unkey the transmitter."""
        ...

    # -- Meters ------------------------------------------------------------

    async def get_s_meter(self, receiver: int = 0) -> int:
        """Get S-meter reading (raw value, vendor-specific scale)."""
        ...

    async def get_swr(self) -> float:
        """Get SWR reading (1.0 = perfect match)."""
        ...

    # -- Power -------------------------------------------------------------

    async def get_power(self) -> int:
        """Get TX power level (0-255 normalised scale)."""
        ...

    async def set_power(self, level: int) -> None:
        """Set TX power level (0-255 normalised scale)."""
        ...

    # -- Levels ------------------------------------------------------------

    async def set_af_level(self, level: int) -> None:
        """Set AF (audio) output level (0-255)."""
        ...

    async def set_rf_gain(self, level: int) -> None:
        """Set RF gain level (0-255)."""
        ...

    async def set_squelch(self, level: int) -> None:
        """Set squelch level (0-255)."""
        ...

    # -- State -------------------------------------------------------------

    @property
    def radio_state(self) -> RadioState:
        """Live radio state (freq, mode, meters for all receivers)."""
        ...

    @property
    def model(self) -> str:
        """Human-readable radio model name (e.g. 'IC-7610', 'FTX-1')."""
        ...

    @property
    def capabilities(self) -> set[str]:
        """Set of capability tags this radio supports.

        Standard tags: audio, scope, dual_rx, meters, tx, cw,
        attenuator, preamp, rf_gain, af_level, squelch, nb, nr.
        """
        ...

    # -- Server integration ------------------------------------------------

    def set_state_change_callback(
        self, callback: Callable[..., Any] | None,
    ) -> None:
        """Register a callback for radio state change notifications.

        Called by the web server to receive real-time updates.
        Pass ``None`` to unregister.
        """
        ...

    def set_reconnect_callback(
        self, callback: Callable[..., Any] | None,
    ) -> None:
        """Register a callback invoked after successful reconnection.

        Used by the web server to re-enable scope/audio after transport
        recovery.  Pass ``None`` to unregister.
        """
        ...


# ---------------------------------------------------------------------------
# Optional capability Protocols
# ---------------------------------------------------------------------------


@runtime_checkable
class AudioCapable(Protocol):
    """Radio supports real-time audio streaming (LAN, USB, or virtual).

    Audio format is Opus-encoded.  For USB audio devices, the backend
    handles capture/playback internally and exposes the same interface.
    """

    async def start_audio_rx_opus(
        self, callback: Callable[..., Awaitable[None]],
    ) -> None:
        """Start receiving audio.  Decoded frames are passed to *callback*."""
        ...

    async def stop_audio_rx_opus(self) -> None:
        """Stop receiving audio."""
        ...

    async def push_audio_tx_opus(self, data: bytes) -> None:
        """Send Opus-encoded audio data for transmission."""
        ...


@runtime_checkable
class ScopeCapable(Protocol):
    """Radio supports a spectrum/panadapter scope data stream."""

    async def enable_scope(self, **kwargs: Any) -> None:
        """Enable the spectrum scope.

        Keyword arguments are backend-specific (e.g. span, center_freq).
        """
        ...

    async def disable_scope(self) -> None:
        """Disable the spectrum scope."""
        ...


@runtime_checkable
class DualReceiverCapable(Protocol):
    """Radio has two independent receivers (e.g. IC-7610 Main/Sub)."""

    async def vfo_exchange(self) -> None:
        """Swap Main and Sub VFO frequencies."""
        ...

    async def vfo_equalize(self) -> None:
        """Set Sub VFO frequency equal to Main."""
        ...
