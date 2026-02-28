"""Integration tests using MockIcomRadio — no real hardware required.

These tests exercise the full IcomRadio → IcomTransport → UDP stack against a
local mock server, verifying the connection lifecycle and CI-V commands end-to-end.
"""

from __future__ import annotations

import asyncio

import pytest

from icom_lan.exceptions import AuthenticationError
from icom_lan.radio import IcomRadio
from icom_lan.types import Mode

from mock_server import MockIcomRadio


# ---------------------------------------------------------------------------
# Connection lifecycle
# ---------------------------------------------------------------------------


class TestConnect:
    async def test_connect_succeeds(self, mock_radio: MockIcomRadio) -> None:
        """Happy-path: connect and disconnect without error."""
        radio = IcomRadio(
            host="127.0.0.1",
            port=mock_radio.control_port,
            username="testuser",
            password="testpass",
        )
        await radio.connect()
        assert radio.connected
        await radio.disconnect()
        assert not radio.connected

    async def test_context_manager(self, mock_radio: MockIcomRadio) -> None:
        """async with IcomRadio(...) as r: should connect and disconnect cleanly."""
        async with IcomRadio(
            host="127.0.0.1",
            port=mock_radio.control_port,
            username="testuser",
            password="testpass",
        ) as radio:
            assert radio.connected
        # After __aexit__, should be disconnected
        assert not radio.connected

    async def test_auth_failure(self, mock_radio: MockIcomRadio) -> None:
        """Auth failure returns an informative AuthenticationError."""
        mock_radio.auth_fail = True
        radio = IcomRadio(
            host="127.0.0.1",
            port=mock_radio.control_port,
            username="wronguser",
            password="wrongpass",
        )
        with pytest.raises(AuthenticationError):
            await radio.connect()
        assert not radio.connected

    async def test_multiple_connect_disconnect_cycles(
        self, mock_radio: MockIcomRadio
    ) -> None:
        """Connect/disconnect can be repeated on the same radio object."""
        for _ in range(3):
            radio = IcomRadio(
                host="127.0.0.1",
                port=mock_radio.control_port,
                username="testuser",
                password="testpass",
            )
            await radio.connect()
            assert radio.connected
            await radio.disconnect()
            assert not radio.connected


# ---------------------------------------------------------------------------
# Frequency
# ---------------------------------------------------------------------------


class TestFrequency:
    async def test_get_frequency_default(
        self, connected_radio: IcomRadio
    ) -> None:
        freq = await connected_radio.get_frequency()
        assert freq == 14_074_000

    async def test_set_and_get_frequency(
        self, connected_radio: IcomRadio, mock_radio: MockIcomRadio
    ) -> None:
        await connected_radio.set_frequency(7_074_000)
        await asyncio.sleep(0)  # fire-and-forget: yield so mock can process the packet
        assert mock_radio._frequency == 7_074_000
        freq = await connected_radio.get_frequency()
        assert freq == 7_074_000

    async def test_set_frequency_updates_internal_state(
        self, connected_radio: IcomRadio
    ) -> None:
        await connected_radio.set_frequency(3_573_000)
        freq = await connected_radio.get_frequency()
        assert freq == 3_573_000


# ---------------------------------------------------------------------------
# Mode
# ---------------------------------------------------------------------------


class TestMode:
    async def test_get_mode_default(self, connected_radio: IcomRadio) -> None:
        mode = await connected_radio.get_mode()
        assert mode == Mode.USB

    async def test_set_and_get_mode(self, connected_radio: IcomRadio) -> None:
        await connected_radio.set_mode(Mode.LSB)
        mode = await connected_radio.get_mode()
        assert mode == Mode.LSB

    async def test_set_mode_string(self, connected_radio: IcomRadio) -> None:
        await connected_radio.set_mode("AM")
        mode = await connected_radio.get_mode()
        assert mode == Mode.AM

    async def test_get_mode_info_returns_filter(
        self, connected_radio: IcomRadio, mock_radio: MockIcomRadio
    ) -> None:
        mock_radio._filter = 2
        _mode, filt = await connected_radio.get_mode_info()
        assert filt == 2


# ---------------------------------------------------------------------------
# Power
# ---------------------------------------------------------------------------


