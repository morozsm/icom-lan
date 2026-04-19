"""Tests for IC-9700 backend initialization, profile routing, and dual-receiver support."""

from icom_lan.backends.config import SerialBackendConfig
from icom_lan.backends.factory import create_radio
from icom_lan.backends.ic9700.serial import Ic9700SerialRadio


def test_ic9700_factory_creates_correct_backend():
    """Factory should route IC-9700 serial config to Ic9700SerialRadio."""
    config = SerialBackendConfig(
        device="/dev/ttyUSB0",
        model="IC-9700",
    )
    radio = create_radio(config)
    assert isinstance(radio, Ic9700SerialRadio)
    assert radio.model == "IC-9700"


def test_ic9700_factory_case_insensitive():
    """Factory should handle case-insensitive model names for IC-9700."""
    config = SerialBackendConfig(
        device="/dev/ttyUSB0",
        model="ic-9700",  # lowercase
    )
    radio = create_radio(config)
    assert isinstance(radio, Ic9700SerialRadio)


def test_ic9700_backend_default_model():
    """IC-9700 backend should default model to IC-9700."""
    radio = Ic9700SerialRadio(device="/dev/ttyUSB0")
    assert radio.model == "IC-9700"


def test_ic9700_profile_loading():
    """IC-9700 backend should load ic9700.toml profile with dual-receiver support."""
    radio = Ic9700SerialRadio(device="/dev/ttyUSB0", model="IC-9700")
    profile = radio._profile
    assert profile.model == "IC-9700"
    assert profile.civ_addr == 0xA2  # IC-9700 CI-V address
    assert profile.receiver_count == 2  # Dual receiver support
    assert profile.has_lan is True  # LAN-capable


def test_ic9700_dual_receiver_capability():
    """IC-9700 should support dual receivers (unique to IC-9700)."""
    radio = Ic9700SerialRadio(device="/dev/ttyUSB0", model="IC-9700")
    profile = radio._profile
    # IC-9700 is the only currently supported radio with dual receivers
    assert profile.receiver_count == 2
    # Compare with IC-7300 (single receiver)
    from icom_lan.backends.ic7300.serial import Ic7300SerialRadio

    ic7300 = Ic7300SerialRadio(device="/dev/ttyUSB0", model="IC-7300")
    assert ic7300._profile.receiver_count == 1


def test_ic9700_serial_inherits_from_core():
    """Ic9700SerialRadio should inherit from CoreRadio."""
    radio = Ic9700SerialRadio(device="/dev/ttyUSB0")
    # Verify it has the expected methods and properties
    assert hasattr(radio, "connect")
    assert hasattr(radio, "disconnect")
    assert hasattr(radio, "get_frequency")
    assert hasattr(radio, "set_frequency")
    assert hasattr(radio, "enable_scope")
    assert hasattr(radio, "disable_scope")
