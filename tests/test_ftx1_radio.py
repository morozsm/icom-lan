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


# ---------------------------------------------------------------------------
# D1: RX Audio Controls
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_af_level(connected_radio):
    connected_radio._transport.query = AsyncMock(return_value="AG0128")
    level = await connected_radio.get_af_level()
    assert level == 128
    connected_radio._transport.query.assert_called_once_with("AG0;")


@pytest.mark.asyncio
async def test_set_af_level(connected_radio):
    connected_radio._transport.write = AsyncMock()
    await connected_radio.set_af_level(200)
    connected_radio._transport.write.assert_called_once_with("AG0200;")


@pytest.mark.asyncio
async def test_get_rf_gain(connected_radio):
    connected_radio._transport.query = AsyncMock(return_value="RG0255")
    assert await connected_radio.get_rf_gain() == 255
    connected_radio._transport.query.assert_called_once_with("RG0;")


@pytest.mark.asyncio
async def test_set_squelch(connected_radio):
    connected_radio._transport.write = AsyncMock()
    await connected_radio.set_squelch(50)
    connected_radio._transport.write.assert_called_once_with("SQ0050;")


# ---------------------------------------------------------------------------
# D2: RF Front-End
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_attenuator_off(connected_radio):
    connected_radio._transport.query = AsyncMock(return_value="RA00")
    state = await connected_radio.get_attenuator()
    assert state == 0
    connected_radio._transport.query.assert_called_once_with("RA0;")


@pytest.mark.asyncio
async def test_set_attenuator_on(connected_radio):
    connected_radio._transport.write = AsyncMock()
    await connected_radio.set_attenuator(1)
    connected_radio._transport.write.assert_called_once_with("RA01;")


@pytest.mark.asyncio
async def test_get_preamp(connected_radio):
    connected_radio._transport.query = AsyncMock(return_value="PA01")
    assert await connected_radio.get_preamp() == 1
    connected_radio._transport.query.assert_called_once_with("PA0;")


@pytest.mark.asyncio
async def test_set_preamp(connected_radio):
    connected_radio._transport.write = AsyncMock()
    await connected_radio.set_preamp(2, band=0)
    connected_radio._transport.write.assert_called_once_with("PA02;")


# ---------------------------------------------------------------------------
# D3: DSP (NB/NR/Notch)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_nb_level(connected_radio):
    connected_radio._transport.query = AsyncMock(return_value="NL0005")
    assert await connected_radio.get_nb_level() == 5
    connected_radio._transport.query.assert_called_once_with("NL0;")


@pytest.mark.asyncio
async def test_set_nb_level(connected_radio):
    connected_radio._transport.write = AsyncMock()
    await connected_radio.set_nb_level(3)
    connected_radio._transport.write.assert_called_once_with("NL0003;")


@pytest.mark.asyncio
async def test_get_nr_level(connected_radio):
    connected_radio._transport.query = AsyncMock(return_value="RL007")
    assert await connected_radio.get_nr_level() == 7
    connected_radio._transport.query.assert_called_once_with("RL0;")


@pytest.mark.asyncio
async def test_get_auto_notch_on(connected_radio):
    connected_radio._transport.query = AsyncMock(return_value="BC01")
    assert await connected_radio.get_auto_notch() is True


@pytest.mark.asyncio
async def test_get_auto_notch_off(connected_radio):
    connected_radio._transport.query = AsyncMock(return_value="BC00")
    assert await connected_radio.get_auto_notch() is False


@pytest.mark.asyncio
async def test_set_auto_notch(connected_radio):
    connected_radio._transport.write = AsyncMock()
    await connected_radio.set_auto_notch(True)
    connected_radio._transport.write.assert_called_once_with("BC01;")


@pytest.mark.asyncio
async def test_get_manual_notch(connected_radio):
    """get_manual_notch calls both BP00 and BP01 queries."""
    responses = iter(["BP00001", "BP01120"])
    connected_radio._transport.query = AsyncMock(side_effect=responses)
    enabled, freq = await connected_radio.get_manual_notch()
    assert enabled is True
    assert freq == 120


