"""Regression tests for MOR-238 — clamp USB audio channels to device capability.

USB RX/TX channel count is derived from the codec (``_CHANNELS_BY_CODEC`` /
``_serial_audio_channels_for_codec``), not from the device. A mono USB codec
(1 input channel) whose profile lacks a mono ``codec_preference`` entry made the
driver request a 2-channel ``InputStream`` → PortAudio PaErrorCode -9998
("Invalid number of channels") → 0 RX frames / silent LIVE audio. This is the
class of bug behind MOR-236, which was worked around per-profile.

Sample rate already auto-negotiates against the device. These tests pin that the
channel count is now device-capability-aware too: ``UsbAudioDriver`` clamps the
open to ``device.input_channels`` (RX) / ``device.output_channels`` (TX), so any
mono/stereo USB codec self-heals with no per-profile entry — including the X6200
path with its ``codec_preference`` removed.
"""

from __future__ import annotations

import asyncio

import pytest

from rigplane.audio.backend import (
    AudioDeviceId,
    AudioDeviceInfo,
    FakeRxStream,
    FakeTxStream,
)
from rigplane.audio.usb_driver import UsbAudioDriver
from rigplane.backends.ic705.serial import Ic705SerialRadio
from rigplane.types import AudioCodec


class _StrictChannelBackend:
    """Fake backend that rejects any open whose channel count ≠ device capability.

    Reproduces PortAudio's -9998 ("Invalid number of channels") so a test only
    passes if the driver clamps the requested channels to what the device
    actually exposes before opening the stream.
    """

    def __init__(self, *, input_channels: int = 1, output_channels: int = 1) -> None:
        self._device = AudioDeviceInfo(
            id=AudioDeviceId(0),
            name="USB Audio Device",
            input_channels=input_channels,
            output_channels=output_channels,
            default_samplerate=48_000,
            is_default_input=True,
            is_default_output=True,
        )
        self.rx_streams: list[FakeRxStream] = []
        self.tx_streams: list[FakeTxStream] = []
        self.rx_open_channels: list[int] = []
        self.tx_open_channels: list[int] = []

    def list_devices(self) -> list[AudioDeviceInfo]:
        return [self._device]

    def check_sample_rate(
        self, device: AudioDeviceId, sample_rate: int, *, direction: str = "rx"
    ) -> bool:
        return sample_rate in (48_000, 24_000, 16_000, 8_000)

    def open_rx(
        self,
        device: AudioDeviceId,
        *,
        sample_rate: int = 48_000,
        channels: int = 1,
        frame_ms: int = 20,
    ) -> FakeRxStream:
        self.rx_open_channels.append(channels)
        if channels != self._device.input_channels:
            raise RuntimeError(
                "Error opening InputStream: Invalid number of channels "
                f"[requested {channels}, device exposes "
                f"{self._device.input_channels}]"
            )
        stream = FakeRxStream()
        self.rx_streams.append(stream)
        return stream

    def open_tx(
        self,
        device: AudioDeviceId,
        *,
        sample_rate: int = 48_000,
        channels: int = 1,
        frame_ms: int = 20,
    ) -> FakeTxStream:
        self.tx_open_channels.append(channels)
        if channels != self._device.output_channels:
            raise RuntimeError(
                "Error opening OutputStream: Invalid number of channels "
                f"[requested {channels}, device exposes "
                f"{self._device.output_channels}]"
            )
        stream = FakeTxStream()
        self.tx_streams.append(stream)
        return stream


class _FakeSerialCivLink:
    """Minimal serial CI-V link double so the radio reports ``connected``."""

    def __init__(self) -> None:
        self.connected = False
        self.ready = False
        self.healthy = False

    async def connect(self) -> None:
        self.connected = True
        self.ready = True
        self.healthy = True

    async def disconnect(self) -> None:
        self.connected = False
        self.ready = False
        self.healthy = False

    async def send(self, frame: bytes) -> None:
        _ = frame

    async def receive(self, timeout: float | None = None) -> bytes | None:
        await asyncio.sleep(0.02 if timeout is None else min(timeout, 0.02))
        return None


@pytest.mark.asyncio
async def test_rx_stereo_request_clamps_to_mono_device() -> None:
    """A 2-channel RX request opens at 1 ch on a mono-input device."""
    backend = _StrictChannelBackend(input_channels=1)
    driver = UsbAudioDriver(serial_port=None, backend=backend)
    received: list[bytes] = []

    await driver.start_rx(received.append, channels=2)

    assert driver.rx_running
    assert backend.rx_open_channels == [1]
    contract = driver.usb_audio_contract
    assert contract is not None and contract.rx is not None
    assert contract.rx.channels == 1
    assert contract.rx.channel_source == "device-clamp"
    assert contract.rx.fallback_reason == "channels-2-clamped-to-device-1"

    pcm = b"\x10\x20" * 480
    backend.rx_streams[0].inject_frame(pcm)
    assert received == [pcm]
    await driver.stop_rx()


