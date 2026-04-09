"""Tests for audio_bridge module."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from icom_lan._bridge_metrics import BridgeMetrics
from icom_lan._bridge_state import BridgeState, BridgeStateChange
from icom_lan.audio.backend import (
    AudioDeviceId,
    AudioDeviceInfo,
    FakeAudioBackend,
)
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
# Helpers
# ---------------------------------------------------------------------------

_BH_DEVICE = AudioDeviceInfo(
    id=AudioDeviceId(1),
    name="BlackHole 2ch",
    input_channels=2,
    output_channels=2,
)


def _bridge_backend(
    devices: list[AudioDeviceInfo] | None = None,
) -> FakeAudioBackend:
    return FakeAudioBackend(
        devices
        or [
            AudioDeviceInfo(
                id=AudioDeviceId(0),
                name="Built-in Output",
                output_channels=2,
            ),
            _BH_DEVICE,
        ]
    )


def _make_radio() -> MagicMock:
    from icom_lan.audio_bus import AudioBus

    radio = MagicMock()
    radio.start_audio_rx_opus = AsyncMock()
    radio.stop_audio_rx_opus = AsyncMock()
    radio.start_audio_tx_pcm = AsyncMock()
    radio.stop_audio_tx_pcm = AsyncMock()
    radio.push_audio_tx_pcm = AsyncMock()
    radio.push_audio_tx_opus = AsyncMock()
    bus = AudioBus(radio)
    radio.audio_bus = bus
    return radio


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
# find_loopback_device (legacy compat)
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
# list_audio_devices (legacy compat)
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
    assert bridge.bridge_state == BridgeState.IDLE
    s = bridge.stats
    assert s["running"] is False
    assert s["bridge_state"] == "idle"
    assert s["reconnect_attempt"] == 0
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


async def test_bridge_start_no_device():
    radio = MagicMock()
    backend = FakeAudioBackend(
        [AudioDeviceInfo(id=AudioDeviceId(0), name="Built-in", output_channels=2)]
    )
    bridge = AudioBridge(radio, device_name="BlackHole", backend=backend)
    with pytest.raises(RuntimeError, match="Virtual audio device not found"):
        await bridge.start()
    # State should revert to IDLE on start failure
    assert bridge.bridge_state == BridgeState.IDLE


# ---------------------------------------------------------------------------
# AudioBridge start + stop — happy path
# ---------------------------------------------------------------------------


async def test_bridge_start_stop_rx_only():
    radio = _make_radio()
    backend = _bridge_backend()
    bridge = AudioBridge(
        radio, device_name="BlackHole", tx_enabled=False, backend=backend
    )
    await bridge.start()

    assert bridge._running
    assert bridge.bridge_state == BridgeState.RUNNING
    assert radio.audio_bus.subscriber_count == 1
    assert len(backend.tx_streams) == 1
    assert backend.tx_streams[0].running

    await bridge.stop()
    assert not bridge._running
    assert bridge.bridge_state == BridgeState.IDLE
    await asyncio.sleep(0.05)
    assert radio.audio_bus.subscriber_count == 0
    assert backend.tx_streams[0].stopped_count == 1


async def test_bridge_start_already_running():
    radio = _make_radio()
    backend = _bridge_backend()
    bridge = AudioBridge(
        radio, device_name="BlackHole", tx_enabled=False, backend=backend
    )
    await bridge.start()
    await bridge.start()  # no-op
    assert radio.audio_bus.subscriber_count == 1
    await bridge.stop()


async def test_bridge_stop_when_not_running():
    radio = MagicMock()
    bridge = AudioBridge(radio)
    await bridge.stop()  # no-op, no error


# ---------------------------------------------------------------------------
# RX callback — packets flow from bus to backend TxStream
# ---------------------------------------------------------------------------


async def test_bridge_rx_via_bus():
    radio = _make_radio()
    backend = _bridge_backend()
    bridge = AudioBridge(
        radio, device_name="BlackHole", tx_enabled=False, backend=backend
    )
    await bridge.start()

    packet = MagicMock()
    packet.data = b"\x01\x02\x03"
    radio.audio_bus._on_opus_packet(packet)
    assert bridge._subscription._received == 1

    radio.audio_bus._on_opus_packet(None)
    assert bridge._subscription._received == 2

    await bridge.stop()


# ---------------------------------------------------------------------------
# TX path — captured audio flows from backend RxStream to radio
# ---------------------------------------------------------------------------


async def test_bridge_tx_path_uses_backend_rx_stream():
    radio = _make_radio()
    backend = _bridge_backend()
    bridge = AudioBridge(
        radio, device_name="BlackHole", tx_enabled=True, backend=backend
    )
    await bridge.start()

    assert len(backend.tx_streams) == 1
    assert len(backend.rx_streams) == 1
    assert backend.rx_streams[0].running

    import numpy as np

    loud_frame = np.full(SAMPLES_PER_FRAME, 1000, dtype=np.int16).tobytes()
    backend.rx_streams[0].inject_frame(loud_frame)

    await asyncio.sleep(0.05)
    await bridge.stop()

    assert radio.push_audio_tx_opus.called or bridge._tx_frames > 0


# ---------------------------------------------------------------------------
# State machine — BridgeState transitions
# ---------------------------------------------------------------------------


def test_initial_state_is_idle():
    radio = MagicMock()
    bridge = AudioBridge(radio)
    assert bridge.bridge_state == BridgeState.IDLE


async def test_state_transitions_to_running_on_start():
    radio = _make_radio()
    backend = _bridge_backend()
    events: list[BridgeStateChange] = []
    bridge = AudioBridge(
        radio,
        device_name="BlackHole",
        tx_enabled=False,
        backend=backend,
        on_state_changed=events.append,
    )
    await bridge.start()
    assert bridge.bridge_state == BridgeState.RUNNING

    # Expect IDLE→CONNECTING→RUNNING
    assert len(events) == 2
    assert events[0].previous == BridgeState.IDLE
    assert events[0].current == BridgeState.CONNECTING
    assert events[0].reason == "start"
    assert events[1].previous == BridgeState.CONNECTING
    assert events[1].current == BridgeState.RUNNING
    assert events[1].reason == "started"

    await bridge.stop()
    # RUNNING→IDLE
    assert events[-1].current == BridgeState.IDLE
    assert events[-1].reason == "stopped"


async def test_on_state_changed_callback_fires():
    radio = _make_radio()
    backend = _bridge_backend()
    events: list[BridgeStateChange] = []
    bridge = AudioBridge(
        radio,
        device_name="BlackHole",
        tx_enabled=False,
        backend=backend,
        on_state_changed=events.append,
    )
    await bridge.start()
    await bridge.stop()

    assert len(events) >= 3  # CONNECTING, RUNNING, IDLE
    states = [e.current for e in events]
    assert BridgeState.CONNECTING in states
    assert BridgeState.RUNNING in states
    assert BridgeState.IDLE in states


# ---------------------------------------------------------------------------
# Reconnect state machine
# ---------------------------------------------------------------------------


async def test_reconnect_on_stream_write_failure():
    """When the RX TxStream write fails, bridge enters RECONNECTING."""
    radio = _make_radio()
    backend = _bridge_backend()
    events: list[BridgeStateChange] = []
    bridge = AudioBridge(
        radio,
        device_name="BlackHole",
        tx_enabled=False,
        backend=backend,
        max_retries=2,
        retry_base_delay=0.01,
        on_state_changed=events.append,
    )
    await bridge.start()
    assert bridge.bridge_state == BridgeState.RUNNING

    # Inject a write failure on the TxStream
    backend.tx_streams[0].fail_on_write = OSError("device removed")

    # Deliver a packet to trigger the write
    packet = MagicMock()
    packet.data = b"\x01\x02\x03" * 100
    radio.audio_bus._on_opus_packet(packet)

    # Give the RX loop time to hit the error and trigger reconnect
    await asyncio.sleep(0.15)

    # Should have reconnected (device is still in the backend list)
    assert bridge.bridge_state == BridgeState.RUNNING
    assert any(e.reason == "reconnected" for e in events)

    await bridge.stop()


async def test_reconnect_succeeds_when_device_returns():
    """Device removed then re-added — bridge reconnects."""
    radio = _make_radio()
    backend = _bridge_backend()
    events: list[BridgeStateChange] = []
    bridge = AudioBridge(
        radio,
        device_name="BlackHole",
        tx_enabled=False,
        backend=backend,
        max_retries=5,
        retry_base_delay=0.01,
        on_state_changed=events.append,
    )
    await bridge.start()
    assert bridge.bridge_state == BridgeState.RUNNING

    # Simulate device loss
    backend.tx_streams[0].fail_on_write = OSError("device removed")
    backend.remove_devices()

    packet = MagicMock()
    packet.data = b"\xAA" * 100
    radio.audio_bus._on_opus_packet(packet)

    await asyncio.sleep(0.05)
    assert bridge.bridge_state == BridgeState.RECONNECTING

    # Bring device back
    backend.add_device(_BH_DEVICE)
    await asyncio.sleep(0.2)

    assert bridge.bridge_state == BridgeState.RUNNING
    assert any(e.reason == "reconnected" for e in events)

    await bridge.stop()


async def test_failed_state_after_max_retries():
    """Bridge enters FAILED when device never comes back."""
    radio = _make_radio()
    backend = _bridge_backend()
    events: list[BridgeStateChange] = []
    bridge = AudioBridge(
        radio,
        device_name="BlackHole",
        tx_enabled=False,
        backend=backend,
        max_retries=2,
        retry_base_delay=0.01,
        on_state_changed=events.append,
    )
    await bridge.start()

    # Permanently remove device
    backend.tx_streams[0].fail_on_write = OSError("gone")
    backend.remove_devices()

    packet = MagicMock()
    packet.data = b"\xBB" * 100
    radio.audio_bus._on_opus_packet(packet)

    # Wait for all retries to exhaust (2 retries at 0.01s base, ~0.03s total)
    await asyncio.sleep(0.3)

    assert bridge.bridge_state == BridgeState.FAILED
    assert any(e.reason == "max_retries" for e in events)


async def test_stop_cancels_reconnect_task():
    """Calling stop() during reconnect cancels the reconnect loop."""
    radio = _make_radio()
    backend = _bridge_backend()
    bridge = AudioBridge(
        radio,
        device_name="BlackHole",
        tx_enabled=False,
        backend=backend,
        max_retries=10,
        retry_base_delay=1.0,  # long delay so reconnect is in progress
    )
    await bridge.start()

    # Trigger reconnect
    backend.tx_streams[0].fail_on_write = OSError("gone")
    backend.remove_devices()

    packet = MagicMock()
    packet.data = b"\xCC" * 100
    radio.audio_bus._on_opus_packet(packet)

    await asyncio.sleep(0.05)
    assert bridge.bridge_state == BridgeState.RECONNECTING

    # Stop should cancel the long backoff reconnect
    await bridge.stop()
    assert bridge.bridge_state == BridgeState.IDLE


async def test_stats_includes_bridge_state():
    radio = _make_radio()
    backend = _bridge_backend()
    bridge = AudioBridge(
        radio, device_name="BlackHole", tx_enabled=False, backend=backend
    )
    assert bridge.stats["bridge_state"] == "idle"
    await bridge.start()
    assert bridge.stats["bridge_state"] == "running"
    await bridge.stop()
    assert bridge.stats["bridge_state"] == "idle"


# ---------------------------------------------------------------------------
# Latency stats
# ---------------------------------------------------------------------------


def test_stats_has_new_fields():
    radio = MagicMock()
    bridge = AudioBridge(radio)
    s = bridge.stats
    assert "uptime_seconds" in s
    assert "rx_interval_ms" in s
    assert "tx_interval_ms" in s
    assert "buffer_size" in s
    assert "bridge_state" in s
    assert "reconnect_attempt" in s


def test_rx_latency_calculation():
    import time

    radio = MagicMock()
    bridge = AudioBridge(radio)
    bridge._last_rx_time = time.monotonic() - 0.020
    bridge._rx_latency_samples.append(0.020)
    bridge._rx_latency_samples.append(0.020)

    s = bridge.stats
    assert s["rx_interval_ms"] == pytest.approx(20.0, abs=0.1)
    assert s["buffer_size"] == 2


def test_tx_latency_calculation():
    radio = MagicMock()
    bridge = AudioBridge(radio)
    bridge._tx_latency_samples.append(0.040)
    bridge._tx_latency_samples.append(0.040)

    s = bridge.stats
    assert s["tx_interval_ms"] == pytest.approx(40.0, abs=0.1)


def test_latency_buffer_capped_at_100():
    import time

    radio = MagicMock()
    bridge = AudioBridge(radio)
    bridge._last_rx_time = time.monotonic() - 0.020

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
    radio = MagicMock()
    radio.model = "IC-7610"
    assert derive_bridge_label(radio, "my-label") == "my-label"


def test_derive_label_from_model():
    radio = MagicMock()
    radio.model = "IC-7610"
    assert derive_bridge_label(radio, None) == "icom-lan (IC-7610)"


def test_derive_label_no_model():
    radio = MagicMock(spec=[])
    assert derive_bridge_label(radio, None) == "icom-lan"


def test_derive_label_empty_model():
    radio = MagicMock()
    radio.model = ""
    assert derive_bridge_label(radio, None) == "icom-lan"


# ---------------------------------------------------------------------------
# Label parameter
# ---------------------------------------------------------------------------


def test_bridge_label_default():
    radio = MagicMock()
    bridge = AudioBridge(radio)
    assert bridge.label == "icom-lan"


def test_bridge_label_custom():
    radio = MagicMock()
    bridge = AudioBridge(radio, label="icom-lan (IC-7610)")
    assert bridge.label == "icom-lan (IC-7610)"


def test_bridge_label_in_stats():
    radio = MagicMock()
    bridge = AudioBridge(radio, label="icom-lan (IC-905)")
    assert bridge.stats["label"] == "icom-lan (IC-905)"


async def test_bridge_label_in_log_messages(caplog):
    import logging

    radio = MagicMock()
    bridge = AudioBridge(radio, label="icom-lan (IC-905)")

    with caplog.at_level(logging.WARNING):
        bridge._running = True
        await bridge.start()

    assert "icom-lan (IC-905): already running" in caplog.text


# ---------------------------------------------------------------------------
# BridgeMetrics
# ---------------------------------------------------------------------------


def test_metrics_returns_bridge_metrics_instance():
    radio = MagicMock()
    bridge = AudioBridge(radio)
    m = bridge.metrics
    assert isinstance(m, BridgeMetrics)
    assert m.running is False
    assert m.bridge_state == "idle"
    assert m.rx_frames == 0
    assert m.rx_jitter_ms == 0.0
    assert m.rx_level_dbfs == -96.0
    assert m.tx_level_dbfs == -96.0
    assert m.rx_underruns == 0
    assert m.tx_overruns == 0


def test_metrics_to_dict_backward_compat():
    """stats returns a dict with all BridgeMetrics fields."""
    radio = MagicMock()
    bridge = AudioBridge(radio)
    s = bridge.stats
    assert isinstance(s, dict)
    assert "rx_jitter_ms" in s
    assert "rx_level_dbfs" in s
    assert "tx_overruns" in s
    assert "bridge_state" in s


def test_metrics_jitter_computed():
    """Jitter is the std dev of inter-frame intervals."""
    radio = MagicMock()
    bridge = AudioBridge(radio)
    # Vary intervals: 20ms, 22ms, 18ms, 20ms
    bridge._rx_latency_samples = [0.020, 0.022, 0.018, 0.020]
    m = bridge.metrics
    assert m.rx_jitter_ms > 0
    assert m.rx_jitter_ms < 5  # should be small


async def test_on_metrics_callback():
    """on_metrics callback receives BridgeMetrics snapshots."""
    radio = _make_radio()
    backend = _bridge_backend()
    metrics_list: list[BridgeMetrics] = []
    bridge = AudioBridge(
        radio,
        device_name="BlackHole",
        tx_enabled=False,
        backend=backend,
        on_metrics=metrics_list.append,
    )
    await bridge.start()

    # Deliver 50 frames to trigger a metrics emission (every 50 frames)
    for i in range(51):
        packet = MagicMock()
        packet.data = b"\xAA" * 100
        radio.audio_bus._on_opus_packet(packet)

    await asyncio.sleep(0.1)
    await bridge.stop()

    assert len(metrics_list) >= 1
    assert isinstance(metrics_list[0], BridgeMetrics)
    assert metrics_list[0].rx_frames > 0
