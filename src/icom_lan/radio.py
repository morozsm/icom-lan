"""IcomRadio — high-level async API for Icom transceivers over LAN.

Usage::

    async with IcomRadio("192.168.1.100", username="u", password="p") as radio:
        freq = await radio.get_frequency()
        print(f"Freq: {freq / 1e6:.3f} MHz")
        await radio.set_frequency(7_074_000)
        await radio.set_mode("USB")
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
import warnings
from typing import TYPE_CHECKING, AsyncGenerator

if TYPE_CHECKING:
    from typing import Any, Awaitable, Callable

from .commands import (
    CONTROLLER_ADDR,
    RECEIVER_MAIN,
    _level_bcd_decode,
    build_civ_frame,
    get_alc,
    get_af_mute,
    get_attenuator as get_attenuator_cmd,
    get_apf_type_level,
    get_band_edge_freq,
    get_data_mode as get_data_mode_cmd,
    get_dash_ratio,
    get_digisel_shift,
    get_drive_gain,
    get_frequency,
    get_break_in_delay,
    get_break_in,
    get_compressor_level,
    get_compressor,
    get_cw_pitch,
    get_dial_lock,
    get_key_speed,
    get_mic_gain,
    get_mode,
    get_monitor_gain,
    get_monitor,
    get_nb_depth,
    get_nb_level,
    get_nb_width,
    get_notch_filter,
    get_nr_level,
    get_pbt_inner,
    get_pbt_outer,
    get_power,
    get_s_meter_sql_status,
    get_overflow_status,
    get_agc,
    get_audio_peak_filter,
    get_auto_notch,
    get_filter_shape,
    get_digisel,
    get_manual_notch,
    get_preamp as get_preamp_cmd,
    get_ref_adjust,
    get_s_meter,
    get_swr,
    get_ssb_tx_bandwidth,
    get_main_sub_tracking as _get_main_sub_tracking_cmd,
    set_main_sub_tracking as _set_main_sub_tracking_cmd,
    get_twin_peak_filter,
    get_agc_time_constant,
    get_various_squelch,
    get_vox,
    get_vox_gain,
    get_anti_vox_gain,
    parse_ack_nak,
    parse_bool_response,
    parse_civ_frame,
    parse_data_mode_response,
    parse_frequency_response,
    parse_level_response,
    parse_meter_response,
    parse_mode_response,
    parse_scope_center_type_response,
    parse_scope_during_tx_response,
    parse_scope_edge_response,
    parse_scope_fixed_edge_response,
    parse_scope_hold_response,
    parse_scope_main_sub_response,
    parse_scope_mode_response,
    parse_scope_rbw_response,
    parse_scope_ref_response,
    parse_scope_single_dual_response,
    parse_scope_span_response,
    parse_scope_speed_response,
    parse_scope_vbw_response,
    power_off,
    power_on,
    ptt_off,
    ptt_on,
    scope_data_output as _scope_data_output_cmd,
    get_scope_center_type as _get_scope_center_type_cmd,
    get_scope_during_tx as _get_scope_during_tx_cmd,
    get_scope_edge as _get_scope_edge_cmd,
    get_scope_fixed_edge as _get_scope_fixed_edge_cmd,
    get_scope_hold as _get_scope_hold_cmd,
    get_scope_main_sub as _get_scope_main_sub_cmd,
    get_scope_mode as _get_scope_mode_cmd,
    get_scope_rbw as _get_scope_rbw_cmd,
    get_scope_ref as _get_scope_ref_cmd,
    get_scope_single_dual as _get_scope_single_dual_cmd,
    get_scope_span as _get_scope_span_cmd,
    get_scope_speed as _get_scope_speed_cmd,
    get_scope_vbw as _get_scope_vbw_cmd,
    scope_on as _scope_on_cmd,
    scope_set_center_type as _scope_set_center_type_cmd,
    scope_set_during_tx as _scope_set_during_tx_cmd,
    scope_set_edge as _scope_set_edge_cmd,
    scope_set_fixed_edge as _scope_set_fixed_edge_cmd,
    scope_set_hold as _scope_set_hold_cmd,
    scope_set_mode as _scope_set_mode_cmd,
    scope_set_rbw as _scope_set_rbw_cmd,
    scope_set_ref as _scope_set_ref_cmd,
    scope_set_span as _scope_set_span_cmd,
    scope_set_speed as _scope_set_speed_cmd,
    scope_set_vbw as _scope_set_vbw_cmd,
    scope_main_sub as _scope_main_sub_cmd,
    scope_single_dual as _scope_single_dual_cmd,
    select_vfo as _select_vfo_cmd,
    send_cw,
    set_af_mute,
    set_apf_type_level,
    set_attenuator,
    set_attenuator_level,
    set_break_in_delay,
    set_break_in,
    set_compressor_level,
    set_compressor,
    set_cw_pitch,
    set_data_mode as set_data_mode_cmd,
    set_dash_ratio,
    set_dial_lock,
    set_digisel,
    set_digisel_shift,
    set_drive_gain,
    set_agc,
    set_audio_peak_filter,
    set_auto_notch,
    set_filter_shape,
    set_key_speed,
    set_manual_notch,
    set_mic_gain,
    set_monitor,
    set_monitor_gain,
    set_nb,
    set_nb_depth,
    set_nb_level,
    set_nb_width,
    set_notch_filter,
    set_nr,
    set_nr_level,
    set_pbt_inner,
    set_pbt_outer,
    set_ref_adjust,
    set_ssb_tx_bandwidth,
    set_twin_peak_filter,
    set_agc_time_constant,
    set_vox,
    get_nb,
    get_nr,
    get_ip_plus,
    set_ip_plus,
    set_frequency,
    set_mode,
    set_vox_gain,
    set_anti_vox_gain,
    set_power,
    get_rf_gain,
    set_rf_gain,
    get_af_level,
    set_af_level,
    set_preamp,
    set_split,
    stop_cw,
    vfo_a_equals_b,
    vfo_swap,
    # Transceiver status family (#136)
    get_power_meter,
    get_comp_meter,
    get_vd_meter,
    get_id_meter,
    get_tuner_status,
    set_tuner_status,
    get_xfc_status,
    set_xfc_status,
    get_tx_freq_monitor,
    set_tx_freq_monitor,
    speech,
    get_transceiver_id,
    get_rit_frequency,
    set_rit_frequency,
    get_rit_status,
    set_rit_status,
    get_rit_tx_status,
    set_rit_tx_status,
    parse_rit_frequency_response,
    # VFO / Dual Watch / Scanning (#132)
    get_tuning_step,
    set_tuning_step,
    start_scan,
    stop_scan,
    get_dual_watch,
    set_dual_watch,
    quick_dual_watch,
    quick_split,
    # Tone/TSQL (#134)
    get_repeater_tone as _get_repeater_tone_cmd,
    set_repeater_tone as _set_repeater_tone_cmd,
    get_repeater_tsql as _get_repeater_tsql_cmd,
    set_repeater_tsql as _set_repeater_tsql_cmd,
    get_tone_freq as _get_tone_freq_cmd,
    set_tone_freq as _set_tone_freq_cmd,
    get_tsql_freq as _get_tsql_freq_cmd,
    set_tsql_freq as _set_tsql_freq_cmd,
    parse_tone_freq_response,
    parse_tsql_freq_response,
    _SUB_REPEATER_TONE,
    _SUB_REPEATER_TSQL,
    # System/Config commands (#135)
    get_antenna_1,
    set_antenna_1,
    get_antenna_2,
    set_antenna_2,
    get_rx_antenna_ant1,
    set_rx_antenna_ant1,
    get_rx_antenna_ant2,
    set_rx_antenna_ant2,
    get_acc1_mod_level,
    set_acc1_mod_level,
    get_usb_mod_level,
    set_usb_mod_level,
    get_lan_mod_level,
    set_lan_mod_level,
    get_data_off_mod_input,
    set_data_off_mod_input,
    get_data1_mod_input,
    set_data1_mod_input,
    get_data2_mod_input,
    set_data2_mod_input,
    get_data3_mod_input,
    set_data3_mod_input,
    get_civ_transceive,
    set_civ_transceive,
    get_civ_output_ant,
    set_civ_output_ant,
    get_system_date,
    set_system_date,
    parse_system_date_response,
    get_system_time,
    set_system_time,
    parse_system_time_response,
    get_utc_offset,
    set_utc_offset,
    parse_utc_offset_response,
    # Memory and band-stacking (#133)
    build_memory_mode_set,
    build_memory_write,
    build_memory_to_vfo,
    build_memory_clear,
    build_memory_contents_set,
    build_band_stack_set,
)
from .exceptions import (
    CommandError,
    ConnectionError,
    TimeoutError,
)
from .profiles import RadioProfile, resolve_radio_profile
from ._audio_transcoder import PcmOpusTranscoder, create_pcm_opus_transcoder
from .audio import AudioPacket, AudioStats, AudioStream
from .commander import IcomCommander, Priority
from .rigctld.state_cache import StateCache
from .civ import (
    CivEvent,
    CivRequestTracker,
)
from .radio_state import RadioState
from .scope import ScopeAssembler, ScopeFrame
from .transport import IcomTransport
from .types import (
    AgcMode,
    AudioCapabilities,
    AudioPeakFilter,
    AudioCodec,
    BandStackRegister,
    BreakInMode,
    CivFrame,
    FilterShape,
    MemoryChannel,
    Mode,
    ScopeFixedEdge,
    ScopeCompletionPolicy,
    SsbTxBandwidth,
    get_audio_capabilities,
)

# Import split modules
from ._connection_state import RadioConnectionState
from ._audio_recovery import AudioRecoveryState, _AudioRecoveryMixin
from ._civ_rx import _CivRxMixin
from ._control_phase import (
    CONNINFO_SIZE,  # noqa: F401 (re-export for tests)
    OPENCLOSE_SIZE,  # noqa: F401 (re-export for tests)
    STATUS_SIZE,  # noqa: F401 (re-export for tests)
    TOKEN_ACK_SIZE,  # noqa: F401 (re-export for tests)
    _ControlPhaseMixin,
)

__all__ = [
    "AudioRecoveryState",
    "Icom7610CoreRadio",
    "IcomRadio",
    "RadioProfile",
    "AudioCodec",
    "RadioConnectionState",
    "ScopeFrame",
    "ScopeCompletionPolicy",
]


logger = logging.getLogger(__name__)

_AUDIO_CAPABILITIES = get_audio_capabilities()
_DEFAULT_AUDIO_CODEC = _AUDIO_CAPABILITIES.default_codec
_DEFAULT_AUDIO_SAMPLE_RATE = _AUDIO_CAPABILITIES.default_sample_rate_hz
# Default TTLs (seconds) for the GET-command cache fallback paths.
_DEFAULT_CACHE_TTL: dict[str, float] = {"freq": 10.0, "mode": 10.0, "rf_power": 30.0}


class Icom7610CoreRadio(_ControlPhaseMixin, _CivRxMixin, _AudioRecoveryMixin):
    """High-level async interface for controlling an Icom transceiver over LAN.

    Manages two UDP connections:
    - Control port (default 50001): authentication and session management.
    - CI-V port (default 50002): CI-V command exchange.

    Args:
        host: Radio IP address or hostname.
        port: Radio control port.
        username: Authentication username.
        password: Authentication password.
        radio_addr: Optional CI-V address override. If omitted, uses
            the resolved profile default.
        timeout: Default timeout for operations in seconds.

    Example::

        async with IcomRadio("192.168.1.100", username="u", password="p") as radio:
            freq = await radio.get_frequency()
            await radio.set_frequency(7_074_000)
    """

    def __init__(
        self,
        host: str,
        port: int = 50001,
        username: str = "",
        password: str = "",
        radio_addr: int | None = None,
        timeout: float = 5.0,
        audio_codec: AudioCodec | int = _DEFAULT_AUDIO_CODEC,
        audio_sample_rate: int = _DEFAULT_AUDIO_SAMPLE_RATE,
        auto_reconnect: bool = False,
        reconnect_delay: float = 2.0,
        reconnect_max_delay: float = 60.0,
        watchdog_timeout: float = 30.0,
        auto_recover_audio: bool = True,
        on_audio_recovery: "Callable[[AudioRecoveryState], None] | None" = None,
        cache_ttl_s: "dict[str, float] | None" = None,
        profile: RadioProfile | str | None = None,
        model: str | None = None,
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        if radio_addr is not None and not (0 <= radio_addr <= 0xFF):
            raise ValueError("radio_addr must be a single byte (0..255).")
        self._timeout = timeout
        self._audio_codec = AudioCodec(audio_codec)
        self._audio_sample_rate = audio_sample_rate
        self._ctrl_transport = IcomTransport()
        self._civ_transport: IcomTransport | None = None
        self._audio_transport: IcomTransport | None = None
        self._audio_stream: AudioStream | None = None
        self._pcm_transcoder: PcmOpusTranscoder | None = None
        self._pcm_transcoder_fmt: tuple[int, int, int] | None = None
        self._pcm_tx_fmt: tuple[int, int, int] | None = None
        self._conn_state = RadioConnectionState.DISCONNECTED
        self._token: int = 0
        self._tok_request: int = 0
        self._auth_seq: int = 0
        self._civ_port: int = 0
        self._audio_port: int = 0
        self._civ_send_seq: int = 0
        self._audio_send_seq: int = 0
        self._civ_lock = asyncio.Lock()
        self._last_civ_send_monotonic: float = 0.0
        self._civ_min_interval: float = (
            float(os.environ.get("ICOM_CIV_MIN_INTERVAL_MS", "35")) / 1000.0
        )
        self._commander: IcomCommander | None = None
        self._filter_width: int | None = None
        self._attenuator_state: bool | None = None
        self._preamp_level: int | None = None
        self._last_freq_hz: int | None = None
        self._last_mode: Mode | None = None
        self._last_power: int | None = None
        self._last_split: bool | None = None
        self._last_vfo: str | None = None
        self._token_task: asyncio.Task | None = None
        self._auto_reconnect = auto_reconnect
        self._reconnect_delay = reconnect_delay
        self._reconnect_max_delay = reconnect_max_delay
        self._watchdog_timeout = watchdog_timeout
        self._watchdog_task: asyncio.Task | None = None
        self._reconnect_task: asyncio.Task | None = None
        self._auto_recover_audio = auto_recover_audio
        self._on_audio_recovery = on_audio_recovery
        self._on_reconnect: Callable[[], None] | None = None
        self._civ_stream_ready: bool = False
        self._civ_recovering: bool = False
        self._civ_recovery_lock = asyncio.Lock()
        self._civ_recovery_wait_timeout: float = float(
            os.environ.get("ICOM_CIV_RECOVERY_WAIT_TIMEOUT_S", "12.0")
        )
        self._civ_ready_idle_timeout: float = float(
            os.environ.get("ICOM_CIV_READY_IDLE_TIMEOUT_S", "5.0")
        )
        self._pcm_rx_user_callback: Callable[[bytes | None], None] | None = None
        self._pcm_rx_jitter_depth: int = 5
        self._opus_rx_user_callback: Callable[[AudioPacket | None], None] | None = None
        self._opus_rx_jitter_depth: int = 5
        # AudioBus — lazy-initialized pub/sub for multi-consumer audio
        self._audio_bus: Any = None
        self._scope_assembler: ScopeAssembler = ScopeAssembler()
        self._scope_callback: Callable[[ScopeFrame], Any] | None = None
        self._civ_rx_task: asyncio.Task[None] | None = None
        self._civ_request_tracker = CivRequestTracker()
        self._civ_epoch = self._civ_request_tracker.generation
        self._scope_frame_queue: asyncio.Queue[ScopeFrame] = asyncio.Queue(maxsize=64)
        self._scope_activity_counter: int = 0
        self._scope_activity_event = asyncio.Event()
        self._civ_event_queue: asyncio.Queue[CivEvent] = asyncio.Queue(maxsize=256)
        self._civ_ack_sink_grace: float = (
            float(os.environ.get("ICOM_CIV_ACK_SINK_GRACE_MS", "120")) / 1000.0
        )
        self._civ_waiter_ttl_gc_interval: float = 1.0
        self._civ_last_waiter_gc_monotonic: float = time.monotonic()
        self._civ_retry_slice_timeout: float = (
            float(os.environ.get("ICOM_CIV_RETRY_SLICE_MS", "150")) / 1000.0
        )
        self._state_cache: StateCache = StateCache()
        self._on_state_change: Callable | None = None  # set by server
        self._radio_state: RadioState = RadioState()  # may be replaced by WebServer
        _ttl = {**_DEFAULT_CACHE_TTL, **(cache_ttl_s or {})}
        self._cache_ttl_freq: float = _ttl["freq"]
        self._cache_ttl_mode: float = _ttl["mode"]
        self._cache_ttl_rf_power: float = _ttl["rf_power"]
        self._profile = resolve_radio_profile(
            profile=profile,
            model=model,
            radio_addr=radio_addr,
        )
        self._radio_addr = (
            self._profile.civ_addr if radio_addr is None else radio_addr
        )
        # GET commands use a shorter timeout than the general connection timeout.
        # wfview-style: send once, short deadline, fall back to cache.
        self._civ_get_timeout: float = min(timeout, 2.0)

    def __del__(self) -> None:
        """Emit WARN if instance is collected while still connected (forgotten teardown)."""
        try:
            if self._conn_state == RadioConnectionState.CONNECTED:
                logger.warning(
                    "Radio collected with active connection/tasks; "
                    "ensure disconnect() or async with is used."
                )
        except Exception:
            pass  # avoid raising in destructor

    @property
    def conn_state(self) -> RadioConnectionState:
        """Current connection state."""
        return self._conn_state

    @property
    def connected(self) -> bool:
        """Whether the radio is currently connected and CI-V transport is healthy."""
        if self._conn_state != RadioConnectionState.CONNECTED:
            return False
        civ = self._civ_transport
        if civ is None:
            return False
        # Check for UDP errors (only on real IcomTransport, not mocks)
        error_count = getattr(civ, "_udp_error_count", None)
        if isinstance(error_count, int) and error_count > 0:
            return False
        return True

    @property
    def control_connected(self) -> bool:
        """Whether the control transport is alive (LAN session active)."""
        ctrl = self._ctrl_transport
        if ctrl is None:
            return False
        return getattr(ctrl, "_udp_transport", None) is not None

    @property
    def radio_ready(self) -> bool:
        """Whether CI-V stream is healthy enough for client operations."""
        if not self.connected:
            return False
        if self._civ_recovering or not self._civ_stream_ready:
            return False
        last = getattr(self, "_last_civ_data_received", None)
        if not isinstance(last, (int, float)):
            return False
        return (time.monotonic() - float(last)) <= self._civ_ready_idle_timeout

    # ------------------------------------------------------------------
    # Backwards-compatible property shims for _connected / _intentional_disconnect
    # (used by tests and internal loops — keep in sync with _conn_state)
    # ------------------------------------------------------------------

    @property
    def _connected(self) -> bool:
        return self._conn_state == RadioConnectionState.CONNECTED

    @_connected.setter
    def _connected(self, value: bool) -> None:
        if value:
            self._conn_state = RadioConnectionState.CONNECTED
        elif self._conn_state == RadioConnectionState.CONNECTED:
            self._conn_state = RadioConnectionState.DISCONNECTED

    @property
    def _intentional_disconnect(self) -> bool:
        return self._conn_state == RadioConnectionState.DISCONNECTED

    @_intentional_disconnect.setter
    def _intentional_disconnect(self, value: bool) -> None:
        if value:
            self._conn_state = RadioConnectionState.DISCONNECTED
        elif self._conn_state == RadioConnectionState.DISCONNECTED:
            # Clearing intentional disconnect means reconnect is allowed.
            self._conn_state = RadioConnectionState.RECONNECTING

    @property
    def state_cache(self) -> StateCache:
        """Last-known radio state cache (frequency, mode, PTT, meters).

        Updated from both explicit GET responses and unsolicited CI-V frames
        (e.g. VFO knob turns).  Callers can read this directly for a
        non-blocking snapshot of recent state.
        """
        return self._state_cache

    @property
    def radio_state(self) -> RadioState:
        """Dual-receiver state snapshot (MAIN + SUB receivers, PTT, etc.).

        Populated by the CI-V RX stream.  May be replaced by
        :class:`~icom_lan.web.server.WebServer` with a shared instance.
        """
        return self._radio_state

    @property
    def audio_bus(self) -> Any:
        """Lazy-initialized AudioBus for pub/sub audio distribution."""
        if self._audio_bus is None:
            from .audio_bus import AudioBus
            self._audio_bus = AudioBus(self)
        return self._audio_bus

    @property
    def profile(self) -> RadioProfile:
        """Active runtime radio profile."""
        return self._profile

    @property
    def model(self) -> str:
        """Human-readable radio model name."""
        return self._profile.model

    @property
    def capabilities(self) -> set[str]:
        """Set of capability tags supported by this radio.

        Standard tags: ``audio``, ``scope``, ``dual_rx``, ``meters``,
        ``tx``, ``cw``.
        """
        return set(self._profile.capabilities)

    def _require_receiver(self, receiver: int, *, operation: str) -> None:
        """Validate receiver index against active profile."""
        if self._profile.supports_receiver(receiver):
            return
        raise CommandError(
            f"{operation} does not support receiver={receiver} for profile "
            f"{self._profile.model} (receivers={self._profile.receiver_count})"
        )

    def _require_capability(self, capability: str, *, operation: str) -> None:
        """Ensure a profile capability exists before executing operation."""
        if self._profile.supports_capability(capability):
            return
        raise CommandError(
            f"{operation} is not supported by profile {self._profile.model} "
            f"(missing capability: {capability})"
        )

    def _require_cmd29_route(
        self,
        command: int,
        sub: int | None,
        *,
        receiver: int,
        operation: str,
    ) -> None:
        """Require Command29 support for per-receiver command routing."""
        if receiver == RECEIVER_MAIN:
            return
        if self._profile.supports_cmd29(command, sub):
            return
        raise CommandError(
            f"{operation} receiver={receiver} is unsupported for profile "
            f"{self._profile.model}: command 0x{command:02X}"
            + (f"/0x{sub:02X}" if sub is not None else "")
            + " has no cmd29 route"
        )

    def _active_receiver_name(self) -> str:
        """Best-effort active receiver name for VFO-routing fallbacks."""
        active = getattr(self._radio_state, "active", None)
        if active in {"MAIN", "SUB"}:
            return active
        if self._last_vfo in {"SUB", "B"}:
            return "SUB"
        return "MAIN"

    async def _run_with_receiver_vfo_fallback(
        self,
        *,
        receiver: int,
        operation: str,
        action: "Callable[[], Awaitable[Any]]",
    ) -> Any:
        """Run an operation for a receiver using temporary MAIN/SUB VFO switching."""
        target = "MAIN" if receiver == RECEIVER_MAIN else "SUB"
        current = self._active_receiver_name()
        switched = False

        if current != target:
            if target == "SUB" and self._profile.vfo_sub_code is None:
                raise CommandError(
                    f"{operation} receiver={receiver} is unsupported for profile "
                    f"{self._profile.model}: no SUB VFO select code"
                )
            if target == "MAIN" and self._profile.vfo_main_code is None:
                raise CommandError(
                    f"{operation} receiver={receiver} is unsupported for profile "
                    f"{self._profile.model}: no MAIN VFO select code"
                )
            await self.select_vfo(target)
            self._radio_state.active = target
            switched = True

        try:
            return await action()
        finally:
            if switched:
                try:
                    await self.select_vfo(current)
                    self._radio_state.active = current
                except Exception:
                    logger.warning(
                        "%s: failed to restore VFO receiver to %s",
                        operation,
                        current,
                        exc_info=True,
                    )

    async def _get_frequency_main(
        self, *, bypass_cache: bool = False, update_cache: bool = True
    ) -> int:
        """Read MAIN receiver frequency with optional cache updates."""
        civ = get_frequency(to_addr=self._radio_addr)
        try:
            resp = await self._send_civ_raw(
                civ, key="get_frequency", dedupe=not bypass_cache,
            )
            freq = parse_frequency_response(resp)
            if update_cache:
                self._last_freq_hz = freq
                self._state_cache.update_freq(freq)
            return freq
        except TimeoutError:
            if update_cache and self._state_cache.is_fresh("freq", self._cache_ttl_freq):
                logger.debug(
                    "get_frequency: timeout, returning cached %d Hz",
                    self._state_cache.freq,
                )
                return self._state_cache.freq
            raise

    async def _set_frequency_main(self, freq_hz: int, *, update_cache: bool = True) -> None:
        """Set MAIN receiver frequency with optional cache updates."""
        civ = set_frequency(freq_hz, to_addr=self._radio_addr, receiver=RECEIVER_MAIN)
        await self._send_civ_raw(civ, wait_response=False)
        if update_cache:
            self._last_freq_hz = freq_hz
            self._state_cache.update_freq(freq_hz)

    async def _get_mode_info_main(
        self, *, update_cache: bool = True
    ) -> tuple[Mode, int | None]:
        """Read MAIN receiver mode/filter with optional cache updates."""
        civ = get_mode(to_addr=self._radio_addr)
        try:
            resp = await self._send_civ_raw(civ)
            mode, filt = parse_mode_response(resp)
            if update_cache:
                self._last_mode = mode
                if filt is not None:
                    self._filter_width = filt
                self._state_cache.update_mode(mode.name, filt)
            return mode, filt
        except TimeoutError:
            if update_cache and self._state_cache.is_fresh("mode", self._cache_ttl_mode):
                logger.debug(
                    "get_mode_info: timeout, returning cached %s",
                    self._state_cache.mode,
                )
                return Mode[self._state_cache.mode], self._state_cache.filter_width
            raise

    async def _set_mode_main(
        self,
        mode: Mode,
        *,
        filter_width: int | None = None,
        update_cache: bool = True,
    ) -> None:
        """Set MAIN receiver mode/filter with optional cache updates."""
        civ = set_mode(
            mode,
            filter_width=filter_width,
            to_addr=self._radio_addr,
            receiver=RECEIVER_MAIN,
        )
        await self._send_civ_raw(civ, wait_response=False)
        self._last_mode = mode
        if update_cache:
            if filter_width is not None:
                self._filter_width = filter_width
            cached_filter = (
                filter_width if filter_width is not None else self._filter_width
            )
            self._state_cache.update_mode(mode.name, cached_filter)

    @staticmethod
    def _coerce_mode(mode: Mode | str) -> Mode:
        """Normalize mode input and validate string names."""
        if isinstance(mode, Mode):
            return mode
        raw_mode = mode
        mode_key = mode.strip().upper()
        try:
            return Mode[mode_key]
        except KeyError as exc:
            supported = ", ".join(m.name for m in Mode)
            raise ValueError(
                f"Unknown mode: {raw_mode!r}. Supported modes: {supported}"
            ) from exc

    def set_state_change_callback(self, callback: Callable | None) -> None:
        """Register callback for CI-V state change notifications."""
        self._on_state_change = callback

    def set_reconnect_callback(self, callback: Callable | None) -> None:
        """Register callback invoked after successful soft reconnect."""
        self._on_reconnect = callback

    def civ_stats(self) -> dict[str, int]:
        """Return CI-V request tracker statistics for monitoring.

        Returns:
            Dict with keys ``active_waiters``, ``stale_cleaned``,
            ``timeouts``, ``generation``, ``ack_backlog_hits``,
            ``ack_backlog_drops``, and ``ack_orphans``.
        """
        return self._civ_request_tracker.snapshot_stats()

    async def __aenter__(self) -> "Icom7610CoreRadio":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:  # type: ignore[no-untyped-def]
        await self.disconnect()

    async def disconnect(self) -> None:
        """Cleanly disconnect from the radio."""
        if self._conn_state == RadioConnectionState.CONNECTED:
            self._conn_state = RadioConnectionState.DISCONNECTING
            self._advance_civ_generation("disconnect")
            self._stop_watchdog()
            self._stop_reconnect()
            self._stop_token_renewal()
            # Stop audio streams
            if self._audio_stream is not None:
                await self._audio_stream.stop_rx()
                await self._audio_stream.stop_tx()
                self._audio_stream = None
            self._pcm_tx_fmt = None
            self._pcm_rx_user_callback = None
            self._opus_rx_user_callback = None
            if self._audio_transport is not None:
                try:
                    await self._send_audio_open_close(open_stream=False)
                except Exception:
                    logger.debug("disconnect: audio open/close failed", exc_info=True)
                await self._audio_transport.disconnect()
                self._audio_transport = None
            if self._civ_transport:
                try:
                    await self._send_open_close(open_stream=False)
                except Exception:
                    logger.debug("disconnect: civ open/close failed", exc_info=True)
                await self._stop_civ_data_watchdog()
                await self._stop_civ_worker()
                await self._stop_civ_rx_pump()
                await self._civ_transport.disconnect()
                self._civ_transport = None
            try:
                await self._send_token(0x01)
            except Exception:
                logger.debug("disconnect: token remove failed", exc_info=True)
            await self._ctrl_transport.disconnect()
            self._conn_state = RadioConnectionState.DISCONNECTED
            self._civ_stream_ready = False
            self._civ_recovering = False
            logger.info("Disconnected from %s:%d", self._host, self._port)

    async def soft_disconnect(self) -> None:
        """Disconnect CI-V and audio but keep control transport alive.

        This allows fast reconnect without re-authentication — the radio
        keeps the session open on the control port.
        """
        if self._conn_state != RadioConnectionState.CONNECTED:
            return
        self._conn_state = RadioConnectionState.DISCONNECTING
        self._advance_civ_generation("soft_disconnect")

        # Stop audio
        if self._audio_stream is not None:
            await self._audio_stream.stop_rx()
            await self._audio_stream.stop_tx()
            self._audio_stream = None
        self._pcm_tx_fmt = None
        self._pcm_rx_user_callback = None
        self._opus_rx_user_callback = None
        if self._audio_transport is not None:
            try:
                await self._send_audio_open_close(open_stream=False)
            except Exception:
                logger.debug("soft_disconnect: audio open/close failed", exc_info=True)
            await self._audio_transport.disconnect()
            self._audio_transport = None

        # Stop CI-V
        if self._civ_transport:
            try:
                await self._send_open_close(open_stream=False)
            except Exception:
                logger.debug("soft_disconnect: civ open/close failed", exc_info=True)
            await self._stop_civ_data_watchdog()
            await self._stop_civ_worker()
            await self._stop_civ_rx_pump()
            await self._civ_transport.disconnect()
            self._civ_transport = None

        self._conn_state = RadioConnectionState.DISCONNECTED
        self._civ_stream_ready = False
        self._civ_recovering = False
        logger.info("Soft disconnect from %s:%d (control kept alive)", self._host, self._port)

    async def _force_cleanup_civ(self) -> None:
        """Unconditionally tear down CI-V transport regardless of state.

        Used as a last resort before reconnect when normal soft_disconnect
        fails or state is inconsistent (e.g. after struct overflow crash).
        """
        logger.info("force_cleanup_civ: tearing down CI-V unconditionally")
        await self._stop_civ_data_watchdog()
        await self._stop_civ_worker()
        await self._stop_civ_rx_pump()
        if self._civ_transport is not None:
            try:
                await self._civ_transport.disconnect()
            except Exception:
                logger.debug("force_cleanup_civ: transport disconnect failed", exc_info=True)
            self._civ_transport = None
        ctrl_alive = bool(
            self._ctrl_transport
            and getattr(self._ctrl_transport, "_udp_transport", None) is not None
        )
        self._conn_state = (
            RadioConnectionState.RECONNECTING
            if ctrl_alive
            else RadioConnectionState.DISCONNECTED
        )
        self._civ_stream_ready = False
        self._civ_recovering = ctrl_alive

    async def soft_reconnect(self) -> None:
        """Reconnect CI-V transport using existing control session.

        Skips discovery and authentication — reuses the existing control
        transport and token. Only re-opens the CI-V data stream.
        """
        if self._civ_transport is not None:
            logger.warning("soft_reconnect: CI-V transport already open")
            return
        if not self._ctrl_transport or not self._ctrl_transport._udp_transport:
            # Control transport dead — need full connect
            logger.info("soft_reconnect: control transport gone, doing full connect")
            await self.connect()
            return

        self._conn_state = RadioConnectionState.CONNECTING
        self._civ_stream_ready = False
        self._civ_recovering = True

        # Re-open CI-V transport (reuse known port)
        from .transport import IcomTransport
        self._civ_transport = IcomTransport()
        try:
            await self._civ_transport.connect(
                self._host, self._civ_port,
                local_port=getattr(self, "_civ_local_port", 0),
            )
        except OSError as exc:
            self._civ_transport = None
            self._conn_state = (
                RadioConnectionState.RECONNECTING
                if self.control_connected
                else RadioConnectionState.DISCONNECTED
            )
            self._civ_stream_ready = False
            self._civ_recovering = self.control_connected
            raise ConnectionError(f"Failed to reconnect CI-V: {exc}") from exc

        self._civ_transport.start_ping_loop()
        self._civ_transport.start_retransmit_loop()
        # ⚠️ DO NOT REMOVE — see _control_phase.py comment (2026-03-02)
        self._civ_transport.start_idle_loop()
        await self._send_open_close(open_stream=True)

        self._advance_civ_generation("soft_reconnect")
        self._civ_last_waiter_gc_monotonic = __import__("time").monotonic()
        # Force-restart rx pump (old task may be lingering)
        await self._stop_civ_rx_pump()
        self._start_civ_rx_pump()
        self._conn_state = RadioConnectionState.CONNECTED
        self._civ_transport._udp_error_count = 0  # reset error count after successful reconnect
        # Reset watchdog timestamp so it doesn't immediately trigger
        self._last_civ_data_received = __import__("time").monotonic()
        self._start_civ_worker()
        self._start_civ_data_watchdog()
        logger.info("Soft reconnect to %s (civ=%d)", self._host, self._civ_port)
        # Notify server to re-enable scope/audio after CI-V stream reset
        if self._on_reconnect is not None:
            try:
                self._on_reconnect()
            except Exception:
                logger.debug("soft_reconnect: _on_reconnect callback failed", exc_info=True)

    # ------------------------------------------------------------------
    # Watchdog & reconnect loops
    # ------------------------------------------------------------------

    async def _watchdog_loop(self) -> None:
        """Monitor connection health via transport packet queue activity.

        If no packets are received for ``watchdog_timeout`` seconds,
        triggers a reconnect attempt.

        Reference: wfview icomudpaudio.cpp watchdog() — 30s timeout.
        """
        last_activity = time.monotonic()
        last_health_log = time.monotonic()
        last_rx_count = self._ctrl_transport.rx_packet_count
        last_civ_count = (
            self._civ_transport.rx_packet_count if self._civ_transport else 0
        )
        try:
            while self._connected:
                await asyncio.sleep(self.WATCHDOG_CHECK_INTERVAL)
                if not self._connected:
                    break

                # Check if any transport has received new packets since last check
                ctrl_count = self._ctrl_transport.rx_packet_count
                civ_count = (
                    self._civ_transport.rx_packet_count
                    if self._civ_transport
                    else 0
                )
                if ctrl_count != last_rx_count or civ_count != last_civ_count:
                    last_activity = time.monotonic()
                    last_rx_count = ctrl_count
                    last_civ_count = civ_count

                now = time.monotonic()
                idle = now - last_activity

                # Periodic health status log
                if now - last_health_log >= self._WATCHDOG_HEALTH_LOG_INTERVAL:
                    logger.info(
                        "Transport health: ctrl_rx=%d civ_rx=%d idle=%.1fs",
                        ctrl_count,
                        civ_count,
                        idle,
                    )
                    last_health_log = now

                if idle > self._watchdog_timeout:
                    logger.warning(
                        "Watchdog: no activity for %.1fs, triggering reconnect",
                        idle,
                    )
                    self._conn_state = RadioConnectionState.RECONNECTING
                    self._advance_civ_generation("watchdog-timeout")
                    self._reconnect_task = asyncio.create_task(self._reconnect_loop())
                    return
        except asyncio.CancelledError:
            pass

    async def _reconnect_loop(self) -> None:
        """Attempt to reconnect with exponential backoff."""
        delay = self._reconnect_delay
        attempt = 0
        try:
            while self._conn_state != RadioConnectionState.DISCONNECTED:
                attempt += 1
                logger.info("Reconnect attempt %d (delay=%.1fs)", attempt, delay)
                try:
                    self._advance_civ_generation("reconnect-attempt")
                    # Capture audio state for auto-recovery.
                    audio_snapshot = self._capture_audio_snapshot()
                    # Clean up old transports
                    self._stop_token_renewal()
                    if self._audio_stream is not None:
                        try:
                            await self._audio_stream.stop_rx()
                            await self._audio_stream.stop_tx()
                        except Exception:
                            logger.debug("reconnect: audio_stream stop failed", exc_info=True)
                        self._audio_stream = None
                    if self._audio_transport is not None:
                        try:
                            await self._audio_transport.disconnect()
                        except Exception:
                            logger.debug("reconnect: audio_transport disconnect failed", exc_info=True)
                        self._audio_transport = None
                    if self._civ_transport is not None:
                        try:
                            await self._civ_transport.disconnect()
                        except Exception:
                            logger.debug("reconnect: civ_transport disconnect failed", exc_info=True)
                        self._civ_transport = None
                    try:
                        await self._send_token(0x01)
                    except Exception:
                        logger.debug("reconnect: token remove failed", exc_info=True)
                    try:
                        await self._ctrl_transport.disconnect()
                    except Exception:
                        logger.debug("reconnect: ctrl_transport disconnect failed", exc_info=True)

                    # Re-initialize transport
                    self._ctrl_transport = IcomTransport()
                    await self.connect()
                    logger.info(
                        "Reconnected successfully after %d attempts", attempt
                    )
                    if self._auto_recover_audio and audio_snapshot is not None:
                        await self._recover_audio(audio_snapshot)
                    return
                except Exception as exc:
                    self._conn_state = RadioConnectionState.RECONNECTING
                    logger.warning("Reconnect attempt %d failed: %s", attempt, exc)
                    await asyncio.sleep(delay)
                    delay = min(delay * 2, self._reconnect_max_delay)
        except asyncio.CancelledError:
            logger.info("Reconnect cancelled")

    # ------------------------------------------------------------------
    # Audio streaming
    # ------------------------------------------------------------------

    @staticmethod
    def _warn_audio_alias(old_name: str, replacement: str) -> None:
        warnings.warn(
            (
                f"IcomRadio.{old_name}() is deprecated and will be removed after two "
                f"minor releases; use IcomRadio.{replacement}() instead."
            ),
            DeprecationWarning,
            stacklevel=2,
        )

    async def start_audio_rx_opus(
        self,
        callback: "Callable[[AudioPacket | None], None]",
        *,
        jitter_depth: int = 5,
    ) -> None:
        """Start receiving Opus audio from the radio.

        Connects the audio transport if not already connected,
        then begins streaming RX audio to the callback.

        Args:
            callback: Called with each :class:`AudioPacket`.
            jitter_depth: Jitter buffer depth (0 to disable, default 5).

        Raises:
            ConnectionError: If not connected or audio port unavailable.
        """
        self._check_connected()
        await self._ensure_audio_transport()
        assert self._audio_stream is not None
        self._opus_rx_user_callback = callback
        self._opus_rx_jitter_depth = jitter_depth
        await self._audio_stream.start_rx(callback, jitter_depth=jitter_depth)

    async def start_audio_rx_pcm(
        self,
        callback: "Callable[[bytes | None], None]",
        *,
        sample_rate: int = 48000,
        channels: int = 1,
        frame_ms: int = 20,
        jitter_depth: int = 5,
    ) -> None:
        """Start receiving decoded PCM audio from the radio.

        This high-level API decodes incoming Opus RX frames to fixed-size
        PCM frames and delivers them to ``callback``. Gap placeholders are
        passed through as ``None`` when jitter buffering detects loss.

        Args:
            callback: Called with decoded PCM frame bytes, or ``None`` for gaps.
            sample_rate: PCM sample rate in Hz (Opus-supported values only).
            channels: PCM channels (1 or 2).
            frame_ms: Frame duration in ms (10/20/40/60).
            jitter_depth: Jitter buffer depth (0 to disable, default 5).

        Raises:
            ConnectionError: If not connected or audio port unavailable.
            TypeError: If callback is not callable or numeric args are not ints.
            ValueError: If ``jitter_depth`` is negative.
            AudioCodecBackendError: If Opus backend is unavailable.
            AudioFormatError: If PCM format is unsupported.
        """
        if not callable(callback):
            raise TypeError("callback must be callable and accept bytes | None.")

        for name, value in (
            ("sample_rate", sample_rate),
            ("channels", channels),
            ("frame_ms", frame_ms),
            ("jitter_depth", jitter_depth),
        ):
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name} must be an int, got {type(value).__name__}.")
        if jitter_depth < 0:
            raise ValueError(f"jitter_depth must be >= 0, got {jitter_depth}.")

        self._check_connected()

        # Validate codec/backend and PCM format before stream startup.
        self._get_pcm_transcoder(
            sample_rate=sample_rate,
            channels=channels,
            frame_ms=frame_ms,
        )
        self._pcm_rx_user_callback = callback
        self._pcm_rx_jitter_depth = jitter_depth
        await self.start_audio_rx_opus(
            self._build_pcm_rx_callback(
                callback,
                sample_rate=sample_rate,
                channels=channels,
                frame_ms=frame_ms,
            ),
            jitter_depth=jitter_depth,
        )

    async def stop_audio_rx_pcm(self) -> None:
        """Stop receiving decoded PCM audio from the radio."""
        self._pcm_rx_user_callback = None
        await self.stop_audio_rx_opus()

    async def stop_audio_rx_opus(self) -> None:
        """Stop receiving Opus audio from the radio."""
        self._opus_rx_user_callback = None
        if self._audio_stream is not None:
            await self._audio_stream.stop_rx()

    def _add_opus_rx_tap(
        self, callback: "Callable[[AudioPacket | None], None]",
    ) -> None:
        """Add an additional opus RX listener (non-exclusive, parallel to main callback)."""
        if self._audio_stream is not None:
            self._audio_stream.add_rx_tap(callback)

    def _remove_opus_rx_tap(
        self, callback: "Callable[[AudioPacket | None], None]",
    ) -> None:
        """Remove an opus RX tap."""
        if self._audio_stream is not None:
            self._audio_stream.remove_rx_tap(callback)

    async def start_audio_tx_opus(self) -> None:
        """Start transmitting Opus audio to the radio.

        Connects the audio transport if not already connected.

        Raises:
            ConnectionError: If not connected or audio port unavailable.
        """
        self._check_connected()
        await self._ensure_audio_transport()
        assert self._audio_stream is not None
        await self._audio_stream.start_tx()

    async def start_audio_tx_pcm(
        self,
        *,
        sample_rate: int = 48000,
        channels: int = 1,
        frame_ms: int = 20,
    ) -> None:
        """Start transmitting PCM audio to the radio.

        This high-level API validates PCM format settings, initializes
        the Opus transcoder backend, and starts the underlying Opus TX stream.

        Args:
            sample_rate: PCM sample rate in Hz (Opus-supported values only).
            channels: PCM channels (1 or 2).
            frame_ms: Frame duration in ms (10/20/40/60).

        Raises:
            ConnectionError: If not connected or audio port unavailable.
            TypeError: If numeric args are not ints.
            AudioCodecBackendError: If Opus backend is unavailable.
            AudioFormatError: If PCM format is unsupported.
        """
        for name, value in (
            ("sample_rate", sample_rate),
            ("channels", channels),
            ("frame_ms", frame_ms),
        ):
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name} must be an int, got {type(value).__name__}.")

        self._check_connected()

        # Validate codec/backend and PCM format before stream startup.
        self._get_pcm_transcoder(
            sample_rate=sample_rate,
            channels=channels,
            frame_ms=frame_ms,
        )
        await self.start_audio_tx_opus()
        self._pcm_tx_fmt = (sample_rate, channels, frame_ms)

    async def push_audio_tx_opus(self, opus_data: bytes) -> None:
        """Send an Opus-encoded audio frame to the radio.

        Args:
            opus_data: Opus-encoded audio data.

        Raises:
            ConnectionError: If not connected.
            RuntimeError: If audio TX not started.
        """
        self._check_connected()
        if self._audio_stream is None:
            raise RuntimeError("Audio TX not started")
        await self._audio_stream.push_tx(opus_data)

    async def push_audio_tx_pcm(
        self,
        pcm_bytes: bytes | bytearray | memoryview,
    ) -> None:
        """Encode and send one PCM audio frame to the radio.

        Args:
            pcm_bytes: One fixed-size PCM frame (s16le, interleaved).

        Raises:
            ConnectionError: If not connected.
            RuntimeError: If PCM TX not started with :meth:`start_audio_tx_pcm`.
            AudioFormatError: If frame type/size is invalid.
            AudioTranscodeError: If encode operation fails.
        """
        self._check_connected()
        if self._pcm_tx_fmt is None:
            raise RuntimeError(
                "PCM TX not started; call start_audio_tx_pcm() before push_audio_tx_pcm()."
            )
        sample_rate, channels, frame_ms = self._pcm_tx_fmt
        await self._push_audio_tx_pcm_internal(
            pcm_bytes,
            sample_rate=sample_rate,
            channels=channels,
            frame_ms=frame_ms,
        )

    async def stop_audio_tx_pcm(self) -> None:
        """Stop transmitting PCM audio to the radio."""
        await self.stop_audio_tx_opus()

    async def stop_audio_tx_opus(self) -> None:
        """Stop transmitting Opus audio to the radio."""
        if self._audio_stream is not None:
            await self._audio_stream.stop_tx()
        self._pcm_tx_fmt = None

    async def start_audio_opus(
        self,
        rx_callback: "Callable[[AudioPacket | None], None]",
        *,
        tx_enabled: bool = True,
        jitter_depth: int = 5,
    ) -> None:
        """Start full-duplex Opus audio (RX + optional TX).

        Convenience method that starts both RX and TX audio streams
        on the same transport.

        Args:
            rx_callback: Called with each :class:`AudioPacket` (or None for gaps).
            tx_enabled: Whether to also enable TX (default True).
            jitter_depth: Jitter buffer depth (0 to disable, default 5).

        Raises:
            ConnectionError: If not connected or audio port unavailable.
        """
        await self.start_audio_rx_opus(rx_callback, jitter_depth=jitter_depth)
        if tx_enabled:
            assert self._audio_stream is not None
            await self._audio_stream.start_tx()

    async def stop_audio_opus(self) -> None:
        """Stop all Opus audio streams (RX and TX)."""
        await self.stop_audio_tx_opus()
        await self.stop_audio_rx_opus()

    async def start_audio_rx(
        self, callback: "Callable[[AudioPacket | None], None]"
    ) -> None:
        """Deprecated alias for :meth:`start_audio_rx_opus`."""
        self._warn_audio_alias("start_audio_rx", "start_audio_rx_opus")
        await self.start_audio_rx_opus(callback)

    async def stop_audio_rx(self) -> None:
        """Deprecated alias for :meth:`stop_audio_rx_opus`."""
        self._warn_audio_alias("stop_audio_rx", "stop_audio_rx_opus")
        await self.stop_audio_rx_opus()

    async def start_audio_tx(self) -> None:
        """Deprecated alias for :meth:`start_audio_tx_opus`."""
        self._warn_audio_alias("start_audio_tx", "start_audio_tx_opus")
        await self.start_audio_tx_opus()

    async def push_audio_tx(self, opus_data: bytes) -> None:
        """Deprecated alias for :meth:`push_audio_tx_opus`."""
        self._warn_audio_alias("push_audio_tx", "push_audio_tx_opus")
        await self.push_audio_tx_opus(opus_data)

    async def stop_audio_tx(self) -> None:
        """Deprecated alias for :meth:`stop_audio_tx_opus`."""
        self._warn_audio_alias("stop_audio_tx", "stop_audio_tx_opus")
        await self.stop_audio_tx_opus()

    async def start_audio(
        self,
        rx_callback: "Callable[[AudioPacket | None], None]",
        *,
        tx_enabled: bool = True,
    ) -> None:
        """Deprecated alias for :meth:`start_audio_opus`."""
        self._warn_audio_alias("start_audio", "start_audio_opus")
        await self.start_audio_opus(rx_callback, tx_enabled=tx_enabled)

    def get_audio_stats(self) -> dict[str, bool | int | float | str]:
        """Return runtime audio stats for the active stream.

        Returns a JSON-friendly dictionary with packet/loss/jitter/buffer/latency
        metrics. If no audio stream is active, returns a zeroed idle snapshot.
        """
        if self._audio_stream is None:
            return AudioStats.inactive().to_dict()
        return self._audio_stream.get_audio_stats()

    async def stop_audio(self) -> None:
        """Deprecated alias for :meth:`stop_audio_opus`."""
        self._warn_audio_alias("stop_audio", "stop_audio_opus")
        await self.stop_audio_opus()

    def _get_pcm_transcoder(
        self,
        *,
        sample_rate: int = 48000,
        channels: int = 1,
        frame_ms: int = 20,
    ) -> PcmOpusTranscoder:
        """Get/create cached PCM<->Opus transcoder for internal PCM hooks."""
        key = (sample_rate, channels, frame_ms)
        if self._pcm_transcoder is not None and self._pcm_transcoder_fmt == key:
            return self._pcm_transcoder
        self._pcm_transcoder = create_pcm_opus_transcoder(
            sample_rate=sample_rate,
            channels=channels,
            frame_ms=frame_ms,
        )
        self._pcm_transcoder_fmt = key
        return self._pcm_transcoder

    def _build_pcm_rx_callback(
        self,
        callback: "Callable[[bytes | None], None]",
        *,
        sample_rate: int = 48000,
        channels: int = 1,
        frame_ms: int = 20,
    ) -> "Callable[[AudioPacket | None], None]":
        """Internal adapter: AudioPacket callback -> PCM callback."""

        def _on_audio_packet(packet: AudioPacket | None) -> None:
            if packet is None:
                callback(None)
                return
            pcm_frame = self._decode_audio_packet_to_pcm(
                packet,
                sample_rate=sample_rate,
                channels=channels,
                frame_ms=frame_ms,
            )
            callback(pcm_frame)

        return _on_audio_packet

    def _decode_audio_packet_to_pcm(
        self,
        packet: AudioPacket,
        *,
        sample_rate: int = 48000,
        channels: int = 1,
        frame_ms: int = 20,
    ) -> bytes:
        """Internal helper for future high-level RX PCM APIs."""
        transcoder = self._get_pcm_transcoder(
            sample_rate=sample_rate,
            channels=channels,
            frame_ms=frame_ms,
        )
        return transcoder.opus_to_pcm(packet.data)

    async def _push_audio_tx_pcm_internal(
        self,
        pcm_data: bytes | bytearray | memoryview,
        *,
        sample_rate: int = 48000,
        channels: int = 1,
        frame_ms: int = 20,
    ) -> None:
        """Internal helper for future high-level TX PCM APIs."""
        transcoder = self._get_pcm_transcoder(
            sample_rate=sample_rate,
            channels=channels,
            frame_ms=frame_ms,
        )
        opus_data = transcoder.pcm_to_opus(pcm_data)
        await self.push_audio_tx_opus(opus_data)

    @property
    def audio_codec(self) -> "AudioCodec":
        """Configured audio codec."""
        return self._audio_codec

    @property
    def audio_sample_rate(self) -> int:
        """Configured audio sample rate in Hz."""
        return self._audio_sample_rate

    @staticmethod
    def audio_capabilities() -> AudioCapabilities:
        """Return icom-lan audio capabilities and deterministic defaults."""
        return get_audio_capabilities()

    async def _ensure_audio_transport(self) -> None:
        """Connect the audio transport if not already connected."""
        if self._audio_stream is not None:
            return

        if self._audio_port == 0:
            raise ConnectionError("Audio port not available")

        self._audio_transport = IcomTransport()
        try:
            await self._audio_transport.connect(
                self._host, self._audio_port,
                local_port=getattr(self, "_audio_local_port", 0),
            )
        except OSError as exc:
            self._audio_transport = None
            raise ConnectionError(
                f"Failed to connect audio port {self._audio_port}: {exc}"
            ) from exc

        self._audio_transport.start_ping_loop()
        self._audio_transport.start_retransmit_loop()
        self._audio_transport.start_idle_loop()

        # Per wfview, audio stream also uses OpenClose on its own UDP channel.
        await self._send_audio_open_close(open_stream=True)

        self._audio_stream = AudioStream(self._audio_transport)
        logger.info("Audio transport connected on port %d", self._audio_port)

    # ------------------------------------------------------------------
    # Public CI-V API
    # ------------------------------------------------------------------

    async def send_civ(
        self,
        command: int,
        sub: int | None = None,
        data: bytes | None = None,
        *,
        wait_response: bool = True,
    ) -> CivFrame | None:
        """Send a CI-V command.

        Args:
            command: CI-V command byte.
            sub: Optional sub-command byte.
            data: Optional payload data.
            wait_response: If False, fire-and-forget (no response wait).

        Returns:
            Parsed response CivFrame, or None if wait_response=False.
        """
        self._check_connected()
        frame = build_civ_frame(
            self._radio_addr, CONTROLLER_ADDR, command, sub=sub, data=data
        )
        return await self._send_civ_raw(frame, wait_response=wait_response)

    async def get_frequency(
        self, receiver: int = RECEIVER_MAIN, *, bypass_cache: bool = False
    ) -> int:
        """Get the current operating frequency in Hz.

        Args:
            receiver: 0=MAIN, 1=SUB.
            bypass_cache: Skip dedupe and cache fallback (used by RadioPoller).

        On timeout falls back to the state cache (if populated) rather than
        raising immediately, allowing callers to remain responsive while the
        radio is busy streaming scope data.
        """
        self._check_connected()
        self._require_receiver(receiver, operation="get_frequency")
        if receiver == RECEIVER_MAIN:
            return await self._get_frequency_main(bypass_cache=bypass_cache)

        return await self._run_with_receiver_vfo_fallback(
            receiver=receiver,
            operation="get_frequency",
            action=lambda: self._get_frequency_main(
                bypass_cache=bypass_cache, update_cache=False
            ),
        )

    async def set_frequency(self, freq_hz: int, receiver: int = 0) -> None:
        """Set the operating frequency.

        Args:
            freq_hz: Frequency in Hz.
            receiver: 0=MAIN, 1=SUB.
        """
        self._check_connected()
        self._require_receiver(receiver, operation="set_frequency")
        if receiver == RECEIVER_MAIN:
            await self._set_frequency_main(freq_hz)
            return

        if self._profile.supports_cmd29(0x05):
            civ = set_frequency(freq_hz, to_addr=self._radio_addr, receiver=receiver)
            await self._send_civ_raw(civ, wait_response=False)
        else:
            await self._run_with_receiver_vfo_fallback(
                receiver=receiver,
                operation="set_frequency",
                action=lambda: self._set_frequency_main(freq_hz, update_cache=False),
            )

        self._radio_state.receiver("SUB").freq = freq_hz

    async def get_mode(self, receiver: int = 0) -> tuple[str, int | None]:  # type: ignore[override]
        """Get current mode as (name, filter) — Protocol-compatible.

        Returns a ``(mode_name, filter_number)`` tuple. For the Icom-specific
        :class:`Mode` enum, use :meth:`get_mode_info` instead.

        .. note:: The returned mode name is the Mode enum ``.name`` attribute
           (e.g. ``"USB"``, ``"CW"``), which matches hamlib mode strings.
        """
        mode, filt = await self.get_mode_info(receiver=receiver)
        return mode.name, filt

    async def get_mode_enum(self) -> "Mode":
        """Get the current operating mode as a :class:`Mode` enum (legacy).

        .. deprecated:: 0.12
           Use :meth:`get_mode` (returns ``tuple[str, int | None]``) or
           :meth:`get_mode_info` (returns ``tuple[Mode, int | None]``).
        """
        mode, _ = await self.get_mode_info()
        return mode

    async def get_mode_info(
        self, receiver: int = RECEIVER_MAIN
    ) -> tuple[Mode, int | None]:
        """Get current mode and filter number (if reported by radio).

        On timeout falls back to the state cache when populated.
        """
        self._check_connected()
        self._require_receiver(receiver, operation="get_mode_info")
        if receiver == RECEIVER_MAIN:
            return await self._get_mode_info_main(update_cache=True)

        return await self._run_with_receiver_vfo_fallback(
            receiver=receiver,
            operation="get_mode_info",
            action=lambda: self._get_mode_info_main(update_cache=False),
        )

    async def get_filter(self) -> int | None:
        """Get current mode filter number (1-3) when available."""
        _, filt = await self.get_mode_info()
        return filt if filt is not None else self._filter_width

    async def set_filter(self, filter_width: int, receiver: int = 0) -> None:
        """Set filter number (1-3) while keeping current mode unchanged."""
        mode_name, _ = await self.get_mode(receiver=receiver)
        await self.set_mode(mode_name, filter_width=filter_width, receiver=receiver)

    async def set_mode(self, mode: Mode | str, filter_width: int | None = None, receiver: int = 0) -> None:
        """Set the operating mode.

        Args:
            mode: Mode enum or string name (e.g. "USB", "LSB").
            filter_width: Optional filter number (1-3).
            receiver: 0=MAIN, 1=SUB.
        """
        self._check_connected()
        self._require_receiver(receiver, operation="set_mode")
        parsed_mode = self._coerce_mode(mode)

        if receiver == RECEIVER_MAIN:
            await self._set_mode_main(parsed_mode, filter_width=filter_width)
            return

        if self._profile.supports_cmd29(0x06):
            civ = set_mode(
                parsed_mode,
                filter_width=filter_width,
                to_addr=self._radio_addr,
                receiver=receiver,
            )
            await self._send_civ_raw(civ, wait_response=False)
        else:
            await self._run_with_receiver_vfo_fallback(
                receiver=receiver,
                operation="set_mode",
                action=lambda: self._set_mode_main(
                    parsed_mode, filter_width=filter_width, update_cache=False
                ),
            )

        sub = self._radio_state.receiver("SUB")
        sub.mode = parsed_mode.name
        if filter_width is not None:
            sub.filter = filter_width

    async def get_data_mode(self) -> bool:
        """Get the IC-7610 DATA mode state (command 0x1A 0x06).

        Returns:
            True if DATA mode is active (DATA1/2/3), False if off.
        """
        self._check_connected()
        civ = get_data_mode_cmd(to_addr=self._radio_addr)
        resp = await self._send_civ_raw(civ)
        return parse_data_mode_response(resp)

    async def set_data_mode(self, on: bool) -> None:
        """Set the IC-7610 DATA mode (command 0x1A 0x06).

        Args:
            on: True to enable DATA1 mode, False to disable.
        """
        self._check_connected()
        civ = set_data_mode_cmd(on, to_addr=self._radio_addr)
        resp = await self._send_civ_raw(civ)
        ack = parse_ack_nak(resp)
        if ack is False:
            raise CommandError(f"Radio rejected set_data_mode({on})")

    def _parse_level(self, resp: "CivFrame") -> int:
        """Parse a level BCD response into an integer 0-255."""
        return _level_bcd_decode(resp.data)

    async def _get_bcd_level(
        self,
        civ: bytes,
        *,
        key: str,
        command: int,
        sub: int,
        prefix: bytes = b"",
        bcd_bytes: int = 2,
    ) -> int:
        """Send a GET command and parse a BCD-encoded integer response."""
        self._check_connected()
        resp = await self._send_civ_raw(civ, key=key, dedupe=True)
        return parse_level_response(
            resp,
            command=command,
            sub=sub,
            prefix=prefix,
            bcd_bytes=bcd_bytes,
        )

    async def _get_bool_value(
        self,
        civ: bytes,
        *,
        key: str,
        command: int,
        sub: int,
        prefix: bytes = b"",
    ) -> bool:
        """Send a GET command and parse a boolean response."""
        self._check_connected()
        resp = await self._send_civ_raw(civ, key=key, dedupe=True)
        return parse_bool_response(resp, command=command, sub=sub, prefix=prefix)

    async def _send_fire_and_forget(self, civ: bytes) -> None:
        """Send a fire-and-forget CI-V command after connection checks."""
        self._check_connected()
        await self._send_civ_raw(civ, wait_response=False)

    async def get_power(self) -> int:
        """Get the RF power level (0-255).

        On timeout falls back to the state cache if populated.
        """
        self._check_connected()
        civ = get_power(to_addr=self._radio_addr)
        try:
            resp = await self._send_civ_raw(civ, key="get_power", dedupe=True)
            level = _level_bcd_decode(resp.data)
            self._last_power = level
            self._state_cache.update_rf_power(level / 255.0)
            return level
        except TimeoutError:
            if (
                self._state_cache.is_fresh("rf_power", self._cache_ttl_rf_power)
                and self._state_cache.rf_power is not None
            ):
                cached_level = round(self._state_cache.rf_power * 255)
                logger.debug(
                    "get_power: timeout, returning cached %d", cached_level
                )
                return cached_level
            raise

    async def set_power(self, level: int) -> None:
        """Set the RF power level (0-255).

        Args:
            level: Power level 0-255.
        """
        self._check_connected()
        civ = set_power(level, to_addr=self._radio_addr)
        await self._send_civ_raw(civ, wait_response=False)
        self._last_power = level

    async def get_rf_gain(self) -> int:
        """Read the current RF gain level (0-255)."""
        self._check_connected()
        civ = get_rf_gain(to_addr=self._radio_addr)
        try:
            resp = await self._send_civ_raw(civ, key="get_rf_gain", dedupe=True)
            return self._parse_level(resp)
        except TimeoutError:
            raise

    async def set_rf_gain(self, level: int, receiver: int = 0) -> None:
        """Set RF gain level (0-255)."""
        if not 0 <= level <= 255:
            raise ValueError(f"RF gain must be 0-255, got {level}")
        self._check_connected()
        self._require_capability("rf_gain", operation="set_rf_gain")
        self._require_receiver(receiver, operation="set_rf_gain")
        self._require_cmd29_route(
            0x14,
            0x02,
            receiver=receiver,
            operation="set_rf_gain",
        )
        civ = set_rf_gain(level, to_addr=self._radio_addr, receiver=receiver)
        await self._send_civ_raw(civ, wait_response=False)

    async def get_af_level(self) -> int:
        """Read the current AF output level (0-255)."""
        self._check_connected()
        civ = get_af_level(to_addr=self._radio_addr)
        try:
            resp = await self._send_civ_raw(civ, key="get_af_level", dedupe=True)
            return self._parse_level(resp)
        except TimeoutError:
            raise

    async def set_af_level(self, level: int, receiver: int = 0) -> None:
        """Set AF output level (0-255)."""
        if not 0 <= level <= 255:
            raise ValueError(f"AF level must be 0-255, got {level}")
        self._check_connected()
        self._require_capability("af_level", operation="set_af_level")
        self._require_receiver(receiver, operation="set_af_level")
        self._require_cmd29_route(
            0x14,
            0x01,
            receiver=receiver,
            operation="set_af_level",
        )
        civ = set_af_level(level, to_addr=self._radio_addr, receiver=receiver)
        await self._send_civ_raw(civ, wait_response=False)

    async def set_squelch(self, level: int, receiver: int = 0) -> None:
        """Set squelch level (0-255, 0=open)."""
        if not 0 <= level <= 255:
            raise ValueError(f"Squelch level must be 0-255, got {level}")
        self._check_connected()
        self._require_capability("squelch", operation="set_squelch")
        self._require_receiver(receiver, operation="set_squelch")
        self._require_cmd29_route(
            0x14,
            0x03,
            receiver=receiver,
            operation="set_squelch",
        )
        from .commands import set_squelch as _set_squelch
        civ = _set_squelch(level, to_addr=self._radio_addr, receiver=receiver)
        await self._send_civ_raw(civ, wait_response=False)

    async def get_apf_type_level(self, receiver: int = RECEIVER_MAIN) -> int:
        """Read APF Type Level (0-255)."""
        self._require_receiver(receiver, operation="get_apf_type_level")
        self._require_cmd29_route(
            0x14, 0x05, receiver=receiver, operation="get_apf_type_level"
        )
        civ = get_apf_type_level(to_addr=self._radio_addr, receiver=receiver)
        return await self._get_bcd_level(
            civ,
            key=f"get_apf_type_level:{receiver}",
            command=0x14,
            sub=0x05,
        )

    async def set_apf_type_level(
        self, level: int, receiver: int = RECEIVER_MAIN
    ) -> None:
        """Set APF Type Level (0-255)."""
        self._require_receiver(receiver, operation="set_apf_type_level")
        self._require_cmd29_route(
            0x14, 0x05, receiver=receiver, operation="set_apf_type_level"
        )
        await self._send_fire_and_forget(
            set_apf_type_level(level, to_addr=self._radio_addr, receiver=receiver)
        )

    async def get_nr_level(self, receiver: int = RECEIVER_MAIN) -> int:
        """Read NR Level (0-255)."""
        self._require_receiver(receiver, operation="get_nr_level")
        self._require_cmd29_route(
            0x14, 0x06, receiver=receiver, operation="get_nr_level"
        )
        civ = get_nr_level(to_addr=self._radio_addr, receiver=receiver)
        return await self._get_bcd_level(
            civ, key=f"get_nr_level:{receiver}", command=0x14, sub=0x06
        )

    async def set_nr_level(self, level: int, receiver: int = RECEIVER_MAIN) -> None:
        """Set NR Level (0-255)."""
        self._require_receiver(receiver, operation="set_nr_level")
        self._require_cmd29_route(
            0x14, 0x06, receiver=receiver, operation="set_nr_level"
        )
        await self._send_fire_and_forget(
            set_nr_level(level, to_addr=self._radio_addr, receiver=receiver)
        )

    async def get_pbt_inner(self, receiver: int = RECEIVER_MAIN) -> int:
        """Read PBT Inner level (0-255)."""
        self._require_receiver(receiver, operation="get_pbt_inner")
        self._require_cmd29_route(
            0x14, 0x07, receiver=receiver, operation="get_pbt_inner"
        )
        civ = get_pbt_inner(to_addr=self._radio_addr, receiver=receiver)
        return await self._get_bcd_level(
            civ, key=f"get_pbt_inner:{receiver}", command=0x14, sub=0x07
        )

    async def set_pbt_inner(self, level: int, receiver: int = RECEIVER_MAIN) -> None:
        """Set PBT Inner level (0-255)."""
        self._require_receiver(receiver, operation="set_pbt_inner")
        self._require_cmd29_route(
            0x14, 0x07, receiver=receiver, operation="set_pbt_inner"
        )
        await self._send_fire_and_forget(
            set_pbt_inner(level, to_addr=self._radio_addr, receiver=receiver)
        )

    async def get_pbt_outer(self, receiver: int = RECEIVER_MAIN) -> int:
        """Read PBT Outer level (0-255)."""
        self._require_receiver(receiver, operation="get_pbt_outer")
        self._require_cmd29_route(
            0x14, 0x08, receiver=receiver, operation="get_pbt_outer"
        )
        civ = get_pbt_outer(to_addr=self._radio_addr, receiver=receiver)
        return await self._get_bcd_level(
            civ, key=f"get_pbt_outer:{receiver}", command=0x14, sub=0x08
        )

    async def set_pbt_outer(self, level: int, receiver: int = RECEIVER_MAIN) -> None:
        """Set PBT Outer level (0-255)."""
        self._require_receiver(receiver, operation="set_pbt_outer")
        self._require_cmd29_route(
            0x14, 0x08, receiver=receiver, operation="set_pbt_outer"
        )
        await self._send_fire_and_forget(
            set_pbt_outer(level, to_addr=self._radio_addr, receiver=receiver)
        )

    async def get_cw_pitch(self) -> int:
        """Read CW pitch in Hz."""
        level = await self._get_bcd_level(
            get_cw_pitch(to_addr=self._radio_addr),
            key="get_cw_pitch",
            command=0x14,
            sub=0x09,
        )
        return round((((600.0 / 255.0) * level) + 300) / 5.0) * 5

    async def set_cw_pitch(self, pitch_hz: int) -> None:
        """Set CW pitch in Hz."""
        await self._send_fire_and_forget(
            set_cw_pitch(pitch_hz, to_addr=self._radio_addr)
        )

    async def get_mic_gain(self) -> int:
        """Read Mic Gain (0-255)."""
        return await self._get_bcd_level(
            get_mic_gain(to_addr=self._radio_addr),
            key="get_mic_gain",
            command=0x14,
            sub=0x0B,
        )

    async def set_mic_gain(self, level: int) -> None:
        """Set Mic Gain (0-255)."""
        await self._send_fire_and_forget(set_mic_gain(level, to_addr=self._radio_addr))

    async def get_key_speed(self) -> int:
        """Read key speed in WPM."""
        level = await self._get_bcd_level(
            get_key_speed(to_addr=self._radio_addr),
            key="get_key_speed",
            command=0x14,
            sub=0x0C,
        )
        return round((level / 6.071) + 6)

    async def set_key_speed(self, wpm: int) -> None:
        """Set key speed in WPM."""
        await self._send_fire_and_forget(
            set_key_speed(wpm, to_addr=self._radio_addr)
        )

    async def get_notch_filter(self) -> int:
        """Read notch filter level (0-255)."""
        return await self._get_bcd_level(
            get_notch_filter(to_addr=self._radio_addr),
            key="get_notch_filter",
            command=0x14,
            sub=0x0D,
        )

    async def set_notch_filter(self, level: int) -> None:
        """Set notch filter level (0-255)."""
        await self._send_fire_and_forget(
            set_notch_filter(level, to_addr=self._radio_addr)
        )

    async def get_compressor_level(self) -> int:
        """Read compressor level (0-255)."""
        return await self._get_bcd_level(
            get_compressor_level(to_addr=self._radio_addr),
            key="get_compressor_level",
            command=0x14,
            sub=0x0E,
        )

    async def set_compressor_level(self, level: int) -> None:
        """Set compressor level (0-255)."""
        await self._send_fire_and_forget(
            set_compressor_level(level, to_addr=self._radio_addr)
        )

    async def get_break_in_delay(self) -> int:
        """Read break-in delay level (0-255)."""
        return await self._get_bcd_level(
            get_break_in_delay(to_addr=self._radio_addr),
            key="get_break_in_delay",
            command=0x14,
            sub=0x0F,
        )

    async def set_break_in_delay(self, level: int) -> None:
        """Set break-in delay level (0-255)."""
        await self._send_fire_and_forget(
            set_break_in_delay(level, to_addr=self._radio_addr)
        )

    async def get_nb_level(self, receiver: int = RECEIVER_MAIN) -> int:
        """Read NB level (0-255)."""
        self._require_receiver(receiver, operation="get_nb_level")
        self._require_cmd29_route(
            0x14, 0x12, receiver=receiver, operation="get_nb_level"
        )
        civ = get_nb_level(to_addr=self._radio_addr, receiver=receiver)
        return await self._get_bcd_level(
            civ, key=f"get_nb_level:{receiver}", command=0x14, sub=0x12
        )

    async def set_nb_level(self, level: int, receiver: int = RECEIVER_MAIN) -> None:
        """Set NB level (0-255)."""
        self._require_receiver(receiver, operation="set_nb_level")
        self._require_cmd29_route(
            0x14, 0x12, receiver=receiver, operation="set_nb_level"
        )
        await self._send_fire_and_forget(
            set_nb_level(level, to_addr=self._radio_addr, receiver=receiver)
        )

    async def get_digisel_shift(self, receiver: int = RECEIVER_MAIN) -> int:
        """Read DIGI-SEL Shift (0-255)."""
        self._require_receiver(receiver, operation="get_digisel_shift")
        self._require_cmd29_route(
            0x14, 0x13, receiver=receiver, operation="get_digisel_shift"
        )
        civ = get_digisel_shift(to_addr=self._radio_addr, receiver=receiver)
        return await self._get_bcd_level(
            civ, key=f"get_digisel_shift:{receiver}", command=0x14, sub=0x13
        )

    async def set_digisel_shift(
        self, level: int, receiver: int = RECEIVER_MAIN
    ) -> None:
        """Set DIGI-SEL Shift (0-255)."""
        self._require_receiver(receiver, operation="set_digisel_shift")
        self._require_cmd29_route(
            0x14, 0x13, receiver=receiver, operation="set_digisel_shift"
        )
        await self._send_fire_and_forget(
            set_digisel_shift(level, to_addr=self._radio_addr, receiver=receiver)
        )

    async def get_drive_gain(self) -> int:
        """Read drive gain (0-255)."""
        return await self._get_bcd_level(
            get_drive_gain(to_addr=self._radio_addr),
            key="get_drive_gain",
            command=0x14,
            sub=0x14,
        )

    async def set_drive_gain(self, level: int) -> None:
        """Set drive gain (0-255)."""
        await self._send_fire_and_forget(
            set_drive_gain(level, to_addr=self._radio_addr)
        )

    async def get_monitor_gain(self) -> int:
        """Read monitor gain (0-255)."""
        return await self._get_bcd_level(
            get_monitor_gain(to_addr=self._radio_addr),
            key="get_monitor_gain",
            command=0x14,
            sub=0x15,
        )

    async def set_monitor_gain(self, level: int) -> None:
        """Set monitor gain (0-255)."""
        await self._send_fire_and_forget(
            set_monitor_gain(level, to_addr=self._radio_addr)
        )

    async def get_vox_gain(self) -> int:
        """Read VOX gain (0-255)."""
        return await self._get_bcd_level(
            get_vox_gain(to_addr=self._radio_addr),
            key="get_vox_gain",
            command=0x14,
            sub=0x16,
        )

    async def set_vox_gain(self, level: int) -> None:
        """Set VOX gain (0-255)."""
        await self._send_fire_and_forget(
            set_vox_gain(level, to_addr=self._radio_addr)
        )

    async def get_anti_vox_gain(self) -> int:
        """Read anti-VOX gain (0-255)."""
        return await self._get_bcd_level(
            get_anti_vox_gain(to_addr=self._radio_addr),
            key="get_anti_vox_gain",
            command=0x14,
            sub=0x17,
        )

    async def set_anti_vox_gain(self, level: int) -> None:
        """Set anti-VOX gain (0-255)."""
        await self._send_fire_and_forget(
            set_anti_vox_gain(level, to_addr=self._radio_addr)
        )

    async def get_ref_adjust(self) -> int:
        """Read REF Adjust (0-511)."""
        return await self._get_bcd_level(
            get_ref_adjust(to_addr=self._radio_addr),
            key="get_ref_adjust",
            command=0x1A,
            sub=0x05,
            prefix=b"\x00\x70",
        )

    async def set_ref_adjust(self, value: int) -> None:
        """Set REF Adjust (0-511)."""
        await self._send_fire_and_forget(
            set_ref_adjust(value, to_addr=self._radio_addr)
        )

    async def get_dash_ratio(self) -> int:
        """Read dash ratio (28-45)."""
        return await self._get_bcd_level(
            get_dash_ratio(to_addr=self._radio_addr),
            key="get_dash_ratio",
            command=0x1A,
            sub=0x05,
            prefix=b"\x02\x28",
            bcd_bytes=1,
        )

    async def set_dash_ratio(self, value: int) -> None:
        """Set dash ratio (28-45)."""
        await self._send_fire_and_forget(
            set_dash_ratio(value, to_addr=self._radio_addr)
        )

    async def get_nb_depth(self) -> int:
        """Read NB depth (0-9)."""
        return await self._get_bcd_level(
            get_nb_depth(to_addr=self._radio_addr),
            key="get_nb_depth",
            command=0x1A,
            sub=0x05,
            prefix=b"\x02\x90",
            bcd_bytes=1,
        )

    async def set_nb_depth(self, value: int) -> None:
        """Set NB depth (0-9)."""
        await self._send_fire_and_forget(
            set_nb_depth(value, to_addr=self._radio_addr)
        )

    async def get_nb_width(self) -> int:
        """Read NB width (0-255)."""
        return await self._get_bcd_level(
            get_nb_width(to_addr=self._radio_addr),
            key="get_nb_width",
            command=0x1A,
            sub=0x05,
            prefix=b"\x02\x91",
        )

    async def set_nb_width(self, value: int) -> None:
        """Set NB width (0-255)."""
        await self._send_fire_and_forget(
            set_nb_width(value, to_addr=self._radio_addr)
        )

    async def get_af_mute(self, receiver: int = RECEIVER_MAIN) -> bool:
        """Read AF mute status."""
        self._require_receiver(receiver, operation="get_af_mute")
        self._require_cmd29_route(
            0x1A, 0x09, receiver=receiver, operation="get_af_mute"
        )
        civ = get_af_mute(to_addr=self._radio_addr, receiver=receiver)
        return await self._get_bool_value(
            civ, key=f"get_af_mute:{receiver}", command=0x1A, sub=0x09
        )

    async def set_af_mute(self, on: bool, receiver: int = RECEIVER_MAIN) -> None:
        """Set AF mute status."""
        self._require_receiver(receiver, operation="set_af_mute")
        self._require_cmd29_route(
            0x1A, 0x09, receiver=receiver, operation="set_af_mute"
        )
        await self._send_fire_and_forget(
            set_af_mute(on, to_addr=self._radio_addr, receiver=receiver)
        )

    async def get_s_meter_sql_status(self, receiver: int = RECEIVER_MAIN) -> bool:
        """Read S-meter squelch status for the selected receiver."""
        self._require_receiver(receiver, operation="get_s_meter_sql_status")
        self._require_cmd29_route(
            0x15, 0x01, receiver=receiver, operation="get_s_meter_sql_status"
        )
        civ = get_s_meter_sql_status(to_addr=self._radio_addr, receiver=receiver)
        return await self._get_bool_value(
            civ,
            key=f"get_s_meter_sql_status:{receiver}",
            command=0x15,
            sub=0x01,
        )

    async def get_overflow_status(self) -> bool:
        """Read OVF indicator status."""
        civ = get_overflow_status(to_addr=self._radio_addr)
        return await self._get_bool_value(
            civ,
            key="get_overflow_status",
            command=0x15,
            sub=0x07,
        )

    async def get_agc(self) -> AgcMode:
        """Read AGC mode."""
        value = await self._get_bcd_level(
            get_agc(to_addr=self._radio_addr),
            key="get_agc",
            command=0x16,
            sub=0x12,
            bcd_bytes=1,
        )
        return AgcMode(value)

    async def set_agc(self, mode: AgcMode | int) -> None:
        """Set AGC mode."""
        agc = AgcMode(mode)
        await self._send_fire_and_forget(set_agc(agc, to_addr=self._radio_addr))

    async def get_audio_peak_filter(
        self, receiver: int = RECEIVER_MAIN
    ) -> AudioPeakFilter:
        """Read audio peak filter mode."""
        self._require_receiver(receiver, operation="get_audio_peak_filter")
        self._require_cmd29_route(
            0x16, 0x32, receiver=receiver, operation="get_audio_peak_filter"
        )
        value = await self._get_bcd_level(
            get_audio_peak_filter(to_addr=self._radio_addr, receiver=receiver),
            key=f"get_audio_peak_filter:{receiver}",
            command=0x16,
            sub=0x32,
            bcd_bytes=1,
        )
        return AudioPeakFilter(value)

    async def set_audio_peak_filter(
        self,
        mode: AudioPeakFilter | int,
        receiver: int = RECEIVER_MAIN,
    ) -> None:
        """Set audio peak filter mode."""
        self._require_receiver(receiver, operation="set_audio_peak_filter")
        self._require_cmd29_route(
            0x16, 0x32, receiver=receiver, operation="set_audio_peak_filter"
        )
        apf = AudioPeakFilter(mode)
        await self._send_fire_and_forget(
            set_audio_peak_filter(apf, to_addr=self._radio_addr, receiver=receiver)
        )

    async def get_auto_notch(self, receiver: int = RECEIVER_MAIN) -> bool:
        """Read auto-notch status."""
        self._require_receiver(receiver, operation="get_auto_notch")
        self._require_cmd29_route(
            0x16, 0x41, receiver=receiver, operation="get_auto_notch"
        )
        civ = get_auto_notch(to_addr=self._radio_addr, receiver=receiver)
        return await self._get_bool_value(
            civ,
            key=f"get_auto_notch:{receiver}",
            command=0x16,
            sub=0x41,
        )

    async def set_auto_notch(
        self, on: bool, receiver: int = RECEIVER_MAIN
    ) -> None:
        """Set auto-notch status."""
        self._require_receiver(receiver, operation="set_auto_notch")
        self._require_cmd29_route(
            0x16, 0x41, receiver=receiver, operation="set_auto_notch"
        )
        await self._send_fire_and_forget(
            set_auto_notch(on, to_addr=self._radio_addr, receiver=receiver)
        )

    async def get_compressor(self) -> bool:
        """Read speech compressor status."""
        civ = get_compressor(to_addr=self._radio_addr)
        return await self._get_bool_value(
            civ, key="get_compressor", command=0x16, sub=0x44
        )

    async def set_compressor(self, on: bool) -> None:
        """Set speech compressor status."""
        await self._send_fire_and_forget(set_compressor(on, to_addr=self._radio_addr))

    async def get_monitor(self) -> bool:
        """Read monitor status."""
        civ = get_monitor(to_addr=self._radio_addr)
        return await self._get_bool_value(
            civ, key="get_monitor", command=0x16, sub=0x45
        )

    async def set_monitor(self, on: bool) -> None:
        """Set monitor status."""
        await self._send_fire_and_forget(set_monitor(on, to_addr=self._radio_addr))

    async def get_vox(self) -> bool:
        """Read VOX status."""
        civ = get_vox(to_addr=self._radio_addr)
        return await self._get_bool_value(civ, key="get_vox", command=0x16, sub=0x46)

    async def set_vox(self, on: bool) -> None:
        """Set VOX status."""
        await self._send_fire_and_forget(set_vox(on, to_addr=self._radio_addr))

    async def get_break_in(self) -> BreakInMode:
        """Read break-in mode."""
        value = await self._get_bcd_level(
            get_break_in(to_addr=self._radio_addr),
            key="get_break_in",
            command=0x16,
            sub=0x47,
            bcd_bytes=1,
        )
        return BreakInMode(value)

    async def set_break_in(self, mode: BreakInMode | int) -> None:
        """Set break-in mode."""
        break_in = BreakInMode(mode)
        await self._send_fire_and_forget(
            set_break_in(break_in, to_addr=self._radio_addr)
        )

    async def get_manual_notch(self, receiver: int = RECEIVER_MAIN) -> bool:
        """Read manual-notch status."""
        self._require_receiver(receiver, operation="get_manual_notch")
        self._require_cmd29_route(
            0x16, 0x48, receiver=receiver, operation="get_manual_notch"
        )
        civ = get_manual_notch(to_addr=self._radio_addr, receiver=receiver)
        return await self._get_bool_value(
            civ,
            key=f"get_manual_notch:{receiver}",
            command=0x16,
            sub=0x48,
        )

    async def set_manual_notch(
        self, on: bool, receiver: int = RECEIVER_MAIN
    ) -> None:
        """Set manual-notch status."""
        self._require_receiver(receiver, operation="set_manual_notch")
        self._require_cmd29_route(
            0x16, 0x48, receiver=receiver, operation="set_manual_notch"
        )
        await self._send_fire_and_forget(
            set_manual_notch(on, to_addr=self._radio_addr, receiver=receiver)
        )

    async def get_twin_peak_filter(self, receiver: int = RECEIVER_MAIN) -> bool:
        """Read twin peak filter status."""
        self._require_receiver(receiver, operation="get_twin_peak_filter")
        self._require_cmd29_route(
            0x16, 0x4F, receiver=receiver, operation="get_twin_peak_filter"
        )
        civ = get_twin_peak_filter(to_addr=self._radio_addr, receiver=receiver)
        return await self._get_bool_value(
            civ,
            key=f"get_twin_peak_filter:{receiver}",
            command=0x16,
            sub=0x4F,
        )

    async def set_twin_peak_filter(
        self, on: bool, receiver: int = RECEIVER_MAIN
    ) -> None:
        """Set twin peak filter status."""
        self._require_receiver(receiver, operation="set_twin_peak_filter")
        self._require_cmd29_route(
            0x16, 0x4F, receiver=receiver, operation="set_twin_peak_filter"
        )
        await self._send_fire_and_forget(
            set_twin_peak_filter(on, to_addr=self._radio_addr, receiver=receiver)
        )

    async def get_dial_lock(self) -> bool:
        """Read dial lock status."""
        civ = get_dial_lock(to_addr=self._radio_addr)
        return await self._get_bool_value(
            civ, key="get_dial_lock", command=0x16, sub=0x50
        )

    async def set_dial_lock(self, on: bool) -> None:
        """Set dial lock status."""
        await self._send_fire_and_forget(set_dial_lock(on, to_addr=self._radio_addr))

    async def get_filter_shape(
        self, receiver: int = RECEIVER_MAIN
    ) -> FilterShape:
        """Read DSP IF filter shape."""
        self._require_receiver(receiver, operation="get_filter_shape")
        self._require_cmd29_route(
            0x16, 0x56, receiver=receiver, operation="get_filter_shape"
        )
        value = await self._get_bcd_level(
            get_filter_shape(to_addr=self._radio_addr, receiver=receiver),
            key=f"get_filter_shape:{receiver}",
            command=0x16,
            sub=0x56,
            bcd_bytes=1,
        )
        return FilterShape(value)

    async def set_filter_shape(
        self,
        shape: FilterShape | int,
        receiver: int = RECEIVER_MAIN,
    ) -> None:
        """Set DSP IF filter shape."""
        self._require_receiver(receiver, operation="set_filter_shape")
        self._require_cmd29_route(
            0x16, 0x56, receiver=receiver, operation="set_filter_shape"
        )
        filter_shape = FilterShape(shape)
        await self._send_fire_and_forget(
            set_filter_shape(
                filter_shape,
                to_addr=self._radio_addr,
                receiver=receiver,
            )
        )

    async def get_ssb_tx_bandwidth(self) -> SsbTxBandwidth:
        """Read SSB transmit bandwidth preset."""
        value = await self._get_bcd_level(
            get_ssb_tx_bandwidth(to_addr=self._radio_addr),
            key="get_ssb_tx_bandwidth",
            command=0x16,
            sub=0x58,
            bcd_bytes=1,
        )
        return SsbTxBandwidth(value)

    async def set_ssb_tx_bandwidth(
        self, bandwidth: SsbTxBandwidth | int
    ) -> None:
        """Set SSB transmit bandwidth preset."""
        ssb_tx_bandwidth = SsbTxBandwidth(bandwidth)
        await self._send_fire_and_forget(
            set_ssb_tx_bandwidth(ssb_tx_bandwidth, to_addr=self._radio_addr)
        )

    async def get_main_sub_tracking(self) -> bool:
        """Read Main/Sub Tracking status."""
        civ = _get_main_sub_tracking_cmd(to_addr=self._radio_addr)
        return await self._get_bool_value(
            civ, key="get_main_sub_tracking", command=0x16, sub=0x5E
        )

    async def set_main_sub_tracking(self, on: bool) -> None:
        """Set Main/Sub Tracking status."""
        await self._send_fire_and_forget(
            _set_main_sub_tracking_cmd(on, to_addr=self._radio_addr)
        )

    async def get_agc_time_constant(self, receiver: int = RECEIVER_MAIN) -> int:
        """Read AGC time constant preset (0-13)."""
        self._require_receiver(receiver, operation="get_agc_time_constant")
        self._require_cmd29_route(
            0x1A, 0x04, receiver=receiver, operation="get_agc_time_constant"
        )
        return await self._get_bcd_level(
            get_agc_time_constant(to_addr=self._radio_addr, receiver=receiver),
            key=f"get_agc_time_constant:{receiver}",
            command=0x1A,
            sub=0x04,
            bcd_bytes=1,
        )

    async def set_agc_time_constant(
        self, value: int, receiver: int = RECEIVER_MAIN
    ) -> None:
        """Set AGC time constant preset (0-13)."""
        self._require_receiver(receiver, operation="set_agc_time_constant")
        self._require_cmd29_route(
            0x1A, 0x04, receiver=receiver, operation="set_agc_time_constant"
        )
        await self._send_fire_and_forget(
            set_agc_time_constant(
                value,
                to_addr=self._radio_addr,
                receiver=receiver,
            )
        )

    async def get_s_meter(self) -> int:
        """Read the S-meter value (0-255)."""
        self._check_connected()
        civ = get_s_meter(to_addr=self._radio_addr)
        resp = await self._send_civ_raw(civ)
        return parse_meter_response(resp)

    async def get_swr(self) -> int:
        """Read the SWR meter value (0-255)."""
        self._check_connected()
        civ = get_swr(to_addr=self._radio_addr)
        resp = await self._send_civ_raw(civ)
        return parse_meter_response(resp)

    async def get_alc(self) -> int:
        """Read the ALC meter value (0-255)."""
        self._check_connected()
        civ = get_alc(to_addr=self._radio_addr)
        resp = await self._send_civ_raw(civ)
        return parse_meter_response(resp)

    async def set_ptt(self, on: bool) -> None:
        """Toggle PTT (Push-To-Talk).

        Fire-and-forget: the command is sent at IMMEDIATE priority without
        blocking for an ACK.  The state cache is updated optimistically.

        Args:
            on: True for TX, False for RX.
        """
        self._check_connected()
        civ = (
            ptt_on(to_addr=self._radio_addr)
            if on
            else ptt_off(to_addr=self._radio_addr)
        )
        await self._send_civ_raw(civ, priority=Priority.IMMEDIATE, wait_response=False)
        self._state_cache.update_ptt(on)
        logger.debug("set_ptt(%s) sent (fire-and-forget)", on)

    # ------------------------------------------------------------------
    # Transceiver status family (#136)
    # ------------------------------------------------------------------

    async def get_band_edge_freq(self) -> int:
        """Read the current band-edge frequency in Hz."""
        self._check_connected()
        civ = get_band_edge_freq(to_addr=self._radio_addr)
        resp = await self._send_civ_raw(civ, key="get_band_edge_freq", dedupe=True)
        return parse_frequency_response(resp)

    async def get_various_squelch(
        self, receiver: int = RECEIVER_MAIN
    ) -> bool:
        """Read various-squelch status for the selected receiver."""
        self._require_receiver(receiver, operation="get_various_squelch")
        self._require_cmd29_route(
            0x15, 0x05, receiver=receiver, operation="get_various_squelch"
        )
        civ = get_various_squelch(to_addr=self._radio_addr, receiver=receiver)
        return await self._get_bool_value(
            civ,
            key=f"get_various_squelch:{receiver}",
            command=0x15,
            sub=0x05,
        )

    async def get_power_meter(self) -> int:
        """Read the RF power meter (0-255 raw BCD)."""
        self._check_connected()
        civ = get_power_meter(to_addr=self._radio_addr)
        resp = await self._send_civ_raw(civ)
        return parse_meter_response(resp)

    async def get_comp_meter(self) -> int:
        """Read the compressor meter (0-255 raw BCD)."""
        self._check_connected()
        civ = get_comp_meter(to_addr=self._radio_addr)
        resp = await self._send_civ_raw(civ)
        return parse_meter_response(resp)

    async def get_vd_meter(self) -> int:
        """Read the Vd supply voltage meter (0-255 raw BCD)."""
        self._check_connected()
        civ = get_vd_meter(to_addr=self._radio_addr)
        resp = await self._send_civ_raw(civ)
        return parse_meter_response(resp)

    async def get_id_meter(self) -> int:
        """Read the Id drain current meter (0-255 raw BCD)."""
        self._check_connected()
        civ = get_id_meter(to_addr=self._radio_addr)
        resp = await self._send_civ_raw(civ)
        return parse_meter_response(resp)

    async def speech(self, what: int = 0) -> None:
        """Trigger voice synthesizer announcement.

        Fire-and-forget.

        Args:
            what: 0 = all (S-meter, frequency, mode),
                  1 = frequency + S-meter,
                  2 = mode.
        """
        self._check_connected()
        civ = speech(what, to_addr=self._radio_addr)
        await self._send_civ_raw(civ, wait_response=False)

    async def get_transceiver_id(self) -> int:
        """Read the transceiver model ID (IC-7610 = 0x98)."""
        self._check_connected()
        civ = get_transceiver_id(to_addr=self._radio_addr)
        resp = await self._send_civ_raw(civ)
        if resp.data:
            return resp.data[0]
        return 0

    async def get_tuner_status(self) -> int:
        """Read the tuner/ATU status (0=off, 1=on, 2=tuning)."""
        self._check_connected()
        civ = get_tuner_status(to_addr=self._radio_addr)
        resp = await self._send_civ_raw(civ)
        if resp.data:
            return resp.data[0]
        return 0

    async def set_tuner_status(self, value: int) -> None:
        """Set the tuner/ATU status (0=off, 1=on, 2=tune).

        Fire-and-forget SET command.
        """
        self._check_connected()
        civ = set_tuner_status(value, to_addr=self._radio_addr)
        await self._send_civ_raw(civ, wait_response=False)

    async def get_xfc_status(self) -> bool:
        """Read XFC (transmit frequency correction) status."""
        self._check_connected()
        civ = get_xfc_status(to_addr=self._radio_addr)
        resp = await self._send_civ_raw(civ)
        return bool(resp.data[0]) if resp.data else False

    async def set_xfc_status(self, on: bool) -> None:
        """Set XFC status on/off. Fire-and-forget."""
        self._check_connected()
        civ = set_xfc_status(on, to_addr=self._radio_addr)
        await self._send_civ_raw(civ, wait_response=False)

    async def get_tx_freq_monitor(self) -> bool:
        """Read TX frequency monitor status."""
        self._check_connected()
        civ = get_tx_freq_monitor(to_addr=self._radio_addr)
        resp = await self._send_civ_raw(civ)
        return bool(resp.data[0]) if resp.data else False

    async def set_tx_freq_monitor(self, on: bool) -> None:
        """Set TX frequency monitor on/off. Fire-and-forget."""
        self._check_connected()
        civ = set_tx_freq_monitor(on, to_addr=self._radio_addr)
        await self._send_civ_raw(civ, wait_response=False)

    async def get_rit_frequency(self) -> int:
        """Read the RIT frequency offset in Hz (±9999)."""
        self._check_connected()
        civ = get_rit_frequency(to_addr=self._radio_addr)
        resp = await self._send_civ_raw(civ)
        return parse_rit_frequency_response(resp.data)

    async def set_rit_frequency(self, offset_hz: int) -> None:
        """Set the RIT frequency offset in Hz (±9999). Fire-and-forget."""
        self._check_connected()
        civ = set_rit_frequency(offset_hz, to_addr=self._radio_addr)
        await self._send_civ_raw(civ, wait_response=False)

    async def get_rit_status(self) -> bool:
        """Read RIT on/off status."""
        self._check_connected()
        civ = get_rit_status(to_addr=self._radio_addr)
        resp = await self._send_civ_raw(civ)
        return bool(resp.data[0]) if resp.data else False

    async def set_rit_status(self, on: bool) -> None:
        """Set RIT on/off. Fire-and-forget."""
        self._check_connected()
        civ = set_rit_status(on, to_addr=self._radio_addr)
        await self._send_civ_raw(civ, wait_response=False)

    async def get_rit_tx_status(self) -> bool:
        """Read RIT TX status."""
        self._check_connected()
        civ = get_rit_tx_status(to_addr=self._radio_addr)
        resp = await self._send_civ_raw(civ)
        return bool(resp.data[0]) if resp.data else False

    async def set_rit_tx_status(self, on: bool) -> None:
        """Set RIT TX status on/off. Fire-and-forget."""
        self._check_connected()
        civ = set_rit_tx_status(on, to_addr=self._radio_addr)
        await self._send_civ_raw(civ, wait_response=False)

    # ------------------------------------------------------------------
    # VFO / Split
    # ------------------------------------------------------------------

    async def select_vfo(self, vfo: str = "A") -> None:
        """Select VFO.

        Args:
            vfo: "A", "B", "MAIN", or "SUB".
                 IC-7610 uses MAIN/SUB.
        """
        self._check_connected()
        civ = _select_vfo_cmd(vfo, to_addr=self._radio_addr)
        resp = await self._send_civ_raw(civ)
        ack = parse_ack_nak(resp)
        if ack is False:
            raise CommandError(f"Radio rejected VFO select {vfo}")
        self._last_vfo = vfo.upper()

    async def vfo_equalize(self) -> None:
        """Copy VFO A to VFO B (A=B)."""
        self._check_connected()
        civ = vfo_a_equals_b(to_addr=self._radio_addr)
        await self._send_civ_raw(civ)

    async def vfo_exchange(self) -> None:
        """Swap VFO A and B."""
        self._check_connected()
        civ = vfo_swap(to_addr=self._radio_addr)
        await self._send_civ_raw(civ)

    async def set_split_mode(self, on: bool) -> None:
        """Enable or disable split mode."""
        self._check_connected()
        civ = set_split(on, to_addr=self._radio_addr)
        resp = await self._send_civ_raw(civ)
        ack = parse_ack_nak(resp)
        if ack is False:
            raise CommandError(f"Radio rejected split {'on' if on else 'off'}")
        self._last_split = on

    async def get_tuning_step(self) -> int:
        """Read the tuning step index (0-8, BCD-encoded per IC-7610, CI-V 0x10)."""
        self._check_connected()
        civ = get_tuning_step(to_addr=self._radio_addr)
        resp = await self._send_civ_raw(civ)
        if resp.data:
            b = resp.data[0]
            return ((b >> 4) & 0x0F) * 10 + (b & 0x0F)
        return 0

    async def set_tuning_step(self, step: int) -> None:
        """Set the tuning step index (0-8, BCD-encoded, CI-V 0x10). Fire-and-forget."""
        self._check_connected()
        civ = set_tuning_step(step, to_addr=self._radio_addr)
        await self._send_civ_raw(civ, wait_response=False)

    async def start_scan(self) -> None:
        """Start scanning (CI-V 0x0E 0x01). Fire-and-forget."""
        self._check_connected()
        civ = start_scan(to_addr=self._radio_addr)
        await self._send_civ_raw(civ, wait_response=False)

    async def stop_scan(self) -> None:
        """Stop scanning (CI-V 0x0E 0x00). Fire-and-forget."""
        self._check_connected()
        civ = stop_scan(to_addr=self._radio_addr)
        await self._send_civ_raw(civ, wait_response=False)

    async def get_dual_watch(self) -> bool:
        """Query dual watch status (CI-V 0x07 0xC2).

        Returns:
            True if dual watch is enabled, False otherwise.
        """
        self._check_connected()
        civ = get_dual_watch(to_addr=self._radio_addr)
        resp = await self._send_civ_raw(civ)
        # Response: cmd=0x07, data=[0xC2, <value>]
        if resp.data and len(resp.data) >= 2 and resp.data[0] == 0xC2:
            return bool(resp.data[1])
        return False

    async def set_dual_watch(self, on: bool) -> None:
        """Enable or disable dual watch (CI-V 0x07 0xC0/0xC1). Fire-and-forget."""
        self._check_connected()
        civ = set_dual_watch(on, to_addr=self._radio_addr)
        await self._send_civ_raw(civ, wait_response=False)

    async def quick_dual_watch(self) -> None:
        """One-shot dual watch trigger (CI-V 0x1A 0x05 0x00 0x32). Fire-and-forget."""
        self._check_connected()
        civ = quick_dual_watch(to_addr=self._radio_addr)
        await self._send_civ_raw(civ, wait_response=False)

    async def quick_split(self) -> None:
        """One-shot split trigger (CI-V 0x1A 0x05 0x00 0x33). Fire-and-forget."""
        self._check_connected()
        civ = quick_split(to_addr=self._radio_addr)
        await self._send_civ_raw(civ, wait_response=False)

    async def get_attenuator_level(self, receiver: int = RECEIVER_MAIN) -> int:
        """Read attenuator level in dB (Command29-aware).

        Args:
            receiver: RECEIVER_MAIN (0) or RECEIVER_SUB (1).
        """
        self._check_connected()
        self._require_capability("attenuator", operation="get_attenuator_level")
        self._require_receiver(receiver, operation="get_attenuator_level")
        if not self._profile.supports_cmd29(0x11):
            raise CommandError(
                f"get_attenuator_level is unsupported by profile {self._profile.model}: "
                "no cmd29 route for command 0x11"
            )
        civ = get_attenuator_cmd(to_addr=self._radio_addr, receiver=receiver)
        try:
            resp = await self._send_civ_raw(civ)
            if resp.data:
                raw = resp.data[0]
                val = ((raw >> 4) & 0x0F) * 10 + (raw & 0x0F)
                self._attenuator_state = val != 0
                return val
        except TimeoutError:
            pass

        if self._attenuator_state is not None:
            return 18 if self._attenuator_state else 0
        raise CommandError("Radio returned empty attenuator response")

    async def get_attenuator(self) -> bool:
        """Read attenuator state (compat wrapper)."""
        return (await self.get_attenuator_level()) > 0

    async def set_attenuator_level(
        self, db: int, receiver: int = RECEIVER_MAIN
    ) -> None:
        """Set attenuator level in dB (Command29-aware).

        Fire-and-forget: the command is sent without waiting for an ACK.
        The attenuator state is updated optimistically.

        Args:
            db: Attenuation in dB (0..45 in 3 dB steps).
            receiver: RECEIVER_MAIN (0) or RECEIVER_SUB (1).
        """
        self._check_connected()
        self._require_capability("attenuator", operation="set_attenuator_level")
        self._require_receiver(receiver, operation="set_attenuator_level")
        if not self._profile.supports_cmd29(0x11):
            raise CommandError(
                f"set_attenuator_level is unsupported by profile {self._profile.model}: "
                "no cmd29 route for command 0x11"
            )
        if db < 0 or db > 45 or db % 3 != 0:
            raise ValueError(f"Attenuator level must be 0..45 in 3 dB steps, got {db}")
        civ = set_attenuator_level(db, to_addr=self._radio_addr, receiver=receiver)
        await self._send_civ_raw(civ, wait_response=False)
        self._attenuator_state = db > 0
        logger.debug("set_attenuator(%d dB) sent (fire-and-forget)", db)

    async def set_attenuator(self, on: bool, receiver: int = RECEIVER_MAIN) -> None:
        """Enable or disable attenuator (compat wrapper, Command29-aware)."""
        self._check_connected()
        self._require_capability("attenuator", operation="set_attenuator")
        self._require_receiver(receiver, operation="set_attenuator")
        if not self._profile.supports_cmd29(0x11):
            raise CommandError(
                f"set_attenuator is unsupported by profile {self._profile.model}: "
                "no cmd29 route for command 0x11"
            )
        civ = set_attenuator(on, to_addr=self._radio_addr, receiver=receiver)
        await self._send_civ_raw(civ, wait_response=False)
        self._attenuator_state = on

    async def get_preamp(self, receiver: int = RECEIVER_MAIN) -> int:
        """Read preamp level (0=off, 1=PREAMP1, 2=PREAMP2) (Command29-aware).

        Args:
            receiver: RECEIVER_MAIN (0) or RECEIVER_SUB (1).
        """
        self._check_connected()
        self._require_capability("preamp", operation="get_preamp")
        self._require_receiver(receiver, operation="get_preamp")
        if not self._profile.supports_cmd29(0x16, 0x02):
            raise CommandError(
                f"get_preamp is unsupported by profile {self._profile.model}: "
                "no cmd29 route for command 0x16/0x02"
            )
        civ = get_preamp_cmd(to_addr=self._radio_addr, receiver=receiver)
        try:
            resp = await self._send_civ_raw(civ)
            if resp.data:
                raw = resp.data[0]
                self._preamp_level = ((raw >> 4) & 0x0F) * 10 + (raw & 0x0F)
                return self._preamp_level
        except TimeoutError:
            pass

        if self._preamp_level is not None:
            return self._preamp_level
        raise CommandError("Radio returned empty preamp response")

    async def set_preamp(self, level: int = 1, receiver: int = RECEIVER_MAIN) -> None:
        """Set preamp level (0=off, 1=PREAMP1, 2=PREAMP2) (Command29-aware).

        Args:
            level: 0=off, 1=PREAMP1, 2=PREAMP2.
            receiver: RECEIVER_MAIN (0) or RECEIVER_SUB (1).

        Raises:
            CommandError: If DIGI-SEL (IP+) is enabled. On IC-7610, PREAMP and
                DIGI-SEL are mutually exclusive — disable DIGI-SEL first.
        """
        self._check_connected()
        self._require_capability("preamp", operation="set_preamp")
        self._require_receiver(receiver, operation="set_preamp")
        self._require_cmd29_route(
            0x16,
            0x02,
            receiver=receiver,
            operation="set_preamp",
        )

        # Pre-flight: check DIGI-SEL / PREAMP mutual exclusion
        if level > 0:
            try:
                if await self.get_digisel():
                    raise CommandError(
                        f"Cannot set preamp level {level}: DIGI-SEL (IP+) is ON. "
                        "PREAMP and DIGI-SEL are mutually exclusive — disable DIGI-SEL first."
                    )
            except CommandError as exc:
                if "DIGI-SEL" in str(exc) and "mutually exclusive" in str(exc):
                    raise  # Our own error — propagate
                # get_digisel() failed (radio doesn't support it, timeout, etc.) — ignore
            except Exception:
                logger.debug("set_preamp: unexpected error checking DIGI-SEL, proceeding", exc_info=True)

        civ = set_preamp(level, to_addr=self._radio_addr, receiver=receiver)
        await self._send_civ_raw(civ, wait_response=False)
        self._preamp_level = level

    async def get_digisel(self) -> bool:
        """Read DIGI-SEL status (IC-7610 frontend selector)."""
        self._check_connected()
        self._require_capability("digisel", operation="get_digisel")
        if not self._profile.supports_cmd29(0x16, 0x4E):
            raise CommandError(
                f"get_digisel is unsupported by profile {self._profile.model}: "
                "no cmd29 route for command 0x16/0x4E"
            )
        civ = get_digisel(to_addr=self._radio_addr)
        resp = await self._send_civ_raw(civ)
        if not resp.data:
            raise CommandError("Radio returned empty DIGI-SEL response")
        raw = resp.data[0]
        val = ((raw >> 4) & 0x0F) * 10 + (raw & 0x0F)
        return bool(val)

    async def set_digisel(self, on: bool, receiver: int = 0) -> None:
        """Set DIGI-SEL status."""
        self._check_connected()
        self._require_capability("digisel", operation="set_digisel")
        self._require_receiver(receiver, operation="set_digisel")
        self._require_cmd29_route(
            0x16,
            0x4E,
            receiver=receiver,
            operation="set_digisel",
        )
        civ = set_digisel(on, to_addr=self._radio_addr, receiver=receiver)
        resp = await self._send_civ_raw(civ)
        ack = parse_ack_nak(resp)
        if ack is False:
            raise CommandError(f"Radio rejected DIGI-SEL {'on' if on else 'off'}")


    async def get_nb(self) -> bool:
        """Read Noise Blanker status."""
        self._check_connected()
        civ = get_nb(to_addr=self._radio_addr)
        resp = await self._send_civ_raw(civ)
        return resp.data[0] == 0x01 if resp.data else False

    async def set_nb(self, on: bool, receiver: int = 0) -> None:
        """Set Noise Blanker on/off."""
        self._check_connected()
        self._require_capability("nb", operation="set_nb")
        self._require_receiver(receiver, operation="set_nb")
        self._require_cmd29_route(
            0x16,
            0x22,
            receiver=receiver,
            operation="set_nb",
        )
        civ = set_nb(on, to_addr=self._radio_addr, receiver=receiver)
        await self._send_civ_raw(civ, wait_response=False)

    async def get_nr(self) -> bool:
        """Read Noise Reduction status."""
        self._check_connected()
        civ = get_nr(to_addr=self._radio_addr)
        resp = await self._send_civ_raw(civ)
        return resp.data[0] == 0x01 if resp.data else False

    async def set_nr(self, on: bool, receiver: int = 0) -> None:
        """Set Noise Reduction on/off."""
        self._check_connected()
        self._require_capability("nr", operation="set_nr")
        self._require_receiver(receiver, operation="set_nr")
        self._require_cmd29_route(
            0x16,
            0x40,
            receiver=receiver,
            operation="set_nr",
        )
        civ = set_nr(on, to_addr=self._radio_addr, receiver=receiver)
        await self._send_civ_raw(civ, wait_response=False)



    async def get_ip_plus(self) -> bool:
        """Read IP+ status."""
        self._check_connected()
        civ = get_ip_plus(to_addr=self._radio_addr)
        resp = await self._send_civ_raw(civ)
        return resp.data[0] == 0x01 if resp.data else False

    async def set_ip_plus(self, on: bool, receiver: int = 0) -> None:
        """Set IP+ on/off."""
        self._check_connected()
        self._require_capability("ip_plus", operation="set_ip_plus")
        self._require_receiver(receiver, operation="set_ip_plus")
        self._require_cmd29_route(
            0x16,
            0x65,
            receiver=receiver,
            operation="set_ip_plus",
        )
        civ = set_ip_plus(on, to_addr=self._radio_addr, receiver=receiver)
        await self._send_civ_raw(civ, wait_response=False)

    async def get_repeater_tone(self, receiver: int = 0) -> bool:
        """Read repeater tone status (0x16 0x42)."""
        civ = _get_repeater_tone_cmd(to_addr=self._radio_addr, receiver=receiver)
        return await self._get_bool_value(
            civ, key="get_repeater_tone", command=0x16, sub=_SUB_REPEATER_TONE
        )

    async def set_repeater_tone(self, on: bool, receiver: int = 0) -> None:
        """Set repeater tone on/off (0x16 0x42)."""
        await self._send_fire_and_forget(
            _set_repeater_tone_cmd(on, to_addr=self._radio_addr, receiver=receiver)
        )

    async def get_repeater_tsql(self, receiver: int = 0) -> bool:
        """Read repeater TSQL status (0x16 0x43)."""
        civ = _get_repeater_tsql_cmd(to_addr=self._radio_addr, receiver=receiver)
        return await self._get_bool_value(
            civ, key="get_repeater_tsql", command=0x16, sub=_SUB_REPEATER_TSQL
        )

    async def set_repeater_tsql(self, on: bool, receiver: int = 0) -> None:
        """Set repeater TSQL on/off (0x16 0x43)."""
        await self._send_fire_and_forget(
            _set_repeater_tsql_cmd(on, to_addr=self._radio_addr, receiver=receiver)
        )

    async def get_tone_freq(self, receiver: int = 0) -> float:
        """Read CTCSS tone frequency in Hz (0x1B 0x00)."""
        self._check_connected()
        civ = _get_tone_freq_cmd(to_addr=self._radio_addr, receiver=receiver)
        resp = await self._send_civ_raw(civ)
        _, freq = parse_tone_freq_response(resp)
        return freq

    async def set_tone_freq(self, freq_hz: float, receiver: int = 0) -> None:
        """Set CTCSS tone frequency in Hz (0x1B 0x00)."""
        await self._send_fire_and_forget(
            _set_tone_freq_cmd(freq_hz, to_addr=self._radio_addr, receiver=receiver)
        )

    async def get_tsql_freq(self, receiver: int = 0) -> float:
        """Read TSQL frequency in Hz (0x1B 0x01)."""
        self._check_connected()
        civ = _get_tsql_freq_cmd(to_addr=self._radio_addr, receiver=receiver)
        resp = await self._send_civ_raw(civ)
        _, freq = parse_tsql_freq_response(resp)
        return freq

    async def set_tsql_freq(self, freq_hz: float, receiver: int = 0) -> None:
        """Set TSQL frequency in Hz (0x1B 0x01)."""
        await self._send_fire_and_forget(
            _set_tsql_freq_cmd(freq_hz, to_addr=self._radio_addr, receiver=receiver)
        )

    # ------------------------------------------------------------------
    # System/Config commands (#135)
    # ------------------------------------------------------------------

    async def get_antenna_1(self) -> bool:
        """Read ANT1 selection status (0x12 0x00)."""
        return await self._get_bool_value(
            get_antenna_1(to_addr=self._radio_addr),
            key="get_antenna_1",
            command=0x12,
            sub=0x00,
        )

    async def set_antenna_1(self, enabled: bool) -> None:
        """Set ANT1 selection (0x12 0x00)."""
        await self._send_fire_and_forget(
            set_antenna_1(enabled, to_addr=self._radio_addr)
        )

    async def get_antenna_2(self) -> bool:
        """Read ANT2 selection status (0x12 0x01)."""
        return await self._get_bool_value(
            get_antenna_2(to_addr=self._radio_addr),
            key="get_antenna_2",
            command=0x12,
            sub=0x01,
        )

    async def set_antenna_2(self, enabled: bool) -> None:
        """Set ANT2 selection (0x12 0x01)."""
        await self._send_fire_and_forget(
            set_antenna_2(enabled, to_addr=self._radio_addr)
        )

    async def get_rx_antenna_ant1(self) -> bool:
        """Read RX antenna on ANT1 status (0x12 0x12)."""
        return await self._get_bool_value(
            get_rx_antenna_ant1(to_addr=self._radio_addr),
            key="get_rx_antenna_ant1",
            command=0x12,
            sub=0x12,
        )

    async def set_rx_antenna_ant1(self, enabled: bool) -> None:
        """Set RX antenna on ANT1 (0x12 0x12)."""
        await self._send_fire_and_forget(
            set_rx_antenna_ant1(enabled, to_addr=self._radio_addr)
        )

    async def get_rx_antenna_ant2(self) -> bool:
        """Read RX antenna on ANT2 status (0x12 0x13)."""
        return await self._get_bool_value(
            get_rx_antenna_ant2(to_addr=self._radio_addr),
            key="get_rx_antenna_ant2",
            command=0x12,
            sub=0x13,
        )

    async def set_rx_antenna_ant2(self, enabled: bool) -> None:
        """Set RX antenna on ANT2 (0x12 0x13)."""
        await self._send_fire_and_forget(
            set_rx_antenna_ant2(enabled, to_addr=self._radio_addr)
        )

    async def get_acc1_mod_level(self) -> int:
        """Read ACC1 modulation level (0-255)."""
        return await self._get_bcd_level(
            get_acc1_mod_level(to_addr=self._radio_addr),
            key="get_acc1_mod_level",
            command=0x14,
            sub=0x0B,
        )

    async def set_acc1_mod_level(self, level: int) -> None:
        """Set ACC1 modulation level (0-255)."""
        await self._send_fire_and_forget(
            set_acc1_mod_level(level, to_addr=self._radio_addr)
        )

    async def get_usb_mod_level(self) -> int:
        """Read USB modulation level (0-255)."""
        return await self._get_bcd_level(
            get_usb_mod_level(to_addr=self._radio_addr),
            key="get_usb_mod_level",
            command=0x14,
            sub=0x10,
        )

    async def set_usb_mod_level(self, level: int) -> None:
        """Set USB modulation level (0-255)."""
        await self._send_fire_and_forget(
            set_usb_mod_level(level, to_addr=self._radio_addr)
        )

    async def get_lan_mod_level(self) -> int:
        """Read LAN modulation level (0-255)."""
        return await self._get_bcd_level(
            get_lan_mod_level(to_addr=self._radio_addr),
            key="get_lan_mod_level",
            command=0x14,
            sub=0x11,
        )

    async def set_lan_mod_level(self, level: int) -> None:
        """Set LAN modulation level (0-255)."""
        await self._send_fire_and_forget(
            set_lan_mod_level(level, to_addr=self._radio_addr)
        )

    async def get_data_off_mod_input(self) -> int:
        """Read Data Off modulation input source (0-5)."""
        return await self._get_bcd_level(
            get_data_off_mod_input(to_addr=self._radio_addr),
            key="get_data_off_mod_input",
            command=0x1A,
            sub=0x05,
            prefix=b"\x00\x91",
            bcd_bytes=1,
        )

    async def set_data_off_mod_input(self, source: int) -> None:
        """Set Data Off modulation input source (0-5)."""
        await self._send_fire_and_forget(
            set_data_off_mod_input(source, to_addr=self._radio_addr)
        )

    async def get_data1_mod_input(self) -> int:
        """Read DATA1 modulation input source (0-4)."""
        return await self._get_bcd_level(
            get_data1_mod_input(to_addr=self._radio_addr),
            key="get_data1_mod_input",
            command=0x1A,
            sub=0x05,
            prefix=b"\x00\x92",
            bcd_bytes=1,
        )

    async def set_data1_mod_input(self, source: int) -> None:
        """Set DATA1 modulation input source (0-4)."""
        await self._send_fire_and_forget(
            set_data1_mod_input(source, to_addr=self._radio_addr)
        )

    async def get_data2_mod_input(self) -> int:
        """Read DATA2 modulation input source (0-4)."""
        return await self._get_bcd_level(
            get_data2_mod_input(to_addr=self._radio_addr),
            key="get_data2_mod_input",
            command=0x1A,
            sub=0x05,
            prefix=b"\x00\x93",
            bcd_bytes=1,
        )

    async def set_data2_mod_input(self, source: int) -> None:
        """Set DATA2 modulation input source (0-4)."""
        await self._send_fire_and_forget(
            set_data2_mod_input(source, to_addr=self._radio_addr)
        )

    async def get_data3_mod_input(self) -> int:
        """Read DATA3 modulation input source (0-4)."""
        return await self._get_bcd_level(
            get_data3_mod_input(to_addr=self._radio_addr),
            key="get_data3_mod_input",
            command=0x1A,
            sub=0x05,
            prefix=b"\x00\x94",
            bcd_bytes=1,
        )

    async def set_data3_mod_input(self, source: int) -> None:
        """Set DATA3 modulation input source (0-4)."""
        await self._send_fire_and_forget(
            set_data3_mod_input(source, to_addr=self._radio_addr)
        )

    async def get_civ_transceive(self) -> bool:
        """Read CI-V transceive status."""
        return await self._get_bool_value(
            get_civ_transceive(to_addr=self._radio_addr),
            key="get_civ_transceive",
            command=0x1A,
            sub=0x05,
            prefix=b"\x01\x29",
        )

    async def set_civ_transceive(self, enabled: bool) -> None:
        """Set CI-V transceive status."""
        await self._send_fire_and_forget(
            set_civ_transceive(enabled, to_addr=self._radio_addr)
        )

    async def get_civ_output_ant(self) -> bool:
        """Read CI-V output (ANT) status."""
        return await self._get_bool_value(
            get_civ_output_ant(to_addr=self._radio_addr),
            key="get_civ_output_ant",
            command=0x1A,
            sub=0x05,
            prefix=b"\x01\x30",
        )

    async def set_civ_output_ant(self, enabled: bool) -> None:
        """Set CI-V output (ANT) status."""
        await self._send_fire_and_forget(
            set_civ_output_ant(enabled, to_addr=self._radio_addr)
        )

    async def get_system_date(self) -> tuple[int, int, int]:
        """Read system date as (year, month, day)."""
        self._check_connected()
        civ = get_system_date(to_addr=self._radio_addr)
        resp = await self._send_civ_raw(civ, key="get_system_date", dedupe=True)
        return parse_system_date_response(resp)

    async def set_system_date(self, year: int, month: int, day: int) -> None:
        """Set system date.

        Args:
            year: 4-digit year.
            month: Month 1-12.
            day: Day 1-31.
        """
        await self._send_fire_and_forget(
            set_system_date(year, month, day, to_addr=self._radio_addr)
        )

    async def get_system_time(self) -> tuple[int, int]:
        """Read system time as (hour, minute)."""
        self._check_connected()
        civ = get_system_time(to_addr=self._radio_addr)
        resp = await self._send_civ_raw(civ, key="get_system_time", dedupe=True)
        return parse_system_time_response(resp)

    async def set_system_time(self, hour: int, minute: int) -> None:
        """Set system time.

        Args:
            hour: Hour 0-23.
            minute: Minute 0-59.
        """
        await self._send_fire_and_forget(
            set_system_time(hour, minute, to_addr=self._radio_addr)
        )

    async def get_utc_offset(self) -> tuple[int, int, bool]:
        """Read UTC offset as (hours, minutes, is_negative)."""
        self._check_connected()
        civ = get_utc_offset(to_addr=self._radio_addr)
        resp = await self._send_civ_raw(civ, key="get_utc_offset", dedupe=True)
        return parse_utc_offset_response(resp)

    async def set_utc_offset(self, hours: int, minutes: int, is_negative: bool) -> None:
        """Set UTC offset.

        Args:
            hours: Offset hours 0-14.
            minutes: Offset minutes, one of 0/15/30/45.
            is_negative: True for negative (west) offset.
        """
        await self._send_fire_and_forget(
            set_utc_offset(hours, minutes, is_negative, to_addr=self._radio_addr)
        )

    async def snapshot_state(self) -> dict[str, object]:
        """Best-effort snapshot of core rig state for safe restore."""
        self._check_connected()
        state: dict[str, object] = {}

        try:
            state["frequency"] = await self.get_frequency()
        except Exception:
            logger.debug("snapshot: get_frequency failed, using cache", exc_info=True)
            if self._last_freq_hz is not None:
                state["frequency"] = self._last_freq_hz

        try:
            mode, filt = await self.get_mode_info()
            state["mode"] = mode
            if filt is not None:
                state["filter"] = filt
        except Exception:
            logger.debug("snapshot: get_mode_info failed, using cache", exc_info=True)
            if self._last_mode is not None:
                state["mode"] = self._last_mode
            if self._filter_width is not None:
                state["filter"] = self._filter_width

        try:
            state["power"] = await self.get_power()
        except Exception:
            logger.debug("snapshot: get_power failed, using cache", exc_info=True)
            if self._last_power is not None:
                state["power"] = self._last_power

        if self._last_split is not None:
            state["split"] = self._last_split
        if self._last_vfo is not None:
            state["vfo"] = self._last_vfo
        if self._attenuator_state is not None:
            state["attenuator"] = self._attenuator_state
        if self._preamp_level is not None:
            state["preamp"] = self._preamp_level

        return state

    async def restore_state(self, state: dict[str, object]) -> None:
        """Best-effort restore of state produced by snapshot_state()."""
        self._check_connected()

        if "split" in state:
            try:
                await self.set_split_mode(bool(state["split"]))
            except Exception:
                logger.debug("restore_state: set_split_mode failed", exc_info=True)
        if "vfo" in state:
            try:
                await self.select_vfo(str(state["vfo"]))
            except Exception:
                logger.debug("restore_state: select_vfo failed", exc_info=True)

        if "power" in state:
            try:
                await self.set_power(int(state["power"]))
            except Exception:
                logger.debug("restore_state: set_power failed", exc_info=True)

        mode = state.get("mode")
        filt = state.get("filter")
        if isinstance(mode, Mode):
            try:
                await self.set_mode(
                    mode, filter_width=int(filt) if isinstance(filt, int) else None
                )
            except Exception:
                logger.debug("restore_state: set_mode failed", exc_info=True)

        if "frequency" in state:
            try:
                await self.set_frequency(int(state["frequency"]))
            except Exception:
                logger.debug("restore_state: set_frequency failed", exc_info=True)

        if "attenuator" in state:
            try:
                await self.set_attenuator(bool(state["attenuator"]))
            except Exception:
                logger.debug("restore_state: set_attenuator failed", exc_info=True)

        if "preamp" in state:
            try:
                await self.set_preamp(int(state["preamp"]))
            except Exception:
                logger.debug("restore_state: set_preamp failed", exc_info=True)

    async def run_state_transaction(
        self,
        body: "Callable[[], Awaitable[None]]",
    ) -> None:
        """Run operation with snapshot/restore guard (wfview-style safety pattern)."""
        self._check_connected()

        async def _body() -> dict[str, object]:
            await body()
            return {}

        if self._commander is None:
            snapshot = await self.snapshot_state()
            try:
                await body()
            finally:
                await self.restore_state(snapshot)
            return

        await self._commander.transaction(
            snapshot=self.snapshot_state,
            restore=self.restore_state,
            body=_body,
        )

    # ------------------------------------------------------------------
    # CW keying
    # ------------------------------------------------------------------

    async def send_cw_text(self, text: str) -> None:
        """Send CW text via the radio's built-in keyer.

        Text is split into 30-character chunks.

        Args:
            text: CW text (A-Z, 0-9, prosigns).
        """
        self._check_connected()
        frames = send_cw(text, to_addr=self._radio_addr)
        for frame in frames:
            resp = await self._send_civ_raw(frame)
            ack = parse_ack_nak(resp)
            if ack is False:
                raise CommandError("Radio rejected CW text")

    async def stop_cw_text(self) -> None:
        """Stop CW sending."""
        self._check_connected()
        civ = stop_cw(to_addr=self._radio_addr)
        await self._send_civ_raw(civ, priority=Priority.IMMEDIATE)
        # Stop CW may not return ACK, just ignore

    async def power_control(self, on: bool) -> None:
        """Power the radio on or off.

        Args:
            on: True to power on, False to power off.
        """
        await self.set_powerstat(on)

    async def set_powerstat(self, on: bool) -> None:
        """Power the radio on or off (PowerControlCapable protocol)."""
        self._check_connected()
        civ = (
            power_on(to_addr=self._radio_addr)
            if on
            else power_off(to_addr=self._radio_addr)
        )
        resp = await self._send_civ_raw(civ)
        ack = parse_ack_nak(resp)
        if ack is False:
            raise CommandError(f"Radio rejected power {'on' if on else 'off'}")

    # ------------------------------------------------------------------
    # Scope / Waterfall API
    # ------------------------------------------------------------------

    def on_scope_data(self, callback: "Callable[[ScopeFrame], None] | None") -> None:
        """Register a callback for completed scope frames.

        Args:
            callback: Function taking a ScopeFrame, or None to unregister.
        """
        self._scope_callback = callback

    def _scope_controls(self):
        """Return the mutable scope-control state bucket."""
        return self._radio_state.scope_controls

    def _apply_scope_receiver_hint(self, receiver: int | None) -> None:
        if receiver is not None:
            self._scope_controls().receiver = receiver

    async def scope_stream(self) -> AsyncGenerator[ScopeFrame, None]:
        """Consume scope frames asynchronously.

        Yields:
            ScopeFrame objects as they are assembled.
            Stops yielding if the radio disconnects.

        Note:
            Uses a bounded queue (maxsize=64) that drops oldest frames if not
            consumed fast enough. Call enable_scope() separately to start data.
        """
        while self._connected:
            try:
                frame = await asyncio.wait_for(
                    self._scope_frame_queue.get(), timeout=1.0
                )
                yield frame
                self._scope_frame_queue.task_done()
            except asyncio.TimeoutError:
                continue

    async def enable_scope(
        self,
        *,
        output: bool = True,
        policy: ScopeCompletionPolicy | str = ScopeCompletionPolicy.VERIFY,
        timeout: float = 5.0,
    ) -> None:
        """Enable scope display and data output on the radio.

        Args:
            output: Also enable wave data output (default True).
            policy: Completion policy (strict, fast, verify).
            timeout: Verification timeout in seconds.

        Raises:
            CommandError: If the radio rejects the command (in strict mode).
            TimeoutError: If verification times out (in verify mode).
        """
        self._check_connected()
        pol = ScopeCompletionPolicy(policy)
        wait_resp = pol == ScopeCompletionPolicy.STRICT

        if pol == ScopeCompletionPolicy.VERIFY:
            self._scope_activity_event.clear()

        resp = await self._send_civ_raw(
            _scope_on_cmd(to_addr=self._radio_addr), wait_response=wait_resp
        )
        if wait_resp and resp is not None:
            if parse_ack_nak(resp) is False:
                raise CommandError("Radio rejected scope enable")
        if output:
            resp = await self._send_civ_raw(
                _scope_data_output_cmd(True, to_addr=self._radio_addr),
                wait_response=wait_resp,
            )
            if wait_resp and resp is not None:
                if parse_ack_nak(resp) is False:
                    raise CommandError("Radio rejected scope data output enable")

        if pol == ScopeCompletionPolicy.VERIFY:
            try:
                await asyncio.wait_for(
                    self._scope_activity_event.wait(), timeout=timeout
                )
            except asyncio.TimeoutError:
                raise TimeoutError("Scope enable verification timed out (no data seen)")

    async def disable_scope(
        self, *, policy: ScopeCompletionPolicy | str = ScopeCompletionPolicy.FAST
    ) -> None:
        """Disable scope data output on the radio.

        Args:
            policy: Completion policy, usually fast.

        Raises:
            CommandError: If the radio rejects the command (strict mode).
        """
        self._check_connected()
        pol = ScopeCompletionPolicy(policy)
        wait_resp = pol == ScopeCompletionPolicy.STRICT

        resp = await self._send_civ_raw(
            _scope_data_output_cmd(False, to_addr=self._radio_addr),
            wait_response=wait_resp,
        )
        if wait_resp and resp is not None:
            if parse_ack_nak(resp) is False:
                raise CommandError("Radio rejected scope data output disable")

    async def get_scope_receiver(self) -> int:
        """Read the selected scope receiver (0=MAIN, 1=SUB)."""
        self._check_connected()
        resp = await self._send_civ_raw(_get_scope_main_sub_cmd(to_addr=self._radio_addr))
        receiver = parse_scope_main_sub_response(resp)
        self._scope_controls().receiver = receiver
        return receiver

    async def set_scope_receiver(self, receiver: int) -> None:
        """Select the scope receiver (0=MAIN, 1=SUB)."""
        self._check_connected()
        if receiver not in (0, 1):
            raise ValueError(f"scope receiver must be 0 or 1, got {receiver}")
        await self._send_civ_raw(
            _scope_main_sub_cmd(receiver, to_addr=self._radio_addr),
            wait_response=False,
        )
        self._scope_controls().receiver = receiver

    async def get_scope_dual(self) -> bool:
        """Read whether the scope is in dual-display mode."""
        self._check_connected()
        resp = await self._send_civ_raw(_get_scope_single_dual_cmd(to_addr=self._radio_addr))
        dual = parse_scope_single_dual_response(resp)
        self._scope_controls().dual = dual
        return dual

    async def set_scope_dual(self, dual: bool) -> None:
        """Enable or disable dual scope mode."""
        self._check_connected()
        await self._send_civ_raw(
            _scope_single_dual_cmd(dual, to_addr=self._radio_addr),
            wait_response=False,
        )
        self._scope_controls().dual = dual

    async def get_scope_mode(self) -> int:
        """Read the current scope mode (0=center, 1=fixed, 2=scroll-C, 3=scroll-F)."""
        self._check_connected()
        resp = await self._send_civ_raw(_get_scope_mode_cmd(to_addr=self._radio_addr))
        receiver, mode = parse_scope_mode_response(resp)
        self._apply_scope_receiver_hint(receiver)
        self._scope_controls().mode = mode
        return mode

    async def set_scope_mode(self, mode: int) -> None:
        """Set the scope mode (0=center, 1=fixed, 2=scroll-C, 3=scroll-F)."""
        self._check_connected()
        await self._send_civ_raw(
            _scope_set_mode_cmd(mode, to_addr=self._radio_addr),
            wait_response=False,
        )
        self._scope_controls().mode = mode

    async def get_scope_span(self) -> int:
        """Read the scope span preset index (0..7)."""
        self._check_connected()
        resp = await self._send_civ_raw(_get_scope_span_cmd(to_addr=self._radio_addr))
        receiver, span = parse_scope_span_response(resp)
        self._apply_scope_receiver_hint(receiver)
        self._scope_controls().span = span
        return span

    async def set_scope_span(self, span: int) -> None:
        """Set the scope span preset index (0..7)."""
        self._check_connected()
        await self._send_civ_raw(
            _scope_set_span_cmd(span, to_addr=self._radio_addr),
            wait_response=False,
        )
        self._scope_controls().span = span

    async def get_scope_edge(self) -> int:
        """Read the fixed-edge selection (1..4)."""
        self._check_connected()
        resp = await self._send_civ_raw(_get_scope_edge_cmd(to_addr=self._radio_addr))
        receiver, edge = parse_scope_edge_response(resp)
        self._apply_scope_receiver_hint(receiver)
        self._scope_controls().edge = edge
        return edge

    async def set_scope_edge(self, edge: int) -> None:
        """Set the fixed-edge selection (1..4)."""
        self._check_connected()
        await self._send_civ_raw(
            _scope_set_edge_cmd(edge, to_addr=self._radio_addr),
            wait_response=False,
        )
        self._scope_controls().edge = edge

    async def get_scope_hold(self) -> bool:
        """Read whether scope hold is enabled."""
        self._check_connected()
        resp = await self._send_civ_raw(_get_scope_hold_cmd(to_addr=self._radio_addr))
        receiver, hold = parse_scope_hold_response(resp)
        self._apply_scope_receiver_hint(receiver)
        self._scope_controls().hold = hold
        return hold

    async def set_scope_hold(self, on: bool) -> None:
        """Enable or disable scope hold."""
        self._check_connected()
        await self._send_civ_raw(
            _scope_set_hold_cmd(on, to_addr=self._radio_addr),
            wait_response=False,
        )
        self._scope_controls().hold = on

    async def get_scope_ref(self) -> float:
        """Read the scope reference level in dB."""
        self._check_connected()
        resp = await self._send_civ_raw(_get_scope_ref_cmd(to_addr=self._radio_addr))
        receiver, ref_db = parse_scope_ref_response(resp)
        self._apply_scope_receiver_hint(receiver)
        self._scope_controls().ref_db = ref_db
        return ref_db

    async def set_scope_ref(self, ref: float) -> None:
        """Set the scope reference level in dB."""
        self._check_connected()
        await self._send_civ_raw(
            _scope_set_ref_cmd(ref, to_addr=self._radio_addr),
            wait_response=False,
        )
        self._scope_controls().ref_db = ref

    async def get_scope_speed(self) -> int:
        """Read the scope speed preset (0=fast, 1=mid, 2=slow)."""
        self._check_connected()
        resp = await self._send_civ_raw(_get_scope_speed_cmd(to_addr=self._radio_addr))
        receiver, speed = parse_scope_speed_response(resp)
        self._apply_scope_receiver_hint(receiver)
        self._scope_controls().speed = speed
        return speed

    async def set_scope_speed(self, speed: int) -> None:
        """Set the scope speed preset (0=fast, 1=mid, 2=slow)."""
        self._check_connected()
        await self._send_civ_raw(
            _scope_set_speed_cmd(speed, to_addr=self._radio_addr),
            wait_response=False,
        )
        self._scope_controls().speed = speed

    async def get_scope_during_tx(self) -> bool:
        """Read whether the scope remains visible during transmit."""
        self._check_connected()
        resp = await self._send_civ_raw(_get_scope_during_tx_cmd(to_addr=self._radio_addr))
        during_tx = parse_scope_during_tx_response(resp)
        self._scope_controls().during_tx = during_tx
        return during_tx

    async def set_scope_during_tx(self, on: bool) -> None:
        """Enable or disable scope during transmit."""
        self._check_connected()
        await self._send_civ_raw(
            _scope_set_during_tx_cmd(on, to_addr=self._radio_addr),
            wait_response=False,
        )
        self._scope_controls().during_tx = on

    async def get_scope_center_type(self) -> int:
        """Read the scope center-type setting (0..2)."""
        self._check_connected()
        resp = await self._send_civ_raw(_get_scope_center_type_cmd(to_addr=self._radio_addr))
        receiver, center_type = parse_scope_center_type_response(resp)
        self._apply_scope_receiver_hint(receiver)
        self._scope_controls().center_type = center_type
        return center_type

    async def set_scope_center_type(self, center_type: int) -> None:
        """Set the scope center-type setting (0..2)."""
        self._check_connected()
        await self._send_civ_raw(
            _scope_set_center_type_cmd(center_type, to_addr=self._radio_addr),
            wait_response=False,
        )
        self._scope_controls().center_type = center_type

    async def get_scope_vbw(self) -> bool:
        """Read whether narrow scope VBW is enabled."""
        self._check_connected()
        resp = await self._send_civ_raw(_get_scope_vbw_cmd(to_addr=self._radio_addr))
        receiver, narrow = parse_scope_vbw_response(resp)
        self._apply_scope_receiver_hint(receiver)
        self._scope_controls().vbw_narrow = narrow
        return narrow

    async def set_scope_vbw(self, narrow: bool) -> None:
        """Enable or disable narrow scope VBW."""
        self._check_connected()
        await self._send_civ_raw(
            _scope_set_vbw_cmd(narrow, to_addr=self._radio_addr),
            wait_response=False,
        )
        self._scope_controls().vbw_narrow = narrow

    async def get_scope_fixed_edge(self) -> ScopeFixedEdge:
        """Read the fixed-edge scope bounds."""
        self._check_connected()
        resp = await self._send_civ_raw(_get_scope_fixed_edge_cmd(to_addr=self._radio_addr))
        fixed_edge = parse_scope_fixed_edge_response(resp)
        self._scope_controls().fixed_edge = fixed_edge
        self._scope_controls().edge = fixed_edge.edge
        return fixed_edge

    async def set_scope_fixed_edge(
        self,
        *,
        edge: int,
        start_hz: int,
        end_hz: int,
        range_index: int | None = None,
    ) -> None:
        """Set the fixed-edge scope bounds."""
        self._check_connected()
        civ = _scope_set_fixed_edge_cmd(
            edge=edge,
            start_hz=start_hz,
            end_hz=end_hz,
            range_index=range_index,
            to_addr=self._radio_addr,
        )
        await self._send_civ_raw(
            civ,
            wait_response=False,
        )
        # Re-parse the frame we just built to recover the resolved range_index
        # (computed inside scope_set_fixed_edge_cmd) without duplicating logic.
        fixed_edge = parse_scope_fixed_edge_response(parse_civ_frame(civ))
        self._scope_controls().fixed_edge = fixed_edge
        self._scope_controls().edge = fixed_edge.edge

    async def get_scope_rbw(self) -> int:
        """Read the scope RBW preset (0=wide, 1=mid, 2=narrow)."""
        self._check_connected()
        resp = await self._send_civ_raw(_get_scope_rbw_cmd(to_addr=self._radio_addr))
        receiver, rbw = parse_scope_rbw_response(resp)
        self._apply_scope_receiver_hint(receiver)
        self._scope_controls().rbw = rbw
        return rbw

    async def set_scope_rbw(self, rbw: int) -> None:
        """Set the scope RBW preset (0=wide, 1=mid, 2=narrow)."""
        self._check_connected()
        await self._send_civ_raw(
            _scope_set_rbw_cmd(rbw, to_addr=self._radio_addr),
            wait_response=False,
        )
        self._scope_controls().rbw = rbw

    async def capture_scope_frame(self, timeout: float = 5.0) -> ScopeFrame:
        """Enable scope and capture one complete frame.

        Does NOT disable scope after — caller decides when to stop.

        Args:
            timeout: Maximum time to wait for a frame in seconds.

        Returns:
            First complete ScopeFrame received.

        Raises:
            TimeoutError: If no frame is received within timeout.
        """
        frames = await self.capture_scope_frames(count=1, timeout=timeout)
        return frames[0]

    async def capture_scope_frames(
        self, count: int = 50, timeout: float = 10.0
    ) -> list[ScopeFrame]:
        """Enable scope and capture *count* complete frames.

        Does NOT disable scope after — caller decides when to stop.

        Args:
            count: Number of complete frames to capture.
            timeout: Maximum time to wait in seconds.

        Returns:
            List of ScopeFrame objects, oldest first.

        Raises:
            TimeoutError: If fewer than *count* frames arrive within timeout.
        """
        self._check_connected()

        collected: list[ScopeFrame] = []
        frame_ready = asyncio.Event()

        def _on_frame(frame: ScopeFrame) -> None:
            collected.append(frame)
            if len(collected) >= count:
                frame_ready.set()

        old_callback = self._scope_callback
        self.on_scope_data(_on_frame)
        try:
            await self.enable_scope(policy=ScopeCompletionPolicy.VERIFY, timeout=timeout)
            try:
                await asyncio.wait_for(frame_ready.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                raise TimeoutError(
                    f"Scope capture timed out: received {len(collected)}/{count} frames"
                )
        finally:
            self.on_scope_data(old_callback)
        return collected[:count]

    # --- Memory Commands ---

    async def get_memory_mode(self) -> int:
        """Get currently selected memory channel (1-101).
        
        Raises:
            NotImplementedError: IC-7610 does not support reading the current
                memory channel. Command 0x08 is SELECT-only per the official
                CI-V Reference Manual.
        """
        raise NotImplementedError(
            "IC-7610 does not support reading the current memory channel. "
            "Command 0x08 is SELECT-only (no GET variant). "
            "See IC-7610 CI-V Reference Manual page 4."
        )

    async def set_memory_mode(self, channel: int) -> None:
        """Select memory channel (1-101)."""
        if not 1 <= channel <= 101:
            raise ValueError(f"Channel must be 1-101, got {channel}")
        await self._send_fire_and_forget(
            build_memory_mode_set(channel, to_addr=self._radio_addr)
        )

    async def memory_write(self) -> None:
        """Write current VFO state to selected memory channel."""
        await self._send_fire_and_forget(
            build_memory_write(to_addr=self._radio_addr)
        )

    async def memory_to_vfo(self, channel: int) -> None:
        """Load memory channel to VFO."""
        if not 1 <= channel <= 101:
            raise ValueError(f"Channel must be 1-101, got {channel}")
        await self._send_fire_and_forget(
            build_memory_to_vfo(channel, to_addr=self._radio_addr)
        )

    async def memory_clear(self, channel: int) -> None:
        """Clear memory channel."""
        if not 1 <= channel <= 101:
            raise ValueError(f"Channel must be 1-101, got {channel}")
        await self._send_fire_and_forget(
            build_memory_clear(channel, to_addr=self._radio_addr)
        )

    async def get_memory_contents(self, channel: int) -> MemoryChannel:
        """Read full memory channel data.
        
        Args:
            channel: Memory channel number (1-101).
            
        Raises:
            NotImplementedError: IC-7610 does not support reading memory
                contents. Command 0x1A 0x00 GET is not documented in the
                official CI-V Reference Manual.
        """
        if not 1 <= channel <= 101:
            raise ValueError(f"Channel must be 1-101, got {channel}")
        raise NotImplementedError(
            f"IC-7610 does not support reading memory channel {channel} contents. "
            "Command 0x1A 0x00 GET is not documented in the CI-V Reference Manual."
        )

    async def set_memory_contents(self, mem: MemoryChannel) -> None:
        """Write full memory channel data."""
        if not 1 <= mem.channel <= 101:
            raise ValueError(f"Channel must be 1-101, got {mem.channel}")
        await self._send_fire_and_forget(
            build_memory_contents_set(mem, to_addr=self._radio_addr)
        )

    async def get_band_stack(
        self, band: int, register: int
    ) -> BandStackRegister:
        """Read band stacking register (band 0-24, register 1-3).
        
        Args:
            band: Band number (0-24).
            register: Register number (1-3).
            
        Raises:
            NotImplementedError: IC-7610 does not support reading band
                stacking registers. Command 0x1A 0x01 GET is not documented
                in the official CI-V Reference Manual.
        """
        if not 0 <= band <= 24:
            raise ValueError(f"Band must be 0-24, got {band}")
        if not 1 <= register <= 3:
            raise ValueError(f"Register must be 1-3, got {register}")
        raise NotImplementedError(
            f"IC-7610 does not support reading band stack register (band={band}, reg={register}). "
            "Command 0x1A 0x01 GET is not documented in the CI-V Reference Manual."
        )

    async def set_band_stack(self, bsr: BandStackRegister) -> None:
        """Write band stacking register."""
        if not 0 <= bsr.band <= 24:
            raise ValueError(f"Band must be 0-24, got {bsr.band}")
        if not 1 <= bsr.register <= 3:
            raise ValueError(f"Register must be 1-3, got {bsr.register}")
        await self._send_fire_and_forget(
            build_band_stack_set(bsr, to_addr=self._radio_addr)
        )


class IcomRadio(Icom7610CoreRadio):
    """LAN adapter for IC-7610 built on top of the shared executable core."""

    pass


# ---------------------------------------------------------------------------
# Protocol compliance checks (not executed automatically — call explicitly)
# ---------------------------------------------------------------------------

def _check_protocol_compliance() -> None:
    """Verify IcomRadio satisfies all Radio protocol variants.

    Note: ``@runtime_checkable`` checks only method/attribute *existence*.
    It does not validate full runtime semantics.
    """
    from .radio_protocol import AudioCapable, DualReceiverCapable, Radio, ScopeCapable

    assert isinstance(IcomRadio(host=""), Radio), (
        "IcomRadio does not satisfy Radio protocol"
    )
    assert isinstance(IcomRadio(host=""), AudioCapable), (
        "IcomRadio does not satisfy AudioCapable protocol"
    )
    assert isinstance(IcomRadio(host=""), ScopeCapable), (
        "IcomRadio does not satisfy ScopeCapable protocol"
    )
    assert isinstance(IcomRadio(host=""), DualReceiverCapable), (
        "IcomRadio does not satisfy DualReceiverCapable protocol"
    )
