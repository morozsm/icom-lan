"""icom-lan CLI — command-line interface for Icom LAN control.

Usage:
    icom-lan status [--host HOST] [--user USER] [--pass PASS]
    icom-lan freq [VALUE] [--host HOST] [--user USER] [--pass PASS]
    icom-lan mode [VALUE] [--host HOST] [--user USER] [--pass PASS]
    icom-lan power [VALUE] [--host HOST] [--user USER] [--pass PASS]
    icom-lan meter [--host HOST] [--user USER] [--pass PASS]
    icom-lan audio caps [--json] [--stats]
    icom-lan audio rx --out rx.wav [--seconds 10]
    icom-lan audio tx --in tx.wav
    icom-lan audio loopback [--seconds 10]
    icom-lan att [VALUE] [--host HOST] [--user USER] [--pass PASS]
    icom-lan preamp [VALUE] [--host HOST] [--user USER] [--pass PASS]
    icom-lan ptt {on,off} [--host HOST] [--user USER] [--pass PASS]
    icom-lan discover
"""

import argparse
import asyncio
import json
import logging
import os
import signal
import sys
from pathlib import Path
import time
import wave
from typing import Any

logger = logging.getLogger(__name__)

from . import __version__
from .audio import AudioStats
from .backends.config import LanBackendConfig, SerialBackendConfig
from .backends.factory import create_radio
from .radio import IcomRadio
from .types import Mode

_AUDIO_FRAME_MS = 20
_PCM_SAMPLE_WIDTH_BYTES = 2


def _get_env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


