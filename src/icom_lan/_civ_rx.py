"""CI-V receive pump and event dispatch for IcomRadio."""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import TYPE_CHECKING

from .civ import (
    CivEvent,
    CivEventType,
    iter_civ_frames,
    request_key_from_frame,
)
from .commander import IcomCommander, Priority
from .commands import (
    CONTROLLER_ADDR,
    parse_civ_frame,
    parse_frequency_response,
    parse_mode_response,
)
from .exceptions import ConnectionError, TimeoutError
from .scope import ScopeFrame
from .types import CivFrame

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

CIV_HEADER_SIZE = 0x15

# CI-V data watchdog (wfview icomudpcivdata::watchdog)
# If no CI-V data for this long, send open_close to restart the stream.
_CIV_DATA_WATCHDOG_TIMEOUT = 2.0  # seconds (wfview: 2000ms)
_CIV_DATA_WATCHDOG_RETRY = 0.1    # retry interval (wfview: 100ms via startCivDataTimer)


class _CivRxMixin:
    """Mixin providing CI-V receive pump and command dispatch for IcomRadio."""

    # ------------------------------------------------------------------
    # Generation / stale-waiter housekeeping
    # ------------------------------------------------------------------

    def _advance_civ_generation(self, reason: str) -> None:
        """Advance CI-V request generation and fail stale waiters."""
        self._civ_epoch = self._civ_request_tracker.advance_generation(  # type: ignore[attr-defined]
            ConnectionError(f"CI-V generation advanced: {reason}")
        )

    def _cleanup_stale_civ_waiters(self) -> None:
        """Run periodic stale waiter GC on request tracker."""
        now = time.monotonic()
        if (
            now - self._civ_last_waiter_gc_monotonic  # type: ignore[attr-defined]
            < self._civ_waiter_ttl_gc_interval  # type: ignore[attr-defined]
        ):
            return
        cleaned = self._civ_request_tracker.cleanup_stale(now_monotonic=now)  # type: ignore[attr-defined]
        self._civ_last_waiter_gc_monotonic = now  # type: ignore[attr-defined]
        if cleaned:
            logger.debug("Cleaned %d stale CI-V waiter(s)", cleaned)

    # ------------------------------------------------------------------
    # RX pump lifecycle
    # ------------------------------------------------------------------

    def _start_civ_rx_pump(self) -> None:
        """Start always-on CI-V receive pump."""
        if self._civ_rx_task is None or self._civ_rx_task.done():  # type: ignore[attr-defined]
            self._civ_rx_task = asyncio.create_task(  # type: ignore[attr-defined]
                self._civ_rx_loop(self._civ_epoch)  # type: ignore[attr-defined]
            )

    async def _stop_civ_rx_pump(self) -> None:
        """Stop CI-V receive pump and fail pending request futures."""
        self._civ_request_tracker.fail_all(  # type: ignore[attr-defined]
            ConnectionError("CI-V RX pump stopped")
        )
        if (
            self._civ_rx_task is not None  # type: ignore[attr-defined]
            and not self._civ_rx_task.done()  # type: ignore[attr-defined]
        ):
            self._civ_rx_task.cancel()  # type: ignore[attr-defined]
            try:
                await self._civ_rx_task  # type: ignore[attr-defined]
            except asyncio.CancelledError:
                pass
        self._civ_rx_task = None  # type: ignore[attr-defined]

    # ------------------------------------------------------------------
    # CI-V data watchdog (wfview icomudpcivdata::watchdog)
    # ------------------------------------------------------------------

    def _start_civ_data_watchdog(self) -> None:
        """Start CI-V data watchdog task.

        Monitors incoming CI-V data. If no data arrives for
        _CIV_DATA_WATCHDOG_TIMEOUT seconds, sends sendOpenClose(open)
        repeatedly to restart the CI-V data stream from the radio.

        Reference: wfview icomudpcivdata.cpp watchdog() — checks
        lastReceived every WATCHDOG_PERIOD, starts startCivDataTimer
        (100ms) which calls sendOpenClose(false=open) until data resumes.
        """
        if (
            getattr(self, "_civ_data_watchdog_task", None) is not None
            and not self._civ_data_watchdog_task.done()  # type: ignore[attr-defined]
        ):
            return
        self._civ_data_watchdog_task = asyncio.create_task(  # type: ignore[attr-defined]
            self._civ_data_watchdog_loop(), name="civ-data-watchdog"
        )
        logger.info("civ-data-watchdog: started")

    async def _stop_civ_data_watchdog(self) -> None:
        """Stop CI-V data watchdog."""
        task = getattr(self, "_civ_data_watchdog_task", None)
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._civ_data_watchdog_task = None  # type: ignore[attr-defined]

    async def _civ_data_watchdog_loop(self) -> None:
        """Monitor CI-V data flow; recover with open_close then soft_reconnect.

        Phase 1 (wfview-style): if no CI-V data for 2s, send OpenClose(open)
        every 100ms for up to 5 seconds to restart the stream.

        Phase 2: if OpenClose doesn't help after 5s, do a full
        soft_reconnect (tear down CI-V transport and reconnect).
        """
        _OPENCLOSE_DEADLINE = 5.0  # seconds of open_close attempts before reconnect
        _MAX_RECONNECTS = 3       # max soft_reconnect attempts before giving up
        _RECONNECT_PAUSE = 15.0   # seconds between reconnect attempts (let radio release slot)
        recovering = False
        recovery_start: float = 0.0
        reconnect_count = 0
        try:
            while True:
                await asyncio.sleep(
                    _CIV_DATA_WATCHDOG_RETRY if recovering
                    else _CIV_DATA_WATCHDOG_TIMEOUT / 2
                )

                last = getattr(self, "_last_civ_data_received", None)
                if last is None:
                    continue

                idle = time.monotonic() - last
                if idle > _CIV_DATA_WATCHDOG_TIMEOUT:
                    if not recovering:
                        civ_t = getattr(self, "_civ_transport", None)
                        rx_count = civ_t.rx_packet_count if civ_t else -1
                        q_size = civ_t._packet_queue.qsize() if civ_t else -1
                        logger.warning(
                            "civ-data-watchdog: no CI-V data for %.1fs, "
                            "requesting data start "
                            "(transport rx_count=%d, queue=%d)",
                            idle, rx_count, q_size,
                        )
                        recovering = True
                        recovery_start = time.monotonic()

                    elapsed_recovery = time.monotonic() - recovery_start

                    if elapsed_recovery < _OPENCLOSE_DEADLINE:
                        # Phase 1: try OpenClose
                        try:
                            await self._send_open_close(open_stream=True)  # type: ignore[attr-defined]
                        except Exception:
                            logger.debug(
                                "civ-data-watchdog: open_close failed",
                                exc_info=True,
                            )
                    else:
                        # Phase 2: OpenClose didn't help — soft_reconnect
                        reconnect_count += 1
                        if reconnect_count > _MAX_RECONNECTS:
                            logger.error(
                                "civ-data-watchdog: %d reconnect attempts failed, "
                                "giving up (radio may need reboot)",
                                reconnect_count - 1,
                            )
                            return
                        logger.warning(
                            "civ-data-watchdog: OpenClose failed for %.1fs, "
                            "triggering soft_reconnect (%d/%d)",
                            elapsed_recovery, reconnect_count, _MAX_RECONNECTS,
                        )
                        try:
                            await self._stop_civ_data_watchdog()  # stop ourselves
                            await self.soft_disconnect()  # type: ignore[attr-defined]
                            await asyncio.sleep(_RECONNECT_PAUSE)  # let radio release slot
                            await self.soft_reconnect()  # type: ignore[attr-defined]
                        except Exception:
                            logger.error(
                                "civ-data-watchdog: soft_reconnect failed",
                                exc_info=True,
                            )
                        return  # watchdog restarted by soft_reconnect
                else:
                    if recovering:
                        logger.info("civ-data-watchdog: CI-V data resumed")
                        recovering = False
        except asyncio.CancelledError:
            pass

    def _ensure_civ_runtime(self) -> None:
        """Ensure CI-V transport exists (tests may bypass connect()).

        Note: we intentionally do NOT start the CI-V RX pump here.
        The RX pump should be started explicitly (connect() or right before
        sending) to avoid races with tests that pre-queue mock packets.
        """
        if self._civ_transport is None:  # type: ignore[attr-defined]
            raise ConnectionError("Not connected to radio")

    # ------------------------------------------------------------------
    # CI-V RX loop + routing
    # ------------------------------------------------------------------

    async def _civ_rx_loop(self, generation: int) -> None:
        """Continuously consume CI-V transport packets and route events.

        Drains ALL pending packets from the transport queue each iteration
        (wfview-style) to prevent scope flood from starving CI-V command
        responses.  See issue #66.
        """
        assert self._civ_transport is not None  # type: ignore[attr-defined]
        self._last_civ_data_received = time.monotonic()  # type: ignore[attr-defined]
        try:
            while self._civ_transport is not None:  # type: ignore[attr-defined]
                # Wait for at least one packet.
                try:
                    packet = await self._civ_transport.receive_packet(timeout=0.2)  # type: ignore[attr-defined]
                except asyncio.TimeoutError:
                    self._cleanup_stale_civ_waiters()
                    continue

                # Drain ALL pending packets from the queue (non-blocking).
                # This is critical: scope floods ~225 pkt/sec on the CI-V port.
                # Processing one-at-a-time causes ACK/response packets to wait
                # behind hundreds of scope packets, causing GET timeouts.
                packets = [packet]
                queue = getattr(self._civ_transport, "_packet_queue", None)  # type: ignore[attr-defined]
                if queue is not None:
                    while not queue.empty():
                        try:
                            packets.append(queue.get_nowait())
                        except asyncio.QueueEmpty:
                            break

                # Mark that we received CI-V data (for watchdog)
                self._last_civ_data_received = time.monotonic()  # type: ignore[attr-defined]

                # Process all collected packets.
                for pkt in packets:
                    if len(pkt) <= CIV_HEADER_SIZE:
                        continue
                    payload = pkt[CIV_HEADER_SIZE:]
                    for frame_bytes in iter_civ_frames(payload):
                        try:
                            frame = parse_civ_frame(frame_bytes)
                        except ValueError:
                            continue
                        try:
                            await self._route_civ_frame(frame, generation=generation)
                        except Exception:
                            logger.exception(
                                "Unhandled exception while routing CI-V frame"
                            )
                self._cleanup_stale_civ_waiters()
        except asyncio.CancelledError:
            pass

    async def _route_civ_frame(self, frame: CivFrame, *, generation: int) -> None:
        """Route one parsed CI-V frame into command/scope event paths."""
        if frame.from_addr != self._radio_addr:  # type: ignore[attr-defined]
            return
        # Accept frames addressed to us (0xE0) OR broadcast (0x00).
        # Unsolicited changes (knob turns) go to 0x00.
        if frame.to_addr not in (CONTROLLER_ADDR, 0x00):
            return
        # Log non-scope frames for debugging
        if frame.command != 0x27:
            logger.info("civ-rx: frame cmd=0x%02X sub=0x%02X to=0x%02X data=%d",
                        frame.command, frame.sub or 0, frame.to_addr, len(frame.data))

        if frame.command == 0x27 and frame.sub == 0x00 and len(frame.data) >= 3:
            receiver = frame.data[0]
            self._scope_activity_counter += 1  # type: ignore[attr-defined]
            self._scope_activity_event.set()  # type: ignore[attr-defined]
            self._publish_civ_event(
                CivEvent(
                    type=CivEventType.SCOPE_CHUNK,
                    frame=frame,
                    receiver=receiver,
                )
            )
            scope_frame = self._scope_assembler.feed(frame.data[1:], receiver)  # type: ignore[attr-defined]
            if scope_frame is not None:
                self._publish_scope_frame(scope_frame)
            return

        if frame.command == 0xFB:
            event = CivEvent(type=CivEventType.ACK, frame=frame)
        elif frame.command == 0xFA:
            event = CivEvent(type=CivEventType.NAK, frame=frame)
        else:
            event = CivEvent(type=CivEventType.RESPONSE, frame=frame)
            # Update state cache for all RESPONSE frames (solicited and unsolicited).
            self._update_state_cache_from_frame(frame)

        self._publish_civ_event(event)
        self._civ_request_tracker.resolve(event, generation=generation)  # type: ignore[attr-defined]

    def _update_state_cache_from_frame(self, frame: CivFrame) -> None:
        """Best-effort update of state cache from an incoming CI-V frame.

        Called for every data RESPONSE event (both solicited query responses
        and unsolicited frames sent by the radio on knob turns, mode changes,
        etc.).  This is the ONLY place state gets updated from the radio.

        The _on_state_change callback notifies the server so it can broadcast
        events to WebSocket clients.
        """
        cache = self._state_cache  # type: ignore[attr-defined]
        try:
            if frame.command in (0x03, 0x00):  # frequency (response / unsolicited)
                freq = parse_frequency_response(frame)
                old = cache.freq
                logger.info("civ-rx: freq=%d (cmd=0x%02X to=0x%02X) old=%d", freq, frame.command, frame.to_addr, old)
                self._last_freq_hz = freq  # type: ignore[attr-defined]
                cache.update_freq(freq)
                if freq != old:
                    self._notify_change("freq_changed", {"freq": freq, "vfo": "A"})
            elif frame.command in (0x04, 0x01):  # mode (response / unsolicited)
                mode, filt = parse_mode_response(frame)
                old_mode, old_filt = cache.mode, cache.filter_width
                self._last_mode = mode  # type: ignore[attr-defined]
                if filt is not None:
                    self._filter_width = filt  # type: ignore[attr-defined]
                cache.update_mode(mode.name, filt)
                if mode.name != old_mode or filt != old_filt:
                    filt_str = f"FIL{filt}" if filt else ""
                    self._notify_change("mode_changed", {"mode": mode.name, "filter": filt_str})
            elif frame.command == 0x15:  # meter readings
                if len(frame.data) >= 2:
                    sub = frame.sub
                    # IC-7610 meters are BCD-encoded (0x0137 = 137, not 311)
                    b0, b1 = frame.data[0], frame.data[1]
                    raw = (b0 >> 4) * 1000 + (b0 & 0x0F) * 100 + (b1 >> 4) * 10 + (b1 & 0x0F)
                    if sub == 0x02:  # S-meter
                        cache.update_s_meter(raw)
                        self._notify_change("meter", {"type": "smeter", "value": raw})
                    elif sub == 0x11:  # RF power
                        cache.update_rf_power(raw / 255.0)
                        self._notify_change("meter", {"type": "power", "value": raw})
                    elif sub == 0x12:  # SWR
                        cache.update_swr(float(raw))
                        self._notify_change("meter", {"type": "swr", "value": raw})
                    elif sub == 0x13:  # ALC
                        cache.update_alc(float(raw))
                        self._notify_change("meter", {"type": "alc", "value": raw})
            elif frame.command == 0x14:  # levels
                if len(frame.data) >= 2:
                    raw = int.from_bytes(frame.data[:2], "big")
                    if frame.sub == 0x02:  # RF gain
                        cache.update_rf_gain(float(raw))
                    elif frame.sub == 0x01:  # AF level
                        cache.update_af_level(float(raw))
            elif frame.command == 0x11:  # attenuator
                if frame.data:
                    val = frame.data[0]
                    old = cache.attenuator
                    cache.update_attenuator(val)
                    if val != old:
                        self._notify_change("att_changed", {"db": val})
            elif frame.command == 0x16 and frame.sub == 0x02:  # preamp
                if frame.data:
                    val = frame.data[0]
                    old = cache.preamp
                    cache.update_preamp(val)
                    if val != old:
                        self._notify_change("preamp_changed", {"level": val})
            elif frame.command == 0x1C and frame.sub == 0x00:  # PTT
                if frame.data:
                    val = bool(frame.data[0])
                    cache.update_ptt(val)
                    self._notify_change("ptt", {"state": val})
        except Exception:
            pass  # Best-effort; never let cache update break the RX loop

    def _notify_change(self, event_name: str, data: dict) -> None:
        """Notify server of state change (best-effort)."""
        cb = getattr(self, "_on_state_change", None)
        if cb is not None:
            logger.info("civ-rx: notify %s %s", event_name, data)
            try:
                cb(event_name, data)
            except Exception:
                logger.warning("civ-rx: notify failed", exc_info=True)
        else:
            logger.debug("civ-rx: no callback for %s", event_name)

    def _publish_scope_frame(self, frame: ScopeFrame) -> None:
        """Publish a complete scope frame to callback and bounded queue."""
        self._publish_civ_event(CivEvent(type=CivEventType.SCOPE_FRAME))
        if self._scope_frame_queue.full():  # type: ignore[attr-defined]
            try:
                self._scope_frame_queue.get_nowait()  # type: ignore[attr-defined]
            except asyncio.QueueEmpty:
                pass
        self._scope_frame_queue.put_nowait(frame)  # type: ignore[attr-defined]
        callback = self._scope_callback  # type: ignore[attr-defined]
        if callback is not None:
            try:
                callback(frame)
            except Exception:
                logger.exception("Scope callback raised an exception")

    def _publish_civ_event(self, event: CivEvent) -> None:
        """Publish CI-V event to internal event queue (best effort)."""
        if self._civ_event_queue.full():  # type: ignore[attr-defined]
            try:
                self._civ_event_queue.get_nowait()  # type: ignore[attr-defined]
            except asyncio.QueueEmpty:
                pass
        self._civ_event_queue.put_nowait(event)  # type: ignore[attr-defined]

    # ------------------------------------------------------------------
    # CI-V worker (commander) lifecycle
    # ------------------------------------------------------------------

    def _start_civ_worker(self) -> None:
        """Start serialized CI-V commander (wfview-like queueing)."""
        self._ensure_civ_runtime()
        self._start_civ_rx_pump()
        if self._commander is None:  # type: ignore[attr-defined]
            self._commander = IcomCommander(  # type: ignore[attr-defined]
                self._execute_civ_raw,
                min_interval=self._civ_min_interval,  # type: ignore[attr-defined]
            )
        self._commander.start()  # type: ignore[attr-defined]

    async def _stop_civ_worker(self) -> None:
        """Stop CI-V commander and fail pending commands."""
        if self._commander is not None:  # type: ignore[attr-defined]
            await self._commander.stop()  # type: ignore[attr-defined]

    # ------------------------------------------------------------------
    # CI-V send infrastructure
    # ------------------------------------------------------------------

    def _check_connected(self) -> None:
        """Raise ConnectionError if not connected."""
        if not self._connected or self._civ_transport is None:  # type: ignore[attr-defined]
            raise ConnectionError("Not connected to radio")

    def _wrap_civ(self, civ_frame: bytes) -> bytes:
        """Wrap a CI-V frame in a UDP data packet for the CI-V port."""
        import struct

        assert self._civ_transport is not None  # type: ignore[attr-defined]
        total_len = CIV_HEADER_SIZE + len(civ_frame)
        pkt = bytearray(total_len)
        struct.pack_into("<I", pkt, 0, total_len)
        struct.pack_into("<H", pkt, 4, 0x00)  # type = DATA
        struct.pack_into("<I", pkt, 8, self._civ_transport.my_id)  # type: ignore[attr-defined]
        struct.pack_into("<I", pkt, 0x0C, self._civ_transport.remote_id)  # type: ignore[attr-defined]
        pkt[0x10] = 0xC1  # reply marker for CI-V data
        struct.pack_into("<H", pkt, 0x11, len(civ_frame))
        struct.pack_into(">H", pkt, 0x13, self._civ_send_seq)  # type: ignore[attr-defined]
        self._civ_send_seq += 1  # type: ignore[attr-defined]
        pkt[CIV_HEADER_SIZE:] = civ_frame
        return bytes(pkt)

    async def _send_civ_raw(
        self,
        civ_frame: bytes,
        *,
        priority: Priority = Priority.NORMAL,
        key: "str | None" = None,
        dedupe: bool = False,
        wait_response: bool = True,
        timeout: "float | None" = None,
    ) -> "CivFrame | None":
        """Enqueue a CI-V command and wait for its response."""
        assert self._civ_transport is not None  # type: ignore[attr-defined]
        self._ensure_civ_runtime()

        if self._commander is None:  # type: ignore[attr-defined]
            # Fallback path (e.g. during tests/mocks before queue init).
            coro = self._execute_civ_raw(civ_frame, wait_response=wait_response)
            if timeout is not None:
                return await asyncio.wait_for(coro, timeout=timeout)
            return await coro

        return await self._commander.send(  # type: ignore[attr-defined]
            civ_frame,
            priority=priority,
            key=key,
            dedupe=dedupe,
            wait_response=wait_response,
            timeout=timeout,
        )

    @staticmethod
    def _civ_expects_response(frame: CivFrame) -> bool:
        """Determine if a CI-V frame expects a data RESPONSE or just an ACK/NAK."""
        if frame.command in (0x03, 0x04):
            return True
        if frame.command == 0x17:
            return False
        if frame.command == 0x27:
            return False
        # If no further payload beyond command/sub is included, it's typically a GET
        return len(frame.data) == 0

    async def _drain_ack_sinks_before_blocking(self) -> None:
        """Give fire-and-forget ACK sinks a short chance to drain, then clear stale ones.

        This prevents a missing ACK from poisoning the ACK waiter queue for the
        next blocking command.
        """
        if self._civ_request_tracker.ack_sink_count == 0:  # type: ignore[attr-defined]
            return

        deadline = time.monotonic() + self._civ_ack_sink_grace  # type: ignore[attr-defined]
        while (
            self._civ_request_tracker.ack_sink_count > 0  # type: ignore[attr-defined]
            and time.monotonic() < deadline
        ):
            await asyncio.sleep(0.005)

        dropped = self._civ_request_tracker.drop_ack_sinks()  # type: ignore[attr-defined]
        if dropped:
            logger.debug(
                "Dropped %d stale ACK sink waiter(s) before blocking command", dropped
            )

    async def _execute_civ_raw(
        self,
        civ_frame: bytes,
        wait_response: bool = True,
        deadline_monotonic: "float | None" = None,
    ) -> "CivFrame | None":
        """Execute one CI-V command via request tracker (serialized by worker)."""
        assert self._civ_transport is not None  # type: ignore[attr-defined]
        self._ensure_civ_runtime()

        parsed_frame = parse_civ_frame(civ_frame)
        request_key = request_key_from_frame(parsed_frame)
        expects_response = self._civ_expects_response(parsed_frame)
        if deadline_monotonic is None:
            deadline_monotonic = time.monotonic() + self._civ_get_timeout  # type: ignore[attr-defined]

        self._cleanup_stale_civ_waiters()

        if not wait_response:
            ack_sink_token: "int | None" = None

            # Fire-and-forget: sink the ACK so it doesn't shift the queue.
            if not expects_response:
                token_or_future = self._civ_request_tracker.register_ack(wait=False)  # type: ignore[attr-defined]
                if isinstance(token_or_future, int):
                    ack_sink_token = token_or_future

            # Ensure RX pump is running for event routing.
            self._start_civ_rx_pump()

            # Rate limit applies to fire-and-forget as well
            now = time.monotonic()
            delta = now - self._last_civ_send_monotonic  # type: ignore[attr-defined]
            if delta < self._civ_min_interval:  # type: ignore[attr-defined]
                await asyncio.sleep(self._civ_min_interval - delta)  # type: ignore[attr-defined]

            pkt = self._wrap_civ(civ_frame)
            try:
                await self._civ_transport.send_tracked(pkt)  # type: ignore[attr-defined]
            except Exception:
                if ack_sink_token is not None:
                    self._civ_request_tracker.unregister_ack_sink(ack_sink_token)  # type: ignore[attr-defined]
                raise

            self._last_civ_send_monotonic = time.monotonic()  # type: ignore[attr-defined]
            return None

        await self._drain_ack_sinks_before_blocking()

        remaining_total = deadline_monotonic - time.monotonic()
        if remaining_total <= 0:
            raise TimeoutError("CI-V response timed out")

        pending: "asyncio.Future[CivFrame] | None" = None
        try:
            # Register future BEFORE starting RX pump / sending.
            if expects_response:
                pending = self._civ_request_tracker.register_response(request_key)  # type: ignore[attr-defined]
            else:
                pending_or_token = self._civ_request_tracker.register_ack(wait=True)  # type: ignore[attr-defined]
                if isinstance(pending_or_token, int):
                    raise RuntimeError("ACK waiter registration returned sink token")
                pending = pending_or_token

            # Ensure RX pump is running for event routing.
            self._start_civ_rx_pump()

            # Rate-limit CI-V commands slightly (wfview-like pacing).
            now = time.monotonic()
            delta = now - self._last_civ_send_monotonic  # type: ignore[attr-defined]
            if delta < self._civ_min_interval:  # type: ignore[attr-defined]
                await asyncio.sleep(self._civ_min_interval - delta)  # type: ignore[attr-defined]

            pkt = self._wrap_civ(civ_frame)
            await self._civ_transport.send_tracked(pkt)  # type: ignore[attr-defined]
            self._last_civ_send_monotonic = time.monotonic()  # type: ignore[attr-defined]
            assert pending is not None
            remaining = deadline_monotonic - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("CI-V response timed out")
            try:
                return await asyncio.wait_for(pending, timeout=remaining)
            except asyncio.TimeoutError:
                self._civ_request_tracker.note_timeout()  # type: ignore[attr-defined]
                logger.debug(
                    "CI-V command 0x%02X timed out",
                    request_key.command,
                )
                raise TimeoutError("CI-V response timed out")
        finally:
            if pending is not None:
                self._civ_request_tracker.unregister(pending)  # type: ignore[attr-defined]
