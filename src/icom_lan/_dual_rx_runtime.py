"""DualRxRuntimeMixin — dual-receiver routing methods extracted from CoreRadio.

Part of the radio.py decomposition (#505). All methods are accessed via
``IcomRadio`` which inherits this mixin.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any, Awaitable, Callable

    from .radio import CoreRadio as _MixinBase  # type: ignore[attr-defined]
else:
    _MixinBase = object

from .commands import (
    CONTROLLER_ADDR,
    RECEIVER_MAIN,
    build_civ_frame,
    get_freq,
    get_mode,
    parse_frequency_response,
    parse_mode_response,
    set_freq,
    set_mode,
)
from .commands import get_selected_freq as _get_selected_freq_cmd
from .commands import get_selected_mode as _get_selected_mode_cmd
from .commands import get_unselected_freq as _get_unselected_freq_cmd
from .commands import get_unselected_mode as _get_unselected_mode_cmd
from .commands import parse_selected_freq_response as _parse_selected_freq_response
from .commands import parse_selected_mode_response as _parse_selected_mode_response
from .exceptions import CommandError, TimeoutError
from .types import Mode

# CI-V command byte for VFO select / equal / swap (0x07).
_CMD_VFO = 0x07

logger = logging.getLogger(__name__)


class DualRxRuntimeMixin(_MixinBase):  # type: ignore[misc]
    """Dual-receiver routing methods for CoreRadio (mixin)."""

    def _require_receiver(self, receiver: int, *, operation: str) -> None:
        """Validate receiver index against active profile."""
        if self._profile.supports_receiver(receiver):
            return
        raise CommandError(
            f"{operation} does not support receiver={receiver} for profile "
            f"{self._profile.model} (receivers={self._profile.receiver_count})"
        )

    def _require_capability(self, capability: str, *, operation: str) -> None:
        """Ensure a profile capability exists before executing operation."""
        if self._profile.supports_capability(capability):
            return
        raise CommandError(
            f"{operation} is not supported by profile {self._profile.model} "
            f"(missing capability: {capability})"
        )

    def _require_cmd29_route(
        self,
        command: int,
        sub: int | None,
        *,
        receiver: int,
        operation: str,
    ) -> None:
        """Require Command29 support for per-receiver command routing."""
        if receiver == RECEIVER_MAIN:
            return
        if self._profile.supports_cmd29(command, sub):
            return
        raise CommandError(
            f"{operation} receiver={receiver} is unsupported for profile "
            f"{self._profile.model}: command 0x{command:02X}"
            + (f"/0x{sub:02X}" if sub is not None else "")
            + " has no cmd29 route"
        )

    def _active_receiver_name(self) -> str:
        """Best-effort active receiver name for VFO-routing fallbacks."""
        active = getattr(self._radio_state, "active", None)
        if active in {"MAIN", "SUB"}:
            return str(active)
        if self._last_vfo in {"SUB", "B"}:
            return "SUB"
        return "MAIN"

    async def _run_with_receiver_vfo_fallback(
        self,
        *,
        receiver: int,
        operation: str,
        action: Callable[[], Awaitable[Any]],
    ) -> Any:
        """Run an operation for a receiver using temporary MAIN/SUB VFO switching."""
        target = "MAIN" if receiver == RECEIVER_MAIN else "SUB"
        current = self._active_receiver_name()
        switched = False

        if current != target:
            if target == "SUB" and self._profile.vfo_sub_code is None:
                raise CommandError(
                    f"{operation} receiver={receiver} is unsupported for profile "
                    f"{self._profile.model}: no SUB VFO select code"
                )
            if target == "MAIN" and self._profile.vfo_main_code is None:
                raise CommandError(
                    f"{operation} receiver={receiver} is unsupported for profile "
                    f"{self._profile.model}: no MAIN VFO select code"
                )
            await self.set_vfo(target)
            self._radio_state.active = target
            switched = True

        try:
            return await action()
        finally:
            if switched:
                try:
                    await self.set_vfo(current)
                    self._radio_state.active = current
                except TimeoutError:
                    # Do not swallow — radio would silently remain on the
                    # temporary receiver. Retry once (the first attempt may
                    # fail because a prior fire-and-forget ACK sink consumed
                    # the timeout budget), then propagate on a second failure.
                    logger.warning(
                        "%s: timeout restoring VFO receiver to %s, retrying once",
                        operation,
                        current,
                    )
                    await self.set_vfo(current)
                    self._radio_state.active = current

    async def _get_frequency_main(
        self, *, bypass_cache: bool = False, update_cache: bool = True
    ) -> int:
        """Read MAIN receiver frequency with optional cache updates."""
        civ = get_freq(to_addr=self._radio_addr)
        try:
            resp = await self._send_civ_expect(
                civ,
                key="get_frequency",
                dedupe=not bypass_cache,
                label="get_frequency",
            )
            freq = parse_frequency_response(resp)
            if update_cache:
                self._last_freq_hz = freq
                self._state_cache.update_freq(freq)
            return freq
        except TimeoutError:
            if update_cache and self._state_cache.is_fresh(
                "freq", self._cache_ttl_freq
            ):
                logger.debug(
                    "get_frequency: timeout, returning cached %d Hz",
                    self._state_cache.freq,
                )
                return self._state_cache.freq  # type: ignore[no-any-return]
            raise

    async def _set_frequency_main(
        self, freq_hz: int, *, update_cache: bool = True
    ) -> None:
        """Set MAIN receiver frequency with optional cache updates."""
        civ = set_freq(freq_hz, to_addr=self._radio_addr, receiver=RECEIVER_MAIN)
        await self._send_civ_raw(civ, wait_response=False)
        if update_cache:
            self._last_freq_hz = freq_hz
            self._state_cache.update_freq(freq_hz)

    async def _get_mode_info_main(
        self, *, update_cache: bool = True
    ) -> tuple[Mode, int | None]:
        """Read MAIN receiver mode/filter with optional cache updates."""
        civ = get_mode(to_addr=self._radio_addr)
        try:
            resp = await self._send_civ_expect(civ, label="get_mode_info_main")
            mode, filt = parse_mode_response(resp)
            if update_cache:
                self._last_mode = mode
                if filt is not None:
                    self._filter_width = filt
                self._state_cache.update_mode(mode.name, filt)
            return mode, filt
        except TimeoutError:
            if update_cache and self._state_cache.is_fresh(
                "mode", self._cache_ttl_mode
            ):
                logger.debug(
                    "get_mode_info: timeout, returning cached %s",
                    self._state_cache.mode,
                )
                return Mode[self._state_cache.mode], self._state_cache.filter_width
            raise

    async def _set_mode_main(
        self,
        mode: Mode,
        *,
        filter_width: int | None = None,
        update_cache: bool = True,
    ) -> None:
        """Set MAIN receiver mode/filter with optional cache updates."""
        civ = set_mode(
            mode,
            filter_width=filter_width,
            to_addr=self._radio_addr,
            receiver=RECEIVER_MAIN,
        )
        await self._send_civ_raw(civ, wait_response=False)
        self._last_mode = mode
        if update_cache:
            if filter_width is not None:
                self._filter_width = filter_width
            cached_filter = (
                filter_width if filter_width is not None else self._filter_width
            )
            self._state_cache.update_mode(mode.name, cached_filter)

    # ------------------------------------------------------------------
    # Selected / Unselected receiver freq & mode (0x25 / 0x26)
    # ------------------------------------------------------------------

    async def _get_selected_freq(self) -> int:
        """Read the selected (active) receiver frequency via CI-V 0x25 0x00."""
        civ = _get_selected_freq_cmd(to_addr=self._radio_addr)
        resp = await self._send_civ_expect(civ, label="get_selected_freq")
        _rcvr, freq = _parse_selected_freq_response(resp)
        return freq

    async def _get_unselected_freq(self) -> int:
        """Read the unselected (inactive) receiver frequency via CI-V 0x25 0x01."""
        civ = _get_unselected_freq_cmd(to_addr=self._radio_addr)
        resp = await self._send_civ_expect(civ, label="get_unselected_freq")
        _rcvr, freq = _parse_selected_freq_response(resp)
        return freq

    async def _get_selected_mode(self) -> tuple[Mode, int | None]:
        """Read the selected (active) receiver mode via CI-V 0x26 0x00."""
        civ = _get_selected_mode_cmd(to_addr=self._radio_addr)
        resp = await self._send_civ_expect(civ, label="get_selected_mode")
        _rcvr, mode, _data_mode, filt = _parse_selected_mode_response(resp)
        return mode, filt

    async def _get_unselected_mode(self) -> tuple[Mode, int | None]:
        """Read the unselected (inactive) receiver mode via CI-V 0x26 0x01."""
        civ = _get_unselected_mode_cmd(to_addr=self._radio_addr)
        resp = await self._send_civ_expect(civ, label="get_unselected_mode")
        _rcvr, mode, _data_mode, filt = _parse_selected_mode_response(resp)
        return mode, filt

    # ------------------------------------------------------------------
    # Explicit swap/equalize — MAIN/SUB vs A/B (issue #714)
    # ------------------------------------------------------------------

    async def swap_main_sub(self) -> None:
        """Swap MAIN and SUB VFO frequencies. Requires a dual-RX profile."""
        self._check_connected()
        if self._profile.receiver_count < 2:
            raise CommandError(
                f"swap_main_sub not supported by profile {self._profile.model}: "
                "not dual-RX"
            )
        code = self._profile.swap_main_sub_code
        if code is None:
            raise CommandError(
                f"swap_main_sub not supported by profile {self._profile.model}: "
                "no swap_main_sub_code"
            )
        civ = build_civ_frame(
            self._radio_addr, CONTROLLER_ADDR, _CMD_VFO, data=bytes([code])
        )
        await self._send_civ_raw(civ, wait_response=False)

    async def equalize_main_sub(self) -> None:
        """Copy MAIN VFO state to SUB. Requires a dual-RX profile."""
        self._check_connected()
        if self._profile.receiver_count < 2:
            raise CommandError(
                f"equalize_main_sub not supported by profile "
                f"{self._profile.model}: not dual-RX"
            )
        code = self._profile.equal_main_sub_code
        if code is None:
            raise CommandError(
                f"equalize_main_sub not supported by profile "
                f"{self._profile.model}: no equal_main_sub_code"
            )
        civ = build_civ_frame(
            self._radio_addr, CONTROLLER_ADDR, _CMD_VFO, data=bytes([code])
        )
        await self._send_civ_raw(civ, wait_response=False)

    async def swap_vfo_ab(self, receiver: int = 0) -> None:
        """Swap VFO A and VFO B within ``receiver``.

        On dual-RX profiles the target receiver (MAIN/SUB) is selected
        first so the swap opcode affects the intended receiver.  On
        single-RX profiles the swap is issued directly.

        Raises ``CommandError`` when the profile does not declare a
        dedicated ``swap_ab_code``.  We do NOT silently fall back to
        ``swap_main_sub_code`` because on IC-7610 / IC-9700 that opcode
        exchanges MAIN↔SUB — a different semantic than A↔B within a
        single receiver.  Callers wanting MAIN↔SUB must use
        ``swap_main_sub()`` explicitly.
        """
        self._check_connected()
        self._require_receiver(receiver, operation="swap_vfo_ab")
        code = self._profile.swap_ab_code
        if code is None:
            raise CommandError(
                f"swap_vfo_ab not supported by {self._profile.model}: "
                "profile declares no swap_ab_code. "
                "For MAIN↔SUB exchange use swap_main_sub()."
            )
        if self._profile.receiver_count > 1:
            target = "MAIN" if receiver == RECEIVER_MAIN else "SUB"
            await self.set_vfo(target)
        civ = build_civ_frame(
            self._radio_addr, CONTROLLER_ADDR, _CMD_VFO, data=bytes([code])
        )
        await self._send_civ_raw(civ, wait_response=False)

    async def equalize_vfo_ab(self, receiver: int = 0) -> None:
        """Copy the active VFO's state to the inactive VFO on ``receiver``.

        Raises ``CommandError`` when the profile does not declare a
        dedicated ``equal_ab_code``.  We do NOT silently fall back to
        ``equal_main_sub_code``: on dual-RX rigs that opcode copies
        MAIN→SUB, not A→B within a receiver.
        """
        self._check_connected()
        self._require_receiver(receiver, operation="equalize_vfo_ab")
        code = self._profile.equal_ab_code
        if code is None:
            raise CommandError(
                f"equalize_vfo_ab not supported by {self._profile.model}: "
                "profile declares no equal_ab_code. "
                "For MAIN→SUB copy use equalize_main_sub()."
            )
        if self._profile.receiver_count > 1:
            target = "MAIN" if receiver == RECEIVER_MAIN else "SUB"
            await self.set_vfo(target)
        civ = build_civ_frame(
            self._radio_addr, CONTROLLER_ADDR, _CMD_VFO, data=bytes([code])
        )
        await self._send_civ_raw(civ, wait_response=False)
