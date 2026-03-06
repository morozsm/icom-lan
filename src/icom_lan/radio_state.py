"""RadioState — dual-receiver radio state model.

Holds the complete state for both MAIN and SUB receivers of the IC-7610,
plus global parameters (PTT, split, TX power).  Populated by
:class:`~icom_lan._civ_rx._CivRxMixin` from incoming CI-V frames; read
by the HTTP ``GET /api/v1/state`` endpoint.

This is intentionally additive: it runs *alongside* the existing
:class:`~icom_lan.rigctld.state_cache.StateCache` without replacing it.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

__all__ = ["ReceiverState", "RadioState"]


@dataclass(slots=True)
class ReceiverState:
    """Per-receiver (MAIN or SUB) state."""

    freq: int = 0
    mode: str = "USB"
    filter: int | None = None
    data_mode: bool = False
    att: int = 0        # dB: 0, 3, 6, …, 45
    preamp: int = 0     # 0=off, 1=P1, 2=P2
    nb: bool = False
    nr: bool = False
    digisel: bool = False
    ipplus: bool = False
    af_level: int = 0   # 0-255
    rf_gain: int = 0    # 0-255
    squelch: int = 0    # 0-255
    s_meter: int = 0    # raw 0-241
    apf_type_level: int = 0   # 0-255
    nr_level: int = 0         # 0-255
    pbt_inner: int = 0        # 0-255
    pbt_outer: int = 0        # 0-255
    nb_level: int = 0         # 0-255
    digisel_shift: int = 0    # 0-255
    af_mute: bool = False


@dataclass(slots=True)
class RadioState:
    """Full radio state: two receivers + global parameters."""

    main: ReceiverState = field(default_factory=ReceiverState)
    sub: ReceiverState = field(default_factory=ReceiverState)
    active: str = "MAIN"    # "MAIN" | "SUB"
    ptt: bool = False
    power_level: int = 0    # TX power 0-255
    split: bool = False
    dual_watch: bool = False
    cw_pitch: int = 0           # Hz
    mic_gain: int = 0           # 0-255
    key_speed: int = 0          # WPM
    notch_filter: int = 0       # 0-255
    compressor_level: int = 0   # 0-255
    break_in_delay: int = 0     # 0-255
    drive_gain: int = 0         # 0-255
    monitor_gain: int = 0       # 0-255
    vox_gain: int = 0           # 0-255
    anti_vox_gain: int = 0      # 0-255
    ref_adjust: int = 0         # 0-511
    dash_ratio: int = 0         # 28-45
    nb_depth: int = 0           # 0-9
    nb_width: int = 0           # 0-255

    def to_dict(self) -> dict:
        """Return a JSON-serialisable dict of the current radio state."""
        return {
            "active": self.active,
            "ptt": self.ptt,
            "power_level": self.power_level,
            "split": self.split,
            "dual_watch": self.dual_watch,
            "cw_pitch": self.cw_pitch,
            "mic_gain": self.mic_gain,
            "key_speed": self.key_speed,
            "notch_filter": self.notch_filter,
            "compressor_level": self.compressor_level,
            "break_in_delay": self.break_in_delay,
            "drive_gain": self.drive_gain,
            "monitor_gain": self.monitor_gain,
            "vox_gain": self.vox_gain,
            "anti_vox_gain": self.anti_vox_gain,
            "ref_adjust": self.ref_adjust,
            "dash_ratio": self.dash_ratio,
            "nb_depth": self.nb_depth,
            "nb_width": self.nb_width,
            "main": asdict(self.main),
            "sub": asdict(self.sub),
        }

    def receiver(self, which: str) -> ReceiverState:
        """Return the :class:`ReceiverState` for *which* (``"MAIN"`` or ``"SUB"``)."""
        return self.main if which == "MAIN" else self.sub