class _DeprecatedPortAction(argparse.Action):
    """Deprecated --port alias — prints a warning and stores to control_port."""

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: Any,
        option_string: str | None = None,
    ) -> None:
        print(
            "Warning: --port is deprecated, use --control-port instead",
            file=sys.stderr,
        )
        setattr(namespace, self.dest, values)


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
        "--control-port",
        type=int,
        default=int(_get_env("ICOM_PORT", "50001")),
        dest="control_port",
        help="Radio control port (default: $ICOM_PORT or 50001)",
    )
    p.add_argument(
        "--port",
        type=int,
        dest="control_port",
        default=argparse.SUPPRESS,
        action=_DeprecatedPortAction,
        help="Deprecated: use --control-port instead",
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
    p.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON when supported by the selected command",
    )
    p.add_argument(
        "--backend",
        choices=["lan", "serial"],
        default="lan",
        help="Backend type: lan (default) or serial (USB CI-V + audio)",
    )
    p.add_argument(
        "--serial-port",
        dest="serial_port",
        default=_get_env("ICOM_SERIAL_DEVICE", ""),
        metavar="PATH",
        help="Serial device path for --backend serial (default: $ICOM_SERIAL_DEVICE)",
    )
    p.add_argument(
        "--serial-baud",
        dest="serial_baud",
        type=int,
        default=int(_get_env("ICOM_SERIAL_BAUDRATE", "115200")),
        metavar="BAUD",
        help="Serial baud rate for --backend serial (default: $ICOM_SERIAL_BAUDRATE or 115200)",
    )
    p.add_argument(
        "--serial-ptt-mode",
        dest="serial_ptt_mode",
        choices=["civ"],
        default=_get_env("ICOM_SERIAL_PTT_MODE", "civ").lower(),
        metavar="MODE",
        help="Serial PTT mode for --backend serial (currently supported: civ)",
    )
    p.add_argument(
        "--rx-device",
        dest="rx_device",
        default=_get_env("ICOM_USB_RX_DEVICE") or None,
        metavar="NAME",
        help="USB audio RX device name for --backend serial (default: $ICOM_USB_RX_DEVICE or auto)",
    )
    p.add_argument(
        "--tx-device",
        dest="tx_device",
        default=_get_env("ICOM_USB_TX_DEVICE") or None,
        metavar="NAME",
        help="USB audio TX device name for --backend serial (default: $ICOM_USB_TX_DEVICE or auto)",
    )
    p.add_argument(
        "--list-audio-devices",
        dest="list_audio_devices",
        action="store_true",
        help="List available USB audio devices and exit (requires icom-lan[bridge])",
    )
    sub = p.add_subparsers(dest="command", help="Command")

    def _add_json(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--json", action="store_true", help="Output as JSON")

    def _add_stats(sp: argparse.ArgumentParser) -> None:
        sp.add_argument(
            "--stats",
            action="store_true",
            help="Probe runtime audio stream stats (1 second RX sample)",
        )

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

    # audio
    audio_p = sub.add_parser("audio", help="Audio helper commands")
    audio_sub = audio_p.add_subparsers(dest="audio_command", help="Audio command")
    audio_sub.required = True
    audio_caps_p = audio_sub.add_parser(
        "caps",
        help="Show icom-lan audio capabilities and defaults",
    )
    _add_json(audio_caps_p)
    _add_stats(audio_caps_p)

    audio_caps = IcomRadio.audio_capabilities()

    def _add_audio_common_flags(sp: argparse.ArgumentParser) -> None:
        sp.add_argument(
            "--sample-rate",
            type=int,
            default=audio_caps.default_sample_rate_hz,
            help=(
                "PCM sample rate in Hz "
                f"(default: {audio_caps.default_sample_rate_hz})"
            ),
        )
        sp.add_argument(
            "--channels",
            type=int,
            default=audio_caps.default_channels,
            help=f"PCM channels (default: {audio_caps.default_channels})",
        )
        sp.add_argument("--json", action="store_true", help="Output as JSON")
        sp.add_argument(
            "--stats",
            action="store_true",
            help="Print transfer statistics (ignored when --json is set)",
        )

    audio_rx_p = audio_sub.add_parser(
        "rx",
        help="Capture RX audio to a WAV file",
        description=(
            "Capture PCM audio from the radio and write a 16-bit PCM WAV file.\n"
            "Example: icom-lan audio rx --out rx.wav --seconds 10"
        ),
    )
    _add_audio_common_flags(audio_rx_p)
    audio_rx_p.add_argument(
        "--out",
        dest="output_file",
        required=True,
        help="Output WAV file path",
    )
    audio_rx_p.add_argument(
        "--seconds",
        type=float,
        default=10.0,
        help="Capture duration in seconds (default: 10)",
    )

    audio_tx_p = audio_sub.add_parser(
        "tx",
        help="Transmit audio from a WAV file",
        description=(
            "Read a 16-bit PCM WAV file and transmit it over LAN audio.\n"
            "Example: icom-lan audio tx --in tx.wav"
        ),
    )
    _add_audio_common_flags(audio_tx_p)
    audio_tx_p.add_argument(
        "--in",
        dest="input_file",
        required=True,
        help="Input WAV file path",
    )

    audio_loopback_p = audio_sub.add_parser(
        "loopback",
        help="RX->TX PCM loopback for quick audio path checks",
        description=(
            "Receive PCM audio and immediately feed it back to TX.\n"
            "Example: icom-lan audio loopback --seconds 10"
        ),
    )
    _add_audio_common_flags(audio_loopback_p)
    audio_loopback_p.add_argument(
        "--seconds",
        type=float,
        default=10.0,
        help="Loopback duration in seconds (default: 10)",
    )

    # bridge
    audio_bridge_p = audio_sub.add_parser(
        "bridge",
        help="Bridge radio audio to a virtual audio device (e.g. BlackHole)",
        description=(
            "Bidirectional PCM audio bridge between the radio and a system\n"
            "audio device. Allows WSJT-X, fldigi, JS8Call etc. to use the\n"
            "radio by selecting the virtual device as their sound card.\n\n"
            "Requires: pip install icom-lan[bridge]\n"
            "Virtual device: brew install blackhole-2ch\n\n"
            "Example: icom-lan audio bridge --device 'BlackHole 2ch'"
        ),
    )
    audio_bridge_p.add_argument(
        "--device",
        type=str,
        default=None,
        help="Audio device name (default: auto-detect BlackHole/Loopback)",
    )
    audio_bridge_p.add_argument(
        "--rx-only",
        action="store_true",
        help="RX only (don't bridge TX from device to radio)",
    )
    audio_bridge_p.add_argument(
        "--list-devices",
        action="store_true",
        help="List available audio devices and exit",
    )

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

    # serve
    serve_p = sub.add_parser("serve", help="Start rigctld-compatible TCP server")
    serve_p.add_argument(
        "--host",
        dest="serve_host",
        default="0.0.0.0",
        help="Server listen address (default: 0.0.0.0)",
    )
    serve_p.add_argument(
        "--port",
        dest="serve_port",
        type=int,
        default=4532,
        help="Server TCP port (default: 4532)",
    )
    serve_p.add_argument(
        "--read-only",
        action="store_true",
        default=False,
        help="Disallow set commands (read-only mode)",
    )
    serve_p.add_argument(
        "--max-clients",
        dest="max_clients",
        type=int,
        default=10,
        help="Maximum concurrent clients (default: 10)",
    )
    serve_p.add_argument(
        "--cache-ttl",
        dest="cache_ttl",
        type=float,
        default=0.2,
        help="Cache TTL in seconds (default: 0.2)",
    )
    serve_p.add_argument(
        "--wsjtx-compat",
        action="store_true",
        default=False,
        help="Enable WSJT-X compatibility pre-warm (auto-enable DATA mode on first client)",
    )
    serve_p.add_argument(
        "--log-level",
        dest="log_level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level for the rigctld server (default: INFO)",
    )
    serve_p.add_argument(
        "--audit-log",
        dest="audit_log",
        default=None,
        metavar="PATH",
        help="Path to write JSON audit log (one line per command; default: disabled)",
    )
    serve_p.add_argument(
        "--rate-limit",
        dest="rate_limit",
        type=float,
        default=None,
        metavar="N",
        help="Max commands per second per client (default: unlimited)",
    )

    # web
    web_p = sub.add_parser("web", help="Start built-in HTTP + WebSocket web UI server")
    web_p.add_argument(
        "--host",
        dest="web_host",
        default="0.0.0.0",
        help="Server listen address (default: 0.0.0.0)",
    )
    web_p.add_argument(
        "--port",
        dest="web_port",
        type=int,
        default=8080,
        help="Server HTTP/WS port (default: 8080)",
    )
    web_p.add_argument(
        "--static-dir",
        dest="web_static_dir",
        default=None,
        metavar="PATH",
        help="Directory to serve static files from (default: built-in)",
    )
    web_p.add_argument(
        "--bridge",
        dest="web_bridge",
        default=None,
        nargs="?",
        const="auto",
        metavar="DEVICE",
        help="Start audio bridge to virtual device (e.g. 'BlackHole 2ch', or omit for auto-detect)",
    )
    web_p.add_argument(
        "--bridge-tx-device",
        dest="web_bridge_tx_device",
        default=None,
        metavar="DEVICE",
        help="Separate TX device for bridge (e.g. 'BlackHole 16ch'). Required for bidirectional audio.",
    )
    web_p.add_argument(
        "--bridge-rx-only",
        dest="web_bridge_rx_only",
        action="store_true",
        help="Bridge RX only (no TX from virtual device to radio)",
    )
    web_p.add_argument(
        "--dx-cluster",
        dest="dx_cluster",
        default=None,
        metavar="HOST:PORT",
        help="Connect to DX cluster server (e.g. dxc.nc7j.com:7373). Feature is opt-in.",
    )
    web_p.add_argument(
        "--callsign",
        dest="callsign",
        default=None,
        metavar="CALL",
        help="Your callsign for DX cluster login (required with --dx-cluster)",
    )
    web_p.add_argument(
        "--no-rigctld",
        dest="web_rigctld",
        action="store_false",
        default=True,
        help="Disable the rigctld-compatible TCP server (enabled by default)",
    )
    web_p.add_argument(
        "--rigctld-port",
        dest="web_rigctld_port",
        type=int,
        default=4532,
        help="rigctld TCP port (default: 4532)",
    )

    # proxy
    proxy_p = sub.add_parser("proxy", help="Transparent UDP relay for remote access via VPN")
    proxy_p.add_argument(
        "--radio",
        required=True,
        help="Radio IP address (e.g. 192.168.55.40)",
    )
    proxy_p.add_argument(
        "--listen",
        default="0.0.0.0",
        help="Listen address (default: 0.0.0.0)",
    )
    proxy_p.add_argument(
        "--port",
        type=int,
        default=50001,
        help="Base port (default: 50001, uses +0/+1/+2)",
    )

    # scope
    scope_p = sub.add_parser("scope", help="Capture scope/waterfall and render image")
    scope_p.add_argument(
        "--output",
        "-o",
        default="scope.png",
        help="Output file path (default: scope.png)",
    )
    scope_p.add_argument(
        "--frames",
        "-n",
        type=int,
        default=50,
        help="Number of frames to capture for waterfall (default: 50)",
    )
    scope_p.add_argument(
        "--theme",
        choices=["classic", "grayscale"],
        default="classic",
        help="Color theme (default: classic)",
    )
    scope_p.add_argument(
        "--spectrum-only",
        action="store_true",
        help="Capture 1 frame and render spectrum only",
    )
    scope_p.add_argument(
        "--width",
        type=int,
        default=800,
        help="Image width in pixels (default: 800)",
    )
    scope_p.add_argument(
        "--json",
        action="store_true",
        help="Output raw frame data as JSON instead of image",
    )
    scope_p.add_argument(
        "--capture-timeout",
        type=float,
        default=None,
        help="Capture timeout in seconds (default: 10 for spectrum-only, 15 for waterfall)",
    )

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


def _build_backend_config(args: argparse.Namespace) -> LanBackendConfig | SerialBackendConfig:
    """Build typed backend config from parsed CLI args."""
    backend = getattr(args, "backend", "lan")
    if backend == "serial":
        device = getattr(args, "serial_port", "")
        if not device:
            raise ValueError(
                "Serial backend requires --serial-port (or $ICOM_SERIAL_DEVICE).\n"
                "  Example: icom-lan --backend serial --serial-port /dev/tty.usbmodem-IC7610 status"
            )
        return SerialBackendConfig(
            device=device,
            baudrate=getattr(args, "serial_baud", 115200),
            timeout=args.timeout,
            rx_device=getattr(args, "rx_device", None) or None,
            tx_device=getattr(args, "tx_device", None) or None,
            ptt_mode=getattr(args, "serial_ptt_mode", "civ"),
        )
    return LanBackendConfig(
        host=args.host,
        port=args.control_port,
        username=args.user,
        password=args.password,
        timeout=args.timeout,
    )


async def _cmd_list_audio_devices(args: argparse.Namespace) -> int:
    """List available USB audio devices."""
    try:
        import sounddevice as _sd
    except ImportError:
        print(
            "Error: --list-audio-devices requires the sounddevice package.\n"
            "  Install with: pip install icom-lan[bridge]",
            file=sys.stderr,
        )
        return 1
    from .backends.icom7610.drivers.usb_audio import list_usb_audio_devices

    devices = list_usb_audio_devices(_sd)
    if getattr(args, "json", False):
        print(
            json.dumps(
                [
                    {
                        "index": d.index,
                        "name": d.name,
                        "input_channels": d.input_channels,
                        "output_channels": d.output_channels,
                        "default_samplerate": d.default_samplerate,
                        "is_default_input": d.is_default_input,
                        "is_default_output": d.is_default_output,
                    }
                    for d in devices
                ]
            )
        )
    else:
        if not devices:
            print("No audio devices found.")
        else:
            print(f"{len(devices)} audio device(s):")
            for d in devices:
                tags: list[str] = []
                if d.is_default_input:
                    tags.append("default-in")
                if d.is_default_output:
                    tags.append("default-out")
                tag_str = f"  [{', '.join(tags)}]" if tags else ""
                print(
                    f"  [{d.index}] {d.name}"
                    f"  (in={d.input_channels}, out={d.output_channels}){tag_str}"
                )
    return 0


async def _run(args: argparse.Namespace) -> int:
    wants_stats = bool(getattr(args, "stats", False))
    if args.command == "audio" and args.audio_command == "caps" and not wants_stats:
        return await _cmd_audio_caps(args)

    try:
        config = _build_backend_config(args)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    radio = create_radio(config)  # type: ignore[assignment]

    try:
        async with radio:
            if args.command == "audio" and args.audio_command == "caps":
                runtime_stats: dict[str, bool | int | float | str] = (
                    AudioStats.inactive().to_dict()
                )
                await radio.start_audio_rx_opus(lambda _pkt: None)
                try:
                    await asyncio.sleep(1.0)
                    runtime_stats = radio.get_audio_stats()
                finally:
                    await radio.stop_audio_rx_opus()
                return await _cmd_audio_caps(args, runtime_stats=runtime_stats)
            elif args.command == "status":
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
            elif args.command == "web":
                return await _cmd_web(radio, args)
            elif args.command == "scope":
                return await _cmd_scope(radio, args)
            elif args.command == "serve":
                return await _cmd_serve(radio, args)
            elif args.command == "audio":
                if args.audio_command == "rx":
                    return await _cmd_audio_rx(radio, args)
                elif args.audio_command == "tx":
                    return await _cmd_audio_tx(radio, args)
                elif args.audio_command == "loopback":
                    return await _cmd_audio_loopback(radio, args)
                elif args.audio_command == "bridge":
                    return await _cmd_audio_bridge(radio, args)
                print("Error: unknown audio command", file=sys.stderr)
                return 1
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


def _audio_frame_bytes(sample_rate: int, channels: int, frame_ms: int = _AUDIO_FRAME_MS) -> int:
    return sample_rate * channels * _PCM_SAMPLE_WIDTH_BYTES * frame_ms // 1000


def _validate_audio_format_args(sample_rate: int, channels: int) -> str | None:
    if sample_rate <= 0:
        return "--sample-rate must be > 0."
    if channels <= 0:
        return "--channels must be > 0."

    caps = IcomRadio.audio_capabilities()
    if sample_rate not in caps.supported_sample_rates_hz:
        supported = ", ".join(str(rate) for rate in caps.supported_sample_rates_hz)
        return f"Unsupported --sample-rate {sample_rate}. Supported values: {supported}."
    if channels not in caps.supported_channels:
        supported = ", ".join(str(ch) for ch in caps.supported_channels)
        return f"Unsupported --channels {channels}. Supported values: {supported}."
    return None


def _validate_positive_seconds(seconds: float) -> str | None:
    if seconds <= 0:
        return "--seconds must be > 0."
    return None


def _emit_audio_result(
    args: argparse.Namespace,
    *,
    message: str,
    payload: dict[str, Any],
) -> None:
    if args.json:
        print(json.dumps(payload))
        return

    print(message)
    if args.stats:
        for key, value in payload.items():
            print(f"{key}: {value}")


def _print_audio_stats(stats: dict[str, bool | int | float | str]) -> None:
    print("Runtime stats:")
    print(f"  active: {stats['active']}")
    print(f"  state: {stats['state']}")
    print(f"  rx_packets_received: {stats['rx_packets_received']}")
    print(f"  rx_packets_delivered: {stats['rx_packets_delivered']}")
    print(f"  tx_packets_sent: {stats['tx_packets_sent']}")
    print(f"  packets_lost: {stats['packets_lost']}")
    print(f"  packet_loss_percent: {float(stats['packet_loss_percent']):.3f}")
    print(f"  jitter_ms: {float(stats['jitter_ms']):.3f}")
    print(f"  jitter_max_ms: {float(stats['jitter_max_ms']):.3f}")
    print(f"  underrun_count: {stats['underrun_count']}")
    print(f"  overrun_count: {stats['overrun_count']}")
    print(f"  estimated_latency_ms: {float(stats['estimated_latency_ms']):.3f}")
    print(
        "  jitter_buffer_depth_packets: "
        f"{stats['jitter_buffer_depth_packets']}"
    )
    print(
        "  jitter_buffer_pending_packets: "
        f"{stats['jitter_buffer_pending_packets']}"
    )
    print(f"  duplicates_dropped: {stats['duplicates_dropped']}")
    print(f"  stale_packets_dropped: {stats['stale_packets_dropped']}")
    print(f"  out_of_order_packets: {stats['out_of_order_packets']}")


async def _cmd_status(radio: IcomRadio, args: argparse.Namespace) -> int:
    freq = await radio.get_frequency()
    mode_name, _filt = await radio.get_mode()
    s_meter = await radio.get_s_meter()
    power = await radio.get_power()

    if args.json:
        import json

        print(
            json.dumps(
                {
                    "frequency_hz": freq,
                    "frequency_mhz": round(freq / 1e6, 6),
                    "mode": mode_name,
                    "s_meter": s_meter,
                    "power": power,
                }
            )
        )
    else:
        print(f"Frequency: {freq:>12,} Hz  ({freq / 1e6:.6f} MHz)")
        print(f"Mode:      {mode_name}")
        print(f"S-meter:   {s_meter}")
        print(f"Power:     {power}")
    return 0


async def _cmd_audio_caps(
    args: argparse.Namespace,
    *,
    runtime_stats: dict[str, bool | int | float | str] | None = None,
) -> int:
    caps = IcomRadio.audio_capabilities()
    wants_stats = bool(getattr(args, "stats", False))

    if args.json:
        import json

        payload = caps.to_dict()
        if wants_stats:
            payload["runtime_stats"] = (
                runtime_stats
                if runtime_stats is not None
                else AudioStats.inactive().to_dict()
            )
        print(json.dumps(payload))
    else:
        print("Supported codecs:")
        for codec in caps.supported_codecs:
            print(f"  - {codec.name} (0x{int(codec):02X})")
        print(
            "Supported sample rates (Hz): "
            + ", ".join(str(rate) for rate in caps.supported_sample_rates_hz)
        )
        print(
            "Supported channels: "
            + ", ".join(str(channels) for channels in caps.supported_channels)
        )
        print("Defaults:")
        print(
            f"  codec: {caps.default_codec.name} "
            f"(0x{int(caps.default_codec):02X})"
        )
        print(f"  sample_rate_hz: {caps.default_sample_rate_hz}")
        print(f"  channels: {caps.default_channels}")
        print("Selection rules:")
        print("  codec: first supported codec in preference order")
        print("  sample_rate_hz: highest supported rate")
        print("  channels: from default codec (fallback to minimum)")
        if wants_stats:
            _print_audio_stats(
                runtime_stats
                if runtime_stats is not None
                else AudioStats.inactive().to_dict()
            )
    return 0


async def _cmd_audio_rx(radio: IcomRadio, args: argparse.Namespace) -> int:
    fmt_error = _validate_audio_format_args(args.sample_rate, args.channels)
    if fmt_error is not None:
        print(f"Error: {fmt_error}", file=sys.stderr)
        return 1

    seconds_error = _validate_positive_seconds(args.seconds)
    if seconds_error is not None:
        print(f"Error: {seconds_error}", file=sys.stderr)
        return 1

    frame_bytes = _audio_frame_bytes(args.sample_rate, args.channels)
    silence_frame = b"\x00" * frame_bytes
    frames: list[bytes] = []
    rx_frames = 0
    gap_frames = 0
    started = False
    start_time = time.monotonic()

    def on_pcm(frame: bytes | None) -> None:
        nonlocal rx_frames, gap_frames
        if frame is None:
            gap_frames += 1
            frames.append(silence_frame)
            return
        rx_frames += 1
        frames.append(frame)

    try:
        await radio.start_audio_rx_pcm(
            on_pcm,
            sample_rate=args.sample_rate,
            channels=args.channels,
            frame_ms=_AUDIO_FRAME_MS,
        )
        started = True
        await asyncio.sleep(args.seconds)
    finally:
        if started:
            try:
                await radio.stop_audio_rx_pcm()
            except Exception:
                logger.debug("audio-rx: stop_audio_rx_pcm failed", exc_info=True)

    pcm_bytes = b"".join(frames)
    try:
        with wave.open(args.output_file, "wb") as wf:
            wf.setnchannels(args.channels)
            wf.setsampwidth(_PCM_SAMPLE_WIDTH_BYTES)
            wf.setframerate(args.sample_rate)
            wf.writeframes(pcm_bytes)
    except Exception as exc:
        print(f"Error: failed to write WAV file '{args.output_file}': {exc}", file=sys.stderr)
        return 1

    elapsed = round(time.monotonic() - start_time, 3)
    payload = {
        "command": "audio-rx",
        "output_file": args.output_file,
        "seconds_requested": args.seconds,
        "seconds_elapsed": elapsed,
        "sample_rate": args.sample_rate,
        "channels": args.channels,
        "rx_frames": rx_frames,
        "gap_frames": gap_frames,
        "bytes_written": len(pcm_bytes),
    }
    _emit_audio_result(
        args,
        message=f"Saved RX audio to {args.output_file}",
        payload=payload,
    )
    return 0


def _load_wav_pcm(input_file: str) -> tuple[int, int, int, bytes]:
    with wave.open(input_file, "rb") as wf:
        channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        sample_rate = wf.getframerate()
        pcm = wf.readframes(wf.getnframes())
    return sample_rate, channels, sample_width, pcm


async def _cmd_audio_tx(radio: IcomRadio, args: argparse.Namespace) -> int:
    fmt_error = _validate_audio_format_args(args.sample_rate, args.channels)
    if fmt_error is not None:
        print(f"Error: {fmt_error}", file=sys.stderr)
        return 1

    try:
        file_sample_rate, file_channels, sample_width, pcm = _load_wav_pcm(args.input_file)
    except FileNotFoundError:
        print(f"Error: input file not found: {args.input_file}", file=sys.stderr)
        return 1
    except wave.Error as exc:
        print(f"Error: invalid WAV file '{args.input_file}': {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Error: failed to read '{args.input_file}': {exc}", file=sys.stderr)
        return 1

    if sample_width != _PCM_SAMPLE_WIDTH_BYTES:
        print(
            (
                "Error: input WAV must be 16-bit PCM "
                f"(got {sample_width * 8}-bit)."
            ),
            file=sys.stderr,
        )
        return 1
    if file_sample_rate != args.sample_rate:
        print(
            (
                f"Error: input WAV sample rate is {file_sample_rate} Hz, "
                f"but --sample-rate is {args.sample_rate}. "
                "Use a matching WAV or pass the file's sample rate."
            ),
            file=sys.stderr,
        )
        return 1
    if file_channels != args.channels:
        print(
            (
                f"Error: input WAV has {file_channels} channel(s), "
                f"but --channels is {args.channels}. "
                "Use a matching WAV or pass the file's channel count."
            ),
            file=sys.stderr,
        )
        return 1
    if not pcm:
        print("Error: input WAV contains no PCM frames.", file=sys.stderr)
        return 1

    frame_bytes = _audio_frame_bytes(args.sample_rate, args.channels)
    frame_interval = _AUDIO_FRAME_MS / 1000.0
    start_time = time.monotonic()
    tx_frames = 0
    started = False

    try:
        await radio.start_audio_tx_pcm(
            sample_rate=args.sample_rate,
            channels=args.channels,
            frame_ms=_AUDIO_FRAME_MS,
        )
        started = True
        for i in range(0, len(pcm), frame_bytes):
            chunk = pcm[i : i + frame_bytes]
            if not chunk:
                break
            if len(chunk) < frame_bytes:
                chunk = chunk + (b"\x00" * (frame_bytes - len(chunk)))
            await radio.push_audio_tx_pcm(chunk)
            tx_frames += 1
            await asyncio.sleep(frame_interval)
    finally:
        if started:
            try:
                await radio.stop_audio_tx_pcm()
            except Exception:
                logger.debug("audio-tx: stop_audio_tx_pcm failed", exc_info=True)

    elapsed = round(time.monotonic() - start_time, 3)
    payload = {
        "command": "audio-tx",
        "input_file": args.input_file,
        "seconds_elapsed": elapsed,
        "sample_rate": args.sample_rate,
        "channels": args.channels,
        "tx_frames": tx_frames,
        "bytes_read": len(pcm),
    }
    _emit_audio_result(
        args,
        message=f"Transmitted WAV audio from {args.input_file}",
        payload=payload,
    )
    return 0


async def _cmd_audio_loopback(radio: IcomRadio, args: argparse.Namespace) -> int:
    fmt_error = _validate_audio_format_args(args.sample_rate, args.channels)
    if fmt_error is not None:
        print(f"Error: {fmt_error}", file=sys.stderr)
        return 1

    seconds_error = _validate_positive_seconds(args.seconds)
    if seconds_error is not None:
        print(f"Error: {seconds_error}", file=sys.stderr)
        return 1

    frame_bytes = _audio_frame_bytes(args.sample_rate, args.channels)
    silence_frame = b"\x00" * frame_bytes
    frame_interval = _AUDIO_FRAME_MS / 1000.0
    queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=256)
    stop_event = asyncio.Event()

    rx_frames = 0
    gap_frames = 0
    tx_frames = 0
    dropped_frames = 0

    def on_pcm(frame: bytes | None) -> None:
        nonlocal rx_frames, gap_frames, dropped_frames
        if frame is None:
            gap_frames += 1
            out = silence_frame
        else:
            rx_frames += 1
            out = frame
        try:
            queue.put_nowait(out)
        except asyncio.QueueFull:
            dropped_frames += 1

    async def tx_worker() -> None:
        nonlocal tx_frames
        while not (stop_event.is_set() and queue.empty()):
            try:
                frame = await asyncio.wait_for(queue.get(), timeout=0.1)
            except asyncio.TimeoutError:
                continue
            await radio.push_audio_tx_pcm(frame)
            tx_frames += 1
            await asyncio.sleep(frame_interval)

    rx_started = False
    tx_started = False
    worker_task: asyncio.Task[None] | None = None
    worker_error: Exception | None = None
    start_time = time.monotonic()

    try:
        await radio.start_audio_tx_pcm(
            sample_rate=args.sample_rate,
            channels=args.channels,
            frame_ms=_AUDIO_FRAME_MS,
        )
        tx_started = True
        worker_task = asyncio.create_task(tx_worker())
        await radio.start_audio_rx_pcm(
            on_pcm,
            sample_rate=args.sample_rate,
            channels=args.channels,
            frame_ms=_AUDIO_FRAME_MS,
        )
        rx_started = True
        await asyncio.sleep(args.seconds)
    finally:
        if rx_started:
            try:
                await radio.stop_audio_rx_pcm()
            except Exception:
                logger.debug("audio-loopback: stop_audio_rx_pcm failed", exc_info=True)
        stop_event.set()
        if worker_task is not None:
            try:
                await worker_task
            except Exception as exc:
                worker_error = exc
        if tx_started:
            try:
                await radio.stop_audio_tx_pcm()
            except Exception:
                logger.debug("audio-loopback: stop_audio_tx_pcm failed", exc_info=True)

    if worker_error is not None:
        raise worker_error

    elapsed = round(time.monotonic() - start_time, 3)
    payload = {
        "command": "audio-loopback",
        "seconds_requested": args.seconds,
        "seconds_elapsed": elapsed,
        "sample_rate": args.sample_rate,
        "channels": args.channels,
        "rx_frames": rx_frames,
        "gap_frames": gap_frames,
        "tx_frames": tx_frames,
        "dropped_frames": dropped_frames,
    }
    _emit_audio_result(
        args,
        message="Audio loopback completed",
        payload=payload,
    )
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
        mode_name, _ = await radio.get_mode()
        if args.json:
            import json

            print(json.dumps({"mode": mode_name}))
        else:
            print(mode_name)
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


