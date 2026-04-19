"""Tests for WebRTC signaling scaffold (issue #104).

Covers:
- aiortc availability detection
- /api/v1/rtc/offer endpoint behavior with and without aiortc
- Capability exposure in /api/v1/info and /api/v1/capabilities
- Error handling (missing body, bad JSON, no radio audio)
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from icom_lan.web.server import WebServer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeWriter:
    """Minimal asyncio.StreamWriter stand-in that captures bytes."""

    def __init__(self) -> None:
        self.buffer = bytearray()

    def write(self, data: bytes) -> None:
        self.buffer.extend(data)

    async def drain(self) -> None:
        pass

    def close(self) -> None:
        pass

    async def wait_closed(self) -> None:
        pass


def _parse_response(writer: _FakeWriter) -> tuple[int, dict]:
    """Extract HTTP status code and JSON body from captured response."""
    text = writer.buffer.decode("ascii", errors="replace")
    status_line = text.split("\r\n", 1)[0]
    status_code = int(status_line.split(" ", 2)[1])
    body_start = text.index("\r\n\r\n") + 4
    body = json.loads(text[body_start:]) if text[body_start:] else {}
    return status_code, body


def _make_radio(*, audio: bool = True, caps: set[str] | None = None):
    """Build a fake radio, optionally implementing AudioCapable."""
    from icom_lan.radio_protocol import AudioCapable, ScopeCapable

    bases: list[type] = [ScopeCapable]
    if audio:
        bases.append(AudioCapable)

    class _FakeRadio(*bases):  # type: ignore[misc]
        pass

    radio = _FakeRadio()
    radio.model = "IC-7610"
    radio.connected = True
    radio.control_connected = False
    radio.radio_ready = True
    radio.capabilities = caps if caps is not None else {"audio", "scope"}
    return radio


# ---------------------------------------------------------------------------
# Unit tests: rtc module
# ---------------------------------------------------------------------------


class TestWebrtcAvailability:
    """webrtc_available() detection."""

    def test_reports_false_when_aiortc_missing(self):
        import icom_lan.web.rtc as rtc_mod

        # Reset cached state
        rtc_mod._aiortc_checked = False
        rtc_mod._aiortc_ok = False

        with patch.dict("sys.modules", {"aiortc": None}):
            rtc_mod._aiortc_checked = False
            result = rtc_mod.webrtc_available()

        assert result is False

    def test_caches_result(self):
        import icom_lan.web.rtc as rtc_mod

        rtc_mod._aiortc_checked = True
        rtc_mod._aiortc_ok = True
        # Even if import would fail, cached True is returned
        assert rtc_mod.webrtc_available() is True
        # Reset
        rtc_mod._aiortc_checked = False


class TestRtcCapabilityInfo:
    """rtc_capability_info() output."""

    def test_unavailable_info(self):
        from icom_lan.web.rtc import rtc_capability_info

        with patch("icom_lan.web.rtc.webrtc_available", return_value=False):
            info = rtc_capability_info()

        assert info["available"] is False
        assert info["reason"] is not None
        assert info["supportedDirections"] == []

    def test_available_info(self):
        from icom_lan.web.rtc import rtc_capability_info

        with patch("icom_lan.web.rtc.webrtc_available", return_value=True):
            info = rtc_capability_info()

        assert info["available"] is True
        assert info["reason"] is None
        assert "rx" in info["supportedDirections"]


class TestHandleRtcOffer:
    """handle_rtc_offer() logic."""

    @pytest.mark.asyncio
    async def test_returns_error_when_aiortc_missing(self):
        from icom_lan.web.rtc import handle_rtc_offer

        radio = _make_radio()
        with patch("icom_lan.web.rtc.webrtc_available", return_value=False):
            result = await handle_rtc_offer("v=0\r\n", "offer", radio)

        assert result["status"] == "error"
        assert result["code"] == "webrtc_unavailable"

    @pytest.mark.asyncio
    async def test_returns_error_when_no_radio(self):
        from icom_lan.web.rtc import handle_rtc_offer

        with patch("icom_lan.web.rtc.webrtc_available", return_value=True):
            result = await handle_rtc_offer("v=0\r\n", "offer", None)

        assert result["status"] == "error"
        assert result["code"] == "audio_unavailable"

    @pytest.mark.asyncio
    async def test_success_includes_scaffold_note(self):
        from unittest.mock import AsyncMock, MagicMock

        from icom_lan.web.rtc import handle_rtc_offer

        radio = _make_radio()

        mock_desc = MagicMock()
        mock_desc.sdp = "v=0\r\nanswer"
        mock_desc.type = "answer"

        mock_pc = MagicMock()
        mock_pc.addTransceiver = MagicMock()
        mock_pc.setRemoteDescription = AsyncMock()
        mock_pc.createAnswer = AsyncMock()
        mock_pc.setLocalDescription = AsyncMock()
        mock_pc.localDescription = mock_desc
        mock_pc.close = AsyncMock()

        fake_aiortc = MagicMock()
        fake_aiortc.RTCPeerConnection.return_value = mock_pc
        fake_aiortc.RTCSessionDescription.return_value = MagicMock()

        with (
            patch("icom_lan.web.rtc.webrtc_available", return_value=True),
            patch.dict("sys.modules", {"aiortc": fake_aiortc}),
        ):
            result = await handle_rtc_offer("v=0\r\n", "offer", radio)

        assert result["status"] == "ok"
        assert "note" in result
        assert "not yet" in result["note"].lower()

    @pytest.mark.asyncio
    async def test_returns_error_when_radio_has_no_audio(self):
        from icom_lan.web.rtc import handle_rtc_offer

        radio = _make_radio(audio=False)
        with patch("icom_lan.web.rtc.webrtc_available", return_value=True):
            result = await handle_rtc_offer("v=0\r\n", "offer", radio)

        assert result["status"] == "error"
        assert result["code"] == "audio_unavailable"


# ---------------------------------------------------------------------------
# Endpoint tests: _handle_rtc_offer on WebServer
# ---------------------------------------------------------------------------


class TestRtcOfferEndpoint:
    """POST /api/v1/rtc/offer via WebServer._handle_rtc_offer."""

    @pytest.mark.asyncio
    async def test_501_when_aiortc_unavailable(self):
        srv = WebServer(radio=None)
        writer = _FakeWriter()

        with patch("icom_lan.web.server.webrtc_available", return_value=False):
            await srv._handle_rtc_offer(writer, {}, None)  # noqa: SLF001

        status, body = _parse_response(writer)
        assert status == 501
        assert body["code"] == "webrtc_unavailable"

    @pytest.mark.asyncio
    async def test_400_when_no_body(self):
        srv = WebServer(radio=None)
        writer = _FakeWriter()

        with patch("icom_lan.web.server.webrtc_available", return_value=True):
            await srv._handle_rtc_offer(writer, {}, None)  # noqa: SLF001

        status, body = _parse_response(writer)
        assert status == 400
        assert body["code"] == "missing_body"

    @pytest.mark.asyncio
    async def test_400_when_invalid_json(self):
        import asyncio

        srv = WebServer(radio=None)
        writer = _FakeWriter()

        raw = b"not json"
        reader = asyncio.StreamReader()
        reader.feed_data(raw)
        reader.feed_eof()
        headers = {"content-length": str(len(raw))}

        with patch("icom_lan.web.server.webrtc_available", return_value=True):
            await srv._handle_rtc_offer(writer, headers, reader)  # noqa: SLF001

        status, body = _parse_response(writer)
        assert status == 400
        assert body["code"] == "invalid_json"

    @pytest.mark.asyncio
    async def test_400_when_sdp_missing(self):
        import asyncio

        srv = WebServer(radio=None)
        writer = _FakeWriter()

        raw = json.dumps({"type": "offer"}).encode()
        reader = asyncio.StreamReader()
        reader.feed_data(raw)
        reader.feed_eof()
        headers = {"content-length": str(len(raw))}

        with patch("icom_lan.web.server.webrtc_available", return_value=True):
            await srv._handle_rtc_offer(writer, headers, reader)  # noqa: SLF001

        status, body = _parse_response(writer)
        assert status == 400
        assert body["code"] == "missing_sdp"

    @pytest.mark.asyncio
    async def test_503_when_radio_audio_unavailable(self):
        import asyncio

        radio = _make_radio(audio=False, caps={"scope"})
        srv = WebServer(radio=radio)
        writer = _FakeWriter()

        raw = json.dumps({"sdp": "v=0\r\n", "type": "offer"}).encode()
        reader = asyncio.StreamReader()
        reader.feed_data(raw)
        reader.feed_eof()
        headers = {"content-length": str(len(raw))}

        with (
            patch("icom_lan.web.server.webrtc_available", return_value=True),
            patch("icom_lan.web.rtc.webrtc_available", return_value=True),
        ):
            await srv._handle_rtc_offer(writer, headers, reader)  # noqa: SLF001

        status, body = _parse_response(writer)
        assert status == 503
        assert body["code"] == "audio_unavailable"

    @pytest.mark.asyncio
    async def test_400_when_sdp_error(self):
        import asyncio
        from unittest.mock import MagicMock

        radio = _make_radio()
        with patch("icom_lan.web.server.AudioFftScope", MagicMock()):
            srv = WebServer(radio=radio)
        writer = _FakeWriter()

        raw = json.dumps({"sdp": "v=0\r\n", "type": "offer"}).encode()
        reader = asyncio.StreamReader()
        reader.feed_data(raw)
        reader.feed_eof()
        headers = {"content-length": str(len(raw))}

        sdp_err = {"status": "error", "code": "sdp_error", "message": "bad"}
        with (
            patch("icom_lan.web.server.webrtc_available", return_value=True),
            patch("icom_lan.web.server.handle_rtc_offer", return_value=sdp_err),
        ):
            await srv._handle_rtc_offer(writer, headers, reader)  # noqa: SLF001

        status, body = _parse_response(writer)
        assert status == 400
        assert body["code"] == "sdp_error"


# ---------------------------------------------------------------------------
# Capability exposure tests
# ---------------------------------------------------------------------------


class TestCapabilityExposure:
    """WebRTC info appears in /api/v1/info and /api/v1/capabilities."""

    @pytest.mark.asyncio
    async def test_info_includes_has_webrtc_false(self):
        srv = WebServer(radio=None)
        writer = _FakeWriter()

        with patch("icom_lan.web.server.webrtc_available", return_value=False):
            await srv._serve_info(writer)  # noqa: SLF001

        _, body = _parse_response(writer)
        assert body["capabilities"]["hasWebrtc"] is False

    @pytest.mark.asyncio
    async def test_info_includes_has_webrtc_true_with_audio(self):
        from unittest.mock import MagicMock

        radio = _make_radio()

        with patch("icom_lan.web.server.AudioFftScope", MagicMock()):
            srv = WebServer(radio=radio)

        writer = _FakeWriter()

        with patch("icom_lan.web.server.webrtc_available", return_value=True):
            await srv._serve_info(writer)  # noqa: SLF001

        _, body = _parse_response(writer)
        assert body["capabilities"]["hasWebrtc"] is True

    @pytest.mark.asyncio
    async def test_info_webrtc_false_when_no_audio_cap(self):
        radio = _make_radio(audio=False, caps={"scope"})
        srv = WebServer(radio=radio)
        writer = _FakeWriter()

        with patch("icom_lan.web.server.webrtc_available", return_value=True):
            await srv._serve_info(writer)  # noqa: SLF001

        _, body = _parse_response(writer)
        # webrtc_available() is True but audio cap is missing
        assert body["capabilities"]["hasWebrtc"] is False

    @pytest.mark.asyncio
    async def test_capabilities_includes_webrtc_block(self):
        srv = WebServer(radio=None)
        writer = _FakeWriter()

        with patch(
            "icom_lan.web.server.rtc_capability_info",
            return_value={
                "available": False,
                "reason": "aiortc not installed",
                "supportedDirections": [],
            },
        ):
            await srv._serve_capabilities(writer)  # noqa: SLF001

        _, body = _parse_response(writer)
        assert "webrtc" in body
        assert body["webrtc"]["available"] is False