@pytest.mark.asyncio
async def test_tx_stereo_request_clamps_to_mono_device() -> None:
    """A 2-channel TX request opens at 1 ch on a mono-output device."""
    backend = _StrictChannelBackend(output_channels=1)
    driver = UsbAudioDriver(serial_port=None, backend=backend)

    await driver.start_tx(channels=2)

    assert driver.tx_running
    assert backend.tx_open_channels == [1]
    contract = driver.usb_audio_contract
    assert contract is not None and contract.tx is not None
    assert contract.tx.channels == 1
    assert contract.tx.channel_source == "device-clamp"
    await driver.stop_tx()


@pytest.mark.asyncio
async def test_stereo_device_request_is_unchanged() -> None:
    """A stereo request on a stereo device is passed through verbatim."""
    backend = _StrictChannelBackend(input_channels=2, output_channels=2)
    driver = UsbAudioDriver(serial_port=None, backend=backend)

    await driver.start_rx(lambda _frame: None, channels=2)

    assert backend.rx_open_channels == [2]
    contract = driver.usb_audio_contract
    assert contract is not None and contract.rx is not None
    assert contract.rx.channels == 2
    assert contract.rx.channel_source == "requested"
    assert contract.rx.fallback_reason is None
    await driver.stop_rx()


@pytest.mark.asyncio
async def test_mono_request_on_stereo_device_not_upmixed() -> None:
    """A mono request is never raised to the device max (clamp only narrows)."""
    backend = _StrictChannelBackend(input_channels=2, output_channels=2)
    backend._device = AudioDeviceInfo(  # type: ignore[attr-defined]
        id=AudioDeviceId(0),
        name="USB Audio Device",
        input_channels=2,
        output_channels=2,
        default_samplerate=48_000,
        is_default_input=True,
        is_default_output=True,
    )
    driver = UsbAudioDriver(serial_port=None, backend=backend)

    # A 1-ch request must stay 1-ch even though the device exposes 2 inputs;
    # the strict backend would raise if the driver upmixed to 2.
    with pytest.raises(RuntimeError, match="Invalid number of channels"):
        await driver.start_rx(lambda _frame: None, channels=1)
    assert backend.rx_open_channels == [1]


@pytest.mark.asyncio
async def test_zero_channel_device_is_not_clamped_to_zero() -> None:
    """A device advertising 0 channels for the direction is left untouched.

    Clamping to 0 would silently open an unusable stream; instead the request
    passes through so the open surfaces the real selection error.
    """
    backend = _StrictChannelBackend(input_channels=0, output_channels=2)
    driver = UsbAudioDriver(serial_port=None, backend=backend)

    # Device selection picks the device; the open then requests the real
    # requested channel count (2), which the 0-input device rejects.
    with pytest.raises(Exception):
        await driver.start_rx(lambda _frame: None, channels=2)
    # The clamp must not have rewritten the request down to 0 channels.
    assert 0 not in backend.rx_open_channels


@pytest.mark.asyncio
async def test_x6200_path_self_heals_without_codec_preference() -> None:
    """The X6200 mono capture flows even when the codec asks for stereo.

    Proves the clamp alone suffices: the radio is built with the *default*
    stereo ``PCM_2CH_16BIT`` codec (i.e. as if the X6200 profile's
    ``codec_preference`` were removed). The serial path derives 2 channels from
    that codec, but the driver clamps the open to the mono device and RX PCM
    still reaches the radio callback. The profile entry stays in place as
    belt-and-suspenders; this test guards that the clamp is the load-bearing
    fix.
    """
    backend = _StrictChannelBackend(input_channels=1, output_channels=1)
    audio_driver = UsbAudioDriver(serial_port=None, backend=backend)
    radio = Ic705SerialRadio(
        device="/dev/tty.usbmodem-X6200",
        model="X6200",
        civ_link=_FakeSerialCivLink(),
        audio_driver=audio_driver,
    )
    # Emulate the X6200 profile with its mono ``codec_preference`` REMOVED: the
    # resolved codec falls back to the global stereo default. (The profile entry
    # stays in the tree as belt-and-suspenders; we override only the resolved
    # codec here to prove the clamp — not the profile entry — is load-bearing.)
    radio._audio_codec = AudioCodec.PCM_2CH_16BIT
    assert radio._serial_audio_channels_for_codec() == 2

    await radio.connect()
    packets: list[bytes] = []
    try:
        await radio.start_audio_rx_opus(lambda pkt: packets.append(pkt.data))
        assert len(backend.rx_streams) == 1, "RX capture did not open"
        assert backend.rx_open_channels == [1], "channels were not clamped to mono"
        pcm_frame = b"\xab\xcd" * 480
        backend.rx_streams[0].inject_frame(pcm_frame)
        await asyncio.sleep(0.01)
        # PCM codec → no Opus transcode → raw mono PCM forwarded verbatim.
        assert packets == [pcm_frame]
    finally:
        await radio.stop_audio_rx_opus()
        await radio.disconnect()
