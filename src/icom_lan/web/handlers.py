"""Route handlers for WebSocket channels and HTTP endpoints.

Each handler manages the lifecycle of one client connection on one channel:
- control (/api/v1/ws): JSON commands, events, state
- scope (/api/v1/scope): binary scope frames with backpressure
- audio (/api/v1/audio): placeholder for future audio streaming
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any, Protocol, cast

from .._audio_transcoder import PcmOpusTranscoder, create_pcm_opus_transcoder
from ..profiles import RadioProfile
from ..radio_state import RadioState
from ..scope import ScopeFrame
from ..types import AudioCodec
from .protocol import (
    AUDIO_CODEC_OPUS,
    AUDIO_CODEC_PCM16,
    AUDIO_HEADER_SIZE,
    MSG_TYPE_AUDIO_RX,
    decode_json,
    encode_audio_frame,
    encode_json,
    encode_scope_frame,
)
from .radio_poller import (
    PttOff,
    PttOn,
    SelectVfo,
    SetAcc1ModLevel,
    SetAfLevel,
    SetAgc,
    SetAgcTimeConstant,
    SetAntenna1,
    SetAntenna2,
    SetAttenuator,
    SetAutoNotch,
    SetBand,
    SetCompressor,
    SetCompressorLevel,
    SetCwPitch,
    SetDataMode,
    SetDialLock,
    SetDigiSel,
    SetDualWatch,
    SetFilter,
    SetFilterShape,
    SetFilterWidth,
    SetFreq,
    SetIpPlus,
    SetLanModLevel,
    SetManualNotch,
    SetMicGain,
    SetMode,
    SetMonitor,
    SetMonitorGain,
    SetNB,
    SetNBLevel,
    SetNotchFilter,
    SetNR,
    SetNRLevel,
    SetPbtInner,
    SetPbtOuter,
    SetPower,
    SetPowerstat,
    SetPreamp,
    SetRfGain,
    SetRitFrequency,
    SetRitStatus,
    SetRitTxStatus,
    SetRxAntennaAnt1,
    SetRxAntennaAnt2,
    SetScopeCenterType,
    SetScopeDuringTx,
    SetScopeFixedEdge,
    SetSplit,
    SetSquelch,
    SetSystemDate,
    SetSystemTime,
    SetUsbModLevel,
    SetVox,
    SwitchScopeReceiver,
    VfoEqualize,
    VfoSwap,
)
from .runtime_helpers import (
    build_public_state_payload,
    radio_ready,
    runtime_capabilities,
)
from .websocket import WS_OP_BINARY, WS_OP_TEXT, WebSocketConnection

if TYPE_CHECKING:
    from ..radio_protocol import Radio

from ..radio_protocol import AdvancedControlCapable, LevelsCapable, PowerControlCapable

__all__ = [
    "HIGH_WATERMARK",
    "ControlHandler",
    "ScopeHandler",
    "AudioHandler",
]

logger = logging.getLogger(__name__)

HIGH_WATERMARK = 5  # Max queued scope/meter frames before dropping


def _runtime_capabilities(radio: "Radio | None") -> set[str]:
    """Backward-compatible alias to shared runtime_capabilities helper."""
    return runtime_capabilities(radio)


class ControlHandler:
    """Handles the /api/v1/ws control WebSocket channel.

    Receives JSON commands from the client and enqueues them via the
    server's CommandQueue.  Receives broadcast events from RadioPoller
    via an asyncio.Queue and forwards them to the WebSocket.

    Args:
        ws: Established WebSocket connection.
        radio: Radio protocol instance (may be None in standalone mode).
        server_version: Version string for the hello message.
        radio_model: Radio model string for the hello message.
        server: WebServer instance for command_queue and event broadcast.
    """

    _COMMANDS = frozenset(
        [
            "set_freq",
            "set_band",
            "set_mode",
            "set_filter",
            "set_filter_width",
            "set_filter_shape",
            "ptt",
            "set_rf_power",
            "set_power",  # backward-compat alias for set_rf_power
            "set_powerstat",
            "set_rf_gain",
            "set_af_level",
            "set_sql",
            "set_squelch",
            "set_nb",
            "set_nr",
            "set_nr_level",
            "set_nb_level",
            "set_auto_notch",
            "set_manual_notch",
            "set_notch_filter",
            "set_digisel",
            "set_ip_plus",
            "set_ipplus",  # backward-compat alias for set_ip_plus
            "set_att",
            "set_attenuator",
            "set_preamp",
            "set_pbt_inner",
            "set_pbt_outer",
            "set_cw_pitch",
            "set_data_mode",
            "set_mic_gain",
            "set_vox",
            "set_compressor_level",
            "set_monitor",
            "set_monitor_gain",
            "set_dial_lock",
            "set_agc_time_constant",
            "set_agc",
            "set_rit_status",
            "set_rit_tx_status",
            "set_rit_frequency",
            "set_split",
            "set_vfo",
            "select_vfo",  # backward-compat alias for set_vfo
            "ptt_on",
            "ptt_off",
            "vfo_swap",
            "vfo_equalize",
            "switch_scope_receiver",
            "set_scope_during_tx",
            "set_scope_center_type",
            "set_scope_fixed_edge",
            "set_antenna_1",
            "set_antenna_2",
            "set_rx_antenna_ant1",
            "set_rx_antenna_ant2",
            "get_system_date",
            "set_system_date",
            "get_system_time",
            "set_system_time",
            "set_acc1_mod_level",
            "set_usb_mod_level",
            "set_lan_mod_level",
            "get_dual_watch",
            "set_dual_watch",
            "get_tuner_status",
            "set_tuner_status",
            "set_comp",
            "set_compressor",
        ]
    )

    def __init__(
        self,
        ws: WebSocketConnection,
        radio: "Radio | None",
        server_version: str,
        radio_model: str,
        server: Any = None,
    ) -> None:
        self._ws = ws
        self._radio = radio
        self._version = server_version
        self._radio_model = radio_model
        self._server = server
        self._subscribed_streams: set[str] = set()
        self._event_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(
            maxsize=100,
        )
        # Per-command rate limiting: command_name -> (last_time, drop_count)
        self._cmd_last: dict[str, float] = {}
        self._cmd_drops: dict[str, int] = {}
        # Minimum interval between same command (seconds).
        # Continuous slider/knob drag sends dozens of set_* per second.
        self._CMD_MIN_INTERVAL = 0.05  # 50ms = max 20 commands/sec per client

    async def run(self) -> None:
        """Run the control channel lifecycle."""
        await self._send_hello()
        if self._server is not None:
            self._server.register_control_event_queue(self._event_queue)
        event_task: asyncio.Task[None] = asyncio.create_task(self._event_sender_loop())
        try:
            while True:
                opcode, payload = await self._ws.recv()
                if opcode == WS_OP_TEXT:
                    await self._handle_text(payload.decode("utf-8"))
        except EOFError:
            pass
        finally:
            event_task.cancel()
            try:
                await event_task
            except asyncio.CancelledError:
                pass
            if self._server is not None:
                self._server.unregister_control_event_queue(self._event_queue)

    async def _event_sender_loop(self) -> None:
        """Drain event queue and forward events to WebSocket."""
        try:
            while True:
                event = await self._event_queue.get()
                msg_type = event.get("type")
                if msg_type == "notification":
                    await self._send_json(event)
                elif msg_type == "state_update":
                    # Always forward state updates (clients need fresh state)
                    await self._send_json(event)
                elif (
                    "state" in self._subscribed_streams
                    or "events" in self._subscribed_streams
                ):
                    await self._send_json(event)
        except asyncio.CancelledError:
            pass

    async def _send_hello(self) -> None:
        raw_connected = (
            getattr(self._radio, "connected", False) if self._radio else False
        )
        caps = sorted(self._capabilities())
        msg = {
            "type": "hello",
            "proto": 1,
            "server": "icom-lan",
            "version": self._version,
            "radio": self._radio_model,
            "connected": raw_connected if isinstance(raw_connected, bool) else False,
            "radio_ready": self._radio_ready(),
            "capabilities": caps,
        }
        await self._ws.send_text(encode_json(msg))

    def _capabilities(self) -> set[str]:
        return runtime_capabilities(self._radio)

    def _ensure_receiver_supported(self, receiver: int) -> None:
        if self._radio is None:
            return
        raw_profile = getattr(self._radio, "profile", None)
        if isinstance(raw_profile, RadioProfile):
            receiver_count = raw_profile.receiver_count
        else:
            receiver_count = 2 if "dual_rx" in self._capabilities() else 1
        if 0 <= receiver < receiver_count:
            return
        raise ValueError(
            f"receiver={receiver} is not supported by active profile "
            f"(receivers={receiver_count})"
        )

    def _ensure_capability(self, capability: str, command_name: str) -> None:
        if self._radio is None:
            return
        caps = self._capabilities()
        # Also check profile capabilities (runtime_capabilities may strip
        # protocol-gated tags like dual_rx even when the profile supports them).
        raw_profile = getattr(self._radio, "profile", None)
        if isinstance(raw_profile, RadioProfile):
            if capability in raw_profile.capabilities:
                return
        if capability in caps:
            return
        raise ValueError(
            f"command {command_name!r} is not supported by active profile "
            f"(missing capability: {capability})"
        )

    def _radio_ready(self) -> bool:
        """Return backend radio readiness (CI-V healthy), with fallback."""
        return radio_ready(self._radio)

    def _backend_recovering(self) -> bool:
        """Whether backend is already managing a reconnect/recovery path."""
        if self._radio is None:
            return False
        conn_state = getattr(self._radio, "conn_state", None)
        state_value = getattr(conn_state, "value", conn_state)
        if state_value in {"connecting", "reconnecting", "disconnecting"}:
            return True
        connected = getattr(self._radio, "connected", False)
        connected_bool = connected if isinstance(connected, bool) else False
        return bool(connected_bool and not self._radio_ready())

    async def _handle_text(self, text: str) -> None:
        try:
            msg = decode_json(text)
        except ValueError as exc:
            logger.debug("control: invalid JSON: %s", exc)
            return

        msg_type = msg.get("type")

        if msg_type == "subscribe":
            await self._handle_subscribe(msg)
        elif msg_type == "unsubscribe":
            await self._handle_unsubscribe(msg)
        elif msg_type == "cmd":
            await self._handle_command(msg)
        elif msg_type == "radio_connect":
            await self._handle_radio_connect(msg)
        elif msg_type == "radio_disconnect":
            await self._handle_radio_disconnect(msg)
        else:
            logger.debug("control: unknown message type: %r", msg_type)

    async def _handle_radio_connect(self, msg: dict[str, Any]) -> None:
        """Handle radio_connect request — reconnect the radio."""
        logger.info("radio_connect requested")
        msg_id = msg.get("id", "")
        if self._radio is None:
            await self._send_json(
                {
                    "type": "response",
                    "id": msg_id,
                    "ok": False,
                    "error": "no_radio",
                    "message": "no radio instance",
                }
            )
            return
        if self._backend_recovering():
            await self._send_json(
                {
                    "type": "response",
                    "id": msg_id,
                    "ok": False,
                    "error": "backend_recovering",
                    "message": "backend is already managing radio recovery",
                }
            )
            return
        try:
            if self._radio.connected:
                await self._send_json(
                    {
                        "type": "response",
                        "id": msg_id,
                        "ok": True,
                        "result": {"status": "already_connected"},
                    }
                )
                return
            from ..radio_protocol import RecoverableConnection

            if isinstance(self._radio, RecoverableConnection):
                recoverable = cast(RecoverableConnection, self._radio)
                try:
                    await recoverable.soft_reconnect()
                except Exception:
                    logger.info("soft_reconnect failed, trying full connect")
                    await self._radio.connect()
            else:
                await self._radio.connect()
            await self._send_json(
                {
                    "type": "response",
                    "id": msg_id,
                    "ok": True,
                    "result": {"status": "connected"},
                }
            )
            await self._broadcast_connection_state(True)
        except Exception as exc:
            logger.warning("radio_connect failed: %s", exc)
            await self._send_json(
                {
                    "type": "response",
                    "id": msg_id,
                    "ok": False,
                    "error": "connect_failed",
                    "message": str(exc),
                }
            )

    async def _handle_radio_disconnect(self, msg: dict[str, Any]) -> None:
        """Handle radio_disconnect request — disconnect the radio."""
        logger.info("radio_disconnect requested")
        msg_id = msg.get("id", "")
        if self._radio is None:
            await self._send_json(
                {
                    "type": "response",
                    "id": msg_id,
                    "ok": False,
                    "error": "no_radio",
                    "message": "no radio instance",
                }
            )
            return
        try:
            if not self._radio.connected:
                await self._send_json(
                    {
                        "type": "response",
                        "id": msg_id,
                        "ok": True,
                        "result": {"status": "already_disconnected"},
                    }
                )
                return
            from ..radio_protocol import RecoverableConnection

            if isinstance(self._radio, RecoverableConnection):
                await cast(RecoverableConnection, self._radio).soft_disconnect()
            else:
                await self._radio.disconnect()
            await self._send_json(
                {
                    "type": "response",
                    "id": msg_id,
                    "ok": True,
                    "result": {"status": "disconnected"},
                }
            )
            await self._broadcast_connection_state(False)
        except Exception as exc:
            logger.warning("radio_disconnect failed: %s", exc)
            await self._send_json(
                {
                    "type": "response",
                    "id": msg_id,
                    "ok": False,
                    "error": "disconnect_failed",
                    "message": str(exc),
                }
            )

    async def _broadcast_connection_state(self, connected: bool) -> None:
        """Broadcast connection state change to this client."""
        await self._send_json(
            {
                "type": "event",
                "event": "connection_state",
                "connected": connected,
                "radio_ready": self._radio_ready(),
            }
        )

    async def _send_json(self, obj: dict[str, Any]) -> None:
        """Send a JSON message to the WebSocket client."""
        await self._ws.send_text(encode_json(obj))

    async def _handle_subscribe(self, msg: dict[str, Any]) -> None:
        streams = msg.get("streams", [])
        if isinstance(streams, list):
            self._subscribed_streams.update(str(s) for s in streams)
        await self._send_state_snapshot()

    async def _handle_unsubscribe(self, msg: dict[str, Any]) -> None:
        streams = msg.get("streams", [])
        if isinstance(streams, list):
            for s in streams:
                self._subscribed_streams.discard(str(s))

    async def _send_state_snapshot(self) -> None:
        payload: dict[str, Any] | None = None
        builder = (
            getattr(self._server, "build_public_state", None)
            if self._server is not None
            else None
        )
        if callable(builder):
            try:
                payload = cast(dict[str, Any], builder())
            except Exception as exc:
                logger.debug("control: public state build failed: %s", exc)

        if payload is None:
            raw_radio_state = (
                getattr(self._radio, "radio_state", None)
                if self._radio is not None
                else None
            )
            radio_state = (
                raw_radio_state
                if isinstance(raw_radio_state, RadioState)
                else RadioState()
            )
            raw_profile = (
                getattr(self._radio, "profile", None)
                if self._radio is not None
                else None
            )
            if isinstance(raw_profile, RadioProfile):
                receiver_count = raw_profile.receiver_count
            else:
                receiver_count = 2 if "dual_rx" in self._capabilities() else 1
            payload = build_public_state_payload(
                radio_state,
                radio=self._radio,
                revision=0,
                receiver_count=receiver_count,
            )

        msg_out = {"type": "state_update", "data": payload}
        await self._ws.send_text(encode_json(msg_out))
        # Send current DX spots if available
        if self._server is not None and hasattr(self._server, "_spot_buffer"):
            spots = self._server._spot_buffer.get_spots()
            await self._ws.send_text(encode_json({"type": "dx_spots", "spots": spots}))

    async def _handle_command(self, msg: dict[str, Any]) -> None:
        cmd_id = msg.get("id", "")
        name = msg.get("name", "")
        params = msg.get("params", {})

        # ── Server-side rate limiting (per client, per command) ──
        # Only throttle SET commands (continuous slider/knob drag).
        # GET and read-only commands pass through.
        if name.startswith("set_"):
            now = time.monotonic()
            last = self._cmd_last.get(name, 0.0)
            if now - last < self._CMD_MIN_INTERVAL:
                drops = self._cmd_drops.get(name, 0) + 1
                self._cmd_drops[name] = drops
                if drops == 1 or drops % 50 == 0:
                    logger.warning(
                        "rate-limit: dropping %s (%.0fms since last, dropped=%d)",
                        name,
                        (now - last) * 1000,
                        drops,
                    )
                # Still ACK the client so it doesn't stall
                await self._ws.send_text(
                    encode_json(
                        {
                            "type": "response",
                            "id": cmd_id,
                            "ok": True,
                            "result": {"throttled": True},
                        }
                    )
                )
                return
            self._cmd_last[name] = now
            self._cmd_drops[name] = 0

        if name not in self._COMMANDS:
            await self._ws.send_text(
                encode_json(
                    {
                        "type": "response",
                        "id": cmd_id,
                        "ok": False,
                        "error": "unknown_command",
                        "message": f"unknown command: {name!r}",
                    }
                )
            )
            return

        if self._radio is None:
            await self._ws.send_text(
                encode_json(
                    {
                        "type": "response",
                        "id": cmd_id,
                        "ok": False,
                        "error": "no_radio",
                        "message": "no radio connected",
                    }
                )
            )
            return

        try:
            result = await self._enqueue_command(name, params)
            await self._ws.send_text(
                encode_json(
                    {
                        "type": "response",
                        "id": cmd_id,
                        "ok": True,
                        "result": result,
                    }
                )
            )
        except Exception as exc:
            logger.warning("control: command %r failed: %s", name, exc)
            await self._ws.send_text(
                encode_json(
                    {
                        "type": "response",
                        "id": cmd_id,
                        "ok": False,
                        "error": "command_failed",
                        "message": str(exc),
                    }
                )
            )

    async def _enqueue_command(
        self, name: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Build a Command dataclass, enqueue it, and return the ack result."""
        logger.info("enqueue_command: %s params=%s", name, params)

        # Read-only commands — no command queue needed
        if name == "get_system_date":
            if self._radio is None:
                raise RuntimeError("radio connection not available")
            if not isinstance(self._radio, AdvancedControlCapable):
                raise RuntimeError("radio does not support this command")
            year, month, day = await self._radio.get_system_date()
            return {"year": year, "month": month, "day": day}
        if name == "get_system_time":
            if self._radio is None:
                raise RuntimeError("radio connection not available")
            if not isinstance(self._radio, AdvancedControlCapable):
                raise RuntimeError("radio does not support this command")
            hour, minute = await self._radio.get_system_time()
            return {"hour": hour, "minute": minute}
        if name == "get_dual_watch":
            if self._radio is None:
                raise RuntimeError("radio connection not available")
            if not isinstance(self._radio, AdvancedControlCapable):
                raise RuntimeError("radio does not support this command")
            on = await self._radio.get_dual_watch()
            return {"on": on}
        if name == "get_tuner_status":
            if self._radio is None:
                raise RuntimeError("radio connection not available")
            if not isinstance(self._radio, AdvancedControlCapable):
                raise RuntimeError("radio does not support this command")
            status = await self._radio.get_tuner_status()
            label = {0: "OFF", 1: "ON", 2: "TUNING"}.get(status, "UNKNOWN")
            return {"status": status, "label": label}
        if name == "set_tuner_status":
            if self._radio is None:
                raise RuntimeError("radio connection not available")
            if not isinstance(self._radio, AdvancedControlCapable):
                raise RuntimeError("radio does not support this command")
            if "value" not in params:
                raise ValueError("missing required 'value' parameter")
            value = int(params["value"])
            if value not in (0, 1, 2):
                raise ValueError(f"tuner value must be 0, 1, or 2, got {value}")
            await self._radio.set_tuner_status(value)
            label = {0: "OFF", 1: "ON", 2: "TUNING"}[value]
            return {"value": value, "label": label}

        q = self._server.command_queue if self._server is not None else None
        if q is None:
            raise RuntimeError("no command queue available")

        match name:
            case "set_band":
                band = int(params["band"])
                q.put(SetBand(band))
                return {"band": band}
            case "set_freq":
                freq = int(params["freq"])
                rx = int(params.get("receiver", 0))
                self._ensure_receiver_supported(rx)
                q.put(SetFreq(freq, receiver=rx))
                return {"freq": freq, "receiver": rx}
            case "set_mode":
                mode = str(params["mode"])
                rx = int(params.get("receiver", 0))
                self._ensure_receiver_supported(rx)
                q.put(SetMode(mode, receiver=rx))
                return {"mode": mode, "receiver": rx}
            case "set_filter":
                fil_str = str(params.get("filter", "FIL1"))
                fil_num = int(fil_str[-1]) if fil_str[-1].isdigit() else 1
                rx = int(params.get("receiver", 0))
                self._ensure_receiver_supported(rx)
                q.put(SetFilter(fil_num, receiver=rx))
                return {"filter": fil_str, "receiver": rx}
            case "set_filter_width":
                width = int(params["width"])
                rx = int(params.get("receiver", 0))
                self._ensure_receiver_supported(rx)
                q.put(SetFilterWidth(width, receiver=rx))
                return {"width": width, "receiver": rx}
            case "set_filter_shape":
                shape = int(params["shape"])
                rx = int(params.get("receiver", 0))
                self._ensure_capability("filter_shape", "set_filter_shape")
                self._ensure_receiver_supported(rx)
                q.put(SetFilterShape(shape, receiver=rx))
                return {"shape": shape, "receiver": rx}
            case "ptt":
                on = bool(params["state"])
                logger.info("handler: PTT %s received", "ON" if on else "OFF")
                q.put(PttOn() if on else PttOff())
                return {"state": on}
            case "ptt_on":
                q.put(PttOn())
                return {}
            case "ptt_off":
                q.put(PttOff())
                return {}
            case "set_rf_power" | "set_power":
                if not isinstance(self._radio, PowerControlCapable):
                    raise ValueError(
                        "command set_rf_power is not supported by this radio "
                        "(missing PowerControlCapable)"
                    )
                level = int(params["level"])
                q.put(SetPower(level))
                return {"level": level}
            case "set_powerstat":
                if not isinstance(self._radio, PowerControlCapable):
                    raise ValueError(
                        "command set_powerstat is not supported by this radio "
                        "(missing PowerControlCapable)"
                    )
                on = bool(params.get("on", True))
                q.put(SetPowerstat(on))
                return {"on": on}
            case "set_rf_gain":
                if not isinstance(self._radio, LevelsCapable):
                    raise ValueError(
                        "command set_rf_gain is not supported by this radio "
                        "(missing LevelsCapable)"
                    )
                level = int(params["level"])
                rx = int(params.get("receiver", 0))
                self._ensure_capability("rf_gain", "set_rf_gain")
                self._ensure_receiver_supported(rx)
                q.put(SetRfGain(level, receiver=rx))
                return {"level": level, "receiver": rx}
            case "set_af_level":
                if not isinstance(self._radio, LevelsCapable):
                    raise ValueError(
                        "command set_af_level is not supported by this radio "
                        "(missing LevelsCapable)"
                    )
                level = int(params["level"])
                rx = int(params.get("receiver", 0))
                self._ensure_capability("af_level", "set_af_level")
                self._ensure_receiver_supported(rx)
                q.put(SetAfLevel(level, receiver=rx))
                return {"level": level, "receiver": rx}
            case "set_sql" | "set_squelch":
                if not isinstance(self._radio, LevelsCapable):
                    raise ValueError(
                        f"command {name!r} is not supported by this radio "
                        "(missing LevelsCapable)"
                    )
                level = int(params["level"])
                rx = int(params.get("receiver", 0))
                self._ensure_capability("squelch", name)
                self._ensure_receiver_supported(rx)
                q.put(SetSquelch(level, receiver=rx))
                return {"level": level, "receiver": rx}
            case "set_nb":
                on = bool(params.get("on", False))
                rx = int(params.get("receiver", 0))
                self._ensure_capability("nb", "set_nb")
                self._ensure_receiver_supported(rx)
                q.put(SetNB(on, receiver=rx))
                return {"on": on, "receiver": rx}
            case "set_nr":
                on = bool(params.get("on", False))
                rx = int(params.get("receiver", 0))
                self._ensure_capability("nr", "set_nr")
                self._ensure_receiver_supported(rx)
                q.put(SetNR(on, receiver=rx))
                return {"on": on, "receiver": rx}
            case "set_nr_level":
                level = int(params["level"])
                rx = int(params.get("receiver", 0))
                self._ensure_capability("nr", "set_nr_level")
                self._ensure_receiver_supported(rx)
                q.put(SetNRLevel(level, receiver=rx))
                return {"level": level, "receiver": rx}
            case "set_nb_level":
                level = int(params["level"])
                rx = int(params.get("receiver", 0))
                self._ensure_capability("nb", "set_nb_level")
                self._ensure_receiver_supported(rx)
                q.put(SetNBLevel(level, receiver=rx))
                return {"level": level, "receiver": rx}
            case "set_auto_notch":
                on = bool(params.get("on", False))
                rx = int(params.get("receiver", 0))
                self._ensure_capability("notch", "set_auto_notch")
                self._ensure_receiver_supported(rx)
                q.put(SetAutoNotch(on, receiver=rx))
                return {"on": on, "receiver": rx}
            case "set_manual_notch":
                on = bool(params.get("on", False))
                rx = int(params.get("receiver", 0))
                self._ensure_capability("notch", "set_manual_notch")
                self._ensure_receiver_supported(rx)
                q.put(SetManualNotch(on, receiver=rx))
                return {"on": on, "receiver": rx}
            case "set_notch_filter":
                level = int(params["value"])
                self._ensure_capability("notch", "set_notch_filter")
                q.put(SetNotchFilter(level))
                return {"value": level}
            case "set_digisel":
                on = bool(params.get("on", False))
                rx = int(params.get("receiver", 0))
                self._ensure_capability("digisel", "set_digisel")
                self._ensure_receiver_supported(rx)
                q.put(SetDigiSel(on, receiver=rx))
                return {"on": on, "receiver": rx}
            case "set_ip_plus" | "set_ipplus":
                on = bool(params.get("on", False))
                rx = int(params.get("receiver", 0))
                self._ensure_capability("ip_plus", "set_ip_plus")
                self._ensure_receiver_supported(rx)
                q.put(SetIpPlus(on, receiver=rx))
                return {"on": on, "receiver": rx}
            case "set_att" | "set_attenuator":
                db = int(params.get("level", params.get("db", 0)))
                rx = int(params.get("receiver", 0))
                self._ensure_capability("attenuator", name)
                self._ensure_receiver_supported(rx)
                q.put(SetAttenuator(db, receiver=rx))
                return {"db": db, "receiver": rx}
            case "set_preamp":
                level = int(params["level"])
                rx = int(params.get("receiver", 0))
                self._ensure_capability("preamp", "set_preamp")
                self._ensure_receiver_supported(rx)
                q.put(SetPreamp(level, receiver=rx))
                return {"level": level, "receiver": rx}
            case "set_pbt_inner":
                level = int(params["value"])
                rx = int(params.get("receiver", 0))
                self._ensure_capability("pbt", "set_pbt_inner")
                self._ensure_receiver_supported(rx)
                q.put(SetPbtInner(level, receiver=rx))
                return {"value": level, "receiver": rx}
            case "set_pbt_outer":
                level = int(params["value"])
                rx = int(params.get("receiver", 0))
                self._ensure_capability("pbt", "set_pbt_outer")
                self._ensure_receiver_supported(rx)
                q.put(SetPbtOuter(level, receiver=rx))
                return {"value": level, "receiver": rx}
            case "set_cw_pitch":
                value = int(params["value"])
                self._ensure_capability("cw", "set_cw_pitch")
                q.put(SetCwPitch(value))
                return {"value": value}
            case "set_data_mode":
                mode = int(params["mode"])
                rx = int(params.get("receiver", 0))
                self._ensure_capability("data_mode", "set_data_mode")
                self._ensure_receiver_supported(rx)
                q.put(SetDataMode(mode, receiver=rx))
                return {"mode": mode, "receiver": rx}
            case "set_mic_gain":
                level = int(params["level"])
                q.put(SetMicGain(level))
                return {"level": level}
            case "set_vox":
                on = bool(params.get("on", False))
                self._ensure_capability("vox", "set_vox")
                q.put(SetVox(on))
                return {"on": on}
            case "set_compressor_level":
                level = int(params["level"])
                self._ensure_capability("compressor", "set_compressor_level")
                q.put(SetCompressorLevel(level))
                return {"level": level}
            case "set_monitor":
                on = bool(params.get("on", False))
                self._ensure_capability("monitor", "set_monitor")
                q.put(SetMonitor(on))
                return {"on": on}
            case "set_monitor_gain":
                level = int(params["level"])
                self._ensure_capability("monitor", "set_monitor_gain")
                q.put(SetMonitorGain(level))
                return {"level": level}
            case "set_dial_lock":
                on = bool(params.get("on", False))
                q.put(SetDialLock(on))
                return {"on": on}
            case "set_agc_time_constant":
                value = int(params["value"])
                rx = int(params.get("receiver", 0))
                self._ensure_receiver_supported(rx)
                q.put(SetAgcTimeConstant(value, receiver=rx))
                return {"value": value, "receiver": rx}
            case "set_agc":
                mode = int(params["mode"])
                rx = int(params.get("receiver", 0))
                self._ensure_receiver_supported(rx)
                q.put(SetAgc(mode, receiver=rx))
                return {"mode": mode, "receiver": rx}
            case "set_rit_status":
                on = bool(params.get("on", False))
                self._ensure_capability("rit", "set_rit_status")
                q.put(SetRitStatus(on))
                return {"on": on}
            case "set_rit_tx_status":
                on = bool(params.get("on", False))
                self._ensure_capability("rit", "set_rit_tx_status")
                q.put(SetRitTxStatus(on))
                return {"on": on}
            case "set_rit_frequency":
                freq = int(params.get("freq", 0))
                self._ensure_capability("rit", "set_rit_frequency")
                q.put(SetRitFrequency(freq))
                return {"freq": freq}
            case "set_split":
                on = bool(params.get("on", False))
                self._ensure_capability("split", "set_split")
                q.put(SetSplit(on))
                return {"on": on}
            case "set_vfo" | "select_vfo":
                vfo = str(params.get("vfo", "A"))
                q.put(SelectVfo(vfo))
                return {"vfo": vfo}
            case "vfo_swap":
                q.put(VfoSwap())
                return {}
            case "vfo_equalize":
                q.put(VfoEqualize())
                return {}
            case "switch_scope_receiver":
                receiver = int(params.get("receiver", 0))
                self._ensure_capability("scope", "switch_scope_receiver")
                self._ensure_receiver_supported(receiver)
                q.put(SwitchScopeReceiver(receiver))
                return {"receiver": receiver}
            case "set_scope_during_tx":
                on = bool(params["on"])
                self._ensure_capability("scope", "set_scope_during_tx")
                q.put(SetScopeDuringTx(on))
                return {"on": on}
            case "set_scope_center_type":
                center_type = int(params["center_type"])
                self._ensure_capability("scope", "set_scope_center_type")
                q.put(SetScopeCenterType(center_type))
                return {"center_type": center_type}
            case "set_scope_fixed_edge":
                edge = int(params["edge"])
                start_hz = int(params["start_hz"])
                end_hz = int(params["end_hz"])
                self._ensure_capability("scope", "set_scope_fixed_edge")
                q.put(SetScopeFixedEdge(edge, start_hz, end_hz))
                return {"edge": edge, "start_hz": start_hz, "end_hz": end_hz}
            case "set_antenna_1":
                on = bool(params.get("on", False))
                q.put(SetAntenna1(on))
                return {"on": on}
            case "set_antenna_2":
                on = bool(params.get("on", False))
                q.put(SetAntenna2(on))
                return {"on": on}
            case "set_rx_antenna_ant1":
                on = bool(params.get("on", False))
                q.put(SetRxAntennaAnt1(on))
                return {"on": on}
            case "set_rx_antenna_ant2":
                on = bool(params.get("on", False))
                q.put(SetRxAntennaAnt2(on))
                return {"on": on}
            case "set_system_date":
                year = int(params["year"])
                month = int(params["month"])
                day = int(params["day"])
                q.put(SetSystemDate(year, month, day))
                return {"year": year, "month": month, "day": day}
            case "set_system_time":
                hour = int(params["hour"])
                minute = int(params["minute"])
                q.put(SetSystemTime(hour, minute))
                return {"hour": hour, "minute": minute}
            case "set_acc1_mod_level":
                level = int(params["level"])
                q.put(SetAcc1ModLevel(level))
                return {"level": level}
            case "set_usb_mod_level":
                level = int(params["level"])
                q.put(SetUsbModLevel(level))
                return {"level": level}
            case "set_lan_mod_level":
                level = int(params["level"])
                q.put(SetLanModLevel(level))
                return {"level": level}
            case "set_dual_watch":
                on = bool(params.get("on", False))
                self._ensure_capability("dual_rx", "set_dual_watch")
                q.put(SetDualWatch(on))
                return {"on": on}
            case "set_comp" | "set_compressor":
                on = bool(params.get("on", True))
                q.put(SetCompressor(on))
                return {"on": on}
            case _:
                raise ValueError(f"unhandled command: {name!r}")

    @property
    def subscribed_streams(self) -> frozenset[str]:
        """Current subscribed stream names."""
        return frozenset(self._subscribed_streams)


