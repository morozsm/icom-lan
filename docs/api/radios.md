# Radio Models

Presets for known Icom radios with CI-V addresses and capabilities.

::: icom_lan.radios.RadioModel

::: icom_lan.radios.get_civ_addr

## Supported Models

| Model | CI-V Address | Receivers | LAN | WiFi |
|-------|-------------|-----------|-----|------|
| IC-7610 | 0x98 | 2 | ✅ | ❌ |
| IC-7300 | 0x94 | 1 | ✅ | ❌ |
| IC-705 | 0xA4 | 1 | ✅ | ✅ |
| IC-9700 | 0xA2 | 2 | ✅ | ❌ |
| IC-R8600 | 0x96 | 1 | ✅ | ❌ |
| IC-7851 | 0x8E | 2 | ✅ | ❌ |

## Usage

```python
from icom_lan import IcomRadio, get_civ_addr

# Look up CI-V address by model name
addr = get_civ_addr("IC-705")  # returns 0xA4

# Use with IcomRadio
radio = IcomRadio("192.168.1.100", radio_addr=addr)
```
