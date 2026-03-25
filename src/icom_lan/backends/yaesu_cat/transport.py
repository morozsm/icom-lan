"""Yaesu CAT serial transport — async line protocol with semicolon terminator.

Minimal async transport for Yaesu CAT protocol:
- ASCII text commands/responses
- Semicolon-terminated (`;`)
- Optional echo handling (radio may echo request before response)
- Timeouts for read operations
- Debug logging for hardware bring-up
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from serial_asyncio import SerialTransport  # type: ignore[import-not-found]

__all__ = ["YaesuCatTransport", "CatTransportError", "CatTimeoutError"]

logger = logging.getLogger(__name__)

_DEPENDENCY_HINT = (
    "Yaesu CAT serial backend requires optional dependencies pyserial and "
    "pyserial-asyncio. Install with: pip install icom-lan[serial]"
)


class CatTransportError(Exception):
    """Base error for CAT transport failures."""


class CatTimeoutError(CatTransportError):
    """Raised when read operation times out."""


class YaesuCatTransport:
    """Async serial transport for Yaesu CAT protocol.
    
    Usage::
        
        transport = YaesuCatTransport(device="/dev/cu.usbserial-01AE340D0", baudrate=38400)
        await transport.connect()
        
        response = await transport.query("FA;")  # Query freq
        print(f"Response: {response}")
        
        await transport.write("FA014074000;")  # Set freq
        
        await transport.close()
    
    Features:
    - Line-based readline (until `;` terminator)
    - Optional echo suppression (radio echoes request before response)
    - Configurable timeouts
    - Debug logging (TX/RX lines for hardware troubleshooting)
    """

    def __init__(
        self,
        *,
        device: str,
        baudrate: int = 38400,
        timeout: float = 1.0,
        echo_suppression: bool = True,
        debug_logging: bool = False,
    ) -> None:
        """Initialize CAT transport.
        
        Args:
            device: Serial port device path (e.g., "/dev/cu.usbserial-...")
            baudrate: Baud rate (default: 38400 for FTX-1)
            timeout: Read timeout in seconds (default: 1.0)
            echo_suppression: If True, ignore first line matching request (default: True)
            debug_logging: If True, log every TX/RX line at DEBUG level (default: False)
        """
        self._device = device
        self._baudrate = baudrate
        self._timeout = timeout
        self._echo_suppression = echo_suppression
        self._debug_logging = debug_logging
        
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._connected = False

    @property
    def connected(self) -> bool:
        """Whether transport is connected."""
        return self._connected

    async def connect(self) -> None:
        """Open serial connection."""
        if self._connected:
            return
        
        try:
            # Lazy import to avoid import error when serial deps not installed
            import serial_asyncio  # type: ignore[import-not-found]
        except ImportError as exc:
            raise CatTransportError(_DEPENDENCY_HINT) from exc
        
        logger.info(
            f"Opening CAT serial port: {self._device} @ {self._baudrate} baud"
        )
        
        try:
            self._reader, self._writer = await serial_asyncio.open_serial_connection(
                url=self._device,
                baudrate=self._baudrate,
                bytesize=8,
                parity="N",
                stopbits=1,
            )
            self._connected = True
            logger.info(f"CAT serial port opened: {self._device}")
        except Exception as exc:
            raise CatTransportError(
                f"Failed to open serial port {self._device}: {exc}"
            ) from exc

    async def close(self) -> None:
        """Close serial connection."""
        if not self._connected:
            return
        
        logger.info(f"Closing CAT serial port: {self._device}")
        
        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()
        
        self._reader = None
        self._writer = None
        self._connected = False
        logger.info(f"CAT serial port closed: {self._device}")

    async def write(self, command: str) -> None:
        """Write command to radio (no response expected).
        
        Args:
            command: CAT command string (e.g., "TX1;")
        
        Raises:
            CatTransportError: If not connected or write fails
        """
        if not self._connected or not self._writer:
            raise CatTransportError("Transport not connected")
        
        if not command.endswith(";"):
            command += ";"
        
        if self._debug_logging:
            logger.debug(f"CAT TX: {command!r}")
        
        try:
            self._writer.write(command.encode("ascii"))
            await self._writer.drain()
        except Exception as exc:
            raise CatTransportError(f"Write failed: {exc}") from exc

    async def readline(self, *, timeout: float | None = None) -> str:
        """Read one line (until `;` terminator).
        
        Args:
            timeout: Read timeout in seconds (default: instance timeout)
        
        Returns:
            Response line (with trailing `;` stripped)
        
        Raises:
            CatTimeoutError: If read times out
            CatTransportError: If not connected or read fails
        """
        if not self._connected or not self._reader:
            raise CatTransportError("Transport not connected")
        
        if timeout is None:
            timeout = self._timeout
        
        try:
            # Read until `;` terminator
            line_bytes = await asyncio.wait_for(
                self._reader.readuntil(b";"),
                timeout=timeout,
            )
            line = line_bytes.decode("ascii").rstrip(";")
            
            if self._debug_logging:
                logger.debug(f"CAT RX: {line!r}")
            
            return line
        except asyncio.TimeoutError as exc:
            raise CatTimeoutError(
                f"Read timeout ({timeout}s) waiting for ';' terminator"
            ) from exc
        except Exception as exc:
            raise CatTransportError(f"Read failed: {exc}") from exc

    async def query(self, command: str, *, timeout: float | None = None) -> str:
        """Send command and read response.
        
        Args:
            command: CAT command string (e.g., "FA;")
            timeout: Read timeout in seconds (default: instance timeout)
        
        Returns:
            Response line (with trailing `;` stripped)
        
        Raises:
            CatTimeoutError: If read times out
            CatTransportError: If not connected or operation fails
        """
        await self.write(command)
        
        # Read first line
        response = await self.readline(timeout=timeout)
        
        # If echo suppression enabled and response matches request, read again
        if self._echo_suppression and response == command.rstrip(";"):
            if self._debug_logging:
                logger.debug(f"CAT: echo detected, reading actual response")
            response = await self.readline(timeout=timeout)
        
        return response

    async def __aenter__(self) -> "YaesuCatTransport":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:  # type: ignore[no-untyped-def]
        await self.close()