async def _cmd_scope(radio: IcomRadio, args: argparse.Namespace) -> int:
    if args.frames < 1:
        print("Error: --frames must be >= 1", file=sys.stderr)
        return 1
    if args.width < 64:
        print("Error: --width must be >= 64", file=sys.stderr)
        return 1
    if args.capture_timeout is not None and args.capture_timeout <= 0:
        print("Error: --capture-timeout must be > 0", file=sys.stderr)
        return 1

    if not args.json:
        try:
            from .scope_render import render_scope_image, render_spectrum
        except ImportError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

    try:
        if args.spectrum_only:
            timeout = args.capture_timeout if args.capture_timeout is not None else 10.0
            print("Capturing 1 scope frame...", file=sys.stderr)
            frame = await radio.capture_scope_frame(timeout=timeout)

            if args.json:
                import json

                print(
                    json.dumps(
                        {
                            "receiver": frame.receiver,
                            "mode": frame.mode,
                            "start_freq_hz": frame.start_freq_hz,
                            "end_freq_hz": frame.end_freq_hz,
                            "out_of_range": frame.out_of_range,
                            "pixels": list(frame.pixels),
                        }
                    )
                )
            else:
                img = render_spectrum(frame, width=args.width, theme=args.theme)
                img.save(args.output, "PNG")
                print(f"Saved spectrum to {args.output}")
        else:
            n = args.frames
            timeout = args.capture_timeout if args.capture_timeout is not None else 15.0
            print(f"Capturing {n} scope frames...", file=sys.stderr)
            frames = await radio.capture_scope_frames(count=n, timeout=timeout)

            if args.json:
                import json

                data = [
                    {
                        "receiver": f.receiver,
                        "mode": f.mode,
                        "start_freq_hz": f.start_freq_hz,
                        "end_freq_hz": f.end_freq_hz,
                        "out_of_range": f.out_of_range,
                        "pixels": list(f.pixels),
                    }
                    for f in frames
                ]
                print(json.dumps(data))
            else:
                render_scope_image(
                    frames,
                    width=args.width,
                    theme=args.theme,
                    output=args.output,
                )
                print(f"Saved scope image to {args.output}")
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        # Always disable scope data output when CLI is done
        try:
            await radio.disable_scope()
        except Exception:
            logger.debug("scope: disable_scope failed", exc_info=True)

    return 0


