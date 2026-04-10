"""Tests for IC-7300 backend initialization and profile routing."""


from icom_lan.backends.config import SerialBackendConfig
from icom_lan.backends.factory import create_radio
from icom_lan.backends.ic7300.serial import Ic7300SerialRadio


def test_ic7300_factory_creates_correct_backend():
    """Factory should route IC-7300 serial config to Ic7300SerialRadio."""
    config = SerialBackendConfig(
        device="/dev/ttyUSB0",
        model="IC-7300",
    )
    radio = create_radio(config)
    assert isinstance(radio, Ic7300SerialRadio)
    assert radio.model == "IC-7300"


def test_ic7300_factory_case_insensitive():
    """Factory should handle case-insensitive model names."""
    config = SerialBackendConfig(
        device="/dev/ttyUSB0",
        model="ic-7300",  # lowercase
    )
    radio = create_radio(config)
    assert isinstance(radio, Ic7300SerialRadio)


def test_ic7300_backend_default_model():
    """IC-7300 backend should default model to IC-7300."""
    radio = Ic7300SerialRadio(device="/dev/ttyUSB0")
    assert radio.model == "IC-7300"


def test_ic7300_profile_loading():
    """IC-7300 backend should load ic7300.toml profile."""
    radio = Ic7300SerialRadio(device="/dev/ttyUSB0", model="IC-7300")
    profile = radio._profile
    assert profile.model == "IC-7300"
    assert profile.civ_addr == 0x94  # IC-7300 CI-V address


def test_ic7300_serial_inherits_from_core():
    """Ic7300SerialRadio should inherit from CoreRadio."""
    radio = Ic7300SerialRadio(device="/dev/ttyUSB0")
    # Verify it has the expected methods and properties
    assert hasattr(radio, "connect")
    assert hasattr(radio, "disconnect")
    assert hasattr(radio, "get_frequency")
    assert hasattr(radio, "set_frequency")
    assert hasattr(radio, "enable_scope")
    assert hasattr(radio, "disable_scope")
