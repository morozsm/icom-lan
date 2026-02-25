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
| `TestPTT` | Toggle PTT | ⚠️ No TX |
| `TestVFO` | VFO selection | ✅ Yes |
| `TestSplit` | Split mode | ✅ Yes |
| `TestCW` | CW keying | ❌ Requires antenna |
| `TestStatus` | Comprehensive status | ✅ Yes |

### CW Tests

CW tests are **disabled by default** because they require an antenna or dummy load.
To enable, remove the `@pytest.mark.skip` decorator in `test_radio_integration.py`.

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
