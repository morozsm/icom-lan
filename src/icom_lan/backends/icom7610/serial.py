"""Serial adaptation layer for the IC-7610 backend."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING

from ..._connection_state import RadioConnectionState
from ...exceptions import ConnectionError
from ...radio import Icom7610CoreRadio
from .drivers.serial_civ_link import SerialCivLink
from .drivers.serial_session import SerialSessionDriver

if TYPE_CHECKING:
    from ...profiles import RadioProfile

logger = logging.getLogger(__name__)


class Icom7610SerialRadio(Icom7610CoreRadio):
    """IC-7610 backend wired to shared core over serial CI-V session driver."""

    _SERIAL_WATCHDOG_INTERVAL_S = 0.2
    _SERIAL_WATCHDOG_RETRY_S = 0.5

    def __init__(
        self,
        *,
        device: str,
        baudrate: int = 115200,
        radio_addr: int | None = None,
        timeout: float = 5.0,
        profile: "RadioProfile | str | None" = None,
        model: str | None = None,
        civ_link: SerialCivLink | None = None,
        session_driver: SerialSessionDriver | None = None,
    ) -> None:
        if session_driver is not None and civ_link is not None:
            raise ValueError("Provide either civ_link or session_driver, not both.")
        super().__init__(
            host=device,
            port=0,
            username="",
            password="",
            radio_addr=radio_addr,
            timeout=timeout,
            profile=profile,
            model=model,
        )
        self._serial_device = device
        self._serial_baudrate = baudrate
        serial_link = civ_link or SerialCivLink(device=device, baudrate=baudrate)
        self._serial_session = session_driver or SerialSessionDriver(serial_link)

    @property
    def connected(self) -> bool:
        if self._conn_state != RadioConnectionState.CONNECTED:
            return False
        if self._civ_transport is None:
            return False
        return self._serial_session.connected

    @property
    def control_connected(self) -> bool:
        return self._serial_session.connected

    @property
    def radio_ready(self) -> bool:
        if not self.connected:
            return False
        if self._civ_recovering or not self._civ_stream_ready:
            return False
        return self._serial_session.ready

    async def connect(self) -> None:
        if self.connected:
            return

        self._conn_state = RadioConnectionState.CONNECTING
        self._civ_stream_ready = False
        self._civ_recovering = False
        self._last_status_error = 0
        self._last_status_disconnected = False
        try:
            await self._serial_session.connect()
        except Exception as exc:
            self._conn_state = RadioConnectionState.DISCONNECTED
            self._civ_stream_ready = False
            self._civ_recovering = False
            raise ConnectionError(
                f"Failed to connect serial session on {self._serial_device}: {exc}"
            ) from exc

        self._ctrl_transport = self._serial_session.control_transport
        self._civ_transport = self._serial_session.civ_transport
        self._advance_civ_generation("serial-connect")
        self._civ_last_waiter_gc_monotonic = time.monotonic()
        self._last_civ_data_received = time.monotonic()
        self._start_civ_rx_pump()
        self._start_civ_data_watchdog()
        self._start_civ_worker()

        self._conn_state = RadioConnectionState.CONNECTED
        self._civ_stream_ready = self._serial_session.ready
        self._civ_recovering = not self._civ_stream_ready
        logger.info(
            "Connected to %s over serial (%s @ %d baud)",
            self.model,
            self._serial_device,
            self._serial_baudrate,
        )

    async def soft_disconnect(self) -> None:
        await self.disconnect()

    async def disconnect(self) -> None:
        # Always stop watchdog first to avoid orphan retry loops on failed reconnects.
        await self._stop_civ_data_watchdog()
        if (
            self._conn_state != RadioConnectionState.CONNECTED
            and not self._serial_session.connected
        ):
            self._conn_state = RadioConnectionState.DISCONNECTED
            self._civ_stream_ready = False
            self._civ_recovering = False
            return
        if self._conn_state != RadioConnectionState.CONNECTED:
            await self._stop_civ_worker()
            await self._stop_civ_rx_pump()
            await self._serial_session.disconnect()
            self._ctrl_transport = self._serial_session.control_transport
            self._civ_transport = None
            self._conn_state = RadioConnectionState.DISCONNECTED
            self._civ_stream_ready = False
            self._civ_recovering = False
            return
        await super().disconnect()
        await self._serial_session.disconnect()
        self._ctrl_transport = self._serial_session.control_transport

    async def soft_reconnect(self) -> None:
        if self._serial_session.ready and self._civ_transport is not None:
            return

        self._conn_state = RadioConnectionState.RECONNECTING
        self._civ_stream_ready = False
        self._civ_recovering = True
        self._advance_civ_generation("serial-soft-reconnect")
        await self._stop_civ_worker()
        await self._stop_civ_rx_pump()
        await self._serial_session.disconnect()

        try:
            await self._serial_session.connect()
        except Exception as exc:
            # Keep recovery state so watchdog can continue retries.
            self._conn_state = RadioConnectionState.RECONNECTING
            self._civ_stream_ready = False
            self._civ_recovering = True
            raise ConnectionError(
                f"Failed to reconnect serial session on {self._serial_device}: {exc}"
            ) from exc

        self._ctrl_transport = self._serial_session.control_transport
        self._civ_transport = self._serial_session.civ_transport
        self._civ_last_waiter_gc_monotonic = time.monotonic()
        self._last_civ_data_received = time.monotonic()
        self._start_civ_rx_pump()
        self._start_civ_worker()

        self._conn_state = RadioConnectionState.CONNECTED
        self._civ_stream_ready = self._serial_session.ready
        self._civ_recovering = not self._civ_stream_ready
        if self._on_reconnect is not None:
            try:
                self._on_reconnect()
            except Exception:
                logger.debug(
                    "serial soft_reconnect: _on_reconnect callback failed",
                    exc_info=True,
                )

    async def _send_open_close(self, *, open_stream: bool) -> None:
        _ = open_stream
        return None

    async def _send_token(self, magic: int) -> None:
        _ = magic
        return None

    def _start_civ_data_watchdog(self) -> None:
        if (
            getattr(self, "_civ_data_watchdog_task", None) is not None
            and not self._civ_data_watchdog_task.done()
        ):
            return
        self._civ_data_watchdog_task = asyncio.create_task(
            self._serial_civ_watchdog_loop(),
            name="serial-civ-watchdog",
        )

    async def _stop_civ_data_watchdog(self) -> None:
        task = getattr(self, "_civ_data_watchdog_task", None)
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._civ_data_watchdog_task = None

    async def _serial_civ_watchdog_loop(self) -> None:
        try:
            while True:
                await asyncio.sleep(self._SERIAL_WATCHDOG_INTERVAL_S)
                if self._conn_state not in (
                    RadioConnectionState.CONNECTED,
                    RadioConnectionState.RECONNECTING,
                ):
                    continue
                if self._serial_session.ready:
                    self._civ_stream_ready = True
                    self._civ_recovering = False
                    self._conn_state = RadioConnectionState.CONNECTED
                    self._last_civ_data_received = time.monotonic()
                    continue

                self._civ_stream_ready = False
                self._civ_recovering = True
                try:
                    await self.soft_reconnect()
                except Exception:
                    logger.warning(
                        "serial-civ-watchdog: soft reconnect failed",
                        exc_info=True,
                    )
                    await asyncio.sleep(self._SERIAL_WATCHDOG_RETRY_S)
        except asyncio.CancelledError:
            pass


__all__ = ["Icom7610SerialRadio"]
