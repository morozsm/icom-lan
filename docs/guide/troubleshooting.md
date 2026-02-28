# Troubleshooting

## Connection Issues

### "Radio did not respond to discovery"

**Symptom:** `TimeoutError: Radio did not respond to discovery after 10 attempts`

**Causes:**

1. **Wrong IP address** — verify your radio's IP in its network settings menu
2. **Radio not on network** — ensure the radio is powered on and connected to your LAN
3. **Firewall blocking UDP** — allow UDP ports 50001–50003
4. **Different subnet** — the client and radio must be on the same subnet (or have routing configured)
5. **Network Control disabled** — enable "Remote Control" in your radio's network settings

**Debug:**

```bash
# Can you reach the radio?
ping 192.168.1.100

# Is the port open?
nc -u -z 192.168.1.100 50001

# Try discovery
icom-lan discover
```

### "Authentication failed"

**Symptom:** `AuthenticationError: Authentication failed (error=0xFEFFFFFF)`

**Causes:**

1. **Wrong username/password** — check your radio's Network User settings
2. **Too many connections** — the radio supports limited concurrent connections. Disconnect other clients (RS-BA1, wfview, etc.)
3. **Account disabled** — ensure the network user account is enabled

### "CI-V response timed out"

**Symptom:** `TimeoutError: CI-V response timed out`

**Causes:**

1. **CI-V port negotiation failed** — this usually means the conninfo exchange didn't complete properly
2. **Radio busy** — another application may be holding the CI-V stream
3. **Network congestion** — try increasing the timeout
4. **Command pacing too aggressive for current link/rig state** — increase `ICOM_CIV_MIN_INTERVAL_MS` (e.g., 50-80)

**Debug:**

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# This will show the full handshake sequence
async with IcomRadio("192.168.1.100", ...) as radio:
    freq = await radio.get_frequency()
```

Look for:
- `Status: civ_port=50002` — confirms port negotiation succeeded
- `CI-V port not in status, using default` — port negotiation failed, likely a GUID issue

### Connection drops after ~30 seconds

**Symptom:** Commands work initially, then start timing out.

**Cause:** Keep-alive pings stopped. This shouldn't happen under normal use, but can occur if:

- The event loop is blocked for extended periods
- The Python process is suspended

The library sends pings every 500ms automatically. If the radio doesn't receive pings for its timeout period (usually 10–30 seconds), it drops the connection.

## Command Issues

### "Radio rejected set_frequency"

**Symptom:** `CommandError: Radio rejected set_frequency(999999999)`

The radio returned NAK (0xFA). Possible causes:

- Frequency out of the radio's supported range
- Radio is in a mode that doesn't allow frequency changes
- VFO lock is enabled

### SWR/ALC always returns 0

These meters only report values during transmit. When receiving, they return 0.

### CW text not sending

- Ensure the radio is in CW mode (`await radio.set_mode("CW")`)
- Check that CW keying speed is set appropriately on the radio
- Text must be ASCII A–Z, 0–9

## Network Tips

### Static IP

Assign a static IP to your radio to avoid DHCP lease changes:

- IC-7610: **Menu → Set → Network → IP Address** — set to Manual
- Use an IP outside your DHCP range

### WiFi vs Ethernet

- **Ethernet** is more reliable with lower latency
- **WiFi** (IC-705) works but may experience higher packet loss
- For WiFi radios, increase the timeout: `timeout=10.0`

### VPN / Remote Access

The library works over VPN tunnels if UDP traffic is forwarded:

- Ensure your VPN supports UDP
- Allow ports 50001–50003
- Increase timeout for high-latency links
- Discovery (broadcast) won't work over VPN — specify the radio's IP directly

## Retry / Fail-Fast Policy

Recommended policy for real-radio automation:

- **Retry allowed (soft-fail):** idempotent reads (`get_*`) and non-critical telemetry.
- **Retry with recovery:** command timeout after all retries -> one reconnect recovery path -> retry command once.
- **Fail-fast (no blind retries):** safety-critical toggles (`PTT`, `power_control`, CW stop/start transactions) when state uncertainty is dangerous.
- **Always log on timeout:** command name, attempt, timeout flag, recovered flag, duration.

In integration soak, use structured JSON logs with canonical fields:

- `test`, `step`, `cmd`, `attempt`, `timeout`, `recovered`, `duration_ms`

## Soak / Integration Diagnostics

Use soak mode to capture rare timeout behavior with structured logs:

```bash
export ICOM_SOAK_SECONDS=120
pytest -m integration tests/integration/test_radio_integration.py::TestSoak::test_soak_retries_and_logging -q -s
```

Look for:

- `{"ev":"timeout", ...}` — timeout event
- `{"ev":"recover", ...}` — reconnect recovery attempts
- `SOAK_SUMMARY {...}` — final counters (`timeouts`, `timeouts_unrecovered`, etc.)

## Getting Help

1. Enable debug logging (see above)
2. [Open an issue](https://github.com/morozsm/icom-lan/issues) with:
    - Your radio model
    - Python version
    - OS
    - Debug log output
    - Steps to reproduce

## CI-V Commands Timeout During Scope/Waterfall

**Symptom:** `get_frequency()`, `get_power()` etc. return cached values or raise
`TimeoutError` while scope/waterfall is active.

**Cause:** Fixed in v0.8.0. In earlier versions, the RX pump processed one packet
at a time. Scope data (~225 packets/sec) would queue ahead of command responses.

**Solution:** Upgrade to v0.8.0+. The drain-all RX pattern processes all queued
packets each iteration.

## Connection Fails With `civ_port=0`

**Symptom:** Log shows `Status: civ_port=0, audio_port=0` repeatedly.

**Cause:** The radio needs time to recover between connections. Rapid reconnects
(especially during development/testing) cause this.

**Solutions:**
1. Wait 30–60 seconds before reconnecting
2. v0.8.0+ uses optimistic default ports — connects instantly even with `civ_port=0`
3. If persistent: power-cycle the radio's network (Menu → Set → Network → LAN → Off/On)

## Audio Cuts Out on Mobile (Safari iOS)

**Symptom:** Audio stops when Safari goes to background, doesn't resume on return.

**Cause:** iOS suspends WebSocket connections and AudioContext in background tabs.

**Solution:** v0.8.0+ adds `visibilitychange` listener that resumes AudioContext
and reconnects the audio WebSocket when the tab returns to foreground. Audio
may stutter briefly during reconnection.

## Audio Stutters Over VPN/Tailscale

**Symptom:** Audio playback has gaps or stutters when accessing the Web UI remotely.

**Cause:** Network jitter from VPN tunneling.

**Solution:** v0.8.0+ uses a 200ms jitter buffer (up from 50ms). For very high
latency connections, this may still be insufficient — consider a local deployment.
