"""icom-lan: Python library for controlling Icom transceivers over LAN."""

__version__ = "0.1.0"

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
from .transport import ConnectionState, IcomTransport
from .types import (
    HEADER_SIZE,
    Mode,
    PacketHeader,
    PacketType,
    bcd_decode,
    bcd_encode,
)

__all__ = [
    "__version__",
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
    "HEADER_SIZE",
    "bcd_encode",
    "bcd_decode",
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
]
