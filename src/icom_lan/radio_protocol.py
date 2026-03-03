"""Abstract Radio Protocol definitions for icom-lan.

Defines :class:`Radio` and optional-capability Protocols so that the Web UI,
rigctld server, and other consumers can work with any radio backend, not just
:class:`~icom_lan.radio.IcomRadio`.

Usage::

    from icom_lan.radio_protocol import Radio, AudioCapable, ScopeCapable

    def needs_radio(r: Radio) -> None:
        ...

    if isinstance(r, AudioCapable):
        await r.start_audio_rx_opus(callback)
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


@runtime_checkable
class Radio(Protocol):
    """Minimal interface for a controllable radio transceiver."""

    async def connect(self) -> None: ...
    async def disconnect(self) -> None: ...

    @property
    def connected(self) -> bool: ...

    # Frequency
    async def get_frequency(self, receiver: int = 0) -> int: ...
    async def set_frequency(self, freq: int, receiver: int = 0) -> None: ...

    # Mode — returns (mode_name, filter_number_or_None)
    async def get_mode(self, receiver: int = 0) -> tuple[str, int | None]: ...
    async def set_mode(
        self, mode: Any, filter_width: int | None = None, receiver: int = 0
    ) -> None: ...

    # DATA mode
    async def get_data_mode(self) -> bool: ...
    async def set_data_mode(self, on: bool) -> None: ...

    # TX
    async def set_ptt(self, on: bool) -> None: ...

    # Meters
    async def get_s_meter(self, receiver: int = 0) -> int: ...
    async def get_swr(self) -> float: ...

    # Power
    async def get_power(self) -> int: ...
    async def set_power(self, level: int) -> None: ...

    # Levels
    async def set_af_level(self, level: int) -> None: ...
    async def set_rf_gain(self, level: int) -> None: ...
    async def set_squelch(self, level: int) -> None: ...

    # State
    @property
    def radio_state(self) -> RadioState: ...

    @property
    def model(self) -> str: ...

    @property
    def capabilities(self) -> set[str]: ...

    # Callback registration (for server integration)
    def set_state_change_callback(self, callback: Callable[..., Any] | None) -> None: ...
    def set_reconnect_callback(self, callback: Callable[..., Any] | None) -> None: ...


@runtime_checkable
class AudioCapable(Protocol):
    """Optional protocol for radios that support audio streaming."""

    async def start_audio_rx_opus(
        self, callback: Callable[..., Awaitable[None]]
    ) -> None: ...

    async def stop_audio_rx_opus(self) -> None: ...

    async def push_audio_tx_opus(self, data: bytes) -> None: ...


@runtime_checkable
class ScopeCapable(Protocol):
    """Optional protocol for radios that support a panadapter scope."""

    async def enable_scope(self, **kwargs: Any) -> None: ...
    async def disable_scope(self) -> None: ...


@runtime_checkable
class DualReceiverCapable(Protocol):
    """Optional protocol for radios with dual independent receivers."""

    async def vfo_exchange(self) -> None: ...
    async def vfo_equalize(self) -> None: ...
