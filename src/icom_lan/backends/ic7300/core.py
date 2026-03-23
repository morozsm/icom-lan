"""Shared executable core for IC-7300 behavior.

IC-7300 inherits shared core command routing from Icom7610CoreRadio.
Profile-driven routing based on ic7300.toml capabilities and CI-V address (0x94).
"""

from ...radio import Icom7610CoreRadio

__all__ = ["Ic7300CoreRadio"]


class Ic7300CoreRadio(Icom7610CoreRadio):
    """IC-7300 model mapped to shared core with profile-driven routing.

    Inherits all command logic from Icom7610CoreRadio;
    model="IC-7300" triggers ic7300.toml profile which defines:
    - CI-V address: 0x94
    - Capabilities: audio, RF/AF, dsp, filter, scope, meters, etc.
    - Frequency ranges and band stacking
    """

    pass
