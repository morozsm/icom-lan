"""Unit tests for YaesuCatRadio (mock transport — no real hardware required)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from icom_lan.backends.yaesu_cat.radio import YaesuCatRadio
from icom_lan.backends.yaesu_cat.parser import CatParseError
from icom_lan.backends.yaesu_cat.transport import CatTimeoutError
from icom_lan.exceptions import CommandError
from icom_lan.exceptions import ConnectionError as RadioConnectionError
from icom_lan.rig_loader import load_rig

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_RIGS_DIR = Path(__file__).parents[1] / "rigs"


@pytest.fixture()
def config():
    """Load the real ftx1 RigConfig from TOML."""
    return load_rig(_RIGS_DIR / "ftx1.toml")


@pytest.fixture()
def radio(config):
    """Return a YaesuCatRadio with mocked transport (not connected)."""
    r = YaesuCatRadio("/dev/null", profile=config)
    return r


@pytest.fixture()
def connected_radio(radio):
    """Return a YaesuCatRadio whose transport reports connected=True."""
    radio._transport._connected = True
    return radio


# ---------------------------------------------------------------------------
# Instantiation
# ---------------------------------------------------------------------------


def test_instantiation_with_string_profile():
    """Can create a radio using the 'ftx1' profile string."""
    r = YaesuCatRadio("/dev/null", profile="ftx1")
    assert r.model == "FTX-1"
    assert not r.connected


def test_instantiation_with_rig_config(config):
    """Can create a radio using an already-loaded RigConfig."""
    r = YaesuCatRadio("/dev/null", profile=config)
    assert r.model == "FTX-1"


def test_capabilities_include_expected(config):
    r = YaesuCatRadio("/dev/null", profile=config)
    assert "tx" in r.capabilities
    assert "meters" in r.capabilities


def test_mode_map_built_correctly(radio):
    """Mode codes are 1-based; LSB=1, USB=2, CW-U=3."""
    assert radio._code_to_mode["1"] == "LSB"
    assert radio._code_to_mode["2"] == "USB"
    assert radio._code_to_mode["3"] == "CW-U"
    assert radio._mode_to_code["LSB"] == "1"
    assert radio._mode_to_code["USB"] == "2"


def test_parsers_compiled_for_key_commands(radio):
    """Parser cache should have entries for the four core commands."""
    assert "get_freq" in radio._parsers
    assert "get_mode" in radio._parsers
    assert "get_ptt" in radio._parsers
    assert "get_s_meter" in radio._parsers


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_context_manager_connects_and_disconnects(radio):
    """__aenter__ calls connect(), __aexit__ calls disconnect()."""
    radio._transport.connect = AsyncMock()
    radio._transport.close = AsyncMock()

    async with radio as r:
        assert r is radio
        radio._transport.connect.assert_called_once()

    radio._transport.close.assert_called_once()


@pytest.mark.asyncio
async def test_require_connected_raises_when_not_connected(radio):
    with pytest.raises(RadioConnectionError):
        await radio.get_freq()


# ---------------------------------------------------------------------------
# get_freq / set_freq
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_freq_main(connected_radio):
    connected_radio._transport.query = AsyncMock(return_value="FA014074000")
    freq = await connected_radio.get_freq(receiver=0)
    assert freq == 14_074_000
    connected_radio._transport.query.assert_called_once_with("FA;")
    assert connected_radio.radio_state.main.freq == 14_074_000


@pytest.mark.asyncio
async def test_get_freq_sub(connected_radio):
    connected_radio._transport.query = AsyncMock(return_value="FB007074000")
    freq = await connected_radio.get_freq(receiver=1)
    assert freq == 7_074_000
    connected_radio._transport.query.assert_called_once_with("FB;")
    assert connected_radio.radio_state.sub.freq == 7_074_000


@pytest.mark.asyncio
async def test_set_freq_main(connected_radio):
    connected_radio._transport.write = AsyncMock()
    await connected_radio.set_freq(14_074_000, receiver=0)
    connected_radio._transport.write.assert_called_once_with("FA014074000;")
    assert connected_radio.radio_state.main.freq == 14_074_000


@pytest.mark.asyncio
async def test_set_freq_sub(connected_radio):
    connected_radio._transport.write = AsyncMock()
    await connected_radio.set_freq(7_074_000, receiver=1)
    connected_radio._transport.write.assert_called_once_with("FB007074000;")
    assert connected_radio.radio_state.sub.freq == 7_074_000


@pytest.mark.asyncio
async def test_get_freq_roundtrip(connected_radio):
    """set_freq then get_freq returns same value (via mock)."""
    connected_radio._transport.write = AsyncMock()
    connected_radio._transport.query = AsyncMock(return_value="FA021074000")

    await connected_radio.set_freq(21_074_000)
    freq = await connected_radio.get_freq()
    assert freq == 21_074_000


# ---------------------------------------------------------------------------
# get_mode / set_mode
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_mode_usb(connected_radio):
    # Code "2" → USB
    connected_radio._transport.query = AsyncMock(return_value="MD02")
    mode, filt = await connected_radio.get_mode(receiver=0)
    assert mode == "USB"
    assert filt is None
    assert connected_radio.radio_state.main.mode == "USB"


@pytest.mark.asyncio
async def test_get_mode_lsb(connected_radio):
    connected_radio._transport.query = AsyncMock(return_value="MD01")
    mode, _ = await connected_radio.get_mode()
    assert mode == "LSB"


@pytest.mark.asyncio
async def test_get_mode_sub_receiver(connected_radio):
    connected_radio._transport.query = AsyncMock(return_value="MD14")
    mode, _ = await connected_radio.get_mode(receiver=1)
    assert mode == "FM"
    connected_radio._transport.query.assert_called_once_with("MD1;")
    assert connected_radio.radio_state.sub.mode == "FM"


@pytest.mark.asyncio
async def test_set_mode_usb(connected_radio):
    connected_radio._transport.write = AsyncMock()
    await connected_radio.set_mode("USB", receiver=0)
    connected_radio._transport.write.assert_called_once_with("MD02;")
    assert connected_radio.radio_state.main.mode == "USB"


@pytest.mark.asyncio
async def test_set_mode_sub(connected_radio):
    connected_radio._transport.write = AsyncMock()
    await connected_radio.set_mode("LSB", receiver=1)
    connected_radio._transport.write.assert_called_once_with("MD11;")
    assert connected_radio.radio_state.sub.mode == "LSB"


@pytest.mark.asyncio
async def test_set_mode_unknown_raises(connected_radio):
    with pytest.raises(CommandError, match="Unknown mode"):
        await connected_radio.set_mode("INVALID_MODE")


@pytest.mark.asyncio
async def test_get_set_mode_roundtrip(connected_radio):
    """set_mode("CW-U") then get_mode returns "CW-U"."""
    connected_radio._transport.write = AsyncMock()
    connected_radio._transport.query = AsyncMock(return_value="MD03")

    await connected_radio.set_mode("CW-U")
    mode, _ = await connected_radio.get_mode()
    assert mode == "CW-U"


# ---------------------------------------------------------------------------
# PTT
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_set_ptt_on(connected_radio):
    connected_radio._transport.write = AsyncMock()
    await connected_radio.set_ptt(True)
    connected_radio._transport.write.assert_called_once_with("TX1;")
    assert connected_radio.radio_state.ptt is True


@pytest.mark.asyncio
async def test_set_ptt_off(connected_radio):
    connected_radio._transport.write = AsyncMock()
    await connected_radio.set_ptt(False)
    connected_radio._transport.write.assert_called_once_with("TX0;")
    assert connected_radio.radio_state.ptt is False


@pytest.mark.asyncio
async def test_get_ptt_transmitting(connected_radio):
    connected_radio._transport.query = AsyncMock(return_value="TX1")
    ptt = await connected_radio.get_ptt()
    assert ptt is True
    assert connected_radio.radio_state.ptt is True


@pytest.mark.asyncio
async def test_get_ptt_receiving(connected_radio):
    connected_radio._transport.query = AsyncMock(return_value="TX0")
    ptt = await connected_radio.get_ptt()
    assert ptt is False


# ---------------------------------------------------------------------------
# S-meter
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_s_meter_main(connected_radio):
    connected_radio._transport.query = AsyncMock(return_value="SM0130")
    raw = await connected_radio.get_s_meter(receiver=0)
    assert raw == 130
    connected_radio._transport.query.assert_called_once_with("SM0;")
    assert connected_radio.radio_state.main.s_meter == 130


@pytest.mark.asyncio
async def test_get_s_meter_sub(connected_radio):
    connected_radio._transport.query = AsyncMock(return_value="SM1055")
    raw = await connected_radio.get_s_meter(receiver=1)
    assert raw == 55
    connected_radio._transport.query.assert_called_once_with("SM1;")
    assert connected_radio.radio_state.sub.s_meter == 55


@pytest.mark.asyncio
async def test_get_s_meter_zero(connected_radio):
    connected_radio._transport.query = AsyncMock(return_value="SM0000")
    raw = await connected_radio.get_s_meter()
    assert raw == 0


@pytest.mark.asyncio
async def test_get_s_meter_max(connected_radio):
    connected_radio._transport.query = AsyncMock(return_value="SM0255")
    raw = await connected_radio.get_s_meter()
    assert raw == 255


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_command_not_in_profile_raises(connected_radio):
    """Accessing a command not in the profile raises CommandError."""
    with pytest.raises(CommandError, match="not found in profile"):
        connected_radio._get_spec("nonexistent_command_xyz")


@pytest.mark.asyncio
async def test_transport_timeout_propagates(connected_radio):
    """CatTimeoutError from transport bubbles up unchanged."""
    connected_radio._transport.query = AsyncMock(
        side_effect=CatTimeoutError("timeout")
    )
    with pytest.raises(CatTimeoutError):
        await connected_radio.get_freq()


@pytest.mark.asyncio
async def test_parse_error_propagates(connected_radio):
    """Malformed response raises CatParseError."""
    connected_radio._transport.query = AsyncMock(return_value="GARBAGE_RESPONSE")
    with pytest.raises(CatParseError):
        await connected_radio.get_freq()


@pytest.mark.asyncio
async def test_data_mode_stubs(connected_radio):
    """get_data_mode returns False; set_data_mode is a no-op."""
    assert await connected_radio.get_data_mode() is False
    await connected_radio.set_data_mode(True)  # should not raise


def test_radio_state_initially_default(radio):
    """radio_state is a RadioState with default values."""
    from icom_lan.radio_state import RadioState
    assert isinstance(radio.radio_state, RadioState)
    assert radio.radio_state.ptt is False
    assert radio.radio_state.main.freq == 0
