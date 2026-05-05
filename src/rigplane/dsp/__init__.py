"""DSP pipeline core abstractions for real-time audio processing."""

from __future__ import annotations

from rigplane.dsp.exceptions import DSPBackendUnavailable, DSPConfigError
from rigplane.dsp.pipeline import DSPNode, DSPPipeline
from rigplane.dsp.tap_registry import TapHandle, TapRegistry

__all__ = [
    "DSPBackendUnavailable",
    "DSPConfigError",
    "DSPNode",
    "DSPPipeline",
    "TapHandle",
    "TapRegistry",
]
