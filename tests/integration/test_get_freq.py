"""Integration: handshake + get frequency from IC-7610."""

import asyncio
import random
import struct
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
from icom_lan.auth import encode_credentials
from icom_lan.commands import get_frequency, parse_civ_frame, parse_frequency_response

RADIO_IP = os.environ.get("ICOM_HOST", "192.168.1.100")
RADIO_PORT = 50001
CONTROL_SIZE = 0x10
LOGIN_SIZE = 0x80
LOGIN_RESPONSE_SIZE = 0x60
CIV_HEADER_SIZE = 0x15

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
        self.token = 0
        self.ping_seq_radio = 0

    def connection_made(self, transport):
        self.tr = transport
        port = transport.get_extra_info("sockname")[1]
        self.my_id = (port & 0xFFFF) | 0x10000

    def datagram_received(self, data, addr):
        # Auto-respond to ping requests
        if len(data) == 21:  # PING_SIZE
            pt = struct.unpack_from("<H", data, 4)[0]
            if pt == 0x07:  # ping
                reply_flag = data[0x10]
                if reply_flag == 0x00:  # ping request
                    # Send ping reply
                    reply = bytearray(21)
                    struct.pack_into("<I", reply, 0, 21)
                    struct.pack_into("<H", reply, 4, 0x07)
                    seq = struct.unpack_from("<H", data, 6)[0]
                    struct.pack_into("<H", reply, 6, seq)
                    struct.pack_into("<I", reply, 8, self.my_id)
                    struct.pack_into("<I", reply, 0x0C, self.remote_id)
                    reply[0x10] = 0x01  # reply
                    reply[0x11:0x15] = data[0x11:0x15]
                    self.tr.sendto(bytes(reply))
                    return  # don't queue it

        # Queue all other packets
        self.q.put_nowait(data)

    def send(self, data):
        self.tr.sendto(data)

    async def recv(self, timeout=3.0):
        try:
            return await asyncio.wait_for(self.q.get(), timeout=timeout)
        except (asyncio.TimeoutError, TimeoutError):
            return None

    def control(self, ptype, seq=0):
        return struct.pack(
            "<IHHII", CONTROL_SIZE, ptype, seq, self.my_id, self.remote_id
        )

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
        pkt[0x40 : 0x40 + len(ue)] = ue
        pe = encode_credentials(PASSWORD)
        pkt[0x50 : 0x50 + len(pe)] = pe
        nm = b"icom-lan"
        pkt[0x60 : 0x60 + len(nm)] = nm
        return bytes(pkt), tok

    def token_pkt(self, magic=0x02):
        pkt = bytearray(0x40)
        struct.pack_into("<I", pkt, 0x00, 0x40)
        struct.pack_into("<H", pkt, 0x06, self.seq)
        self.seq += 1
        struct.pack_into("<I", pkt, 0x08, self.my_id)
        struct.pack_into("<I", pkt, 0x0C, self.remote_id)
        struct.pack_into(">I", pkt, 0x10, 0x40 - 0x10)
        pkt[0x14] = 0x01
        pkt[0x15] = magic
        struct.pack_into(">H", pkt, 0x16, self.auth_seq)
        self.auth_seq += 1
        struct.pack_into("<I", pkt, 0x1C, self.token)
        return bytes(pkt)

    def wrap_civ(self, civ_frame: bytes) -> bytes:
        total = CIV_HEADER_SIZE + len(civ_frame)
        pkt = bytearray(total)
        struct.pack_into("<I", pkt, 0, total)
        struct.pack_into("<H", pkt, 4, 0x00)  # DATA
        struct.pack_into("<H", pkt, 6, self.seq)
        self.seq += 1
        struct.pack_into("<I", pkt, 8, self.my_id)
        struct.pack_into("<I", pkt, 0x0C, self.remote_id)
        pkt[0x10] = 0x00
        struct.pack_into("<H", pkt, 0x11, len(civ_frame))
        struct.pack_into("<H", pkt, 0x13, 0)
        pkt[CIV_HEADER_SIZE:] = civ_frame
        return bytes(pkt)


async def do_handshake(p):
    # Are You There
    for att in range(10):
        p.send(p.control(0x03))
        r = await p.recv(1.0)
        if r and len(r) >= 16:
            pt = struct.unpack_from("<H", r, 4)[0]
            if pt == 0x04:
                p.remote_id = struct.unpack_from("<I", r, 8)[0]
                print(f"[hs] I Am Here, remote_id=0x{p.remote_id:08X}")
                break
    else:
        print("[hs] ❌ No response")
        return False

    # Are You Ready
    p.send(p.control(0x06))
    for _ in range(5):
        r = await p.recv(2.0)
        if r is None:
            break
        if struct.unpack_from("<H", r, 4)[0] == 0x06:
            print("[hs] I Am Ready")
            break

    # Login
    lpkt, tok = p.login_pkt()
    p.send(lpkt)
    for _ in range(10):
        r = await p.recv(3.0)
        if r is None:
            break
        if len(r) == LOGIN_RESPONSE_SIZE:
            error = struct.unpack_from("<I", r, 0x30)[0]
            p.token = struct.unpack_from("<I", r, 0x1C)[0]
            if error == 0xFEFFFFFF:
                print("[hs] ❌ Invalid credentials")
                return False
            print(f"[hs] ✅ Login OK, token=0x{p.token:08X}")
            p.send(p.token_pkt(0x02))
            return True

    print("[hs] ❌ No login response")
    return False


async def main():
    loop = asyncio.get_event_loop()
    tr, p = await loop.create_datagram_endpoint(
        Proto, remote_addr=(RADIO_IP, RADIO_PORT)
    )

    try:
        if not await do_handshake(p):
            return

        # Wait a moment for capabilities packet
        await asyncio.sleep(0.5)

        # Flush queue
        count = 0
        while True:
            r = await p.recv(0.1)
            if r is None:
                break
            count += 1
        print(f"[flush] Flushed {count} pending packets")

        # Get Frequency
        print("\n── Get Frequency ──")
        civ_frame = get_frequency(to_addr=0x98)
        print(f"CIV: {civ_frame.hex()}")

        udp_pkt = p.wrap_civ(civ_frame)
        p.send(udp_pkt)

        # Wait for CI-V response (filter out idle/ping/other)
        for i in range(20):
            r = await p.recv(3.0)
            if r is None:
                print("⏱️ Timeout")
                break

            pt = struct.unpack_from("<H", r, 4)[0] if len(r) >= 6 else -1

            # Skip non-data packets
            if pt != 0x00:
                continue

            # Check for CIV payload
            if len(r) > CIV_HEADER_SIZE:
                civ_data = r[CIV_HEADER_SIZE:]
                if len(civ_data) >= 4 and civ_data[0] == 0xFE and civ_data[1] == 0xFE:
                    frame = parse_civ_frame(civ_data)
                    print(
                        f"  CIV frame: cmd=0x{frame.command:02X} from=0x{frame.from_addr:02X} to=0x{frame.to_addr:02X}"
                    )

                    if frame.command == 0x03 and frame.data:
                        freq = parse_frequency_response(frame)
                        print(f"\n✅ Frequency: {freq:,} Hz ({freq / 1e6:.3f} MHz)")
                        break
                    elif frame.command == 0xFB:
                        print("  ACK")
                    elif frame.command == 0xFA:
                        print("  NAK")

        # Disconnect
        print("\n── Disconnect ──")
        p.send(p.control(0x05))
        await asyncio.sleep(0.2)
        print("✅ Done")

    finally:
        tr.close()


if __name__ == "__main__":
    asyncio.run(main())
