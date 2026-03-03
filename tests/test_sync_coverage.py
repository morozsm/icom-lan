"""Additional coverage tests for icom_lan.sync."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from icom_lan.sync import IcomRadio


def _radio() -> IcomRadio:
    r = IcomRadio("127.0.0.1")
    r._radio.connect = AsyncMock()
    r._radio.disconnect = AsyncMock()
    return r


def test_connect_disconnect_and_context_manager() -> None:
    r = _radio()
    r.connect()
    r.disconnect()
    r._radio.connect.assert_awaited_once()
    r._radio.disconnect.assert_awaited_once()
    r._loop.close()

    r2 = _radio()
    with r2 as entered:
        assert entered is r2
    assert r2._loop.is_closed()
    r2._radio.connect.assert_awaited_once()
    r2._radio.disconnect.assert_awaited_once()


def test_sync_wrappers_delegate_and_return_values() -> None:
    r = _radio()
    r._radio.get_frequency = AsyncMock(return_value=7_100_000)
    r._radio.get_mode = AsyncMock(return_value="USB")
    r._radio.get_mode_info = AsyncMock(return_value=("USB", 2))
    r._radio.get_filter = AsyncMock(return_value=2)
    r._radio.get_power = AsyncMock(return_value=200)
    r._radio.get_s_meter = AsyncMock(return_value=99)
    r._radio.get_swr = AsyncMock(return_value=10)
    r._radio.get_alc = AsyncMock(return_value=5)
    r._radio.get_attenuator_level = AsyncMock(return_value=18)
    r._radio.get_attenuator = AsyncMock(return_value=True)
    r._radio.get_preamp = AsyncMock(return_value=1)
    r._radio.get_digisel = AsyncMock(return_value=False)
    r._radio.snapshot_state = AsyncMock(return_value={"freq": 7100000})

    r._radio.set_frequency = AsyncMock()
    r._radio.set_filter = AsyncMock()
    r._radio.set_mode = AsyncMock()
    r._radio.set_power = AsyncMock()
    r._radio.set_ptt = AsyncMock()
    r._radio.select_vfo = AsyncMock()
    r._radio.vfo_equalize = AsyncMock()
    r._radio.vfo_exchange = AsyncMock()
    r._radio.set_split_mode = AsyncMock()
    r._radio.set_attenuator_level = AsyncMock()
    r._radio.set_attenuator = AsyncMock()
    r._radio.set_preamp = AsyncMock()
    r._radio.set_digisel = AsyncMock()
    r._radio.restore_state = AsyncMock()
    r._radio.send_cw_text = AsyncMock()
    r._radio.stop_cw_text = AsyncMock()
    r._radio.power_control = AsyncMock()

    assert r.get_frequency() == 7_100_000
    assert r.get_mode() == "USB"
    assert r.get_mode_info() == ("USB", 2)
    assert r.get_filter() == 2
    assert r.get_power() == 200
    assert r.get_s_meter() == 99
    assert r.get_swr() == 10
    assert r.get_alc() == 5
    assert r.get_attenuator_level() == 18
    assert r.get_attenuator() is True
    assert r.get_preamp() == 1
    assert r.get_digisel() is False
    assert r.snapshot_state() == {"freq": 7100000}

    r.set_frequency(7100000)
    r.set_filter(2)
    r.set_mode("LSB", 1)
    r.set_power(150)
    r.set_ptt(True)
    r.select_vfo("B")
    r.vfo_equalize()
    r.vfo_exchange()
    r.set_split_mode(True)
    r.set_attenuator_level(18)
    r.set_attenuator(True)
    r.set_preamp(2)
    r.set_digisel(True)
    r.restore_state({"freq": 7000000})
    r.send_cw_text("TEST")
    r.stop_cw_text()
    r.power_control(False)

    r._radio.set_frequency.assert_awaited_once_with(7100000)
    r._radio.set_filter.assert_awaited_once_with(2)
    r._radio.set_mode.assert_awaited_once_with("LSB", 1)
    r._radio.set_power.assert_awaited_once_with(150)
    r._radio.set_ptt.assert_awaited_once_with(True)
    r._radio.select_vfo.assert_awaited_once_with("B")
    r._radio.vfo_equalize.assert_awaited_once()
    r._radio.vfo_exchange.assert_awaited_once()
    r._radio.set_split_mode.assert_awaited_once_with(True)
    r._radio.set_attenuator_level.assert_awaited_once_with(18)
    r._radio.set_attenuator.assert_awaited_once_with(True)
    r._radio.set_preamp.assert_awaited_once_with(2)
    r._radio.set_digisel.assert_awaited_once_with(True)
    r._radio.restore_state.assert_awaited_once_with({"freq": 7000000})
    r._radio.send_cw_text.assert_awaited_once_with("TEST")
    r._radio.stop_cw_text.assert_awaited_once()
    r._radio.power_control.assert_awaited_once_with(False)
    r._loop.close()


def test_audio_wrappers_and_deprecated_aliases() -> None:
    r = _radio()

    def cb(_pkt: object) -> None:
        return None

    r._radio.start_audio_rx_opus = AsyncMock()
    r._radio.stop_audio_rx_opus = AsyncMock()
    r._radio.start_audio_tx_opus = AsyncMock()
    r._radio.push_audio_tx_opus = AsyncMock()
    r._radio.stop_audio_tx_opus = AsyncMock()

    r.start_audio_rx_opus(cb, jitter_depth=7)
    r.stop_audio_rx_opus()
    r.start_audio_tx_opus()
    r.push_audio_tx_opus(b"\xAA\xBB")
    r.stop_audio_tx_opus()

    r._radio.start_audio_rx_opus.assert_awaited_once_with(cb, jitter_depth=7)
    r._radio.stop_audio_rx_opus.assert_awaited_once()
    r._radio.start_audio_tx_opus.assert_awaited_once()
    r._radio.push_audio_tx_opus.assert_awaited_once_with(b"\xAA\xBB")
    r._radio.stop_audio_tx_opus.assert_awaited_once()

    with pytest.warns(DeprecationWarning):
        r.start_audio_rx(cb)
    with pytest.warns(DeprecationWarning):
        r.stop_audio_rx()
    with pytest.warns(DeprecationWarning):
        r.start_audio_tx()
    with pytest.warns(DeprecationWarning):
        r.push_audio_tx(b"\x01")
    with pytest.warns(DeprecationWarning):
        r.stop_audio_tx()
    r._loop.close()
