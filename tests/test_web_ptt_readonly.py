"""Tests for read-only guard on web PTT dispatch (issue #950)."""

from __future__ import annotations

from queue import Queue
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

from icom_lan.web.handlers.control import ControlHandler


def _make_handler(
    *, read_only: bool = False, radio: Any = None
) -> tuple[ControlHandler, Queue[Any]]:
    """Build a ControlHandler with a fake server and return (handler, command_queue)."""
    ws = MagicMock()

    command_queue: Queue[Any] = Queue()

    server = SimpleNamespace(
        command_queue=command_queue,
    )

    if radio is None:
        radio = MagicMock()

    handler = ControlHandler(
        ws=ws,
        radio=radio,
        server_version="test",
        radio_model="IC-7610",
        server=server,
        read_only=read_only,
    )
    return handler, command_queue


class TestWebPttReadOnly:
    """read_only=True must reject PTT commands without enqueuing anything."""

    @pytest.mark.asyncio
    async def test_ptt_rejected_in_read_only_mode(self) -> None:
        """ptt command raises PermissionError when read_only=True."""
        handler, q = _make_handler(read_only=True)

        with pytest.raises(PermissionError, match="read-only"):
            await handler._enqueue_command("ptt", {"state": True})

        assert q.empty(), "command queue must not be touched in read-only mode"

    @pytest.mark.asyncio
    async def test_ptt_on_rejected_in_read_only_mode(self) -> None:
        """ptt_on command raises PermissionError when read_only=True."""
        handler, q = _make_handler(read_only=True)

        with pytest.raises(PermissionError, match="read-only"):
            await handler._enqueue_command("ptt_on", {})

        assert q.empty(), "command queue must not be touched in read-only mode"

    @pytest.mark.asyncio
    async def test_ptt_off_rejected_in_read_only_mode(self) -> None:
        """ptt_off command raises PermissionError when read_only=True."""
        handler, q = _make_handler(read_only=True)

        with pytest.raises(PermissionError, match="read-only"):
            await handler._enqueue_command("ptt_off", {})

        assert q.empty(), "command queue must not be touched in read-only mode"

    @pytest.mark.asyncio
    async def test_ptt_allowed_when_not_read_only(self) -> None:
        """ptt command dispatches normally when read_only=False."""
        handler, q = _make_handler(read_only=False)

        result = await handler._enqueue_command("ptt", {"state": True})

        assert result == {"state": True}
        assert not q.empty(), "PttOn must be enqueued"

    @pytest.mark.asyncio
    async def test_ptt_on_allowed_when_not_read_only(self) -> None:
        """ptt_on command dispatches normally when read_only=False."""
        handler, q = _make_handler(read_only=False)

        result = await handler._enqueue_command("ptt_on", {})

        assert result == {}
        assert not q.empty(), "PttOn must be enqueued"

    @pytest.mark.asyncio
    async def test_ptt_off_allowed_when_not_read_only(self) -> None:
        """ptt_off command dispatches normally when read_only=False."""
        handler, q = _make_handler(read_only=False)

        result = await handler._enqueue_command("ptt_off", {})

        assert result == {}
        assert not q.empty(), "PttOff must be enqueued"
