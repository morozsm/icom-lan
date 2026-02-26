"""Autonomous radio state poller for the rigctld server.

Polls the radio at a configurable interval and keeps the shared
:class:`~icom_lan.rigctld.state_cache.StateCache` up to date so that
read commands can be served from cache instead of waiting for a CI-V
round-trip.

The poller runs as a background asyncio task and is intentionally
resilient: timeout or connection errors from a single poll cycle are
logged as warnings and the poller continues on the next cycle.

If a :class:`~icom_lan.rigctld.circuit_breaker.CircuitBreaker` is
attached, the poller skips cycles when the circuit is OPEN and uses a
single-command probe when HALF_OPEN.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING

from ..exceptions import ConnectionError as IcomConnectionError
from ..exceptions import TimeoutError as IcomTimeoutError
from .circuit_breaker import CircuitBreaker, CircuitState
from .contract import CIV_TO_HAMLIB_MODE, RigctldConfig
from .state_cache import StateCache

if TYPE_CHECKING:
    from ..radio import IcomRadio

__all__ = ["RadioPoller"]

logger = logging.getLogger(__name__)

# How often to emit periodic stats to the log.
_STATS_LOG_INTERVAL: float = 30.0


class RadioPoller:
    """Background task that periodically polls the radio and updates a cache.

    Args:
        radio: Connected IcomRadio instance.
        cache: Shared StateCache to update on each poll cycle.
        config: Server configuration (uses ``poll_interval``).
        circuit_breaker: Optional circuit breaker.  When provided, poll cycles
            are skipped while the circuit is OPEN and a single-command probe
            is used when HALF_OPEN.
    """

    def __init__(
        self,
        radio: "IcomRadio",
        cache: StateCache,
        config: RigctldConfig,
        circuit_breaker: CircuitBreaker | None = None,
    ) -> None:
        self._radio = radio
        self._cache = cache
        self._config = config
        self._circuit_breaker = circuit_breaker
        self._task: asyncio.Task[None] | None = None
        # Set to True while a write command is in progress so the poll
        # cycle can be skipped to avoid interleaving CI-V commands.
        self.write_busy: bool = False
        # Initialise to now so the first log fires after a full interval.
        self._last_stats_log: float = time.monotonic()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the background poll loop.

        Idempotent: calling start() on an already-running poller is a no-op.
        """
        if self._task is not None:
            return
        loop = asyncio.get_running_loop()
        self._task = loop.create_task(self._run(), name="rigctld-poller")
        logger.debug("RadioPoller started (interval=%.3fs)", self._config.poll_interval)

    async def stop(self) -> None:
        """Cancel the background poll loop and wait for it to finish.

        Idempotent: safe to call when the poller was never started.
        """
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None
        logger.debug("RadioPoller stopped")

    # ------------------------------------------------------------------
    # Internal loop
    # ------------------------------------------------------------------

    async def _run(self) -> None:
        """Main poll loop — runs until cancelled."""
        while True:
            await asyncio.sleep(self._config.poll_interval)
            if self.write_busy:
                logger.debug("RadioPoller: write command in progress, skipping cycle")
                continue

            # Circuit breaker gate: skip if OPEN, probe if HALF_OPEN.
            cb = self._circuit_breaker
            if cb is not None:
                state = cb.state  # may trigger OPEN → HALF_OPEN transition
                if state == CircuitState.OPEN:
                    logger.debug("RadioPoller: circuit OPEN, skipping poll cycle")
                    continue

            await self._poll_once()
            self._maybe_log_stats()

    async def _poll_once(self) -> None:
        """Execute one poll cycle: get frequency, then (if not a probe) mode."""
        cb = self._circuit_breaker
        is_probe = cb is not None and cb.state == CircuitState.HALF_OPEN

        # --- frequency --------------------------------------------------
        try:
            freq = await self._radio.get_frequency()
            self._cache.update_freq(freq)
            if cb is not None:
                cb.record_success()
        except (IcomTimeoutError, IcomConnectionError) as exc:
            logger.warning("RadioPoller: get_frequency failed: %s", exc)
            if cb is not None:
                cb.record_failure()
        except Exception as exc:  # pragma: no cover — unexpected
            logger.warning("RadioPoller: get_frequency unexpected error: %s", exc)

        # HALF_OPEN probe: one command is enough to test connectivity.
        if is_probe:
            return

        # Bail out early if a write started while we were awaiting.
        if self.write_busy:
            return

        # --- mode -------------------------------------------------------
        try:
            mode, filter_width = await self._radio.get_mode_info()
            mode_str = CIV_TO_HAMLIB_MODE.get(mode.value, "USB")
            self._cache.update_mode(mode_str, filter_width)
        except (IcomTimeoutError, IcomConnectionError) as exc:
            logger.warning("RadioPoller: get_mode_info failed: %s", exc)
        except Exception as exc:  # pragma: no cover — unexpected
            logger.warning("RadioPoller: get_mode_info unexpected error: %s", exc)

        # Bail out early if a write started while we were awaiting.
        if self.write_busy:
            return

        # --- data mode --------------------------------------------------
        try:
            data_mode = await self._radio.get_data_mode()
            self._cache.update_data_mode(data_mode)
        except (IcomTimeoutError, IcomConnectionError) as exc:
            logger.warning("RadioPoller: get_data_mode failed: %s", exc)
        except Exception as exc:  # pragma: no cover — unexpected
            logger.warning("RadioPoller: get_data_mode unexpected error: %s", exc)

    # ------------------------------------------------------------------
    # Monitoring
    # ------------------------------------------------------------------

    def _maybe_log_stats(self) -> None:
        """Emit periodic stats log (throttled to every 30 seconds)."""
        now = time.monotonic()
        if now - self._last_stats_log < _STATS_LOG_INTERVAL:
            return
        self._last_stats_log = now

        cb = self._circuit_breaker
        cb_state = cb.state.value if cb is not None else "N/A"

        tracker_stats: dict[str, int] = {}
        if hasattr(self._radio, "civ_stats"):
            try:
                tracker_stats = self._radio.civ_stats()
            except Exception:  # pragma: no cover
                pass

        logger.info(
            "RadioPoller stats — circuit: %s, tracker: %s",
            cb_state,
            tracker_stats,
        )
