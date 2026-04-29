"""Tests for issue #1101 — DspControlCapable filter family extension.

Covers:
- Hz↔index round-trip across IC-7610 (segmented_bcd_index) and FTX-1 (table_index)
- DspControlCapable protocol satisfaction (IcomRadio + YaesuCatRadio)
- rigctld filter-width round-trip via set_mode/get_mode passband
- get_filter receiver param fix (P3-04)
- web/radio_poller dispatches set_filter_width via protocol (P2-04)
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from icom_lan.backends.yaesu_cat.radio import YaesuCatRadio
from icom_lan.commands._codec import (
    filter_hz_to_index,
    filter_index_to_hz,
    hz_to_table_index,
    table_index_to_hz,
)
from icom_lan.profiles import resolve_radio_profile
from icom_lan.radio import IcomRadio
from icom_lan.radio_protocol import DspControlCapable
from icom_lan.rig_loader import load_rig
from icom_lan.types import CivFrame

_RIGS_DIR = Path(__file__).parents[1] / "rigs"


# ---------------------------------------------------------------------------
# Hz↔index round-trip — IC-7610 (segmented_bcd_index)
# ---------------------------------------------------------------------------


class TestIc7610FilterWidthRoundtrip:
    """IC-7610 SSB profile uses segmented BCD index encoding."""

    def test_ssb_segments_round_trip_at_segment_boundary(self) -> None:
        profile = resolve_radio_profile(model="IC-7610")
        rule = profile.resolve_filter_rule("USB")
        assert rule is not None
        assert rule.segments

        for hz in (50, 100, 250, 500, 600, 800, 1500, 2000, 2400, 3600):
            idx = filter_hz_to_index(hz, segments=rule.segments)
            assert filter_index_to_hz(idx, segments=rule.segments) == hz, (
                f"round-trip failed at {hz} Hz"
            )

    def test_index_round_trip_across_full_range(self) -> None:
        profile = resolve_radio_profile(model="IC-7610")
        rule = profile.resolve_filter_rule("USB")
        assert rule is not None

        # For every valid index, Hz→index→Hz is identity.
        for idx in range(0, 41):
            hz = filter_index_to_hz(idx, segments=rule.segments)
            assert filter_hz_to_index(hz, segments=rule.segments) == idx


# ---------------------------------------------------------------------------
# Hz↔index round-trip — FTX-1 (table_index)
# ---------------------------------------------------------------------------


class TestFtx1FilterWidthRoundtrip:
    """FTX-1 uses table-index encoding with mode-specific tables."""

    def test_usb_table_round_trip_at_table_entries(self) -> None:
        profile = load_rig(_RIGS_DIR / "ftx1.toml").to_profile()
        rule = profile.resolve_filter_rule("USB")
        assert rule is not None
        assert rule.table

        for hz in rule.table:
            idx = hz_to_table_index(hz, table=rule.table)
            assert table_index_to_hz(idx, table=rule.table) == hz, (
                f"round-trip failed at {hz} Hz"
            )

    def test_full_index_round_trip(self) -> None:
        profile = load_rig(_RIGS_DIR / "ftx1.toml").to_profile()
        rule = profile.resolve_filter_rule("USB")
        assert rule is not None

        for idx in range(len(rule.table)):
            hz = table_index_to_hz(idx, table=rule.table)
            assert hz_to_table_index(hz, table=rule.table) == idx


# ---------------------------------------------------------------------------
# Protocol satisfaction
# ---------------------------------------------------------------------------


class TestDspControlCapableSatisfaction:
    """Both IcomRadio and YaesuCatRadio satisfy the extended DspControlCapable."""

    def test_icom_radio_is_dsp_control_capable(self) -> None:
        radio = IcomRadio(host="127.0.0.1", username="x", password="y")
        assert isinstance(radio, DspControlCapable)

    def test_yaesu_cat_radio_is_dsp_control_capable(self) -> None:
        config = load_rig(_RIGS_DIR / "ftx1.toml")
        radio = YaesuCatRadio("/dev/null", profile=config)
        assert isinstance(radio, DspControlCapable)

    def test_protocol_in_all(self) -> None:
        from icom_lan import radio_protocol

        assert "DspControlCapable" in radio_protocol.__all__

    def test_new_methods_present_on_protocol(self) -> None:
        # Verify the protocol surface contains the methods added in #1101.
        for name in (
            "get_filter",
            "get_filter_width",
            "set_filter_width",
            "get_agc",
        ):
            assert hasattr(DspControlCapable, name), f"missing {name!r}"


# ---------------------------------------------------------------------------
# IcomRadio backend behaviour — Hz↔index encoding
# ---------------------------------------------------------------------------


def _connected_icom(*, model: str | None = None) -> IcomRadio:
    """Build a minimally-connected IcomRadio for unit tests."""
    kwargs: dict[str, str] = {}
    if model is not None:
        kwargs["model"] = model
    radio = IcomRadio(host="127.0.0.1", username="x", password="y", **kwargs)
    # Bypass _check_connected without touching transport internals.
    radio._civ_runtime._check_connected = lambda: None  # type: ignore[method-assign]
    radio._civ_runtime._connected = True  # type: ignore[attr-defined]
    return radio


@pytest.mark.asyncio
async def test_icom_set_filter_width_translates_hz_to_bcd_cmd29() -> None:
    """IC-7610: Hz → index → 1-byte BCD wrapped in cmd29 frame (P2-04)."""
    radio = _connected_icom()
    radio.send_civ = AsyncMock()  # type: ignore[method-assign]
    # Default mode is USB → segmented rule; 1500 Hz → index 19 → BCD 0x19.
    radio._radio_state.main.mode = "USB"

    await radio.set_filter_width(1500, receiver=0)

    radio.send_civ.assert_awaited_once_with(
        0x29, data=b"\x00\x1a\x03\x19", wait_response=False
    )


@pytest.mark.asyncio
async def test_icom_set_filter_width_routes_sub_via_cmd29() -> None:
    """SUB receiver routing via cmd29 prefix (rx byte 0x01)."""
    radio = _connected_icom()
    radio.send_civ = AsyncMock()  # type: ignore[method-assign]
    radio._radio_state.sub.mode = "USB"

    await radio.set_filter_width(1500, receiver=1)

    radio.send_civ.assert_awaited_once_with(
        0x29, data=b"\x01\x1a\x03\x19", wait_response=False
    )


@pytest.mark.asyncio
async def test_icom_set_filter_width_rejects_out_of_range() -> None:
    """Bounds enforcement happens inside the backend (P2-04)."""
    from icom_lan.exceptions import CommandError

    radio = _connected_icom()
    radio.send_civ = AsyncMock()  # type: ignore[method-assign]
    radio._radio_state.main.mode = "USB"

    with pytest.raises(CommandError):
        await radio.set_filter_width(20, receiver=0)
    radio.send_civ.assert_not_awaited()


# ---------------------------------------------------------------------------
# get_filter_width — branches on profile.filter_width_encoding (issue #1145)
# ---------------------------------------------------------------------------


class TestIcomGetFilterWidthProfileBranching:
    """get_filter_width must branch on encoding, mirroring set_filter_width.

    Regression for #1145: prior code always used a cmd29-wrapped 1-byte BCD
    GET, which broke ``direct_bcd_hz`` profiles (IC-705, IC-9700) — multi-byte
    BCD widths like 2400 Hz were truncated to 24.
    """

    @pytest.mark.asyncio
    async def test_ic7610_segmented_index_request_is_cmd29_wrapped(self) -> None:
        """IC-7610 (segmented_bcd_index): request frame is cmd29-wrapped."""
        radio = _connected_icom(model="IC-7610")
        captured: dict[str, bytes] = {}

        async def fake_expect(civ: bytes, **_: object) -> CivFrame:
            captured["civ"] = civ
            # 1-byte BCD 0x20 = decimal 20 = USB segment index 20 → 1600 Hz.
            return CivFrame(
                to_addr=0xE0, from_addr=0x98, command=0x1A, sub=0x03, data=b"\x20"
            )

        radio._send_civ_expect = fake_expect  # type: ignore[method-assign]
        radio._radio_state.main.mode = "USB"

        hz = await radio.get_filter_width(receiver=0)
        # Wire frame: cmd29-wrapped (0x29 + receiver=0x00 + 0x1A 0x03).
        assert captured["civ"].hex() == "fefe98e029001a03fd"
        # Decoded: BCD 0x20 → index 20 → USB segment 600 + (20 - 10) * 100 = 1600 Hz.
        assert hz == 1600

    @pytest.mark.asyncio
    async def test_ic705_direct_bcd_hz_request_is_not_cmd29_wrapped(self) -> None:
        """IC-705 (direct_bcd_hz): request frame is direct, NOT cmd29-wrapped."""
        radio = _connected_icom(model="IC-705")
        captured: dict[str, bytes] = {}

        async def fake_expect(civ: bytes, **_: object) -> CivFrame:
            captured["civ"] = civ
            # 2-byte BCD: 0x24 0x00 = 2400 Hz (raw Hz, not index).
            return CivFrame(
                to_addr=0xE0,
                from_addr=0xA4,
                command=0x1A,
                sub=0x03,
                data=b"\x24\x00",
            )

        radio._send_civ_expect = fake_expect  # type: ignore[method-assign]

        hz = await radio.get_filter_width(receiver=0)
        # Wire frame: direct 0x1A 0x03 GET with no cmd29 wrap, no receiver byte.
        assert captured["civ"].hex() == "fefea4e01a03fd"
        # Decoded: 2-byte BCD 0x24 0x00 → 2400 Hz (regression: was 24 before fix).
        assert hz == 2400

    @pytest.mark.asyncio
    async def test_ic9700_direct_bcd_hz_request_is_not_cmd29_wrapped(self) -> None:
        """IC-9700 (direct_bcd_hz, no cmd29 support): direct GET frame."""
        radio = _connected_icom(model="IC-9700")
        captured: dict[str, bytes] = {}

        async def fake_expect(civ: bytes, **_: object) -> CivFrame:
            captured["civ"] = civ
            return CivFrame(
                to_addr=0xE0,
                from_addr=0xA2,
                command=0x1A,
                sub=0x03,
                data=b"\x24\x00",
            )

        radio._send_civ_expect = fake_expect  # type: ignore[method-assign]

        hz = await radio.get_filter_width(receiver=0)
        # Wire frame: direct GET (IC-9700 has no cmd29 at all per profile).
        assert captured["civ"].hex() == "fefea2e01a03fd"
        assert hz == 2400


# ---------------------------------------------------------------------------
# YaesuCatRadio — Hz↔index translation in set/get_filter_width
# ---------------------------------------------------------------------------


@pytest.fixture()
def ftx1_radio() -> YaesuCatRadio:
    config = load_rig(_RIGS_DIR / "ftx1.toml")
    radio = YaesuCatRadio("/dev/null", profile=config)
    radio._transport._connected = True
    return radio


@pytest.mark.asyncio
async def test_yaesu_set_filter_width_translates_hz_to_index(
    ftx1_radio: YaesuCatRadio,
) -> None:
    """FTX-1 USB table: 2400 Hz lives at index 12."""
    ftx1_radio._transport.write = AsyncMock()  # type: ignore[method-assign]
    await ftx1_radio.set_filter_width(2400)
    ftx1_radio._transport.write.assert_called_once_with("SH0012;")


@pytest.mark.asyncio
async def test_yaesu_get_filter_width_translates_index_to_hz(
    ftx1_radio: YaesuCatRadio,
) -> None:
    """FTX-1 USB table: index 12 → 2400 Hz."""
    ftx1_radio._transport.query = AsyncMock(return_value="SH0012")
    assert await ftx1_radio.get_filter_width() == 2400


@pytest.mark.asyncio
async def test_yaesu_filter_width_round_trip(ftx1_radio: YaesuCatRadio) -> None:
    """Hz set then get returns same Hz (round-trip)."""
    ftx1_radio._transport.write = AsyncMock()  # type: ignore[method-assign]
    captured: dict[str, str] = {}

    async def fake_write(cmd: str) -> None:
        captured["cmd"] = cmd

    ftx1_radio._transport.write = fake_write  # type: ignore[method-assign]
    await ftx1_radio.set_filter_width(2400)

    # Use the captured command's index payload as the response stub.
    # Format: "SH0{code:03d};" so payload is chars [3:6].
    code = captured["cmd"][3:6]
    ftx1_radio._transport.query = AsyncMock(return_value=f"SH0{code}")
    assert await ftx1_radio.get_filter_width() == 2400


# ---------------------------------------------------------------------------
# get_filter receiver param fix (P3-04)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_icom_get_filter_accepts_receiver_param() -> None:
    """IcomRadio.get_filter must accept ``receiver`` (P3-04)."""
    radio = _connected_icom()
    radio.get_mode_info = AsyncMock(return_value=("USB", 2))  # type: ignore[method-assign]

    assert await radio.get_filter(receiver=0) == 2
    assert await radio.get_filter(receiver=1) == 2

    # Receiver param is propagated to get_mode_info.
    radio.get_mode_info.assert_awaited_with(receiver=1)


@pytest.mark.asyncio
async def test_icom_get_filter_sub_no_fallback_to_main_cache() -> None:
    """SUB never returns MAIN's legacy ``_filter_width`` cache."""
    radio = _connected_icom()
    radio.get_mode_info = AsyncMock(return_value=("USB", None))  # type: ignore[method-assign]
    radio._filter_width = 2  # MAIN-only legacy cache

    assert await radio.get_filter(receiver=0) == 2  # MAIN fallback OK
    assert await radio.get_filter(receiver=1) is None  # SUB does not borrow MAIN


