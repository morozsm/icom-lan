"""Generic capability-aware radio profile system.

A profile is a declarative desired state — set only the fields you want
to change. ``apply_profile`` inspects the radio for each setter and silently
skips fields the radio does not support.

Example::

    from icom_lan import OperatingProfile, apply_profile, PRESETS

    # Custom profile
    profile = OperatingProfile(
        frequency_hz=145_500_000,
        mode="FM",
        data_mode=True,
        vox=False,
    )
    snapshot = await apply_profile(radio, profile)
    # ... operate ...
    await radio.restore_state(snapshot)

    # Using a built-in preset
    snapshot = await apply_profile(radio, PRESETS.ft8_20m)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

from .types import ScopeCompletionPolicy

logger = logging.getLogger(__name__)

__all__ = [
    "OperatingProfile",
    "apply_profile",
    "PRESETS",
]


@dataclass
class OperatingProfile:
    """Declarative desired radio state.

    Each field defaults to ``None``, meaning "do not touch this setting".
    Set only the fields you want to change. Boolean fields like ``vox=False``
    explicitly disable the feature — they are distinct from ``None`` (unchanged).

    Attributes:
        frequency_hz: Tuning frequency in Hz.
        mode: Operating mode string, e.g. ``"FM"``, ``"USB"``, ``"CW"``.
        filter_width: Passband filter width in Hz (passed to ``set_mode``).
        vox: ``True`` to enable VOX, ``False`` to disable.
        split: ``True`` to enable split, ``False`` to disable.
        vfo: VFO to select, ``"A"`` or ``"B"``.
        data_mode: ``True`` to enable DATA mode, ``False`` to disable.
        data_off_mod_input: DATA-OFF modulation input source index.
        data1_mod_input: DATA-1 modulation input source index.
        squelch_level: Squelch level (0 = open).
        equalize_vfo: If ``True``, copy the active VFO to both VFOs after
            tuning. Requires ``radio.vfo_equalize()``.
        scope_enabled: ``True`` to enable spectrum scope, ``False`` to disable,
            ``None`` to leave unchanged.
        scope_mode: Scope centre/fixed mode index.
        scope_span: Scope span index.
        scope_output: Passed as the ``output`` keyword arg to ``enable_scope``.
        scope_policy: Scope completion policy (``ScopeCompletionPolicy``).
        scope_timeout: Timeout in seconds for scope enable/verify.
    """

    frequency_hz: int | None = None
    mode: str | None = None
    filter_width: int | None = None
    vox: bool | None = None
    split: bool | None = None
    vfo: str | None = None
    data_mode: bool | None = None
    data_off_mod_input: int | None = None
    data1_mod_input: int | None = None
    squelch_level: int | None = None
    equalize_vfo: bool = False
    scope_enabled: bool | None = None
    scope_mode: int | None = None
    scope_span: int | None = None
    scope_output: bool = False
    scope_policy: ScopeCompletionPolicy | str = ScopeCompletionPolicy.FAST
    scope_timeout: float = 5.0


async def apply_profile(radio: Any, profile: OperatingProfile) -> dict[str, object]:
    """Apply a declarative profile to a radio and return a restore snapshot.

    Steps are applied in a safe order: VOX → VFO selection → split →
    frequency → mode → DATA mode → modulation inputs → VFO equalise →
    squelch → scope → final VFO re-select.

    Each step is silently skipped if:

    - The field is ``None`` in the profile (not specified by the caller).
    - The radio object lacks the required setter method.

    A ``DEBUG`` log message is emitted for every skipped capability.

    Args:
        radio: Any radio object — LAN-connected ``IcomRadio``, serial backend,
            or a test double.
        profile: Desired state to apply.

    Returns:
        A snapshot dict from ``radio.snapshot_state()`` suitable for passing
        to ``radio.restore_state()`` to undo all changes.
    """
    snapshot = await radio.snapshot_state()

    if profile.vox is not None:
        if hasattr(radio, "set_vox"):
            await radio.set_vox(profile.vox)
        else:
            logger.debug("apply_profile: radio has no set_vox, skipping")

    if profile.vfo is not None:
        if hasattr(radio, "set_vfo"):
            await radio.set_vfo(profile.vfo)
        else:
            logger.debug("apply_profile: radio has no set_vfo, skipping")

    if profile.split is not None:
        if hasattr(radio, "set_split_mode"):
            await radio.set_split_mode(profile.split)
        else:
            logger.debug("apply_profile: radio has no set_split_mode, skipping")

    if profile.frequency_hz is not None:
        if hasattr(radio, "set_freq"):
            await radio.set_freq(profile.frequency_hz)
        else:
            logger.debug("apply_profile: radio has no set_freq, skipping")

    if profile.mode is not None:
        if hasattr(radio, "set_mode"):
            if profile.filter_width is not None:
                await radio.set_mode(profile.mode, filter_width=profile.filter_width)
            else:
                await radio.set_mode(profile.mode)
        else:
            logger.debug("apply_profile: radio has no set_mode, skipping")

    if profile.data_mode is not None:
        if hasattr(radio, "set_data_mode"):
            await radio.set_data_mode(profile.data_mode)
        else:
            logger.debug("apply_profile: radio has no set_data_mode, skipping")

    if profile.data_off_mod_input is not None:
        if hasattr(radio, "set_data_off_mod_input"):
            await radio.set_data_off_mod_input(profile.data_off_mod_input)
        else:
            logger.debug("apply_profile: radio has no set_data_off_mod_input, skipping")

    if profile.data1_mod_input is not None:
        if hasattr(radio, "set_data1_mod_input"):
            await radio.set_data1_mod_input(profile.data1_mod_input)
        else:
            logger.debug("apply_profile: radio has no set_data1_mod_input, skipping")

    if profile.equalize_vfo:
        if hasattr(radio, "vfo_equalize"):
            await radio.vfo_equalize()
        else:
            logger.debug("apply_profile: radio has no vfo_equalize, skipping")

    if profile.squelch_level is not None:
        if hasattr(radio, "set_squelch"):
            await radio.set_squelch(profile.squelch_level)
        else:
            logger.debug("apply_profile: radio has no set_squelch, skipping")

    if profile.scope_enabled is not None:
        if profile.scope_enabled:
            if hasattr(radio, "enable_scope"):
                await radio.enable_scope(
                    output=profile.scope_output,
                    policy=profile.scope_policy,
                    timeout=profile.scope_timeout,
                )
            else:
                logger.debug("apply_profile: radio has no enable_scope, skipping")
            if profile.scope_mode is not None:
                if hasattr(radio, "set_scope_mode"):
                    await radio.set_scope_mode(profile.scope_mode)
                else:
                    logger.debug("apply_profile: radio has no set_scope_mode, skipping")
            if profile.scope_span is not None:
                if hasattr(radio, "set_scope_span"):
                    await radio.set_scope_span(profile.scope_span)
                else:
                    logger.debug("apply_profile: radio has no set_scope_span, skipping")
        else:
            if hasattr(radio, "disable_scope"):
                await radio.disable_scope()
            else:
                logger.debug("apply_profile: radio has no disable_scope, skipping")

    # Re-select VFO at the end to ensure consistent state after all operations.
    if profile.vfo is not None:
        if hasattr(radio, "set_vfo"):
            await radio.set_vfo(profile.vfo)

    return snapshot


#: Built-in operating presets for common modes.
PRESETS = SimpleNamespace(
    aprs_vhf=OperatingProfile(
        frequency_hz=145_500_000,
        mode="FM",
        data_mode=True,
        vox=False,
    ),
    ft8_20m=OperatingProfile(
        frequency_hz=14_074_000,
        mode="USB",
        data_mode=True,
        vox=False,
    ),
    cw_contest=OperatingProfile(
        vox=False,
        split=False,
    ),
    ssb_40m=OperatingProfile(
        frequency_hz=7_040_000,
        mode="LSB",
    ),
)