async def _cmd_audio_bridge(radio: IcomRadio, args: argparse.Namespace) -> int:
    """Bridge radio audio to a virtual audio device."""
    from .audio_bridge import AudioBridge, find_loopback_device, list_audio_devices

    if args.list_devices:
        try:
            devices = list_audio_devices()
        except ImportError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        print("Available audio devices:")
        for dev in devices:
            marker = ""
            name = dev.get("name", "?")
            idx = dev.get("index", "?")
            max_in = dev.get("max_input_channels", 0)
            max_out = dev.get("max_output_channels", 0)
            # Mark likely virtual devices
            for hint in ("BlackHole", "Loopback", "VB-Audio", "Virtual"):
                if hint.lower() in name.lower():
                    marker = " ← virtual"
                    break
            print(f"  [{idx}] {name}  (in={max_in}, out={max_out}){marker}")
        return 0

    try:
        bridge = AudioBridge(
            radio,
            device_name=args.device,
            tx_enabled=not args.rx_only,
        )
        await bridge.start()
    except ImportError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    direction = "RX only" if args.rx_only else "RX+TX"
    print(f"Audio bridge running ({direction}). Press Ctrl+C to stop.")

    try:
        while True:
            await asyncio.sleep(10)
            s = bridge.stats
            logger.info(
                "audio-bridge: rx=%d tx=%d drops=%d",
                s["rx_frames"],
                s["tx_frames"],
                s["rx_drops"],
            )
    except asyncio.CancelledError:
        pass
    finally:
        await bridge.stop()
        s = bridge.stats
        print(
            f"\nBridge stopped. RX: {s['rx_frames']} frames, "
            f"TX: {s['tx_frames']} frames, drops: {s['rx_drops']}"
        )

    return 0


