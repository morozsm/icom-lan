"""Tests for Main/Sub Tracking command (CI-V 0x16 0x5E)."""

import icom_lan.commands as raw_commands

from icom_lan import IC_7610_ADDR
from icom_lan.commands import (
    get_main_sub_tracking,
    set_main_sub_tracking,
    parse_civ_frame
)
from _command_test_helpers import bind_default_addr_globals, bind_default_addr_module

bind_default_addr_module(raw_commands, to_addr=IC_7610_ADDR)
bind_default_addr_globals(globals(), to_addr=IC_7610_ADDR)


class TestGetMainSubTracking:
    """Test get_main_sub_tracking frame builder."""

    def test_get_frame_bytes(self) -> None:
        frame = get_main_sub_tracking()
        # CI-V: FE FE 98 E0 16 5E FD
        assert frame == b"\xfe\xfe\x98\xe0\x16\x5e\xfd"

    def test_get_frame_custom_addr(self) -> None:
        frame = get_main_sub_tracking(to_addr=0x94, from_addr=0xE1)
        assert frame == b"\xfe\xfe\x94\xe1\x16\x5e\xfd"

    def test_get_frame_parsed(self) -> None:
        frame = get_main_sub_tracking()
        parsed = parse_civ_frame(frame)
        assert parsed.command == 0x16
        assert parsed.sub == 0x5E
        assert parsed.data == b""


class TestSetMainSubTracking:
    """Test set_main_sub_tracking frame builder."""

    def test_set_on_frame_bytes(self) -> None:
        frame = set_main_sub_tracking(True)
        # CI-V: FE FE 98 E0 16 5E 01 FD
        assert frame == b"\xfe\xfe\x98\xe0\x16\x5e\x01\xfd"

    def test_set_off_frame_bytes(self) -> None:
        frame = set_main_sub_tracking(False)
        # CI-V: FE FE 98 E0 16 5E 00 FD
        assert frame == b"\xfe\xfe\x98\xe0\x16\x5e\x00\xfd"

    def test_set_on_parsed(self) -> None:
        frame = set_main_sub_tracking(True)
        parsed = parse_civ_frame(frame)
        assert parsed.command == 0x16
        assert parsed.sub == 0x5E
        assert parsed.data == b"\x01"

    def test_set_off_parsed(self) -> None:
        frame = set_main_sub_tracking(False)
        parsed = parse_civ_frame(frame)
        assert parsed.command == 0x16
        assert parsed.sub == 0x5E
        assert parsed.data == b"\x00"

    def test_set_custom_addr(self) -> None:
        frame = set_main_sub_tracking(True, to_addr=0x94, from_addr=0xE1)
        assert frame == b"\xfe\xfe\x94\xe1\x16\x5e\x01\xfd"


class TestMainSubTrackingState:
    """Test that RadioState and _CivRxMixin handle 0x16 0x5E frames."""

    def test_radio_state_has_field(self) -> None:
        from icom_lan.radio_state import RadioState

        rs = RadioState()
        assert hasattr(rs, "main_sub_tracking")
        assert rs.main_sub_tracking is False

    def test_radio_state_to_dict_includes_field(self) -> None:
        from icom_lan.radio_state import RadioState

        rs = RadioState()
        d = rs.to_dict()
        assert "main_sub_tracking" in d
        assert d["main_sub_tracking"] is False

    def test_radio_state_field_set(self) -> None:
        from icom_lan.radio_state import RadioState

        rs = RadioState()
        rs.main_sub_tracking = True
        assert rs.main_sub_tracking is True
