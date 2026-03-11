from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..radio_protocol import AudioCapable, DualReceiverCapable, ScopeCapable

if TYPE_CHECKING:
    from ..radio_protocol import Radio

__all__ = ["runtime_capabilities", "radio_ready"]


def runtime_capabilities(radio: "Radio | None") -> set[str]:
    """Return conservative runtime capabilities for the active radio.

    Semantics:
    - If ``radio`` is ``None`` → empty set.
    - If ``radio.capabilities`` is a set (including the empty set), use it as the
      starting point and *do not* fall back to Protocol checks, but drop tags
      that contradict the runtime Protocols (e.g. tag ``"scope"`` without
      :class:`ScopeCapable`).
    - If ``radio.capabilities`` is missing or not a set, derive tags purely from
      the capability Protocols implemented by the instance.
    """
    if radio is None:
        return set()

    raw_caps = getattr(radio, "capabilities", None)
    if isinstance(raw_caps, set):
        caps = set(raw_caps)
        if "scope" in caps and not isinstance(radio, ScopeCapable):
            caps.discard("scope")
        if "audio" in caps and not isinstance(radio, AudioCapable):
            caps.discard("audio")
        if "dual_rx" in caps and not isinstance(radio, DualReceiverCapable):
            caps.discard("dual_rx")
        return caps

    caps: set[str] = set()
    if isinstance(radio, ScopeCapable):
        caps.add("scope")
    if isinstance(radio, AudioCapable):
        caps.add("audio")
    if isinstance(radio, DualReceiverCapable):
        caps.add("dual_rx")
    return caps


def radio_ready(radio: "Radio | None") -> bool:
    """Return backend radio readiness (CI-V healthy), with fallback.

    Rules:
    - ``None`` → ``False``.
    - If ``radio.radio_ready`` is a bool, use it.
    - Otherwise fall back to ``bool(radio.connected)`` when the attribute is a
      proper bool; non-bool truthy values do not count as connected.
    """
    if radio is None:
        return False
    ready: Any = getattr(radio, "radio_ready", None)
    if isinstance(ready, bool):
        return ready
    connected: Any = getattr(radio, "connected", False)
    return connected if isinstance(connected, bool) else False

