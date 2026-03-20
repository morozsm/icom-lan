"""Mock-based integration tests for IC-7610 tone/TSQL commands (issue #134).

Tests the full request/response cycle for all 4 tone/TSQL command groups using a
local mock radio server.  No real hardware required — runs in CI without env vars.

Commands under test:
  1. Repeater Tone enable/disable (0x16 sub 0x42)
  2. Repeater TSQL enable/disable (0x16 sub 0x43)
  3. Tone Frequency set/get (0x1B sub 0x00)
  4. TSQL Frequency set/get (0x1B sub 0x01)

Run with::

    pytest tests/integration/test_tone_tsql_integration.py -v
"""

from __future__ import annotations

import asyncio
import sys
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest

# Make tests/ importable from tests/integration/
sys.path.insert(0, str(Path(__file__).parent.parent))

# All tests use MockIcomRadio — no real hardware required.
pytestmark = pytest.mark.mock_integration

from icom_lan.radio import IcomRadio  # noqa: E402, TID251
from _perf_helpers import fast_connect  # noqa: E402
from mock_server import MockIcomRadio  # noqa: E402

# ---------------------------------------------------------------------------
# Local CI-V constants (keep mock self-contained)
# ---------------------------------------------------------------------------

_CMD_TONE = 0x1B
_CMD_FUNC = 0x16

_SUB_TONE_FREQ = 0x00
_SUB_TSQL_FREQ = 0x01
_SUB_REPEATER_TONE = 0x42
_SUB_REPEATER_TSQL = 0x43

_SETTLE = 0.05  # seconds: wait after fire-and-forget SET before GET

# Standard CTCSS test frequencies (Hz)
_FREQ_MIN = 67.0
_FREQ_DEFAULT = 88.5
_FREQ_MID_LO = 110.9
_FREQ_MID_HI = 136.5
_FREQ_MID_2 = 167.9
_FREQ_MAX = 254.1


# ---------------------------------------------------------------------------
# BCD helpers
# ---------------------------------------------------------------------------


