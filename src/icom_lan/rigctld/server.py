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

from .contract import ClientSession, HamlibError, RigctldConfig

if TYPE_CHECKING:
    from ..radio import IcomRadio

logger = logging.getLogger(__name__)

__all__ = ["RigctldServer", "run_rigctld_server"]


class RigctldServer:
    """Asyncio TCP server implementing the hamlib NET rigctld protocol.

    Args:
        radio: Connected IcomRadio instance.
        config: Server configuration; defaults to RigctldConfig().
        _protocol: Override the protocol module (for testing).
        _handler: Override the handler instance (for testing).
    """

    def __init__(
        self,
        radio: IcomRadio,
        config: RigctldConfig | None = None,
        *,
        _protocol: Any = None,
        _handler: Any = None,
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
            self._rig_handler = _handler_mod.RigctldHandler(
                self._radio, self._config
            )

        self._server = await asyncio.start_server(
            self._accept_client,
            host=self._config.host,
            port=self._config.port,
        )
        addr = self._server.sockets[0].getsockname()
        logger.info("rigctld listening on %s:%d", addr[0], addr[1])

    async def stop(self) -> None:
        """Close the listener and cancel all active client tasks."""
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
        task.add_done_callback(self._on_client_done)

    def _on_client_done(self, task: asyncio.Task[None]) -> None:
        self._client_tasks.discard(task)
        self._client_count -= 1

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
            raise ValueError(
                f"command line exceeds StreamReader buffer limit"
            )

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
