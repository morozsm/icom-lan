"""Concrete DSP nodes for audio processing pipelines."""

from __future__ import annotations

from rigplane.dsp.nodes.base import GainNode, PassthroughNode
from rigplane.dsp.nodes.nr_scipy import NRScipyNode

__all__ = ["GainNode", "NRScipyNode", "PassthroughNode"]
