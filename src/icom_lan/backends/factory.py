"""Backend factory for assembling radio implementations from typed config."""

from __future__ import annotations

from ..radio import IcomRadio  # noqa: TID251
from ..radio_protocol import Radio
from .config import BackendConfig, LanBackendConfig, SerialBackendConfig
from .ic705.serial import Ic705SerialRadio
from .icom7610.serial import Icom7610SerialRadio


def create_radio(config: BackendConfig) -> Radio:
    """Create a radio instance for the selected backend config.

    Routes to model-specific backends for serial connections.
    For LAN, uses profile-driven routing (model parameter handled by IcomRadio).
    """
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
        # Route to model-specific serial backend
        model = config.model or "IC-7610"
        if model.upper() == "IC-705":
            serial_class = Ic705SerialRadio
        else:
            # Default to IC-7610 for compatibility
            serial_class = Icom7610SerialRadio

        return serial_class(
            device=config.device,
            baudrate=config.baudrate,
            radio_addr=config.radio_addr,
            timeout=config.timeout,
            audio_codec=config.audio_codec,
            audio_sample_rate=config.audio_sample_rate,
            rx_device=config.rx_device,
            tx_device=config.tx_device,
            ptt_mode=config.ptt_mode,
            allow_low_baud_scope=config.allow_low_baud_scope,
            profile=config.profile,
            model=config.model,
        )

    backend = getattr(config, "backend", None)
    if backend in {"lan", "serial"}:
        raise TypeError(
            "Unsupported config instance for backend "
            f"{backend!r}; use typed backend config dataclasses."
        )
    raise ValueError("Unsupported backend. Expected backend 'lan' or 'serial'.")


__all__ = ["create_radio"]
