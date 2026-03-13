"""Tests for serial port enumeration, candidate filtering, and CI-V probing."""

from __future__ import annotations

import asyncio
from unittest.mock import Mock, patch

import pytest

from icom_lan.discovery import (
    CivProbeResult,
    SerialPortCandidate,
    _is_candidate,
    _parse_probe_response,
    dedupe_radios,
    enumerate_serial_ports,
    probe_serial_civ,
)


# ---------------------------------------------------------------------------
# Fake serial transport helpers for CI-V probe tests
# ---------------------------------------------------------------------------

class _FakeReader:
    def __init__(self, chunks: list[bytes]) -> None:
        self._queue: asyncio.Queue[bytes] = asyncio.Queue()
        for chunk in chunks:
            self._queue.put_nowait(chunk)

    async def read(self, n: int) -> bytes:
        return await self._queue.get()


class _FakeWriter:
    def __init__(self) -> None:
        self.written: list[bytes] = []
        self.closed = False

    def write(self, data: bytes) -> None:
        self.written.append(bytes(data))

    async def drain(self) -> None:
        pass

    def close(self) -> None:
        self.closed = True

    async def wait_closed(self) -> None:
        pass


def _make_open(reader: _FakeReader, writer: _FakeWriter):
    async def _open(*, url: str, baudrate: int, **_kw: object):
        return reader, writer
    return _open


_IC7610_RESPONSE = bytes([0xFE, 0xFE, 0xE0, 0x98, 0x19, 0x00, 0x01, 0x06, 0xFD])
_PROBE_CMD = bytes([0xFE, 0xFE, 0x00, 0xE0, 0x19, 0x00, 0xFD])


# ---------------------------------------------------------------------------
# CI-V probe tests
# ---------------------------------------------------------------------------

