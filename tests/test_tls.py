"""Tests for TLS certificate generation and SSL context building."""

from __future__ import annotations

import ssl
from pathlib import Path
from unittest.mock import patch


from icom_lan.web.tls import build_ssl_context, generate_self_signed


class TestGenerateSelfSigned:
    """Test self-signed certificate generation."""

    def test_generates_cert_and_key(self, tmp_path: Path) -> None:
        cert = tmp_path / "cert.pem"
        key = tmp_path / "key.pem"
        result_cert, result_key = generate_self_signed(cert, key, hostname="localhost")
        assert result_cert == cert
        assert result_key == key
        assert cert.exists()
        assert key.exists()
        assert cert.read_bytes().startswith(b"-----BEGIN CERTIFICATE-----")
        assert key.read_bytes().startswith(b"-----BEGIN")

    def test_reuses_existing_cert(self, tmp_path: Path) -> None:
        cert = tmp_path / "cert.pem"
        key = tmp_path / "key.pem"
        # First generation
        generate_self_signed(cert, key, hostname="localhost")
        original_cert_bytes = cert.read_bytes()
        original_key_bytes = key.read_bytes()
        # Second call should reuse
        generate_self_signed(cert, key, hostname="localhost")
        assert cert.read_bytes() == original_cert_bytes
        assert key.read_bytes() == original_key_bytes

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        cert = tmp_path / "deep" / "nested" / "cert.pem"
        key = tmp_path / "deep" / "nested" / "key.pem"
        generate_self_signed(cert, key, hostname="localhost")
        assert cert.exists()
        assert key.exists()

    def test_default_hostname_is_gethostname(self, tmp_path: Path) -> None:
        cert = tmp_path / "cert.pem"
        key = tmp_path / "key.pem"
        # Should not raise — uses socket.gethostname() internally
        generate_self_signed(cert, key)
        assert cert.exists()

    def test_openssl_fallback(self, tmp_path: Path) -> None:
        """Falls back to openssl CLI when cryptography is not available."""
        cert = tmp_path / "cert.pem"
        key = tmp_path / "key.pem"
        with patch.dict("sys.modules", {"cryptography": None}):
            # Need to also block submodules
            with patch(
                "icom_lan.web.tls._generate_with_cryptography",
                side_effect=ImportError("no cryptography"),
            ):
                generate_self_signed(cert, key, hostname="localhost")
        assert cert.exists()
        assert key.exists()


class TestBuildSslContext:
    """Test SSL context creation."""

    def test_auto_generates_when_no_paths(self, tmp_path: Path) -> None:
        cert = tmp_path / "cert.pem"
        key = tmp_path / "key.pem"
        with patch(
            "icom_lan.web.tls.generate_self_signed",
            side_effect=lambda **kw: (
                generate_self_signed(cert, key, hostname="localhost")
            ),
        ) as mock_gen:
            ctx = build_ssl_context()
        assert isinstance(ctx, ssl.SSLContext)
        assert cert.exists()
        mock_gen.assert_called_once()

    def test_uses_provided_paths(self, tmp_path: Path) -> None:
        cert = tmp_path / "cert.pem"
        key = tmp_path / "key.pem"
        generate_self_signed(cert, key, hostname="localhost")
        ctx = build_ssl_context(cert_path=cert, key_path=key)
        assert isinstance(ctx, ssl.SSLContext)

    def test_accepts_string_paths(self, tmp_path: Path) -> None:
        cert = tmp_path / "cert.pem"
        key = tmp_path / "key.pem"
        generate_self_signed(cert, key, hostname="localhost")
        ctx = build_ssl_context(cert_path=str(cert), key_path=str(key))
        assert isinstance(ctx, ssl.SSLContext)


class TestWebConfigTls:
    """Test WebConfig TLS fields."""

    def test_tls_enabled(self) -> None:
        from icom_lan.web.server import WebConfig

        config = WebConfig(tls=True)
        assert config.tls is True

    def test_tls_defaults_off(self) -> None:
        from icom_lan.web.server import WebConfig

        config = WebConfig()
        assert config.tls is False
        assert config.tls_cert == ""
        assert config.tls_key == ""
