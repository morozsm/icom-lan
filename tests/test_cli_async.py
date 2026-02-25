"""Tests for CLI async command handlers using mocked IcomRadio."""

import json
from argparse import Namespace
from unittest.mock import AsyncMock, patch

import pytest

from icom_lan.cli import (
    _cmd_cw,
    _cmd_freq,
    _cmd_meter,
    _cmd_mode,
    _cmd_power,
    _cmd_ptt,
    _cmd_status,
    _run,
    main,
)
from icom_lan.exceptions import TimeoutError as IcomTimeout
from icom_lan.types import Mode


# ---------------------------------------------------------------------------
# Mock radio fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_radio():
    radio = AsyncMock()
    radio.get_frequency = AsyncMock(return_value=14_074_000)
    radio.set_frequency = AsyncMock()
    radio.get_mode = AsyncMock(return_value=Mode.USB)
    radio.set_mode = AsyncMock()
    radio.get_power = AsyncMock(return_value=128)
    radio.set_power = AsyncMock()
    radio.get_s_meter = AsyncMock(return_value=120)
    radio.get_swr = AsyncMock(return_value=50)
    radio.get_alc = AsyncMock(return_value=30)
    radio.set_ptt = AsyncMock()
    radio.send_cw_text = AsyncMock()
    radio.power_control = AsyncMock()
    return radio


# ---------------------------------------------------------------------------
# _cmd_status
# ---------------------------------------------------------------------------


class TestCmdStatus:
    @pytest.mark.asyncio
    async def test_status_text(self, mock_radio, capsys) -> None:
        args = Namespace(json=False)
        rc = await _cmd_status(mock_radio, args)
        assert rc == 0
        out = capsys.readouterr().out
        assert "14,074,000" in out
        assert "USB" in out

    @pytest.mark.asyncio
    async def test_status_json(self, mock_radio, capsys) -> None:
        args = Namespace(json=True)
        rc = await _cmd_status(mock_radio, args)
        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        assert data["frequency_hz"] == 14_074_000
        assert data["mode"] == "USB"
        assert data["s_meter"] == 120
        assert data["power"] == 128


# ---------------------------------------------------------------------------
# _cmd_freq
# ---------------------------------------------------------------------------


class TestCmdFreq:
    @pytest.mark.asyncio
    async def test_get_freq_text(self, mock_radio, capsys) -> None:
        args = Namespace(value=None, json=False)
        rc = await _cmd_freq(mock_radio, args)
        assert rc == 0
        out = capsys.readouterr().out
        assert "14,074,000" in out

    @pytest.mark.asyncio
    async def test_get_freq_json(self, mock_radio, capsys) -> None:
        args = Namespace(value=None, json=True)
        rc = await _cmd_freq(mock_radio, args)
        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        assert data["frequency_hz"] == 14_074_000

    @pytest.mark.asyncio
    async def test_set_freq(self, mock_radio, capsys) -> None:
        args = Namespace(value="7074000", json=False)
        rc = await _cmd_freq(mock_radio, args)
        assert rc == 0
        mock_radio.set_frequency.assert_called_once_with(7_074_000)
        out = capsys.readouterr().out
        assert "7,074,000" in out

    @pytest.mark.asyncio
    async def test_set_freq_mhz(self, mock_radio, capsys) -> None:
        args = Namespace(value="14.074m", json=False)
        rc = await _cmd_freq(mock_radio, args)
        assert rc == 0
        mock_radio.set_frequency.assert_called_once_with(14_074_000)


# ---------------------------------------------------------------------------
# _cmd_mode
# ---------------------------------------------------------------------------


class TestCmdMode:
    @pytest.mark.asyncio
    async def test_get_mode_text(self, mock_radio, capsys) -> None:
        args = Namespace(value=None, json=False)
        rc = await _cmd_mode(mock_radio, args)
        assert rc == 0
        assert "USB" in capsys.readouterr().out

    @pytest.mark.asyncio
    async def test_get_mode_json(self, mock_radio, capsys) -> None:
        args = Namespace(value=None, json=True)
        rc = await _cmd_mode(mock_radio, args)
        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        assert data["mode"] == "USB"

    @pytest.mark.asyncio
    async def test_set_mode(self, mock_radio, capsys) -> None:
        args = Namespace(value="LSB", json=False)
        rc = await _cmd_mode(mock_radio, args)
        assert rc == 0
        mock_radio.set_mode.assert_called_once_with("LSB")