async def _cmd_serve(radio: IcomRadio, args: argparse.Namespace) -> int:
    import logging as _logging

    from .rigctld.audit import AUDIT_LOGGER_NAME, RigctldAuditFormatter
    from .rigctld.contract import RigctldConfig
    from .rigctld.server import RigctldServer

    # Apply requested log level to the icom_lan logger hierarchy.
    log_level = getattr(args, "log_level", "INFO")
    _logging.getLogger("icom_lan").setLevel(getattr(_logging, log_level))

    # Configure JSON audit log if a path was provided.
    audit_log_path: str | None = getattr(args, "audit_log", None)
    if audit_log_path:
        fh = _logging.FileHandler(audit_log_path)
        fh.setFormatter(RigctldAuditFormatter())
        audit_logger = _logging.getLogger(AUDIT_LOGGER_NAME)
        audit_logger.addHandler(fh)
        audit_logger.setLevel(_logging.INFO)
        audit_logger.propagate = False

    config = RigctldConfig(
        host=args.serve_host,
        port=args.serve_port,
        read_only=args.read_only,
        max_clients=args.max_clients,
        cache_ttl=args.cache_ttl,
        wsjtx_compat=args.wsjtx_compat,
        command_rate_limit=getattr(args, "rate_limit", None),
    )
    ro_str = "yes" if args.read_only else "no"
    compat_str = "on" if args.wsjtx_compat else "off"
    print(
        f"Listening on {args.serve_host}:{args.serve_port} "
        f"(read-only: {ro_str}, wsjtx-compat: {compat_str})"
    )
    try:
        await RigctldServer(radio, config).serve_forever()
    except asyncio.CancelledError:
        pass
    return 0


