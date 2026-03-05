"""icom-lan: Python library for controlling Icom transceivers over LAN."""

__version__ = "0.11.0"

from .auth import (
    AuthResponse,
    StatusResponse,
    build_conninfo_packet,
    build_login_packet,
    encode_credentials,
    parse_auth_response,
    parse_status_response,
)
from .exceptions import (
    AudioCodecBackendError,
    AudioError,
    AudioFormatError,
    AudioTranscodeError,
    AuthenticationError,
    CommandError,
    ConnectionError,
    IcomLanError,
    TimeoutError,
)
from .protocol import identify_packet_type, parse_header, serialize_header
from .audio import (
    AUDIO_HEADER_SIZE,
    AudioPacket,
    AudioState,
    AudioStats,
    AudioStream,
    JitterBuffer,
)
from .transport import ConnectionState, IcomTransport
from ._connection_state import RadioConnectionState
from .commander import IcomCommander, Priority
from .radio import AudioRecoveryState, IcomRadio
from .radio_protocol import AudioCapable, DualReceiverCapable, Radio, ScopeCapable
from .radio_state import RadioState
from .profiles import RadioProfile, get_radio_profile, resolve_radio_profile
from .radios import RADIOS, RadioModel, get_civ_addr
from .backends import BackendConfig, LanBackendConfig, SerialBackendConfig, create_radio
from .commands import (
    CONTROLLER_ADDR,
    IC_7610_ADDR,
    RECEIVER_MAIN,
    RECEIVER_SUB,
    build_civ_frame,
    build_cmd29_frame,
    get_alc,
    get_attenuator,
    get_frequency,
    get_mode,
    get_power,
    get_preamp,
    get_s_meter,
    get_swr,
    parse_ack_nak,
    parse_civ_frame,
    parse_frequency_response,
    parse_meter_response,
    parse_mode_response,
    ptt_off,
    ptt_on,
    scope_data_output_off,
    scope_data_output_on,
    scope_main_sub,
    scope_off,
    scope_on,
    scope_single_dual,
    set_attenuator,
    set_attenuator_level,
    set_frequency,
    set_mode,
    set_power,
    get_rf_gain,
    set_rf_gain,
    get_af_level,
    set_af_level,
    set_preamp,
)
from .scope import ScopeAssembler, ScopeFrame

# scope_render is an optional dep (Pillow); import lazily to avoid hard crash
try:
    from .scope_render import (  # noqa: F401
        THEMES as SCOPE_THEMES,
        amplitude_to_color,
        render_scope_image,
        render_spectrum,
        render_waterfall,
    )
    _SCOPE_RENDER_AVAILABLE = True
except ImportError:
    _SCOPE_RENDER_AVAILABLE = False
from .types import (
    HEADER_SIZE,
    AudioCapabilities,
    AudioCodec,
    CivFrame,
    Mode,
    PacketHeader,
    PacketType,
    ScopeCompletionPolicy,
    bcd_decode,
    bcd_encode,
    get_audio_capabilities,
)

__all__ = [
    "__version__",
    # Radio
    "AudioRecoveryState",
    "IcomRadio",
    "IcomCommander",
    "RadioConnectionState",
    "Priority",
    # Protocol
    "Radio",
    "AudioCapable",
    "ScopeCapable",
    "DualReceiverCapable",
    # State
    "RadioState",
    "RadioProfile",
    "get_radio_profile",
    "resolve_radio_profile",
    # Radio models
    "RADIOS",
    "RadioModel",
    "get_civ_addr",
    "BackendConfig",
    "LanBackendConfig",
    "SerialBackendConfig",
    "create_radio",
    # Exceptions
    "IcomLanError",
    "ConnectionError",
    "AuthenticationError",
    "CommandError",
    "TimeoutError",
    "AudioError",
    "AudioCodecBackendError",
    "AudioFormatError",
    "AudioTranscodeError",
    # Types
    "PacketType",
    "Mode",
    "AudioCodec",
    "AudioCapabilities",
    "ScopeCompletionPolicy",
    "PacketHeader",
    "CivFrame",
    "HEADER_SIZE",
    "bcd_encode",
    "bcd_decode",
    "get_audio_capabilities",
    # Commands
    "IC_7610_ADDR",
    "CONTROLLER_ADDR",
    "RECEIVER_MAIN",
    "RECEIVER_SUB",
    "build_civ_frame",
    "build_cmd29_frame",
    "parse_civ_frame",
    "get_frequency",
    "set_frequency",
    "get_mode",
    "set_mode",
    "get_power",
    "set_power",
    "get_rf_gain",
    "set_rf_gain",
    "get_af_level",
    "set_af_level",
    "get_s_meter",
    "get_swr",
    "get_alc",
    "get_attenuator",
    "set_attenuator",
    "set_attenuator_level",
    "get_preamp",
    "set_preamp",
    "ptt_on",
    "ptt_off",
    "parse_frequency_response",
    "parse_mode_response",
    "parse_meter_response",
    "parse_ack_nak",
    # Scope / Waterfall
    "ScopeAssembler",
    "ScopeFrame",
    # Scope rendering (optional — requires Pillow)
    "SCOPE_THEMES",
    "amplitude_to_color",
    "render_scope_image",
    "render_spectrum",
    "render_waterfall",
    "scope_on",
    "scope_off",
    "scope_data_output_on",
    "scope_data_output_off",
    "scope_main_sub",
    "scope_single_dual",
    # Protocol
    "parse_header",
    "serialize_header",
    "identify_packet_type",
    # Auth
    "AuthResponse",
    "StatusResponse",
    "encode_credentials",
    "build_login_packet",
    "build_conninfo_packet",
    "parse_auth_response",
    "parse_status_response",
    # Transport
    "ConnectionState",
    "IcomTransport",
    # Audio
    "AudioPacket",
    "AudioState",
    "AudioStats",
    "AudioStream",
    "JitterBuffer",
    "AUDIO_HEADER_SIZE",
]
