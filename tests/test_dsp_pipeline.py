"""Tests for DSP pipeline core abstractions."""

from __future__ import annotations

import struct
from typing import Any

import numpy as np
import pytest

from icom_lan.dsp import DSPBackendUnavailable, DSPConfigError, DSPPipeline


# ---------------------------------------------------------------------------
# Test node helpers
# ---------------------------------------------------------------------------

class GainNode:
    """Multiplies samples by a fixed gain factor."""

    def __init__(self, name: str, gain: float = 2.0) -> None:
        self.name = name
        self.enabled = True
        self.required_sample_rate: int | None = None
        self._gain = gain
        self._reset_count = 0

    def process(self, samples: np.ndarray, sample_rate: int) -> np.ndarray:
        return samples * self._gain

    def get_params(self) -> dict[str, Any]:
        return {"gain": self._gain}

    def set_params(self, **kwargs: Any) -> None:
        if "gain" in kwargs:
            self._gain = kwargs["gain"]

    def reset(self) -> None:
        self._reset_count += 1


class OffsetNode:
    """Adds a fixed offset to all samples."""

    def __init__(self, name: str, offset: float = 0.1) -> None:
        self.name = name
        self.enabled = True
        self.required_sample_rate: int | None = None
        self._offset = offset
        self._reset_count = 0

    def process(self, samples: np.ndarray, sample_rate: int) -> np.ndarray:
        return samples + self._offset

    def get_params(self) -> dict[str, Any]:
        return {"offset": self._offset}

    def set_params(self, **kwargs: Any) -> None:
        if "offset" in kwargs:
            self._offset = kwargs["offset"]

    def reset(self) -> None:
        self._reset_count += 1


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestDSPPipelinePassthrough:
    """Empty pipeline returns input unchanged."""

    def test_no_nodes_passthrough(self) -> None:
        pipe = DSPPipeline()
        samples = np.array([0.0, 0.5, -0.5, 1.0], dtype=np.float32)
        out = pipe.process(samples, 48000)
        np.testing.assert_array_equal(out, samples)

    def test_empty_property_true(self) -> None:
        pipe = DSPPipeline()
        assert pipe.empty is True

    def test_empty_property_false(self) -> None:
        pipe = DSPPipeline([GainNode("g")])
        assert pipe.empty is False


class TestDSPPipelineDisabledNodes:
    """Pipeline skips disabled nodes."""

    def test_disabled_node_skipped(self) -> None:
        node = GainNode("gain", gain=2.0)
        node.enabled = False
        pipe = DSPPipeline([node])
        samples = np.array([1.0], dtype=np.float32)
        out = pipe.process(samples, 48000)
        np.testing.assert_array_equal(out, samples)


class TestDSPPipelineOrder:
    """Pipeline processes nodes in order."""

    def test_gain_then_offset(self) -> None:
        # gain(2) then offset(0.1): 1.0 * 2 + 0.1 = 2.1
        pipe = DSPPipeline([GainNode("g", 2.0), OffsetNode("o", 0.1)])
        samples = np.array([1.0], dtype=np.float32)
        out = pipe.process(samples, 48000)
        np.testing.assert_allclose(out, [2.1], rtol=1e-6)

    def test_offset_then_gain(self) -> None:
        # offset(0.1) then gain(2): (1.0 + 0.1) * 2 = 2.2
        pipe = DSPPipeline([OffsetNode("o", 0.1), GainNode("g", 2.0)])
        samples = np.array([1.0], dtype=np.float32)
        out = pipe.process(samples, 48000)
        np.testing.assert_allclose(out, [2.2], rtol=1e-6)


class TestDSPPipelineReset:
    """reset() calls reset on all nodes."""

    def test_reset_all(self) -> None:
        g = GainNode("g")
        o = OffsetNode("o")
        pipe = DSPPipeline([g, o])
        pipe.reset()
        assert g._reset_count == 1
        assert o._reset_count == 1


class TestDSPPipelineProcessBytes:
    """process_bytes s16le roundtrip."""

    def test_passthrough_roundtrip(self) -> None:
        """No nodes → bytes out == bytes in."""
        pipe = DSPPipeline()
        values = [0, 1000, -1000, 32767, -32768]
        pcm_in = struct.pack(f"<{len(values)}h", *values)
        pcm_out = pipe.process_bytes(pcm_in, 48000)
        assert pcm_out == pcm_in

    def test_gain_node_roundtrip(self) -> None:
        """Gain=2 doubles sample values."""
        pipe = DSPPipeline([GainNode("g", gain=2.0)])
        values = [100, -100, 0]
        pcm_in = struct.pack(f"<{len(values)}h", *values)
        pcm_out = pipe.process_bytes(pcm_in, 48000)
        result = struct.unpack(f"<{len(values)}h", pcm_out)
        assert result == (200, -200, 0)


class TestDSPPipelineAddRemoveGet:
    """add_node / remove_node / get_node."""

    def test_add_and_get(self) -> None:
        pipe = DSPPipeline()
        g = GainNode("gain1")
        pipe.add_node(g)
        assert pipe.get_node("gain1") is g
        assert pipe.empty is False

    def test_remove(self) -> None:
        pipe = DSPPipeline([GainNode("g")])
        pipe.remove_node("g")
        assert pipe.empty is True

    def test_get_missing_returns_none(self) -> None:
        pipe = DSPPipeline()
        assert pipe.get_node("nope") is None

    def test_remove_missing_raises(self) -> None:
        pipe = DSPPipeline()
        with pytest.raises(KeyError):
            pipe.remove_node("nope")


class TestDSPPipelineConfig:
    """to_config / from_config roundtrip."""

    def test_roundtrip(self) -> None:
        g = GainNode("g", gain=3.0)
        o = OffsetNode("o", offset=0.5)
        pipe = DSPPipeline([g, o])
        config = pipe.to_config()

        assert len(config) == 2
        assert config[0]["name"] == "g"
        assert config[0]["enabled"] is True
        assert config[0]["params"] == {"gain": 3.0}

        # Rebuild from config using a registry
        registry = {
            "g": lambda name, params: GainNode(name, **params),
            "o": lambda name, params: OffsetNode(name, **params),
        }
        pipe2 = DSPPipeline.from_config(config, registry)
        assert pipe2.get_node("g") is not None
        assert pipe2.get_node("o") is not None
        assert pipe2.get_node("g").get_params() == {"gain": 3.0}  # type: ignore[union-attr]

    def test_from_config_missing_registry_key(self) -> None:
        config = [{"name": "unknown", "enabled": True, "params": {}}]
        with pytest.raises(DSPConfigError):
            DSPPipeline.from_config(config, {})


class TestDSPExceptions:
    """Exception hierarchy."""

    def test_backend_unavailable_is_import_error(self) -> None:
        assert issubclass(DSPBackendUnavailable, ImportError)

    def test_config_error_is_value_error(self) -> None:
        assert issubclass(DSPConfigError, ValueError)
