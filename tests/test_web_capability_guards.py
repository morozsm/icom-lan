"""Web UI capability guards — verify API responses adapt to rig profile.

TDD: these tests were written FIRST, then the backend was modified to pass them.
"""

from __future__ import annotations

import json

import pytest

from icom_lan.web.server import WebServer


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


def _parse_json_body(writer: _FakeWriter) -> dict:
    text = writer.buffer.decode("ascii", errors="replace")
    body_start = text.index("\r\n\r\n") + 4
    return json.loads(text[body_start:])


# ── Helpers: fake radios with profiles ──────────────────────────


def _make_radio(model: str = "IC-7610", caps: set[str] | None = None):
    """Build a fake radio with a real RadioProfile resolved by model name."""
    from icom_lan.radio_protocol import (
        AudioCapable,
        DualReceiverCapable,
        ScopeCapable,
    )

    from icom_lan.profiles import resolve_radio_profile

    profile = resolve_radio_profile(model=model)

    class _FakeRadio(ScopeCapable, AudioCapable, DualReceiverCapable):
        pass

    radio = _FakeRadio()
    radio.model = model
    radio.connected = True
    radio.control_connected = False
    radio.radio_ready = True
    radio.capabilities = caps if caps is not None else set(profile.capabilities)
    radio.profile = profile
    return radio


# ── /api/v1/info tests ─────────────────────────────────────────


class TestInfoEndpoint:
    """Verify /api/v1/info includes rig-specific metadata."""

    @pytest.mark.asyncio
    async def test_info_includes_receivers_for_dual(self):
        radio = _make_radio("IC-7610")
        srv = WebServer(radio)
        writer = _FakeWriter()
        await srv._serve_info(writer)  # noqa: SLF001
        data = _parse_json_body(writer)
        assert data["capabilities"]["maxReceivers"] == 2

    @pytest.mark.asyncio
    async def test_info_includes_receivers_for_single(self):
        radio = _make_radio("IC-7300")
        srv = WebServer(radio)
        writer = _FakeWriter()
        await srv._serve_info(writer)  # noqa: SLF001
        data = _parse_json_body(writer)
        assert data["capabilities"]["maxReceivers"] == 1

    @pytest.mark.asyncio
    async def test_info_includes_vfo_scheme_main_sub(self):
        radio = _make_radio("IC-7610")
        srv = WebServer(radio)
        writer = _FakeWriter()
        await srv._serve_info(writer)  # noqa: SLF001
        data = _parse_json_body(writer)
        assert data["capabilities"]["vfoScheme"] == "main_sub"

    @pytest.mark.asyncio
    async def test_info_includes_vfo_scheme_ab(self):
        radio = _make_radio("IC-7300")
        srv = WebServer(radio)
        writer = _FakeWriter()
        await srv._serve_info(writer)  # noqa: SLF001
        data = _parse_json_body(writer)
        assert data["capabilities"]["vfoScheme"] == "ab"

    @pytest.mark.asyncio
    async def test_info_includes_has_lan_true(self):
        radio = _make_radio("IC-7610")
        srv = WebServer(radio)
        writer = _FakeWriter()
        await srv._serve_info(writer)  # noqa: SLF001
        data = _parse_json_body(writer)
        assert data["capabilities"]["hasLan"] is True

    @pytest.mark.asyncio
    async def test_info_includes_has_lan_false(self):
        radio = _make_radio("IC-7300")
        srv = WebServer(radio)
        writer = _FakeWriter()
        await srv._serve_info(writer)  # noqa: SLF001
        data = _parse_json_body(writer)
        assert data["capabilities"]["hasLan"] is False

    @pytest.mark.asyncio
    async def test_info_ic7300_no_dual_rx_tag(self):
        radio = _make_radio("IC-7300")
        srv = WebServer(radio)
        writer = _FakeWriter()
        await srv._serve_info(writer)  # noqa: SLF001
        data = _parse_json_body(writer)
        assert "dual_rx" not in data["capabilities"]["tags"]


