"""Tests for cw_auto_tune command wiring in ControlHandler."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from icom_lan.dsp.tap_registry import TapRegistry
from icom_lan.radio_state import RadioState, ReceiverState
from icom_lan.web.handlers.control import ControlHandler


def _make_handler(
    *,
    radio_state: RadioState | None = None,
    radio: Any = None,
) -> ControlHandler:
    """Build a ControlHandler with a fake server and WebSocket."""
    ws = MagicMock()
    ws.send_text = AsyncMock()

    tap_registry = TapRegistry()
    broadcaster = MagicMock()
    broadcaster._tap_registry = tap_registry
    broadcaster.ensure_relay = AsyncMock()

    command_queue = MagicMock()

    if radio_state is None:
        radio_state = RadioState(
            main=ReceiverState(freq=14_074_000),
            cw_pitch=600,
        )

    server = SimpleNamespace(
        _audio_broadcaster=broadcaster,
        _radio_state=radio_state,
        command_queue=command_queue,
    )

    handler = ControlHandler(
        ws=ws,
        radio=radio if radio is not None else MagicMock(),
        server_version="test",
        radio_model="IC-7610",
        server=server,
    )
    return handler


class TestCwAutoTuneWiring:
    """Test cw_auto_tune command dispatch in ControlHandler."""

    async def test_cw_auto_tune_in_commands_set(self) -> None:
        """cw_auto_tune is listed in _COMMANDS."""
        assert "cw_auto_tune" in ControlHandler._COMMANDS

    async def test_timeout_returns_not_detected(self) -> None:
        """If no audio arrives within 3s, return detected=None."""
        handler = _make_handler()
        # No audio fed → tuner never fires → timeout
        with patch(
            "icom_lan.web.handlers.control.asyncio.wait_for",
            side_effect=asyncio.TimeoutError,
        ):
            result = await handler._cw_auto_tune()

        assert result == {"detected": None, "applied": False}

    async def test_successful_detection(self) -> None:
        """Detected tone returns Hz, delta, and applied flag."""
        handler = _make_handler(
            radio_state=RadioState(
                main=ReceiverState(freq=14_074_000),
                cw_pitch=600,
            ),
        )
        # Patch CwAutoTuner to immediately call the callback with 650 Hz
        with patch("icom_lan.cw_auto_tuner.CwAutoTuner") as MockTuner:
            instance = MockTuner.return_value
            instance.feed_audio = MagicMock()
            instance.cancel = MagicMock()

            def fake_start(callback):
                # Immediately call callback to simulate detection
                callback(650)

            instance.start_collection = MagicMock(side_effect=fake_start)

            result = await handler._cw_auto_tune()

        assert result["detected"] == 650
        assert result["cw_pitch"] == 600
        assert result["delta"] == 50
        assert result["applied"] is True

        # Verify frequency was shifted
        q = handler._server.command_queue
        q.put.assert_called_once()
        cmd = q.put.call_args[0][0]
        assert cmd.freq == 14_074_000 + 50

    async def test_detection_none_returns_not_applied(self) -> None:
        """Detected=None (silence) returns applied=False."""
        handler = _make_handler()

        with patch("icom_lan.cw_auto_tuner.CwAutoTuner") as MockTuner:
            instance = MockTuner.return_value
            instance.feed_audio = MagicMock()
            instance.cancel = MagicMock()

            def fake_start(callback):
                callback(None)

            instance.start_collection = MagicMock(side_effect=fake_start)

            result = await handler._cw_auto_tune()

        assert result == {"detected": None, "applied": False}

    async def test_small_delta_not_applied(self) -> None:
        """Delta <= 5 Hz does not shift frequency."""
        handler = _make_handler(
            radio_state=RadioState(
                main=ReceiverState(freq=7_030_000),
                cw_pitch=600,
            ),
        )

        with patch("icom_lan.cw_auto_tuner.CwAutoTuner") as MockTuner:
            instance = MockTuner.return_value
            instance.feed_audio = MagicMock()
            instance.cancel = MagicMock()

            def fake_start(callback):
                callback(603)  # delta = 3 Hz, below threshold

            instance.start_collection = MagicMock(side_effect=fake_start)

            result = await handler._cw_auto_tune()

        assert result["detected"] == 603
        assert result["delta"] == 3
        assert result["applied"] is False
        handler._server.command_queue.put.assert_not_called()

    async def test_no_server_raises(self) -> None:
        """Raises RuntimeError when server is None."""
        ws = MagicMock()
        ws.send_text = AsyncMock()
        handler = ControlHandler(
            ws=ws,
            radio=MagicMock(),
            server_version="test",
            radio_model="IC-7610",
            server=None,
        )
        with pytest.raises(RuntimeError, match="server not available"):
            await handler._cw_auto_tune()

    async def test_tap_is_unregistered_on_success(self) -> None:
        """Tap handle is removed from registry after detection."""
        handler = _make_handler()
        registry = handler._server._audio_broadcaster._tap_registry

        with patch("icom_lan.cw_auto_tuner.CwAutoTuner") as MockTuner:
            instance = MockTuner.return_value
            instance.feed_audio = MagicMock()
            instance.cancel = MagicMock()

            def fake_start(callback):
                callback(700)

            instance.start_collection = MagicMock(side_effect=fake_start)

            await handler._cw_auto_tune()

        # Registry should have no active taps after completion
        assert not registry.active

    async def test_tap_is_unregistered_on_timeout(self) -> None:
        """Tap handle is removed from registry even on timeout."""
        handler = _make_handler()
        registry = handler._server._audio_broadcaster._tap_registry

        with patch(
            "icom_lan.web.handlers.control.asyncio.wait_for",
            side_effect=asyncio.TimeoutError,
        ):
            await handler._cw_auto_tune()

        assert not registry.active

    async def test_ensure_relay_called(self) -> None:
        """ensure_relay is called so audio flows to the tap."""
        handler = _make_handler()

        with patch("icom_lan.cw_auto_tuner.CwAutoTuner") as MockTuner:
            instance = MockTuner.return_value
            instance.feed_audio = MagicMock()
            instance.cancel = MagicMock()

            def fake_start(callback):
                callback(700)

            instance.start_collection = MagicMock(side_effect=fake_start)

            await handler._cw_auto_tune()

        handler._server._audio_broadcaster.ensure_relay.assert_awaited_once()
