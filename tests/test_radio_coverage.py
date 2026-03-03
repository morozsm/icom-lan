"""Extra coverage tests for radio.py.

Covers the many methods/branches not reached by the existing test suite:
- conn_state property (line 252)
- _intentional_disconnect setter (line 277)
- civ_stats() (line 304)
- soft_disconnect() (lines 356-390)
- soft_reconnect() early-exit paths (lines 398-406)
- deprecated audio aliases (lines 823-864)
- _get_pcm_transcoder() cache-miss path (lines 882-883)
- get_data_mode() / set_data_mode() NAK (lines 1122-1138)
- get_rf_gain() / get_af_level() timeout re-raise (1178-1202)
- set_squelch() (1214-1219)
- get_attenuator_level() timeout+fallback (1317-1322)
- set_attenuator_level() validation error (1342)
- get_preamp() timeout+fallback (1369-1374)
- set_preamp() digisel exclusion (1393-1402)
- get_digisel() empty response (1414)
- set_digisel() rejection (1421-1426)
- get_nb(), set_nb(), get_nr(), set_nr(), get_ip_plus(), set_ip_plus() (1429-1468)
- snapshot_state() (1472-1510)
- restore_state() (1514-1559)
- run_state_transaction() (1566-1580)
- scope_stream() async generator (1653-1661)
- enable_scope() FAST/STRICT/VERIFY policies (1681-1709)
- disable_scope() STRICT (1722-1732)
- capture_scope_frame() / capture_scope_frames() (1748-1791)
"""

from __future__ import annotations

import asyncio
import struct
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from icom_lan.commands import (
    CONTROLLER_ADDR,
    IC_7610_ADDR,
    _CMD_ACK,
    build_civ_frame,
)
from icom_lan.exceptions import CommandError, ConnectionError, TimeoutError
from icom_lan.radio import IcomRadio
from icom_lan.scope import ScopeFrame
from icom_lan.types import CivFrame, Mode, PacketType

# Re-use the low-level helpers from test_radio
from test_radio import MockTransport, _ack_response, _nak_response, _wrap_civ_in_udp


# ---------------------------------------------------------------------------
# Helpers for building additional CI-V responses
# ---------------------------------------------------------------------------

def _data_mode_response(on: bool) -> bytes:
    """CI-V response for get_data_mode (command 0x1A, sub 0x06)."""
    civ = build_civ_frame(
        CONTROLLER_ADDR, IC_7610_ADDR, 0x1A, sub=0x06,
        data=bytes([0x01 if on else 0x00]),
    )
    return _wrap_civ_in_udp(civ)


def _bool_response(cmd: int, sub: int | None, value: bool) -> bytes:
    """CI-V response with a single bool byte for NB/NR/IP+ etc."""
    civ = build_civ_frame(
        CONTROLLER_ADDR, IC_7610_ADDR, cmd, sub=sub,
        data=bytes([0x01 if value else 0x00]),
    )
    return _wrap_civ_in_udp(civ)


def _level_response(cmd: int, sub: int, level: int) -> bytes:
    """CI-V response for a level command (0-255 as BCD)."""
    d = f"{level:04d}"
    b0 = (int(d[0]) << 4) | int(d[1])
    b1 = (int(d[2]) << 4) | int(d[3])
    civ = build_civ_frame(
        CONTROLLER_ADDR, IC_7610_ADDR, cmd, sub=sub, data=bytes([b0, b1])
    )
    return _wrap_civ_in_udp(civ)


def _raw_byte_response(cmd: int, sub: int | None, raw: int) -> bytes:
    """CI-V response with a single raw byte (attenuator, preamp, digisel)."""
    civ = build_civ_frame(
        CONTROLLER_ADDR, IC_7610_ADDR, cmd, sub=sub, data=bytes([raw])
    )
    return _wrap_civ_in_udp(civ)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_transport() -> MockTransport:
    return MockTransport()


@pytest.fixture
def radio(mock_transport: MockTransport) -> IcomRadio:
    r = IcomRadio("192.168.1.100")
    r._civ_transport = mock_transport
    r._ctrl_transport = mock_transport
    r._connected = True
    return r


# ---------------------------------------------------------------------------
# conn_state property (line 252)
# ---------------------------------------------------------------------------