async def _cmd_web(radio: IcomRadio, args: argparse.Namespace) -> int:
    import pathlib

    from .web.server import WebConfig, WebServer

    static_dir = (
        pathlib.Path(args.web_static_dir) if args.web_static_dir else None
    )
    config_kwargs: dict[str, Any] = {
        "host": args.web_host,
        "port": args.web_port,
    }
    if static_dir is not None:
        config_kwargs["static_dir"] = static_dir

    dx_cluster = getattr(args, "dx_cluster", None)
    if dx_cluster:
        host_part, sep, port_str = dx_cluster.rpartition(":")
        if not host_part or not sep or not port_str.isdigit():
            print(
                f"Error: --dx-cluster must be HOST:PORT (got {dx_cluster!r})",
                file=sys.stderr,
            )
            return 1
        config_kwargs["dx_cluster_host"] = host_part
        config_kwargs["dx_cluster_port"] = int(port_str)
        config_kwargs["dx_callsign"] = getattr(args, "callsign", None) or ""

    config = WebConfig(**config_kwargs)
    server = WebServer(radio, config)
    if dx_cluster:
        print(f"DX cluster: {dx_cluster} (callsign: {config_kwargs.get('dx_callsign', '')})")
    print(f"Web UI listening on http://{args.web_host}:{args.web_port}/")

    # Start audio bridge if requested
    bridge_device = getattr(args, "web_bridge", None)
    if bridge_device is not None:
        device_name = None if bridge_device == "auto" else bridge_device
        tx_device_name = getattr(args, "web_bridge_tx_device", None)
        rx_only = getattr(args, "web_bridge_rx_only", False)
        try:
            await server.start_audio_bridge(
                device_name=device_name,
                tx_device_name=tx_device_name,
                tx_enabled=not rx_only,
            )
            direction = "RX only" if rx_only else "RX+TX"
            print(f"Audio bridge active ({direction})")
        except Exception as exc:
            print(f"Warning: audio bridge failed: {exc}", file=sys.stderr)

    # Start rigctld if requested
    rigctld_server = None
    if getattr(args, "web_rigctld", False):
        from .rigctld.contract import RigctldConfig
        from .rigctld.server import RigctldServer

        rigctld_port = getattr(args, "web_rigctld_port", 4532)
        rigctld_config = RigctldConfig(
            host="0.0.0.0",
            port=rigctld_port,
        )
        rigctld_server = RigctldServer(radio, rigctld_config)
        await rigctld_server.start()
        print(f"rigctld listening on 0.0.0.0:{rigctld_port}")

    try:
        await server.serve_forever()
    except asyncio.CancelledError:
        pass
    finally:
        if rigctld_server is not None:
            await rigctld_server.stop()
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
    import logging

    parser = _build_parser()
    args = parser.parse_args()

    # Enable debug logging with ICOM_DEBUG=1 or any truthy value
    if os.environ.get("ICOM_DEBUG", "").strip() not in ("", "0", "false", "no"):
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s %(name)s %(levelname)s %(message)s",
            datefmt="%H:%M:%S",
        )
    else:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(message)s",
            datefmt="%H:%M:%S",
        )

    if getattr(args, "list_audio_devices", False):
        sys.exit(asyncio.run(_cmd_list_audio_devices(args)))
    elif args.command == "discover":
        if getattr(args, "backend", "lan") == "serial":
            print(
                "Error: 'discover' is not supported for the serial backend.\n"
                "  Tip: discover scans the network via UDP broadcast (LAN only).\n"
                "  Use --backend lan or omit --backend to discover radios on the network.",
                file=sys.stderr,
            )
            sys.exit(1)
        sys.exit(asyncio.run(_cmd_discover(None, args)))  # type: ignore[arg-type]
    elif args.command == "proxy":
        from .proxy import run_proxy
        asyncio.run(run_proxy(args.radio, args.listen, args.port))
        sys.exit(0)
    elif args.command is None:
        parser.print_help()
        sys.exit(0)
    else:
        # Convert SIGTERM to KeyboardInterrupt so asyncio.run() cleanup
        # properly unwinds the async context manager (radio.disconnect()).
        def _sigterm_handler(signum: int, frame: Any) -> None:
            raise KeyboardInterrupt()
        signal.signal(signal.SIGTERM, _sigterm_handler)

        # Write PID file for clean stop/restart
        pid_file = Path("/tmp/icom-lan.pid")
        pid_file.write_text(str(os.getpid()))

        try:
            sys.exit(asyncio.run(_run(args)))
        except KeyboardInterrupt:
            # Graceful Ctrl-C / SIGTERM path (radio/session cleanup happens in async context).
            print("Interrupted, shutting down...", file=sys.stderr)
            sys.exit(130)
        finally:
            try:
                pid_file.unlink(missing_ok=True)
            except OSError:
                pass


if __name__ == "__main__":
    main()
