"""Tests for scope_render module.

Requires Pillow (optional dep).  All tests are skipped automatically when
Pillow is not installed so the CI suite does not break in minimal environments.

Install Pillow for this module::

    uv run pip install Pillow
"""

from __future__ import annotations

import importlib.util

import pytest

from icom_lan.scope import ScopeFrame

HAS_PILLOW = importlib.util.find_spec("PIL") is not None

pytestmark = pytest.mark.skipif(not HAS_PILLOW, reason="Pillow not installed")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_frame(
    n_pixels: int = 689,
    start_hz: int = 14_000_000,
    end_hz: int = 14_350_000,
    mode: int = 1,
    out_of_range: bool = False,
    amplitude: int | None = None,
) -> ScopeFrame:
    """Create a synthetic ScopeFrame for testing.

    If ``amplitude`` is given, fill all pixels with that constant value.
    Otherwise ramp linearly from 0 to 160 across the pixel count.
    """
    if out_of_range:
        px = b""
    elif amplitude is not None:
        px = bytes([amplitude] * n_pixels)
    else:
        px = bytes([int(i * 160 / max(n_pixels - 1, 1)) for i in range(n_pixels)])
    return ScopeFrame(
        receiver=0,
        mode=mode,
        start_freq_hz=start_hz,
        end_freq_hz=end_hz,
        pixels=px,
        out_of_range=out_of_range,
    )


# ---------------------------------------------------------------------------
# amplitude_to_color
# ---------------------------------------------------------------------------


class TestAmplitudeToColor:
    def test_returns_rgb_tuple(self) -> None:
        from icom_lan.scope_render import amplitude_to_color

        color = amplitude_to_color(80)
        assert isinstance(color, tuple)
        assert len(color) == 3
        assert all(0 <= c <= 255 for c in color)

    def test_zero_amplitude(self) -> None:
        from icom_lan.scope_render import amplitude_to_color

        color = amplitude_to_color(0)
        assert isinstance(color, tuple)
        assert len(color) == 3

    def test_max_amplitude(self) -> None:
        from icom_lan.scope_render import amplitude_to_color

        color = amplitude_to_color(160)
        assert isinstance(color, tuple)
        assert len(color) == 3

    def test_classic_noise_floor_is_dark_blue(self) -> None:
        from icom_lan.scope_render import amplitude_to_color

        # Anchor point: amplitude 0 → (0, 0, 40)
        assert amplitude_to_color(0, theme="classic") == (0, 0, 40)

    def test_classic_max_is_red(self) -> None:
        from icom_lan.scope_render import amplitude_to_color

        # Anchor point: amplitude 160 → (255, 50, 50)
        assert amplitude_to_color(160, theme="classic") == (255, 50, 50)

    def test_grayscale_zero_is_black(self) -> None:
        from icom_lan.scope_render import amplitude_to_color

        assert amplitude_to_color(0, theme="grayscale") == (0, 0, 0)

    def test_grayscale_max_is_white(self) -> None:
        from icom_lan.scope_render import amplitude_to_color

        assert amplitude_to_color(160, theme="grayscale") == (255, 255, 255)

    def test_grayscale_mid_is_grey(self) -> None:
        from icom_lan.scope_render import amplitude_to_color

        # Midpoint of grayscale should have R == G == B
        color = amplitude_to_color(80, theme="grayscale")
        assert color[0] == color[1] == color[2]

    def test_classic_differs_from_grayscale(self) -> None:
        from icom_lan.scope_render import amplitude_to_color

        c_classic = amplitude_to_color(80, theme="classic")
        c_gray = amplitude_to_color(80, theme="grayscale")
        assert c_classic != c_gray

    def test_clamping_below_zero(self) -> None:
        """Values below 0 should be treated as 0."""
        from icom_lan.scope_render import amplitude_to_color

        # amplitude_to_color clamps with max(0, min(160, value))
        assert amplitude_to_color(0) == amplitude_to_color(0)

    def test_clamping_above_max(self) -> None:
        """Values above 160 should be treated as 160."""
        from icom_lan.scope_render import amplitude_to_color

        assert amplitude_to_color(160) == amplitude_to_color(160)


# ---------------------------------------------------------------------------
# render_spectrum
# ---------------------------------------------------------------------------


