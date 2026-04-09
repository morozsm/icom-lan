"""Public package export tests."""

import icom_lan
from icom_lan import AudioCodecBackendError, AudioFormatError, ScopeCompletionPolicy


def test_scope_completion_policy_exported() -> None:
    assert ScopeCompletionPolicy.VERIFY.value == "verify"


def test_audio_errors_exported() -> None:
    assert issubclass(AudioCodecBackendError, Exception)
    assert issubclass(AudioFormatError, Exception)


def test_public_api_surface() -> None:
    """__all__ contains only the trimmed public API (~30 symbols)."""
    expected_public = {
        "__version__",
        # Factory
        "create_radio",
        # Backend configs
        "BackendConfig",
        "LanBackendConfig",
        "SerialBackendConfig",
        "YaesuCatBackendConfig",
        # Radio protocol + capabilities
        "Radio",
        "AudioCapable",
        "ScopeCapable",
        "DualReceiverCapable",
        "LevelsCapable",
        "MetersCapable",
        "PowerControlCapable",
        "StateNotifyCapable",
        "CivCommandCapable",
        "ModeInfoCapable",
        "RecoverableConnection",
        "AdvancedControlCapable",
        "StateCacheCapable",
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
        # Public types
        "Mode",
        "AudioCodec",
        "RadioState",
        "RadioProfile",
        # Backward compat
        "IcomRadio",
    }
    assert set(icom_lan.__all__) == expected_public


def test_internal_symbols_still_importable() -> None:
    """Internal symbols removed from __all__ are still importable by name."""
    internal_symbols = [
        "build_civ_frame",
        "parse_civ_frame",
        "bcd_encode",
        "bcd_decode",
        "IC_7610_ADDR",
        "CONTROLLER_ADDR",
        "RECEIVER_MAIN",
        "RECEIVER_SUB",
        "IcomTransport",
        "IcomCommander",
        "ScopeAssembler",
        "ScopeFrame",
        "PacketHeader",
        "PacketType",
        "CivFrame",
        "AudioCapabilities",
        "get_audio_capabilities",
        "ScopeCompletionPolicy",
        "ScopeFixedEdge",
        "HEADER_SIZE",
    ]
    for name in internal_symbols:
        assert hasattr(icom_lan, name), f"{name} should still be importable from icom_lan"
        assert name not in icom_lan.__all__, f"{name} should NOT be in __all__"
