"""Tests for radio model presets."""

import pytest

from icom_lan.radios import RADIOS, RadioModel, get_civ_addr


class TestRadioModels:
    def test_ic7610(self) -> None:
        r = RADIOS["IC-7610"]
        assert r.civ_addr == 0x98
        assert r.receivers == 2
        assert r.has_lan is True

    def test_ic705(self) -> None:
        r = RADIOS["IC-705"]
        assert r.civ_addr == 0xA4
        assert r.has_wifi is True

    def test_ic7300(self) -> None:
        r = RADIOS["IC-7300"]
        assert r.civ_addr == 0x94

    def test_ic9700(self) -> None:
        r = RADIOS["IC-9700"]
        assert r.civ_addr == 0xA2
        assert r.receivers == 2

    def test_icr8600(self) -> None:
        r = RADIOS["IC-R8600"]
        assert r.civ_addr == 0x96

    def test_all_have_lan(self) -> None:
        for name, r in RADIOS.items():
            assert r.has_lan, f"{name} should have LAN"


class TestGetCivAddr:
    def test_known_model(self) -> None:
        assert get_civ_addr("IC-7610") == 0x98
        assert get_civ_addr("IC-705") == 0xA4

    def test_case_insensitive(self) -> None:
        assert get_civ_addr("ic-7300") == 0x94

    def test_unknown_raises(self) -> None:
        with pytest.raises(KeyError, match="Unknown radio"):
            get_civ_addr("IC-FAKE")


class TestRadioModelDataclass:
    def test_frozen(self) -> None:
        r = RadioModel(name="Test", civ_addr=0x01)
        with pytest.raises(AttributeError):
            r.name = "Changed"  # type: ignore[misc]

    def test_defaults(self) -> None:
        r = RadioModel(name="Test", civ_addr=0x01)
        assert r.receivers == 1
        assert r.has_lan is True
        assert r.has_wifi is False
