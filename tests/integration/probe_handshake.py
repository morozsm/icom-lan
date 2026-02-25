"""Diagnostic: send 'Are You There' and capture radio's response."""

import asyncio
import os
import struct

RADIO_IP = os.environ.get("ICOM_HOST", "192.168.1.100")
RADIO_PORT = 50001
CONTROL_SIZE = 0x10


class ProbeProtocol(asyncio.DatagramProtocol):
    def __init__(self, on_response: asyncio.Future):
        self._transport = None
        self._responses: list[bytes] = []
        self._on_response = on_response

    def connection_made(self, transport):
        self._transport = transport
        # Get our local info
        info = transport.get_extra_info("sockname")
        local_port = info[1] if info else 0
        my_id = (local_port & 0xFFFF) | 0x10000
        print(f"[probe] Local port: {local_port}, my_id: 0x{my_id:08X}")

        # Build "Are You There" packet: control (0x10), type=0x03, seq=0, sentid=my_id, rcvdid=0
        pkt = struct.pack("<IHHII", CONTROL_SIZE, 0x03, 0, my_id, 0)
        print(f"[probe] Sending 'Are You There' ({len(pkt)} bytes): {pkt.hex()}")
        transport.sendto(pkt)

    def datagram_received(self, data: bytes, addr):
        print(f"\n[probe] ← Received {len(data)} bytes from {addr}:")
        print(f"  hex: {data.hex()}")

        if len(data) >= CONTROL_SIZE:
            length, ptype, seq, sentid, rcvdid = struct.unpack_from("<IHHII", data)
            print(f"  length=0x{length:04X} type=0x{ptype:04X} seq={seq}")
            print(f"  sentid=0x{sentid:08X} rcvdid=0x{rcvdid:08X}")

        self._responses.append(data)
        if not self._on_response.done():
            self._on_response.set_result(data)

    def error_received(self, exc):
        print(f"[probe] Error: {exc}")


async def main():
    loop = asyncio.get_event_loop()
    response_future = loop.create_future()

    transport, protocol = await loop.create_datagram_endpoint(
        lambda: ProbeProtocol(response_future),
        remote_addr=(RADIO_IP, RADIO_PORT),
    )

    try:
        # Wait up to 3 seconds for first response, then collect more
        await asyncio.wait_for(response_future, timeout=3.0)
        # Give time for additional packets
        await asyncio.sleep(2.0)
    except asyncio.TimeoutError:
        print("[probe] ❌ No response from radio within 3 seconds")
    finally:
        transport.close()

    print(f"\n[probe] Total responses: {len(protocol._responses)}")


if __name__ == "__main__":
    asyncio.run(main())
