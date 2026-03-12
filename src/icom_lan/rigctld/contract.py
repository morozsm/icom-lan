"""Shared contracts between rigctld modules.

This file defines the data types and constants shared across
server.py, protocol.py, handler.py, and commands.py.
All modules import from here — never from each other.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum


# ---------------------------------------------------------------------------
# Hamlib error codes (from hamlib/rig.h)
# ---------------------------------------------------------------------------


class HamlibError(IntEnum):
    """Hamlib error codes returned as ``RPRT <code>``."""

    OK = 0
    EINVAL = -1  # invalid parameter
    ECONF = -2  # invalid configuration
    ENOMEM = -3  # memory shortage
    ENIMPL = -4  # function not implemented
    ETIMEOUT = -5  # communication timed out
    EIO = -6  # I/O error
    EINTERNAL = -7  # internal Hamlib error
    EPROTO = -8  # protocol error
    ERJCTED = -9  # command rejected by the rig
    ETRUNC = -10  # arg truncated
    ENAVAIL = -11  # function not available
    ENTARGET = -12  # VFO not targetable
    BUSERR = -13  # bus error (CI-V collision)
    BUSBUSY = -14  # bus busy (CW keying)
    EARG = -15  # invalid arg
    EVFO = -16  # invalid VFO
    EDOM = -17  # domain error
    EDEPRECATED = -18  # deprecated function
    ESECURITY = -19  # security error
    EPOWER = -20  # rig not powered on
    EEND = -21  # not end of list
    EACCESS = -22  # permission denied (used for read-only mode)


# ---------------------------------------------------------------------------
# Hamlib mode strings ↔ CI-V mode IDs
# ---------------------------------------------------------------------------

# rigctld uses these mode strings; map to icom-lan Mode enum values.
HAMLIB_MODE_MAP: dict[str, int] = {
    "USB": 0x01,
    "LSB": 0x00,
    "CW": 0x03,
    "CWR": 0x07,
    "RTTY": 0x04,
    "RTTYR": 0x08,
    "AM": 0x02,
    "FM": 0x05,
    "WFM": 0x06,
    "PKTUSB": 0x01,  # mapped to USB (DATA mode handled separately)
    "PKTLSB": 0x00,  # mapped to LSB
    "PKTRTTY": 0x04,  # mapped to RTTY
}

# Reverse: CI-V mode int → hamlib string
CIV_TO_HAMLIB_MODE: dict[int, str] = {
    0x00: "LSB",
    0x01: "USB",
    0x02: "AM",
    0x03: "CW",
    0x04: "RTTY",
    0x05: "FM",
    0x06: "WFM",
    0x07: "CWR",
    0x08: "RTTYR",
}


# ---------------------------------------------------------------------------
# Parsed command / response dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RigctldCommand:
    """A parsed rigctld command from the client.

    Attributes:
        short_cmd: Single-char command (e.g. 'f', 'F', 'm', 'q').
        long_cmd: Long-form name (e.g. 'get_freq', 'set_freq').
        args: Tuple of string arguments.
        is_set: True if this is a write/set command.
    """

    short_cmd: str
    long_cmd: str
    args: tuple[str, ...] = ()
    is_set: bool = False


@dataclass(slots=True)
class RigctldResponse:
    """A response to send back to the client.

    Attributes:
        values: List of response lines (for get commands).
        error: Hamlib error code (0 = success).
        cmd_echo: Original command string (for extended protocol).
    """

    values: list[str] = field(default_factory=list)
    error: int = 0
    cmd_echo: str = ""

    @property
    def ok(self) -> bool:
        return self.error == 0


# ---------------------------------------------------------------------------
# Command table — maps short/long names and classifies set vs get
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CommandDef:
    """Definition of a rigctld command."""

    short: str
    long: str
    is_set: bool
    min_args: int = 0
    max_args: int = 0
    description: str = ""


# MVP command set — sufficient for WSJT-X, JS8Call, fldigi
COMMAND_TABLE: dict[str, CommandDef] = {}


def _register(*defs: CommandDef) -> None:
    for d in defs:
        COMMAND_TABLE[d.short] = d
        COMMAND_TABLE[d.long] = d


_register(
    # Get commands
    CommandDef("f", "get_freq", is_set=False, description="Get frequency in Hz"),
    CommandDef("m", "get_mode", is_set=False, description="Get mode and passband"),
    CommandDef("t", "get_ptt", is_set=False, description="Get PTT status"),
    CommandDef("v", "get_vfo", is_set=False, description="Get current VFO"),
    CommandDef("j", "get_rit", is_set=False, description="Get RIT offset"),
    CommandDef(
        "l",
        "get_level",
        is_set=False,
        min_args=1,
        max_args=1,
        description="Get level (STRENGTH, RFPOWER, SWR, etc.)",
    ),
    CommandDef("s", "get_split_vfo", is_set=False, description="Get split VFO status"),
    # Set commands
    CommandDef(
        "F",
        "set_freq",
        is_set=True,
        min_args=1,
        max_args=1,
        description="Set frequency in Hz",
    ),
    CommandDef(
        "M",
        "set_mode",
        is_set=True,
        min_args=1,
        max_args=2,
        description="Set mode and optional passband",
    ),
    CommandDef(
        "T",
        "set_ptt",
        is_set=True,
        min_args=1,
        max_args=1,
        description="Set PTT on/off",
    ),
    CommandDef(
        "V", "set_vfo", is_set=True, min_args=1, max_args=1, description="Set VFO"
    ),
    CommandDef(
        "S",
        "set_split_vfo",
        is_set=True,
        min_args=2,
        max_args=2,
        description="Set split VFO",
    ),
    # Control / info commands (not set, not get — special)
    CommandDef("q", "quit", is_set=False, description="Close connection"),
    CommandDef(
        "\\dump_state", "dump_state", is_set=False, description="Dump rig capabilities"
    ),
    CommandDef(
        "\\get_info", "get_info", is_set=False, description="Get rig info string"
    ),
    CommandDef(
        "\\chk_vfo",
        "chk_vfo",
        is_set=False,
        description="Check if VFO mode is enabled (always 0)",
    ),
    CommandDef(
        "\\get_powerstat", "get_powerstat", is_set=False, description="Get power status"
    ),
    CommandDef("1", "dump_caps", is_set=False, description="Dump capabilities (alias)"),
    # Power conversion (WSJT-X uses these)
    CommandDef(
        "\\power2mW",
        "power2mW",
        is_set=False,
        min_args=1,
        max_args=3,
        description="Convert normalized power to milliwatts",
    ),
    CommandDef(
        "\\mW2power",
        "mW2power",
        is_set=False,
        min_args=1,
        max_args=3,
        description="Convert milliwatts to normalized power",
    ),
    CommandDef(
        "\\get_lock_mode",
        "get_lock_mode",
        is_set=False,
        description="Get lock mode (always 0)",
    ),
)


# ---------------------------------------------------------------------------
# Per-client session state
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class ClientSession:
    """Per-client session state."""

    client_id: int = 0
    peername: str = ""
    extended_mode: bool = False
    vfo_mode: bool = False  # Whether VFO arg is required


# ---------------------------------------------------------------------------
# Server configuration
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class RigctldConfig:
    """Configuration for the rigctld server."""

    host: str = "0.0.0.0"
    port: int = 4532
    read_only: bool = False
    max_clients: int = 10
    client_timeout: float = 300.0  # seconds before idle disconnect
    command_timeout: float = 2.0  # seconds per CI-V command
    cache_ttl: float = 0.2  # seconds for frequency/mode cache
    max_line_length: int = 1024  # max bytes per command line (OOM guard)
    poll_interval: float = 0.2  # seconds between autonomous poll cycles
    wsjtx_compat: bool = False  # pre-warm DATA mode for WSJT-X-style CAT/PTT flow
    command_rate_limit: float | None = None  # max cmds/sec per client, None=unlimited
