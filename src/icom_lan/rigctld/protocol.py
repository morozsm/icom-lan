"""Rigctld wire protocol parser and formatter.

Stateless module — no I/O, no radio access. Pure functions for:
- Parsing line-based rigctld commands
- Formatting responses (normal and extended protocol)
- Error code formatting

Reference: hamlib rigctld(1) man page, rigctl.c source.

Line format:
    <cmd>[<SP><arg1>[<SP><arg2>...]]<LF>

Response format (normal):
    GET: <value1><LF>[<value2><LF>...]
    SET: RPRT <code><LF>

Response format (extended):
    <cmd_echo>:<LF>
    [<value><LF>...]
    RPRT <code><LF>
"""

from __future__ import annotations

import logging

from .contract import (  # noqa: TID251
    COMMAND_TABLE,
    ClientSession,
    RigctldCommand,
    RigctldResponse,
)

__all__ = ["parse_line", "format_response", "format_error"]

logger = logging.getLogger(__name__)


def parse_line(line: bytes) -> RigctldCommand:
    """Parse a rigctld command line into a RigctldCommand.

    Args:
        line: Raw bytes, already stripped of the trailing newline.

    Returns:
        Parsed RigctldCommand.

    Raises:
        ValueError: Unknown command, or wrong number of arguments.
    """
    text = line.rstrip(b"\r").decode("ascii", errors="replace").strip()

    if not text:
        raise ValueError("empty line")

    parts = text.split()
    token = parts[0]
    args: tuple[str, ...] = tuple(parts[1:])

    # Long-form commands arrive with a leading backslash: \get_freq
    # Strip it to get the bare long name used as the lookup key.
    if token.startswith("\\"):
        lookup_key = token[1:]
    else:
        lookup_key = token

    defn = COMMAND_TABLE.get(lookup_key)
    if defn is None:
        raise ValueError(f"Unknown command: {token!r}")

    n = len(args)
    if n < defn.min_args:
        raise ValueError(
            f"Command {token!r} requires at least {defn.min_args} arg(s), got {n}"
        )
    if n > defn.max_args:
        raise ValueError(
            f"Command {token!r} accepts at most {defn.max_args} arg(s), got {n}"
        )

    logger.debug("parsed command %r args=%r", token, args)

    return RigctldCommand(
        short_cmd=defn.short,
        long_cmd=defn.long,
        args=args,
        is_set=defn.is_set,
    )


def format_response(
    cmd: RigctldCommand,
    resp: RigctldResponse,
    session: ClientSession,
) -> bytes:
    """Format a rigctld response for wire transmission.

    Args:
        cmd: The command that was executed.
        resp: The response data.
        session: Current client session state.

    Returns:
        Formatted bytes to send to the client.
    """
    if session.extended_mode:
        return _format_extended(cmd, resp)
    return _format_normal(cmd, resp)


def _format_normal(cmd: RigctldCommand, resp: RigctldResponse) -> bytes:
    if resp.error != 0:
        return format_error(resp.error)
    if cmd.is_set:
        return b"RPRT 0\n"
    # GET success: one value per line.
    if resp.values:
        return ("\n".join(resp.values) + "\n").encode("ascii")
    return b""


def _format_extended(cmd: RigctldCommand, resp: RigctldResponse) -> bytes:
    echo = resp.cmd_echo or cmd.long_cmd
    lines: list[str] = [f"{echo}:"]
    lines.extend(resp.values)
    lines.append(f"RPRT {resp.error}")
    return ("\n".join(lines) + "\n").encode("ascii")


def format_error(code: int) -> bytes:
    """Format a bare Hamlib error response.

    Args:
        code: Hamlib error code (e.g. ``HamlibError.EINVAL`` = -1).

    Returns:
        Wire bytes, e.g. ``b'RPRT -1\\n'``.
    """
    return f"RPRT {code}\n".encode("ascii")
