"""Full handshake in one connection: AreYouThere → Login → done."""

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

USERNAME = os.environ.get("ICOM_USER", "")
PASSWORD = os.environ.get("ICOM_PASS", "")


class Proto(asyncio.DatagramProtocol):
    def __init__(self):
        self.tr = None
        self.my_id = 0
        self.remote_id = 0
        self.q: asyncio.Queue[bytes] = asyncio.Queue()
        self.seq = 0
        self.auth_seq = 0

    def connection_made(self, transport):
        self.tr = transport
        port = transport.get_extra_info("sockname")[1]
        self.my_id = (port & 0xFFFF) | 0x10000

    def datagram_received(self, data, addr):
        self.q.put_nowait(data)

    def send(self, data):
        self.tr.sendto(data)

    async def recv(self, timeout=3.0):
        try:
            return await asyncio.wait_for(self.q.get(), timeout=timeout)
        except (asyncio.TimeoutError, TimeoutError):
            return None

    def control(self, ptype, seq=0):
        return struct.pack("<IHHII", CONTROL_SIZE, ptype, seq, self.my_id, self.remote_id)

    def login_pkt(self):
        pkt = bytearray(LOGIN_SIZE)
        struct.pack_into("<I", pkt, 0x00, LOGIN_SIZE)
        struct.pack_into("<H", pkt, 0x06, self.seq)
        self.seq += 1
        struct.pack_into("<I", pkt, 0x08, self.my_id)
        struct.pack_into("<I", pkt, 0x0C, self.remote_id)
        struct.pack_into(">I", pkt, 0x10, LOGIN_SIZE - 0x10)
        pkt[0x14] = 0x01
        pkt[0x15] = 0x00
        struct.pack_into(">H", pkt, 0x16, self.auth_seq)
        self.auth_seq += 1
        tok = random.randint(0, 0xFFFF)
        struct.pack_into("<H", pkt, 0x1A, tok)
        ue = encode_credentials(USERNAME)
        pkt[0x40:0x40+len(ue)] = ue
        pe = encode_credentials(PASSWORD)
        pkt[0x50:0x50+len(pe)] = pe
        nm = b"icom-lan"
        pkt[0x60:0x60+len(nm)] = nm
        return bytes(pkt), tok


async def main():
    loop = asyncio.get_event_loop()
    tr, p = await loop.create_datagram_endpoint(Proto, remote_addr=(RADIO_IP, RADIO_PORT))

    print(f"my_id=0x{p.my_id:08X}")

    try:
        # 1. Are You There (retry)
        print("\n── Step 1: Are You There ──")
        for att in range(10):
            p.send(p.control(0x03))
            r = await p.recv(1.0)
            if r and len(r) >= 16:
                pt = struct.unpack_from("<H", r, 4)[0]
                sid = struct.unpack_from("<I", r, 8)[0]
                if pt == 0x04:
                    p.remote_id = sid
                    print(f"✅ I Am Here, remote_id=0x{p.remote_id:08X} (attempt {att+1})")
                    break
                print(f"  got type=0x{pt:04X}")
            else:
                if att % 3 == 2:
                    print(f"  retrying... ({att+1})")
        else:
            print("❌ Radio not responding after 10 attempts")
            return

        # 2. Are You Ready
        print("\n── Step 2: Are You Ready ──")
        p.send(p.control(0x06))
        for _ in range(5):
            r = await p.recv(2.0)
            if r is None:
                break
            pt = struct.unpack_from("<H", r, 4)[0]
            if pt == 0x06:
                print("✅ I Am Ready")
                break
            print(f"  got type=0x{pt:04X} len={len(r)}")

        # 3. Login
        print("\n── Step 3: Login ──")
        lpkt, tok = p.login_pkt()
        print(f"Sending login, tokrequest=0x{tok:04X}")
        p.send(lpkt)

        for i in range(10):
            r = await p.recv(3.0)
            if r is None:
                print("⏱️ No more responses")
                break
            pt = struct.unpack_from("<H", r, 4)[0]
            print(f"  ← len={len(r)} type=0x{pt:04X}")

            if len(r) == LOGIN_RESPONSE_SIZE:
                error = struct.unpack_from("<I", r, 0x30)[0]
                token = struct.unpack_from("<I", r, 0x1C)[0]
                tr_resp = struct.unpack_from("<H", r, 0x1A)[0]
                conn = r[0x40:0x50].rstrip(b'\x00').decode('ascii', errors='replace')
                print(f"  LOGIN RESPONSE: error=0x{error:08X} token=0x{token:08X} conn='{conn}'")
                if error == 0xFEFFFFFF:
                    print("  ❌ Invalid username/password!")
                elif tr_resp == tok:
                    print(f"  ✅ Login OK! token=0x{token:08X}")
                break

        # 4. Disconnect cleanly
        print("\n── Disconnect ──")
        p.send(p.control(0x05))
        print("✅ Sent disconnect")

    finally:
        tr.close()


if __name__ == "__main__":
    asyncio.run(main())
