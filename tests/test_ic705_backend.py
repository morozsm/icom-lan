"""Tests for IC-705 backend initialization and profile routing."""

import pytest

from icom_lan.backends.config import SerialBackendConfig
from icom_lan.backends.factory import create_radio
from icom_lan.backends.ic705.serial import Ic705SerialRadio
from icom_lan.backends.icom7610.serial import Icom7610SerialRadio


def test_ic705_factory_creates_correct_backend():
    """Factory should route IC-705 serial config to Ic705SerialRadio."""
    config = SerialBackendConfig(
        device="/dev/ttyUSB0",
        model="IC-705",
    )
    radio = create_radio(config)
    assert isinstance(radio, Ic705SerialRadio)
    assert radio.model == "IC-705"


def test_ic7610_factory_creates_correct_backend():
    """Factory should route IC-7610 serial config to Icom7610SerialRadio."""
    config = SerialBackendConfig(
        device="/dev/ttyUSB0",
        model="IC-7610",
    )
    radio = create_radio(config)
    assert isinstance(radio, Icom7610SerialRadio)
    assert not isinstance(radio, Ic705SerialRadio)


def test_ic705_backend_default_model():
    """IC-705 backend should default model to IC-705."""
    radio = Ic705SerialRadio(device="/dev/ttyUSB0")
    assert radio.model == "IC-705"


def test_ic705_profile_loading():
    """IC-705 backend should load ic705.toml profile."""
    radio = Ic705SerialRadio(device="/dev/ttyUSB0", model="IC-705")
    profile = radio._profile
    assert profile.model == "IC-705"
    assert profile.civ_addr == 0xA4  # IC-705 CI-V address


def test_ic705_serial_inherits_from_core():
    """Ic705SerialRadio should inherit from Icom7610CoreRadio."""
    radio = Ic705SerialRadio(device="/dev/ttyUSB0")
    # Verify it has the expected methods and properties
    assert hasattr(radio, "connect")
    assert hasattr(radio, "disconnect")
    assert hasattr(radio, "get_frequency")
    assert hasattr(radio, "set_frequency")
    assert hasattr(radio, "enable_scope")
    assert hasattr(radio, "disable_scope")
