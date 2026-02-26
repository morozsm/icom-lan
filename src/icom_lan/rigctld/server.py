"""Rigctld TCP server — asyncio.start_server transport layer.

Responsibilities:
- TCP listener on configurable host:port
- Per-client asyncio.Task with isolated StreamReader/StreamWriter
- Connection lifecycle (accept, timeout, graceful close)
- Max client limit
- Structured logging (client connect/disconnect/errors)
- CLI entry point integration

This module handles only I/O. It delegates parsing to protocol.py
and command execution to handler.py.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from .circuit_breaker import CircuitBreaker, CircuitState
from .contract import ClientSession, HamlibError, RigctldConfig

if TYPE_CHECKING:
    from ..radio import IcomRadio

logger = logging.getLogger(__name__)

__all__ = ["RigctldServer", "run_rigctld_server"]


def _is_packet_mode_set(cmd: Any) -> bool:
    """Return True for set_mode PKT* commands.

    Used to hold poller writes a bit longer while radio applies DATA-mode
    transitions (USB/LSB/RTTY -> PKT*).
    """
    try:
        return (
            getattr(cmd, "long_cmd", "") == "set_mode"
            and bool(getattr(cmd, "args", ()))
            and str(cmd.args[0]).upper().startswith("PKT")
        )
    except Exception:
        return False


class RigctldServer:
    """Asyncio TCP server implementing the hamlib NET rigctld protocol.

    Args:
        radio: Connected IcomRadio instance.
        config: Server configuration; defaults to RigctldConfig().
        _protocol: Override the protocol module (for testing).
        _handler: Override the handler instance (for testing).
        _poller: Override the poller instance (for testing).
        _circuit_breaker: Override the circuit breaker (for testing).
    """

    def __init__(
        self,
        radio: IcomRadio,
        config: RigctldConfig | None = None,
        *,
        _protocol: Any = None,
        _handler: Any = None,
        _poller: Any = None,
        _circuit_breaker: Any = None,
    ) -> None:
        self._radio = radio
        self._config = config or RigctldConfig()
        self._server: asyncio.Server | None = None
        self._client_tasks: set[asyncio.Task[None]] = set()
        self._client_count = 0
        self._next_client_id = 0
        # Injected for testing; populated lazily in start() if None.
        self._protocol: Any = _protocol
        self._rig_handler: Any = _handler
        self._poller: Any = _poller
        self._circuit_breaker: CircuitBreaker | None = _circuit_breaker

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    @property
    def circuit_breaker_state(self) -> CircuitState | None:
        """Current circuit breaker state, or ``None`` if not yet initialised."""
        if self._circuit_breaker is None:
            return None
        return self._circuit_breaker.state

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the TCP listener and initialise the command handler."""
        if self._protocol is None:
            from . import protocol as _proto_mod  # noqa: PLC0415
            self._protocol = _proto_mod

        if self._rig_handler is None:
            from . import handler as _handler_mod  # noqa: PLC0415
            from .state_cache import StateCache  # noqa: PLC0415
            from .poller import RadioPoller  # noqa: PLC0415
            cache = StateCache()
            self._rig_handler = _handler_mod.RigctldHandler(
                self._radio, self._config, cache=cache
            )
            if self._poller is None:
                if self._circuit_breaker is None:
                    self._circuit_breaker = CircuitBreaker()
                self._poller = RadioPoller(
                    self._radio, cache, self._config,
                    circuit_breaker=self._circuit_breaker,
                )

        self._server = await asyncio.start_server(
            self._accept_client,
            host=self._config.host,
            port=self._config.port,
        )
        addr = self._server.sockets[0].getsockname()
        logger.info("rigctld listening on %s:%d", addr[0], addr[1])

        # Poller starts lazily on first client connection to avoid idle
        # CI-V traffic/noise when no CAT clients are connected.

    async def stop(self) -> None:
        """Close the listener and cancel all active client tasks."""
        if self._poller is not None:
            await self._poller.stop()
            self._poller = None

        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

        tasks = list(self._client_tasks)
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        logger.info("rigctld stopped")

    async def serve_forever(self) -> None:
        """Start the server and block until cancelled or stop() is called."""
        await self.start()
        assert self._server is not None
        try:
            await self._server.serve_forever()
        finally:
            await self.stop()

    async def __aenter__(self) -> RigctldServer:
        await self.start()
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.stop()

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def _accept_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Callback from asyncio.start_server — spawns a per-client task.

        Called synchronously within the event loop; must not block.
        """
        if self._client_count >= self._config.max_clients:
            peer = writer.get_extra_info("peername", ("?", 0))
            logger.warning(
                "max_clients (%d) reached, rejecting %s:%s",
                self._config.max_clients,
                peer[0],
                peer[1],
            )
            writer.close()
            return

        loop = asyncio.get_running_loop()
        task = loop.create_task(self._handle_client(reader, writer))
        self._client_tasks.add(task)
        self._client_count += 1

        # Start poller when the first client connects.
        if self._poller is not None and self._client_count == 1:
            loop.create_task(self._poller.start())

        # Optional WSJT-X compatibility pre-warm for first client:
        # if radio is in USB/LSB/RTTY with DATA off, enable DATA mode upfront
        # to avoid long CAT/PTT latency on first TX sequence.
        if self._client_count == 1 and self._config.wsjtx_compat:
            loop.create_task(self._wsjtx_compat_prewarm())

        task.add_done_callback(self._on_client_done)

    def _on_client_done(self, task: asyncio.Task[None]) -> None:
        self._client_tasks.discard(task)
        self._client_count -= 1

        # Stop poller when no clients remain.
        if self._poller is not None and self._client_count <= 0:
            self._client_count = 0
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._poller.stop())
            except RuntimeError:
                # Loop already closed during shutdown.
                pass

    async def _wsjtx_compat_prewarm(self) -> None:
        """Best-effort DATA-mode prewarm for WSJT-X compatibility mode."""
        poller = self._poller
        if poller is not None:
            poller.write_busy = True
        try:
            mode, _ = await self._radio.get_mode_info()
            data_on = await self._radio.get_data_mode()
            mode_name = getattr(mode, "name", str(mode)).upper()
            if not data_on and mode_name in {"USB", "LSB", "RTTY"}:
                await self._radio.set_data_mode(True)
                if poller is not None:
                    poller.hold_for(1.5)
                logger.info(
                    "WSJT-X compat prewarm: DATA mode enabled (base mode=%s)",
                    mode_name,
                )
        except Exception as exc:
            logger.debug("WSJT-X compat prewarm skipped/failed: %s", exc)
        finally:
            if poller is not None:
                poller.write_busy = False

    # ------------------------------------------------------------------
    # Per-client coroutine
    # ------------------------------------------------------------------

    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Manage a single TCP client for its full lifetime."""
        proto = self._protocol
        rig_handler = self._rig_handler

        peer = writer.get_extra_info("peername", ("?", 0))
        self._next_client_id += 1
        client_id = self._next_client_id
        session = ClientSession(
            client_id=client_id,
            peername=f"{peer[0]}:{peer[1]}",
        )
        logger.info("client #%d connected from %s", client_id, session.peername)

        try:
            while True:
                # ── read with idle timeout ───────────────────────────
                try:
                    raw = await asyncio.wait_for(
                        self._readline(reader),
                        timeout=self._config.client_timeout,
                    )
                except asyncio.TimeoutError:
                    logger.info(
                        "client #%d idle timeout (%.1fs)",
                        client_id,
                        self._config.client_timeout,
                    )
                    break
                except ValueError as exc:
                    # Line too long or malformed framing — close connection.
                    logger.warning("client #%d framing error: %s", client_id, exc)
                    break

                if raw is None:
                    logger.info("client #%d EOF", client_id)
                    break

                if not raw:
                    continue  # skip blank lines

                logger.debug("client #%d → %r", client_id, raw)

                # ── parse ────────────────────────────────────────────
                try:
                    cmd = proto.parse_line(raw)
                except ValueError as exc:
                    # Unknown command or bad args → ENIMPL, not EPROTO
                    # (WSJT-X sends commands we don't support yet)
                    logger.debug(
                        "client #%d unknown/bad command: %s", client_id, exc
                    )
                    writer.write(proto.format_error(HamlibError.ENIMPL))
                    await writer.drain()
                    continue
                except Exception as exc:
                    logger.warning(
                        "client #%d parse error: %s", client_id, exc
                    )
                    writer.write(proto.format_error(HamlibError.EPROTO))
                    await writer.drain()
                    continue

                # ── quit ─────────────────────────────────────────────
                if cmd.short_cmd == "q":
                    logger.info("client #%d quit", client_id)
                    break

                # ── execute with command timeout ─────────────────────
                poller_hold = bool(cmd.is_set and self._poller is not None)
                if poller_hold:
                    self._poller.write_busy = True
                try:
                    resp = await asyncio.wait_for(
                        rig_handler.execute(cmd),
                        timeout=self._config.command_timeout,
                    )
                except asyncio.TimeoutError:
                    logger.warning(
                        "client #%d command %r timed out",
                        client_id,
                        cmd.short_cmd,
                    )
                    writer.write(proto.format_error(HamlibError.ETIMEOUT))
                    await writer.drain()
                    continue
                except Exception as exc:
                    logger.error(
                        "client #%d handler error: %s", client_id, exc
                    )
                    writer.write(proto.format_error(HamlibError.EIO))
                    await writer.drain()
                    continue
                finally:
                    if poller_hold:
                        # Packet mode transitions can make CI-V briefly unresponsive.
                        # Keep poller paused for a settle window to avoid
                        # immediate get_frequency storms.
                        if _is_packet_mode_set(cmd):
                            try:
                                self._poller.hold_for(3.0)
                            except Exception:
                                pass
                        self._poller.write_busy = False

                # ── send response ────────────────────────────────────
                out = proto.format_response(cmd, resp, session)
                logger.debug("client #%d ← %r", client_id, out)
                writer.write(out)
                await writer.drain()

        except asyncio.CancelledError:
            logger.info("client #%d cancelled (server shutdown)", client_id)
        except ConnectionResetError:
            logger.info("client #%d connection reset by peer", client_id)
        except Exception as exc:
            logger.error(
                "client #%d unexpected error: %s", client_id, exc, exc_info=True
            )
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
            logger.info("client #%d disconnected", client_id)

    # ------------------------------------------------------------------
    # Line reader
    # ------------------------------------------------------------------

    async def _readline(
        self, reader: asyncio.StreamReader
    ) -> bytes | None:
        """Read one newline-terminated line, stripping the terminator.

        Returns:
            Stripped bytes, or None on EOF.

        Raises:
            ValueError: If the line exceeds max_line_length.
        """
        try:
            line = await reader.readline()
        except asyncio.IncompleteReadError:
            # EOF arrived before a newline (abrupt disconnect).
            return None
        except asyncio.LimitOverrunError:
            raise ValueError("command line exceeds StreamReader buffer limit")

        if not line:
            return None  # clean EOF

        stripped = line.rstrip(b"\r\n")
        if len(stripped) > self._config.max_line_length:
            raise ValueError(
                f"command line too long: {len(stripped)} bytes "
                f"(max {self._config.max_line_length})"
            )
        return stripped


# ---------------------------------------------------------------------------
# Convenience entry point
# ---------------------------------------------------------------------------


async def run_rigctld_server(radio: IcomRadio, **kwargs: Any) -> None:
    """Create a :class:`RigctldServer` from *kwargs* and run it forever.

    Keyword arguments are forwarded to :class:`RigctldConfig`.

    Example::

        await run_rigctld_server(radio, host="0.0.0.0", port=4532)
    """
    config = RigctldConfig(**kwargs)  # type: ignore[arg-type]
    server = RigctldServer(radio, config)
    await server.serve_forever()
