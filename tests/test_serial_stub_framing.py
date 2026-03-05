"""Deterministic unit tests for serial-ready framing and receive stability."""

from __future__ import annotations

import pytest

from icom_lan.backends.icom7610.drivers.serial_stub import (
    DeterministicSerialCivLink,
    SerialFrameCodec,
    SerialFrameOverflowError,
    SerialFrameTimeoutError,
)


def test_serial_frame_codec_parses_single_frame() -> None:
    codec = SerialFrameCodec(max_frame_len=64, frame_timeout_s=0.05)
    frame = b"\xFE\xFE\x98\xE0\x03\xFD"
    assert codec.feed(frame) == [frame]


def test_serial_frame_codec_ignores_noise_and_parses_frame() -> None:
    codec = SerialFrameCodec(max_frame_len=64, frame_timeout_s=0.05)
    mixed = b"\x00\x01garbage\xFE\xFE\x98\xE0\x03\xFD\x99"
    assert codec.feed(mixed) == [b"\xFE\xFE\x98\xE0\x03\xFD"]


def test_serial_frame_codec_collects_partial_chunks() -> None:
    codec = SerialFrameCodec(max_frame_len=64, frame_timeout_s=0.05)
    assert codec.feed(b"\xFE\xFE\x98") == []
    assert codec.feed(b"\xE0\x03") == []
    assert codec.feed(b"\xFD") == [b"\xFE\xFE\x98\xE0\x03\xFD"]


def test_serial_frame_codec_multiple_frames_in_one_chunk() -> None:
    codec = SerialFrameCodec(max_frame_len=64, frame_timeout_s=0.05)
    chunk = b"\xFE\xFE\x98\xE0\x03\xFD\xFE\xFE\x98\xE0\x04\xFD"
    frames = codec.feed(chunk)
    assert frames == [b"\xFE\xFE\x98\xE0\x03\xFD", b"\xFE\xFE\x98\xE0\x04\xFD"]


def test_serial_frame_codec_overflow_raises() -> None:
    codec = SerialFrameCodec(max_frame_len=6, frame_timeout_s=0.05)
    codec.feed(b"\xFE\xFE\x98\xE0")
    with pytest.raises(SerialFrameOverflowError):
        codec.feed(b"\x03\x99\x98")


@pytest.mark.asyncio
async def test_serial_link_receive_timeout_without_frame_returns_none() -> None:
    link = DeterministicSerialCivLink(
        SerialFrameCodec(max_frame_len=64, frame_timeout_s=0.01)
    )
    assert await link.receive(timeout=0.005) is None


@pytest.mark.asyncio
async def test_serial_link_receive_timeout_for_partial_frame_raises() -> None:
    link = DeterministicSerialCivLink(
        SerialFrameCodec(max_frame_len=64, frame_timeout_s=0.001)
    )
    link.push_incoming_chunk(b"\xFE\xFE\x98")
    with pytest.raises(SerialFrameTimeoutError):
        await link.receive(timeout=0.01)


@pytest.mark.asyncio
async def test_serial_link_send_encodes_and_receive_decodes() -> None:
    link = DeterministicSerialCivLink(
        SerialFrameCodec(max_frame_len=64, frame_timeout_s=0.05)
    )
    await link.send(b"\x98\xE0\x03")
    assert link.sent_frames == [b"\xFE\xFE\x98\xE0\x03\xFD"]

    link.push_incoming_chunk(b"\xFE\xFE\x98\xE0\x03\xFD")
    assert await link.receive(timeout=0.01) == b"\xFE\xFE\x98\xE0\x03\xFD"