def _bcd_byte(value: int) -> int:
    """Encode 0-99 integer to one BCD byte (e.g. 18 → 0x18)."""
    return ((value // 10) << 4) | (value % 10)


def _bcd_byte_decode(b: int) -> int:
    """Decode one BCD byte to integer (e.g. 0x18 → 18)."""
    return ((b >> 4) & 0x0F) * 10 + (b & 0x0F)


def _encode_tone_freq(freq_hz: float) -> bytes:
    """Encode a CTCSS tone frequency to 3-byte BCD.

    The radio stores frequency in three BCD bytes:
      byte[0] = hundreds of Hz  (e.g. 110.9 Hz → _bcd_byte(1)  = 0x01)
      byte[1] = tens+units of Hz (e.g. 110.9 Hz → _bcd_byte(10) = 0x10)
      byte[2] = tenths of Hz    (e.g. 110.9 Hz → _bcd_byte(9)  = 0x09)
    """
    int_part = int(freq_hz)
    hundreds = int_part // 100
    tens_units = int_part % 100
    tenths_digit = int(round(freq_hz * 10)) % 10
    return bytes([_bcd_byte(hundreds), _bcd_byte(tens_units), _bcd_byte(tenths_digit)])


def _decode_tone_freq(data: bytes) -> float:
    """Decode 3-byte BCD to a CTCSS tone frequency in Hz."""
    hundreds = _bcd_byte_decode(data[0])
    tens_units = _bcd_byte_decode(data[1])
    tenths = _bcd_byte_decode(data[2])
    return round(hundreds * 100 + tens_units + tenths / 10.0, 1)


# ---------------------------------------------------------------------------
# Extended mock with tone/TSQL state
# ---------------------------------------------------------------------------


class ToneMockRadio(MockIcomRadio):
    """MockIcomRadio extended with repeater tone/TSQL and frequency state.

    Handles:
      - 0x16 / sub 0x42: repeater tone on/off
      - 0x16 / sub 0x43: repeater TSQL on/off
      - 0x1B / sub 0x00: tone frequency get/set (3-byte BCD)
      - 0x1B / sub 0x01: TSQL frequency get/set (3-byte BCD)

    All other commands are forwarded to the parent MockIcomRadio.
    """

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._repeater_tone: int = 0  # 0 = off, 1 = on
        self._repeater_tsql: int = 0  # 0 = off, 1 = on
        self._tone_freq_hz: float = _FREQ_DEFAULT
        self._tsql_freq_hz: float = _FREQ_DEFAULT

    # ------------------------------------------------------------------
    # Helper: strip receiver prefix (command29)
    # ------------------------------------------------------------------

    @staticmethod
    def _strip_receiver_prefix(data: bytes) -> tuple[int | None, bytes]:
        """Strip receiver prefix (0x00=MAIN, 0x01=SUB) from command29 data."""
        if not data:
            return (None, data)
        if data[0] in (0x00, 0x01):
            return (data[0], data[1:])
        return (None, data)

    # ------------------------------------------------------------------
    # CI-V dispatch override
    # ------------------------------------------------------------------

    def _dispatch_civ(self, cmd: int, payload: bytes, from_addr: int) -> bytes | None:
        """Intercept tone (0x1B) commands (non-command29)."""
        if cmd == _CMD_TONE:
            return self._dispatch_tone(payload, from_addr)
        return super()._dispatch_civ(cmd, payload, from_addr)

    def _dispatch_cmd29(
        self, real_cmd: int, inner: bytes, from_addr: int, receiver: int
    ) -> bytes | None:
        """Handle Command29-wrapped tone/TSQL commands."""
        to = from_addr
        frm = self._radio_addr

        # Handle 0x16 (PREAMP/functions) with tone/TSQL sub-commands
        if real_cmd == _CMD_FUNC:
            if not inner:
                return self._civ_nak(to, frm)
            sub = inner[0]
            rest = inner[1:]

            if sub == _SUB_REPEATER_TONE:
                if rest:  # SET
                    self._repeater_tone = rest[0]
                    return self._civ_ack(to, frm)
                # GET — wrap in Command29
                return self._civ_frame(
                    to,
                    frm,
                    0x29,
                    data=bytes(
                        [receiver, _CMD_FUNC, _SUB_REPEATER_TONE, self._repeater_tone]
                    ),
                )

            if sub == _SUB_REPEATER_TSQL:
                if rest:  # SET
                    self._repeater_tsql = rest[0]
                    return self._civ_ack(to, frm)
                # GET — wrap in Command29
                return self._civ_frame(
                    to,
                    frm,
                    0x29,
                    data=bytes(
                        [receiver, _CMD_FUNC, _SUB_REPEATER_TSQL, self._repeater_tsql]
                    ),
                )

        # Handle 0x1B (tone frequency) sub-commands
        if real_cmd == _CMD_TONE:
            if not inner:
                return self._civ_nak(to, frm)
            sub = inner[0]
            rest = inner[1:]

            if sub == _SUB_TONE_FREQ:
                if len(rest) >= 3:  # SET (3-byte BCD)
                    self._tone_freq_hz = _decode_tone_freq(rest[:3])
                    return self._civ_ack(to, frm)
                # GET — wrap in Command29
                return self._civ_frame(
                    to,
                    frm,
                    0x29,
                    data=bytes([receiver, _CMD_TONE, _SUB_TONE_FREQ])
                    + _encode_tone_freq(self._tone_freq_hz),
                )

            if sub == _SUB_TSQL_FREQ:
                if len(rest) >= 3:  # SET (3-byte BCD)
                    self._tsql_freq_hz = _decode_tone_freq(rest[:3])
                    return self._civ_ack(to, frm)
                # GET — wrap in Command29
                return self._civ_frame(
                    to,
                    frm,
                    0x29,
                    data=bytes([receiver, _CMD_TONE, _SUB_TSQL_FREQ])
                    + _encode_tone_freq(self._tsql_freq_hz),
                )

        # Fall through to parent for other commands (ATT, preamp status, etc.)
        return super()._dispatch_cmd29(real_cmd, inner, from_addr, receiver)

    # ------------------------------------------------------------------
    # Tone frequency dispatch (0x1B)
    # ------------------------------------------------------------------

    def _dispatch_tone(self, payload: bytes, from_addr: int) -> bytes | None:
        """Dispatch tone-frequency commands (cmd 0x1B)."""
        if not payload:
            return self._civ_nak(from_addr, self._radio_addr)
        sub = payload[0]
        rest = payload[1:]
        if sub == _SUB_TONE_FREQ:
            return self._handle_tone_freq(rest, from_addr)
        if sub == _SUB_TSQL_FREQ:
            return self._handle_tsql_freq(rest, from_addr)
        return self._civ_nak(from_addr, self._radio_addr)

    # ------------------------------------------------------------------
    # Individual command handlers
    # ------------------------------------------------------------------

    def _handle_repeater_tone(self, rest: bytes, from_addr: int) -> bytes:
        """Handle repeater tone enable/disable (0x16 sub 0x42)."""
        to = from_addr
        frm = self._radio_addr
        # Strip receiver prefix (command29)
        receiver, data = self._strip_receiver_prefix(rest)
        if data:  # SET
            self._repeater_tone = data[0]
            return self._civ_ack(to, frm)
        # GET: include receiver prefix in response if present
        response_data = (bytes([receiver]) if receiver is not None else b"") + bytes(
            [self._repeater_tone]
        )
        return self._civ_frame(
            to,
            frm,
            _CMD_FUNC,
            sub=_SUB_REPEATER_TONE,
            data=response_data,
        )

    def _handle_repeater_tsql(self, rest: bytes, from_addr: int) -> bytes:
        """Handle repeater TSQL enable/disable (0x16 sub 0x43)."""
        to = from_addr
        frm = self._radio_addr
        # Strip receiver prefix (command29)
        receiver, data = self._strip_receiver_prefix(rest)
        if data:  # SET
            self._repeater_tsql = data[0]
            return self._civ_ack(to, frm)
        # GET: include receiver prefix in response if present
        response_data = (bytes([receiver]) if receiver is not None else b"") + bytes(
            [self._repeater_tsql]
        )
        return self._civ_frame(
            to,
            frm,
            _CMD_FUNC,
            sub=_SUB_REPEATER_TSQL,
            data=response_data,
        )

    def _handle_tone_freq(self, rest: bytes, from_addr: int) -> bytes:
        """Handle tone frequency get/set (0x1B sub 0x00)."""
        to = from_addr
        frm = self._radio_addr
        # Strip receiver prefix (command29)
        receiver, data = self._strip_receiver_prefix(rest)
        if len(data) >= 3:  # SET (3-byte BCD payload)
            self._tone_freq_hz = _decode_tone_freq(data[:3])
            return self._civ_ack(to, frm)
        # GET: include receiver prefix in response if present
        response_data = (
            bytes([receiver]) if receiver is not None else b""
        ) + _encode_tone_freq(self._tone_freq_hz)
        return self._civ_frame(
            to,
            frm,
            _CMD_TONE,
            sub=_SUB_TONE_FREQ,
            data=response_data,
        )

    def _handle_tsql_freq(self, rest: bytes, from_addr: int) -> bytes:
        """Handle TSQL frequency get/set (0x1B sub 0x01)."""
        to = from_addr
        frm = self._radio_addr
        # Strip receiver prefix (command29)
        receiver, data = self._strip_receiver_prefix(rest)
        if len(data) >= 3:  # SET (3-byte BCD payload)
            self._tsql_freq_hz = _decode_tone_freq(data[:3])
            return self._civ_ack(to, frm)
        # GET: include receiver prefix in response if present
        response_data = (
            bytes([receiver]) if receiver is not None else b""
        ) + _encode_tone_freq(self._tsql_freq_hz)
        return self._civ_frame(
            to,
            frm,
            _CMD_TONE,
            sub=_SUB_TSQL_FREQ,
            data=response_data,
        )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def tone_mock() -> AsyncGenerator[ToneMockRadio, None]:
    """Start a ToneMockRadio server for each test, stop it after."""
    server = ToneMockRadio()
    await server.start()
    yield server
    await server.stop()


@pytest.fixture
async def tone_radio(tone_mock: ToneMockRadio) -> AsyncGenerator[IcomRadio, None]:
    """IcomRadio connected to ToneMockRadio, disconnected after each test."""
    radio = IcomRadio(
        host="127.0.0.1",
        port=tone_mock.control_port,
        username="testuser",
        password="testpass",
        timeout=5.0,
    )
    with fast_connect():
        await radio.connect()
    yield radio
    await radio.disconnect()


# ---------------------------------------------------------------------------
# 1. Repeater Tone
# ---------------------------------------------------------------------------


class TestRepeaterTone:
    """Repeater tone enable/disable roundtrip tests."""

    async def test_default_off(self, tone_radio: IcomRadio) -> None:
        """Default repeater tone state is OFF."""
        result = await tone_radio.get_repeater_tone()
        assert result is False

    async def test_set_on(
        self, tone_radio: IcomRadio, tone_mock: ToneMockRadio
    ) -> None:
        """Set repeater tone ON and verify via GET."""
        await tone_radio.set_repeater_tone(True)
        await asyncio.sleep(_SETTLE)

        result = await tone_radio.get_repeater_tone()
        assert result is True
        assert tone_mock._repeater_tone == 1

    async def test_set_off_after_on(
        self, tone_radio: IcomRadio, tone_mock: ToneMockRadio
    ) -> None:
        """Set repeater tone ON then OFF; GET returns False."""
        await tone_radio.set_repeater_tone(True)
        await asyncio.sleep(_SETTLE)

        await tone_radio.set_repeater_tone(False)
        await asyncio.sleep(_SETTLE)

        result = await tone_radio.get_repeater_tone()
        assert result is False
        assert tone_mock._repeater_tone == 0

    async def test_toggle_on_off_on(self, tone_radio: IcomRadio) -> None:
        """Toggle repeater tone on → off → on."""
        await tone_radio.set_repeater_tone(True)
        await asyncio.sleep(_SETTLE)
        assert await tone_radio.get_repeater_tone() is True

        await tone_radio.set_repeater_tone(False)
        await asyncio.sleep(_SETTLE)
        assert await tone_radio.get_repeater_tone() is False

        await tone_radio.set_repeater_tone(True)
        await asyncio.sleep(_SETTLE)
        assert await tone_radio.get_repeater_tone() is True


# ---------------------------------------------------------------------------
# 2. Repeater TSQL
# ---------------------------------------------------------------------------


class TestRepeaterTSQL:
    """Repeater TSQL enable/disable roundtrip tests."""

    async def test_default_off(self, tone_radio: IcomRadio) -> None:
        """Default repeater TSQL state is OFF."""
        result = await tone_radio.get_repeater_tsql()
        assert result is False

    async def test_set_on(
        self, tone_radio: IcomRadio, tone_mock: ToneMockRadio
    ) -> None:
        """Set repeater TSQL ON and verify via GET."""
        await tone_radio.set_repeater_tsql(True)
        await asyncio.sleep(_SETTLE)

        result = await tone_radio.get_repeater_tsql()
        assert result is True
        assert tone_mock._repeater_tsql == 1

    async def test_set_off_after_on(
        self, tone_radio: IcomRadio, tone_mock: ToneMockRadio
    ) -> None:
        """Set repeater TSQL ON then OFF; GET returns False."""
        await tone_radio.set_repeater_tsql(True)
        await asyncio.sleep(_SETTLE)

        await tone_radio.set_repeater_tsql(False)
        await asyncio.sleep(_SETTLE)

        result = await tone_radio.get_repeater_tsql()
        assert result is False
        assert tone_mock._repeater_tsql == 0

    async def test_toggle_on_off_on(self, tone_radio: IcomRadio) -> None:
        """Toggle repeater TSQL on → off → on."""
        await tone_radio.set_repeater_tsql(True)
        await asyncio.sleep(_SETTLE)
        assert await tone_radio.get_repeater_tsql() is True

        await tone_radio.set_repeater_tsql(False)
        await asyncio.sleep(_SETTLE)
        assert await tone_radio.get_repeater_tsql() is False

        await tone_radio.set_repeater_tsql(True)
        await asyncio.sleep(_SETTLE)
        assert await tone_radio.get_repeater_tsql() is True

    async def test_tone_and_tsql_independent(self, tone_radio: IcomRadio) -> None:
        """Repeater tone and TSQL are independent flags."""
        await tone_radio.set_repeater_tone(True)
        await tone_radio.set_repeater_tsql(False)
        await asyncio.sleep(_SETTLE)

        assert await tone_radio.get_repeater_tone() is True
        assert await tone_radio.get_repeater_tsql() is False

        await tone_radio.set_repeater_tone(False)
        await tone_radio.set_repeater_tsql(True)
        await asyncio.sleep(_SETTLE)

        assert await tone_radio.get_repeater_tone() is False
        assert await tone_radio.get_repeater_tsql() is True


# ---------------------------------------------------------------------------
# 3. Tone Frequency
# ---------------------------------------------------------------------------


class TestToneFrequency:
    """Tone frequency set/get roundtrip tests."""

    async def test_default_freq(self, tone_radio: IcomRadio) -> None:
        """Default tone frequency is 88.5 Hz."""
        result = await tone_radio.get_tone_freq()
        assert result == _FREQ_DEFAULT

    async def test_set_min_freq(
        self, tone_radio: IcomRadio, tone_mock: ToneMockRadio
    ) -> None:
        """Set tone frequency to 67.0 Hz (minimum CTCSS tone)."""
        await tone_radio.set_tone_freq(_FREQ_MIN)
        await asyncio.sleep(_SETTLE)

        result = await tone_radio.get_tone_freq()
        assert result == _FREQ_MIN
        assert tone_mock._tone_freq_hz == _FREQ_MIN

    async def test_set_110_9_hz(self, tone_radio: IcomRadio) -> None:
        """Set tone frequency to 110.9 Hz."""
        await tone_radio.set_tone_freq(_FREQ_MID_LO)
        await asyncio.sleep(_SETTLE)

        result = await tone_radio.get_tone_freq()
        assert result == _FREQ_MID_LO

    async def test_set_max_freq(
        self, tone_radio: IcomRadio, tone_mock: ToneMockRadio
    ) -> None:
        """Set tone frequency to 254.1 Hz (maximum CTCSS tone)."""
        await tone_radio.set_tone_freq(_FREQ_MAX)
        await asyncio.sleep(_SETTLE)

        result = await tone_radio.get_tone_freq()
        assert result == _FREQ_MAX
        assert tone_mock._tone_freq_hz == _FREQ_MAX

    async def test_multiple_freq_changes(self, tone_radio: IcomRadio) -> None:
        """Change tone frequency through all standard test values."""
        for freq in (
            _FREQ_MIN,
            _FREQ_DEFAULT,
            _FREQ_MID_LO,
            _FREQ_MID_HI,
            _FREQ_MID_2,
            _FREQ_MAX,
        ):
            await tone_radio.set_tone_freq(freq)
            await asyncio.sleep(_SETTLE)
            result = await tone_radio.get_tone_freq()
            assert result == freq, f"Expected {freq} Hz, got {result} Hz"

    async def test_freq_roundtrip_precision(self, tone_radio: IcomRadio) -> None:
        """BCD encoding/decoding preserves single-decimal precision."""
        for freq in (67.0, 77.0, 88.5, 100.0, 110.9, 127.3, 167.9, 203.5, 254.1):
            await tone_radio.set_tone_freq(freq)
            await asyncio.sleep(_SETTLE)
            result = await tone_radio.get_tone_freq()
            assert result == freq, f"Precision loss: sent {freq}, got {result}"


# ---------------------------------------------------------------------------
# 4. TSQL Frequency
# ---------------------------------------------------------------------------


class TestTSQLFrequency:
    """TSQL frequency set/get roundtrip tests."""

    async def test_default_freq(self, tone_radio: IcomRadio) -> None:
        """Default TSQL frequency is 88.5 Hz."""
        result = await tone_radio.get_tsql_freq()
        assert result == _FREQ_DEFAULT

    async def test_set_min_freq(
        self, tone_radio: IcomRadio, tone_mock: ToneMockRadio
    ) -> None:
        """Set TSQL frequency to 67.0 Hz (minimum CTCSS tone)."""
        await tone_radio.set_tsql_freq(_FREQ_MIN)
        await asyncio.sleep(_SETTLE)

        result = await tone_radio.get_tsql_freq()
        assert result == _FREQ_MIN
        assert tone_mock._tsql_freq_hz == _FREQ_MIN

    async def test_set_110_9_hz(self, tone_radio: IcomRadio) -> None:
        """Set TSQL frequency to 110.9 Hz."""
        await tone_radio.set_tsql_freq(_FREQ_MID_LO)
        await asyncio.sleep(_SETTLE)

        result = await tone_radio.get_tsql_freq()
        assert result == _FREQ_MID_LO

    async def test_set_max_freq(
        self, tone_radio: IcomRadio, tone_mock: ToneMockRadio
    ) -> None:
        """Set TSQL frequency to 254.1 Hz (maximum CTCSS tone)."""
        await tone_radio.set_tsql_freq(_FREQ_MAX)
        await asyncio.sleep(_SETTLE)

        result = await tone_radio.get_tsql_freq()
        assert result == _FREQ_MAX
        assert tone_mock._tsql_freq_hz == _FREQ_MAX

    async def test_multiple_freq_changes(self, tone_radio: IcomRadio) -> None:
        """Change TSQL frequency through all standard test values."""
        for freq in (
            _FREQ_MIN,
            _FREQ_DEFAULT,
            _FREQ_MID_LO,
            _FREQ_MID_HI,
            _FREQ_MID_2,
            _FREQ_MAX,
        ):
            await tone_radio.set_tsql_freq(freq)
            await asyncio.sleep(_SETTLE)
            result = await tone_radio.get_tsql_freq()
            assert result == freq, f"Expected {freq} Hz, got {result} Hz"

    async def test_tone_and_tsql_freq_independent(self, tone_radio: IcomRadio) -> None:
        """Tone and TSQL frequencies are stored independently."""
        await tone_radio.set_tone_freq(_FREQ_MID_LO)
        await tone_radio.set_tsql_freq(_FREQ_MAX)
        await asyncio.sleep(_SETTLE)

        tone = await tone_radio.get_tone_freq()
        tsql = await tone_radio.get_tsql_freq()
        assert tone == _FREQ_MID_LO
        assert tsql == _FREQ_MAX

    async def test_freq_roundtrip_precision(self, tone_radio: IcomRadio) -> None:
        """BCD encoding/decoding preserves single-decimal precision for TSQL."""
        for freq in (67.0, 77.0, 88.5, 100.0, 110.9, 127.3, 167.9, 203.5, 254.1):
            await tone_radio.set_tsql_freq(freq)
            await asyncio.sleep(_SETTLE)
            result = await tone_radio.get_tsql_freq()
            assert result == freq, f"Precision loss: sent {freq}, got {result}"


# ---------------------------------------------------------------------------
# BCD codec unit checks (no radio needed)
# ---------------------------------------------------------------------------


class TestBcdCodec:
    """Verify the mock's BCD encode/decode helpers are self-consistent."""

    @pytest.mark.parametrize(
        "freq",
        [
            67.0,
            77.0,
            88.5,
            100.0,
            110.9,
            127.3,
            136.5,
            167.9,
            203.5,
            254.1,
        ],
    )
    def test_encode_decode_roundtrip(self, freq: float) -> None:
        """encode → decode must recover the original frequency."""
        encoded = _encode_tone_freq(freq)
        assert len(encoded) == 3
        decoded = _decode_tone_freq(encoded)
        assert decoded == freq, f"Roundtrip failed for {freq} Hz: got {decoded}"