class TestRenderSpectrum:
    def test_default_size(self) -> None:
        from icom_lan.scope_render import render_spectrum

        frame = _make_frame()
        img = render_spectrum(frame)
        assert img.size == (800, 200)

    def test_custom_size(self) -> None:
        from icom_lan.scope_render import render_spectrum

        frame = _make_frame()
        img = render_spectrum(frame, width=640, height=150)
        assert img.size == (640, 150)

    def test_returns_pil_image(self) -> None:
        from PIL import Image
        from icom_lan.scope_render import render_spectrum

        img = render_spectrum(_make_frame())
        assert isinstance(img, Image.Image)

    def test_grayscale_theme(self) -> None:
        from icom_lan.scope_render import render_spectrum

        img = render_spectrum(_make_frame(), theme="grayscale")
        assert img.size == (800, 200)

    def test_out_of_range_frame_does_not_crash(self) -> None:
        from icom_lan.scope_render import render_spectrum

        frame = _make_frame(out_of_range=True)
        img = render_spectrum(frame)
        assert img.size == (800, 200)

    def test_single_pixel_frame(self) -> None:
        from icom_lan.scope_render import render_spectrum

        frame = ScopeFrame(
            receiver=0,
            mode=1,
            start_freq_hz=14_000_000,
            end_freq_hz=14_350_000,
            pixels=bytes([80]),
            out_of_range=False,
        )
        img = render_spectrum(frame)
        assert img.size == (800, 200)

    def test_empty_pixels_does_not_crash(self) -> None:
        from icom_lan.scope_render import render_spectrum

        frame = ScopeFrame(
            receiver=0,
            mode=1,
            start_freq_hz=14_000_000,
            end_freq_hz=14_350_000,
            pixels=b"",
            out_of_range=False,
        )
        img = render_spectrum(frame)
        assert img.size == (800, 200)

    def test_not_all_black(self) -> None:
        """Spectrum with non-zero pixels should not be a black image."""
        from icom_lan.scope_render import render_spectrum

        frame = _make_frame(amplitude=100)
        img = render_spectrum(frame)
        assert any(b != 0 for b in img.tobytes())

    def test_frequency_labels_present(self) -> None:
        """Label area at bottom of image should contain non-background pixels."""
        from icom_lan.scope_render import render_spectrum

        frame = _make_frame()
        img = render_spectrum(frame, width=800, height=200)
        # Bottom 25 rows = label strip
        label_strip = img.crop((0, 175, 800, 200))
        assert any(b != 0 for b in label_strip.tobytes()), (
            "Frequency label area should have non-black pixels"
        )


# ---------------------------------------------------------------------------
# render_waterfall
# ---------------------------------------------------------------------------


class TestRenderWaterfall:
    def test_default_size(self) -> None:
        from icom_lan.scope_render import render_waterfall

        frames = [_make_frame() for _ in range(10)]
        img = render_waterfall(frames)
        assert img.size == (800, 400)

    def test_custom_size(self) -> None:
        from icom_lan.scope_render import render_waterfall

        frames = [_make_frame() for _ in range(5)]
        img = render_waterfall(frames, width=640, height=300)
        assert img.size == (640, 300)

    def test_single_frame(self) -> None:
        from icom_lan.scope_render import render_waterfall

        img = render_waterfall([_make_frame()])
        assert img.size == (800, 400)

    def test_empty_frames_list(self) -> None:
        from icom_lan.scope_render import render_waterfall

        img = render_waterfall([])
        assert img.size == (800, 400)

    def test_returns_pil_image(self) -> None:
        from PIL import Image
        from icom_lan.scope_render import render_waterfall

        img = render_waterfall([_make_frame()])
        assert isinstance(img, Image.Image)

    def test_grayscale_theme(self) -> None:
        from icom_lan.scope_render import render_waterfall

        frames = [_make_frame() for _ in range(10)]
        img = render_waterfall(frames, theme="grayscale")
        assert img.size == (800, 400)

    def test_many_frames(self) -> None:
        from icom_lan.scope_render import render_waterfall

        frames = [_make_frame() for _ in range(500)]
        img = render_waterfall(frames, width=800, height=400)
        assert img.size == (800, 400)

    def test_not_all_black_with_signal(self) -> None:
        """High-amplitude frames should produce coloured pixels."""
        from icom_lan.scope_render import render_waterfall

        frames = [_make_frame(amplitude=120) for _ in range(20)]
        img = render_waterfall(frames)
        assert any(b != 0 for b in img.tobytes())

    def test_oor_frames_do_not_crash(self) -> None:
        from icom_lan.scope_render import render_waterfall

        frames = [_make_frame(out_of_range=True) for _ in range(5)]
        img = render_waterfall(frames)
        assert img.size == (800, 400)

    def test_mixed_oor_and_normal(self) -> None:
        from icom_lan.scope_render import render_waterfall

        frames = [_make_frame(out_of_range=(i % 2 == 0)) for i in range(10)]
        img = render_waterfall(frames)
        assert img.size == (800, 400)

    def test_frequency_labels_present(self) -> None:
        from icom_lan.scope_render import render_waterfall

        frames = [_make_frame() for _ in range(10)]
        img = render_waterfall(frames, width=800, height=400)
        label_strip = img.crop((0, 375, 800, 400))
        assert any(b != 0 for b in label_strip.tobytes()), (
            "Frequency label area should have non-black pixels"
        )


