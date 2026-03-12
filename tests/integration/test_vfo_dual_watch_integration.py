"""Mock-based integration tests for VFO/dual-watch/scanning commands (issue #132, Part 3).

Tests the full request/response cycle for the 7 new commands using a local mock
radio server.  No real hardware required — runs in CI without env vars.

Commands under test:
  1. Tuning Step — get/set (CI-V 0x10)
  2. Scanning — start/stop (CI-V 0x0E)
  3. Dual Watch — on/off/state (CI-V 0x07 0xC0/0xC1/0xC2)
  4. Quick Dual Watch — fire-and-forget (CI-V 0x1A 0x05 0x00 0x32)
  5. Quick Split — fire-and-forget (CI-V 0x1A 0x05 0x00 0x33)

Wire encoding (matches actual implementation in commands.py):
  Tuning step 0x10:
    - GET: empty payload → radio replies with 1-byte BCD step index
    - SET: 1-byte BCD step index payload → radio ACKs
    - Step index 1-11: IC-7610 standard steps, BCD-encoded (10=0x10, 11=0x11)
  Scanning 0x0E: [0x01=start | 0x00=stop] → ACK
  Dual Watch:
    - SET OFF 0x07 0xC0 → ACK
    - SET ON  0x07 0xC1 → ACK
    - QUERY   0x07 0xC2 → radio replies with [0xC2, 0x00=off | 0x01=on]
  Quick DW (0x1A 0x05 0x00 0x32) → ACK
  Quick Split (0x1A 0x05 0x00 0x33) → ACK

Note on get_dual_watch():
  The current implementation routes the dual-watch query as an ACK-waiter
  (because _civ_expects_response sees non-empty data for cmd 0x07).
  Dual watch state is therefore tested via mock internal state (for SET)
  and via unsolicited frame injection (for the CIV-RX state path).

Run with::

    pytest tests/integration/test_vfo_dual_watch_integration.py -v
"""

from __future__ import annotations

import asyncio
import sys
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest

# Make tests/ importable from tests/integration/
sys.path.insert(0, str(Path(__file__).parent.parent))

# All tests in this module use MockIcomRadio and require no real hardware.
pytestmark = pytest.mark.mock_integration

from icom_lan.radio import IcomRadio  # noqa: E402, TID251
from mock_server import MockIcomRadio  # noqa: E402

# ---------------------------------------------------------------------------
# Local CI-V constants (keep mock self-contained)
# ---------------------------------------------------------------------------

_CMD_VFO_SELECT = 0x07
_CMD_SCANNING = 0x0E
_CMD_TUNING_STEP = 0x10
_CMD_CTL_MEM = 0x1A

_CONTROLLER_ADDR = 0xE0
_RADIO_ADDR = 0x98

# ---------------------------------------------------------------------------
# Extended mock with dual-watch / scanning / tuning-step state
# ---------------------------------------------------------------------------