# ---------------------------------------------------------------------------
# rigctld filter-width round-trip
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rigctld_filter_width_passband_round_trip() -> None:
    """rigctld set_mode → get_mode passband round-trip (smoke)."""
    from icom_lan.rigctld.contract import RigctldCommand, RigctldConfig
    from icom_lan.rigctld.handler import RigctldHandler

    class _Stub:
        def __init__(self) -> None:
            self.mode: str = "USB"
            self.filt: int | None = None
            self.data_mode: bool = False
            self.radio_state = SimpleNamespace(
                main=SimpleNamespace(freq=0, mode="", filter=None, data_mode=0)
            )

        async def get_mode(self, receiver: int = 0) -> tuple[str, int | None]:
            return self.mode, self.filt

        async def set_mode(
            self,
            mode: str,
            filter_width: int | None = None,
            receiver: int = 0,
        ) -> None:
            self.mode = mode
            self.filt = filter_width

        async def get_data_mode(self) -> bool:
            return self.data_mode

        async def set_data_mode(self, on: bool) -> None:
            self.data_mode = on

    radio = _Stub()
    handler = RigctldHandler(radio, RigctldConfig(cache_ttl=0.0))

    # Set mode USB with passband 2400 Hz → filter 2.
    set_resp = await handler.execute(
        RigctldCommand(
            short_cmd="M",
            long_cmd="set_mode",
            args=("USB", "2400"),
            is_set=True,
        )
    )
    assert set_resp.ok
    assert radio.filt == 2

    # Reading mode back yields the matching passband (2400 Hz).
    get_resp = await handler.execute(
        RigctldCommand(
            short_cmd="m",
            long_cmd="get_mode",
            args=(),
            is_set=False,
        )
    )
    assert get_resp.ok
    assert get_resp.values[0] == "USB"
    assert get_resp.values[1] == "2400"
