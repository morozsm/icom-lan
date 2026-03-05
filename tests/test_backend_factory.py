"""Smoke tests for backend config/contracts/factory foundation layer."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from icom_lan import IcomRadio, create_radio
from icom_lan.backends.config import LanBackendConfig, SerialBackendConfig
from icom_lan.backends.icom7610.drivers.contracts import AudioDriver, CivLink, SessionDriver


class TestBackendConfigValidation:
    def test_lan_backend_defaults(self) -> None:
        config = LanBackendConfig(host="192.168.55.40")
        assert config.backend == "lan"
        assert config.port == 50001
        assert config.radio_addr is None

    def test_lan_backend_host_required(self) -> None:
        with pytest.raises(ValueError, match="host"):
            LanBackendConfig(host="")

    def test_serial_backend_port_required(self) -> None:
        with pytest.raises(ValueError, match="device"):
            SerialBackendConfig(device="")


class TestCreateRadioFactory:
    def test_create_radio_builds_lan_backend(self) -> None:
        radio = create_radio(LanBackendConfig(host="192.168.55.40", username="u", password="p"))
        assert isinstance(radio, IcomRadio)
        assert radio.model == "IC-7610"

    def test_create_radio_uses_profile_civ_addr_when_model_provided(self) -> None:
        radio = create_radio(LanBackendConfig(host="192.168.55.40", model="IC-7300"))
        assert isinstance(radio, IcomRadio)
        assert radio.model == "IC-7300"
        assert radio._radio_addr == 0x94

    def test_create_radio_serial_stub_is_actionable(self) -> None:
        with pytest.raises(NotImplementedError, match="Serial backend is not implemented yet"):
            create_radio(SerialBackendConfig(device="/dev/ttyUSB0"))

    def test_create_radio_rejects_unknown_backend(self) -> None:
        @dataclass(slots=True)
        class _UnknownConfig:
            backend: str = "bluetooth"

        with pytest.raises(ValueError, match="Unsupported backend"):
            create_radio(_UnknownConfig())  # type: ignore[arg-type]


class TestContracts:
    def test_minimal_session_contract_shape(self) -> None:
        class _Session:
            async def connect(self) -> None:
                return None

            async def disconnect(self) -> None:
                return None

            @property
            def connected(self) -> bool:
                return True

        assert isinstance(_Session(), SessionDriver)

    def test_minimal_civ_contract_shape(self) -> None:
        class _Civ:
            async def send(self, frame: bytes) -> None:
                return None

            async def receive(self, timeout: float | None = None) -> bytes | None:
                return frame if (frame := b"x") else None

        assert isinstance(_Civ(), CivLink)

    def test_minimal_audio_contract_shape(self) -> None:
        class _Audio:
            async def start_rx(self) -> None:
                return None

            async def stop_rx(self) -> None:
                return None

            async def start_tx(self) -> None:
                return None

            async def stop_tx(self) -> None:
                return None

        assert isinstance(_Audio(), AudioDriver)
