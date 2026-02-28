"""Audio snapshot/resume logic for IcomRadio reconnect scenarios."""

from __future__ import annotations

import dataclasses
import enum
import logging
from typing import TYPE_CHECKING, Callable

from .audio import AudioPacket, AudioState

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class AudioRecoveryState(enum.Enum):
    """State emitted by the ``on_audio_recovery`` callback."""

    RECOVERING = "recovering"
    RECOVERED = "recovered"
    FAILED = "failed"


@dataclasses.dataclass(frozen=True, slots=True)
class _AudioSnapshot:
    """Captured audio state before disconnect for auto-recovery."""

    rx_active: bool
    tx_active: bool
    pcm_mode: bool
    pcm_rx_callback: "Callable[[bytes | None], None] | None"
    opus_rx_callback: "Callable[[AudioPacket | None], None] | None"
    pcm_params: tuple[int, int, int] | None
    jitter_depth: int


class _AudioRecoveryMixin:
    """Mixin providing audio snapshot/resume for IcomRadio reconnect cycles."""

    def _capture_audio_snapshot(self) -> _AudioSnapshot | None:
        """Capture current audio state for recovery after reconnect.

        Returns ``None`` if no audio stream is active.
        """
        if self._audio_stream is None:  # type: ignore[attr-defined]
            return None

        state = self._audio_stream.state  # type: ignore[attr-defined]
        if state == AudioState.IDLE:
            return None

        rx_active = state in (AudioState.RECEIVING, AudioState.TRANSMITTING) and (
            self._pcm_rx_user_callback is not None  # type: ignore[attr-defined]
            or self._opus_rx_user_callback is not None  # type: ignore[attr-defined]
        )
        tx_active = (
            state == AudioState.TRANSMITTING
            or self._pcm_tx_fmt is not None  # type: ignore[attr-defined]
        )
        pcm_mode = (
            self._pcm_rx_user_callback is not None  # type: ignore[attr-defined]
            or self._pcm_tx_fmt is not None  # type: ignore[attr-defined]
        )

        # Determine PCM params from TX format or transcoder format.
        pcm_params = (
            self._pcm_tx_fmt  # type: ignore[attr-defined]
            or self._pcm_transcoder_fmt  # type: ignore[attr-defined]
        )

        jitter_depth = (
            self._pcm_rx_jitter_depth  # type: ignore[attr-defined]
            if self._pcm_rx_user_callback is not None  # type: ignore[attr-defined]
            else self._opus_rx_jitter_depth  # type: ignore[attr-defined]
        )

        return _AudioSnapshot(
            rx_active=rx_active,
            tx_active=tx_active,
            pcm_mode=pcm_mode,
            pcm_rx_callback=self._pcm_rx_user_callback,  # type: ignore[attr-defined]
            opus_rx_callback=self._opus_rx_user_callback,  # type: ignore[attr-defined]
            pcm_params=pcm_params,
            jitter_depth=jitter_depth,
        )

    async def _recover_audio(self, snapshot: _AudioSnapshot) -> None:
        """Attempt to restart audio streams from a pre-disconnect snapshot.

        Recovery failure is logged but does not raise.
        """
        if self._on_audio_recovery is not None:  # type: ignore[attr-defined]
            self._on_audio_recovery(AudioRecoveryState.RECOVERING)  # type: ignore[attr-defined]

        try:
            if snapshot.rx_active:
                if snapshot.pcm_mode and snapshot.pcm_rx_callback is not None:
                    sr, ch, fms = snapshot.pcm_params or (48000, 1, 20)
                    await self.start_audio_rx_pcm(  # type: ignore[attr-defined]
                        snapshot.pcm_rx_callback,
                        sample_rate=sr,
                        channels=ch,
                        frame_ms=fms,
                        jitter_depth=snapshot.jitter_depth,
                    )
                elif snapshot.opus_rx_callback is not None:
                    await self.start_audio_rx_opus(  # type: ignore[attr-defined]
                        snapshot.opus_rx_callback,
                        jitter_depth=snapshot.jitter_depth,
                    )

            if snapshot.tx_active:
                if snapshot.pcm_mode and snapshot.pcm_params is not None:
                    sr, ch, fms = snapshot.pcm_params
                    await self.start_audio_tx_pcm(  # type: ignore[attr-defined]
                        sample_rate=sr,
                        channels=ch,
                        frame_ms=fms,
                    )
                else:
                    await self.start_audio_tx_opus()  # type: ignore[attr-defined]

        except Exception as exc:
            logger.warning("Audio auto-recovery failed: %s", exc)
            if self._on_audio_recovery is not None:  # type: ignore[attr-defined]
                self._on_audio_recovery(AudioRecoveryState.FAILED)  # type: ignore[attr-defined]
            return

        if self._on_audio_recovery is not None:  # type: ignore[attr-defined]
            self._on_audio_recovery(AudioRecoveryState.RECOVERED)  # type: ignore[attr-defined]