class ScopeHandler:
    """Handles the /api/v1/scope binary WebSocket channel.

    Receives scope frames from the radio and forwards them to the client.
    Implements backpressure: drops frames when the send queue exceeds
    HIGH_WATERMARK.

    Args:
        ws: Established WebSocket connection.
        radio: Radio protocol instance (may be None).
    """

    def __init__(
        self,
        ws: WebSocketConnection,
        radio: "Radio | None",
        server: Any = None,
    ) -> None:
        self._ws = ws
        self._radio = radio
        self._server = server
        self._seq: int = 0
        self._frame_queue: asyncio.Queue[bytes] = asyncio.Queue(
            maxsize=HIGH_WATERMARK * 2
        )
        self._running = False

    def enqueue_frame(self, frame: "ScopeFrame") -> None:
        """Enqueue a scope frame (called by server broadcast)."""
        if not self._running:
            return
        encoded = encode_scope_frame(frame, self._seq)
        self._seq = (self._seq + 1) & 0xFFFF
        if self._frame_queue.full():
            try:
                self._frame_queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        try:
            self._frame_queue.put_nowait(encoded)
        except asyncio.QueueFull:
            pass

    async def run(self) -> None:
        """Run the scope channel lifecycle."""
        self._running = True
        # Register with server — server handles enable_scope() once
        if self._server is not None:
            await self._server.ensure_scope_enabled(self)
        try:
            sender_task = asyncio.create_task(self._sender())
            try:
                while True:
                    opcode, payload = await self._ws.recv()
                    if opcode == WS_OP_TEXT:
                        self._handle_control(payload.decode("utf-8"))
            except EOFError:
                pass
            finally:
                sender_task.cancel()
                try:
                    await sender_task
                except asyncio.CancelledError:
                    pass
        finally:
            self._running = False
            if self._server is not None:
                self._server.unregister_scope_handler(self)

    def _handle_control(self, text: str) -> None:
        """Handle optional JSON control messages on the scope channel."""
        try:
            msg = decode_json(text)
            logger.debug("scope: control message: %r", msg.get("type"))
        except ValueError:
            pass

    async def _sender(self) -> None:
        """Continuously dequeues and sends scope frames."""
        sent = 0
        while True:
            try:
                data = await asyncio.wait_for(
                    self._frame_queue.get(),
                    timeout=1.0,
                )
                await self._ws.send_binary(data)
                sent += 1
                if sent <= 3 or sent % 300 == 0:
                    logger.debug("scope: sent frame #%d (%d bytes)", sent, len(data))
            except TimeoutError:
                if sent == 0:
                    logger.debug(
                        "scope: sender timeout, no frames yet, qsize=%d",
                        self._frame_queue.qsize(),
                    )
            except Exception as exc:
                logger.warning("scope: sender error: %s", exc)
                break

    def push_frame(self, frame: ScopeFrame) -> None:
        """Push a scope frame directly (used by server for testing/injection).

        Args:
            frame: Scope frame to forward to the client.
        """
        self.enqueue_frame(frame)