@pytest.mark.asyncio
async def test_set_manual_notch(connected_radio):
    connected_radio._transport.write = AsyncMock()
    await connected_radio.set_manual_notch(True)
    connected_radio._transport.write.assert_called_once_with("BP00001;")


@pytest.mark.asyncio
async def test_set_manual_notch_freq(connected_radio):
    connected_radio._transport.write = AsyncMock()
    await connected_radio.set_manual_notch_freq(80)
    connected_radio._transport.write.assert_called_once_with("BP01080;")


# ---------------------------------------------------------------------------
# D4: Filters
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_filter_width(connected_radio):
    connected_radio._transport.query = AsyncMock(return_value="SH0010")
    assert await connected_radio.get_filter_width() == 10
    connected_radio._transport.query.assert_called_once_with("SH0;")


@pytest.mark.asyncio
async def test_set_filter_width(connected_radio):
    connected_radio._transport.write = AsyncMock()
    await connected_radio.set_filter_width(5)
    connected_radio._transport.write.assert_called_once_with("SH0005;")


@pytest.mark.asyncio
async def test_get_if_shift_positive(connected_radio):
    connected_radio._transport.query = AsyncMock(return_value="IS00+0500")
    offset = await connected_radio.get_if_shift()
    assert offset == 500


@pytest.mark.asyncio
async def test_get_if_shift_negative(connected_radio):
    connected_radio._transport.query = AsyncMock(return_value="IS00-0200")
    offset = await connected_radio.get_if_shift()
    assert offset == -200


@pytest.mark.asyncio
async def test_set_if_shift_positive(connected_radio):
    connected_radio._transport.write = AsyncMock()
    await connected_radio.set_if_shift(300)
    connected_radio._transport.write.assert_called_once_with("IS00+0300;")


@pytest.mark.asyncio
async def test_set_if_shift_negative(connected_radio):
    connected_radio._transport.write = AsyncMock()
    await connected_radio.set_if_shift(-150)
    connected_radio._transport.write.assert_called_once_with("IS00-0150;")


@pytest.mark.asyncio
async def test_get_narrow(connected_radio):
    connected_radio._transport.query = AsyncMock(return_value="NA01")
    assert await connected_radio.get_narrow() is True


@pytest.mark.asyncio
async def test_set_narrow(connected_radio):
    connected_radio._transport.write = AsyncMock()
    await connected_radio.set_narrow(False)
    connected_radio._transport.write.assert_called_once_with("NA00;")


# ---------------------------------------------------------------------------
# D5: Split/Dual Watch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_split_on(connected_radio):
    connected_radio._transport.query = AsyncMock(return_value="ST1")
    assert await connected_radio.get_split() is True
    connected_radio._transport.query.assert_called_once_with("ST;")


@pytest.mark.asyncio
async def test_set_split(connected_radio):
    connected_radio._transport.write = AsyncMock()
    await connected_radio.set_split(True)
    connected_radio._transport.write.assert_called_once_with("ST1;")


@pytest.mark.asyncio
async def test_get_rx_func(connected_radio):
    connected_radio._transport.query = AsyncMock(return_value="FR00")
    assert await connected_radio.get_rx_func() == 0
    connected_radio._transport.query.assert_called_once_with("FR;")


@pytest.mark.asyncio
async def test_get_tx_func(connected_radio):
    connected_radio._transport.query = AsyncMock(return_value="FT1")
    assert await connected_radio.get_tx_func() == 1
    connected_radio._transport.query.assert_called_once_with("FT;")


@pytest.mark.asyncio
async def test_get_vfo_select(connected_radio):
    connected_radio._transport.query = AsyncMock(return_value="VS0")
    assert await connected_radio.get_vfo_select() == 0
    connected_radio._transport.query.assert_called_once_with("VS;")


@pytest.mark.asyncio
async def test_vfo_a_to_b(connected_radio):
    connected_radio._transport.write = AsyncMock()
    await connected_radio.vfo_a_to_b()
    connected_radio._transport.write.assert_called_once_with("AB;")


