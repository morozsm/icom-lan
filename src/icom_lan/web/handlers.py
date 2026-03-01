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
    METER_ALC,
    METER_POWER,
    METER_SMETER_MAIN,
    METER_SWR,
    MSG_TYPE_AUDIO_RX,
    decode_json,
    encode_audio_frame,
    encode_json,
    encode_meter_frame,
    encode_scope_frame,
)
from .websocket import WS_OP_BINARY, WS_OP_TEXT, WebSocketConnection

if TYPE_CHECKING:
    from ..radio import IcomRadio

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

    Receives JSON commands from the client and dispatches them to the radio.
    Sends hello on connect, state snapshot after subscribe, and events
    for state changes.

    Args:
        ws: Established WebSocket connection.
        radio: IcomRadio instance (may be None in standalone mode).
        server_version: Version string for the hello message.
        radio_model: Radio model string for the hello message.
    """

    _COMMANDS = frozenset(
        [
            "set_freq",
            "set_mode",
            "set_filter",
            "ptt",
            "set_power",
            "set_rf_gain",
            "set_af_level",
            "set_att",
            "set_preamp",
            "select_vfo",
            "vfo_swap",
            "vfo_equalize",
        ]
    )

    def __init__(
        self,
        ws: WebSocketConnection,
        radio: "IcomRadio | None",
        server_version: str,
        radio_model: str,
    ) -> None:
        self._ws = ws
        self._radio = radio
        self._version = server_version
        self._radio_model = radio_model
        self._subscribed_streams: set[str] = set()

    async def run(self) -> None:
        """Run the control channel lifecycle."""
        await self._send_hello()
        state_task: asyncio.Task[None] = asyncio.create_task(self._state_poll_loop())
        try:
            while True:
                opcode, payload = await self._ws.recv()
                if opcode == WS_OP_TEXT:
                    await self._handle_text(payload.decode("utf-8"))
        except EOFError:
            pass
        finally:
            state_task.cancel()
            try:
                await state_task
            except asyncio.CancelledError:
                pass

    async def _state_poll_loop(self) -> None:
        """Poll state_cache every 300ms and push freq/mode/ptt changes."""
        prev_freq: int = 0
        prev_mode: str = ""
        prev_filter: str = ""
        prev_ptt: bool = False
        try:
            while True:
                await asyncio.sleep(0.3)
                if self._radio is None or "state" not in self._subscribed_streams:
                    continue
                try:
                    cache = self._radio.state_cache
                    events: list[dict[str, Any]] = []
                    freq = cache.freq if cache.freq_ts > 0 else 0
                    if freq and freq != prev_freq:
                        prev_freq = freq
                        events.append({"type": "event", "name": "freq_changed",
                            "data": {"freq": freq, "vfo": "A"}})
                    mode = cache.mode if cache.mode_ts > 0 else ""
                    filt = f"FIL{cache.filter_width}" if cache.filter_width else ""
                    if mode and (mode != prev_mode or filt != prev_filter):
                        prev_mode = mode
                        prev_filter = filt
                        events.append({"type": "event", "name": "mode_changed",
                            "data": {"mode": mode, "filter": filt}})
                    ptt = cache.ptt
                    if ptt != prev_ptt:
                        prev_ptt = ptt
                        events.append({"type": "event", "name": "ptt",
                            "data": {"state": ptt}})
                    for ev in events:
                        await self._send_json(ev)
                except Exception as exc:
                    logger.debug("state poll error: %s", exc)
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
            # Try soft reconnect (CI-V only) if control transport alive,
            # otherwise full connect.
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
            # Broadcast state to all clients
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
        # Send state snapshot after subscribe
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
        if self._radio is not None:
            # Read from state cache first — non-blocking, always fast.
            cache_hit_freq = False
            cache_hit_mode = False
            try:
                cache = self._radio.state_cache
                if cache.freq_ts > 0.0:
                    data["freq_a"] = cache.freq
                    cache_hit_freq = True
                if cache.mode_ts > 0.0:
                    data["mode"] = cache.mode
                    if cache.filter_width is not None:
                        data["filter"] = f"FIL{cache.filter_width}"
                    cache_hit_mode = True
                data["ptt"] = cache.ptt
            except Exception as exc:
                logger.debug("control: state cache read failed: %s", exc)

            # Supplement with live queries for fields not yet in cache.
            if not cache_hit_freq or not cache_hit_mode:
                try:
                    if not cache_hit_freq:
                        data["freq_a"] = await self._radio.get_frequency()
                    if not cache_hit_mode:
                        data["mode"] = (await self._radio.get_mode()).name
                        fil = await self._radio.get_filter()
                        if fil is not None:
                            data["filter"] = f"FIL{fil}"
                except Exception as exc:
                    logger.debug("control: state snapshot partial failure: %s", exc)
        msg = {"type": "state", "data": data}
        await self._ws.send_text(encode_json(msg))

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
            result = await self._dispatch_command(name, params)
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

    async def _dispatch_command(
        self, name: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        radio = self._radio
        assert radio is not None

        if name == "set_freq":
            freq = int(params["freq"])
            await radio.set_frequency(freq)
            result: dict[str, Any] = {"freq": freq}
            try:
                fil = await radio.get_filter()
            except Exception as exc:
                logger.debug("control: set_freq filter read failed: %s", exc)
            else:
                if fil is not None:
                    result["filter"] = f"FIL{fil}"
            return result

        if name == "set_mode":
            mode = str(params["mode"])
            await radio.set_mode(mode)
            return {"mode": mode}

        if name == "set_filter":
            fil_str = str(params.get("filter", "FIL1"))
            fil_num = int(fil_str[-1]) if fil_str[-1].isdigit() else 1
            await radio.set_filter(fil_num)
            return {"filter": fil_str}

        if name == "ptt":
            state = bool(params["state"])
            await radio.set_ptt(state)
            return {"state": state}

        if name == "set_power":
            level = int(params["level"])
            await radio.set_power(level)
            return {"level": level}

        if name == "set_rf_gain":
            level = int(params["level"])
            await radio.set_rf_gain(level)
            return {"level": level}

        if name == "set_af_level":
            level = int(params["level"])
            await radio.set_af_level(level)
            return {"level": level}

        if name == "set_att":
            db = int(params["db"])
            await radio.set_attenuator_level(db)
            return {"db": db}

        if name == "set_preamp":
            level = int(params["level"])
            await radio.set_preamp(level)
            return {"level": level}

        if name == "select_vfo":
            vfo = str(params.get("vfo", "A"))
            await radio.select_vfo(vfo)
            return {"vfo": vfo}

        if name == "vfo_swap":
            await radio.vfo_swap()
            return {}

        if name == "vfo_equalize":
            await radio.vfo_a_equals_b()
            return {}

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
        radio: "IcomRadio | None",
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

    Receives meter frames from the server's shared MeterPoller and forwards
    them to the client. Implements backpressure: drops frames when queue
    exceeds HIGH_WATERMARK.

    Args:
        ws: Established WebSocket connection.
        radio: IcomRadio instance (may be None).
        poll_interval: Hint for server poll rate (default 0.1 = 10fps).
        server: WebServer instance for shared polling (optional).
    """

    def __init__(
        self,
        ws: WebSocketConnection,
        radio: "IcomRadio | None",
        poll_interval: float = 0.1,
        server: Any = None,
    ) -> None:
        self._ws = ws
        self._radio = radio
        self._poll_interval = poll_interval
        self._server = server
        self._seq: int = 0
        self._active = False
        self._requested_meters: list[str] = []
        self._frame_queue: asyncio.Queue[bytes] = asyncio.Queue(
            maxsize=HIGH_WATERMARK * 2
        )

    @property
    def poll_interval(self) -> float:
        """Requested poll interval in seconds."""
        return self._poll_interval

    @property
    def requested_meters(self) -> list[str]:
        """Meter names requested by the client."""
        return list(self._requested_meters)

    async def run(self) -> None:
        """Run the meters channel lifecycle.

        Reads JSON control messages (meters_start/stop). On meters_start,
        registers with the server's shared MeterPoller so CI-V is polled
        once for all connected clients.
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
                    self._requested_meters = msg.get("meters", [])
                    fps = float(msg.get("fps", 10))
                    self._poll_interval = max(0.02, 1.0 / fps) if fps > 0 else 0.1
                    self._active = True
                    if self._server is not None:
                        await self._server.ensure_meters_enabled(self)
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
        radio: "IcomRadio | None",
    ) -> None:
        self._ws = ws
        self._radio = radio
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
        """Start receiving audio from the radio."""
        if not self._radio:
            return
        # Always stop first — previous handler may have left stream active
        try:
            await self._radio.stop_audio_rx_opus()
        except Exception:
            pass
        self._rx_active = True
        logger.info("audio: starting RX stream")

        # Determine web-frame codec and format from the radio's audio configuration.
        # Default to PCM16 mono at 48 kHz — the radio's default codec.
        _web_codec: int = AUDIO_CODEC_PCM16
        _sample_rate: int = 48000
        _channels: int = 1
        _codec = getattr(self._radio, "audio_codec", None)
        if isinstance(_codec, AudioCodec):
            if _codec in (AudioCodec.OPUS_1CH, AudioCodec.OPUS_2CH):
                _web_codec = AUDIO_CODEC_OPUS
            if _codec in (
                AudioCodec.PCM_2CH_8BIT,
                AudioCodec.PCM_2CH_16BIT,
                AudioCodec.ULAW_2CH,
                AudioCodec.OPUS_2CH,
            ):
                _channels = 2
        _sr = getattr(self._radio, "audio_sample_rate", None)
        if isinstance(_sr, int) and not isinstance(_sr, bool) and _sr > 0:
            _sample_rate = _sr
        logger.info(
            "audio: RX codec=0x%02x sample_rate=%d channels=%d",
            _web_codec, _sample_rate, _channels,
        )

        def _on_packet(pkt: Any) -> None:
            if pkt is None:
                return
            if self._seq < 3 or self._seq % 500 == 0:
                logger.info(
                    "audio: rx packet #%d, web_codec=0x%02x, data=%d bytes",
                    self._seq, _web_codec, len(pkt.data),
                )
            frame = encode_audio_frame(
                MSG_TYPE_AUDIO_RX,
                _web_codec,
                self._seq,
                _sample_rate // 100,
                _channels,
                20,   # advisory frame_ms for header
                pkt.data,
            )
            self._seq = (self._seq + 1) & 0xFFFF
            try:
                self._frame_queue.put_nowait(frame)
            except asyncio.QueueFull:
                # Drop oldest, enqueue newest (backpressure)
                try:
                    self._frame_queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
                try:
                    self._frame_queue.put_nowait(frame)
                except asyncio.QueueFull:
                    pass

        try:
            await self._radio.start_audio_rx_opus(_on_packet)
        except Exception:
            logger.exception("audio: failed to start RX")
            self._rx_active = False

    async def _stop_rx(self) -> None:
        """Stop receiving audio from the radio."""
        if not self._rx_active or not self._radio:
            return
        self._rx_active = False
        try:
            await self._radio.stop_audio_rx_opus()
        except Exception:
            logger.debug("audio: stop RX error (ignored)", exc_info=True)

    async def _handle_tx_audio(self, payload: bytes) -> None:
        """Forward TX audio from browser to radio."""
        if not self._tx_active or not self._radio:
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