class TestPower:
    async def test_get_power_default(self, connected_radio: IcomRadio) -> None:
        power = await connected_radio.get_power()
        assert power == 100

    async def test_set_and_get_power(self, connected_radio: IcomRadio) -> None:
        await connected_radio.set_power(200)
        power = await connected_radio.get_power()
        assert power == 200

    async def test_set_power_zero(self, connected_radio: IcomRadio) -> None:
        await connected_radio.set_power(0)
        power = await connected_radio.get_power()
        assert power == 0

    async def test_set_power_max(self, connected_radio: IcomRadio) -> None:
        await connected_radio.set_power(255)
        power = await connected_radio.get_power()
        assert power == 255


# ---------------------------------------------------------------------------
# Meters
# ---------------------------------------------------------------------------


class TestMeters:
    async def test_get_s_meter(
        self, connected_radio: IcomRadio, mock_radio: MockIcomRadio
    ) -> None:
        mock_radio.set_s_meter(150)
        value = await connected_radio.get_s_meter()
        assert value == 150

    async def test_get_swr(
        self, connected_radio: IcomRadio, mock_radio: MockIcomRadio
    ) -> None:
        mock_radio.set_swr(42)
        value = await connected_radio.get_swr()
        assert value == 42

    async def test_s_meter_zero(
        self, connected_radio: IcomRadio, mock_radio: MockIcomRadio
    ) -> None:
        mock_radio.set_s_meter(0)
        value = await connected_radio.get_s_meter()
        assert value == 0

    async def test_s_meter_max(
        self, connected_radio: IcomRadio, mock_radio: MockIcomRadio
    ) -> None:
        mock_radio.set_s_meter(255)
        value = await connected_radio.get_s_meter()
        assert value == 255


# ---------------------------------------------------------------------------
# ATT / PREAMP (Command29)
# ---------------------------------------------------------------------------


class TestAttPreamp:
    async def test_get_attenuator_default_zero(
        self, connected_radio: IcomRadio
    ) -> None:
        level = await connected_radio.get_attenuator_level()
        assert level == 0

    async def test_set_and_get_attenuator(
        self, connected_radio: IcomRadio
    ) -> None:
        await connected_radio.set_attenuator_level(18)
        level = await connected_radio.get_attenuator_level()
        assert level == 18

    async def test_attenuator_bool_on(
        self, connected_radio: IcomRadio
    ) -> None:
        await connected_radio.set_attenuator(True)
        assert await connected_radio.get_attenuator() is True

    async def test_attenuator_bool_off(
        self, connected_radio: IcomRadio
    ) -> None:
        await connected_radio.set_attenuator_level(18)
        await connected_radio.set_attenuator(False)
        assert await connected_radio.get_attenuator() is False

    async def test_get_preamp_default_zero(
        self, connected_radio: IcomRadio
    ) -> None:
        level = await connected_radio.get_preamp()
        assert level == 0

    async def test_set_and_get_preamp(
        self, connected_radio: IcomRadio
    ) -> None:
        await connected_radio.set_preamp(1)
        level = await connected_radio.get_preamp()
        assert level == 1

    async def test_preamp_level_2(
        self, connected_radio: IcomRadio
    ) -> None:
        await connected_radio.set_preamp(2)
        level = await connected_radio.get_preamp()
        assert level == 2

    async def test_digisel_off_by_default_allows_preamp(
        self, connected_radio: IcomRadio, mock_radio: MockIcomRadio
    ) -> None:
        """set_preamp should succeed when DIGI-SEL is off (default)."""
        mock_radio.set_digisel(False)
        await connected_radio.set_preamp(1)  # must not raise
        await asyncio.sleep(0)  # fire-and-forget: yield so mock can process the packet
        assert mock_radio._preamp == 1


# ---------------------------------------------------------------------------
# Keep-alive / ping
# ---------------------------------------------------------------------------


class TestKeepalive:
    async def test_stays_connected_over_time(
        self, connected_radio: IcomRadio
    ) -> None:
        """Radio stays connected during a short wait (pings should keep it alive)."""
        assert connected_radio.connected
        await asyncio.sleep(1.5)  # > 3 × ping interval (0.5 s each)
        assert connected_radio.connected


# ---------------------------------------------------------------------------
# Disconnect
# ---------------------------------------------------------------------------


class TestDisconnect:
    async def test_disconnect_marks_not_connected(
        self, connected_radio: IcomRadio
    ) -> None:
        assert connected_radio.connected
        await connected_radio.disconnect()
        assert not connected_radio.connected

    async def test_double_disconnect_is_safe(
        self, connected_radio: IcomRadio
    ) -> None:
        await connected_radio.disconnect()
        await connected_radio.disconnect()  # must not raise