@pytest.mark.asyncio
async def test_vfo_b_to_a(connected_radio):
    connected_radio._transport.write = AsyncMock()
    await connected_radio.vfo_b_to_a()
    connected_radio._transport.write.assert_called_once_with("BA;")


# ---------------------------------------------------------------------------
# D6: TX Stack
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_power(connected_radio):
    connected_radio._transport.query = AsyncMock(return_value="PC2100")
    head, watts = await connected_radio.get_power()
    assert head == 2
    assert watts == 100
    connected_radio._transport.query.assert_called_once_with("PC;")


@pytest.mark.asyncio
async def test_set_power(connected_radio):
    connected_radio._transport.write = AsyncMock()
    await connected_radio.set_power(50, head=2)
    connected_radio._transport.write.assert_called_once_with("PC2050;")


@pytest.mark.asyncio
async def test_get_mic_gain(connected_radio):
    connected_radio._transport.query = AsyncMock(return_value="MG050")
    assert await connected_radio.get_mic_gain() == 50
    connected_radio._transport.query.assert_called_once_with("MG;")


@pytest.mark.asyncio
async def test_get_processor(connected_radio):
    connected_radio._transport.query = AsyncMock(return_value="PR01")
    assert await connected_radio.get_processor() is True


@pytest.mark.asyncio
async def test_get_monitor_on(connected_radio):
    """ML0 sub-command: monitor on/off state."""
    connected_radio._transport.query = AsyncMock(return_value="ML0001")
    assert await connected_radio.get_monitor_on() is True
    connected_radio._transport.query.assert_called_once_with("ML0;")


@pytest.mark.asyncio
async def test_get_monitor_on_off(connected_radio):
    """ML0 sub-command: monitor off."""
    connected_radio._transport.query = AsyncMock(return_value="ML0000")
    assert await connected_radio.get_monitor_on() is False


@pytest.mark.asyncio
async def test_set_monitor_on(connected_radio):
    """ML0 sub-command: set monitor on."""
    connected_radio._transport.write = AsyncMock()
    await connected_radio.set_monitor_on(True)
    connected_radio._transport.write.assert_called_once_with("ML0001;")


@pytest.mark.asyncio
async def test_get_monitor_level(connected_radio):
    """ML1 sub-command: monitor gain level."""
    connected_radio._transport.query = AsyncMock(return_value="ML1100")
    assert await connected_radio.get_monitor_level() == 100
    connected_radio._transport.query.assert_called_once_with("ML1;")


@pytest.mark.asyncio
async def test_set_monitor_level(connected_radio):
    """ML1 sub-command: set monitor gain level."""
    connected_radio._transport.write = AsyncMock()
    await connected_radio.set_monitor_level(128)
    connected_radio._transport.write.assert_called_once_with("ML1128;")


# ---------------------------------------------------------------------------
# D7: CW
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_keyer_speed(connected_radio):
    connected_radio._transport.query = AsyncMock(return_value="KS020")
    assert await connected_radio.get_keyer_speed() == 20
    connected_radio._transport.query.assert_called_once_with("KS;")


@pytest.mark.asyncio
async def test_set_keyer_speed(connected_radio):
    connected_radio._transport.write = AsyncMock()
    await connected_radio.set_keyer_speed(25)
    connected_radio._transport.write.assert_called_once_with("KS025;")


@pytest.mark.asyncio
async def test_get_key_pitch(connected_radio):
    connected_radio._transport.query = AsyncMock(return_value="KP30")
    assert await connected_radio.get_key_pitch() == 30
    connected_radio._transport.query.assert_called_once_with("KP;")


@pytest.mark.asyncio
async def test_send_cw(connected_radio):
    connected_radio._transport.write = AsyncMock()
    await connected_radio.send_cw("0", "CQ DE W1ABC")
    connected_radio._transport.write.assert_called_once_with("KY0CQ DE W1ABC;")


@pytest.mark.asyncio
async def test_get_break_in_delay(connected_radio):
    connected_radio._transport.query = AsyncMock(return_value="SD0300")
    assert await connected_radio.get_break_in_delay() == 300
    connected_radio._transport.query.assert_called_once_with("SD;")