class AudioBroadcaster:
    """Single-instance RX audio broadcaster shared by all AudioHandler clients.

    Uses :class:`~icom_lan.audio_bus.AudioBus` to subscribe to the radio's
    opus RX stream.  Multiple consumers (WebSocket clients, audio bridge,
    recorders) can all share the same stream through the bus.
    """

    HIGH_WATERMARK: int = 10

    def __init__(self, radio: "Radio | None") -> None:
        self._radio = radio
        self._clients: dict[int, asyncio.Queue[bytes]] = {}
        self._client_ws: dict[int, WebSocketConnection] = {}
        self._subscription: _AudioSubscription | None = None
        self._relay_task: asyncio.Task[None] | None = None
        self._seq: int = 0
        self._web_codec: int = AUDIO_CODEC_PCM16
        self._sample_rate: int = 48000
        self._channels: int = 1
        self._lock = asyncio.Lock()

    async def subscribe(
        self, ws: WebSocketConnection | None = None
    ) -> asyncio.Queue[bytes]:
        """Register a new WebSocket client and start relaying if first."""
        queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=self.HIGH_WATERMARK)
        client_id = id(queue)
        async with self._lock:
            self._clients[client_id] = queue
            if ws is not None:
                self._client_ws[client_id] = ws
            if self._subscription is None and self._radio:
                await self._start_relay()
        logger.info("audio-broadcaster: client added (total=%d)", len(self._clients))
        return queue

    async def unsubscribe(self, queue: asyncio.Queue[bytes]) -> None:
        """Unregister a client and stop relay if last."""
        client_id = id(queue)
        async with self._lock:
            self._clients.pop(client_id, None)
            self._client_ws.pop(client_id, None)
            if not self._clients and self._subscription is not None:
                await self._stop_relay()
        logger.info("audio-broadcaster: client removed (total=%d)", len(self._clients))

    def reap_dead_clients(self) -> int:
        """Remove clients whose WebSocket is no longer alive. Returns count removed."""
        dead_ids = [
            cid
            for cid, ws in list(self._client_ws.items())
            if not ws.is_alive()
        ]
        for cid in dead_ids:
            self._clients.pop(cid, None)
            self._client_ws.pop(cid, None)
        if dead_ids:
            logger.info(
                "audio-broadcaster: reaped %d dead clients (total=%d)",
                len(dead_ids),
                len(self._clients),
            )
        return len(dead_ids)

    async def _start_relay(self) -> None:
        from ..radio_protocol import AudioCapable

        if not self._radio or not isinstance(self._radio, AudioCapable):
            return

        # Negotiate web codec from radio's actual audio codec
        _codec = getattr(self._radio, "audio_codec", None)
        if isinstance(_codec, AudioCodec):
            # Map radio codec → web transport codec
            _CODEC_MAP = {
                AudioCodec.OPUS_1CH: AUDIO_CODEC_OPUS,
                AudioCodec.OPUS_2CH: AUDIO_CODEC_OPUS,
                AudioCodec.PCM_1CH_16BIT: AUDIO_CODEC_PCM16,
                AudioCodec.PCM_2CH_16BIT: AUDIO_CODEC_PCM16,
                AudioCodec.PCM_1CH_8BIT: AUDIO_CODEC_PCM16,  # upcast in future
                AudioCodec.PCM_2CH_8BIT: AUDIO_CODEC_PCM16,
                AudioCodec.ULAW_1CH: AUDIO_CODEC_PCM16,  # TODO: decode ulaw→pcm
                AudioCodec.ULAW_2CH: AUDIO_CODEC_PCM16,
            }
            self._web_codec = _CODEC_MAP.get(_codec, AUDIO_CODEC_PCM16)
            if _codec in (
                AudioCodec.PCM_2CH_8BIT,
                AudioCodec.PCM_2CH_16BIT,
                AudioCodec.ULAW_2CH,
                AudioCodec.OPUS_2CH,
            ):
                self._channels = 2
            logger.info(
                "audio-broadcaster: radio codec=%s (0x%02x) → web_codec=0x%02x",
                _codec.name,
                int(_codec),
                self._web_codec,
            )
        else:
            logger.warning(
                "audio-broadcaster: no radio codec info, defaulting to PCM16"
            )
        _sr = getattr(self._radio, "audio_sample_rate", None)
        if isinstance(_sr, int) and not isinstance(_sr, bool) and _sr > 0:
            self._sample_rate = _sr
        logger.info(
            "audio-broadcaster: starting relay codec=0x%02x sr=%d ch=%d",
            self._web_codec,
            self._sample_rate,
            self._channels,
        )

        try:
            bus = self._radio.audio_bus
            self._subscription = cast(_AudioBus, bus).subscribe(name="web-audio")
            await self._subscription.start()
            self._relay_task = asyncio.create_task(self._relay_loop())
        except Exception:
            logger.exception("audio-broadcaster: failed to start relay")
            self._subscription = None

    async def _relay_loop(self) -> None:
        """Read packets from AudioBus subscription and fan out to WS clients."""
        if self._subscription is None:
            return
        try:
            async for pkt in self._subscription:
                if pkt is None:
                    continue
                if self._seq < 3 or self._seq % 500 == 0:
                    logger.info(
                        "audio: rx packet #%d, web_codec=0x%02x, data=%d bytes",
                        self._seq,
                        self._web_codec,
                        len(pkt.data),
                    )
                frame = encode_audio_frame(
                    MSG_TYPE_AUDIO_RX,
                    self._web_codec,
                    self._seq,
                    self._sample_rate // 100,
                    self._channels,
                    20,
                    pkt.data,
                )
                self._seq = (self._seq + 1) & 0xFFFF
                dead_ids: list[int] = []
                for client_id, q in list(self._clients.items()):
                    ws = self._client_ws.get(client_id)
                    if ws is not None and not ws.is_alive():
                        dead_ids.append(client_id)
                        continue
                    try:
                        q.put_nowait(frame)
                    except asyncio.QueueFull:
                        try:
                            q.get_nowait()
                        except asyncio.QueueEmpty:
                            pass
                        try:
                            q.put_nowait(frame)
                        except asyncio.QueueFull:
                            pass
                for client_id in dead_ids:
                    self._clients.pop(client_id, None)
                    self._client_ws.pop(client_id, None)
                    logger.info("audio-broadcaster: removed dead client during relay")
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("audio-broadcaster: relay loop error")

    async def _stop_relay(self) -> None:
        if self._relay_task is not None:
            self._relay_task.cancel()
            try:
                await self._relay_task
            except asyncio.CancelledError:
                pass
            self._relay_task = None
        if self._subscription is not None:
            self._subscription.stop()
            self._subscription = None
        logger.info("audio-broadcaster: relay stopped")


