"""Deterministic unit tests for USB audio stub driver contracts."""

from __future__ import annotations

import pytest

from icom_lan.backends.icom7610.drivers.usb_audio_stub import (
    AudioDeviceSelectionError,
    AudioDriverLifecycleError,
    UsbAudioDevice,
    UsbAudioDriverStub,
    select_usb_audio_device,
)


def test_select_usb_audio_device_prefers_explicit_name() -> None:
    devices = [
        UsbAudioDevice(name="Built-in", input_channels=2, output_channels=2),
        UsbAudioDevice(name="USB CODEC", input_channels=2, output_channels=2),
    ]
    selected = select_usb_audio_device(devices, preferred_name="USB CODEC")
    assert selected.name == "USB CODEC"


def test_select_usb_audio_device_requires_duplex() -> None:
    devices = [
        UsbAudioDevice(name="InputOnly", input_channels=1, output_channels=0),
    ]
    with pytest.raises(AudioDeviceSelectionError):
        select_usb_audio_device(devices, require_duplex=True)


def test_select_usb_audio_device_uses_default_when_available() -> None:
    devices = [
        UsbAudioDevice(name="Fallback", input_channels=2, output_channels=2),
        UsbAudioDevice(name="DefaultDevice", input_channels=2, output_channels=2, is_default=True),
    ]
    selected = select_usb_audio_device(devices)
    assert selected.name == "DefaultDevice"


@pytest.mark.asyncio
async def test_usb_audio_driver_lifecycle_start_stop() -> None:
    device = UsbAudioDevice(name="USB", input_channels=2, output_channels=2)
    driver = UsbAudioDriverStub(device)
    await driver.start_rx()
    await driver.start_tx()
    assert driver.rx_running is True
    assert driver.tx_running is True

    await driver.stop_tx()
    await driver.stop_rx()
    assert driver.rx_running is False
    assert driver.tx_running is False


@pytest.mark.asyncio
async def test_usb_audio_driver_double_start_is_rejected() -> None:
    device = UsbAudioDevice(name="USB", input_channels=2, output_channels=2)
    driver = UsbAudioDriverStub(device)
    await driver.start_rx()
    with pytest.raises(AudioDriverLifecycleError):
        await driver.start_rx()


@pytest.mark.asyncio
async def test_usb_audio_driver_injected_start_error_path() -> None:
    device = UsbAudioDevice(name="USB", input_channels=2, output_channels=2)
    driver = UsbAudioDriverStub(device, fail_on_start_tx=True)
    with pytest.raises(AudioDriverLifecycleError):
        await driver.start_tx()
