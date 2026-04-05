"""Tests for Yaesu CAT radio audio integration layer."""

from __future__ import annotations

import asyncio
from typing import Any, Callable
from unittest.mock import AsyncMock

import pytest

from icom_lan.audio import AudioPacket
from icom_lan.backends.yaesu_cat.radio import YaesuCatRadio
from icom_lan.exceptions import AudioFormatError
from icom_lan.types import AudioCodec


# ---------------------------------------------------------------------------
# Fake audio driver — mimics UsbAudioDriver public API without hardware deps
# ---------------------------------------------------------------------------

class FakeAudioDriver:
    """In-memory stand-in for UsbAudioDriver."""

    def __init__(self) -> None:
        self._rx_task: asyncio.Task[None] | None = None
        self._tx_task: asyncio.Task[None] | None = None
        self._rx_callback: Callable[[bytes], None] | None = None
        self._tx_queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=64)

    # -- properties expected by get_audio_stats ------------------------------

    @property
    def rx_running(self) -> bool:
        return self._rx_task is not None

    @property
    def tx_running(self) -> bool:
        return self._tx_task is not None

    # -- lifecycle -----------------------------------------------------------

    async def start_rx(
        self,
        callback: Callable[[bytes], None] | None = None,
        *,
        sample_rate: int | None = None,
        channels: int | None = None,
        frame_ms: int | None = None,
    ) -> None:
        self._rx_callback = callback
        self._rx_task = asyncio.ensure_future(asyncio.sleep(3600))

    async def stop_rx(self) -> None:
        if self._rx_task is not None:
            self._rx_task.cancel()
            try:
                await self._rx_task
            except asyncio.CancelledError:
                pass
            self._rx_task = None
        self._rx_callback = None

    async def start_tx(
        self,
        *,
        sample_rate: int | None = None,
        channels: int | None = None,
        frame_ms: int | None = None,
    ) -> None:
        self._tx_task = asyncio.ensure_future(asyncio.sleep(3600))

    async def stop_tx(self) -> None:
        if self._tx_task is not None:
            self._tx_task.cancel()
            try:
                await self._tx_task
            except asyncio.CancelledError:
                pass
            self._tx_task = None
        self._tx_queue = asyncio.Queue(maxsize=64)

    async def push_tx_pcm(self, frame: bytes) -> None:
        await self._tx_queue.put(frame)

    def inject_rx_frame(self, data: bytes) -> None:
        """Simulate receiving a PCM frame from the hardware."""
        if self._rx_callback is not None:
            self._rx_callback(data)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def fake_driver() -> FakeAudioDriver:
    return FakeAudioDriver()


@pytest.fixture
def radio(fake_driver: FakeAudioDriver, monkeypatch: pytest.MonkeyPatch) -> YaesuCatRadio:
    """Create a YaesuCatRadio with faked transport + audio driver."""
    # Patch transport so connect() doesn't try to open a real serial port
    monkeypatch.setattr(
        "icom_lan.backends.yaesu_cat.transport.YaesuCatTransport.connect",
        AsyncMock(),
    )
    monkeypatch.setattr(
        "icom_lan.backends.yaesu_cat.transport.YaesuCatTransport.close",
        AsyncMock(),
    )
    monkeypatch.setattr(
        "icom_lan.backends.yaesu_cat.transport.YaesuCatTransport.connected",
        True,
    )
    r = YaesuCatRadio(
        device="/dev/fake0",
        audio_driver=fake_driver,  # type: ignore[arg-type]
    )
    return r


# ---------------------------------------------------------------------------
# audio_codec property
# ---------------------------------------------------------------------------

class TestAudioCodecProperty:
    def test_returns_pcm_16bit_mono(self, radio: YaesuCatRadio) -> None:
        assert radio.audio_codec == AudioCodec.PCM_1CH_16BIT

    def test_is_not_opus(self, radio: YaesuCatRadio) -> None:
        assert radio.audio_codec not in (AudioCodec.OPUS_1CH, AudioCodec.OPUS_2CH)


# ---------------------------------------------------------------------------
# get_audio_stats
# ---------------------------------------------------------------------------

