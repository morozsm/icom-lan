"""IcomRadio — high-level async API for Icom transceivers over LAN.

Usage::

    async with IcomRadio("192.168.1.100") as radio:
        freq = await radio.get_frequency()
        print(f"Freq: {freq / 1e6:.3f} MHz")
        await radio.set_frequency(7_074_000)
        await radio.set_mode("USB")
"""

import asyncio
import logging
import struct

from .auth import build_login_packet, parse_auth_response
from .commands import (
    CONTROLLER_ADDR,
    IC_7610_ADDR,
    _level_bcd_decode,
    build_civ_frame,
    get_alc,
    get_frequency,
    get_mode,
    get_power,
    get_s_meter,
    get_swr,
    parse_ack_nak,
    parse_civ_frame,
    parse_frequency_response,
    parse_meter_response,
    parse_mode_response,
    ptt_off,
    ptt_on,
    set_frequency,
    set_mode,
    set_power,
)
from .exceptions import (
    AuthenticationError,
    CommandError,
    ConnectionError,
    TimeoutError,
)
from .transport import ConnectionState, IcomTransport
from .types import CivFrame, Mode, PacketType

__all__ = ["IcomRadio"]

logger = logging.getLogger(__name__)


class IcomRadio:
    """High-level async interface for controlling an Icom transceiver over LAN.

    Args:
        host: Radio IP address or hostname.
        port: Radio control port.
        username: Authentication username.
        password: Authentication password.
        radio_addr: CI-V address of the radio (0x98 for IC-7610).
        timeout: Default timeout for operations in seconds.

    Example::

        async with IcomRadio("192.168.1.100") as radio:
            freq = await radio.get_frequency()
            await radio.set_frequency(7_074_000)
    """

    def __init__(
        self,
        host: str,
        port: int = 50001,
        username: str = "",
        password: str = "",
        radio_addr: int = IC_7610_ADDR,
        timeout: float = 5.0,
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._radio_addr = radio_addr
        self._timeout = timeout
        self._transport = IcomTransport()
        self._connected = False
        self._token: int = 0

    @property
    def connected(self) -> bool:
        """Whether the radio is currently connected."""
        return self._connected

    async def connect(self) -> None:
        """Open connection to the radio and authenticate.

        Raises:
            ConnectionError: If UDP connection fails.
            AuthenticationError: If login is rejected.
            TimeoutError: If the radio doesn't respond.
        """
        try:
            await self._transport.connect(self._host, self._port)
        except OSError as exc:
            raise ConnectionError(
                f"Failed to connect to {self._host}:{self._port}: {exc}"
            ) from exc

        self._transport.start_ping_loop()
        self._transport.start_retransmit_loop()

        # Send login packet
        login_pkt = build_login_packet(
            self._username,
            self._password,
            sender_id=self._transport.my_id,
            receiver_id=self._transport.remote_id,
        )
        await self._transport.send_tracked(login_pkt)

        # Wait for auth response
        try:
            resp_data = await self._transport.receive_packet(timeout=self._timeout)
        except asyncio.TimeoutError:
            raise TimeoutError("Login response timed out")

        auth = parse_auth_response(resp_data)
        if not auth.success:
            raise AuthenticationError(
                f"Authentication failed (error=0x{auth.error:08X})"
            )

        self._token = auth.token
        self._connected = True
        self._transport.state = ConnectionState.CONNECTED
        logger.info("Connected to %s:%d", self._host, self._port)

    async def disconnect(self) -> None:
        """Cleanly disconnect from the radio."""
        if self._connected:
            self._connected = False
            await self._transport.disconnect()
            logger.info("Disconnected from %s:%d", self._host, self._port)

    async def __aenter__(self) -> "IcomRadio":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:  # type: ignore[no-untyped-def]
        await self.disconnect()

    def _check_connected(self) -> None:
        """Raise ConnectionError if not connected."""
        if not self._connected:
            raise ConnectionError("Not connected to radio")

    async def _send_civ_raw(self, civ_frame: bytes) -> CivFrame:
        """Send a CI-V frame and wait for the response.

        Args:
            civ_frame: Raw CI-V frame bytes.

        Returns:
            Parsed response CivFrame.

        Raises:
            TimeoutError: If no response within timeout.
        """
        # Wrap CI-V in UDP data packet
        total_len = 0x15 + len(civ_frame)
        pkt = bytearray(total_len)
        struct.pack_into("<I", pkt, 0, total_len)
        struct.pack_into("<H", pkt, 4, PacketType.DATA)
        struct.pack_into("<I", pkt, 8, self._transport.my_id)
        struct.pack_into("<I", pkt, 0x0C, self._transport.remote_id)
        pkt[0x10] = 0x00
        struct.pack_into("<H", pkt, 0x11, len(civ_frame))
        struct.pack_into("<H", pkt, 0x13, 0)
        pkt[0x15:] = civ_frame

        await self._transport.send_tracked(bytes(pkt))

        # Wait for response
        try:
            resp = await self._transport.receive_packet(timeout=self._timeout)
        except asyncio.TimeoutError:
            raise TimeoutError("CI-V response timed out")

        # Extract CI-V from UDP data packet
        if len(resp) > 0x15:
            civ_data = resp[0x15:]
            return parse_civ_frame(civ_data)

        raise CommandError(f"Unexpected response packet (len={len(resp)})")

    async def send_civ(
        self, command: int, sub: int | None = None, data: bytes | None = None
    ) -> CivFrame:
        """Send a CI-V command and return the response.

        Args:
            command: CI-V command byte.
            sub: Optional sub-command byte.
            data: Optional payload data.

        Returns:
            Parsed response CivFrame.

        Raises:
            ConnectionError: If not connected.
            TimeoutError: If no response.
        """
        self._check_connected()
        frame = build_civ_frame(
            self._radio_addr, CONTROLLER_ADDR, command, sub=sub, data=data
        )
        return await self._send_civ_raw(frame)

    async def get_frequency(self) -> int:
        """Get the current operating frequency in Hz.

        Returns:
            Frequency in Hz.

        Raises:
            ConnectionError: If not connected.
            TimeoutError: If no response.
        """
        self._check_connected()
        civ = get_frequency(to_addr=self._radio_addr)
        resp = await self._send_civ_raw(civ)
        return parse_frequency_response(resp)

    async def set_frequency(self, freq_hz: int) -> None:
        """Set the operating frequency.

        Args:
            freq_hz: Frequency in Hz.

        Raises:
            ConnectionError: If not connected.
            CommandError: If the radio rejects the command.
            TimeoutError: If no response.
        """
        self._check_connected()
        civ = set_frequency(freq_hz, to_addr=self._radio_addr)
        resp = await self._send_civ_raw(civ)
        ack = parse_ack_nak(resp)
        if ack is False:
            raise CommandError(f"Radio rejected set_frequency({freq_hz})")

    async def get_mode(self) -> Mode:
        """Get the current operating mode.

        Returns:
            Current Mode enum value.
        """
        self._check_connected()
        civ = get_mode(to_addr=self._radio_addr)
        resp = await self._send_civ_raw(civ)
        mode, _ = parse_mode_response(resp)
        return mode

    async def set_mode(self, mode: Mode | str) -> None:
        """Set the operating mode.

        Args:
            mode: Mode enum or string name (e.g. "USB", "LSB").

        Raises:
            CommandError: If the radio rejects the command.
        """
        self._check_connected()
        if isinstance(mode, str):
            mode = Mode[mode]
        civ = set_mode(mode, to_addr=self._radio_addr)
        resp = await self._send_civ_raw(civ)
        ack = parse_ack_nak(resp)
        if ack is False:
            raise CommandError(f"Radio rejected set_mode({mode})")

    async def get_power(self) -> int:
        """Get the RF power level (0-255).

        Returns:
            Power level value.
        """
        self._check_connected()
        civ = get_power(to_addr=self._radio_addr)
        resp = await self._send_civ_raw(civ)
        return _level_bcd_decode(resp.data)

    async def set_power(self, level: int) -> None:
        """Set the RF power level (0-255).

        Args:
            level: Power level 0-255.
        """
        self._check_connected()
        civ = set_power(level, to_addr=self._radio_addr)
        resp = await self._send_civ_raw(civ)
        ack = parse_ack_nak(resp)
        if ack is False:
            raise CommandError(f"Radio rejected set_power({level})")

    async def get_s_meter(self) -> int:
        """Read the S-meter value (0-255).

        Returns:
            S-meter reading.
        """
        self._check_connected()
        civ = get_s_meter(to_addr=self._radio_addr)
        resp = await self._send_civ_raw(civ)
        return parse_meter_response(resp)

    async def get_swr(self) -> int:
        """Read the SWR meter value (0-255).

        Returns:
            SWR meter reading.
        """
        self._check_connected()
        civ = get_swr(to_addr=self._radio_addr)
        resp = await self._send_civ_raw(civ)
        return parse_meter_response(resp)

    async def get_alc(self) -> int:
        """Read the ALC meter value (0-255).

        Returns:
            ALC meter reading.
        """
        self._check_connected()
        civ = get_alc(to_addr=self._radio_addr)
        resp = await self._send_civ_raw(civ)
        return parse_meter_response(resp)

    async def set_ptt(self, on: bool) -> None:
        """Toggle PTT (Push-To-Talk).

        Args:
            on: True for TX, False for RX.
        """
        self._check_connected()
        civ = (
            ptt_on(to_addr=self._radio_addr)
            if on
            else ptt_off(to_addr=self._radio_addr)
        )
        resp = await self._send_civ_raw(civ)
        ack = parse_ack_nak(resp)
        if ack is False:
            raise CommandError(f"Radio rejected PTT {'on' if on else 'off'}")
