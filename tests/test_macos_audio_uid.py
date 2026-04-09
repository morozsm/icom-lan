"""Tests for macOS CoreAudio UID integration in UsbAudioDevice."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from icom_lan.audio.usb_driver import (
    UsbAudioDevice,
    list_usb_audio_devices,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_sd_module(devices: list[dict]) -> SimpleNamespace:
    """Build a fake sounddevice module that returns *devices*."""
    return SimpleNamespace(
        query_devices=lambda: devices,
        default=SimpleNamespace(device=[0, 1]),
    )


_FAKE_DEVICES = [
    {
        "index": 0,
        "name": "USB Audio CODEC",
        "max_input_channels": 1,
        "max_output_channels": 2,
        "default_samplerate": 48000,
    },
    {
        "index": 1,
        "name": "MacBook Pro Speakers",
        "max_input_channels": 0,
        "max_output_channels": 2,
        "default_samplerate": 44100,
    },
]

_FAKE_UID_MAP = {
    "USB Audio CODEC": "AppleUSBAudioEngine:BurrBrown:USB Audio CODEC:1234:1,2",
    "MacBook Pro Speakers": "BuiltInSpeakerDevice",
}


# ---------------------------------------------------------------------------
# Tests: platform_uid field basics
# ---------------------------------------------------------------------------


class TestPlatformUidField:
    def test_default_empty(self) -> None:
        dev = UsbAudioDevice(index=0, name="test", input_channels=1, output_channels=0)
        assert dev.platform_uid == ""

    def test_explicit_uid(self) -> None:
        dev = UsbAudioDevice(
            index=0,
            name="test",
            input_channels=1,
            output_channels=0,
            platform_uid="some-stable-uid",
        )
        assert dev.platform_uid == "some-stable-uid"


# ---------------------------------------------------------------------------
# Tests: list_usb_audio_devices with monkeypatched UID map
# ---------------------------------------------------------------------------


class TestListDevicesWithUid:
    def test_uid_populated_via_macos_helper(self) -> None:
        """When _get_uid_map returns data, platform_uid is set."""
        sd = _make_sd_module(_FAKE_DEVICES)
        with patch(
            "icom_lan.audio.usb_driver._get_uid_map",
            return_value=_FAKE_UID_MAP,
        ):
            devices = list_usb_audio_devices(sd)

        assert len(devices) == 2
        assert devices[0].platform_uid == _FAKE_UID_MAP["USB Audio CODEC"]
        assert devices[0].platform_uid != ""
        assert devices[1].platform_uid == _FAKE_UID_MAP["MacBook Pro Speakers"]

    def test_uid_empty_when_helper_returns_empty(self) -> None:
        """When _get_uid_map returns {}, platform_uid stays empty."""
        sd = _make_sd_module(_FAKE_DEVICES)
        with patch(
            "icom_lan.audio.usb_driver._get_uid_map",
            return_value={},
        ):
            devices = list_usb_audio_devices(sd)

        assert all(d.platform_uid == "" for d in devices)

    def test_uid_partial_match(self) -> None:
        """Only devices whose name is in the UID map get a UID."""
        sd = _make_sd_module(_FAKE_DEVICES)
        partial_map = {"USB Audio CODEC": "uid-for-usb-only"}
        with patch(
            "icom_lan.audio.usb_driver._get_uid_map",
            return_value=partial_map,
        ):
            devices = list_usb_audio_devices(sd)

        assert devices[0].platform_uid == "uid-for-usb-only"
        assert devices[1].platform_uid == ""

    def test_other_fields_unchanged(self) -> None:
        """Adding platform_uid must not break existing fields."""
        sd = _make_sd_module(_FAKE_DEVICES)
        with patch(
            "icom_lan.audio.usb_driver._get_uid_map",
            return_value=_FAKE_UID_MAP,
        ):
            devices = list_usb_audio_devices(sd)

        dev = devices[0]
        assert dev.index == 0
        assert dev.name == "USB Audio CODEC"
        assert dev.input_channels == 1
        assert dev.output_channels == 2
        assert dev.default_samplerate == 48_000
        assert dev.supports_rx is True
        assert dev.supports_tx is True
        assert dev.duplex is True


# ---------------------------------------------------------------------------
# Tests: _get_uid_map fallback behaviour
# ---------------------------------------------------------------------------


class TestGetUidMapFallback:
    def test_returns_empty_on_non_darwin(self) -> None:
        """On non-macOS, _get_uid_map must return {}."""
        from icom_lan.audio.usb_driver import _get_uid_map

        with patch("icom_lan.audio.usb_driver.sys") as mock_sys:
            mock_sys.platform = "linux"
            result = _get_uid_map()
        assert result == {}

    def test_returns_empty_on_import_error(self) -> None:
        """If the macOS helper fails to import, _get_uid_map returns {}."""
        from icom_lan.audio.usb_driver import _get_uid_map

        with patch("icom_lan.audio.usb_driver.sys") as mock_sys:
            mock_sys.platform = "darwin"
            with patch(
                "icom_lan.audio._macos_uid.get_device_uid_map",
                side_effect=OSError("no CoreAudio"),
            ):
                result = _get_uid_map()
        assert result == {}
