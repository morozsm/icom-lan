"""RFC 6455 WebSocket protocol implementation (stdlib only).

Provides:
- HTTP Upgrade handshake key computation
- Frame serialization (server→client, unmasked)
- Frame parsing (client→server, masked)
- WebSocketConnection class for full-duplex messaging
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import struct

__all__ = [
    "WS_MAGIC",
    "WS_OP_CONTINUATION",
    "WS_OP_TEXT",
    "WS_OP_BINARY",
    "WS_OP_CLOSE",
    "WS_OP_PING",
    "WS_OP_PONG",
    "WS_KEEPALIVE_INTERVAL",
    "WebSocketError",
    "make_accept_key",
    "make_frame",
    "WebSocketConnection",
]

WS_KEEPALIVE_INTERVAL = 20.0  # seconds between server-initiated pings

WS_MAGIC = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

WS_OP_CONTINUATION = 0x0
WS_OP_TEXT = 0x1
WS_OP_BINARY = 0x2
WS_OP_CLOSE = 0x8
WS_OP_PING = 0x9
WS_OP_PONG = 0xA


class WebSocketError(Exception):
    """Raised when a WebSocket protocol violation is detected."""


def make_accept_key(client_key: str) -> str:
    """Compute the Sec-WebSocket-Accept value from the client's key.

    Args:
        client_key: The Sec-WebSocket-Key header value (base64 string).

    Returns:
        Base64-encoded SHA-1 of (client_key + WS_MAGIC).
    """
    raw = (client_key + WS_MAGIC).encode("ascii")
    return base64.b64encode(hashlib.sha1(raw).digest()).decode("ascii")


def make_frame(opcode: int, payload: bytes, *, fin: bool = True) -> bytes:
    """Serialize a WebSocket frame (server→client, no masking).

    Args:
        opcode: Frame opcode (WS_OP_TEXT, WS_OP_BINARY, etc.).
        payload: Frame payload bytes.
        fin: Whether this is the final fragment (True for all non-fragmented frames).

    Returns:
        Serialized frame bytes.
    """
    first_byte = (0x80 if fin else 0x00) | (opcode & 0x0F)
    length = len(payload)

    if length <= 125:
        header = bytes([first_byte, length])
    elif length <= 65535:
        header = struct.pack("!BBH", first_byte, 126, length)
    else:
        header = struct.pack("!BBQ", first_byte, 127, length)

    return header + payload


async def _read_one_frame(
    reader: asyncio.StreamReader,
) -> tuple[int, bytes, bool]:
    """Read one WebSocket frame from the stream.

    Client→server frames are always masked (RFC 6455 §5.3).
    Server→client frames are never masked.

    Args:
        reader: asyncio StreamReader.

    Returns:
        Tuple of (opcode, payload, fin).

    Raises:
        WebSocketError: On protocol violation.
        asyncio.IncompleteReadError: On EOF.
    """
    header = await reader.readexactly(2)
    byte0, byte1 = header[0], header[1]

    fin = bool(byte0 & 0x80)
    # RSV1-3 must be 0 unless extensions are negotiated (we negotiate none)
    rsv = (byte0 >> 4) & 0x07
    if rsv != 0:
        raise WebSocketError(f"non-zero RSV bits: {rsv:#x}")

    opcode = byte0 & 0x0F
    masked = bool(byte1 & 0x80)
    payload_len = byte1 & 0x7F

    if payload_len == 126:
        ext = await reader.readexactly(2)
        payload_len = struct.unpack("!H", ext)[0]
    elif payload_len == 127:
        ext = await reader.readexactly(8)
        payload_len = struct.unpack("!Q", ext)[0]

    mask_key = b""
    if masked:
        mask_key = await reader.readexactly(4)

    raw = await reader.readexactly(payload_len)

    if masked:
        payload = bytes(b ^ mask_key[i % 4] for i, b in enumerate(raw))
    else:
        payload = raw

    return opcode, payload, fin


class WebSocketConnection:
    """An established WebSocket connection (post-handshake).

    Wraps asyncio StreamReader/StreamWriter and provides frame-level I/O.
    Handles fragmentation, ping/pong, and close handshake internally.

    Args:
        reader: asyncio StreamReader (post-HTTP handshake).
        writer: asyncio StreamWriter (post-HTTP handshake).
    """

    def __init__(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        self._reader = reader
        self._writer = writer
        self._closed = False
        self._fragmented_opcode: int = 0
        self._fragments: list[bytes] = []

    async def recv(self) -> tuple[int, bytes]:
        """Receive the next complete message.

        Handles fragmented frames, ping/pong internally. Raises EOFError
        on clean close or WebSocketError on protocol violation.

        Returns:
            Tuple of (opcode, payload), where opcode is WS_OP_TEXT or
            WS_OP_BINARY (never continuation or control opcodes).

        Raises:
            EOFError: When the connection is closed (cleanly or by peer).
            WebSocketError: On protocol error.
            asyncio.IncompleteReadError: On abrupt EOF.
        """
        while True:
            try:
                opcode, payload, fin = await _read_one_frame(self._reader)
            except asyncio.IncompleteReadError as exc:
                raise EOFError("connection closed") from exc

            if opcode == WS_OP_PING:
                await self._send_raw(make_frame(WS_OP_PONG, payload))
                continue

            if opcode == WS_OP_PONG:
                continue  # ignore unsolicited pong

            if opcode == WS_OP_CLOSE:
                self._closed = True
                # Echo close frame back
                if not self._writer.is_closing():
                    try:
                        self._writer.write(make_frame(WS_OP_CLOSE, payload))
                        await self._writer.drain()
                    except Exception:
                        pass
                raise EOFError("WebSocket closed")

            if opcode == WS_OP_CONTINUATION:
                if not self._fragments:
                    raise WebSocketError("unexpected continuation frame")
                self._fragments.append(payload)
                if fin:
                    data = b"".join(self._fragments)
                    op = self._fragmented_opcode
                    self._fragments = []
                    self._fragmented_opcode = 0
                    return op, data
                # More fragments coming
                continue

            # Data frame (text or binary)
            if not fin:
                # First fragment of a fragmented message
                self._fragmented_opcode = opcode
                self._fragments = [payload]
                continue

            return opcode, payload

    async def send_text(self, text: str) -> None:
        """Send a text frame.

        Args:
            text: UTF-8 string to send.
        """
        await self._send_raw(make_frame(WS_OP_TEXT, text.encode("utf-8")))

    async def send_binary(self, data: bytes) -> None:
        """Send a binary frame.

        Args:
            data: Binary data to send.
        """
        await self._send_raw(make_frame(WS_OP_BINARY, data))

    async def close(self, code: int = 1000, reason: str = "") -> None:
        """Send a WebSocket close frame.

        Args:
            code: WebSocket close status code (default 1000 = normal closure).
            reason: Optional close reason string.
        """
        if not self._closed:
            payload = struct.pack("!H", code) + reason.encode("utf-8")
            try:
                await self._send_raw(make_frame(WS_OP_CLOSE, payload))
            except Exception:
                pass
            self._closed = True

    @property
    def closed(self) -> bool:
        """True if the connection has been closed."""
        return self._closed

    async def keepalive_loop(self, interval: float = 20.0) -> None:
        """Send periodic WebSocket ping frames to detect dead connections.

        Runs until cancelled or the connection is closed. If the underlying
        TCP connection is gone, the write will fail and the exception will
        propagate, causing the task to exit silently.

        Args:
            interval: Seconds between pings (default 20s).
        """
        try:
            while not self._closed:
                await asyncio.sleep(interval)
                if not self._closed:
                    await self._send_raw(make_frame(WS_OP_PING, b"ka"))
        except asyncio.CancelledError:
            pass
        except Exception:
            pass  # Connection gone; exit quietly

    async def _send_raw(self, data: bytes) -> None:
        self._writer.write(data)
        await self._writer.drain()
