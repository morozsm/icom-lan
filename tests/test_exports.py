"""Public package export tests."""

import icom_lan
from icom_lan import AudioCodecBackendError, AudioFormatError, ScopeCompletionPolicy


def test_scope_completion_policy_exported() -> None:
    assert ScopeCompletionPolicy.VERIFY.value == "verify"


def test_audio_errors_exported() -> None:
    assert issubclass(AudioCodecBackendError, Exception)
    assert issubclass(AudioFormatError, Exception)


def test_advanced_top_level_reexports_are_in___all__() -> None:
    expected = {
        "AuthResponse",
        "StatusResponse",
        "build_conninfo_packet",
        "build_login_packet",
        "parse_auth_response",
        "parse_status_response",
        "identify_packet_type",
        "parse_header",
        "serialize_header",
        "AudioPacket",
        "AudioState",
        "AudioStats",
        "AudioStream",
        "JitterBuffer",
        "IcomTransport",
        "ConnectionState",
        "IcomCommander",
        "Priority",
        "CONTROLLER_ADDR",
        "IC_7610_ADDR",
        "RECEIVER_MAIN",
        "RECEIVER_SUB",
        "build_civ_frame",
        "parse_civ_frame",
        "ScopeAssembler",
        "ScopeFrame",
        "HEADER_SIZE",
        "AudioCapabilities",
        "AudioCodec",
        "CivFrame",
        "PacketHeader",
        "PacketType",
        "ScopeCompletionPolicy",
        "ScopeFixedEdge",
        "bcd_encode",
        "bcd_decode",
        "get_audio_capabilities",
    }
    assert expected.issubset(set(icom_lan.__all__))
