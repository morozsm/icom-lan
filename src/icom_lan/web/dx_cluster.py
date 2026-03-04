"""DX cluster client: spot parsing, telnet client, spot buffer."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import re
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Callable

_log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Task 1: DXSpot dataclass + spot parser
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DXSpot:
    spotter: str
    freq: int  # Hz
    call: str
    comment: str = ""
    time_utc: str = ""
    timestamp: float = field(default_factory=time.monotonic)


# Matches the required "DX de SPOTTER: FREQ CALL" prefix.
_SPOT_RE = re.compile(r"^DX de\s+(\S+?):\s+(\d+(?:\.\d*)?)\s+(\S+)")
# Extracts trailing 4-digit UTC time (e.g. "1234Z") from the comment/rest field.
# Leading whitespace is optional so it also matches when the rest IS just the time.
_TIME_RE = re.compile(r"(?:\s+|^)(\d{4}Z)\s*$")


def parse_spot(line: str) -> DXSpot | None:
    """Parse a DX cluster spot line.  Returns None for non-spot lines."""
    line = line.strip()
    m = _SPOT_RE.match(line)
    if not m:
        return None
    spotter = m.group(1)
    freq = round(float(m.group(2)) * 1000)  # kHz → Hz
    call = m.group(3)

    rest = line[m.end():].strip()

    time_m = _TIME_RE.search(rest)
    if time_m:
        time_utc = time_m.group(1)
        comment = rest[: time_m.start()].strip()
    else:
        time_utc = ""
        comment = rest

    return DXSpot(
        spotter=spotter,
        freq=freq,
        call=call,
        comment=comment,
        time_utc=time_utc,
    )