class TestGetAudioStats:
    @pytest.mark.asyncio
    async def test_both_idle(self, radio: YaesuCatRadio) -> None:
        stats = await radio.get_audio_stats()
        assert stats["rx_active"] is False
        assert stats["tx_active"] is False
        assert stats["sample_rate"] == 48000

    @pytest.mark.asyncio
    async def test_rx_active(self, radio: YaesuCatRadio) -> None:
        await radio.connect()
        await radio.start_audio_rx_opus(lambda pkt: None)
        stats = await radio.get_audio_stats()
        assert stats["rx_active"] is True
        assert stats["tx_active"] is False
        await radio.stop_audio_rx_opus()

    @pytest.mark.asyncio
    async def test_tx_active(self, radio: YaesuCatRadio) -> None:
        await radio.connect()
        await radio.start_audio_tx_pcm()
        stats = await radio.get_audio_stats()
        assert stats["tx_active"] is True
        assert stats["rx_active"] is False
        await radio.stop_audio_tx_pcm()

    @pytest.mark.asyncio
    async def test_both_active(self, radio: YaesuCatRadio) -> None:
        await radio.connect()
        await radio.start_audio_rx_opus(lambda pkt: None)
        await radio.start_audio_tx_pcm()
        stats = await radio.get_audio_stats()
        assert stats["rx_active"] is True
        assert stats["tx_active"] is True
        await radio.stop_audio_rx_opus()
        await radio.stop_audio_tx_pcm()


# ---------------------------------------------------------------------------
# RX audio flow
# ---------------------------------------------------------------------------

class TestRxAudio:
    @pytest.mark.asyncio
    async def test_start_rx_opus_wraps_pcm_in_audio_packet(
        self, radio: YaesuCatRadio, fake_driver: FakeAudioDriver
    ) -> None:
        received: list[AudioPacket] = []
        await radio.connect()
        await radio.start_audio_rx_opus(received.append)

        fake_driver.inject_rx_frame(b"\x00" * 960)
        assert len(received) == 1
        pkt = received[0]
        assert isinstance(pkt, AudioPacket)
        assert pkt.data == b"\x00" * 960
        assert pkt.ident == 0x9781
        await radio.stop_audio_rx_opus()

    @pytest.mark.asyncio
    async def test_rx_sequence_increments(
        self, radio: YaesuCatRadio, fake_driver: FakeAudioDriver
    ) -> None:
        received: list[AudioPacket] = []
        await radio.connect()
        await radio.start_audio_rx_opus(received.append)

        for _ in range(3):
            fake_driver.inject_rx_frame(b"\x01" * 960)

        assert [p.send_seq for p in received] == [0, 1, 2]
        await radio.stop_audio_rx_opus()

    @pytest.mark.asyncio
    async def test_start_pcm_rx_delivers_raw_bytes(
        self, radio: YaesuCatRadio, fake_driver: FakeAudioDriver
    ) -> None:
        received: list[bytes | None] = []
        await radio.connect()
        await radio.start_audio_rx_pcm(received.append)

        fake_driver.inject_rx_frame(b"\xAB" * 960)
        assert received == [b"\xAB" * 960]
        await radio.stop_audio_rx_pcm()

    @pytest.mark.asyncio
    async def test_stop_rx_opus_clears_state(
        self, radio: YaesuCatRadio, fake_driver: FakeAudioDriver
    ) -> None:
        await radio.connect()
        await radio.start_audio_rx_opus(lambda pkt: None)
        assert fake_driver.rx_running
        await radio.stop_audio_rx_opus()
        assert not fake_driver.rx_running

    @pytest.mark.asyncio
    async def test_stop_rx_pcm_clears_state(
        self, radio: YaesuCatRadio, fake_driver: FakeAudioDriver
    ) -> None:
        await radio.connect()
        await radio.start_audio_rx_pcm(lambda data: None)
        assert fake_driver.rx_running
        await radio.stop_audio_rx_pcm()
        assert not fake_driver.rx_running


# ---------------------------------------------------------------------------
# TX audio flow
# ---------------------------------------------------------------------------