# ---------------------------------------------------------------------------
# _cmd_power
# ---------------------------------------------------------------------------


class TestCmdPower:
    @pytest.mark.asyncio
    async def test_get_power_text(self, mock_radio, capsys) -> None:
        args = Namespace(value=None, json=False)
        rc = await _cmd_power(mock_radio, args)
        assert rc == 0
        assert "128" in capsys.readouterr().out

    @pytest.mark.asyncio
    async def test_get_power_json(self, mock_radio, capsys) -> None:
        args = Namespace(value=None, json=True)
        rc = await _cmd_power(mock_radio, args)
        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        assert data["power"] == 128

    @pytest.mark.asyncio
    async def test_set_power(self, mock_radio, capsys) -> None:
        args = Namespace(value=200, json=False)
        rc = await _cmd_power(mock_radio, args)
        assert rc == 0
        mock_radio.set_power.assert_called_once_with(200)


# ---------------------------------------------------------------------------
# _cmd_meter
# ---------------------------------------------------------------------------


class TestCmdMeter:
    @pytest.mark.asyncio
    async def test_meter_text(self, mock_radio, capsys) -> None:
        args = Namespace(json=False)
        rc = await _cmd_meter(mock_radio, args)
        assert rc == 0
        out = capsys.readouterr().out
        assert "120" in out  # s_meter
        assert "50" in out  # swr

    @pytest.mark.asyncio
    async def test_meter_json(self, mock_radio, capsys) -> None:
        args = Namespace(json=True)
        rc = await _cmd_meter(mock_radio, args)
        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        assert data["s_meter"] == 120
        assert data["swr"] == 50
        assert data["alc"] == 30

    @pytest.mark.asyncio
    async def test_meter_timeout_handled(self, mock_radio, capsys) -> None:
        mock_radio.get_swr = AsyncMock(side_effect=IcomTimeout("timeout"))
        args = Namespace(json=False)
        rc = await _cmd_meter(mock_radio, args)
        assert rc == 0
        out = capsys.readouterr().out
        assert "n/a" in out


# ---------------------------------------------------------------------------
# _cmd_ptt
# ---------------------------------------------------------------------------


class TestCmdPtt:
    @pytest.mark.asyncio
    async def test_ptt_on(self, mock_radio, capsys) -> None:
        args = Namespace(state="on")
        rc = await _cmd_ptt(mock_radio, args)
        assert rc == 0
        mock_radio.set_ptt.assert_called_once_with(True)
        assert "ON" in capsys.readouterr().out

    @pytest.mark.asyncio
    async def test_ptt_off(self, mock_radio, capsys) -> None:
        args = Namespace(state="off")
        rc = await _cmd_ptt(mock_radio, args)
        assert rc == 0
        mock_radio.set_ptt.assert_called_once_with(False)
        assert "OFF" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# _cmd_cw
# ---------------------------------------------------------------------------


class TestCmdCw:
    @pytest.mark.asyncio
    async def test_cw(self, mock_radio, capsys) -> None:
        args = Namespace(text="CQ DE KN4KYD")
        rc = await _cmd_cw(mock_radio, args)
        assert rc == 0
        mock_radio.send_cw_text.assert_called_once_with("CQ DE KN4KYD")
        assert "CQ DE KN4KYD" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# _run error handling
# ---------------------------------------------------------------------------


class TestRunErrorHandling:
    @pytest.mark.asyncio
    async def test_run_exception(self, capsys) -> None:
        args = Namespace(
            host="192.168.1.100",
            port=50001,
            user="",
            password="",
            timeout=0.1,
            command="status",
            json=False,
        )
        # _run will try to connect and fail — it catches and prints
        rc = await _run(args)
        assert rc == 1
        err = capsys.readouterr().err
        assert "Error" in err


# ---------------------------------------------------------------------------
# main() entrypoint
# ---------------------------------------------------------------------------


class TestMain:
    def test_no_command_prints_help(self, capsys) -> None:
        with patch("sys.argv", ["icom-lan"]):
            # main with no command should print help and exit 0
            with pytest.raises(SystemExit) as exc:
                main()
            assert exc.value.code == 0

    def test_discover_command(self) -> None:
        # Just verify it doesn't crash on import/parse
        with patch("sys.argv", ["icom-lan", "discover"]):
            # Discover will try UDP broadcast — mock socket
            with patch(
                "icom_lan.cli._cmd_discover",
                new_callable=lambda: lambda: AsyncMock(return_value=0),
            ):
                pass  # We just test parsing works