class VfoDualWatchMockRadio(MockIcomRadio):
    """MockIcomRadio extended with dual-watch, scanning, and tuning-step state.

    Wire encoding matches the implementation in commands.py / radio.py:
      * Tuning Step (0x10): 1-byte BCD step index (1-11 per IC-7610 table)
      * Scanning (0x0E):    [0x01=start | 0x00=stop]
      * Dual Watch SET (0x07): [0xC0=off | 0xC1=on]
      * Dual Watch QUERY (0x07): [0xC2] → reply data=[0xC2, 0x00/0x01]
      * Quick DW (0x1A):    sub=0x05, data=b"\\x00\\x32"
      * Quick Split (0x1A): sub=0x05, data=b"\\x00\\x33"
    """

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        # Tuning step stored as raw BCD index byte (matches wire format)
        self._tuning_step: int = 0x04  # BCD index 4 (maps to 1kHz in IC-7610 table)
        self._scanning: bool = False
        self._dual_watch_on: bool = False
        # Unsolicited frame injection (for push-from-radio state update tests)
        self._civ_client_addr: tuple[str, int] | None = None
        self._civ_client_proto: object = None

    # ------------------------------------------------------------------
    # Track CIV client for unsolicited frame injection
    # ------------------------------------------------------------------

    def _dispatch(
        self,
        data: bytes,
        addr: tuple[str, int],
        ptype: int,
        sender_id: int,
        seq: int,
        label: str,
        proto: object,
    ) -> None:
        if label == "civ":
            self._civ_client_addr = addr
            self._civ_client_proto = proto
        super()._dispatch(data, addr, ptype, sender_id, seq, label, proto)

    def inject_unsolicited_civ(self, civ_frame: bytes) -> None:
        """Send an unsolicited CI-V frame to the connected CIV client."""
        if self._civ_client_addr is None or self._civ_client_proto is None:
            return
        pkt = self._wrap_civ(civ_frame, self._civ_client_id)
        self._civ_client_proto.send(pkt, self._civ_client_addr)  # type: ignore[attr-defined]

    # ------------------------------------------------------------------
    # CI-V dispatch overrides
    # ------------------------------------------------------------------

    def _dispatch_civ(self, cmd: int, payload: bytes, from_addr: int) -> bytes | None:
        to = from_addr
        frm = self._radio_addr

        # --- Tuning Step (0x10) ---
        if cmd == _CMD_TUNING_STEP:
            if payload:  # SET: [bcd_step_index]
                self._tuning_step = payload[0]
                return self._civ_ack(to, frm)
            # GET: respond with 1-byte BCD step index
            return self._civ_frame(
                to, frm, _CMD_TUNING_STEP, data=bytes([self._tuning_step])
            )

        # --- Scanning (0x0E) --- SET only
        if cmd == _CMD_SCANNING:
            if payload:
                self._scanning = payload[0] == 0x01
                return self._civ_ack(to, frm)
            return self._civ_nak(to, frm)

        # --- Dual Watch (0x07 0xC0/0xC1/0xC2) ---
        if cmd == _CMD_VFO_SELECT and payload:
            sub = payload[0]
            if sub == 0xC0:  # Dual Watch OFF
                self._dual_watch_on = False
                return self._civ_ack(to, frm)
            if sub == 0xC1:  # Dual Watch ON
                self._dual_watch_on = True
                return self._civ_ack(to, frm)
            if sub == 0xC2:  # Query Dual Watch
                flag = 0x01 if self._dual_watch_on else 0x00
                return self._civ_frame(
                    to, frm, _CMD_VFO_SELECT, data=bytes([0xC2, flag])
                )
            # Other 0x07 sub-commands (VFO select, equalize, swap) → parent
            return super()._dispatch_civ(cmd, payload, from_addr)

        # --- Quick Dual Watch / Quick Split (0x1A sub=0x05) ---
        if cmd == _CMD_CTL_MEM:
            if payload == b"\x05\x00\x32":  # Quick Dual Watch
                return self._civ_ack(to, frm)
            if payload == b"\x05\x00\x33":  # Quick Split
                return self._civ_ack(to, frm)

        return super()._dispatch_civ(cmd, payload, from_addr)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_SETTLE = 0.05  # seconds: wait after fire-and-forget SET before checking state


@pytest.fixture
async def vfo_mock() -> AsyncGenerator[VfoDualWatchMockRadio, None]:
    """Start a VfoDualWatchMockRadio server, stop it after the test."""
    server = VfoDualWatchMockRadio()
    await server.start()
    yield server
    await server.stop()


@pytest.fixture
async def vfo_radio(vfo_mock: VfoDualWatchMockRadio) -> AsyncGenerator[IcomRadio, None]:
    """IcomRadio connected to VfoDualWatchMockRadio, disconnected after test."""
    radio = IcomRadio(
        host="127.0.0.1",
        port=vfo_mock.control_port,
        username="testuser",
        password="testpass",
        timeout=5.0,
    )
    await radio.connect()
    yield radio
    await radio.disconnect()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_civ(
    to: int,
    frm: int,
    cmd: int,
    data: bytes = b"",
) -> bytes:
    """Build a minimal CI-V frame for unsolicited injection."""
    frame = bytearray(b"\xfe\xfe")
    frame.append(to)
    frame.append(frm)
    frame.append(cmd)
    frame.extend(data)
    frame.append(0xFD)
    return bytes(frame)


# ---------------------------------------------------------------------------
# 1. Tuning Step
# ---------------------------------------------------------------------------


