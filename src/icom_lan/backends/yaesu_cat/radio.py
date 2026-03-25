"""Yaesu CAT radio backend — FTX-1 and compatible transceivers.

Implements the core :class:`~icom_lan.radio_protocol.Radio` protocol
using :class:`YaesuCatTransport` for serial I/O and
:class:`CatCommandParser` / :func:`format_command` for encoding.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from ...audio import AudioPacket
from ...audio.usb_driver import UsbAudioDriver
from ...command_spec import CatCommandSpec
from ...exceptions import AudioFormatError, CommandError
from ...exceptions import ConnectionError as RadioConnectionError
from ...radio_state import RadioState
from .parser import CatCommandParser, format_command
from .transport import YaesuCatTransport

if TYPE_CHECKING:
    from ...audio_bus import AudioBus

__all__ = ["YaesuCatRadio"]

logger = logging.getLogger(__name__)

# Path to rigs/ directory: src/icom_lan/backends/yaesu_cat/radio.py → 4 levels up
_RIGS_DIR = Path(__file__).parents[4] / "rigs"


def _load_config(profile: Any) -> Any:
    """Load RigConfig from a profile name or return an existing RigConfig."""
    from ...rig_loader import RigConfig, load_rig

    if isinstance(profile, str):
        path = _RIGS_DIR / f"{profile}.toml"
        return load_rig(path)
    if isinstance(profile, RigConfig):
        return profile
    raise TypeError(f"profile must be str or RigConfig, got {type(profile).__name__}")


class YaesuCatRadio:
    """Radio backend for Yaesu FTX-1 (and compatible) transceivers.

    Communicates via Yaesu CAT protocol over serial.  Supports the four
    core operations needed for the FTX-1 smoke test: frequency, mode,
    PTT, and S-meter.

    Usage::

        async with YaesuCatRadio("/dev/cu.usbserial-...") as radio:
            freq = await radio.get_freq()
            await radio.set_freq(14_074_000)
            mode, _ = await radio.get_mode()
            await radio.set_ptt(True)
            s = await radio.get_s_meter()
    """

    def __init__(
        self,
        device: str,
        baudrate: int = 38400,
        profile: str | Any = "ftx1",
        rx_device: str | None = None,
        tx_device: str | None = None,
        audio_sample_rate: int = 48000,
        audio_driver: UsbAudioDriver | None = None,
    ) -> None:
        """Create a YaesuCatRadio instance.

        Args:
            device: Serial port path (e.g. ``"/dev/cu.usbserial-01AE340D0"``).
            baudrate: Serial baud rate (default 38400 for FTX-1).
            profile: Rig profile name (``"ftx1"``) or a loaded ``RigConfig``.
            rx_device: USB audio input device name for RX audio capture.
            tx_device: USB audio output device name for TX audio playback.
            audio_sample_rate: Audio sample rate in Hz (default 48000).
            audio_driver: Optional pre-constructed UsbAudioDriver (for testing).
        """
        self._config = _load_config(profile)
        self._transport = YaesuCatTransport(device=device, baudrate=baudrate)
        self._state = RadioState()
        self._audio_bus: AudioBus | None = None
        self._audio_seq = 0
        self._opus_rx_user_callback: Callable[[AudioPacket | None], None] | None = None
        self._pcm_rx_user_callback: Callable[[bytes | None], None] | None = None
        self._audio_driver: UsbAudioDriver = audio_driver or UsbAudioDriver(
            serial_port=device,
            rx_device=rx_device,
            tx_device=tx_device,
            sample_rate=audio_sample_rate,
            channels=1,
        )

        # Build bidirectional mode code ↔ name maps.
        # FTX-1 CAT codes are 1-based: index 0 in modes list → code "1".
        self._code_to_mode: dict[str, str] = {}
        self._mode_to_code: dict[str, str] = {}
        for i, name in enumerate(self._config.modes, start=1):
            code = str(i)
            self._code_to_mode[code] = name
            self._mode_to_code[name] = code

        # Compile response parsers once at init time (keyed by command name).
        # Commands with unsupported placeholders (e.g. {vfo}, {band}) are skipped.
        self._parsers: dict[str, CatCommandParser] = {}
        for cmd_name, spec in self._config.commands.items():
            if isinstance(spec, CatCommandSpec) and spec.parse:
                try:
                    self._parsers[cmd_name] = CatCommandParser(spec.parse)
                except ValueError:
                    logger.debug(
                        "Skipping parser for %r (unsupported placeholder)", cmd_name
                    )

    # -- Lifecycle ----------------------------------------------------------

    async def connect(self) -> None:
        """Open the serial port."""
        await self._transport.connect()

    async def disconnect(self) -> None:
        """Close the serial port."""
        await self._audio_driver.stop_rx()
        await self._audio_driver.stop_tx()
        await self._transport.close()

    async def __aenter__(self) -> "YaesuCatRadio":
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.disconnect()

    @property
    def connected(self) -> bool:
        """Whether the serial transport is connected."""
        return self._transport.connected

    @property
    def radio_ready(self) -> bool:
        """Whether the backend is ready for commands."""
        return self._transport.connected

    @property
    def model(self) -> str:
        """Human-readable radio model name (e.g. ``'FTX-1'``)."""
        return self._config.model

    @property
    def capabilities(self) -> set[str]:
        """Set of capability tags from the rig profile."""
        return set(self._config.capabilities)

    @property
    def radio_state(self) -> RadioState:
        """Live radio state snapshot (updated by get_* calls)."""
        return self._state

    @property
    def audio_bus(self) -> "AudioBus":
        """AudioBus instance for pub/sub audio distribution."""
        if self._audio_bus is None:
            from ...audio_bus import AudioBus
            self._audio_bus = AudioBus(self)
        return self._audio_bus

    # -- AudioCapable methods -----------------------------------------------

    async def start_audio_rx_opus(
        self,
        callback: Callable[[AudioPacket | None], None],
        *,
        jitter_depth: int = 5,
    ) -> None:
        if not callable(callback):
            raise TypeError("callback must be callable and accept AudioPacket | None.")
        if isinstance(jitter_depth, bool) or not isinstance(jitter_depth, int):
            raise TypeError(
                f"jitter_depth must be an int, got {type(jitter_depth).__name__}."
            )
        if jitter_depth < 0:
            raise ValueError(f"jitter_depth must be >= 0, got {jitter_depth}.")
        self._require_connected()

        self._opus_rx_user_callback = callback

        def _on_pcm_frame(pcm_frame: bytes) -> None:
            packet = AudioPacket(
                ident=0x9781,
                send_seq=self._audio_seq,
                data=pcm_frame,
            )
            self._audio_seq = (self._audio_seq + 1) & 0xFFFF
            callback(packet)

        await self._audio_driver.start_rx(_on_pcm_frame)

    async def stop_audio_rx_opus(self) -> None:
        self._opus_rx_user_callback = None
        await self._audio_driver.stop_rx()

    async def start_audio_rx_pcm(
        self,
        callback: Callable[[bytes | None], None],
        *,
        sample_rate: int = 48000,
        channels: int = 1,
        frame_ms: int = 20,
        jitter_depth: int = 5,
    ) -> None:
        if not callable(callback):
            raise TypeError("callback must be callable and accept bytes | None.")
        for name, value in (
            ("sample_rate", sample_rate),
            ("channels", channels),
            ("frame_ms", frame_ms),
            ("jitter_depth", jitter_depth),
        ):
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name} must be an int, got {type(value).__name__}.")
        if jitter_depth < 0:
            raise ValueError(f"jitter_depth must be >= 0, got {jitter_depth}.")
        if (sample_rate * frame_ms) % 1000 != 0:
            raise AudioFormatError(
                "sample_rate * frame_ms must produce an integer frame size."
            )

        self._require_connected()
        self._pcm_rx_user_callback = callback

        await self._audio_driver.start_rx(
            callback,
            sample_rate=sample_rate,
            channels=channels,
            frame_ms=frame_ms,
        )

    async def stop_audio_rx_pcm(self) -> None:
        self._pcm_rx_user_callback = None
        await self._audio_driver.stop_rx()

    async def start_audio_tx_pcm(
        self,
        *,
        sample_rate: int = 48000,
        channels: int = 1,
        frame_ms: int = 20,
    ) -> None:
        for name, value in (
            ("sample_rate", sample_rate),
            ("channels", channels),
            ("frame_ms", frame_ms),
        ):
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name} must be an int, got {type(value).__name__}.")
        if (sample_rate * frame_ms) % 1000 != 0:
            raise AudioFormatError(
                "sample_rate * frame_ms must produce an integer frame size."
            )

        self._require_connected()
        await self._audio_driver.start_tx(
            sample_rate=sample_rate,
            channels=channels,
            frame_ms=frame_ms,
        )

    async def stop_audio_tx_pcm(self) -> None:
        await self._audio_driver.stop_tx()

    async def push_pcm_tx(self, frame: bytes) -> None:
        if not isinstance(frame, bytes):
            raise TypeError(f"frame must be bytes, got {type(frame).__name__}.")
        if len(frame) == 0:
            raise ValueError("frame must not be empty.")

        self._require_connected()
        await self._audio_driver.push_tx_pcm(frame)

    # -- Internal helpers ---------------------------------------------------

    def _get_spec(self, name: str) -> CatCommandSpec:
        """Return the CatCommandSpec for *name*, raising CommandError if absent."""
        spec = self._config.commands.get(name)
        if spec is None:
            raise CommandError(
                f"Command {name!r} not found in profile {self._config.model!r}"
            )
        if not isinstance(spec, CatCommandSpec):
            raise CommandError(
                f"Command {name!r} is not a CAT command spec"
            )
        return spec

    def _require_connected(self) -> None:
        if not self._transport.connected:
            raise RadioConnectionError("Radio not connected — call connect() first")

    async def _query(self, cmd_name: str) -> dict[str, Any]:
        """Send a read command and return the parsed response fields.

        The transport strips the trailing ``;`` from responses; we add it
        back before passing to the parser (templates include the semicolon).
        """
        self._require_connected()
        spec = self._get_spec(cmd_name)
        if spec.read is None:
            raise CommandError(f"Command {cmd_name!r} has no read template")

        raw = await self._transport.query(spec.read)

        parser = self._parsers.get(cmd_name)
        if parser is None:
            raise CommandError(f"Command {cmd_name!r} has no parse template")

        # Transport strips trailing ';'; add it back for the parser.
        return parser.parse(raw + ";")

    async def _write(self, cmd_name: str, **kwargs: Any) -> None:
        """Format and send a write command (no response expected)."""
        self._require_connected()
        spec = self._get_spec(cmd_name)
        if spec.write is None:
            raise CommandError(f"Command {cmd_name!r} has no write template")

        cmd = format_command(spec.write, **kwargs)
        await self._transport.write(cmd)

    # -- Frequency ----------------------------------------------------------

    async def get_freq(self, receiver: int = 0) -> int:
        """Get the current VFO frequency in Hz.

        Args:
            receiver: 0 = main (VFO-A), 1 = sub (VFO-B).
        """
        cmd = "get_freq" if receiver == 0 else "get_freq_sub"
        result = await self._query(cmd)
        freq: int = result["freq"]
        if receiver == 0:
            self._state.main.freq = freq
        else:
            self._state.sub.freq = freq
        return freq

    async def set_freq(self, freq: int, receiver: int = 0) -> None:
        """Set the VFO frequency in Hz.

        Args:
            freq: Frequency in Hz (e.g. ``14_074_000``).
            receiver: 0 = main (VFO-A), 1 = sub (VFO-B).
        """
        cmd = "set_freq" if receiver == 0 else "set_freq_sub"
        await self._write(cmd, freq=freq)
        if receiver == 0:
            self._state.main.freq = freq
        else:
            self._state.sub.freq = freq

    # -- Mode ---------------------------------------------------------------

    async def get_mode(self, receiver: int = 0) -> tuple[str, int | None]:
        """Get the current operating mode.

        Returns:
            Tuple of (mode_name, None).  Mode names are from the rig
            profile (e.g. ``"USB"``, ``"LSB"``, ``"CW-U"``).
        """
        cmd = "get_mode" if receiver == 0 else "get_mode_sub"
        result = await self._query(cmd)
        code: str = result["mode"]
        mode_name = self._code_to_mode.get(code, f"UNKNOWN({code})")
        if receiver == 0:
            self._state.main.mode = mode_name
        else:
            self._state.sub.mode = mode_name
        return mode_name, None

    async def set_mode(
        self,
        mode: str,
        filter_width: int | None = None,
        receiver: int = 0,
    ) -> None:
        """Set the operating mode.

        Args:
            mode: Mode name from the rig profile (e.g. ``"USB"``).
            filter_width: Ignored (not supported by this backend).
            receiver: 0 = main, 1 = sub.
        """
        code = self._mode_to_code.get(mode)
        if code is None:
            raise CommandError(
                f"Unknown mode {mode!r} for {self._config.model!r}. "
                f"Available: {list(self._mode_to_code)}"
            )
        cmd = "set_mode" if receiver == 0 else "set_mode_sub"
        await self._write(cmd, mode=code)
        if receiver == 0:
            self._state.main.mode = mode
        else:
            self._state.sub.mode = mode

    async def get_data_mode(self) -> bool:
        """Data mode is not implemented in this minimal backend."""
        return False

    async def set_data_mode(self, on: int | bool, receiver: int = 0) -> None:
        """Data mode is not implemented in this minimal backend."""

    # -- PTT ----------------------------------------------------------------

    async def set_ptt(self, on: bool) -> None:
        """Key or un-key the transmitter.

        Args:
            on: ``True`` to transmit, ``False`` to receive.
        """
        await self._write("set_ptt", state="1" if on else "0")
        self._state.ptt = on

    async def get_ptt(self) -> bool:
        """Query the current PTT state.

        Returns:
            ``True`` if transmitting, ``False`` if receiving.
        """
        result = await self._query("get_ptt")
        ptt = result["state"] == "1"
        self._state.ptt = ptt
        return ptt

    # -- S-meter ------------------------------------------------------------

    async def get_s_meter(self, receiver: int = 0) -> int:
        """Get the S-meter raw value.

        Args:
            receiver: 0 = main, 1 = sub.

        Returns:
            Raw S-meter reading (0–255, vendor scale).
        """
        cmd = "get_s_meter" if receiver == 0 else "get_s_meter_sub"
        result = await self._query(cmd)
        raw: int = result["raw"]
        if receiver == 0:
            self._state.main.s_meter = raw
        else:
            self._state.sub.s_meter = raw
        return raw

    # -- D1: RX Audio Controls ----------------------------------------------

    async def get_af_level(self, receiver: int = 0) -> int:
        """Get the AF (audio) level (0–255).

        Args:
            receiver: 0 = main (sub not yet supported by TOML profile).
        """
        result = await self._query("get_af_level")
        return result["level"]

    async def set_af_level(self, level: int, receiver: int = 0) -> None:
        """Set the AF (audio) level (0–255)."""
        await self._write("set_af_level", level=level)

    async def get_rf_gain(self, receiver: int = 0) -> int:
        """Get the RF gain (0–255)."""
        result = await self._query("get_rf_gain")
        return result["level"]

    async def set_rf_gain(self, level: int, receiver: int = 0) -> None:
        """Set the RF gain (0–255)."""
        await self._write("set_rf_gain", level=level)

    async def get_squelch(self, receiver: int = 0) -> int:
        """Get the squelch level (0–255)."""
        result = await self._query("get_squelch")
        return result["level"]

    async def set_squelch(self, level: int, receiver: int = 0) -> None:
        """Set the squelch level (0–255)."""
        await self._write("set_squelch", level=level)

    # -- D2: RF Front-End ---------------------------------------------------

    async def get_attenuator(self, receiver: int = 0) -> int:
        """Get attenuator state (0 = OFF, 1 = ON)."""
        result = await self._query("get_attenuator")
        return int(result["state"])

    async def set_attenuator(self, state: int, receiver: int = 0) -> None:
        """Set attenuator state (0 = OFF, 1 = ON)."""
        await self._write("set_attenuator", state=str(state))

    async def get_preamp(self, band: int = 0) -> int:
        """Get preamp setting (0–2).

        Args:
            band: 0 = HF/50 MHz (PA0). Sub-band variants not yet supported.
        """
        result = await self._query("get_preamp")
        return int(result["value"])

    async def set_preamp(self, value: int, band: int = 0) -> None:
        """Set preamp setting.

        Args:
            value: Preamp level (0–2).
            band: 0 = HF/50 MHz, 1 = VHF, 2 = UHF.
        """
        await self._write("set_preamp", band=str(band), value=str(value))

    # -- D3: DSP (NB/NR/Notch) ----------------------------------------------

    async def get_nb_level(self, receiver: int = 0) -> int:
        """Get noise blanker level (0 = OFF, 1–10 = level)."""
        result = await self._query("get_nb_level")
        return result["level"]

    async def set_nb_level(self, level: int, receiver: int = 0) -> None:
        """Set noise blanker level (0 = OFF, 1–10 = level)."""
        await self._write("set_nb_level", level=level)

    async def get_nr_level(self, receiver: int = 0) -> int:
        """Get noise reduction level (0 = OFF, 1–15 = level)."""
        result = await self._query("get_nr_level")
        return result["level"]

    async def set_nr_level(self, level: int, receiver: int = 0) -> None:
        """Set noise reduction level (0 = OFF, 1–15 = level)."""
        await self._write("set_nr_level", level=level)

    async def get_auto_notch(self, receiver: int = 0) -> bool:
        """Get auto notch state (True = ON)."""
        result = await self._query("get_auto_notch")
        return result["state"] == "1"

    async def set_auto_notch(self, state: bool, receiver: int = 0) -> None:
        """Set auto notch state."""
        await self._write("set_auto_notch", state="1" if state else "0")

    async def get_manual_notch(self, receiver: int = 0) -> tuple[bool, int]:
        """Get manual notch state and frequency index.

        Returns:
            Tuple of (enabled: bool, freq_index: int 0–255).
        """
        state_result = await self._query("get_manual_notch")
        freq_result = await self._query("get_manual_notch_freq")
        return bool(state_result["state"]), freq_result["freq"]

    async def set_manual_notch(self, state: bool, receiver: int = 0) -> None:
        """Set manual notch ON/OFF (BP00)."""
        await self._write("set_manual_notch", state=1 if state else 0)

    async def set_manual_notch_freq(self, freq: int, receiver: int = 0) -> None:
        """Set manual notch frequency index (0–255, BP01)."""
        await self._write("set_manual_notch_freq", freq=freq)

    # -- D4: Filters --------------------------------------------------------

    async def get_filter_width(self, receiver: int = 0) -> int:
        """Get filter width index (SH00)."""
        result = await self._query("get_filter_width")
        return result["value"]

    async def set_filter_width(self, value: int, receiver: int = 0) -> None:
        """Set filter width index (SH00)."""
        await self._write("set_filter_width", value=value)

    async def get_filter_shift(self, receiver: int = 0) -> int:
        """Get filter shift index (SH01)."""
        result = await self._query("get_filter_shift")
        return result["value"]

    async def set_filter_shift(self, value: int, receiver: int = 0) -> None:
        """Set filter shift index (SH01)."""
        await self._write("set_filter_shift", value=value)

    async def get_if_shift(self, receiver: int = 0) -> int:
        """Get IF shift offset in Hz (signed, IS0).

        Returns:
            Signed offset in Hz (negative = downshift).
        """
        result = await self._query("get_if_shift")
        offset: int = result["offset"]
        return -offset if result["sign"] == "-" else offset

    async def set_if_shift(self, offset: int, receiver: int = 0) -> None:
        """Set IF shift offset in Hz (signed, IS0)."""
        sign = "+" if offset >= 0 else "-"
        await self._write("set_if_shift", sign=sign, offset=abs(offset))

    async def get_narrow(self, receiver: int = 0) -> bool:
        """Get narrow filter state (True = narrow)."""
        result = await self._query("get_narrow")
        return result["state"] == "1"

    async def set_narrow(self, state: bool, receiver: int = 0) -> None:
        """Set narrow filter state."""
        await self._write("set_narrow", state="1" if state else "0")

    # -- D5: Split/Dual Watch -----------------------------------------------

    async def get_rx_func(self) -> int:
        """Get RX function (0 = Dual RX, 1 = Single RX)."""
        result = await self._query("get_rx_func")
        return result["mode"]

    async def set_rx_func(self, mode: int) -> None:
        """Set RX function (0 = Dual RX, 1 = Single RX)."""
        await self._write("set_rx_func", mode=mode)

    async def get_tx_func(self) -> int:
        """Get TX function (0 = MAIN TX, 1 = SUB TX)."""
        result = await self._query("get_tx_func")
        return int(result["vfo"])

    async def set_tx_func(self, vfo: int) -> None:
        """Set TX function (0 = MAIN, 1 = SUB)."""
        await self._write("set_tx_func", vfo=str(vfo))

    async def get_split(self) -> bool:
        """Get split operation state."""
        result = await self._query("get_split")
        return result["state"] == "1"

    async def set_split(self, state: bool) -> None:
        """Set split operation state."""
        await self._write("set_split", state="1" if state else "0")

    async def get_vfo_select(self) -> int:
        """Get VFO selection (0 = MAIN, 1 = SUB)."""
        result = await self._query("get_vfo_select")
        return int(result["vfo"])

    async def set_vfo_select(self, vfo: int) -> None:
        """Set VFO selection (0 = MAIN, 1 = SUB)."""
        await self._write("set_vfo_select", vfo=str(vfo))

    async def vfo_a_to_b(self) -> None:
        """Copy VFO-A to VFO-B."""
        await self._write("vfo_a_to_b")

    async def vfo_b_to_a(self) -> None:
        """Copy VFO-B to VFO-A."""
        await self._write("vfo_b_to_a")

    # -- D6: TX Stack -------------------------------------------------------

    async def get_power(self) -> tuple[int, int]:
        """Get TX power setting.

        Returns:
            Tuple of (head: int, watts: int).
        """
        result = await self._query("get_power")
        return int(result["head"]), result["watts"]

    async def set_power(self, watts: int, head: int = 2) -> None:
        """Set TX power.

        Args:
            watts: Power in watts.
            head: Head selector (default 2).
        """
        await self._write("set_power", head=str(head), watts=watts)

    async def get_mic_gain(self) -> int:
        """Get microphone gain (0–100)."""
        result = await self._query("get_mic_gain")
        return result["level"]

    async def set_mic_gain(self, level: int) -> None:
        """Set microphone gain (0–100)."""
        await self._write("set_mic_gain", level=level)

    async def get_processor(self) -> bool:
        """Get speech processor state."""
        result = await self._query("get_processor")
        return result["state"] == "1"

    async def set_processor(self, state: bool) -> None:
        """Set speech processor state."""
        await self._write("set_processor", state="1" if state else "0")

    async def get_processor_level(self) -> int:
        """Get processor level (0–3)."""
        result = await self._query("get_processor_level")
        return result["level"]

    async def set_processor_level(self, level: int) -> None:
        """Set processor level (0–3)."""
        await self._write("set_processor_level", level=level)

    async def get_monitor_level(self) -> int:
        """Get monitor level (0–255)."""
        result = await self._query("get_monitor_level")
        return result["level"]

    async def set_monitor_level(self, level: int) -> None:
        """Set monitor level (0–255)."""
        await self._write("set_monitor_level", level=level)

    # -- D7: CW -------------------------------------------------------------

    async def get_keyer_speed(self) -> int:
        """Get CW keyer speed in WPM (4–60)."""
        result = await self._query("get_keyer_speed")
        return result["wpm"]

    async def set_keyer_speed(self, wpm: int) -> None:
        """Set CW keyer speed in WPM (4–60)."""
        await self._write("set_keyer_speed", wpm=wpm)

    async def get_key_pitch(self) -> int:
        """Get CW pitch index (0–75, maps to 300–1050 Hz)."""
        result = await self._query("get_key_pitch")
        return result["idx"]

    async def set_key_pitch(self, idx: int) -> None:
        """Set CW pitch index (0–75)."""
        await self._write("set_key_pitch", idx=idx)

    async def get_break_in(self) -> bool:
        """Get CW break-in state."""
        result = await self._query("get_break_in")
        return result["state"] == "1"

    async def set_break_in(self, state: bool) -> None:
        """Set CW break-in state."""
        await self._write("set_break_in", state="1" if state else "0")

    async def get_cw_spot(self) -> bool:
        """Get CW spot tone state."""
        result = await self._query("get_cw_spot")
        return result["state"] == "1"

    async def set_cw_spot(self, state: bool) -> None:
        """Set CW spot tone state."""
        await self._write("set_cw_spot", state="1" if state else "0")

    async def send_cw(self, msg_type: str, mem: str) -> None:
        """Send a CW message (KY command).

        Args:
            msg_type: Message type character.
            mem: CW message text to send.
        """
        await self._write("send_cw", type=msg_type, mem=mem)

    async def get_break_in_delay(self) -> int:
        """Get CW break-in delay in milliseconds (30–3000)."""
        result = await self._query("get_break_in_delay")
        return result["delay"]

    async def set_break_in_delay(self, delay: int) -> None:
        """Set CW break-in delay in milliseconds (30–3000)."""
        await self._write("set_break_in_delay", delay=delay)

    # -- D8: Clarifier (RIT/XIT) --------------------------------------------

    async def get_clarifier(self, receiver: int = 0) -> tuple[bool, bool]:
        """Get clarifier state (CF000).

        Returns:
            Tuple of (rx_clar: bool, tx_clar: bool).
        """
        result = await self._query("get_clarifier")
        return result["rx"] == "1", result["tx"] == "1"

    async def set_clarifier(
        self, rx_clar: bool, tx_clar: bool, receiver: int = 0
    ) -> None:
        """Set clarifier RX/TX state (CF000)."""
        await self._write(
            "set_clarifier",
            rx="1" if rx_clar else "0",
            tx="1" if tx_clar else "0",
            pad=0,
        )

    async def get_clarifier_freq(self, receiver: int = 0) -> int:
        """Get clarifier offset frequency in Hz (signed, CF001)."""
        result = await self._query("get_clarifier_freq")
        offset: int = result["offset"]
        return -offset if result["sign"] == "-" else offset

    async def set_clarifier_freq(self, offset: int, receiver: int = 0) -> None:
        """Set clarifier offset frequency in Hz (signed, CF001)."""
        sign = "+" if offset >= 0 else "-"
        await self._write("set_clarifier_freq", sign=sign, offset=abs(offset))

    # -- D9: Tone/TSQL ------------------------------------------------------

    async def get_sql_type(self, receiver: int = 0) -> int:
        """Get squelch type code (CT0)."""
        result = await self._query("get_sql_type")
        return result["type"]

    async def set_sql_type(self, type_code: int, receiver: int = 0) -> None:
        """Set squelch type code (CT0)."""
        await self._write("set_sql_type", type=type_code)

    # -- D10: System --------------------------------------------------------

    async def get_id(self) -> str:
        """Get radio model ID string (e.g. '0840')."""
        result = await self._query("get_id")
        return str(result["model"]).zfill(4)

    async def get_auto_info(self) -> bool:
        """Get auto-info (AI) state."""
        result = await self._query("get_auto_info")
        return result["state"] == "1"

    async def set_auto_info(self, state: bool) -> None:
        """Set auto-info (AI) state."""
        await self._write("set_auto_info", state="1" if state else "0")

    async def get_vox(self) -> bool:
        """Get VOX state."""
        result = await self._query("get_vox")
        return result["state"] == "1"

    async def set_vox(self, state: bool) -> None:
        """Set VOX state."""
        await self._write("set_vox", state="1" if state else "0")

    async def get_lock(self) -> bool:
        """Get dial lock state."""
        result = await self._query("get_lock")
        return result["state"] == "1"

    async def set_lock(self, state: bool) -> None:
        """Set dial lock state."""
        await self._write("set_lock", state="1" if state else "0")

    async def get_band(self, receiver: int = 0) -> int:
        """Get current band index (BS0)."""
        result = await self._query("get_band")
        return result["band"]

    async def set_band(self, band: int, receiver: int = 0) -> None:
        """Set current band by index (BS0)."""
        await self._write("set_band", band=band)

    async def band_up(self, receiver: int = 0) -> None:
        """Step up one band (BU0)."""
        await self._write("band_up")

    async def band_down(self, receiver: int = 0) -> None:
        """Step down one band (BD0)."""
        await self._write("band_down")

    # -- AGC ----------------------------------------------------------------

    async def get_agc(self, receiver: int = 0) -> int:
        """Get AGC mode (GT0).

        Returns:
            0=OFF, 1=FAST, 2=MID, 3=SLOW, 4=AUTO-F, 5=AUTO-M, 6=AUTO-S.
        """
        result = await self._query("get_agc")
        return int(result["mode"])

    async def set_agc(self, mode: int, receiver: int = 0) -> None:
        """Set AGC mode (GT0, 0–6)."""
        await self._write("set_agc", mode=str(mode))
