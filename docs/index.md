# icom-lan

**Python library for controlling Icom transceivers over LAN (UDP).**

Direct connection to your radio — no wfview, hamlib, or RS-BA1 required.

---

<div class="grid cards" markdown>

- :material-rocket-launch:{ .lg .middle } **Quick Start**

    ---

    Get up and running in under 5 minutes.

    [:octicons-arrow-right-24: Getting Started](guide/quickstart.md)

- :material-console:{ .lg .middle } **CLI Tool**

    ---

    Control your radio from the terminal.

    [:octicons-arrow-right-24: CLI Reference](guide/cli.md)

- :material-api:{ .lg .middle } **API Reference**

    ---

    Full async Python API documentation.

    [:octicons-arrow-right-24: API Docs](api/radio.md)

- :material-radio-tower:{ .lg .middle } **Protocol Internals**

    ---

    Deep dive into the Icom LAN UDP protocol.

    [:octicons-arrow-right-24: Protocol](internals/protocol.md)

</div>

---

## Features

- :white_check_mark: **Direct UDP connection** — no intermediate software
- :white_check_mark: **Full CI-V command set** — frequency, mode/filter, power, meters, PTT, CW keying, VFO, split, ATT/PREAMP
- :white_check_mark: **Audio streaming** — RX/TX with jitter buffer and full-duplex support
- :white_check_mark: **Network discovery** — find radios on your LAN automatically
- :white_check_mark: **CLI tool** — `icom-lan status`, `icom-lan freq 14.074m`
- :white_check_mark: **Async + Sync API** — async by default, blocking wrapper available
- :white_check_mark: **Auto-reconnect** — watchdog + exponential backoff (opt-in)
- :white_check_mark: **Multi-radio presets** — IC-7610, IC-705, IC-7300, IC-9700 and more
- :white_check_mark: **Zero dependencies** — pure Python, stdlib only
- :white_check_mark: **Type-annotated** — full `py.typed` support for IDE autocompletion
- :white_check_mark: **950+ tests** — high coverage with golden protocol fixtures, TCP wire tests, and real-radio integration suite

## Supported Radios

| Radio | Status | CI-V Address |
|-------|--------|-------------|
| IC-7610 | :white_check_mark: Tested | `0x98` |
| IC-705 | :material-help-circle: Should work | `0xA4` |
| IC-7300 | :material-help-circle: Should work | `0x94` |
| IC-9700 | :material-help-circle: Should work | `0xA2` |
| IC-7851 | :material-help-circle: Should work | `0x8E` |
| IC-R8600 | :material-help-circle: Should work | `0x96` |

Any Icom radio with LAN/WiFi control should work — the CI-V address is configurable.

## Minimal Example

```python
import asyncio
from icom_lan import IcomRadio

async def main():
    async with IcomRadio("192.168.1.100", username="user", password="pass") as radio:
        freq = await radio.get_frequency()
        print(f"{freq / 1e6:.3f} MHz")

asyncio.run(main())
```

## License

MIT — see [LICENSE](https://github.com/morozsm/icom-lan/blob/main/LICENSE).

Protocol knowledge derived from the [wfview](https://wfview.org/) project's reverse engineering work. This is an independent clean-room implementation.

!!! note "Trademark Notice"
    Icom™ and the Icom logo are registered trademarks of [Icom Incorporated](https://www.icomjapan.com/). This project is not affiliated with, endorsed by, or sponsored by Icom. Product names are used solely for identification and compatibility purposes (nominative fair use).
