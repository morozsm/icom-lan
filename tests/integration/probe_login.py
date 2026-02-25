"""Diagnostic: full handshake sequence up to login."""

import asyncio
import random
import struct
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
from icom_lan.auth import encode_credentials

RADIO_IP = "192.168.1.100"
RADIO_PORT = 50001
CONTROL_SIZE = 0x10
LOGIN_SIZE = 0x80
LOGIN_RESPONSE_SIZE = 0x60
TOKEN_SIZE = 0x40
STATUS_SIZE = 0x50

USERNAME = os.environ.get("ICOM_USER", "")
PASSWORD = os.environ.get("ICOM_PASS", "")


class HandshakeProtocol(asyncio.DatagramProtocol):
    def __init__(self):
        self._transport = None
        self.my_id = 0
        self.remote_id = 0
        self._queue: asyncio.Queue[bytes] = asyncio.Queue()
        self.seq = 0
        self.auth_seq = 0

    def connection_made(self, transport):
        self._transport = transport
        info = transport.get_extra_info("sockname")
        local_port = info[1] if info else 0
        self.my_id = (local_port & 0xFFFF) | 0x10000
        print(f"[hs] my_id=0x{self.my_id:08X}, local_port={local_port}")

    def datagram_received(self, data: bytes, addr):
        self._queue.put_nowait(data)

    def send(self, data: bytes):
        self._transport.sendto(data)

    async def recv(self, timeout=3.0) -> bytes | None:
        try:
            return await asyncio.wait_for(self._queue.get(), timeout=timeout)
        except (asyncio.TimeoutError, TimeoutError):
            return None

    def build_control(self, ptype: int, seq: int = 0) -> bytes:
        return struct.pack("<IHHII", CONTROL_SIZE, ptype, seq, self.my_id, self.remote_id)

    def build_login(self) -> tuple[bytes, int]:
        pkt = bytearray(LOGIN_SIZE)
        struct.pack_into("<I", pkt, 0x00, LOGIN_SIZE)
        struct.pack_into("<H", pkt, 0x06, self.seq)
        self.seq += 1
        struct.pack_into("<I", pkt, 0x08, self.my_id)
        struct.pack_into("<I", pkt, 0x0C, self.remote_id)
        struct.pack_into(">I", pkt, 0x10, LOGIN_SIZE - 0x10)  # payloadsize BE
        pkt[0x14] = 0x01  # requestreply
        pkt[0x15] = 0x00  # requesttype
        struct.pack_into(">H", pkt, 0x16, self.auth_seq)  # innerseq BE
        self.auth_seq += 1
        tok_request = random.randint(0, 0xFFFF)
        struct.pack_into("<H", pkt, 0x1A, tok_request)
        user_enc = encode_credentials(USERNAME)
        pkt[0x40:0x40+len(user_enc)] = user_enc
        pass_enc = encode_credentials(PASSWORD)
        pkt[0x50:0x50+len(pass_enc)] = pass_enc
        name = b"icom-lan"
        pkt[0x60:0x60+len(name)] = name
        return bytes(pkt), tok_request


def describe_packet(data: bytes) -> str:
    if len(data) < CONTROL_SIZE:
        return f"??? ({len(data)} bytes)"
    length, ptype, seq, sentid, rcvdid = struct.unpack_from("<IHHII", data)
    return f"len=0x{length:04X}({len(data)}B) type=0x{ptype:04X} seq={seq} sent=0x{sentid:08X} rcvd=0x{rcvdid:08X}"


async def main():
    loop = asyncio.get_event_loop()
    transport, proto = await loop.create_datagram_endpoint(
        HandshakeProtocol,
        remote_addr=(RADIO_IP, RADIO_PORT),
    )

    try:
        # Step 1: Are You There
        print("\n[Step 1] Sending 'Are You There' (type=0x03)...")
        for attempt in range(5):
            proto.send(proto.build_control(0x03))
            resp = await proto.recv(timeout=1.0)
            if resp is not None:
                ptype = struct.unpack_from("<H", resp, 4)[0]
                sentid = struct.unpack_from("<I", resp, 8)[0]
                print(f"  ← {describe_packet(resp)}")
                if ptype == 0x04:
                    proto.remote_id = sentid
                    print(f"  ✅ 'I Am Here', remote_id=0x{proto.remote_id:08X}")
                    break
            else:
                print(f"  attempt {attempt+1}/5 — no response, retrying...")
        else:
            print("  ❌ Radio not responding")
            return

        # Step 2: Are You Ready
        print("\n[Step 2] Sending 'Are You Ready' (type=0x06)...")
        proto.send(proto.build_control(0x06))
        for i in range(3):
            resp = await proto.recv(timeout=2.0)
            if resp is None:
                print("  ⏱️ No response")
                break
            ptype = struct.unpack_from("<H", resp, 4)[0]
            print(f"  ← {describe_packet(resp)}")
            if ptype == 0x06:
                print("  ✅ 'I Am Ready'")
                break

        # Step 3: Login
        print("\n[Step 3] Sending Login (0x80 bytes)...")
        login_pkt, tok_request = proto.build_login()
        print(f"  tokrequest=0x{tok_request:04X}")
        proto.send(login_pkt)

        for i in range(10):
            resp = await proto.recv(timeout=3.0)
            if resp is None:
                print("  ⏱️ No more responses")
                break
            
            print(f"\n  ← Response #{i+1}: {describe_packet(resp)}")
            
            if len(resp) == LOGIN_RESPONSE_SIZE:
                error = struct.unpack_from("<I", resp, 0x30)[0]
                token = struct.unpack_from("<I", resp, 0x1C)[0]
                tokresp = struct.unpack_from("<H", resp, 0x1A)[0]
                connection = resp[0x40:0x50].rstrip(b'\x00').decode('ascii', errors='replace')
                print(f"     → LOGIN RESPONSE: error=0x{error:08X} token=0x{token:08X}")
                print(f"       tokrequest=0x{tokresp:04X} (sent 0x{tok_request:04X})")
                print(f"       connection='{connection}'")
                if error == 0xFEFFFFFF:
                    print("     ❌ Invalid username/password!")
                elif tokresp == tok_request:
                    print("     ✅ Login successful!")
                    
            elif len(resp) == STATUS_SIZE:
                error = struct.unpack_from("<I", resp, 0x30)[0]
                civport = struct.unpack_from(">H", resp, 0x42)[0]
                audioport = struct.unpack_from(">H", resp, 0x46)[0]
                print(f"     → STATUS: error=0x{error:08X} civport={civport} audioport={audioport}")

    finally:
        transport.close()

    print("\n[hs] Done.")


if __name__ == "__main__":
    asyncio.run(main())