class AudioHandler:
    """Handler for the /api/v1/audio WebSocket channel.

    Streams RX audio from the radio to the browser as binary Opus frames,
    and accepts TX audio frames from the browser to push to the radio.

    Control flow:
        Client sends JSON text: ``audio_start`` / ``audio_stop``
        Server sends binary Opus frames continuously while RX is active.
        Client sends binary Opus frames while TX is active (after PTT on).

    Args:
        ws: Established WebSocket connection.
        radio: Radio protocol instance (may be None).
    """

    HIGH_WATERMARK: int = 10  # max queued audio frames before dropping

    def __init__(
        self,
        ws: WebSocketConnection,
        radio: "Radio | None",
        broadcaster: "AudioBroadcaster | None" = None,
    ) -> None:
        self._ws = ws
        self._radio = radio
        self._broadcaster = broadcaster
        self._rx_active = False
        self._tx_active = False
        self._seq: int = 0
        self._frame_queue: asyncio.Queue[bytes] = asyncio.Queue(
            maxsize=self.HIGH_WATERMARK,
        )
        self._done = asyncio.Event()
        # Opus decoder for TX when radio uses PCM codec
        self._transcoder: PcmOpusTranscoder | None = None
        try:
            self._transcoder = create_pcm_opus_transcoder()
        except Exception:
            logger.debug("audio: TX transcoder unavailable (opus codec missing?)")

    async def run(self) -> None:
        """Run the audio channel lifecycle."""
        sender = asyncio.create_task(self._sender_loop())
        try:
            await self._reader_loop()
        except Exception:
            logger.exception("audio: handler error")
        finally:
            self._done.set()
            sender.cancel()
            await self._stop_rx()
            logger.info("audio: handler finished")

    async def _reader_loop(self) -> None:
        """Read control messages and TX audio from client."""
        try:
            while True:
                opcode, payload = await self._ws.recv()
                if opcode == WS_OP_TEXT:
                    try:
                        msg = decode_json(payload.decode("utf-8"))
                    except ValueError:
                        continue
                    await self._handle_control(msg)
                elif opcode == WS_OP_BINARY:
                    # TX audio frame from browser
                    await self._handle_tx_audio(payload)
        except EOFError as exc:
            logger.info("audio: reader EOF: %s", exc)
        except asyncio.IncompleteReadError as exc:
            logger.info("audio: reader incomplete: %s", exc)

    async def _handle_control(self, msg: dict[str, Any]) -> None:
        """Handle audio_start / audio_stop messages."""
        logger.info("audio: control msg: %s", msg)
        msg_type = msg.get("type", "")
        direction = msg.get("direction", "rx")

        if msg_type == "audio_start":
            if direction == "rx":
                await self._start_rx()
            elif direction == "tx":
                self._tx_active = True
                logger.info("audio: TX active")
        elif msg_type == "audio_stop":
            if direction == "rx":
                await self._stop_rx()
            elif direction == "tx":
                self._tx_active = False
                logger.info("audio: TX stopped")

    async def _start_rx(self) -> None:
        """Subscribe to audio broadcaster for RX frames."""
        if not self._broadcaster:
            return
        self._rx_active = True
        self._frame_queue = await self._broadcaster.subscribe(ws=self._ws)
        logger.info("audio: subscribed to RX broadcast")

    async def _stop_rx(self) -> None:
        """Unsubscribe from audio broadcaster."""
        if not self._rx_active or not self._broadcaster:
            return
        self._rx_active = False
        await self._broadcaster.unsubscribe(self._frame_queue)
        logger.info("audio: unsubscribed from RX broadcast")

    async def _handle_tx_audio(self, payload: bytes) -> None:
        """Forward TX audio from browser to radio."""
        if not self._tx_active:
            logger.debug(
                "audio: TX frame ignored (tx_active=False), size=%d", len(payload)
            )
            return
        if not self._radio:
            logger.warning("audio: TX frame ignored (no radio), size=%d", len(payload))
            return
        from ..radio_protocol import AudioCapable

        if not isinstance(self._radio, AudioCapable):
            logger.warning(
                "audio: TX frame ignored (radio not AudioCapable), size=%d",
                len(payload),
            )
            return
        if len(payload) < AUDIO_HEADER_SIZE:
            logger.warning(
                "audio: TX frame too small (%d < %d), ignoring",
                len(payload),
                AUDIO_HEADER_SIZE,
            )
            return
        # Extract audio data after 8-byte header (frontend sends Opus)
        opus_data = payload[AUDIO_HEADER_SIZE:]
        if opus_data:
            try:
                # Check if radio uses PCM codec → decode Opus → PCM
                audio_codec = getattr(self._radio, "audio_codec", None)
                if audio_codec == AudioCodec.PCM_1CH_16BIT and self._transcoder:
                    try:
                        # Decode Opus → PCM16
                        pcm_data = self._transcoder.opus_to_pcm(opus_data)
                        # Send PCM via push_audio_tx_opus (method accepts any codec)
                        await self._radio.push_audio_tx_opus(pcm_data)
                        tx_data_desc = f"{len(pcm_data)} bytes pcm"
                    except Exception as e:
                        logger.warning(
                            "audio: Opus decode failed: %s, dropping frame", e
                        )
                        return
                else:
                    # Radio uses Opus or PCM_1CH_8BIT/etc → send Opus as-is
                    await self._radio.push_audio_tx_opus(opus_data)
                    tx_data_desc = f"{len(opus_data)} bytes opus"

                # Log every 50th frame to avoid spam
                if not hasattr(self, "_tx_frame_count"):
                    self._tx_frame_count = 0
                self._tx_frame_count += 1
                if self._tx_frame_count <= 3 or self._tx_frame_count % 50 == 0:
                    logger.info(
                        "audio: TX frame #%d pushed to radio (%s)",
                        self._tx_frame_count,
                        tx_data_desc,
                    )
            except Exception:
                logger.warning("audio: push TX error", exc_info=True)

    async def _sender_loop(self) -> None:
        """Send queued audio frames to the WebSocket client."""
        sent = 0
        try:
            while not self._done.is_set():
                try:
                    frame = await asyncio.wait_for(
                        self._frame_queue.get(),
                        timeout=0.5,
                    )
                    # Wrap send in timeout to detect dead WebSocket connections
                    # If send blocks >5s, connection is likely dead (half-open TCP)
                    try:
                        await asyncio.wait_for(
                            self._ws.send_binary(frame),
                            timeout=5.0,
                        )
                    except TimeoutError:
                        logger.warning(
                            "audio: send timeout after %d frames (dead connection), exiting",
                            sent,
                        )
                        break  # Exit loop, trigger cleanup in finally
                    sent += 1
                    if sent <= 3 or sent % 500 == 0:
                        logger.info(
                            "audio: sent frame #%d (%d bytes)", sent, len(frame)
                        )
                except TimeoutError:
                    continue
        except asyncio.CancelledError:
            logger.info("audio: sender cancelled after %d frames", sent)
        except (EOFError, OSError) as exc:
            logger.info("audio: sender stopped after %d frames: %s", sent, exc)
        except Exception:
            logger.exception("audio: sender error after %d frames", sent)


class _AudioPacketLike(Protocol):
    data: bytes


class _AudioSubscription(Protocol):
    async def start(self) -> None: ...

    def stop(self) -> None: ...

    def __aiter__(self) -> AsyncIterator[_AudioPacketLike | None]: ...


class _AudioBus(Protocol):
    def subscribe(self, name: str = "") -> _AudioSubscription: ...