@pytest.mark.asyncio
async def test_set_break_in_delay(connected_radio):
    connected_radio._transport.write = AsyncMock()
    await connected_radio.set_break_in_delay(500)
    connected_radio._transport.write.assert_called_once_with("SD0500;")


@pytest.mark.asyncio
async def test_get_break_in(connected_radio):
    connected_radio._transport.query = AsyncMock(return_value="BI1")
    assert await connected_radio.get_break_in() is True


@pytest.mark.asyncio
async def test_get_cw_spot(connected_radio):
    connected_radio._transport.query = AsyncMock(return_value="CS0")
    assert await connected_radio.get_cw_spot() is False


# ---------------------------------------------------------------------------
# D8: Clarifier (RIT/XIT)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_clarifier_both_off(connected_radio):
    connected_radio._transport.query = AsyncMock(return_value="CF00000000")
    rx, tx = await connected_radio.get_clarifier()
    assert rx is False
    assert tx is False
    connected_radio._transport.query.assert_called_once_with("CF000;")


@pytest.mark.asyncio
async def test_get_clarifier_rx_on(connected_radio):
    connected_radio._transport.query = AsyncMock(return_value="CF00010000")
    rx, tx = await connected_radio.get_clarifier()
    assert rx is True
    assert tx is False


@pytest.mark.asyncio
async def test_set_clarifier(connected_radio):
    connected_radio._transport.write = AsyncMock()
    await connected_radio.set_clarifier(True, False)
    connected_radio._transport.write.assert_called_once_with("CF00010000;")


@pytest.mark.asyncio
async def test_get_clarifier_freq_positive(connected_radio):
    connected_radio._transport.query = AsyncMock(return_value="CF001+0600")
    assert await connected_radio.get_clarifier_freq() == 600
    connected_radio._transport.query.assert_called_once_with("CF001;")


@pytest.mark.asyncio
async def test_get_clarifier_freq_negative(connected_radio):
    connected_radio._transport.query = AsyncMock(return_value="CF001-0400")
    assert await connected_radio.get_clarifier_freq() == -400


@pytest.mark.asyncio
async def test_set_clarifier_freq(connected_radio):
    connected_radio._transport.write = AsyncMock()
    await connected_radio.set_clarifier_freq(-250)
    connected_radio._transport.write.assert_called_once_with("CF001-0250;")


# ---------------------------------------------------------------------------
# D9: Tone/TSQL
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_sql_type(connected_radio):
    connected_radio._transport.query = AsyncMock(return_value="CT002")
    assert await connected_radio.get_sql_type() == 2
    connected_radio._transport.query.assert_called_once_with("CT0;")


@pytest.mark.asyncio
async def test_set_sql_type(connected_radio):
    connected_radio._transport.write = AsyncMock()
    await connected_radio.set_sql_type(3)
    connected_radio._transport.write.assert_called_once_with("CT003;")


# ---------------------------------------------------------------------------
# D10: System
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_id(connected_radio):
    connected_radio._transport.query = AsyncMock(return_value="ID0840")
    model_id = await connected_radio.get_id()
    assert model_id == "0840"
    connected_radio._transport.query.assert_called_once_with("ID;")


@pytest.mark.asyncio
async def test_get_auto_info(connected_radio):
    connected_radio._transport.query = AsyncMock(return_value="AI0")
    assert await connected_radio.get_auto_info() is False


@pytest.mark.asyncio
async def test_set_auto_info(connected_radio):
    connected_radio._transport.write = AsyncMock()
    await connected_radio.set_auto_info(True)
    connected_radio._transport.write.assert_called_once_with("AI1;")


@pytest.mark.asyncio
async def test_get_vox(connected_radio):
    connected_radio._transport.query = AsyncMock(return_value="VX1")
    assert await connected_radio.get_vox() is True


@pytest.mark.asyncio
async def test_set_vox(connected_radio):
    connected_radio._transport.write = AsyncMock()
    await connected_radio.set_vox(False)
    connected_radio._transport.write.assert_called_once_with("VX0;")


@pytest.mark.asyncio
async def test_get_lock(connected_radio):
    connected_radio._transport.query = AsyncMock(return_value="LK0")
    assert await connected_radio.get_lock() is False


