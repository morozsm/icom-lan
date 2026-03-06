"""Deterministic unit tests for production USB audio driver contracts."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from icom_lan.backends.icom7610.drivers.usb_audio import (
    AudioDeviceSelectionError,
    AudioDriverLifecycleError,
    UsbAudioDevice,
    UsbAudioDriver,
    select_usb_audio_devices,
)


@dataclass(slots=True)
class _FakeArray:
    raw: bytes

    def reshape(self, _rows: int, _cols: int) -> "_FakeArray":
        return self

    def tobytes(self) -> bytes:
        return self.raw


class _FakeNumpy:
    int16 = "int16"

    @staticmethod
    def frombuffer(data: bytes, dtype: object) -> _FakeArray:
        _ = dtype
        return _FakeArray(bytes(data))


class _FakeInputStream:
    def __init__(self, backend: "_FakeSoundDevice", channels: int, blocksize: int) -> None:
        self._backend = backend
        self._channels = channels
        self._blocksize = blocksize
        self.active = False
        self.stopped = False
        self.closed = False

    def start(self) -> None:
        self.active = True

    def stop(self) -> None:
        self.active = False
        self.stopped = True

    def close(self) -> None:
        self.closed = True

    def read(self, _frames: int) -> tuple[_FakeArray, bool]:
        if self._backend.rx_frames:
            frame = self._backend.rx_frames.pop(0)
            return _FakeArray(frame), False
        silence = b"\x00\x00" * self._blocksize * self._channels
        return _FakeArray(silence), False


class _FakeOutputStream:
    def __init__(self, backend: "_FakeSoundDevice") -> None:
        self._backend = backend
        self.active = False
        self.stopped = False
        self.closed = False

    def start(self) -> None:
        self.active = True

    def stop(self) -> None:
        self.active = False
        self.stopped = True

    def close(self) -> None:
        self.closed = True

    def write(self, data: _FakeArray) -> None:
        self._backend.tx_frames.append(data.tobytes())


class _FakeSoundDevice:
    def __init__(
        self,
        devices: list[dict[str, object]],
        *,
        default_input: int,
        default_output: int,
    ) -> None:
        self._devices = list(devices)
        self.default = SimpleNamespace(device=(default_input, default_output))
        self.rx_frames: list[bytes] = []
        self.tx_frames: list[bytes] = []
        self.input_streams: list[_FakeInputStream] = []
        self.output_streams: list[_FakeOutputStream] = []

    def query_devices(self) -> list[dict[str, object]]:
        return list(self._devices)

    def InputStream(  # noqa: N802
        self,
        *,
        samplerate: int,
        channels: int,
        dtype: str,
        device: int,
        blocksize: int,
        latency: str,
    ) -> _FakeInputStream:
        _ = (samplerate, dtype, device, latency)
        stream = _FakeInputStream(self, channels=channels, blocksize=blocksize)
        self.input_streams.append(stream)
        return stream

    def OutputStream(  # noqa: N802
        self,
        *,
        samplerate: int,
        channels: int,
        dtype: str,
        device: int,
        blocksize: int,
        latency: str,
    ) -> _FakeOutputStream:
        _ = (samplerate, channels, dtype, device, blocksize, latency)
        stream = _FakeOutputStream(self)
        self.output_streams.append(stream)
        return stream


def _devices_fixture() -> list[dict[str, object]]:
    return [
        {
            "index": 0,
            "name": "MacBook Pro Speakers",
            "max_input_channels": 0,
            "max_output_channels": 2,
            "default_samplerate": 48_000,
        },
        {
            "index": 1,
            "name": "USB Audio CODEC",
            "max_input_channels": 2,
            "max_output_channels": 2,
            "default_samplerate": 48_000,
        },
        {
            "index": 2,
            "name": "IC-7610 USB Audio",
            "max_input_channels": 2,
            "max_output_channels": 2,
            "default_samplerate": 48_000,
        },
    ]


def test_select_usb_audio_devices_explicit_overrides_take_precedence() -> None:
    devices = [
        UsbAudioDevice(index=1, name="A", input_channels=2, output_channels=2),
        UsbAudioDevice(index=2, name="B", input_channels=2, output_channels=2),
    ]
    selected_rx, selected_tx = select_usb_audio_devices(
        devices,
        rx_device="B",
        tx_device="A",
    )
    assert selected_rx.name == "B"
    assert selected_tx.name == "A"


def test_select_usb_audio_devices_auto_detect_prefers_icom_like_name() -> None:
    devices = [
        UsbAudioDevice(
            index=0,
            name="Default System Input",
            input_channels=2,
            output_channels=0,
            is_default_input=True,
        ),
        UsbAudioDevice(
            index=1,
            name="USB Audio CODEC",
            input_channels=2,
            output_channels=2,
        ),
        UsbAudioDevice(
            index=2,
            name="IC-7610 USB Audio",
            input_channels=2,
            output_channels=2,
        ),
    ]
    selected_rx, selected_tx = select_usb_audio_devices(devices)
    assert selected_rx.name == "IC-7610 USB Audio"
    assert selected_tx.name == "IC-7610 USB Audio"


def test_select_usb_audio_devices_invalid_override_raises_clear_error() -> None:
    devices = [
        UsbAudioDevice(index=1, name="USB Audio CODEC", input_channels=2, output_channels=2),
    ]
    with pytest.raises(AudioDeviceSelectionError, match="Unknown RX device"):
        select_usb_audio_devices(devices, rx_device="Not Existing")


def test_select_usb_audio_devices_missing_directional_capability_raises() -> None:
    devices = [
        UsbAudioDevice(index=1, name="InputOnly", input_channels=2, output_channels=0),
    ]
    with pytest.raises(AudioDeviceSelectionError, match="No suitable TX USB audio device"):
        select_usb_audio_devices(devices)


@pytest.mark.asyncio
async def test_usb_audio_driver_lifecycle_start_stop_and_io() -> None:
    fake_sd = _FakeSoundDevice(
        _devices_fixture(),
        default_input=1,
        default_output=1,
    )
    fake_np = _FakeNumpy()
    driver = UsbAudioDriver(
        dependency_loader=lambda: (fake_sd, fake_np),
    )

    received_frames: list[bytes] = []
    pcm_frame = b"\x11\x22" * 960
    fake_sd.rx_frames.append(pcm_frame)

    await driver.start_rx(received_frames.append)
    await asyncio.sleep(0.05)
    assert driver.rx_running is True
    assert received_frames
    assert received_frames[0] == pcm_frame

    await driver.start_tx()
    await driver.push_tx_pcm(pcm_frame)
    await asyncio.sleep(0.05)
    assert driver.tx_running is True
    assert fake_sd.tx_frames
    assert fake_sd.tx_frames[0] == pcm_frame

    await driver.stop_tx()
    await driver.stop_rx()
    assert driver.rx_running is False
    assert driver.tx_running is False
    assert fake_sd.input_streams[0].closed is True
    assert fake_sd.output_streams[0].closed is True


@pytest.mark.asyncio
async def test_usb_audio_driver_double_start_and_missing_tx_guardrails() -> None:
    fake_sd = _FakeSoundDevice(
        _devices_fixture(),
        default_input=1,
        default_output=1,
    )
    driver = UsbAudioDriver(
        dependency_loader=lambda: (fake_sd, _FakeNumpy()),
    )
    await driver.start_rx(lambda _frame: None)
    with pytest.raises(AudioDriverLifecycleError, match="already started"):
        await driver.start_rx(lambda _frame: None)
    with pytest.raises(AudioDriverLifecycleError, match="Audio TX stream is not started"):
        await driver.push_tx_pcm(b"\x00\x01" * 960)
    await driver.stop_rx()
    await driver.stop_rx()  # idempotent


@pytest.mark.asyncio
async def test_usb_audio_driver_missing_optional_dependencies_is_actionable() -> None:
    def _missing_sounddevice() -> tuple[object, object]:
        raise ImportError("No module named 'sounddevice'")

    driver = UsbAudioDriver(dependency_loader=_missing_sounddevice)
    with pytest.raises(ImportError, match="pip install icom-lan\\[bridge\\]"):
        await driver.start_rx(lambda _frame: None)
