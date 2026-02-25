"""icom-lan CLI — command-line interface for Icom LAN control.

Usage:
    icom-lan status [--host HOST] [--user USER] [--pass PASS]
    icom-lan freq [VALUE] [--host HOST] [--user USER] [--pass PASS]
    icom-lan mode [VALUE] [--host HOST] [--user USER] [--pass PASS]
    icom-lan power [VALUE] [--host HOST] [--user USER] [--pass PASS]
    icom-lan meter [--host HOST] [--user USER] [--pass PASS]
    icom-lan att [VALUE] [--host HOST] [--user USER] [--pass PASS]
    icom-lan preamp [VALUE] [--host HOST] [--user USER] [--pass PASS]
    icom-lan ptt {on,off} [--host HOST] [--user USER] [--pass PASS]
    icom-lan discover
"""

import argparse
import asyncio
import os
import sys

from . import __version__
from .radio import IcomRadio
from .types import Mode


def _get_env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="icom-lan",
        description="Control Icom transceivers over LAN",
    )
    p.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show version and exit",
    )
    p.add_argument(
        "--host",
        default=_get_env("ICOM_HOST", "192.168.1.100"),
        help="Radio IP (default: $ICOM_HOST or 192.168.1.100)",
    )
    p.add_argument(
        "--port",
        type=int,
        default=int(_get_env("ICOM_PORT", "50001")),
        help="Control port (default: 50001)",
    )
    p.add_argument(
        "--user",
        default=_get_env("ICOM_USER", ""),
        help="Username (default: $ICOM_USER)",
    )
    p.add_argument(
        "--pass",
        dest="password",
        default=_get_env("ICOM_PASS", ""),
        help="Password (default: $ICOM_PASS)",
    )
    p.add_argument(
        "--timeout",
        type=float,
        default=5.0,
        help="Timeout in seconds (default: 5)",
    )
    sub = p.add_subparsers(dest="command", help="Command")

    def _add_json(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--json", action="store_true", help="Output as JSON")

    # status
    status_p = sub.add_parser("status", help="Show radio status (freq, mode, meters)")
    _add_json(status_p)

    # freq
    freq_p = sub.add_parser("freq", help="Get or set frequency")
    _add_json(freq_p)
    freq_p.add_argument(
        "value",
        nargs="?",
        type=str,
        help="Frequency in Hz, kHz (with 'k'), or MHz (with 'm')",
    )

    # mode
    mode_p = sub.add_parser("mode", help="Get or set mode")
    _add_json(mode_p)
    mode_p.add_argument(
        "value",
        nargs="?",
        type=str,
        choices=[m.name for m in Mode],
        help="Mode name (USB, LSB, CW, AM, FM, etc.)",
    )

    # power
    power_p = sub.add_parser("power", help="Get or set RF power level")
    _add_json(power_p)
    power_p.add_argument(
        "value",
        nargs="?",
        type=int,
        help="Power level (0-255)",
    )

    # meter
    meter_p = sub.add_parser("meter", help="Read all meters")
    _add_json(meter_p)

    # ptt
    ptt_p = sub.add_parser("ptt", help="PTT control")
    ptt_p.add_argument(
        "state",
        choices=["on", "off"],
        help="PTT state",
    )

    # cw
    cw_p = sub.add_parser("cw", help="Send CW text")
    cw_p.add_argument("text", type=str, help="CW text to send")

    # power-on / power-off
    sub.add_parser("power-on", help="Power on the radio")
    sub.add_parser("power-off", help="Power off the radio")

    # att
    att_p = sub.add_parser("att", help="Get or set attenuator level")
    _add_json(att_p)
    att_p.add_argument(
        "value",
        nargs="?",
        type=str,
        help="Attenuation in dB (0, 3, 6, ..., 45) or 'on'/'off'",
    )

    # preamp
    preamp_p = sub.add_parser("preamp", help="Get or set preamp level")
    _add_json(preamp_p)
    preamp_p.add_argument(
        "value",
        nargs="?",
        type=str,
        help="Preamp level: 0 (off), 1 (PRE1), 2 (PRE2), or 'off'",
    )

    # discover
    sub.add_parser("discover", help="Discover radios on the network")

    return p


def _parse_frequency(value: str) -> int:
    """Parse frequency from string with optional k/m suffix."""
    value = value.strip().lower()
    if value.endswith("m") or value.endswith("mhz"):
        num = value.rstrip("mhz").strip()
        return int(float(num) * 1_000_000)
    elif value.endswith("k") or value.endswith("khz"):
        num = value.rstrip("khz").strip()
        return int(float(num) * 1_000)
    else:
        return int(float(value))


async def _run(args: argparse.Namespace) -> int:
    radio = IcomRadio(
        args.host,
        port=args.port,
        username=args.user,
        password=args.password,
        timeout=args.timeout,
    )

    try:
        async with radio:
            if args.command == "status":
                return await _cmd_status(radio, args)
            elif args.command == "freq":
                return await _cmd_freq(radio, args)
            elif args.command == "mode":
                return await _cmd_mode(radio, args)
            elif args.command == "power":
                return await _cmd_power(radio, args)
            elif args.command == "meter":
                return await _cmd_meter(radio, args)
            elif args.command == "ptt":
                return await _cmd_ptt(radio, args)
            elif args.command == "cw":
                return await _cmd_cw(radio, args)
            elif args.command == "att":
                return await _cmd_att(radio, args)
            elif args.command == "preamp":
                return await _cmd_preamp(radio, args)
            elif args.command == "power-on":
                await radio.power_control(True)
                print("Power ON")
                return 0
            elif args.command == "power-off":
                await radio.power_control(False)
                print("Power OFF")
                return 0
            else:
                return await _cmd_status(radio, args)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


async def _cmd_status(radio: IcomRadio, args: argparse.Namespace) -> int:
    freq = await radio.get_frequency()
    mode = await radio.get_mode()
    s_meter = await radio.get_s_meter()
    power = await radio.get_power()

    if args.json:
        import json

        print(
            json.dumps(
                {
                    "frequency_hz": freq,
                    "frequency_mhz": round(freq / 1e6, 6),
                    "mode": mode.name,
                    "s_meter": s_meter,
                    "power": power,
                }
            )
        )
    else:
        print(f"Frequency: {freq:>12,} Hz  ({freq / 1e6:.6f} MHz)")
        print(f"Mode:      {mode.name}")
        print(f"S-meter:   {s_meter}")
        print(f"Power:     {power}")
    return 0


async def _cmd_freq(radio: IcomRadio, args: argparse.Namespace) -> int:
    if args.value is not None:
        freq_hz = _parse_frequency(args.value)
        await radio.set_frequency(freq_hz)
        print(f"Set: {freq_hz:,} Hz ({freq_hz / 1e6:.6f} MHz)")
    else:
        freq = await radio.get_frequency()
        if args.json:
            import json

            print(
                json.dumps(
                    {"frequency_hz": freq, "frequency_mhz": round(freq / 1e6, 6)}
                )
            )
        else:
            print(f"{freq:,} Hz ({freq / 1e6:.6f} MHz)")
    return 0


async def _cmd_mode(radio: IcomRadio, args: argparse.Namespace) -> int:
    if args.value is not None:
        await radio.set_mode(args.value)
        print(f"Set: {args.value}")
    else:
        mode = await radio.get_mode()
        if args.json:
            import json

            print(json.dumps({"mode": mode.name}))
        else:
            print(mode.name)
    return 0


async def _cmd_power(radio: IcomRadio, args: argparse.Namespace) -> int:
    if args.value is not None:
        await radio.set_power(args.value)
        print(f"Set: {args.value}")
    else:
        power = await radio.get_power()
        if args.json:
            import json

            print(json.dumps({"power": power}))
        else:
            print(power)
    return 0


async def _cmd_meter(radio: IcomRadio, args: argparse.Namespace) -> int:
    from .exceptions import TimeoutError as IcomTimeout

    results: dict[str, int | str] = {}
    for name, getter in [
        ("s_meter", radio.get_s_meter),
        ("power", radio.get_power),
        ("swr", radio.get_swr),
        ("alc", radio.get_alc),
    ]:
        try:
            results[name] = await getter()
        except IcomTimeout:
            results[name] = "n/a"  # Not available (e.g. SWR/ALC in RX mode)

    if args.json:
        import json

        print(json.dumps(results))
    else:
        for name, val in results.items():
            label = name.replace("_", "-").upper().ljust(8)
            print(f"{label} {val}")
    return 0


async def _cmd_ptt(radio: IcomRadio, args: argparse.Namespace) -> int:
    on = args.state == "on"
    await radio.set_ptt(on)
    print(f"PTT {'ON' if on else 'OFF'}")
    return 0


async def _cmd_cw(radio: IcomRadio, args: argparse.Namespace) -> int:
    await radio.send_cw_text(args.text)
    print(f"CW: {args.text}")
    return 0


async def _cmd_att(radio: IcomRadio, args: argparse.Namespace) -> int:
    if args.value is not None:
        val = args.value.strip().lower()
        if val == "on":
            await radio.set_attenuator(True)
            print("Attenuator: ON (18 dB)")
        elif val == "off":
            await radio.set_attenuator_level(0)
            print("Attenuator: OFF (0 dB)")
        else:
            db = int(val)
            await radio.set_attenuator_level(db)
            print(f"Attenuator: {db} dB")
    else:
        db = await radio.get_attenuator_level()
        if args.json:
            import json

            print(json.dumps({"attenuator_db": db, "attenuator_on": db > 0}))
        else:
            if db == 0:
                print("Attenuator: OFF (0 dB)")
            else:
                print(f"Attenuator: {db} dB")
    return 0


_PREAMP_NAMES = {0: "OFF", 1: "PRE1", 2: "PRE2"}


async def _cmd_preamp(radio: IcomRadio, args: argparse.Namespace) -> int:
    if args.value is not None:
        val = args.value.strip().lower()
        if val == "off":
            level = 0
        else:
            level = int(val)
        await radio.set_preamp(level)
        print(f"Preamp: {_PREAMP_NAMES.get(level, str(level))}")
    else:
        level = await radio.get_preamp()
        if args.json:
            import json

            print(
                json.dumps(
                    {
                        "preamp_level": level,
                        "preamp_name": _PREAMP_NAMES.get(level, str(level)),
                    }
                )
            )
        else:
            print(f"Preamp: {_PREAMP_NAMES.get(level, str(level))}")
    return 0


async def _cmd_discover(_radio: IcomRadio, _args: argparse.Namespace) -> int:
    """Discover Icom radios on the local network via broadcast."""
    import socket
    import struct

    print("Scanning for Icom radios (3 seconds)...")

    # Build "Are You There" packet with sender_id=0
    pkt = bytearray(0x10)
    struct.pack_into("<I", pkt, 0, 0x10)
    struct.pack_into("<H", pkt, 4, 0x03)  # ARE_YOU_THERE

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(0.5)

    # Broadcast on common Icom ports
    for port in [50001]:
        sock.sendto(bytes(pkt), ("255.255.255.255", port))

    found: dict[str, int] = {}
    deadline = asyncio.get_event_loop().time() + 3.0
    while asyncio.get_event_loop().time() < deadline:
        try:
            data, addr = sock.recvfrom(256)
            if len(data) >= 0x10:
                ptype = struct.unpack_from("<H", data, 4)[0]
                if ptype == 0x04:  # I_AM_HERE
                    remote_id = struct.unpack_from("<I", data, 8)[0]
                    found[addr[0]] = remote_id
                    print(f"  Found: {addr[0]}:{addr[1]}  id=0x{remote_id:08X}")
        except socket.timeout:
            continue

    sock.close()

    if not found:
        print("No radios found.")
    else:
        print(f"\n{len(found)} radio(s) found.")
    return 0


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "discover":
        sys.exit(asyncio.run(_cmd_discover(None, args)))  # type: ignore[arg-type]
    elif args.command is None:
        parser.print_help()
        sys.exit(0)
    else:
        sys.exit(asyncio.run(_run(args)))


if __name__ == "__main__":
    main()