class TestProbeSerialCiv:
    @pytest.mark.asyncio
    async def test_success_at_first_baud(self) -> None:
        reader = _FakeReader([_IC7610_RESPONSE])
        writer = _FakeWriter()
        result = await probe_serial_civ(
            "/dev/ttyUSB0",
            baud_rates=[19200, 9600],
            timeout=0.1,
            _open_serial=_make_open(reader, writer),
        )
        assert isinstance(result, CivProbeResult)
        assert result.port == "/dev/ttyUSB0"
        assert result.baud == 19200
        assert result.address == 0x98
        assert result.model_id == bytes([0x01, 0x06])

    @pytest.mark.asyncio
    async def test_timeout_tries_next_baud(self) -> None:
        call_count = 0

        async def _open(*, url: str, baudrate: int, **_kw: object):
            nonlocal call_count
            call_count += 1
            if baudrate == 19200:
                return _FakeReader([]), _FakeWriter()
            return _FakeReader([_IC7610_RESPONSE]), _FakeWriter()

        result = await probe_serial_civ(
            "/dev/ttyUSB0",
            baud_rates=[19200, 9600],
            timeout=0.05,
            _open_serial=_open,
        )
        assert result is not None
        assert result.baud == 9600
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_invalid_response_returns_none(self) -> None:
        garbage = bytes([0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08])
        reader = _FakeReader([garbage])
        writer = _FakeWriter()
        result = await probe_serial_civ(
            "/dev/ttyUSB0",
            baud_rates=[19200],
            timeout=0.1,
            _open_serial=_make_open(reader, writer),
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_all_bauds_fail_returns_none(self) -> None:
        async def _open(*, url: str, baudrate: int, **_kw: object):
            return _FakeReader([]), _FakeWriter()

        result = await probe_serial_civ(
            "/dev/ttyUSB0",
            baud_rates=[19200, 9600],
            timeout=0.05,
            _open_serial=_open,
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_port_busy_returns_none(self) -> None:
        async def _open(*, url: str, baudrate: int, **_kw: object):
            raise OSError("Resource busy")

        result = await probe_serial_civ(
            "/dev/ttyUSB0",
            baud_rates=[19200, 9600],
            timeout=0.1,
            _open_serial=_open,
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_echoed_command_before_response(self) -> None:
        data = _PROBE_CMD + _IC7610_RESPONSE
        reader = _FakeReader([data])
        writer = _FakeWriter()
        result = await probe_serial_civ(
            "/dev/ttyUSB0",
            baud_rates=[19200],
            timeout=0.1,
            _open_serial=_make_open(reader, writer),
        )
        assert result is not None
        assert result.address == 0x98
        assert result.model_id == bytes([0x01, 0x06])

    @pytest.mark.asyncio
    async def test_sends_correct_civ_command(self) -> None:
        reader = _FakeReader([_IC7610_RESPONSE])
        writer = _FakeWriter()
        await probe_serial_civ(
            "/dev/ttyUSB0",
            baud_rates=[19200],
            timeout=0.1,
            _open_serial=_make_open(reader, writer),
        )
        assert writer.written[0] == _PROBE_CMD

    @pytest.mark.asyncio
    async def test_closes_writer_after_success(self) -> None:
        reader = _FakeReader([_IC7610_RESPONSE])
        writer = _FakeWriter()
        await probe_serial_civ(
            "/dev/ttyUSB0",
            baud_rates=[19200],
            timeout=0.1,
            _open_serial=_make_open(reader, writer),
        )
        assert writer.closed is True

    @pytest.mark.asyncio
    async def test_default_baud_rates_used_when_none_specified(self) -> None:
        seen_bauds: list[int] = []

        async def _open(*, url: str, baudrate: int, **_kw: object):
            seen_bauds.append(baudrate)
            return _FakeReader([]), _FakeWriter()

        await probe_serial_civ("/dev/ttyUSB0", timeout=0.01, _open_serial=_open)
        assert seen_bauds == [19200, 9600, 115200, 4800]


class TestParseProbeResponse:
    def test_valid_ic7610_response(self) -> None:
        result = _parse_probe_response("/dev/x", 19200, _IC7610_RESPONSE)
        assert result is not None
        assert result.address == 0x98
        assert result.model_id == bytes([0x01, 0x06])

    def test_no_preamble_returns_none(self) -> None:
        assert _parse_probe_response("/dev/x", 19200, bytes(9)) is None

    def test_too_short_after_preamble_returns_none(self) -> None:
        data = bytes([0xFE, 0xFE, 0xE0, 0x98])
        assert _parse_probe_response("/dev/x", 19200, data) is None

    def test_wrong_command_byte_returns_none(self) -> None:
        # byte[4] should be 0x19; use 0x00 here
        data = bytes([0xFE, 0xFE, 0xE0, 0x98, 0x00, 0x00, 0x01, 0x06, 0xFD])
        assert _parse_probe_response("/dev/x", 19200, data) is None

    def test_no_terminator_returns_none(self) -> None:
        data = bytes([0xFE, 0xFE, 0xE0, 0x98, 0x19, 0x00, 0x01, 0x06])
        assert _parse_probe_response("/dev/x", 19200, data) is None


def _make_port(device: str, description: str = "", hwid: str | None = None) -> Mock:
    port = Mock()
    port.device = device
    port.description = description
    port.hwid = hwid
    return port


class TestIsCandidate:
    def test_usb_serial_included(self) -> None:
        port = _make_port("/dev/ttyUSB0", "USB Serial", "USB VID:PID=10C4:EA60")
        assert _is_candidate(port) is True

    def test_usb_modem_included(self) -> None:
        # macOS USB CDC devices appear as /dev/tty.usbmodem*
        port = _make_port("/dev/tty.usbmodem14101", "USB Modem", "USB VID:PID=0403:6001")
        assert _is_candidate(port) is True

    def test_usb_upper_case_included(self) -> None:
        port = _make_port("/dev/ttyUSB1", "USB-Serial CH340", "USB VID:PID=1A86:7523")
        assert _is_candidate(port) is True

    def test_bluetooth_excluded(self) -> None:
        port = _make_port("/dev/tty.Bluetooth-Incoming-Port", "Bluetooth")
        assert _is_candidate(port) is False

    def test_bluetooth_lowercase_excluded(self) -> None:
        port = _make_port("/dev/rfcomm0", "Bluetooth Serial")
        assert _is_candidate(port) is False

    def test_debug_virtual_excluded(self) -> None:
        port = _make_port("/dev/ttydebug0", "Debug UART")
        assert _is_candidate(port) is False

    def test_wlan_virtual_excluded(self) -> None:
        port = _make_port("/dev/ttywlan0", "WLAN UART")
        assert _is_candidate(port) is False

    def test_spi_virtual_excluded(self) -> None:
        port = _make_port("/dev/ttyspi0", "SPI bridge")
        assert _is_candidate(port) is False

    def test_plain_serial_without_usb_excluded(self) -> None:
        port = _make_port("/dev/ttyS0", "Standard Serial")
        assert _is_candidate(port) is False


class TestEnumerateSerialPorts:
    def test_usb_port_returned(self) -> None:
        port = _make_port("/dev/ttyUSB0", "USB Serial", "USB VID:PID=10C4:EA60")
        with patch("serial.tools.list_ports.comports", return_value=[port]):
            result = enumerate_serial_ports()
        assert len(result) == 1
        assert result[0] == SerialPortCandidate(
            device="/dev/ttyUSB0",
            description="USB Serial",
            hwid="USB VID:PID=10C4:EA60",
        )

    def test_bluetooth_excluded(self) -> None:
        port = _make_port("/dev/tty.Bluetooth-Incoming-Port", "Bluetooth")
        with patch("serial.tools.list_ports.comports", return_value=[port]):
            result = enumerate_serial_ports()
        assert result == []

    def test_virtual_ports_excluded(self) -> None:
        ports = [
            _make_port("/dev/ttydebug0", "Debug"),
            _make_port("/dev/ttywlan0", "WLAN"),
            _make_port("/dev/ttyspi0", "SPI"),
        ]
        with patch("serial.tools.list_ports.comports", return_value=ports):
            result = enumerate_serial_ports()
        assert result == []

    def test_empty_list(self) -> None:
        with patch("serial.tools.list_ports.comports", return_value=[]):
            result = enumerate_serial_ports()
        assert result == []

    def test_mixed_ports_only_usb_returned(self) -> None:
        ports = [
            _make_port("/dev/ttyUSB0", "USB Serial", "USB VID:PID=10C4:EA60"),
            _make_port("/dev/tty.Bluetooth-Incoming-Port", "Bluetooth"),
            _make_port("/dev/ttyS0", "Standard"),
        ]
        with patch("serial.tools.list_ports.comports", return_value=ports):
            result = enumerate_serial_ports()
        assert len(result) == 1
        assert result[0].device == "/dev/ttyUSB0"

    def test_returns_list_of_candidates(self) -> None:
        with patch("serial.tools.list_ports.comports", return_value=[]):
            result = enumerate_serial_ports()
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# dedupe_radios tests
# ---------------------------------------------------------------------------


class TestDedupeRadios:
    def test_same_radio_lan_and_serial_grouped(self) -> None:
        lan = [{"model": "IC-7610", "address": 0x98, "host": "192.168.1.100"}]
        serial = [{"model": "IC-7610", "address": 0x98, "port": "/dev/ttyUSB0", "baud": 19200}]

        result = dedupe_radios(lan, serial)

        assert len(result) == 1
        assert result[0]["model"] == "IC-7610"
        assert len(result[0]["lan"]) == 1
        assert len(result[0]["serial"]) == 1

    def test_different_radios_stay_separate(self) -> None:
        lan = [{"model": "IC-7610", "address": 0x98, "host": "192.168.1.100"}]
        serial = [{"model": "IC-705", "address": 0xA4, "port": "/dev/ttyUSB0", "baud": 19200}]

        result = dedupe_radios(lan, serial)

        assert len(result) == 2

    def test_lan_only_no_serial_section(self) -> None:
        lan = [{"model": "IC-7610", "address": 0x98, "host": "192.168.1.100"}]
        serial: list[dict] = []

        result = dedupe_radios(lan, serial)

        assert len(result) == 1
        assert len(result[0]["serial"]) == 0
        assert len(result[0]["lan"]) == 1

    def test_serial_only_no_lan_section(self) -> None:
        lan: list[dict] = []
        serial = [{"model": "IC-705", "address": 0xA4, "port": "/dev/ttyUSB0", "baud": 19200}]

        result = dedupe_radios(lan, serial)

        assert len(result) == 1
        assert len(result[0]["lan"]) == 0
        assert len(result[0]["serial"]) == 1

    def test_empty_both(self) -> None:
        assert dedupe_radios([], []) == []

    def test_two_lan_same_radio_merged(self) -> None:
        # Same model+address from two LAN entries — merged (unusual but defensive)
        lan = [
            {"model": "IC-7610", "address": 0x98, "host": "192.168.1.100"},
            {"model": "IC-7610", "address": 0x98, "host": "192.168.1.101"},
        ]
        result = dedupe_radios(lan, [])
        assert len(result) == 1
        assert len(result[0]["lan"]) == 2

    def test_lan_without_model_not_merged_with_serial(self) -> None:
        # LAN entry has no model/address → cannot be deduped → stays separate
        lan = [{"host": "192.168.1.100"}]
        serial = [{"model": "IC-7610", "address": 0x98, "port": "/dev/ttyUSB0", "baud": 19200}]

        result = dedupe_radios(lan, serial)

        assert len(result) == 2

    def test_multiple_lan_without_model_each_separate(self) -> None:
        # Two unidentified LAN radios → each is its own entry
        lan = [{"host": "192.168.1.100"}, {"host": "192.168.1.101"}]
        result = dedupe_radios(lan, [])
        assert len(result) == 2

    def test_return_type_is_list(self) -> None:
        result = dedupe_radios([], [])
        assert isinstance(result, list)

    def test_result_entry_has_required_keys(self) -> None:
        lan = [{"model": "IC-7610", "address": 0x98, "host": "192.168.1.100"}]
        result = dedupe_radios(lan, [])
        assert "model" in result[0]
        assert "lan" in result[0]
        assert "serial" in result[0]
