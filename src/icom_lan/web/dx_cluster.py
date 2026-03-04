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


# ---------------------------------------------------------------------------
# Task 2: DXClusterClient
# ---------------------------------------------------------------------------


class DXClusterClient:
    """Asyncio telnet client for DX cluster servers.

    Connects, sends callsign login, reads spot lines and calls ``on_spot``
    for every successfully parsed DXSpot.  Auto-reconnects with exponential
    backoff (2**attempt seconds, capped at 60 s) on connection failure.
    """

    def __init__(
        self,
        host: str,
        port: int,
        callsign: str,
        on_spot: Callable[[DXSpot], None],
    ) -> None:
        self._host = host
        self._port = port
        self._callsign = callsign
        self._on_spot = on_spot
        self._running = False
        self._writer: asyncio.StreamWriter | None = None

    async def start(self) -> None:
        """Connect and read spots in a loop.  Auto-reconnects.  Runs forever
        until :meth:`stop` is called or the task is cancelled."""
        self._running = True
        attempt = 0
        while self._running:
            try:
                reader, writer = await asyncio.open_connection(self._host, self._port)
                self._writer = writer
                try:
                    writer.write(f"{self._callsign}\r\n".encode())
                    await writer.drain()
                    attempt = 0
                    async for raw in reader:
                        if not self._running:
                            break
                        line = raw.decode("ascii", errors="replace").rstrip("\r\n")
                        spot = parse_spot(line)
                        if spot is not None:
                            self._on_spot(spot)
                finally:
                    self._writer = None
                    if not writer.is_closing():
                        writer.close()
                    with contextlib.suppress(Exception):
                        await writer.wait_closed()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                if not self._running:
                    break
                wait = min(2 ** attempt, 60)
                attempt += 1
                _log.warning("DX cluster disconnected (%s), retry in %ds", exc, wait)
                await asyncio.sleep(wait)

    async def stop(self) -> None:
        """Signal the loop to stop and close the active connection."""
        self._running = False
        if self._writer is not None and not self._writer.is_closing():
            self._writer.close()
