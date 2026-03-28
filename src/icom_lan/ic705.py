"""IC-705 convenience helpers for data and packet-mode workflows."""

from __future__ import annotations

from typing import Protocol

from .types import ScopeCompletionPolicy


class Ic705DataProfileCapable(Protocol):
    """Minimal radio surface required by the IC-705 data-profile helpers."""

    async def snapshot_state(self) -> dict[str, object]: ...

    async def restore_state(self, state: dict[str, object]) -> None: ...

    async def set_vox(self, on: bool) -> None: ...

    async def set_vfo(self, vfo: str = "A") -> None: ...

    async def set_split_mode(self, on: bool) -> None: ...

    async def set_freq(self, freq_hz: int) -> None: ...

    async def set_mode(self, mode: str, filter_width: int | None = None) -> None: ...

    async def set_data_mode(self, on: int | bool, receiver: int = 0) -> None: ...

    async def set_data_off_mod_input(self, source: int) -> None: ...

    async def set_data1_mod_input(self, source: int) -> None: ...

    async def vfo_equalize(self) -> None: ...

    async def set_squelch(self, level: int, receiver: int = 0) -> None: ...

    async def enable_scope(
        self,
        *,
        output: bool = True,
        policy: ScopeCompletionPolicy | str = ScopeCompletionPolicy.VERIFY,
        timeout: float = 5.0,
    ) -> None: ...

    async def set_scope_mode(self, mode: int) -> None: ...

    async def set_scope_span(self, span: int) -> None: ...


async def prepare_ic705_data_profile(
    radio: Ic705DataProfileCapable,
    *,
    frequency_hz: int,
    mode: str = "FM",
    data_off_mod_input: int | None = None,
    data1_mod_input: int | None = None,
    disable_vox: bool = True,
    squelch_level: int | None = 0,
    enable_scope: bool = False,
    scope_output: bool = False,
    scope_policy: ScopeCompletionPolicy | str = ScopeCompletionPolicy.FAST,
    scope_timeout: float = 5.0,
    scope_mode: int | None = 0,
    scope_span: int | None = 7,
) -> dict[str, object]:
    """Prepare an IC-705 for packet/data work and return a restore snapshot.

    The helper applies the common packet/data workflow used by downstream
    integrations:
    - select VFO A
    - disable split
    - tune both VFOs to the same frequency
    - set a mode such as FM
    - enable DATA mode
    - optionally route modulation inputs
    - optionally open squelch and enable scope

    Returns:
        Snapshot from :meth:`snapshot_state` suitable for
        :func:`restore_ic705_data_profile`.
    """

    snapshot = await radio.snapshot_state()

    if disable_vox:
        await radio.set_vox(False)
    await radio.set_vfo("A")
    await radio.set_split_mode(False)
    await radio.set_freq(int(frequency_hz))
    await radio.set_mode(mode)
    await radio.set_data_mode(True)
    if data_off_mod_input is not None:
        await radio.set_data_off_mod_input(int(data_off_mod_input))
    if data1_mod_input is not None:
        await radio.set_data1_mod_input(int(data1_mod_input))
    await radio.vfo_equalize()
    if squelch_level is not None:
        await radio.set_squelch(int(squelch_level))
    if enable_scope:
        await radio.enable_scope(
            output=scope_output,
            policy=scope_policy,
            timeout=scope_timeout,
        )
        if scope_mode is not None:
            await radio.set_scope_mode(int(scope_mode))
        if scope_span is not None:
            await radio.set_scope_span(int(scope_span))
    await radio.set_vfo("A")
    return snapshot


async def restore_ic705_data_profile(
    radio: Ic705DataProfileCapable,
    snapshot: dict[str, object],
) -> None:
    """Restore a snapshot returned by :func:`prepare_ic705_data_profile`."""

    await radio.restore_state(snapshot)


__all__ = [
    "Ic705DataProfileCapable",
    "prepare_ic705_data_profile",
    "restore_ic705_data_profile",
]
