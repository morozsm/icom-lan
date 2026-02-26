"""Tests for RigctldHandler — command dispatch, cache, read-only, exceptions."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, patch

import pytest

from icom_lan.exceptions import (
    ConnectionError as IcomConnectionError,
    TimeoutError as IcomTimeoutError,
)
from icom_lan.rigctld.contract import (
    HamlibError,
    RigctldCommand,
    RigctldConfig,
    RigctldResponse,
)
from icom_lan.rigctld.handler import RigctldHandler
from icom_lan.types import Mode


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def config() -> RigctldConfig:
    return RigctldConfig()


@pytest.fixture
def mock_radio() -> AsyncMock:
    radio = AsyncMock()
    radio.get_data_mode.return_value = False
    return radio


@pytest.fixture
def handler(mock_radio: AsyncMock, config: RigctldConfig) -> RigctldHandler:
    return RigctldHandler(mock_radio, config)


def get_cmd(long_cmd: str, *args: str) -> RigctldCommand:
    return RigctldCommand(short_cmd="", long_cmd=long_cmd, args=tuple(args), is_set=False)


def set_cmd(long_cmd: str, *args: str) -> RigctldCommand:
    return RigctldCommand(short_cmd="", long_cmd=long_cmd, args=tuple(args), is_set=True)


# ---------------------------------------------------------------------------
# get_freq / set_freq
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_freq_returns_frequency(handler: RigctldHandler, mock_radio: AsyncMock) -> None:
    mock_radio.get_frequency.return_value = 14_074_000
    resp = await handler.execute(get_cmd("get_freq"))
    assert resp.ok
    assert resp.values == ["14074000"]
    mock_radio.get_frequency.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_freq_served_from_cache(handler: RigctldHandler, mock_radio: AsyncMock) -> None:
    mock_radio.get_frequency.return_value = 14_074_000
    cmd = get_cmd("get_freq")
    resp1 = await handler.execute(cmd)
    resp2 = await handler.execute(cmd)
    assert resp1.values == resp2.values
    mock_radio.get_frequency.assert_awaited_once()  # only one real call


@pytest.mark.asyncio
async def test_get_freq_cache_expires(mock_radio: AsyncMock) -> None:
    config = RigctldConfig(cache_ttl=0.0)  # zero TTL → always expired
    h = RigctldHandler(mock_radio, config)
    mock_radio.get_frequency.side_effect = [14_074_000, 7_050_000]
    cmd = get_cmd("get_freq")
    r1 = await h.execute(cmd)
    r2 = await h.execute(cmd)
    assert r1.values == ["14074000"]
    assert r2.values == ["7050000"]
    assert mock_radio.get_frequency.await_count == 2


@pytest.mark.asyncio
async def test_set_freq_calls_radio(handler: RigctldHandler, mock_radio: AsyncMock) -> None:
    resp = await handler.execute(set_cmd("set_freq", "14074000"))
    assert resp.ok
    mock_radio.set_frequency.assert_awaited_once_with(14_074_000)


@pytest.mark.asyncio
async def test_set_freq_invalidates_cache(handler: RigctldHandler, mock_radio: AsyncMock) -> None:
    mock_radio.get_frequency.return_value = 14_074_000
    await handler.execute(get_cmd("get_freq"))  # populate cache

    mock_radio.get_frequency.return_value = 7_050_000
    await handler.execute(set_cmd("set_freq", "7050000"))  # invalidate

    resp = await handler.execute(get_cmd("get_freq"))  # re-fetch
    assert resp.values == ["7050000"]
    assert mock_radio.get_frequency.await_count == 2


@pytest.mark.asyncio
async def test_set_freq_invalid_arg(handler: RigctldHandler, mock_radio: AsyncMock) -> None:
    resp = await handler.execute(set_cmd("set_freq", "not_a_number"))
    assert resp.error == HamlibError.EINVAL
    mock_radio.set_frequency.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_freq_no_args(handler: RigctldHandler, mock_radio: AsyncMock) -> None:
    resp = await handler.execute(set_cmd("set_freq"))
    assert resp.error == HamlibError.EINVAL


# ---------------------------------------------------------------------------
# get_mode / set_mode
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_mode_returns_mode_and_passband(handler: RigctldHandler, mock_radio: AsyncMock) -> None:
    mock_radio.get_mode_info.return_value = (Mode.USB, 2)
    resp = await handler.execute(get_cmd("get_mode"))
    assert resp.ok
    assert resp.values[0] == "USB"
    assert resp.values[1] == "2400"  # FIL2 → 2400 Hz


@pytest.mark.asyncio
async def test_get_mode_none_filter_returns_zero_passband(
    handler: RigctldHandler, mock_radio: AsyncMock
) -> None:
    mock_radio.get_mode_info.return_value = (Mode.CW, None)
    resp = await handler.execute(get_cmd("get_mode"))
    assert resp.values[0] == "CW"
    assert resp.values[1] == "0"


@pytest.mark.asyncio
async def test_get_mode_served_from_cache(handler: RigctldHandler, mock_radio: AsyncMock) -> None:
    mock_radio.get_mode_info.return_value = (Mode.USB, 1)
    cmd = get_cmd("get_mode")
    await handler.execute(cmd)
    await handler.execute(cmd)
    mock_radio.get_mode_info.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_mode_cache_expires(mock_radio: AsyncMock) -> None:
    config = RigctldConfig(cache_ttl=0.0)
    h = RigctldHandler(mock_radio, config)
    mock_radio.get_mode_info.side_effect = [(Mode.USB, 1), (Mode.LSB, 1)]
    await h.execute(get_cmd("get_mode"))
    await h.execute(get_cmd("get_mode"))
    assert mock_radio.get_mode_info.await_count == 2


@pytest.mark.asyncio
async def test_set_mode_calls_radio(handler: RigctldHandler, mock_radio: AsyncMock) -> None:
    resp = await handler.execute(set_cmd("set_mode", "USB", "2400"))
    assert resp.ok
    mock_radio.set_mode.assert_awaited_once_with(Mode.USB, filter_width=2)


@pytest.mark.asyncio
async def test_set_mode_without_passband_uses_none_filter(
    handler: RigctldHandler, mock_radio: AsyncMock
) -> None:
    resp = await handler.execute(set_cmd("set_mode", "LSB"))
    assert resp.ok
    mock_radio.set_mode.assert_awaited_once_with(Mode.LSB, filter_width=None)


@pytest.mark.asyncio
async def test_set_mode_non_packet_does_not_force_data_change(
    handler: RigctldHandler, mock_radio: AsyncMock
) -> None:
    resp = await handler.execute(set_cmd("set_mode", "LSB"))
    assert resp.ok
    mock_radio.set_data_mode.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_mode_passband_zero_uses_none_filter(
    handler: RigctldHandler, mock_radio: AsyncMock
) -> None:
    resp = await handler.execute(set_cmd("set_mode", "FM", "0"))
    assert resp.ok
    mock_radio.set_mode.assert_awaited_once_with(Mode.FM, filter_width=None)


@pytest.mark.asyncio
async def test_set_mode_pktrtty_maps_to_rtty_and_sets_data(
    handler: RigctldHandler, mock_radio: AsyncMock
) -> None:
    resp = await handler.execute(set_cmd("set_mode", "PKTRTTY"))
    assert resp.ok
    mock_radio.set_mode.assert_awaited_once_with(Mode.RTTY, filter_width=None)
    mock_radio.set_data_mode.assert_awaited_once_with(True)


@pytest.mark.asyncio
async def test_set_mode_invalid_mode(handler: RigctldHandler, mock_radio: AsyncMock) -> None:
    resp = await handler.execute(set_cmd("set_mode", "INVALID"))
    assert resp.error == HamlibError.EINVAL
    mock_radio.set_mode.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_mode_refreshes_cache_immediately(
    handler: RigctldHandler, mock_radio: AsyncMock
) -> None:
    mock_radio.get_mode_info.return_value = (Mode.USB, 1)
    await handler.execute(get_cmd("get_mode"))  # populate from radio

    await handler.execute(set_cmd("set_mode", "LSB"))  # updates cache directly

    resp = await handler.execute(get_cmd("get_mode"))
    assert resp.values[0] == "LSB"
    # No extra radio read needed after set_mode.
    assert mock_radio.get_mode_info.await_count == 1


# ---------------------------------------------------------------------------
# get_ptt / set_ptt
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_ptt_defaults_off(handler: RigctldHandler, mock_radio: AsyncMock) -> None:
    resp = await handler.execute(get_cmd("get_ptt"))
    assert resp.ok
    assert resp.values == ["0"]


@pytest.mark.asyncio
async def test_set_ptt_on(handler: RigctldHandler, mock_radio: AsyncMock) -> None:
    resp = await handler.execute(set_cmd("set_ptt", "1"))
    assert resp.ok
    mock_radio.set_ptt.assert_awaited_once_with(True)


@pytest.mark.asyncio
async def test_set_ptt_off(handler: RigctldHandler, mock_radio: AsyncMock) -> None:
    await handler.execute(set_cmd("set_ptt", "1"))
    resp = await handler.execute(set_cmd("set_ptt", "0"))
    assert resp.ok
    mock_radio.set_ptt.assert_awaited_with(False)


@pytest.mark.asyncio
async def test_ptt_state_reflected_in_get(handler: RigctldHandler, mock_radio: AsyncMock) -> None:
    await handler.execute(set_cmd("set_ptt", "1"))
    resp = await handler.execute(get_cmd("get_ptt"))
    assert resp.values == ["1"]

    await handler.execute(set_cmd("set_ptt", "0"))
    resp = await handler.execute(get_cmd("get_ptt"))
    assert resp.values == ["0"]


@pytest.mark.asyncio
async def test_set_ptt_invalid_arg(handler: RigctldHandler, mock_radio: AsyncMock) -> None:
    resp = await handler.execute(set_cmd("set_ptt", "x"))
    assert resp.error == HamlibError.EINVAL


# ---------------------------------------------------------------------------
# get_vfo / set_vfo
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_vfo_returns_vfoa(handler: RigctldHandler, mock_radio: AsyncMock) -> None:
    resp = await handler.execute(get_cmd("get_vfo"))
    assert resp.ok
    assert resp.values == ["VFOA"]


@pytest.mark.asyncio
async def test_set_vfo_accepts_any_name(handler: RigctldHandler, mock_radio: AsyncMock) -> None:
    resp = await handler.execute(set_cmd("set_vfo", "VFOB"))
    assert resp.ok


# ---------------------------------------------------------------------------
# get_level
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_level_strength(handler: RigctldHandler, mock_radio: AsyncMock) -> None:
    mock_radio.get_s_meter.return_value = 120  # ≈ S9 → 0 dB
    resp = await handler.execute(get_cmd("get_level", "STRENGTH"))
    assert resp.ok
    strength = int(resp.values[0])
    assert -60 <= strength <= 70  # reasonable dB range


@pytest.mark.asyncio
async def test_get_level_strength_s0(handler: RigctldHandler, mock_radio: AsyncMock) -> None:
    mock_radio.get_s_meter.return_value = 0
    resp = await handler.execute(get_cmd("get_level", "STRENGTH"))
    assert resp.ok
    assert int(resp.values[0]) == -54


@pytest.mark.asyncio
async def test_get_level_rfpower(handler: RigctldHandler, mock_radio: AsyncMock) -> None:
    mock_radio.get_power.return_value = 255
    resp = await handler.execute(get_cmd("get_level", "RFPOWER"))
    assert resp.ok
    value = float(resp.values[0])
    assert abs(value - 1.0) < 0.001


@pytest.mark.asyncio
async def test_get_level_rfpower_zero(handler: RigctldHandler, mock_radio: AsyncMock) -> None:
    mock_radio.get_power.return_value = 0
    resp = await handler.execute(get_cmd("get_level", "RFPOWER"))
    assert resp.ok
    assert float(resp.values[0]) == pytest.approx(0.0)


@pytest.mark.asyncio
async def test_get_level_swr(handler: RigctldHandler, mock_radio: AsyncMock) -> None:
    mock_radio.get_swr.return_value = 0
    resp = await handler.execute(get_cmd("get_level", "SWR"))
    assert resp.ok
    assert float(resp.values[0]) == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_get_level_swr_max(handler: RigctldHandler, mock_radio: AsyncMock) -> None:
    mock_radio.get_swr.return_value = 255
    resp = await handler.execute(get_cmd("get_level", "SWR"))
    assert resp.ok
    assert float(resp.values[0]) == pytest.approx(5.0)


@pytest.mark.asyncio
async def test_get_level_no_args(handler: RigctldHandler, mock_radio: AsyncMock) -> None:
    resp = await handler.execute(get_cmd("get_level"))
    assert resp.error == HamlibError.EINVAL


@pytest.mark.asyncio
async def test_get_level_unknown(handler: RigctldHandler, mock_radio: AsyncMock) -> None:
    resp = await handler.execute(get_cmd("get_level", "NOSUCHLEVEL"))
    assert resp.error == HamlibError.EINVAL


# ---------------------------------------------------------------------------
# get_split_vfo / set_split_vfo
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_split_vfo(handler: RigctldHandler, mock_radio: AsyncMock) -> None:
    resp = await handler.execute(get_cmd("get_split_vfo"))
    assert resp.ok
    assert resp.values[0] == "0"
    assert resp.values[1] == "VFOA"


@pytest.mark.asyncio
async def test_set_split_vfo(handler: RigctldHandler, mock_radio: AsyncMock) -> None:
    resp = await handler.execute(set_cmd("set_split_vfo", "0", "VFOA"))
    assert resp.ok


# ---------------------------------------------------------------------------
# Info / control commands
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dump_state(handler: RigctldHandler, mock_radio: AsyncMock) -> None:
    resp = await handler.execute(get_cmd("dump_state"))
    assert resp.ok
    lines = resp.values

    # Line 0: protocol version (atol parseable)
    assert lines[0] == "0"
    # Line 1: rig model — IC-7610 hamlib model number
    assert lines[1] == "3078"
    # Line 2: ITU region
    assert lines[2] == "1"
    # Line 3: RX range (7 fields: startf endf modes low_power high_power vfo ant)
    assert lines[3] == "100000.000000 60000000.000000 0x1ff -1 -1 0x3 0xf"
    # Line 4: end of RX ranges sentinel
    assert lines[4] == "0 0 0 0 0 0 0"
    # Line 5: TX range
    assert lines[5] == "1800000.000000 60000000.000000 0x1ff 5000 100000 0x3 0xf"
    # Line 6: end of TX ranges sentinel
    assert lines[6] == "0 0 0 0 0 0 0"
    # Line 7: tuning step (modes ts)
    assert lines[7] == "0x1ff 1"
    # Line 8: end of tuning steps sentinel
    assert lines[8] == "0 0"
    # Lines 9-11: filters (modes width)
    assert lines[9] == "0x1ff 3000"
    assert lines[10] == "0x1ff 2400"
    assert lines[11] == "0x1ff 1800"
    # Line 12: end of filters sentinel
    assert lines[12] == "0 0"
    # Lines 13-16: bare scalars — no 'key: value' prefix
    assert lines[13] == "0"   # max_rit
    assert lines[14] == "0"   # max_xit
    assert lines[15] == "0"   # max_ifshift
    assert lines[16] == "0"   # announces
    # Lines 17-18: preamp/attenuator — space-separated ints, 0-terminated
    assert lines[17] == "12 20 0"
    assert lines[18] == "6 12 18 0"
    # Lines 19-24: capability bitmasks — bare hex/int, no label prefix
    assert lines[19] == "0"             # has_get_func
    assert lines[20] == "0"             # has_set_func
    # has_get_level must include RIG_LEVEL_STRENGTH (0x40000000)
    assert lines[21] == "0x54001000"    # STRENGTH|SWR|ALC|RFPOWER
    assert lines[22] == "0x00001000"    # has_set_level (RFPOWER)
    assert lines[23] == "0"             # has_get_parm
    assert lines[24] == "0"             # has_set_parm
    assert len(lines) == 25


@pytest.mark.asyncio
async def test_dump_caps_same_as_dump_state(handler: RigctldHandler, mock_radio: AsyncMock) -> None:
    r1 = await handler.execute(get_cmd("dump_state"))
    r2 = await handler.execute(get_cmd("dump_caps"))
    assert r1.values == r2.values


@pytest.mark.asyncio
async def test_get_info(handler: RigctldHandler, mock_radio: AsyncMock) -> None:
    resp = await handler.execute(get_cmd("get_info"))
    assert resp.ok
    assert "IC-7610" in resp.values[0]


@pytest.mark.asyncio
async def test_chk_vfo(handler: RigctldHandler, mock_radio: AsyncMock) -> None:
    resp = await handler.execute(get_cmd("chk_vfo"))
    assert resp.ok
    assert resp.values == ["0"]


@pytest.mark.asyncio
async def test_get_powerstat(handler: RigctldHandler, mock_radio: AsyncMock) -> None:
    resp = await handler.execute(get_cmd("get_powerstat"))
    assert resp.ok
    assert resp.values == ["1"]


@pytest.mark.asyncio
async def test_get_rit(handler: RigctldHandler, mock_radio: AsyncMock) -> None:
    resp = await handler.execute(get_cmd("get_rit"))
    assert resp.ok
    assert resp.values == ["0"]


@pytest.mark.asyncio
async def test_quit_returns_ok_with_echo(handler: RigctldHandler, mock_radio: AsyncMock) -> None:
    resp = await handler.execute(get_cmd("quit"))
    assert resp.ok
    assert resp.cmd_echo == "quit"


# ---------------------------------------------------------------------------
# Unknown command
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_unknown_command_returns_enimpl(handler: RigctldHandler, mock_radio: AsyncMock) -> None:
    cmd = RigctldCommand(short_cmd="?", long_cmd="totally_unknown_cmd")
    resp = await handler.execute(cmd)
    assert resp.error == HamlibError.ENIMPL


# ---------------------------------------------------------------------------
# Read-only mode
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_read_only_rejects_set_freq(mock_radio: AsyncMock) -> None:
    h = RigctldHandler(mock_radio, RigctldConfig(read_only=True))
    resp = await h.execute(set_cmd("set_freq", "14074000"))
    assert resp.error == HamlibError.EACCESS
    mock_radio.set_frequency.assert_not_awaited()


@pytest.mark.asyncio
async def test_read_only_rejects_set_mode(mock_radio: AsyncMock) -> None:
    h = RigctldHandler(mock_radio, RigctldConfig(read_only=True))
    resp = await h.execute(set_cmd("set_mode", "USB"))
    assert resp.error == HamlibError.EACCESS


@pytest.mark.asyncio
async def test_read_only_rejects_set_ptt(mock_radio: AsyncMock) -> None:
    h = RigctldHandler(mock_radio, RigctldConfig(read_only=True))
    resp = await h.execute(set_cmd("set_ptt", "1"))
    assert resp.error == HamlibError.EACCESS
    mock_radio.set_ptt.assert_not_awaited()


@pytest.mark.asyncio
async def test_read_only_allows_get_freq(mock_radio: AsyncMock) -> None:
    h = RigctldHandler(mock_radio, RigctldConfig(read_only=True))
    mock_radio.get_frequency.return_value = 14_074_000
    resp = await h.execute(get_cmd("get_freq"))
    assert resp.ok


@pytest.mark.asyncio
async def test_read_only_allows_get_mode(mock_radio: AsyncMock) -> None:
    h = RigctldHandler(mock_radio, RigctldConfig(read_only=True))
    mock_radio.get_mode_info.return_value = (Mode.USB, None)
    resp = await h.execute(get_cmd("get_mode"))
    assert resp.ok


# ---------------------------------------------------------------------------
# Exception translation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_connection_error_becomes_eio(handler: RigctldHandler, mock_radio: AsyncMock) -> None:
    mock_radio.get_frequency.side_effect = IcomConnectionError("lost")
    resp = await handler.execute(get_cmd("get_freq"))
    assert resp.error == HamlibError.EIO


@pytest.mark.asyncio
async def test_timeout_error_becomes_etimeout(handler: RigctldHandler, mock_radio: AsyncMock) -> None:
    mock_radio.get_frequency.side_effect = IcomTimeoutError("timeout")
    resp = await handler.execute(get_cmd("get_freq"))
    assert resp.error == HamlibError.ETIMEOUT


@pytest.mark.asyncio
async def test_value_error_becomes_einval(handler: RigctldHandler, mock_radio: AsyncMock) -> None:
    mock_radio.get_frequency.side_effect = ValueError("bad value")
    resp = await handler.execute(get_cmd("get_freq"))
    assert resp.error == HamlibError.EINVAL


@pytest.mark.asyncio
async def test_unexpected_exception_becomes_einternal(
    handler: RigctldHandler, mock_radio: AsyncMock
) -> None:
    mock_radio.get_frequency.side_effect = RuntimeError("unexpected")
    resp = await handler.execute(get_cmd("get_freq"))
    assert resp.error == HamlibError.EINTERNAL


@pytest.mark.asyncio
async def test_connection_error_on_set_freq_becomes_eio(
    handler: RigctldHandler, mock_radio: AsyncMock
) -> None:
    mock_radio.set_frequency.side_effect = IcomConnectionError("lost")
    resp = await handler.execute(set_cmd("set_freq", "14074000"))
    assert resp.error == HamlibError.EIO


@pytest.mark.asyncio
async def test_timeout_error_on_set_ptt_becomes_etimeout(
    handler: RigctldHandler, mock_radio: AsyncMock
) -> None:
    mock_radio.set_ptt.side_effect = IcomTimeoutError("timeout")
    resp = await handler.execute(set_cmd("set_ptt", "1"))
    assert resp.error == HamlibError.ETIMEOUT


# ---------------------------------------------------------------------------
# Passband / filter mapping helpers (unit tests)
# ---------------------------------------------------------------------------

def test_passband_to_filter_zero_gives_none() -> None:
    from icom_lan.rigctld.handler import _passband_to_filter
    assert _passband_to_filter(0) is None


def test_passband_to_filter_negative_gives_none() -> None:
    from icom_lan.rigctld.handler import _passband_to_filter
    assert _passband_to_filter(-1) is None


def test_passband_to_filter_wide_gives_fil1() -> None:
    from icom_lan.rigctld.handler import _passband_to_filter
    assert _passband_to_filter(3000) == 1


def test_passband_to_filter_medium_gives_fil2() -> None:
    from icom_lan.rigctld.handler import _passband_to_filter
    assert _passband_to_filter(2400) == 2


def test_passband_to_filter_narrow_gives_fil3() -> None:
    from icom_lan.rigctld.handler import _passband_to_filter
    assert _passband_to_filter(1800) == 3


def test_filter_to_passband_none_gives_zero() -> None:
    from icom_lan.rigctld.handler import _filter_to_passband
    assert _filter_to_passband(None) == 0


def test_filter_to_passband_fil1() -> None:
    from icom_lan.rigctld.handler import _filter_to_passband
    assert _filter_to_passband(1) == 3000


def test_filter_to_passband_fil2() -> None:
    from icom_lan.rigctld.handler import _filter_to_passband
    assert _filter_to_passband(2) == 2400


def test_filter_to_passband_fil3() -> None:
    from icom_lan.rigctld.handler import _filter_to_passband
    assert _filter_to_passband(3) == 1800
