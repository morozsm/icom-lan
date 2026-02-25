"""icom-lan: Python library for controlling Icom transceivers over LAN."""

__version__ = "0.2.0"

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
    AuthenticationError,
    CommandError,
    ConnectionError,
    IcomLanError,
    TimeoutError,
)
from .protocol import identify_packet_type, parse_header, serialize_header
from .audio import AUDIO_HEADER_SIZE, AudioPacket, AudioState, AudioStream
from .transport import ConnectionState, IcomTransport
from .radio import IcomRadio
from .commands import (
    CONTROLLER_ADDR,
    IC_7610_ADDR,
    build_civ_frame,
    get_alc,
    get_frequency,
    get_mode,
    get_power,
    get_s_meter,
    get_swr,
    parse_ack_nak,
    parse_civ_frame,
    parse_frequency_response,
    parse_meter_response,
    parse_mode_response,
    ptt_off,
    ptt_on,
    set_frequency,
    set_mode,
    set_power,
)
from .types import (
    HEADER_SIZE,
    CivFrame,
    Mode,
    PacketHeader,
    PacketType,
    bcd_decode,
    bcd_encode,
)

__all__ = [
    "__version__",
    # Radio
    "IcomRadio",
    # Exceptions
    "IcomLanError",
    "ConnectionError",
    "AuthenticationError",
    "CommandError",
    "TimeoutError",
    # Types
    "PacketType",
    "Mode",
    "PacketHeader",
    "CivFrame",
    "HEADER_SIZE",
    "bcd_encode",
    "bcd_decode",
    # Commands
    "IC_7610_ADDR",
    "CONTROLLER_ADDR",
    "build_civ_frame",
    "parse_civ_frame",
    "get_frequency",
    "set_frequency",
    "get_mode",
    "set_mode",
    "get_power",
    "set_power",
    "get_s_meter",
    "get_swr",
    "get_alc",
    "ptt_on",
    "ptt_off",
    "parse_frequency_response",
    "parse_mode_response",
    "parse_meter_response",
    "parse_ack_nak",
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
    "AudioStream",
    "AUDIO_HEADER_SIZE",
]
