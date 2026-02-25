# Synchronous API

Blocking wrapper around the async `IcomRadio` for use without `async/await`.

::: icom_lan.sync.IcomRadio

## Usage

```python
from icom_lan.sync import IcomRadio

with IcomRadio("192.168.1.100", username="u", password="p") as radio:
    freq = radio.get_frequency()
    print(f"Frequency: {freq:,} Hz")

    radio.set_frequency(14_074_000)
    radio.set_mode("USB")

    print(f"S-meter: {radio.get_s_meter()}")
    print(f"SWR: {radio.get_swr()}")
```

### Common sync helpers

```python
mode, filt = radio.get_mode_info()
radio.set_filter(2)
att = radio.get_attenuator()
pre = radio.get_preamp()
state = radio.snapshot_state()
radio.restore_state(state)
```

!!! tip "When to use sync vs async"
    Use the **sync API** for simple scripts, CLI tools, and Jupyter notebooks.
    Use the **async API** for applications that need concurrent operations,
    real-time audio streaming, or integration with async frameworks.
