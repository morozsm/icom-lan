"""Integration test: connect to real IC-7610 — step by step."""

import asyncio
import sys
import os

# Add project to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from icom_lan.radio import IcomRadio


async def step_connect():
    """Step 1: Just connect and disconnect."""
    radio = IcomRadio("192.168.1.100")
    print("[1] Connecting to 192.168.1.100:50001 ...")
    try:
        await radio.connect()
        print(f"[1] ✅ Connected! radio.connected={radio.connected}")
    except Exception as e:
        print(f"[1] ❌ Failed: {type(e).__name__}: {e}")
        return False
    
    print("[1] Disconnecting ...")
    try:
        await radio.disconnect()
        print("[1] ✅ Disconnected cleanly")
    except Exception as e:
        print(f"[1] ❌ Disconnect failed: {type(e).__name__}: {e}")
        return False
    
    return True


if __name__ == "__main__":
    ok = asyncio.run(step_connect())
    sys.exit(0 if ok else 1)
