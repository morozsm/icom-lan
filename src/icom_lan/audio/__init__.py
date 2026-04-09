"""Universal audio subsystem for icom-lan.

Provides:
- LAN audio streaming (IC-7610 UDP) — from :mod:`.lan_stream`
- USB audio device driver (all serial radios) — from :mod:`.usb_driver`
"""

# LAN audio (backward compat — was icom_lan.audio module)
from .lan_stream import (  # noqa: F401
    AUDIO_HEADER_SIZE,
    AudioPacket,
    AudioState,
    AudioStats,
    AudioStream,
    JitterBuffer,
    MAX_AUDIO_PAYLOAD,
    RX_IDENT_0xA0,
    TX_IDENT,
    build_audio_packet,
    parse_audio_packet,
)

# Audio backend abstraction (protocol + implementations)
from .backend import (  # noqa: F401
    AudioBackend,
    AudioDeviceId,
    AudioDeviceInfo,
    FakeAudioBackend,
    FakeRxStream,
    FakeTxStream,
    PortAudioBackend,
    RxStream,
    TxStream,
)

# Configuration
from .config import (  # noqa: F401
    AudioConfig,
    load_audio_config,
    save_audio_config,
)

# DSP pipeline
from .dsp import (  # noqa: F401
    DspPipeline,
    DspStage,
    Limiter,
    NoiseGate,
    RmsNormalizer,
)

# Resampling
from .resample import (  # noqa: F401
    PcmResampler,
    SampleRateNegotiation,
    negotiate_sample_rate,
)

# USB audio driver (moved from icom7610/drivers/)
from .usb_driver import (  # noqa: F401
    AudioDeviceSelectionError,
    AudioDriverLifecycleError,
    UsbAudioDevice,
    UsbAudioDriver,
    list_usb_audio_devices,
    select_usb_audio_devices,
)

__all__ = [
    # Audio backend abstraction
    "AudioBackend",
    "AudioDeviceId",
    "AudioDeviceInfo",
    "FakeAudioBackend",
    "FakeRxStream",
    "FakeTxStream",
    "PortAudioBackend",
    "RxStream",
    "TxStream",
    # LAN audio
    "AUDIO_HEADER_SIZE",
    "AudioPacket",
    "AudioState",
    "AudioStats",
    "AudioStream",
    "JitterBuffer",
    "MAX_AUDIO_PAYLOAD",
    "RX_IDENT_0xA0",
    "build_audio_packet",
    "parse_audio_packet",
    "TX_IDENT",
    # DSP
    "DspPipeline",
    "DspStage",
    "Limiter",
    "NoiseGate",
    "RmsNormalizer",
    # Resampling
    "PcmResampler",
    "SampleRateNegotiation",
    "negotiate_sample_rate",
    # USB audio
    "AudioDeviceSelectionError",
    "AudioDriverLifecycleError",
    "UsbAudioDevice",
    "UsbAudioDriver",
    "list_usb_audio_devices",
    "select_usb_audio_devices",
]