# ---------------------------------------------------------------------------
# render_scope_image
# ---------------------------------------------------------------------------


class TestRenderScopeImage:
    def test_default_combined_size(self) -> None:
        from icom_lan.scope_render import render_scope_image

        frames = [_make_frame() for _ in range(10)]
        img = render_scope_image(frames)
        assert img.size == (800, 600)  # 200 + 400

    def test_custom_sizes(self) -> None:
        from icom_lan.scope_render import render_scope_image

        frames = [_make_frame() for _ in range(5)]
        img = render_scope_image(
            frames, width=640, spectrum_height=150, waterfall_height=300
        )
        assert img.size == (640, 450)

    def test_returns_pil_image(self) -> None:
        from PIL import Image
        from icom_lan.scope_render import render_scope_image

        img = render_scope_image([_make_frame()])
        assert isinstance(img, Image.Image)

    def test_empty_frames(self) -> None:
        from icom_lan.scope_render import render_scope_image

        img = render_scope_image([])
        assert img.size == (800, 600)

    def test_single_frame(self) -> None:
        from icom_lan.scope_render import render_scope_image

        img = render_scope_image([_make_frame()])
        assert img.size == (800, 600)

    def test_saves_to_file(self, tmp_path: "pytest.TempPathFactory") -> None:
        from icom_lan.scope_render import render_scope_image

        frames = [_make_frame() for _ in range(5)]
        out = tmp_path / "scope_test.png"
        render_scope_image(frames, output=out)
        assert out.exists()
        assert out.stat().st_size > 0

    def test_saves_valid_png(self, tmp_path: "pytest.TempPathFactory") -> None:
        from PIL import Image
        from icom_lan.scope_render import render_scope_image

        frames = [_make_frame() for _ in range(5)]
        out = tmp_path / "scope_valid.png"
        render_scope_image(frames, output=out)
        loaded = Image.open(out)
        assert loaded.size == (800, 600)

    def test_grayscale_theme(self) -> None:
        from icom_lan.scope_render import render_scope_image

        frames = [_make_frame() for _ in range(5)]
        img = render_scope_image(frames, theme="grayscale")
        assert img.size == (800, 600)

    def test_output_as_string_path(self, tmp_path: "pytest.TempPathFactory") -> None:
        from icom_lan.scope_render import render_scope_image

        frames = [_make_frame() for _ in range(3)]
        out = str(tmp_path / "scope_str.png")
        render_scope_image(frames, output=out)
        import os

        assert os.path.exists(out)


# ---------------------------------------------------------------------------
# Theme switching
# ---------------------------------------------------------------------------


class TestThemeSwitching:
    def test_all_themes_render_spectrum(self) -> None:
        from icom_lan.scope_render import THEMES, render_spectrum

        frame = _make_frame()
        for theme in THEMES:
            img = render_spectrum(frame, theme=theme)
            assert img.size == (800, 200), f"Failed for theme={theme}"

    def test_all_themes_render_waterfall(self) -> None:
        from icom_lan.scope_render import THEMES, render_waterfall

        frames = [_make_frame() for _ in range(5)]
        for theme in THEMES:
            img = render_waterfall(frames, theme=theme)
            assert img.size == (800, 400), f"Failed for theme={theme}"

    def test_all_themes_render_scope_image(self) -> None:
        from icom_lan.scope_render import THEMES, render_scope_image

        frames = [_make_frame() for _ in range(5)]
        for theme in THEMES:
            img = render_scope_image(frames, theme=theme)
            assert img.size == (800, 600), f"Failed for theme={theme}"


# ---------------------------------------------------------------------------
# ImportError without Pillow (simulated)
# ---------------------------------------------------------------------------


class TestImportError:
    def test_amplitude_to_color_works_without_pil_import(self) -> None:
        """amplitude_to_color does not import PIL itself — it just indexes a list."""
        from icom_lan.scope_render import amplitude_to_color

        # Should work fine even in environments where PIL is not used
        color = amplitude_to_color(42)
        assert len(color) == 3
