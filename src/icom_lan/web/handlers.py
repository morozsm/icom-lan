"""Route handlers for WebSocket channels and HTTP endpoints.

Each handler manages the lifecycle of one client connection on one channel:
- control (/api/v1/ws): JSON commands, events, state
- scope (/api/v1/scope): binary scope frames with backpressure
- meters (/api/v1/meters): binary meter frames
- audio (/api/v1/audio): placeholder for future audio streaming
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

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
    encode_meter_frame,
    encode_scope_frame,
)
from .radio_poller import (
    PttOff,
    PttOn,
    SelectVfo,
    SetAfLevel,
    SetBand,
    SetAttenuator,
    SetFilter,
    SetFreq,
    SetMode,
    SetPower,
    SetPreamp,
    SetRfGain,
    SetSquelch,
    SetNB,
    SetNR,
    SetDigiSel,
    SetIpPlus,
    SwitchScopeReceiver,
    VfoEqualize,
    VfoSwap,
)
from .websocket import WS_OP_BINARY, WS_OP_TEXT, WebSocketConnection

if TYPE_CHECKING:
    from ..radio import IcomRadio
    from ..radio_protocol import Radio, ScopeCapable

__all__ = [
    "HIGH_WATERMARK",
    "ControlHandler",
    "ScopeHandler",
    "MetersHandler",
    "AudioHandler",
]

logger = logging.getLogger(__name__)

HIGH_WATERMARK = 5  # Max queued scope/meter frames before dropping


class ControlHandler:
    """Handles the /api/v1/ws control WebSocket channel.

    Receives JSON commands from the client and enqueues them via the
    server's CommandQueue.  Receives broadcast events from RadioPoller
    via an asyncio.Queue and forwards them to the WebSocket.

    Args:
        ws: Established WebSocket connection.
        radio: IcomRadio instance (may be None in standalone mode).
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
            "ptt",
            "set_power",
            "set_rf_gain",
            "set_af_level",
            "set_sql",
            "set_nb",
            "set_nr",
            "set_digisel",
            "set_ipplus",
            "set_att",
            "set_preamp",
            "select_vfo",
            "vfo_swap",
            "vfo_equalize",
            "switch_scope_receiver",
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

    async def run(self) -> None:
        """Run the control channel lifecycle."""
        await self._send_hello()
        if self._server is not None:
            self._server.register_control_event_queue(self._event_queue)
        event_task: asyncio.Task[None] = asyncio.create_task(
            self._event_sender_loop()
        )
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
                if "state" in self._subscribed_streams:
                    await self._send_json(event)
        except asyncio.CancelledError:
            pass

    async def _send_hello(self) -> None:
        msg = {
            "type": "hello",
            "proto": 1,
            "server": "icom-lan",
            "version": self._version,
            "radio": self._radio_model,
            "connected": self._radio.connected if self._radio else False,
            "capabilities": ["scope", "audio", "tx"],
        }
        await self._ws.send_text(encode_json(msg))

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
            await self._send_json({"type": "response", "id": msg_id, "ok": False,
                                   "error": "no_radio", "message": "no radio instance"})
            return
        try:
            if self._radio.connected:
                await self._send_json({"type": "response", "id": msg_id, "ok": True,
                                       "result": {"status": "already_connected"}})
                return
            if hasattr(self._radio, 'soft_reconnect'):
                try:
                    await self._radio.soft_reconnect()
                except Exception:
                    logger.info("soft_reconnect failed, trying full connect")
                    await self._radio.connect()
            else:
                await self._radio.connect()
            await self._send_json({"type": "response", "id": msg_id, "ok": True,
                                   "result": {"status": "connected"}})
            await self._broadcast_connection_state(True)
        except Exception as exc:
            logger.warning("radio_connect failed: %s", exc)
            await self._send_json({"type": "response", "id": msg_id, "ok": False,
                                   "error": "connect_failed", "message": str(exc)})

    async def _handle_radio_disconnect(self, msg: dict[str, Any]) -> None:
        """Handle radio_disconnect request — disconnect the radio."""
        logger.info("radio_disconnect requested")
        msg_id = msg.get("id", "")
        if self._radio is None:
            await self._send_json({"type": "response", "id": msg_id, "ok": False,
                                   "error": "no_radio", "message": "no radio instance"})
            return
        try:
            if not self._radio.connected:
                await self._send_json({"type": "response", "id": msg_id, "ok": True,
                                       "result": {"status": "already_disconnected"}})
                return
            await self._radio.soft_disconnect()
            await self._send_json({"type": "response", "id": msg_id, "ok": True,
                                   "result": {"status": "disconnected"}})
            await self._broadcast_connection_state(False)
        except Exception as exc:
            logger.warning("radio_disconnect failed: %s", exc)
            await self._send_json({"type": "response", "id": msg_id, "ok": False,
                                   "error": "disconnect_failed", "message": str(exc)})

    async def _broadcast_connection_state(self, connected: bool) -> None:
        """Broadcast connection state change to this client."""
        await self._send_json({"type": "event", "event": "connection_state",
                               "connected": connected})

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
        data: dict[str, Any] = {
            "freq_a": 0,
            "freq_b": 0,
            "mode": "USB",
            "filter": "FIL1",
            "ptt": False,
            "power": 0,
            "smeter": 0,
            "swr": 0,
            "scope": {
                "mode": 0,
                "start_freq": 0,
                "end_freq": 0,
                "receiver": 0,
            },
        }
        # Read from state cache — zero CI-V.
        cache = (
            self._server.state_cache
            if self._server is not None
            else None
        )
        if cache is None and self._radio is not None:
            cache = self._radio.state_cache
        if cache is not None:
            try:
                if cache.freq_ts > 0.0:
                    data["freq_a"] = cache.freq
                if cache.mode_ts > 0.0:
                    data["mode"] = cache.mode
                    if cache.filter_width is not None:
                        data["filter"] = f"FIL{cache.filter_width}"
                data["ptt"] = cache.ptt
            except Exception as exc:
                logger.debug("control: state cache read failed: %s", exc)
        msg_out = {"type": "state", "data": data}
        await self._ws.send_text(encode_json(msg_out))

    async def _handle_command(self, msg: dict[str, Any]) -> None:
        cmd_id = msg.get("id", "")
        name = msg.get("name", "")
        params = msg.get("params", {})

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
            result = self._enqueue_command(name, params)
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

    def _enqueue_command(
        self, name: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Build a Command dataclass, enqueue it, and return the ack result."""
        q = self._server.command_queue if self._server is not None else None
        if q is None:
            raise RuntimeError("no command queue available")
        if name == "set_freq":
            logger.info("enqueue_command: %s params=%s", name, params)
        else:
            logger.info("enqueue_command: %s params=%s", name, params)

        match name:
            case "set_band":
                band = int(params["band"])
                q.put(SetBand(band))
                return {"band": band}
            case "set_freq":
                freq = int(params["freq"])
                rx = int(params.get("receiver", 0))
                q.put(SetFreq(freq, receiver=rx))
                return {"freq": freq, "receiver": rx}
            case "set_mode":
                mode = str(params["mode"])
                rx = int(params.get("receiver", 0))
                q.put(SetMode(mode, receiver=rx))
                return {"mode": mode, "receiver": rx}
            case "set_filter":
                fil_str = str(params.get("filter", "FIL1"))
                fil_num = int(fil_str[-1]) if fil_str[-1].isdigit() else 1
                rx = int(params.get("receiver", 0))
                q.put(SetFilter(fil_num, receiver=rx))
                return {"filter": fil_str, "receiver": rx}
            case "ptt":
                on = bool(params["state"])
                q.put(PttOn() if on else PttOff())
                return {"state": on}
            case "set_power":
                level = int(params["level"])
                q.put(SetPower(level))
                return {"level": level}
            case "set_rf_gain":
                level = int(params["level"])
                rx = int(params.get("receiver", 0))
                q.put(SetRfGain(level, receiver=rx))
                return {"level": level, "receiver": rx}
            case "set_af_level":
                level = int(params["level"])
                rx = int(params.get("receiver", 0))
                q.put(SetAfLevel(level, receiver=rx))
                return {"level": level, "receiver": rx}
            case "set_sql":
                level = int(params["level"])
                rx = int(params.get("receiver", 0))
                q.put(SetSquelch(level, receiver=rx))
                return {"level": level, "receiver": rx}
            case "set_nb":
                on = bool(params.get("on", False))
                rx = int(params.get("receiver", 0))
                q.put(SetNB(on, receiver=rx))
                return {"on": on, "receiver": rx}
            case "set_nr":
                on = bool(params.get("on", False))
                rx = int(params.get("receiver", 0))
                q.put(SetNR(on, receiver=rx))
                return {"on": on, "receiver": rx}
            case "set_digisel":
                on = bool(params.get("on", False))
                rx = int(params.get("receiver", 0))
                q.put(SetDigiSel(on, receiver=rx))
                return {"on": on, "receiver": rx}
            case "set_ipplus":
                on = bool(params.get("on", False))
                rx = int(params.get("receiver", 0))
                q.put(SetIpPlus(on, receiver=rx))
                return {"on": on, "receiver": rx}
            case "set_att":
                db = int(params["db"])
                rx = int(params.get("receiver", 0))
                q.put(SetAttenuator(db, receiver=rx))
                return {"db": db, "receiver": rx}
            case "set_preamp":
                level = int(params["level"])
                rx = int(params.get("receiver", 0))
                q.put(SetPreamp(level, receiver=rx))
                return {"level": level, "receiver": rx}
            case "select_vfo":
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
                q.put(SwitchScopeReceiver(receiver))
                return {"receiver": receiver}
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
        radio: IcomRadio instance (may be None).
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
                    self._frame_queue.get(), timeout=1.0,
                )
                await self._ws.send_binary(data)
                sent += 1
                if sent <= 3 or sent % 300 == 0:
                    logger.debug("scope: sent frame #%d (%d bytes)", sent, len(data))
            except TimeoutError:
                if sent == 0:
                    logger.debug("scope: sender timeout, no frames yet, qsize=%d", self._frame_queue.qsize())
            except Exception as exc:
                logger.warning("scope: sender error: %s", exc)
                break

    def push_frame(self, frame: ScopeFrame) -> None:
        """Push a scope frame directly (used by server for testing/injection).

        Args:
            frame: Scope frame to forward to the client.
        """
        self.enqueue_frame(frame)


class MetersHandler:
    """Handles the /api/v1/meters binary WebSocket channel.

    Receives meter frames broadcast by RadioPoller (via server) and
    forwards them to the client.  Implements backpressure: drops frames
    when queue exceeds HIGH_WATERMARK.

    Args:
        ws: Established WebSocket connection.
        radio: IcomRadio instance (may be None).
        server: WebServer instance for meter broadcast registration.
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
        self._active = False
        self._frame_queue: asyncio.Queue[bytes] = asyncio.Queue(
            maxsize=HIGH_WATERMARK * 2
        )

    async def run(self) -> None:
        """Run the meters channel lifecycle.

        Reads JSON control messages (meters_start/stop).  On meters_start,
        registers with the server for meter broadcasts from RadioPoller.
        """
        sender_task: asyncio.Task[None] = asyncio.create_task(self._sender())
        try:
            while True:
                opcode, payload = await self._ws.recv()
                if opcode != WS_OP_TEXT:
                    continue
                try:
                    msg = decode_json(payload.decode("utf-8"))
                except ValueError:
                    continue

                msg_type = msg.get("type")
                if msg_type == "meters_start":
                    self._active = True
                    if self._server is not None:
                        self._server.register_meter_handler(self)
                elif msg_type == "meters_stop":
                    self._active = False
                    if self._server is not None:
                        self._server.unregister_meter_handler(self)
        except EOFError:
            pass
        finally:
            self._active = False
            if self._server is not None:
                self._server.unregister_meter_handler(self)
            sender_task.cancel()
            try:
                await sender_task
            except asyncio.CancelledError:
                pass

    def enqueue_frame(self, readings: list[tuple[int, int]]) -> None:
        """Enqueue meter readings broadcast by the server's MeterPoller.

        Args:
            readings: List of (meter_id, value) pairs.
        """
        if not self._active:
            return
        encoded = encode_meter_frame(readings, self._seq)
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

    async def _sender(self) -> None:
        """Continuously dequeues and sends meter frames."""
        while True:
            try:
                data = await asyncio.wait_for(
                    self._frame_queue.get(), timeout=1.0
                )
                await self._ws.send_binary(data)
            except asyncio.TimeoutError:
                pass

    def push_frame(self, meters: list[tuple[int, int]]) -> None:
        """Push a meter frame directly (used for testing/injection).

        Args:
            meters: List of (meter_id, value) pairs.
        """
        encoded = encode_meter_frame(meters, self._seq)
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
        self._subscription = None  # AudioSubscription
        self._relay_task: asyncio.Task | None = None
        self._seq: int = 0
        self._web_codec: int = AUDIO_CODEC_PCM16
        self._sample_rate: int = 48000
        self._channels: int = 1
        self._lock = asyncio.Lock()

    async def subscribe(self) -> asyncio.Queue[bytes]:
        """Register a new WebSocket client and start relaying if first."""
        queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=self.HIGH_WATERMARK)
        client_id = id(queue)
        async with self._lock:
            self._clients[client_id] = queue
            if self._subscription is None and self._radio:
                await self._start_relay()
        logger.info("audio-broadcaster: client added (total=%d)", len(self._clients))
        return queue

    async def unsubscribe(self, queue: asyncio.Queue[bytes]) -> None:
        """Unregister a client and stop relay if last."""
        client_id = id(queue)
        async with self._lock:
            self._clients.pop(client_id, None)
            if not self._clients and self._subscription is not None:
                await self._stop_relay()
        logger.info("audio-broadcaster: client removed (total=%d)", len(self._clients))

    async def _start_relay(self) -> None:
        from ..radio_protocol import AudioCapable
        if not self._radio or not isinstance(self._radio, AudioCapable):
            return

        _codec = getattr(self._radio, "audio_codec", None)
        if isinstance(_codec, AudioCodec):
            if _codec in (AudioCodec.OPUS_1CH, AudioCodec.OPUS_2CH):
                self._web_codec = AUDIO_CODEC_OPUS
            if _codec in (
                AudioCodec.PCM_2CH_8BIT, AudioCodec.PCM_2CH_16BIT,
                AudioCodec.ULAW_2CH, AudioCodec.OPUS_2CH,
            ):
                self._channels = 2
        _sr = getattr(self._radio, "audio_sample_rate", None)
        if isinstance(_sr, int) and not isinstance(_sr, bool) and _sr > 0:
            self._sample_rate = _sr
        logger.info(
            "audio-broadcaster: starting relay codec=0x%02x sr=%d ch=%d",
            self._web_codec, self._sample_rate, self._channels,
        )

        try:
            bus = self._radio.audio_bus
            self._subscription = bus.subscribe(name="web-audio")
            await self._subscription.start()
            self._relay_task = asyncio.create_task(self._relay_loop())
        except Exception:
            logger.exception("audio-broadcaster: failed to start relay")
            self._subscription = None

    async def _relay_loop(self) -> None:
        """Read packets from AudioBus subscription and fan out to WS clients."""
        try:
            async for pkt in self._subscription:
                if pkt is None:
                    continue
                if self._seq < 3 or self._seq % 500 == 0:
                    logger.info(
                        "audio: rx packet #%d, web_codec=0x%02x, data=%d bytes",
                        self._seq, self._web_codec, len(pkt.data),
                    )
                frame = encode_audio_frame(
                    MSG_TYPE_AUDIO_RX, self._web_codec, self._seq,
                    self._sample_rate // 100, self._channels, 20, pkt.data,
                )
                self._seq = (self._seq + 1) & 0xFFFF
                for q in list(self._clients.values()):
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
        radio: IcomRadio instance (may be None).
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

    async def run(self) -> None:
        """Run the audio channel lifecycle."""
        sender = asyncio.create_task(self._sender_loop())
        try:
            await self._reader_loop()
        finally:
            self._done.set()
            sender.cancel()
            await self._stop_rx()

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
        except EOFError:
            pass

    async def _handle_control(self, msg: dict[str, Any]) -> None:
        """Handle audio_start / audio_stop messages."""
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
        self._frame_queue = await self._broadcaster.subscribe()
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
        if not self._tx_active or not self._radio:
            return
        from ..radio_protocol import AudioCapable
        if not isinstance(self._radio, AudioCapable):
            return
        if len(payload) < AUDIO_HEADER_SIZE:
            return
        # Extract opus data after 8-byte header
        opus_data = payload[AUDIO_HEADER_SIZE:]
        if opus_data:
            try:
                await self._radio.push_audio_tx_opus(opus_data)
            except Exception:
                logger.debug("audio: push TX error", exc_info=True)

    async def _sender_loop(self) -> None:
        """Send queued audio frames to the WebSocket client."""
        sent = 0
        try:
            while not self._done.is_set():
                try:
                    frame = await asyncio.wait_for(
                        self._frame_queue.get(), timeout=0.5,
                    )
                    await self._ws.send_binary(frame)
                    sent += 1
                    if sent <= 3 or sent % 500 == 0:
                        logger.info("audio: sent frame #%d (%d bytes)", sent, len(frame))
                except TimeoutError:
                    continue
        except (EOFError, OSError) as exc:
            logger.info("audio: sender stopped after %d frames: %s", sent, exc)