@pytest.mark.asyncio
async def test_set_lock(connected_radio):
    connected_radio._transport.write = AsyncMock()
    await connected_radio.set_lock(True)
    connected_radio._transport.write.assert_called_once_with("LK1;")


@pytest.mark.asyncio
async def test_get_band_not_supported(connected_radio):
    """FTX-1 does not support BS read (write-only)."""
    assert not hasattr(connected_radio, "get_band")


@pytest.mark.asyncio
async def test_set_band(connected_radio):
    connected_radio._transport.write = AsyncMock()
    await connected_radio.set_band(3)
    connected_radio._transport.write.assert_called_once_with("BS003;")


@pytest.mark.asyncio
async def test_band_up(connected_radio):
    connected_radio._transport.write = AsyncMock()
    await connected_radio.band_up()
    connected_radio._transport.write.assert_called_once_with("BU0;")


@pytest.mark.asyncio
async def test_band_down(connected_radio):
    connected_radio._transport.write = AsyncMock()
    await connected_radio.band_down()
    connected_radio._transport.write.assert_called_once_with("BD0;")


# ---------------------------------------------------------------------------
# AGC
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_agc(connected_radio):
    connected_radio._transport.query = AsyncMock(return_value="GT03")
    assert await connected_radio.get_agc() == 3
    connected_radio._transport.query.assert_called_once_with("GT0;")


@pytest.mark.asyncio
async def test_set_agc(connected_radio):
    connected_radio._transport.write = AsyncMock()
    await connected_radio.set_agc(2)
    connected_radio._transport.write.assert_called_once_with("GT02;")


# ---------------------------------------------------------------------------
# set_nb / set_nr — level_is_toggle (FTX-1 has no set_nb/set_nr commands)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_set_nb_on_calls_set_nb_level_with_default_when_current_is_zero(
    connected_radio,
):
    """set_nb(True) uses midpoint default (5) when nb_level is 0."""
    connected_radio._transport.write = AsyncMock()
    assert connected_radio._state.main.nb_level == 0
    await connected_radio.set_nb(True)
    connected_radio._transport.write.assert_called_once_with("NL0005;")


@pytest.mark.asyncio
async def test_set_nb_on_keeps_existing_level(connected_radio):
    """set_nb(True) keeps the current level when nb_level > 0."""
    connected_radio._transport.write = AsyncMock()
    connected_radio._state.main.nb_level = 3
    await connected_radio.set_nb(True)
    connected_radio._transport.write.assert_called_once_with("NL0003;")


@pytest.mark.asyncio
async def test_set_nb_off_sends_level_zero(connected_radio):
    """set_nb(False) sends level 0 (= OFF for FTX-1)."""
    connected_radio._transport.write = AsyncMock()
    connected_radio._state.main.nb_level = 5
    await connected_radio.set_nb(False)
    connected_radio._transport.write.assert_called_once_with("NL0000;")


@pytest.mark.asyncio
async def test_set_nr_on_calls_set_nr_level_with_default_when_current_is_zero(
    connected_radio,
):
    """set_nr(True) uses midpoint default (7) when nr_level is 0."""
    connected_radio._transport.write = AsyncMock()
    assert connected_radio._state.main.nr_level == 0
    await connected_radio.set_nr(True)
    connected_radio._transport.write.assert_called_once_with("RL007;")


@pytest.mark.asyncio
async def test_set_nr_on_keeps_existing_level(connected_radio):
    """set_nr(True) keeps the current level when nr_level > 0."""
    connected_radio._transport.write = AsyncMock()
    connected_radio._state.main.nr_level = 4
    await connected_radio.set_nr(True)
    connected_radio._transport.write.assert_called_once_with("RL004;")


@pytest.mark.asyncio
async def test_set_nr_off_sends_level_zero(connected_radio):
    """set_nr(False) sends level 0 (= OFF for FTX-1)."""
    connected_radio._transport.write = AsyncMock()
    connected_radio._state.main.nr_level = 7
    await connected_radio.set_nr(False)
    connected_radio._transport.write.assert_called_once_with("RL000;")