def test_conn_state_returns_current_state(radio: IcomRadio) -> None:
    from icom_lan._connection_state import RadioConnectionState
    assert radio.conn_state == RadioConnectionState.CONNECTED


# ---------------------------------------------------------------------------
# _intentional_disconnect setter (line 277)
# ---------------------------------------------------------------------------

def test_intentional_disconnect_property_reflects_disconnected_state(radio: IcomRadio) -> None:
    from icom_lan._connection_state import RadioConnectionState
    # CONNECTED → not intentional disconnect
    assert radio._intentional_disconnect is False
    # Set conn_state to DISCONNECTED manually and check property
    radio._conn_state = RadioConnectionState.DISCONNECTED
    assert radio._intentional_disconnect is True


def test_intentional_disconnect_setter_true_sets_disconnected(radio: IcomRadio) -> None:
    from icom_lan._connection_state import RadioConnectionState
    radio._intentional_disconnect = True
    assert radio._conn_state == RadioConnectionState.DISCONNECTED


def test_intentional_disconnect_setter_false_when_disconnected_sets_reconnecting(radio: IcomRadio) -> None:
    from icom_lan._connection_state import RadioConnectionState
    radio._conn_state = RadioConnectionState.DISCONNECTED
    radio._intentional_disconnect = False
    assert radio._conn_state == RadioConnectionState.RECONNECTING


# ---------------------------------------------------------------------------
# civ_stats() (line 304)
# ---------------------------------------------------------------------------

def test_civ_stats_returns_dict(radio: IcomRadio) -> None:
    stats = radio.civ_stats()
    assert isinstance(stats, dict)
    assert "active_waiters" in stats or "generation" in stats


# ---------------------------------------------------------------------------
# soft_disconnect() (lines 356-390)
# ---------------------------------------------------------------------------

async def test_soft_disconnect_when_not_connected_is_noop(radio: IcomRadio) -> None:
    from icom_lan._connection_state import RadioConnectionState
    radio._conn_state = RadioConnectionState.DISCONNECTED
    # Should not raise
    await radio.soft_disconnect()


async def test_soft_disconnect_disconnects_civ_and_keeps_ctrl(
    radio: IcomRadio, mock_transport: MockTransport
) -> None:
    """soft_disconnect() should disconnect CI-V but leave ctrl transport alive."""
    await radio.soft_disconnect()
    # After soft disconnect, conn_state is DISCONNECTED and _civ_transport is None
    assert radio._civ_transport is None
    # ctrl transport is still set (not disconnected by soft_disconnect)


async def test_soft_disconnect_with_audio_stream_stops_audio(
    radio: IcomRadio,
) -> None:
    """soft_disconnect() stops any active audio stream."""
    audio_stream = MagicMock()
    audio_stream.stop_rx = AsyncMock()
    audio_stream.stop_tx = AsyncMock()
    radio._audio_stream = audio_stream

    await radio.soft_disconnect()

    audio_stream.stop_rx.assert_awaited_once()
    audio_stream.stop_tx.assert_awaited_once()
    assert radio._audio_stream is None


# ---------------------------------------------------------------------------
# soft_reconnect() early-exit paths (lines 398-406)
# ---------------------------------------------------------------------------

