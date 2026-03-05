"""Backend factory for assembling radio implementations from typed config."""

from __future__ import annotations

from ..radio import IcomRadio
from .config import BackendConfig, LanBackendConfig, SerialBackendConfig


def create_radio(config: BackendConfig) -> IcomRadio:
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
        )
    if isinstance(config, SerialBackendConfig):
        raise NotImplementedError(
            "Serial backend is not implemented yet. "
            "Use LanBackendConfig/backend='lan' for now."
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
