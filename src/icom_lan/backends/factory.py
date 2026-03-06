"""Backend factory for assembling radio implementations from typed config."""

from __future__ import annotations

from ..radio import IcomRadio
from ..radio_protocol import Radio
from .config import BackendConfig, LanBackendConfig, SerialBackendConfig
from .icom7610.serial import Icom7610SerialRadio


def create_radio(config: BackendConfig) -> Radio:
    """Create a radio instance for the selected backend config."""
    if isinstance(config, LanBackendConfig):
        return IcomRadio(
            host=config.host,
            port=config.port,
            username=config.username,
            password=config.password,
            radio_addr=config.radio_addr,
            timeout=config.timeout,
            audio_codec=config.audio_codec,
            audio_sample_rate=config.audio_sample_rate,
            auto_reconnect=config.auto_reconnect,
            reconnect_delay=config.reconnect_delay,
            reconnect_max_delay=config.reconnect_max_delay,
            watchdog_timeout=config.watchdog_timeout,
            auto_recover_audio=config.auto_recover_audio,
            cache_ttl_s=config.cache_ttl_s,
            profile=config.profile,
            model=config.model,
        )
    if isinstance(config, SerialBackendConfig):
        return Icom7610SerialRadio(
            device=config.device,
            baudrate=config.baudrate,
            radio_addr=config.radio_addr,
            timeout=config.timeout,
            audio_codec=config.audio_codec,
            audio_sample_rate=config.audio_sample_rate,
            rx_device=config.rx_device,
            tx_device=config.tx_device,
            profile=config.profile,
            model=config.model,
        )

    backend = getattr(config, "backend", None)
    if backend in {"lan", "serial"}:
        raise TypeError(
            "Unsupported config instance for backend "
            f"{backend!r}; use typed backend config dataclasses."
        )
    raise ValueError(
        "Unsupported backend. Expected backend 'lan' or 'serial'."
    )


__all__ = ["create_radio"]
