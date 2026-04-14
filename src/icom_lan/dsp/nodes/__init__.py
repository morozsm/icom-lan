"""Concrete DSP nodes for audio processing pipelines."""

from __future__ import annotations

from icom_lan.dsp.nodes.base import GainNode, PassthroughNode

__all__ = ["GainNode", "PassthroughNode"]
