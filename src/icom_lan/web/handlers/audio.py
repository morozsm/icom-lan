"""Audio WebSocket handlers — broadcaster + per-client handler."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any, Callable, Protocol, cast

from ..._audio_buffer_pool import AudioBufferPool
from ..._audio_codecs import decode_ulaw_to_pcm16
from ..._audio_transcoder import PcmOpusTranscoder, create_pcm_opus_transcoder
from ...env_config import (
    get_audio_broadcaster_high_watermark,
    get_audio_buffer_pool_size,
    get_audio_client_high_watermark,
)
from ...types import AudioCodec
from ..protocol import (
    AUDIO_CODEC_OPUS,
    AUDIO_CODEC_PCM16,
    AUDIO_HEADER_SIZE,
    MSG_TYPE_AUDIO_RX,
    decode_json,
    encode_audio_frame,
)
from ..websocket import WS_OP_BINARY, WS_OP_TEXT, WebSocketConnection

if TYPE_CHECKING:
    from ...capabilities import CAP_AUDIO as _CAP_AUDIO_TYPE  # noqa: F401
    from ...radio_protocol import Radio

from ...capabilities import CAP_AUDIO

__all__ = ["AudioBroadcaster", "AudioHandler"]

logger = logging.getLogger(__name__)


class _AudioPacketLike(Protocol):
    data: bytes


class _AudioSubscription(Protocol):
    async def start(self) -> None: ...

    def stop(self) -> None: ...

    def __aiter__(self) -> AsyncIterator[_AudioPacketLike | None]: ...


class _AudioBus(Protocol):
    def subscribe(self, name: str = "") -> _AudioSubscription: ...


class AudioBroadcaster:
    """Single-instance RX audio broadcaster shared by all AudioHandler clients.

    Uses :class:`~icom_lan.audio_bus.AudioBus` to subscribe to the radio's
    opus RX stream.  Multiple consumers (WebSocket clients, audio bridge,
    recorders) can all share the same stream through the bus.
    """

    HIGH_WATERMARK: int = 10

    def __init__(self, radio: "Radio | None") -> None:
        self.HIGH_WATERMARK = get_audio_broadcaster_high_watermark()
        self._radio = radio
        self._clients: dict[int, asyncio.Queue[bytes]] = {}
        self._client_ws: dict[int, WebSocketConnection] = {}
        self._subscription: _AudioSubscription | None = None
        self._relay_task: asyncio.Task[None] | None = None
        self._seq: int = 0
        self._web_codec: int = AUDIO_CODEC_PCM16
        self._radio_codec: AudioCodec | None = None
        self._sample_rate: int = 48000
        self._channels: int = 1
        self._lock = asyncio.Lock()
        # PCM tap for audio FFT scope (called with decoded PCM16 bytes)
        self._pcm_tap: Callable[[bytes], None] | None = None
        # Buffer pool for audio encoding/decoding operations
        # Pre-allocates buffers for common audio frame sizes (20ms @ 16kHz stereo = 1280 bytes)
        self._buffer_pool = AudioBufferPool(buffer_size=1280, max_buffers=get_audio_buffer_pool_size(), name="audio-broadcaster")

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
            # Start relay if no active subscription, or if relay task died
            relay_alive = (
                self._relay_task is not None and not self._relay_task.done()
            )
            if self._subscription is None or not relay_alive:
                # Clean up stale subscription/task if needed
                if self._subscription is not None and not relay_alive:
                    logger.info("audio-broadcaster: relay task dead, restarting")
                    if self._relay_task is not None:
                        self._relay_task.cancel()
                        self._relay_task = None
                    self._subscription.stop()
                    self._subscription = None
                if self._radio:
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

    def set_pcm_tap(self, callback: "Callable[[bytes], None] | None") -> None:
        """Register a tap that receives decoded PCM16 audio data.

        Used by AudioFftScope to derive spectrum from audio stream.
        The callback is called synchronously in the relay loop with
        PCM16 mono/stereo bytes after any codec decoding.

        Args:
            callback: Function receiving PCM16 bytes, or None to unregister.
        """
        self._pcm_tap = callback

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
        if not self._radio or CAP_AUDIO not in self._radio.capabilities:
            return

        # Negotiate web codec from radio's actual audio codec
        _codec = getattr(self._radio, "audio_codec", None)
        if isinstance(_codec, AudioCodec):
            # Map radio codec → web transport codec
            # For ulaw codecs, we transcode to PCM16 in _relay_loop
            _CODEC_MAP = {
                AudioCodec.OPUS_1CH: AUDIO_CODEC_OPUS,
                AudioCodec.OPUS_2CH: AUDIO_CODEC_OPUS,
                AudioCodec.PCM_1CH_16BIT: AUDIO_CODEC_PCM16,
                AudioCodec.PCM_2CH_16BIT: AUDIO_CODEC_PCM16,
                AudioCodec.PCM_1CH_8BIT: AUDIO_CODEC_PCM16,  # upcast in future
                AudioCodec.PCM_2CH_8BIT: AUDIO_CODEC_PCM16,
                AudioCodec.ULAW_1CH: AUDIO_CODEC_PCM16,  # decoded in _relay_loop
                AudioCodec.ULAW_2CH: AUDIO_CODEC_PCM16,  # decoded in _relay_loop
            }
            self._web_codec = _CODEC_MAP.get(_codec, AUDIO_CODEC_PCM16)
            # Store original codec for decoding logic
            self._radio_codec = _codec
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

                # Decode audio data if needed
                audio_data = pkt.data
                if self._radio_codec in (AudioCodec.ULAW_1CH, AudioCodec.ULAW_2CH):
                    try:
                        audio_data = decode_ulaw_to_pcm16(audio_data)
                    except Exception as e:
                        logger.warning(
                            "audio: failed to decode ulaw data: %s", e
                        )
                        # Fall back to original data
                        audio_data = pkt.data

                # Tee PCM data to audio FFT scope if registered
                pcm_tap = self._pcm_tap
                if pcm_tap is not None and self._web_codec == AUDIO_CODEC_PCM16:
                    try:
                        pcm_tap(audio_data)
                    except Exception:
                        logger.debug("audio: pcm_tap error", exc_info=True)

                frame = encode_audio_frame(
                    MSG_TYPE_AUDIO_RX,
                    self._web_codec,
                    self._seq,
                    self._sample_rate // 100,
                    self._channels,
                    20,
                    audio_data,
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
        self.HIGH_WATERMARK = get_audio_client_high_watermark()
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
        """Run the audio channel lifecycle.

        Reader and sender run as concurrent tasks. When EITHER exits
        (WS close, send timeout, error), the other is cancelled and
        cleanup (unsubscribe from broadcaster) runs unconditionally.
        """
        reader = asyncio.create_task(self._reader_loop(), name="audio-reader")
        sender = asyncio.create_task(self._sender_loop(), name="audio-sender")
        try:
            # Wait for the first task to finish — then cancel the other
            done, pending = await asyncio.wait(
                {reader, sender}, return_when=asyncio.FIRST_COMPLETED
            )
            # Log which task exited first
            for task in done:
                exc = task.exception() if not task.cancelled() else None
                if exc:
                    logger.warning("audio: %s exited with error: %s", task.get_name(), exc)
                else:
                    logger.debug("audio: %s exited normally", task.get_name())
            # Cancel the remaining task and close WS to unblock any stuck recv()
            for task in pending:
                task.cancel()
            # Close WS to ensure recv() in reader raises EOF
            try:
                await self._ws.close(1001, "peer task exited")
            except Exception:
                pass
            for task in pending:
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        except Exception:
            logger.exception("audio: handler error")
            reader.cancel()
            sender.cancel()
        finally:
            self._done.set()
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
                if self._radio and CAP_AUDIO in self._radio.capabilities:
                    await self._radio.start_audio_tx_opus()
                self._tx_active = True
                logger.info("audio: TX active")
        elif msg_type == "audio_stop":
            if direction == "rx":
                await self._stop_rx()
            elif direction == "tx":
                if self._radio and CAP_AUDIO in self._radio.capabilities:
                    await self._radio.stop_audio_tx()
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
        if CAP_AUDIO not in self._radio.capabilities:
            logger.warning(
                "audio: TX frame ignored (radio missing audio capability), size=%d",
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