class TestTuningStep:
    """Tuning step get/set roundtrip using BCD step index (1-11).

    The implementation stores step as a BCD-encoded index byte per IC-7610
    CI-V reference.  radio.set_tuning_step(n) / get_tuning_step() use the
    raw index, NOT Hz values.
    """

    async def test_tuning_step_roundtrip_index_1(
        self, vfo_radio: IcomRadio, vfo_mock: VfoDualWatchMockRadio
    ) -> None:
        """Set step index 1 (1Hz), verify GET returns 1 and mock state matches."""
        await vfo_radio.set_tuning_step(1)
        await asyncio.sleep(_SETTLE)
        step = await vfo_radio.get_tuning_step()
        assert step == 1
        assert vfo_mock._tuning_step == 0x01

    async def test_tuning_step_roundtrip_index_4(
        self, vfo_radio: IcomRadio, vfo_mock: VfoDualWatchMockRadio
    ) -> None:
        """Set step index 4 (1kHz per IC-7610 table), verify roundtrip."""
        await vfo_radio.set_tuning_step(4)
        await asyncio.sleep(_SETTLE)
        step = await vfo_radio.get_tuning_step()
        assert step == 4
        assert vfo_mock._tuning_step == 0x04

    async def test_tuning_step_roundtrip_index_7(
        self, vfo_radio: IcomRadio, vfo_mock: VfoDualWatchMockRadio
    ) -> None:
        """Set step index 7 (10kHz per IC-7610 table), verify roundtrip."""
        await vfo_radio.set_tuning_step(7)
        await asyncio.sleep(_SETTLE)
        step = await vfo_radio.get_tuning_step()
        assert step == 7
        assert vfo_mock._tuning_step == 0x07

    async def test_tuning_step_multiple_changes(
        self, vfo_radio: IcomRadio, vfo_mock: VfoDualWatchMockRadio
    ) -> None:
        """Step state persists across multiple SET → GET cycles."""
        for idx in (1, 3, 5, 8):
            await vfo_radio.set_tuning_step(idx)
            await asyncio.sleep(_SETTLE)
            got = await vfo_radio.get_tuning_step()
            assert got == idx, f"step mismatch for index {idx}"
            assert vfo_mock._tuning_step == idx

    async def test_tuning_step_default(
        self, vfo_radio: IcomRadio, vfo_mock: VfoDualWatchMockRadio
    ) -> None:
        """GET before any SET returns mock's initial default step index."""
        step = await vfo_radio.get_tuning_step()
        # Mock initialises to BCD index 4; implementation decodes as integer 4
        assert step == vfo_mock._tuning_step


# ---------------------------------------------------------------------------
# 2. Scanning
# ---------------------------------------------------------------------------


class TestScanning:
    """Scanning start/stop: state transitions and persistence."""

    async def test_scan_initial_state_is_stopped(
        self, vfo_mock: VfoDualWatchMockRadio
    ) -> None:
        """Mock starts with scanning=False (radio is not scanning at boot)."""
        assert vfo_mock._scanning is False

    async def test_scan_start(
        self, vfo_radio: IcomRadio, vfo_mock: VfoDualWatchMockRadio
    ) -> None:
        """start_scan() sets mock scanning state to True."""
        await vfo_radio.start_scan()
        await asyncio.sleep(_SETTLE)
        assert vfo_mock._scanning is True

    async def test_scan_stop(
        self, vfo_radio: IcomRadio, vfo_mock: VfoDualWatchMockRadio
    ) -> None:
        """stop_scan() clears mock scanning state."""
        await vfo_radio.start_scan()
        await asyncio.sleep(_SETTLE)
        assert vfo_mock._scanning is True

        await vfo_radio.stop_scan()
        await asyncio.sleep(_SETTLE)
        assert vfo_mock._scanning is False

    async def test_scan_start_stop_cycle(
        self, vfo_radio: IcomRadio, vfo_mock: VfoDualWatchMockRadio
    ) -> None:
        """Full start → stop → start → stop cycle verifies state at each step."""
        await vfo_radio.start_scan()
        await asyncio.sleep(_SETTLE)
        assert vfo_mock._scanning is True

        await vfo_radio.stop_scan()
        await asyncio.sleep(_SETTLE)
        assert vfo_mock._scanning is False

        await vfo_radio.start_scan()
        await asyncio.sleep(_SETTLE)
        assert vfo_mock._scanning is True

        await vfo_radio.stop_scan()
        await asyncio.sleep(_SETTLE)
        assert vfo_mock._scanning is False


# ---------------------------------------------------------------------------
# 3. Dual Watch
# ---------------------------------------------------------------------------


