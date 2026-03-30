"""RadioState — dual-receiver radio state model.

Holds the complete state for both MAIN and SUB receivers of the IC-7610,
plus global parameters (PTT, split, TX power).  Populated by
:class:`~icom_lan._civ_rx.CivRuntime` from incoming CI-V frames; read
by the HTTP ``GET /api/v1/state`` endpoint.

This is intentionally additive: it runs *alongside* the existing
:class:`~icom_lan.rigctld.state_cache.StateCache` without replacing it.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from .types import ScopeFixedEdge

__all__ = ["ReceiverState", "ScopeControlsState", "RadioState"]


@dataclass(slots=True)
class ReceiverState:
    """Per-receiver (MAIN or SUB) state."""

    freq: int = 0
    mode: str = "USB"
    filter: int | None = None
    filter_width: int | None = None
    data_mode: int = 0
    att: int = 0  # dB: 0, 3, 6, …, 45
    preamp: int = 0  # 0=off, 1=P1, 2=P2
    nb: bool = False
    nr: bool = False
    digisel: bool = False
    ipplus: bool = False
    s_meter_sql_open: bool = False
    agc: int = 0
    audio_peak_filter: int = 0
    auto_notch: bool = False
    manual_notch: bool = False
    twin_peak_filter: bool = False
    filter_shape: int = 0
    agc_time_constant: int = 0
    af_level: int = 0  # 0-255
    rf_gain: int = 0  # 0-255
    squelch: int = 0  # 0-255
    s_meter: int = 0  # raw 0-241
    apf_type_level: int = 0  # 0-255
    nr_level: int = 0  # 0-255
    pbt_inner: int = 128  # 0-255, 128=center
    pbt_outer: int = 128  # 0-255, 128=center
    nb_level: int = 0  # 0-255
    digisel_shift: int = 0  # 0-255
    af_mute: bool = False
    contour: int = 0  # 0=off, >0=on (S-DX / contour DSP)
    if_shift: int = 0  # signed Hz, e.g. -1200..+1200
    repeater_tone: bool = False
    repeater_tsql: bool = False
    tone_freq: int = 0  # centihz, e.g. 8850 = 88.50 Hz
    tsql_freq: int = 0  # centihz, e.g. 8850 = 88.50 Hz


@dataclass(slots=True)
class ScopeControlsState:
    """Readable IC-7610 scope-control state."""

    receiver: int = 0
    dual: bool = False
    mode: int = 0
    span: int = 0
    edge: int = 0
    hold: bool = False
    ref_db: float = 0.0
    speed: int = 0
    during_tx: bool = False
    center_type: int = 0
    vbw_narrow: bool = False
    rbw: int = 0
    fixed_edge: ScopeFixedEdge = field(
        default_factory=lambda: ScopeFixedEdge(
            range_index=0,
            edge=0,
            start_hz=0,
            end_hz=0,
        )
    )


@dataclass(slots=True)
class RadioState:
    """Full radio state: two receivers + global parameters."""

    main: ReceiverState = field(default_factory=ReceiverState)
    sub: ReceiverState = field(default_factory=ReceiverState)
    active: str = "MAIN"  # "MAIN" | "SUB"
    power_on: bool = True  # Radio power status (on/off)
    ptt: bool = False
    power_level: int = 0  # TX power 0-255
    split: bool = False
    dual_watch: bool = False
    scanning: bool = False
    tuning_step: int = 0
    overflow: bool = False
    tuner_status: int = 0  # 0=off, 1=on, 2=tuning
    tx_freq_monitor: bool = False
    rit_freq: int = 0  # signed Hz (±9999)
    rit_on: bool = False
    rit_tx: bool = False
    comp_meter: int = 0  # raw 0-255
    vd_meter: int = 0  # raw 0-255 (supply voltage)
    id_meter: int = 0  # raw 0-255 (drain current)
    cw_pitch: int = 0  # Hz
    mic_gain: int = 0  # 0-255
    key_speed: int = 0  # WPM
    notch_filter: int = 0  # 0-255
    main_sub_tracking: bool = False
    compressor_on: bool = False
    compressor_level: int = 0  # 0-255
    monitor_on: bool = False
    break_in_delay: int = 0  # 0-255
    break_in: int = 0  # 0=off, 1=semi, 2=full
    dial_lock: bool = False
    drive_gain: int = 0  # 0-255
    monitor_gain: int = 0  # 0-255
    vox_on: bool = False
    vox_gain: int = 0  # 0-255
    anti_vox_gain: int = 0  # 0-255
    vox_delay: int = 0  # 0-20 (0.0-2.0 sec in 0.1s steps)
    ssb_tx_bandwidth: int = 0  # 0=wide, 1=mid, 2=nar
    ref_adjust: int = 0  # 0-511
    dash_ratio: int = 0  # 28-45
    nb_depth: int = 0  # 0-9
    nb_width: int = 0  # 0-255
    scope_controls: ScopeControlsState = field(default_factory=ScopeControlsState)

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serialisable dict of the current radio state."""
        return {
            "active": self.active,
            "power_on": self.power_on,
            "ptt": self.ptt,
            "power_level": self.power_level,
            "split": self.split,
            "dual_watch": self.dual_watch,
            "scanning": self.scanning,
            "tuning_step": self.tuning_step,
            "overflow": self.overflow,
            "tuner_status": self.tuner_status,
            "tx_freq_monitor": self.tx_freq_monitor,
            "rit_freq": self.rit_freq,
            "rit_on": self.rit_on,
            "rit_tx": self.rit_tx,
            "comp_meter": self.comp_meter,
            "vd_meter": self.vd_meter,
            "id_meter": self.id_meter,
            "cw_pitch": self.cw_pitch,
            "mic_gain": self.mic_gain,
            "key_speed": self.key_speed,
            "notch_filter": self.notch_filter,
            "main_sub_tracking": self.main_sub_tracking,
            "compressor_on": self.compressor_on,
            "compressor_level": self.compressor_level,
            "monitor_on": self.monitor_on,
            "break_in_delay": self.break_in_delay,
            "break_in": self.break_in,
            "dial_lock": self.dial_lock,
            "drive_gain": self.drive_gain,
            "monitor_gain": self.monitor_gain,
            "vox_on": self.vox_on,
            "vox_gain": self.vox_gain,
            "anti_vox_gain": self.anti_vox_gain,
            "vox_delay": self.vox_delay,
            "ssb_tx_bandwidth": self.ssb_tx_bandwidth,
            "ref_adjust": self.ref_adjust,
            "dash_ratio": self.dash_ratio,
            "nb_depth": self.nb_depth,
            "nb_width": self.nb_width,
            "scope_controls": asdict(self.scope_controls),
            "main": asdict(self.main),
            "sub": asdict(self.sub),
        }

    def receiver(self, which: str) -> ReceiverState:
        """Return the :class:`ReceiverState` for *which* (``"MAIN"`` or ``"SUB"``)."""
        return self.main if which == "MAIN" else self.sub
