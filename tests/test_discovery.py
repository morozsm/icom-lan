"""Tests for serial port enumeration and candidate filtering."""

from unittest.mock import Mock, patch

import pytest

from icom_lan.discovery import SerialPortCandidate, _is_candidate, enumerate_serial_ports


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
