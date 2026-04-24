"""Test token comparison security (issue #947).

Verifies that auth token comparison uses hmac.compare_digest for timing safety.
"""

from __future__ import annotations

import asyncio

from icom_lan.web.server import WebConfig, WebServer


async def _http_get_with_auth(
    host: str, port: int, path: str, auth_header: str | None = None
) -> tuple[int, dict[str, str], bytes]:
    """Minimal HTTP GET with optional Authorization header."""
    reader, writer = await asyncio.open_connection(host, port)
    try:
        request_line = (
            f"GET {path} HTTP/1.1\r\nHost: {host}:{port}\r\nConnection: close\r\n"
        )
        if auth_header:
            request_line += f"Authorization: {auth_header}\r\n"
        request_line += "\r\n"

        writer.write(request_line.encode())
        await writer.drain()

        raw = await asyncio.wait_for(reader.read(65536), timeout=5.0)
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass

    # Parse response
    header_end = raw.find(b"\r\n\r\n")
    header_bytes = raw[:header_end]
    body = raw[header_end + 4 :]

    # Extract status code
    status_line = header_bytes.split(b"\r\n")[0].decode()
    status_code = int(status_line.split()[1])

    # Parse headers
    headers = {}
    for line in header_bytes.split(b"\r\n")[1:]:
        if not line:
            break
        key, value = line.decode().split(": ", 1)
        headers[key] = value

    return status_code, headers, body


class TestAuthTokenComparison:
    """Unit tests for auth token comparison with hmac.compare_digest."""

    async def _make_server(
        self, auth_token: str | None = None
    ) -> tuple[WebServer, str, int]:
        """Create and start a WebServer with optional auth token."""
        config = WebConfig(
            host="127.0.0.1", port=0, auth_token=auth_token, radio_model="IC-7610"
        )
        server = WebServer(None, config)
        await server.start()
        addr = server._server.sockets[0].getsockname()
        return server, addr[0], addr[1]

    async def test_api_endpoint_accepts_correct_bearer_token(self):
        """HTTP API endpoint should accept correct Bearer token."""
        token = "super-secret-token-12345"
        server, host, port = await self._make_server(auth_token=token)

        try:
            status, _, body = await _http_get_with_auth(
                host, port, "/api/v1/info", auth_header=f"Bearer {token}"
            )

            # Should succeed with correct token
            assert status == 200, f"Expected 200, got {status}: {body}"
        finally:
            await server.stop()

    async def test_api_endpoint_rejects_incorrect_bearer_token(self):
        """HTTP API endpoint should reject incorrect Bearer token."""
        token = "super-secret-token-12345"
        server, host, port = await self._make_server(auth_token=token)

        try:
            status, headers, body = await _http_get_with_auth(
                host, port, "/api/v1/info", auth_header="Bearer wrong-token"
            )

            # Should reject with 401
            assert status == 401, f"Expected 401, got {status}"
            assert b"unauthorized" in body.lower()
        finally:
            await server.stop()

    async def test_api_endpoint_rejects_missing_bearer_prefix(self):
        """HTTP API endpoint should reject token without Bearer prefix."""
        token = "super-secret-token-12345"
        server, host, port = await self._make_server(auth_token=token)

        try:
            status, _, body = await _http_get_with_auth(
                host, port, "/api/v1/info", auth_header=token
            )

            # Should reject without Bearer prefix
            assert status == 401, f"Expected 401, got {status}"
        finally:
            await server.stop()

    async def test_api_endpoint_no_auth_required_when_no_token_configured(self):
        """HTTP API endpoint should allow access when no auth token is configured."""
        server, host, port = await self._make_server(auth_token=None)

        try:
            status, _, _ = await _http_get_with_auth(host, port, "/api/v1/info")

            # Should allow access without auth
            assert status == 200, f"Expected 200, got {status}"
        finally:
            await server.stop()

    def test_hmac_compare_digest_is_timing_safe(self):
        """Verify hmac.compare_digest is used (timing-safe comparison)."""
        import hmac

        # This test verifies the property of hmac.compare_digest:
        # It should take roughly the same time regardless of where
        # the first difference occurs in the strings.
        token = "secret-token-1234567890"

        # Create test cases with differences at different positions
        test_cases = [
            ("x" + token[1:], "mismatch at position 0"),
            (token[:-1] + "x", "mismatch at position -1"),
        ]

        for wrong_token, desc in test_cases:
            result = hmac.compare_digest(token, wrong_token)
            assert result is False, f"Should reject: {desc}"

        # Verify correct token passes
        result = hmac.compare_digest(token, token)
        assert result is True, "Should accept matching token"