class TestDualWatch:
    """Dual watch on/off via mock state + unsolicited frame state path.

    set_dual_watch() is fire-and-forget — state is verified via mock's
    internal _dual_watch_on flag.  The CIV-RX unsolicited-push path
    (radio knob turn) is tested via inject_unsolicited_civ.
    """

    async def test_dual_watch_initial_state_off(
        self, vfo_mock: VfoDualWatchMockRadio
    ) -> None:
        """Mock starts with dual watch disabled."""
        assert vfo_mock._dual_watch_on is False

    async def test_dual_watch_turn_on(
        self, vfo_radio: IcomRadio, vfo_mock: VfoDualWatchMockRadio
    ) -> None:
        """set_dual_watch(True) → mock._dual_watch_on becomes True."""
        await vfo_radio.set_dual_watch(True)
        await asyncio.sleep(_SETTLE)
        assert vfo_mock._dual_watch_on is True

    async def test_dual_watch_turn_off(
        self, vfo_radio: IcomRadio, vfo_mock: VfoDualWatchMockRadio
    ) -> None:
        """set_dual_watch(False) after on → mock._dual_watch_on becomes False."""
        await vfo_radio.set_dual_watch(True)
        await asyncio.sleep(_SETTLE)
        assert vfo_mock._dual_watch_on is True

        await vfo_radio.set_dual_watch(False)
        await asyncio.sleep(_SETTLE)
        assert vfo_mock._dual_watch_on is False

    async def test_dual_watch_on_off_cycle(
        self, vfo_radio: IcomRadio, vfo_mock: VfoDualWatchMockRadio
    ) -> None:
        """Full off → on → off cycle verifies mock state at each step."""
        # Initially off
        assert vfo_mock._dual_watch_on is False

        await vfo_radio.set_dual_watch(True)
        await asyncio.sleep(_SETTLE)
        assert vfo_mock._dual_watch_on is True

        await vfo_radio.set_dual_watch(False)
        await asyncio.sleep(_SETTLE)
        assert vfo_mock._dual_watch_on is False

    async def test_dual_watch_idempotent_on(
        self, vfo_radio: IcomRadio, vfo_mock: VfoDualWatchMockRadio
    ) -> None:
        """Setting dual watch ON twice does not cause an error."""
        await vfo_radio.set_dual_watch(True)
        await asyncio.sleep(_SETTLE)
        await vfo_radio.set_dual_watch(True)
        await asyncio.sleep(_SETTLE)
        assert vfo_mock._dual_watch_on is True

    async def test_dual_watch_idempotent_off(
        self, vfo_radio: IcomRadio, vfo_mock: VfoDualWatchMockRadio
    ) -> None:
        """Setting dual watch OFF twice does not cause an error."""
        await vfo_radio.set_dual_watch(False)
        await asyncio.sleep(_SETTLE)
        await vfo_radio.set_dual_watch(False)
        await asyncio.sleep(_SETTLE)
        assert vfo_mock._dual_watch_on is False

    async def test_dual_watch_unsolicited_on_fires_event(
        self, vfo_radio: IcomRadio, vfo_mock: VfoDualWatchMockRadio
    ) -> None:
        """Unsolicited 0x07 0xC2 0x01 frame fires dual_watch_changed event."""
        events: list[tuple[str, dict]] = []
        vfo_radio._on_state_change = lambda name, data: events.append((name, data))  # type: ignore[assignment]

        # Inject as if the radio pushed an unsolicited dual-watch=ON update
        frame = _build_civ(
            _CONTROLLER_ADDR, _RADIO_ADDR, _CMD_VFO_SELECT, data=b"\xc2\x01"
        )
        vfo_mock.inject_unsolicited_civ(frame)
        await asyncio.sleep(0.15)

        assert any(name == "dual_watch_changed" for name, _ in events), (
            f"dual_watch_changed not fired; events={[n for n, _ in events]}"
        )
        matching = [d for n, d in events if n == "dual_watch_changed"]
        assert matching[0]["on"] is True

    async def test_dual_watch_unsolicited_off_fires_event(
        self, vfo_radio: IcomRadio, vfo_mock: VfoDualWatchMockRadio
    ) -> None:
        """Unsolicited 0x07 0xC2 0x00 frame fires dual_watch_changed event (off)."""
        events: list[tuple[str, dict]] = []
        vfo_radio._on_state_change = lambda name, data: events.append((name, data))  # type: ignore[assignment]

        # First inject ON to establish state, then OFF
        on_frame = _build_civ(
            _CONTROLLER_ADDR, _RADIO_ADDR, _CMD_VFO_SELECT, data=b"\xc2\x01"
        )
        vfo_mock.inject_unsolicited_civ(on_frame)
        await asyncio.sleep(0.1)

        events.clear()

        off_frame = _build_civ(
            _CONTROLLER_ADDR, _RADIO_ADDR, _CMD_VFO_SELECT, data=b"\xc2\x00"
        )
        vfo_mock.inject_unsolicited_civ(off_frame)
        await asyncio.sleep(0.15)

        assert any(name == "dual_watch_changed" for name, _ in events), (
            f"dual_watch_changed not fired; events={[n for n, _ in events]}"
        )
        matching = [d for n, d in events if n == "dual_watch_changed"]
        assert matching[0]["on"] is False


