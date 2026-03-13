"""Serial port enumeration and candidate filtering for Icom radio discovery."""

from __future__ import annotations

import logging
from dataclasses import dataclass

__all__ = ["SerialPortCandidate", "enumerate_serial_ports"]

logger = logging.getLogger(__name__)

_VIRTUAL_KEYWORDS = ("debug", "wlan", "spi")
_BLUETOOTH_KEYWORDS = ("bluetooth",)


@dataclass
class SerialPortCandidate:
    """A USB serial port that may be connected to an Icom radio.

    Attributes:
        device: OS device path, e.g. ``/dev/ttyUSB0``.
        description: Human-readable description from the OS.
        hwid: Hardware ID string (USB VID:PID), or ``None`` if unavailable.
    """

    device: str
    description: str
    hwid: str | None


def enumerate_serial_ports() -> list[SerialPortCandidate]:
    """Enumerate candidate USB serial ports for Icom radios.

    Returns:
        List of :class:`SerialPortCandidate` objects for ports that pass the
        candidate filter (USB, non-Bluetooth, non-virtual).
    """
    from serial.tools import list_ports

    candidates = []
    for port in list_ports.comports():
        if _is_candidate(port):
            candidates.append(
                SerialPortCandidate(
                    device=port.device,
                    description=port.description,
                    hwid=port.hwid,
                )
            )
            logger.debug("Serial candidate: %s (%s)", port.device, port.description)
        else:
            logger.debug("Skipping port: %s (%s)", port.device, port.description)
    return candidates


def _is_candidate(port: object) -> bool:
    """Return True if *port* is a plausible Icom serial connection.

    Inclusion criteria:
    - Device path contains ``"usb"`` (case-insensitive)

    Exclusion criteria:
    - Device path contains ``"bluetooth"`` (case-insensitive)
    - Device path contains ``"debug"``, ``"wlan"``, or ``"spi"`` (virtual ports)

    Args:
        port: A ``serial.tools.list_ports_common.ListPortInfo`` object.

    Returns:
        ``True`` if the port should be offered as a candidate.
    """
    device: str = getattr(port, "device", "")
    device_lower = device.lower()

    for kw in _BLUETOOTH_KEYWORDS:
        if kw in device_lower:
            return False

    for kw in _VIRTUAL_KEYWORDS:
        if kw in device_lower:
            return False

    return "usb" in device_lower
