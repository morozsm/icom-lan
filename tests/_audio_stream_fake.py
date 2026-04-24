"""FakeAudioStream — deterministic double for AudioStream in tests.

Implements the public surface of :class:`icom_lan.audio.lan_stream.AudioStream`
that production code and tests interact with:

    start_rx(callback, *, jitter_depth=None)
    stop_rx()
    start_tx()
    stop_tx()
    push_tx(opus_data)

Call-tracking attributes allow assertions without MagicMock:

    fake.start_rx_count              # times start_rx was awaited
    fake.stop_rx_count               # times stop_rx was awaited
    fake.start_tx_count              # times start_tx was awaited
    fake.stop_tx_count               # times stop_tx was awaited
    fake.last_start_rx_callback      # callback passed to last start_rx call
    fake.last_start_rx_jitter_depth  # jitter_depth kwarg from last start_rx
    fake.tx_frames                   # list of bytes pushed via push_tx
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from icom_lan.audio import AudioState


class FakeAudioStream:
    """Deterministic double for ``AudioStream`` — no real transport needed."""

    def __init__(self) -> None:
        self.state: AudioState = AudioState.IDLE

        self.start_rx_count: int = 0
        self.stop_rx_count: int = 0
        self.start_tx_count: int = 0
        self.stop_tx_count: int = 0

        self.last_start_rx_callback: Callable[..., Any] | None = None
        self.last_start_rx_jitter_depth: int | None = None

        self.tx_frames: list[bytes] = []

    async def start_rx(
        self,
        callback: Callable[..., Any],
        *,
        jitter_depth: int | None = None,
    ) -> None:
        self.last_start_rx_callback = callback
        self.last_start_rx_jitter_depth = jitter_depth
        self.start_rx_count += 1

    async def stop_rx(self) -> None:
        self.stop_rx_count += 1

    async def start_tx(self) -> None:
        self.start_tx_count += 1

    async def stop_tx(self) -> None:
        self.stop_tx_count += 1

    async def push_tx(self, opus_data: bytes) -> None:
        self.tx_frames.append(opus_data)
