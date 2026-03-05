# Integration Tests

These tests run against a real Icom transceiver on your network.

## Prerequisites

1. Icom radio with LAN/WiFi control (IC-7610, IC-705, IC-7300, IC-9700, etc.)
2. Radio connected to the same network
3. Username and password configured in the radio

## Configuration

Set environment variables:

```bash
export ICOM_HOST=192.168.55.40      # Radio IP address
export ICOM_USER=your_username       # Radio username
export ICOM_PASS=your_password       # Radio password
export ICOM_RADIO_ADDR=0x98          # CI-V address (default: IC-7610)
```

## Running Tests

### All tests including integration:
```bash
pytest
```

### Only integration tests:
```bash
pytest -m integration
```

### Skip integration tests (unit tests only):
```bash
pytest -m "not integration"
```

### Verbose output:
```bash
pytest -m integration -v -s
```

### Specific test file:
```bash
pytest tests/integration/test_radio_integration.py -v
```

### Specific test class:
```bash
pytest tests/integration/test_radio_integration.py::TestFrequency -v
```

### Specific test:
```bash
pytest tests/integration/test_radio_integration.py::TestFrequency::test_get_frequency -v
```

## Test Categories

| Class | Description | Safe? |
|-------|-------------|-------|
| `TestConnection` | Connect/disconnect | ✅ Yes |
| `TestFrequency` | Read/write frequency | ✅ Yes |
| `TestMode` | Read/write mode | ✅ Yes |
| `TestMeters` | Read S-meter, SWR, ALC, power | ✅ Yes |
| `TestPowerControl` | Set TX power | ✅ Yes |
| `TestPTT` | Toggle PTT | ⚠️ Gated (`ICOM_ALLOW_PTT=1`) |
| `TestVFO` | VFO selection | ✅ Yes |
| `TestSplit` | Split mode | ✅ Yes |
| `TestCW` | CW keying | ❌ Gated (`ICOM_ALLOW_CW_TX=1`) |
| `TestAudioTx` | Audio TX/full-duplex | ❌ Gated (`ICOM_ALLOW_AUDIO_TX=1`) |
| `TestStatus` | Comprehensive status | ✅ Yes |
| `TestReliabilityMatrix` | Wrap/ACK/longevity/contention/readiness | ⚠️ Partially gated |
| `TestControlApiExtended` | DATA/RF/AF/squelch/NB/NR/IP+/state restore | ✅ Yes |
| `TestAudioPcm` | PCM RX/TX path | ⚠️ PCM TX gated (`ICOM_ALLOW_AUDIO_TX=1`) |
| `TestScopeIntegration` | Scope enable/capture/disable | ❌ Gated (`ICOM_ALLOW_SCOPE=1`) |
| `TestNegativeAuthConnect` | Invalid auth / unreachable connect | ❌ Gated (`ICOM_ALLOW_NEGATIVE_TESTS=1`) |

### TX Safety Gates

TX-affecting tests are **disabled by default** and require explicit env flags:

```bash
export ICOM_ALLOW_PTT=1
export ICOM_ALLOW_CW_TX=1
export ICOM_ALLOW_AUDIO_TX=1
```

Power-cycle hardware test remains separately gated:

```bash
export ICOM_ALLOW_POWER_CONTROL=1
```

Additional reliability/media gates:

```bash
export ICOM_ALLOW_SESSION_CONTENTION=1   # two concurrent clients
export ICOM_LONG_SOAK_SECONDS=600        # long-run reliability test
export ICOM_ALLOW_SCOPE=1                # scope capture integration tests
export ICOM_ALLOW_NEGATIVE_TESTS=1       # bad credentials/unreachable host tests
export ICOM_PCM_REQUIRE_FRAMES=1         # set 0 for PCM smoke-only
```

## CI/CD

Integration tests are **automatically skipped** in CI environments where
`ICOM_HOST`, `ICOM_USER`, and `ICOM_PASS` are not set.

## Troubleshooting

### Connection refused
- Check radio IP: `ping 192.168.55.40`
- Verify radio is powered on
- Verify LAN control is enabled in radio settings

### Authentication failed
- Check username/password in radio settings
- Some radios require a specific username (often "admin" or empty)

### Timeout errors
- Increase timeout in test: `IcomRadio(..., timeout=10.0)`
- Check network latency: `ping -c 5 192.168.55.40`

### Frequency not changing
- Some radios lock frequency when transmitting
- Check if PTT is stuck (power cycle radio if needed)
