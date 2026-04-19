"""Tests for optional audio.toml configuration."""

from __future__ import annotations

from pathlib import Path


from icom_lan.audio.config import (
    AudioConfig,
    BridgeConfig,
    BridgeReconnectConfig,
    UsbConfig,
    load_audio_config,
    save_audio_config,
)


def test_default_config():
    """Default AudioConfig has sensible defaults."""
    cfg = AudioConfig()
    assert cfg.bridge.device is None
    assert cfg.bridge.rx_only is False
    assert cfg.bridge.reconnect.max_retries == 5
    assert cfg.bridge.reconnect.retry_delay == 1.0
    assert cfg.usb.rx_device is None
    assert cfg.usb.last_rx_uid is None


def test_load_missing_file():
    """Loading from a non-existent path returns defaults."""
    cfg = load_audio_config("/nonexistent/audio.toml")
    assert cfg.bridge.device is None


def test_load_and_save_roundtrip(tmp_path: Path):
    """Save then load preserves config values."""
    original = AudioConfig(
        bridge=BridgeConfig(
            device="BlackHole 2ch",
            tx_device="BlackHole 16ch",
            rx_only=True,
            label="my-bridge",
            reconnect=BridgeReconnectConfig(max_retries=3, retry_delay=2.5),
        ),
        usb=UsbConfig(
            rx_device="USB Audio CODEC",
            tx_device="USB Audio CODEC",
            last_rx_uid="AppleUSBAudioEngine:foo:bar:1.0",
            last_tx_uid="AppleUSBAudioEngine:foo:bar:1.0",
        ),
    )

    path = tmp_path / "audio.toml"
    save_audio_config(original, path)
    assert path.exists()

    loaded = load_audio_config(path)
    assert loaded.bridge.device == "BlackHole 2ch"
    assert loaded.bridge.tx_device == "BlackHole 16ch"
    assert loaded.bridge.rx_only is True
    assert loaded.bridge.label == "my-bridge"
    assert loaded.bridge.reconnect.max_retries == 3
    assert loaded.bridge.reconnect.retry_delay == 2.5
    assert loaded.usb.rx_device == "USB Audio CODEC"
    assert loaded.usb.last_rx_uid == "AppleUSBAudioEngine:foo:bar:1.0"


def test_merge_cli_overrides():
    """CLI flags take precedence over config file values."""
    cfg = AudioConfig(
        bridge=BridgeConfig(
            device="BlackHole 2ch",
            reconnect=BridgeReconnectConfig(max_retries=5),
        ),
        usb=UsbConfig(rx_device="USB Audio CODEC"),
    )

    merged = cfg.merge_cli(
        bridge_device="Loopback Audio",
        bridge_max_retries=10,
    )

    # CLI overrode these
    assert merged.bridge.device == "Loopback Audio"
    assert merged.bridge.reconnect.max_retries == 10
    # Config preserved these (not overridden)
    assert merged.usb.rx_device == "USB Audio CODEC"
    assert merged.bridge.reconnect.retry_delay == 1.0  # default


def test_merge_cli_none_preserves_config():
    """Passing None for CLI args preserves config values."""
    cfg = AudioConfig(
        bridge=BridgeConfig(device="BlackHole 2ch"),
    )
    merged = cfg.merge_cli(bridge_device=None)
    assert merged.bridge.device == "BlackHole 2ch"


def test_save_creates_parent_dirs(tmp_path: Path):
    """save_audio_config creates parent directories."""
    path = tmp_path / "subdir" / "nested" / "audio.toml"
    save_audio_config(AudioConfig(), path)
    assert path.exists()


def test_load_auto_search_not_found():
    """Auto-search with no file returns defaults."""
    cfg = load_audio_config(None)
    assert cfg.bridge.device is None


def test_save_minimal_config(tmp_path: Path):
    """Saving a default config writes a valid TOML file."""
    path = tmp_path / "audio.toml"
    save_audio_config(AudioConfig(), path)
    content = path.read_text()
    assert "[bridge]" in content
    assert "[usb]" in content
    assert "max_retries = 5" in content


def test_save_escapes_special_characters(tmp_path: Path):
    """Device names with quotes/backslashes survive save+load roundtrip."""
    cfg = AudioConfig(
        bridge=BridgeConfig(device='Black"Hole'),
        usb=UsbConfig(rx_device="path\\with\\backslash"),
    )
    path = tmp_path / "audio.toml"
    save_audio_config(cfg, path)
    loaded = load_audio_config(path)
    assert loaded.bridge.device == 'Black"Hole'
    assert loaded.usb.rx_device == "path\\with\\backslash"
