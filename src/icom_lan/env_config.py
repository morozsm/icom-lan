"""Environment variable configuration helpers for icom-lan.

Reads tunable parameters from the process environment so users on
high-latency or constrained links (VPN, cloud VMs) can adjust audio
and buffer behaviour without modifying code.
"""

import logging
import os

__all__ = [
    "get_audio_sample_rate",
    "get_audio_buffer_pool_size",
    "get_audio_broadcaster_high_watermark",
    "get_audio_client_high_watermark",
]

logger = logging.getLogger(__name__)

_SUPPORTED_SAMPLE_RATES = (8000, 16000, 24000, 48000)

_DEFAULTS: dict[str, int] = {
    "ICOM_AUDIO_SAMPLE_RATE": 48000,
    "ICOM_AUDIO_BUFFER_POOL_SIZE": 5,
    "ICOM_AUDIO_BROADCASTER_HIGH_WATERMARK": 10,
    "ICOM_AUDIO_CLIENT_HIGH_WATERMARK": 10,
}


def _read_positive_int(var: str) -> int:
    """Read *var* from the environment, validate it is a positive integer.

    Falls back to the default from ``_DEFAULTS`` and logs a warning when
    the value is absent, non-numeric, or not positive.
    """
    default = _DEFAULTS[var]
    raw = os.environ.get(var)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        logger.warning(
            "env_config: %s=%r is not a valid integer, using default %d",
            var,
            raw,
            default,
        )
        return default
    if value <= 0:
        logger.warning(
            "env_config: %s=%d must be > 0, using default %d",
            var,
            value,
            default,
        )
        return default
    return value


def get_audio_sample_rate() -> int:
    """Return the configured default audio sample rate in Hz.

    Reads ``ICOM_AUDIO_SAMPLE_RATE``.  The value must be one of the
    supported rates (8000, 16000, 24000, 48000).  Invalid values fall
    back to 48000 with a warning.
    """
    default = _DEFAULTS["ICOM_AUDIO_SAMPLE_RATE"]
    raw = os.environ.get("ICOM_AUDIO_SAMPLE_RATE")
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        logger.warning(
            "env_config: ICOM_AUDIO_SAMPLE_RATE=%r is not a valid integer, "
            "using default %d",
            raw,
            default,
        )
        return default
    if value not in _SUPPORTED_SAMPLE_RATES:
        logger.warning(
            "env_config: ICOM_AUDIO_SAMPLE_RATE=%d is not in supported rates %s, "
            "using default %d",
            value,
            _SUPPORTED_SAMPLE_RATES,
            default,
        )
        return default
    return value


def get_audio_buffer_pool_size() -> int:
    """Return the configured audio buffer pool size.

    Reads ``ICOM_AUDIO_BUFFER_POOL_SIZE``.  Must be a positive integer.
    """
    return _read_positive_int("ICOM_AUDIO_BUFFER_POOL_SIZE")


def get_audio_broadcaster_high_watermark() -> int:
    """Return the configured broadcaster HIGH_WATERMARK.

    Reads ``ICOM_AUDIO_BROADCASTER_HIGH_WATERMARK``.  Must be a positive integer.
    """
    return _read_positive_int("ICOM_AUDIO_BROADCASTER_HIGH_WATERMARK")


def get_audio_client_high_watermark() -> int:
    """Return the configured per-client audio HIGH_WATERMARK.

    Reads ``ICOM_AUDIO_CLIENT_HIGH_WATERMARK``.  Must be a positive integer.
    """
    return _read_positive_int("ICOM_AUDIO_CLIENT_HIGH_WATERMARK")