# ---------------------------------------------------------------------------
# 4. Quick Dual Watch
# ---------------------------------------------------------------------------


class TestQuickDualWatch:
    """Quick Dual Watch: fire-and-forget (no persistent state, no response)."""

    async def test_quick_dual_watch_no_exception(self, vfo_radio: IcomRadio) -> None:
        """quick_dual_watch() completes without raising."""
        await vfo_radio.quick_dual_watch()

    async def test_quick_dual_watch_multiple_calls(self, vfo_radio: IcomRadio) -> None:
        """Calling quick_dual_watch() repeatedly does not raise."""
        for _ in range(3):
            await vfo_radio.quick_dual_watch()
            await asyncio.sleep(0.02)


# ---------------------------------------------------------------------------
# 5. Quick Split
# ---------------------------------------------------------------------------


class TestQuickSplit:
    """Quick Split: fire-and-forget (no persistent state, no response)."""

    async def test_quick_split_no_exception(self, vfo_radio: IcomRadio) -> None:
        """quick_split() completes without raising."""
        await vfo_radio.quick_split()

    async def test_quick_split_multiple_calls(self, vfo_radio: IcomRadio) -> None:
        """Calling quick_split() repeatedly does not raise."""
        for _ in range(3):
            await vfo_radio.quick_split()
            await asyncio.sleep(0.02)


# ---------------------------------------------------------------------------
# Cross-command: independent state verification
# ---------------------------------------------------------------------------


class TestStateIndependence:
    """Verify that tuning step, scanning, and dual watch do not interfere."""

    async def test_independent_state(
        self, vfo_radio: IcomRadio, vfo_mock: VfoDualWatchMockRadio
    ) -> None:
        """Commands targeting different state variables stay independent."""
        await vfo_radio.set_tuning_step(3)
        await vfo_radio.set_dual_watch(True)
        await vfo_radio.start_scan()
        await asyncio.sleep(_SETTLE)

        assert vfo_mock._tuning_step == 0x03
        assert vfo_mock._dual_watch_on is True
        assert vfo_mock._scanning is True

        # Disable dual watch — step and scan unchanged
        await vfo_radio.set_dual_watch(False)
        await asyncio.sleep(_SETTLE)
        assert vfo_mock._tuning_step == 0x03
        assert vfo_mock._dual_watch_on is False
        assert vfo_mock._scanning is True

        # Stop scanning — step and dual watch unchanged
        await vfo_radio.stop_scan()
        await asyncio.sleep(_SETTLE)
        assert vfo_mock._tuning_step == 0x03
        assert vfo_mock._dual_watch_on is False
        assert vfo_mock._scanning is False

    async def test_quick_commands_do_not_affect_persistent_state(
        self, vfo_radio: IcomRadio, vfo_mock: VfoDualWatchMockRadio
    ) -> None:
        """quick_dual_watch / quick_split don't alter dual watch or scan state."""
        await vfo_radio.set_dual_watch(True)
        await vfo_radio.start_scan()
        await asyncio.sleep(_SETTLE)

        await vfo_radio.quick_dual_watch()
        await vfo_radio.quick_split()
        await asyncio.sleep(_SETTLE)

        # Persistent state must be unchanged by one-shot commands
        assert vfo_mock._dual_watch_on is True
        assert vfo_mock._scanning is True