class TestTxAudio:
    @pytest.mark.asyncio
    async def test_push_tx_delegates_to_driver(
        self, radio: YaesuCatRadio, fake_driver: FakeAudioDriver
    ) -> None:
        await radio.connect()
        await radio.start_audio_tx_pcm()
        frame = b"\x42" * 1920
        await radio.push_pcm_tx(frame)
        queued = await asyncio.wait_for(fake_driver._tx_queue.get(), timeout=1)
        assert queued == frame
        await radio.stop_audio_tx_pcm()

    @pytest.mark.asyncio
    async def test_stop_tx_clears_state(
        self, radio: YaesuCatRadio, fake_driver: FakeAudioDriver
    ) -> None:
        await radio.connect()
        await radio.start_audio_tx_pcm()
        assert fake_driver.tx_running
        await radio.stop_audio_tx_pcm()
        assert not fake_driver.tx_running

    @pytest.mark.asyncio
    async def test_push_pcm_tx_rejects_non_bytes(self, radio: YaesuCatRadio) -> None:
        await radio.connect()
        with pytest.raises(TypeError, match="bytes"):
            await radio.push_pcm_tx("not bytes")  # type: ignore[arg-type]

    @pytest.mark.asyncio
    async def test_push_pcm_tx_rejects_empty(self, radio: YaesuCatRadio) -> None:
        await radio.connect()
        with pytest.raises(ValueError, match="empty"):
            await radio.push_pcm_tx(b"")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class TestValidation:
    @pytest.mark.asyncio
    async def test_jitter_depth_negative_raises(self, radio: YaesuCatRadio) -> None:
        await radio.connect()
        with pytest.raises(ValueError, match="jitter_depth"):
            await radio.start_audio_rx_opus(lambda pkt: None, jitter_depth=-1)

    @pytest.mark.asyncio
    async def test_jitter_depth_bool_raises(self, radio: YaesuCatRadio) -> None:
        await radio.connect()
        with pytest.raises(TypeError, match="jitter_depth"):
            await radio.start_audio_rx_opus(lambda pkt: None, jitter_depth=True)  # type: ignore[arg-type]

    @pytest.mark.asyncio
    async def test_pcm_rx_bad_frame_format(self, radio: YaesuCatRadio) -> None:
        await radio.connect()
        with pytest.raises(AudioFormatError):
            await radio.start_audio_rx_pcm(
                lambda data: None, sample_rate=44100, frame_ms=7
            )

    @pytest.mark.asyncio
    async def test_tx_bad_frame_format(self, radio: YaesuCatRadio) -> None:
        await radio.connect()
        with pytest.raises(AudioFormatError):
            await radio.start_audio_tx_pcm(sample_rate=44100, frame_ms=7)

    @pytest.mark.asyncio
    async def test_rx_opus_non_callable_raises(self, radio: YaesuCatRadio) -> None:
        await radio.connect()
        with pytest.raises(TypeError, match="callable"):
            await radio.start_audio_rx_opus("not_callable")  # type: ignore[arg-type]

    @pytest.mark.asyncio
    async def test_rx_pcm_non_callable_raises(self, radio: YaesuCatRadio) -> None:
        await radio.connect()
        with pytest.raises(TypeError, match="callable"):
            await radio.start_audio_rx_pcm("not_callable")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# AudioBus lazy init
# ---------------------------------------------------------------------------

class TestAudioBus:
    def test_audio_bus_lazy_init(self, radio: YaesuCatRadio) -> None:
        bus1 = radio.audio_bus
        bus2 = radio.audio_bus
        assert bus1 is bus2

    def test_audio_bus_is_not_none(self, radio: YaesuCatRadio) -> None:
        assert radio.audio_bus is not None


# ---------------------------------------------------------------------------
# Disconnect stops audio
# ---------------------------------------------------------------------------

class TestDisconnect:
    @pytest.mark.asyncio
    async def test_disconnect_stops_audio(
        self, radio: YaesuCatRadio, fake_driver: FakeAudioDriver
    ) -> None:
        await radio.connect()
        await radio.start_audio_rx_opus(lambda pkt: None)
        await radio.start_audio_tx_pcm()
        assert fake_driver.rx_running
        assert fake_driver.tx_running
        await radio.disconnect()
        assert not fake_driver.rx_running
        assert not fake_driver.tx_running