# ── /api/v1/capabilities tests ─────────────────────────────────


class TestCapabilitiesEndpoint:
    """Verify /api/v1/capabilities includes rig-specific metadata."""

    @pytest.mark.asyncio
    async def test_capabilities_includes_receivers(self):
        radio = _make_radio("IC-7610")
        srv = WebServer(radio)
        writer = _FakeWriter()
        await srv._serve_capabilities(writer)  # noqa: SLF001
        data = _parse_json_body(writer)
        assert data["receivers"] == 2

    @pytest.mark.asyncio
    async def test_capabilities_includes_vfo_scheme(self):
        radio = _make_radio("IC-7610")
        srv = WebServer(radio)
        writer = _FakeWriter()
        await srv._serve_capabilities(writer)  # noqa: SLF001
        data = _parse_json_body(writer)
        assert data["vfoScheme"] == "main_sub"

    @pytest.mark.asyncio
    async def test_capabilities_single_receiver(self):
        radio = _make_radio("IC-7300")
        srv = WebServer(radio)
        writer = _FakeWriter()
        await srv._serve_capabilities(writer)  # noqa: SLF001
        data = _parse_json_body(writer)
        assert data["receivers"] == 1
        assert data["vfoScheme"] == "ab"


# ── /api/v1/state tests ───────────────────────────────────────


class TestStateEndpoint:
    """Verify /api/v1/state adapts to receiver count."""

    @pytest.mark.asyncio
    async def test_state_dual_receiver_includes_sub(self):
        radio = _make_radio("IC-7610")
        srv = WebServer(radio)
        writer = _FakeWriter()
        await srv._serve_state(writer)  # noqa: SLF001
        data = _parse_json_body(writer)
        assert "main" in data
        assert "sub" in data

    @pytest.mark.asyncio
    async def test_state_single_receiver_omits_sub(self):
        radio = _make_radio("IC-7300")
        srv = WebServer(radio)
        writer = _FakeWriter()
        await srv._serve_state(writer)  # noqa: SLF001
        data = _parse_json_body(writer)
        assert "main" in data
        assert "sub" not in data


# ── Command capability guards ──────────────────────────────────


class TestCommandGuards:
    """Commands for unsupported capabilities return clear error."""

    def test_dual_watch_guard_single_receiver(self):
        """set_dual_watch on IC-7300 (no dual_rx) should raise ValueError."""
        from icom_lan.web.handlers import ControlHandler

        radio = _make_radio("IC-7300")
        handler = ControlHandler.__new__(ControlHandler)
        handler._radio = radio

        with pytest.raises(ValueError, match="dual_rx"):
            handler._ensure_capability("dual_rx", "set_dual_watch")

    def test_digisel_guard_ic7300(self):
        """set_digisel on IC-7300 (no digisel) should raise ValueError."""
        from icom_lan.web.handlers import ControlHandler

        radio = _make_radio("IC-7300")
        handler = ControlHandler.__new__(ControlHandler)
        handler._radio = radio

        with pytest.raises(ValueError, match="digisel"):
            handler._ensure_capability("digisel", "set_digisel")

    def test_ip_plus_guard_ic7300(self):
        """set_ipplus on IC-7300 (no ip_plus) should raise ValueError."""
        from icom_lan.web.handlers import ControlHandler

        radio = _make_radio("IC-7300")
        handler = ControlHandler.__new__(ControlHandler)
        handler._radio = radio

        with pytest.raises(ValueError, match="ip_plus"):
            handler._ensure_capability("ip_plus", "set_ipplus")

    def test_capability_passes_when_supported(self):
        """_ensure_capability does NOT raise for supported capabilities."""
        from icom_lan.web.handlers import ControlHandler

        radio = _make_radio("IC-7610")
        handler = ControlHandler.__new__(ControlHandler)
        handler._radio = radio

        # Should not raise
        handler._ensure_capability("dual_rx", "set_dual_watch")
