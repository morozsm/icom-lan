"""Tests for PassthroughNode and GainNode — base DSP nodes."""

from __future__ import annotations

import numpy as np
import pytest

from icom_lan.dsp.pipeline import DSPNode


class TestPassthroughNode:
    """PassthroughNode returns samples unchanged."""

    def test_output_equals_input(self) -> None:
        from icom_lan.dsp.nodes import PassthroughNode

        node = PassthroughNode()
        samples = np.array([0.0, 0.5, -0.5, 1.0, -1.0], dtype=np.float32)
        result = node.process(samples, 48000)
        np.testing.assert_array_equal(result, samples)

    def test_conforms_to_dsp_node(self) -> None:
        from icom_lan.dsp.nodes import PassthroughNode

        node = PassthroughNode()
        assert isinstance(node, DSPNode)

    def test_attributes(self) -> None:
        from icom_lan.dsp.nodes import PassthroughNode

        node = PassthroughNode()
        assert node.name == "passthrough"
        assert node.enabled is True
        assert node.required_sample_rate is None

    def test_get_params_empty(self) -> None:
        from icom_lan.dsp.nodes import PassthroughNode

        node = PassthroughNode()
        assert node.get_params() == {}

    def test_set_params_noop(self) -> None:
        from icom_lan.dsp.nodes import PassthroughNode

        node = PassthroughNode()
        node.set_params(foo="bar")  # should not raise

    def test_reset_noop(self) -> None:
        from icom_lan.dsp.nodes import PassthroughNode

        node = PassthroughNode()
        node.reset()  # should not raise


class TestGainNode:
    """GainNode applies linear gain and clips to [-1.0, 1.0]."""

    def test_zero_db_is_passthrough(self) -> None:
        from icom_lan.dsp.nodes import GainNode

        node = GainNode(gain_db=0.0)
        samples = np.array([0.0, 0.5, -0.5, 1.0, -1.0], dtype=np.float32)
        result = node.process(samples, 48000)
        np.testing.assert_array_almost_equal(result, samples)

    def test_plus_6db_doubles_amplitude(self) -> None:
        from icom_lan.dsp.nodes import GainNode

        node = GainNode(gain_db=6.0)
        samples = np.array([0.25], dtype=np.float32)
        result = node.process(samples, 48000)
        # +6dB ≈ 1.9953 linear factor, so 0.25 * ~2.0 ≈ 0.5
        np.testing.assert_allclose(result, [0.25 * 10 ** (6.0 / 20.0)], rtol=1e-5)

    def test_minus_6db_halves_amplitude(self) -> None:
        from icom_lan.dsp.nodes import GainNode

        node = GainNode(gain_db=-6.0)
        samples = np.array([1.0], dtype=np.float32)
        result = node.process(samples, 48000)
        np.testing.assert_allclose(result, [10 ** (-6.0 / 20.0)], rtol=1e-5)

    def test_clips_at_plus_minus_one(self) -> None:
        from icom_lan.dsp.nodes import GainNode

        node = GainNode(gain_db=20.0)
        samples = np.array([0.9, -0.9], dtype=np.float32)
        result = node.process(samples, 48000)
        assert float(result[0]) == pytest.approx(1.0)
        assert float(result[1]) == pytest.approx(-1.0)

    def test_get_params(self) -> None:
        from icom_lan.dsp.nodes import GainNode

        node = GainNode(gain_db=3.5)
        assert node.get_params() == {"gain_db": 3.5}

    def test_set_params_roundtrip(self) -> None:
        from icom_lan.dsp.nodes import GainNode

        node = GainNode(gain_db=0.0)
        node.set_params(gain_db=12.0)
        assert node.get_params() == {"gain_db": 12.0}

    def test_set_params_updates_behavior(self) -> None:
        from icom_lan.dsp.nodes import GainNode

        node = GainNode(gain_db=0.0)
        samples = np.array([0.25], dtype=np.float32)

        # 0 dB — passthrough
        result_before = node.process(samples, 48000)
        np.testing.assert_array_almost_equal(result_before, [0.25])

        # +6 dB — approximately doubles
        node.set_params(gain_db=6.0)
        result_after = node.process(samples, 48000)
        np.testing.assert_allclose(
            result_after, [0.25 * 10 ** (6.0 / 20.0)], rtol=1e-5
        )

    def test_conforms_to_dsp_node(self) -> None:
        from icom_lan.dsp.nodes import GainNode

        node = GainNode()
        assert isinstance(node, DSPNode)

    def test_attributes(self) -> None:
        from icom_lan.dsp.nodes import GainNode

        node = GainNode()
        assert node.name == "gain"
        assert node.enabled is True
        assert node.required_sample_rate is None
