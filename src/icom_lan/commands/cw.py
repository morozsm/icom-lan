"""CW keying commands (send_cw, stop_cw, cw_sync_tune)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ._frame import (
    CONTROLLER_ADDR,
    _CMD_CTL_MEM,
    _CMD_SEND_CW,
    _build_from_map,
    build_civ_frame,
)

if TYPE_CHECKING:
    from ..command_map import CommandMap


def send_cw(
    text: str,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> list[bytes]:
    """Build CI-V frames to send CW text.

    CW text is sent in chunks of up to 30 characters per frame.
    Each character is sent as ASCII byte in the data field.

    Args:
        text: CW text to send (A-Z, 0-9, and common prosigns).
        to_addr: Radio CI-V address.
        from_addr: Controller CI-V address.

    Returns:
        List of CI-V frame bytes (one per chunk).
    """
    frames = []
    text = text.upper()
    for i in range(0, len(text), 30):
        chunk = text[i : i + 30]
        data = chunk.encode("ascii")
        if cmd_map is not None:
            frames.append(
                _build_from_map(
                    cmd_map, "send_cw", to_addr=to_addr, from_addr=from_addr, data=data
                )
            )
        else:
            frames.append(build_civ_frame(to_addr, from_addr, _CMD_SEND_CW, data=data))
    return frames


def stop_cw(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build CI-V frame to stop CW sending."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map, "stop_cw", to_addr=to_addr, from_addr=from_addr, data=b"\xff"
        )
    return build_civ_frame(to_addr, from_addr, _CMD_SEND_CW, data=b"\xff")


# ── SSB/CW Synchronous Tuning (Auto Tune) ──
# Menu command 1A 05 — address differs per model:
#   IC-7610: 0x00 0x61
#   IC-7300: 0x00 0x55
# Rig TOML defines the exact bytes via cmd_map.

_SUB_CTL_MEM = 0x05

def get_cw_sync_tune(
    to_addr: int, from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Read SSB/CW Synchronous Tuning status (0=OFF, 1=ON)."""
    if cmd_map is not None:
        return _build_from_map(cmd_map, "get_cw_sync_tune", to_addr=to_addr, from_addr=from_addr)
    # Fallback for IC-7610 default address
    return build_civ_frame(to_addr, from_addr, _CMD_CTL_MEM, sub=_SUB_CTL_MEM, data=bytes([0x00, 0x61]))


def set_cw_sync_tune(
    on: bool, to_addr: int, from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Set SSB/CW Synchronous Tuning ON/OFF."""
    value = bytes([0x01]) if on else bytes([0x00])
    if cmd_map is not None:
        return _build_from_map(cmd_map, "set_cw_sync_tune", to_addr=to_addr, from_addr=from_addr, data=value)
    return build_civ_frame(to_addr, from_addr, _CMD_CTL_MEM, sub=_SUB_CTL_MEM, data=bytes([0x00, 0x61]) + value)
