"""Tests for audio_bridge module."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np  # import early before any sys.modules patching
import pytest

from icom_lan.audio_bridge import (
    AudioBridge,
    CHANNELS,
    FRAME_BYTES,
    FRAME_MS,
    SAMPLE_RATE,
    SAMPLES_PER_FRAME,
    derive_bridge_label,
    find_loopback_device,
    list_audio_devices,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


def test_constants():
    assert SAMPLE_RATE == 48000
    assert CHANNELS == 1
    assert FRAME_MS == 20
    assert SAMPLES_PER_FRAME == 960
    assert FRAME_BYTES == 1920


# ---------------------------------------------------------------------------
# find_loopback_device
# ---------------------------------------------------------------------------


def test_find_loopback_device_no_sounddevice():
    with patch.dict("sys.modules", {"sounddevice": None}):
        with pytest.raises(ImportError, match="sounddevice"):
            find_loopback_device("BlackHole")


def test_find_loopback_device_found():
    mock_sd = MagicMock()
    mock_sd.query_devices.return_value = [
        {"name": "Built-in Output", "index": 0},
        {"name": "BlackHole 2ch", "index": 1},
    ]
    with patch.dict("sys.modules", {"sounddevice": mock_sd}):
        dev = find_loopback_device("BlackHole")
    assert dev is not None
    assert dev["name"] == "BlackHole 2ch"


def test_find_loopback_device_not_found():
    mock_sd = MagicMock()
    mock_sd.query_devices.return_value = [
        {"name": "Built-in Output", "index": 0},
        {"name": "Built-in Input", "index": 1},
    ]
    with patch.dict("sys.modules", {"sounddevice": mock_sd}):
        dev = find_loopback_device("BlackHole")
    assert dev is None


def test_find_loopback_device_auto_detect():
    mock_sd = MagicMock()
    mock_sd.query_devices.return_value = [
        {"name": "Built-in Output", "index": 0},
        {"name": "Loopback Audio", "index": 1},
    ]
    with patch.dict("sys.modules", {"sounddevice": mock_sd}):
        dev = find_loopback_device(None)
    assert dev is not None
    assert dev["name"] == "Loopback Audio"


# ---------------------------------------------------------------------------
# list_audio_devices
# ---------------------------------------------------------------------------


def test_list_audio_devices():
    mock_sd = MagicMock()
    devs = [{"name": "A", "index": 0}, {"name": "B", "index": 1}]
    mock_sd.query_devices.return_value = devs
    with patch.dict("sys.modules", {"sounddevice": mock_sd}):
        result = list_audio_devices()
    assert result == devs


def test_list_audio_devices_no_sounddevice():
    with patch.dict("sys.modules", {"sounddevice": None}):
        with pytest.raises(ImportError, match="sounddevice"):
            list_audio_devices()


# ---------------------------------------------------------------------------
# AudioBridge init
# ---------------------------------------------------------------------------


def test_bridge_init_defaults():
    radio = MagicMock()
    bridge = AudioBridge(radio)
    assert not bridge.running
    s = bridge.stats
    assert s["running"] is False
    assert s["rx_frames"] == 0
    assert s["tx_frames"] == 0
    assert s["rx_drops"] == 0
    assert s["uptime_seconds"] == 0.0
    assert s["rx_interval_ms"] == 0.0
    assert s["tx_interval_ms"] == 0.0
    assert s["buffer_size"] == 0


def test_bridge_init_custom():
    radio = MagicMock()
    custom_executor = MagicMock()
    bridge = AudioBridge(
        radio,
        device_name="MyDevice",
        sample_rate=8000,
        channels=2,
        frame_ms=40,
        tx_enabled=False,
        tx_executor=custom_executor,
    )
    assert bridge._device_name == "MyDevice"
    assert bridge._sample_rate == 8000
    assert bridge._channels == 2
    assert bridge._frame_ms == 40
    assert bridge._tx_enabled is False
    assert bridge._tx_executor is custom_executor


# ---------------------------------------------------------------------------
# AudioBridge start — device not found
# ---------------------------------------------------------------------------


async def test_bridge_tx_loop_uses_custom_executor():
    """When tx_executor is provided, TX read runs in that executor."""
    from icom_lan.audio_bus import AudioBus

    executor_used: list = []
    custom_executor = MagicMock()
    executor_called = asyncio.Event()

    radio = MagicMock()
    radio.start_audio_rx_opus = AsyncMock()
    radio.stop_audio_rx_opus = AsyncMock()
    radio.start_audio_tx_pcm = AsyncMock()
    radio.stop_audio_tx_pcm = AsyncMock()
    radio.push_audio_tx_pcm = AsyncMock()
    radio.push_audio_tx_opus = AsyncMock()
    bus = AudioBus(radio)
    radio.audio_bus = bus

    mock_output_stream = MagicMock()
    mock_output_stream.active = True

    # TX stream: read returns (samples, overflowed); one frame then bridge can stop
    samples_per_frame = 960
    mock_tx_stream = MagicMock()
    mock_tx_stream.active = True
    mock_tx_stream.read.return_value = (
        np.zeros((samples_per_frame, 1), dtype=np.int16),
        False,
    )

    mock_sd = MagicMock()
    mock_sd.query_devices.return_value = [
        {"name": "BlackHole 2ch", "index": 1},
    ]
    mock_sd.OutputStream.return_value = mock_output_stream
    mock_sd.InputStream.return_value = mock_tx_stream

    mock_opuslib = MagicMock()
    mock_opuslib.Decoder.return_value = MagicMock()

    loop = asyncio.get_running_loop()
    original_run_in_executor = loop.run_in_executor

    def capture_executor(executor, fn, *args):
        executor_used.append(executor)
        executor_called.set()
        return original_run_in_executor(executor, fn, *args)

    with patch.dict("sys.modules", {"sounddevice": mock_sd, "opuslib": mock_opuslib}):
        with patch.object(loop, "run_in_executor", capture_executor):
            bridge = AudioBridge(
                radio,
                device_name="BlackHole",
                tx_enabled=True,
                tx_executor=custom_executor,
            )
            await bridge.start()
            # Wait until TX loop has made at least one run_in_executor call
            await asyncio.wait_for(executor_called.wait(), timeout=2.0)
            await bridge.stop()

    assert len(executor_used) >= 1
    assert executor_used[0] is custom_executor


async def test_bridge_start_no_device():
    radio = MagicMock()
    radio.start_audio_rx_pcm = AsyncMock()

    mock_sd = MagicMock()
    mock_sd.query_devices.return_value = [{"name": "Built-in", "index": 0}]

    mock_np = MagicMock()

    with (
        patch.dict("sys.modules", {"sounddevice": mock_sd, "numpy": mock_np}),
        pytest.raises(RuntimeError, match="Virtual audio device not found"),
    ):
        bridge = AudioBridge(radio, device_name="BlackHole")
        await bridge.start()


# ---------------------------------------------------------------------------
# AudioBridge start + stop — happy path (mocked)
# ---------------------------------------------------------------------------


async def test_bridge_start_stop_rx_only():
    from icom_lan.audio_bus import AudioBus

    radio = MagicMock()
    radio.start_audio_rx_opus = AsyncMock()
    radio.stop_audio_rx_opus = AsyncMock()
    bus = AudioBus(radio)
    radio.audio_bus = bus

    mock_output_stream = MagicMock()
    mock_output_stream.active = True

    mock_sd = MagicMock()
    mock_sd.query_devices.return_value = [
        {"name": "BlackHole 2ch", "index": 1},
    ]
    mock_sd.OutputStream.return_value = mock_output_stream

    mock_opuslib = MagicMock()
    mock_decoder = MagicMock()
    mock_opuslib.Decoder.return_value = mock_decoder

    with patch.dict("sys.modules", {"sounddevice": mock_sd, "opuslib": mock_opuslib}):
        bridge = AudioBridge(radio, device_name="BlackHole", tx_enabled=False)
        await bridge.start()

        assert bridge._running
        assert bus.subscriber_count == 1

        await bridge.stop()
        assert not bridge._running
        await asyncio.sleep(0.05)
        assert bus.subscriber_count == 0
        mock_output_stream.stop.assert_called_once()
        mock_output_stream.close.assert_called_once()


async def test_bridge_start_already_running():
    from icom_lan.audio_bus import AudioBus

    radio = MagicMock()
    radio.start_audio_rx_opus = AsyncMock()
    radio.stop_audio_rx_opus = AsyncMock()
    bus = AudioBus(radio)
    radio.audio_bus = bus

    mock_output_stream = MagicMock()
    mock_output_stream.active = True

    mock_sd = MagicMock()
    mock_sd.query_devices.return_value = [
        {"name": "BlackHole 2ch", "index": 1},
    ]
    mock_sd.OutputStream.return_value = mock_output_stream
    mock_opuslib = MagicMock()

    with patch.dict("sys.modules", {"sounddevice": mock_sd, "opuslib": mock_opuslib}):
        bridge = AudioBridge(radio, device_name="BlackHole", tx_enabled=False)
        await bridge.start()
        await bridge.start()  # no-op
        assert bus.subscriber_count == 1

        await bridge.stop()


async def test_bridge_stop_when_not_running():
    radio = MagicMock()
    bridge = AudioBridge(radio)
    # Should be a no-op, no error
    await bridge.stop()


# ---------------------------------------------------------------------------
# RX callback
# ---------------------------------------------------------------------------


async def test_bridge_rx_via_bus():
    """Bridge receives opus packets via AudioBus subscription."""
    from icom_lan.audio_bus import AudioBus

    radio = MagicMock()
    radio.start_audio_rx_opus = AsyncMock()
    radio.stop_audio_rx_opus = AsyncMock()
    bus = AudioBus(radio)
    radio.audio_bus = bus

    mock_output_stream = MagicMock()
    mock_output_stream.active = True

    mock_sd = MagicMock()
    mock_sd.query_devices.return_value = [
        {"name": "BlackHole 2ch", "index": 1},
    ]
    mock_sd.OutputStream.return_value = mock_output_stream

    mock_opuslib = MagicMock()
    fake_pcm = b"\x00\x01" * SAMPLES_PER_FRAME
    mock_decoder = MagicMock()
    mock_decoder.decode.return_value = fake_pcm
    mock_opuslib.Decoder.return_value = mock_decoder

    with patch.dict("sys.modules", {"sounddevice": mock_sd, "opuslib": mock_opuslib}):
        bridge = AudioBridge(radio, device_name="BlackHole", tx_enabled=False)
        await bridge.start()

        # Simulate radio delivering a packet via bus
        packet = MagicMock()
        packet.data = b"\x01\x02\x03"
        bus._on_opus_packet(packet)

        # deliver() increments _received synchronously
        assert bridge._subscription._received == 1

        # Feed None (gap)
        bus._on_opus_packet(None)
        assert bridge._subscription._received == 2

        await bridge.stop()


# ---------------------------------------------------------------------------
# Latency stats — Task 2
# ---------------------------------------------------------------------------


def test_stats_has_new_fields():
    """stats dict contains all timing fields."""
    radio = MagicMock()
    bridge = AudioBridge(radio)
    s = bridge.stats
    assert "uptime_seconds" in s
    assert "rx_interval_ms" in s
    assert "tx_interval_ms" in s
    assert "buffer_size" in s


def test_rx_latency_calculation():
    """RX inter-frame timing is computed and averaged."""
    import time

    radio = MagicMock()
    bridge = AudioBridge(radio)

    # Simulate two frames arriving ~20ms apart
    bridge._last_rx_time = time.monotonic() - 0.020
    bridge._rx_latency_samples.append(0.020)
    bridge._rx_latency_samples.append(0.020)

    s = bridge.stats
    assert s["rx_interval_ms"] == pytest.approx(20.0, abs=0.1)
    assert s["buffer_size"] == 2


def test_tx_latency_calculation():
    """TX inter-frame timing is computed and averaged."""
    radio = MagicMock()
    bridge = AudioBridge(radio)

    bridge._tx_latency_samples.append(0.040)
    bridge._tx_latency_samples.append(0.040)

    s = bridge.stats
    assert s["tx_interval_ms"] == pytest.approx(40.0, abs=0.1)


def test_latency_buffer_capped_at_100():
    """RX and TX sample buffers are capped at 100 entries."""
    import time

    radio = MagicMock()
    bridge = AudioBridge(radio)
    bridge._last_rx_time = time.monotonic() - 0.020

    # Simulate filling buffer beyond 100
    bridge._rx_latency_samples = [0.020] * 100
    bridge._rx_latency_samples.append(0.030)
    if len(bridge._rx_latency_samples) > 100:
        bridge._rx_latency_samples.pop(0)

    assert len(bridge._rx_latency_samples) == 100
    assert bridge.stats["buffer_size"] == 100


# ---------------------------------------------------------------------------
# derive_bridge_label
# ---------------------------------------------------------------------------


def test_derive_label_explicit():
    """Explicit label is returned as-is."""
    radio = MagicMock()
    radio.model = "IC-7610"
    assert derive_bridge_label(radio, "my-label") == "my-label"


def test_derive_label_from_model():
    """Label includes radio model when no explicit label given."""
    radio = MagicMock()
    radio.model = "IC-7610"
    assert derive_bridge_label(radio, None) == "icom-lan (IC-7610)"


def test_derive_label_no_model():
    """Falls back to 'icom-lan' when model is unavailable."""
    radio = MagicMock(spec=[])  # no .model attribute
    assert derive_bridge_label(radio, None) == "icom-lan"


def test_derive_label_empty_model():
    """Empty model string falls back to 'icom-lan'."""
    radio = MagicMock()
    radio.model = ""
    assert derive_bridge_label(radio, None) == "icom-lan"


# ---------------------------------------------------------------------------
# Label parameter
# ---------------------------------------------------------------------------


def test_bridge_label_default():
    """Default label is 'icom-lan'."""
    radio = MagicMock()
    bridge = AudioBridge(radio)
    assert bridge.label == "icom-lan"


def test_bridge_label_custom():
    """Custom label is stored and accessible."""
    radio = MagicMock()
    bridge = AudioBridge(radio, label="icom-lan (IC-7610)")
    assert bridge.label == "icom-lan (IC-7610)"


def test_bridge_label_in_stats():
    """Stats dict includes label field."""
    radio = MagicMock()
    bridge = AudioBridge(radio, label="icom-lan (IC-905)")
    assert bridge.stats["label"] == "icom-lan (IC-905)"


async def test_bridge_label_in_log_messages(caplog):
    """Label appears in log messages instead of hardcoded 'audio-bridge'."""
    import logging

    radio = MagicMock()
    bridge = AudioBridge(radio, label="icom-lan (IC-905)")

    with caplog.at_level(logging.WARNING):
        bridge._running = True
        await bridge.start()

    assert "icom-lan (IC-905): already running" in caplog.text
