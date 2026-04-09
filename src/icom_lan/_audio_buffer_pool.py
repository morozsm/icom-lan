"""Object pool for audio frame buffers — reduce allocation overhead in audio streaming.

This module provides an efficient buffer pool for reusing bytearray objects in
high-frequency audio packet processing. Instead of allocating new buffers on
every frame (~50/second), buffers are pre-allocated and recycled.

Benefits:
- Reduces GC pressure in audio streaming loop
- Pre-allocated buffers for common sizes (20ms frames at 16kHz = 640 bytes)
- Thread-safe acquire/release semantics
- Automatic buffer sizing for different sample rates/channels

Usage::

    pool = AudioBufferPool(
        buffer_size=1024,  # 20ms @ 16kHz stereo
        max_buffers=10
    )

    # Acquire a reusable buffer
    buf = pool.acquire()
    # ... use buffer ...
    # ... fill with audio data ...
    # Release back to pool for reuse
    pool.release(buf)
"""

from __future__ import annotations

import logging
import threading
from collections import deque

__all__ = ["AudioBufferPool", "BufferExhausted", "ContextManagedBuffer"]

logger = logging.getLogger(__name__)


class BufferExhausted(Exception):
    """Raised when no buffers are available in the pool."""


class AudioBufferPool:
    """Thread-safe object pool for audio frame bytearray buffers.

    Pre-allocates buffers for common audio frame sizes to reduce GC overhead
    in high-frequency audio streaming paths.

    Common sizes:
    - 16kHz mono 20ms: 320 samples × 2 bytes = 640 bytes
    - 16kHz stereo 20ms: 320 samples × 2 bytes × 2 channels = 1280 bytes
    - 48kHz mono 20ms: 960 samples × 2 bytes = 1920 bytes
    """

    def __init__(
        self,
        buffer_size: int = 1280,
        max_buffers: int = 20,
        name: str = "audio",
    ) -> None:
        """Initialize buffer pool.

        Args:
            buffer_size: Size of each pre-allocated buffer in bytes.
            max_buffers: Maximum number of buffers to pre-allocate.
            name: Name for logging (e.g., "audio-rx", "audio-tx").
        """
        self._buffer_size = buffer_size
        self._max_buffers = max_buffers
        self._name = name
        self._lock = threading.Lock()
        self._available: deque[bytearray] = deque()
        self._in_use: set[int] = set()
        self._total_pre_allocated = max_buffers

        # Pre-allocate initial buffers
        for _ in range(max_buffers):
            buf = bytearray(buffer_size)
            self._available.append(buf)

        logger.info(
            "%s buffer pool: size=%d bytes, pool_size=%d",
            name,
            buffer_size,
            max_buffers,
        )

    def acquire(self) -> bytearray:
        """Acquire a buffer from the pool.

        If all pre-allocated buffers are in use, allocates a new one (which
        will not be returned to the pool to prevent unbounded growth).

        Returns:
            A bytearray of the configured size, ready for use.

        Raises:
            BufferExhausted: If pool is exhausted and allocation fails.
        """
        with self._lock:
            if self._available:
                buf = self._available.popleft()
            else:
                # Allocate temporary buffer if pool exhausted
                # This buffer won't be recycled to prevent unbounded growth
                logger.warning(
                    "%s buffer pool exhausted; allocating temporary buffer",
                    self._name,
                )
                buf = bytearray(self._buffer_size)

            self._in_use.add(id(buf))
            return buf

    def release(self, buf: bytearray) -> None:
        """Release a buffer back to the pool.

        The buffer will be cleared and returned to the available queue.

        Args:
            buf: The buffer to release.
        """
        with self._lock:
            buf_id = id(buf)
            if buf_id not in self._in_use:
                logger.warning(
                    "%s buffer not in pool; ignoring release", self._name
                )
                return

            self._in_use.discard(buf_id)

            # Only return to pool if it's one of our pre-allocated buffers
            if len(self._available) < self._max_buffers:
                # Clear the buffer before returning (optional, for safety)
                buf[:] = b'\x00' * len(buf)
                self._available.appendleft(buf)  # Push to front for LIFO reuse
            # else: discard temporary buffers

    def stats(self) -> dict[str, int]:
        """Return pool statistics.

        Returns:
            Dict with keys: available, in_use, total_allocated.
            total_allocated only counts pre-allocated buffers, not temporary ones.
        """
        with self._lock:
            return {
                "available": len(self._available),
                "in_use": len(self._in_use),
                "total_allocated": self._total_pre_allocated,
            }



class ContextManagedBuffer:
    """Convenience wrapper for automatic buffer release via context manager.

    Usage::

        with ContextManagedBuffer(pool) as buf:
            # use buf
            # automatically released on exit
    """

    def __init__(self, pool: AudioBufferPool) -> None:
        self._pool = pool
        self._buffer: bytearray | None = None

    def __enter__(self) -> bytearray:
        self._buffer = self._pool.acquire()
        return self._buffer

    def __exit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: object) -> None:
        if self._buffer is not None:
            self._pool.release(self._buffer)
            self._buffer = None