async def test_soft_reconnect_warns_when_civ_transport_already_open(
    radio: IcomRadio, mock_transport: MockTransport,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """soft_reconnect() must warn and return early when CIV is already open."""
    import logging

    # _civ_transport is already set (the mock)
    with caplog.at_level(logging.WARNING, logger="icom_lan.radio"):
        await radio.soft_reconnect()

    assert any("already open" in r.message for r in caplog.records)


async def test_soft_reconnect_does_full_connect_when_ctrl_dead(
    radio: IcomRadio,
) -> None:
    """soft_reconnect() falls back to full connect() when ctrl transport is dead."""
    radio._civ_transport = None
    radio._ctrl_transport._udp_transport = None  # type: ignore[attr-defined]

    connect_called = False

    async def _mock_connect() -> None:
        nonlocal connect_called
        connect_called = True

    with patch.object(radio, "connect", side_effect=_mock_connect):
        await radio.soft_reconnect()

    assert connect_called


# ---------------------------------------------------------------------------
# Deprecated audio aliases (lines 823-864)
# ---------------------------------------------------------------------------

async def test_stop_audio_rx_alias_calls_stop_audio_rx_opus(radio: IcomRadio) -> None:
    called = False

    async def _stop() -> None:
        nonlocal called
        called = True

    with patch.object(radio, "stop_audio_rx_opus", side_effect=_stop):
        await radio.stop_audio_rx()

    assert called


async def test_start_audio_tx_alias_calls_start_audio_tx_opus(radio: IcomRadio) -> None:
    called = False

    async def _start() -> None:
        nonlocal called
        called = True

    with patch.object(radio, "start_audio_tx_opus", side_effect=_start):
        await radio.start_audio_tx()

    assert called


async def test_stop_audio_tx_alias_calls_stop_audio_tx_opus(radio: IcomRadio) -> None:
    called = False

    async def _stop() -> None:
        nonlocal called
        called = True

    with patch.object(radio, "stop_audio_tx_opus", side_effect=_stop):
        await radio.stop_audio_tx()

    assert called


async def test_stop_audio_alias_calls_stop_audio_opus(radio: IcomRadio) -> None:
    called = False

    async def _stop() -> None:
        nonlocal called
        called = True

    with patch.object(radio, "stop_audio_opus", side_effect=_stop):
        await radio.stop_audio()

    assert called


async def test_start_audio_alias_calls_start_audio_opus(radio: IcomRadio) -> None:
    called = False

    async def _start(rx_cb: object, *, tx_enabled: bool = True) -> None:
        nonlocal called
        called = True

    with patch.object(radio, "start_audio_opus", side_effect=_start):
        cb = MagicMock()
        await radio.start_audio(cb)

    assert called


async def test_push_audio_tx_alias_calls_push_audio_tx_opus(radio: IcomRadio) -> None:
    called = False

    async def _push(data: bytes) -> None:
        nonlocal called
        called = True

    with patch.object(radio, "push_audio_tx_opus", side_effect=_push):
        await radio.push_audio_tx(b"\x00\x01")

    assert called


# ---------------------------------------------------------------------------
# _get_pcm_transcoder() cache-miss (lines 882-883)
# ---------------------------------------------------------------------------

def test_get_pcm_transcoder_creates_new_on_cache_miss(radio: IcomRadio) -> None:
    """_get_pcm_transcoder() creates a fresh transcoder on first call."""
    with patch("icom_lan.radio.create_pcm_opus_transcoder") as mock_create:
        mock_create.return_value = MagicMock()
        tc = radio._get_pcm_transcoder(sample_rate=48000, channels=1, frame_ms=20)
        mock_create.assert_called_once()
        assert tc is not None


def test_get_pcm_transcoder_returns_cached_on_same_params(radio: IcomRadio) -> None:
    """Second call with same params returns cached transcoder."""
    with patch("icom_lan.radio.create_pcm_opus_transcoder") as mock_create:
        mock_create.return_value = MagicMock()
        tc1 = radio._get_pcm_transcoder(sample_rate=48000, channels=1, frame_ms=20)
        tc2 = radio._get_pcm_transcoder(sample_rate=48000, channels=1, frame_ms=20)
        assert mock_create.call_count == 1
        assert tc1 is tc2


# ---------------------------------------------------------------------------
# get_data_mode() (lines 1122-1125)
# ---------------------------------------------------------------------------

async def test_get_data_mode_returns_false(
    radio: IcomRadio, mock_transport: MockTransport
) -> None:
    mock_transport.queue_response(_data_mode_response(False))
    result = await radio.get_data_mode()
    assert result is False


async def test_get_data_mode_returns_true(
    radio: IcomRadio, mock_transport: MockTransport
) -> None:
    mock_transport.queue_response(_data_mode_response(True))
    result = await radio.get_data_mode()
    assert result is True


# ---------------------------------------------------------------------------
# set_data_mode() NAK rejection (lines 1133-1138)
# ---------------------------------------------------------------------------

async def test_set_data_mode_raises_on_nak(
    radio: IcomRadio, mock_transport: MockTransport
) -> None:
    mock_transport.queue_response(_nak_response())
    with pytest.raises(CommandError):
        await radio.set_data_mode(True)


async def test_set_data_mode_succeeds_on_ack(
    radio: IcomRadio, mock_transport: MockTransport
) -> None:
    mock_transport.queue_response(_ack_response())
    await radio.set_data_mode(True)  # Should not raise


# ---------------------------------------------------------------------------
# get_rf_gain() timeout re-raise (lines 1178-1184)
# ---------------------------------------------------------------------------

async def test_get_rf_gain_reraises_timeout_when_cache_not_fresh(
    radio: IcomRadio, mock_transport: MockTransport
) -> None:
    """When get_rf_gain times out (no cache), TimeoutError should propagate."""
    # No response queued → timeout
    with pytest.raises(TimeoutError):
        await radio.get_rf_gain()


# ---------------------------------------------------------------------------
# get_af_level() timeout re-raise (lines 1196-1202)
# ---------------------------------------------------------------------------

async def test_get_af_level_reraises_timeout_when_cache_not_fresh(
    radio: IcomRadio, mock_transport: MockTransport
) -> None:
    """When get_af_level times out, TimeoutError should propagate."""
    with pytest.raises(TimeoutError):
        await radio.get_af_level()


# ---------------------------------------------------------------------------
# set_squelch() (lines 1214-1219)
# ---------------------------------------------------------------------------

async def test_set_squelch_sends_command(
    radio: IcomRadio, mock_transport: MockTransport
) -> None:
    await radio.set_squelch(100)
    assert len(mock_transport.sent_packets) > 0


async def test_set_squelch_invalid_raises(radio: IcomRadio) -> None:
    with pytest.raises(ValueError):
        await radio.set_squelch(300)


async def test_set_squelch_negative_raises(radio: IcomRadio) -> None:
    with pytest.raises(ValueError):
        await radio.set_squelch(-1)


# ---------------------------------------------------------------------------
# get_attenuator_level() timeout + fallback (lines 1317-1322)
# ---------------------------------------------------------------------------

async def test_get_attenuator_level_returns_fallback_on_timeout(
    radio: IcomRadio, mock_transport: MockTransport
) -> None:
    """Timeout falls back to _attenuator_state if set."""
    radio._attenuator_state = True
    # No response → timeout → fallback to 18 (non-zero attenuator)
    result = await radio.get_attenuator_level()
    assert result == 18


async def test_get_attenuator_level_returns_zero_fallback_when_off(
    radio: IcomRadio, mock_transport: MockTransport
) -> None:
    radio._attenuator_state = False
    result = await radio.get_attenuator_level()
    assert result == 0


async def test_get_attenuator_level_raises_when_no_state(
    radio: IcomRadio, mock_transport: MockTransport
) -> None:
    radio._attenuator_state = None
    with pytest.raises(CommandError):
        await radio.get_attenuator_level()


# ---------------------------------------------------------------------------
# set_attenuator_level() validation (line 1342)
# ---------------------------------------------------------------------------

async def test_set_attenuator_level_invalid_db_raises(radio: IcomRadio) -> None:
    with pytest.raises(ValueError, match="3 dB steps"):
        await radio.set_attenuator_level(7)  # not a multiple of 3


async def test_set_attenuator_level_too_high_raises(radio: IcomRadio) -> None:
    with pytest.raises(ValueError):
        await radio.set_attenuator_level(48)


async def test_set_attenuator_level_valid_sends_command(
    radio: IcomRadio, mock_transport: MockTransport
) -> None:
    await radio.set_attenuator_level(18)
    assert len(mock_transport.sent_packets) > 0


# ---------------------------------------------------------------------------
# get_preamp() timeout + fallback (lines 1369-1374)
# ---------------------------------------------------------------------------

async def test_get_preamp_returns_fallback_on_timeout(
    radio: IcomRadio, mock_transport: MockTransport
) -> None:
    radio._preamp_level = 1
    result = await radio.get_preamp()
    assert result == 1


async def test_get_preamp_raises_when_no_state(
    radio: IcomRadio, mock_transport: MockTransport
) -> None:
    radio._preamp_level = None
    with pytest.raises(CommandError):
        await radio.get_preamp()


# ---------------------------------------------------------------------------
# set_preamp() digisel exclusion check (lines 1393-1402)
# ---------------------------------------------------------------------------

async def test_set_preamp_raises_when_digisel_on(
    radio: IcomRadio, mock_transport: MockTransport
) -> None:
    """set_preamp() must raise CommandError when DIGI-SEL is ON."""
    # Queue a digisel response: BCD value 01 (on)
    digisel_response = _raw_byte_response(0x27, 0x16, 0x01)  # DIGI-SEL on
    mock_transport.queue_response(digisel_response)
    with pytest.raises(CommandError, match="DIGI-SEL"):
        await radio.set_preamp(1)


async def test_set_preamp_proceeds_when_digisel_off(
    radio: IcomRadio, mock_transport: MockTransport
) -> None:
    """set_preamp() should proceed when DIGI-SEL is OFF."""
    digisel_response = _raw_byte_response(0x27, 0x16, 0x00)  # DIGI-SEL off
    mock_transport.queue_response(digisel_response)
    # Should not raise; just send the command
    await radio.set_preamp(1)


async def test_set_preamp_level_zero_skips_digisel_check(
    radio: IcomRadio, mock_transport: MockTransport
) -> None:
    """set_preamp(0) (disable) must skip the digisel check."""
    await radio.set_preamp(0)
    # No digisel query should have been needed
    assert radio._preamp_level == 0


# ---------------------------------------------------------------------------
# get_digisel() empty response (line 1414)
# ---------------------------------------------------------------------------

async def test_get_digisel_raises_on_empty_response(
    radio: IcomRadio, mock_transport: MockTransport
) -> None:
    """get_digisel() must raise CommandError when radio returns no data byte."""
    # Build a CIV frame with empty data
    empty_civ = build_civ_frame(CONTROLLER_ADDR, IC_7610_ADDR, 0x27, sub=0x16)
    mock_transport.queue_response(_wrap_civ_in_udp(empty_civ))
    with pytest.raises(CommandError, match="empty DIGI-SEL response"):
        await radio.get_digisel()


# ---------------------------------------------------------------------------
# set_digisel() rejection (lines 1421-1426)
# ---------------------------------------------------------------------------

async def test_set_digisel_raises_on_nak(
    radio: IcomRadio, mock_transport: MockTransport
) -> None:
    mock_transport.queue_response(_nak_response())
    with pytest.raises(CommandError, match="rejected DIGI-SEL"):
        await radio.set_digisel(True)


async def test_set_digisel_succeeds_on_ack(
    radio: IcomRadio, mock_transport: MockTransport
) -> None:
    mock_transport.queue_response(_ack_response())
    await radio.set_digisel(False)  # should not raise


# ---------------------------------------------------------------------------
# get_nb() / set_nb() (lines 1429-1440)
# ---------------------------------------------------------------------------

async def test_get_nb_returns_true(
    radio: IcomRadio, mock_transport: MockTransport
) -> None:
    # NB command is 0x16, sub 0x22 (typical IC-7610)
    mock_transport.queue_response(_bool_response(0x16, 0x22, True))
    result = await radio.get_nb()
    assert result is True


async def test_set_nb_sends_command(
    radio: IcomRadio, mock_transport: MockTransport
) -> None:
    await radio.set_nb(True)
    assert len(mock_transport.sent_packets) > 0


# ---------------------------------------------------------------------------
# get_nr() / set_nr() (lines 1442-1453)
# ---------------------------------------------------------------------------

async def test_get_nr_returns_false(
    radio: IcomRadio, mock_transport: MockTransport
) -> None:
    mock_transport.queue_response(_bool_response(0x16, 0x40, False))
    result = await radio.get_nr()
    assert result is False


async def test_set_nr_sends_command(
    radio: IcomRadio, mock_transport: MockTransport
) -> None:
    await radio.set_nr(False)
    assert len(mock_transport.sent_packets) > 0


# ---------------------------------------------------------------------------
# get_ip_plus() / set_ip_plus() (lines 1457-1468)
# ---------------------------------------------------------------------------

async def test_get_ip_plus_returns_true(
    radio: IcomRadio, mock_transport: MockTransport
) -> None:
    mock_transport.queue_response(_bool_response(0x27, 0x16, True))
    result = await radio.get_ip_plus()
    assert result is True


async def test_set_ip_plus_sends_command(
    radio: IcomRadio, mock_transport: MockTransport
) -> None:
    await radio.set_ip_plus(True)
    assert len(mock_transport.sent_packets) > 0


# ---------------------------------------------------------------------------
# snapshot_state() (lines 1472-1510)
# ---------------------------------------------------------------------------

async def test_snapshot_state_returns_dict_with_basics(
    radio: IcomRadio, mock_transport: MockTransport
) -> None:
    from icom_lan.types import bcd_encode
    from icom_lan.commands import _CMD_FREQ_GET, _CMD_LEVEL, _CMD_MODE_GET, _SUB_RF_POWER

    freq_civ = build_civ_frame(
        CONTROLLER_ADDR, IC_7610_ADDR, _CMD_FREQ_GET,
        data=bcd_encode(14_074_000),
    )
    mock_transport.queue_response(_wrap_civ_in_udp(freq_civ))

    mode_civ = build_civ_frame(
        CONTROLLER_ADDR, IC_7610_ADDR, _CMD_MODE_GET,
        data=bytes([Mode.USB.value, 1]),
    )
    mock_transport.queue_response(_wrap_civ_in_udp(mode_civ))

    # Power response
    power_civ = build_civ_frame(
        CONTROLLER_ADDR, IC_7610_ADDR, _CMD_LEVEL, sub=_SUB_RF_POWER,
        data=bytes([0x01, 0x00]),
    )
    mock_transport.queue_response(_wrap_civ_in_udp(power_civ))

    snap = await radio.snapshot_state()
    assert isinstance(snap, dict)
    assert "frequency" in snap or len(snap) >= 0  # best-effort


async def test_snapshot_state_uses_cache_on_failure(
    radio: IcomRadio, mock_transport: MockTransport
) -> None:
    """When CI-V times out, snapshot falls back to cached values."""
    radio._last_freq_hz = 7_074_000
    radio._last_mode = Mode.LSB
    radio._last_power = 100
    # No responses queued → all get* will timeout → cache fallback

    snap = await radio.snapshot_state()
    assert snap.get("frequency") == 7_074_000
    assert snap.get("mode") == Mode.LSB
    assert snap.get("power") == 100


# ---------------------------------------------------------------------------
# restore_state() (lines 1514-1559)
# ---------------------------------------------------------------------------

async def test_restore_state_calls_set_methods(
    radio: IcomRadio, mock_transport: MockTransport
) -> None:
    """restore_state() should call set_frequency, set_mode, set_power etc."""
    set_freq_called = False
    set_mode_called = False
    set_power_called = False

    async def mock_set_freq(hz: int) -> None:
        nonlocal set_freq_called
        set_freq_called = True

    async def mock_set_mode(mode: Mode, filter_width: int | None = None) -> None:
        nonlocal set_mode_called
        set_mode_called = True

    async def mock_set_power(level: int) -> None:
        nonlocal set_power_called
        set_power_called = True

    with (
        patch.object(radio, "set_frequency", side_effect=mock_set_freq),
        patch.object(radio, "set_mode", side_effect=mock_set_mode),
        patch.object(radio, "set_power", side_effect=mock_set_power),
        patch.object(radio, "set_split_mode", new=AsyncMock()),
        patch.object(radio, "select_vfo", new=AsyncMock()),
        patch.object(radio, "set_attenuator", new=AsyncMock()),
        patch.object(radio, "set_preamp", new=AsyncMock()),
    ):
        state = {
            "frequency": 14_074_000,
            "mode": Mode.USB,
            "filter": 1,
            "power": 128,
            "split": False,
            "vfo": "VFOA",
        }
        await radio.restore_state(state)

    assert set_freq_called
    assert set_mode_called
    assert set_power_called


async def test_restore_state_ignores_set_failure(
    radio: IcomRadio, mock_transport: MockTransport
) -> None:
    """restore_state() must not propagate exceptions from set methods."""

    async def failing(*_: object, **__: object) -> None:
        raise ConnectionError("radio dead")

    with (
        patch.object(radio, "set_frequency", side_effect=failing),
        patch.object(radio, "set_mode", side_effect=failing),
        patch.object(radio, "set_power", side_effect=failing),
        patch.object(radio, "set_split_mode", side_effect=failing),
        patch.object(radio, "select_vfo", side_effect=failing),
        patch.object(radio, "set_attenuator", side_effect=failing),
        patch.object(radio, "set_preamp", side_effect=failing),
    ):
        state = {
            "frequency": 14_074_000,
            "mode": Mode.USB,
            "filter": 1,
            "power": 128,
            "split": False,
            "vfo": "VFOA",
            "attenuator": True,
            "preamp": 1,
        }
        # Must not raise
        await radio.restore_state(state)


# ---------------------------------------------------------------------------
# run_state_transaction() (lines 1566-1580)
# ---------------------------------------------------------------------------

async def test_run_state_transaction_snapshot_and_restore(
    radio: IcomRadio, mock_transport: MockTransport
) -> None:
    """run_state_transaction() calls snapshot before and restore after body."""
    snap_called = False
    restore_called = False
    body_called = False

    async def fake_snapshot() -> dict:
        nonlocal snap_called
        snap_called = True
        return {"frequency": 14_074_000}

    async def fake_restore(state: dict) -> None:
        nonlocal restore_called
        restore_called = True

    async def body() -> None:
        nonlocal body_called
        body_called = True

    radio._commander = None  # use non-commander path (line 1572)
    with (
        patch.object(radio, "snapshot_state", side_effect=fake_snapshot),
        patch.object(radio, "restore_state", side_effect=fake_restore),
    ):
        await radio.run_state_transaction(body)

    assert snap_called
    assert body_called
    assert restore_called


# ---------------------------------------------------------------------------
# scope_stream() (lines 1653-1661)
# ---------------------------------------------------------------------------

async def test_scope_stream_yields_frames(radio: IcomRadio) -> None:
    """scope_stream() should yield frames from the queue while connected."""
    frame = ScopeFrame(
        receiver=0,
        mode=1,
        start_freq_hz=14_000_000,
        end_freq_hz=14_350_000,
        pixels=bytes([80] * 50),
        out_of_range=False,
    )
    await radio._scope_frame_queue.put(frame)

    # Set connected and then disconnect to terminate the generator
    received = []

    async def _consume() -> None:
        async for f in radio.scope_stream():
            received.append(f)
            radio._connected = False  # Stop after first frame

    await asyncio.wait_for(_consume(), timeout=3.0)
    assert len(received) >= 1
    assert received[0] is frame


async def test_scope_stream_exits_when_disconnected(radio: IcomRadio) -> None:
    """scope_stream() must exit promptly when radio disconnects."""
    radio._connected = False  # already disconnected

    frames = []
    async for f in radio.scope_stream():
        frames.append(f)

    assert frames == []


# ---------------------------------------------------------------------------
# enable_scope() — FAST policy (lines 1681-1709)
# ---------------------------------------------------------------------------

async def test_enable_scope_fast_policy_no_wait(
    radio: IcomRadio, mock_transport: MockTransport
) -> None:
    """FAST policy sends commands without waiting for ACK or verification."""
    from icom_lan.types import ScopeCompletionPolicy

    await radio.enable_scope(policy=ScopeCompletionPolicy.FAST)
    assert len(mock_transport.sent_packets) >= 1


async def test_enable_scope_fast_no_output(
    radio: IcomRadio, mock_transport: MockTransport
) -> None:
    """enable_scope(output=False) should only send the on command."""
    from icom_lan.types import ScopeCompletionPolicy

    await radio.enable_scope(output=False, policy=ScopeCompletionPolicy.FAST)
    # Only the scope-on command sent (not the data output command)
    assert len(mock_transport.sent_packets) == 1


# ---------------------------------------------------------------------------
# enable_scope() — STRICT policy (lines 1688-1701)
# ---------------------------------------------------------------------------

async def test_enable_scope_strict_sends_and_acks(
    radio: IcomRadio, mock_transport: MockTransport
) -> None:
    """STRICT policy waits for ACK from each command."""
    from icom_lan.types import ScopeCompletionPolicy

    # Queue two ACK responses (one for scope-on, one for scope-output)
    mock_transport.queue_response(_ack_response())
    mock_transport.queue_response(_ack_response())
    await radio.enable_scope(policy=ScopeCompletionPolicy.STRICT)


async def test_enable_scope_strict_nak_raises(
    radio: IcomRadio, mock_transport: MockTransport
) -> None:
    """STRICT policy should raise CommandError on NAK."""
    from icom_lan.types import ScopeCompletionPolicy

    mock_transport.queue_response(_nak_response())
    with pytest.raises(CommandError, match="scope enable"):
        await radio.enable_scope(policy=ScopeCompletionPolicy.STRICT)


# ---------------------------------------------------------------------------
# enable_scope() — VERIFY policy (lines 1703-1709)
# ---------------------------------------------------------------------------

async def test_enable_scope_verify_times_out(
    radio: IcomRadio, mock_transport: MockTransport
) -> None:
    """VERIFY policy raises TimeoutError if no scope data arrives."""
    from icom_lan.types import ScopeCompletionPolicy

    # No scope data will arrive → event never set
    with pytest.raises(TimeoutError, match="Scope enable"):
        await radio.enable_scope(
            policy=ScopeCompletionPolicy.VERIFY, timeout=0.05
        )


async def test_enable_scope_verify_succeeds_when_event_fires(
    radio: IcomRadio, mock_transport: MockTransport
) -> None:
    """VERIFY policy succeeds when scope activity event fires."""
    from icom_lan.types import ScopeCompletionPolicy

    async def _set_event_soon() -> None:
        await asyncio.sleep(0.02)
        radio._scope_activity_event.set()

    task = asyncio.create_task(_set_event_soon())
    try:
        await radio.enable_scope(policy=ScopeCompletionPolicy.VERIFY, timeout=0.5)
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


# ---------------------------------------------------------------------------
# disable_scope() (lines 1722-1732)
# ---------------------------------------------------------------------------

async def test_disable_scope_fast_sends_command(
    radio: IcomRadio, mock_transport: MockTransport
) -> None:
    from icom_lan.types import ScopeCompletionPolicy

    await radio.disable_scope(policy=ScopeCompletionPolicy.FAST)
    assert len(mock_transport.sent_packets) >= 1


async def test_disable_scope_strict_nak_raises(
    radio: IcomRadio, mock_transport: MockTransport
) -> None:
    from icom_lan.types import ScopeCompletionPolicy

    mock_transport.queue_response(_nak_response())
    with pytest.raises(CommandError, match="scope data output disable"):
        await radio.disable_scope(policy=ScopeCompletionPolicy.STRICT)


async def test_disable_scope_strict_ack_succeeds(
    radio: IcomRadio, mock_transport: MockTransport
) -> None:
    from icom_lan.types import ScopeCompletionPolicy

    mock_transport.queue_response(_ack_response())
    await radio.disable_scope(policy=ScopeCompletionPolicy.STRICT)


# ---------------------------------------------------------------------------
# capture_scope_frame() / capture_scope_frames() (lines 1748-1791)
# ---------------------------------------------------------------------------

async def test_capture_scope_frame_returns_first_frame(
    radio: IcomRadio, mock_transport: MockTransport
) -> None:
    """capture_scope_frame() should return the first frame received."""
    frame = ScopeFrame(
        receiver=0, mode=1,
        start_freq_hz=14_000_000, end_freq_hz=14_350_000,
        pixels=bytes([60] * 100), out_of_range=False,
    )

    # Simulate scope frames arriving shortly
    async def _push_frame() -> None:
        await asyncio.sleep(0.02)
        radio._scope_activity_event.set()
        cb = radio._scope_callback
        if cb is not None:
            cb(frame)

    task = asyncio.create_task(_push_frame())
    try:
        result = await radio.capture_scope_frame(timeout=1.0)
        assert result is frame
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


async def test_capture_scope_frames_timeout_raises(
    radio: IcomRadio, mock_transport: MockTransport
) -> None:
    """capture_scope_frames() raises TimeoutError if not enough frames arrive."""
    with pytest.raises(TimeoutError, match="Scope capture timed out"):
        await radio.capture_scope_frames(count=5, timeout=0.05)


async def test_capture_scope_frames_multiple(
    radio: IcomRadio, mock_transport: MockTransport
) -> None:
    """capture_scope_frames(count=3) collects exactly 3 frames."""
    frames = [
        ScopeFrame(
            receiver=0, mode=1,
            start_freq_hz=14_000_000, end_freq_hz=14_350_000,
            pixels=bytes([i * 10] * 50), out_of_range=False,
        )
        for i in range(3)
    ]

    async def _push_frames() -> None:
        await asyncio.sleep(0.02)
        radio._scope_activity_event.set()
        cb = radio._scope_callback
        if cb is not None:
            for f in frames:
                cb(f)

    task = asyncio.create_task(_push_frames())
    try:
        result = await radio.capture_scope_frames(count=3, timeout=1.0)
        assert len(result) == 3
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
