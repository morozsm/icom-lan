/**
 * Command Bus — maps v2 UI callbacks → sendCommand() WebSocket calls.
 *
 * Each `makeXxxHandlers()` returns an object of callback functions
 * matching the corresponding v2 component's event props.
 *
 * Optimistic state updates happen inside ws-client.ts `_applyOptimistic()`.
 *
 * Epic #289, Phase 2.
 */

import { sendCommand } from '$lib/transport/ws-client';
import { getActiveReceiver, getRadioState, patchActiveReceiver, patchRadioState } from '$lib/stores/radio.svelte';
import { audioManager } from '$lib/audio/audio-manager';
import { setMuted } from '$lib/stores/audio.svelte';
import { mapIfShiftToPbt } from '../panels/filter-controls';

/* ── Helpers ─────────────────────────────────────────────────── */

/** Get the receiver param (0 = MAIN/active, 1 = SUB). */
type Receiver = 0 | 1;

function cmd(name: string, params: Record<string, unknown> = {}): void {
  sendCommand(name, params);
}

/* ── VFO Handlers ────────────────────────────────────────────── */

export function makeVfoHandlers() {
  return {
    onSwap: () => cmd('vfo_swap'),
    onCopy: () => cmd('vfo_equalize'),
    onEqual: () => cmd('vfo_equalize'),
    onSplitToggle: () => cmd('set_split', { on: true }), // toggle handled by backend
    onTxVfoChange: (v: string) => {
      const state = getRadioState();
      const splitActive = state?.split ?? false;
      const targetVfo = splitActive
        ? v === 'main'
          ? 'SUB'
          : 'MAIN'
        : v === 'main'
          ? 'MAIN'
          : 'SUB';
      patchRadioState({ active: targetVfo });
      cmd('set_vfo', { vfo: targetVfo });
    },
    onMainVfoClick: () => cmd('set_vfo', { vfo: 'MAIN' }),
    onSubVfoClick: () => cmd('set_vfo', { vfo: 'SUB' }),
    onMainModeClick: () => {}, // Mode selection handled by mode popup
    onSubModeClick: () => {},
    onFreqChange: (freq: number, receiver: Receiver = 0) => {
      patchActiveReceiver({ freqHz: freq }, true);
      cmd('set_freq', { freq, receiver });
    },
    onModeChange: (mode: string, receiver: Receiver = 0) => {
      patchActiveReceiver({ mode }, true);
      cmd('set_mode', { mode, receiver });
    },
    onFilterChange: (filter: number, receiver: Receiver = 0) => {
      cmd('set_filter', { filter, receiver });
    },
    onDualWatchToggle: (on: boolean) => cmd('set_dual_watch', { on }),
  };
}

/* ── RF Front End Handlers ───────────────────────────────────── */

export function makeRfFrontEndHandlers() {
  return {
    onAttChange: (db: number) => {
      patchActiveReceiver({ att: db });
      cmd('set_attenuator', { db });
    },
    onPreChange: (level: number) => {
      patchActiveReceiver({ preamp: level });
      cmd('set_preamp', { level });
    },
    onRfGainChange: (level: number) => {
      patchActiveReceiver({ rfGain: level }, true);
      cmd('set_rf_gain', { level });
    },
  };
}

/* ── Filter Handlers ─────────────────────────────────────────── */

export function makeFilterHandlers() {
  return {
    onFilterWidthChange: (width: number) => {
      patchActiveReceiver({ filterWidth: width }, true);
      cmd('set_filter_width', { width });
    },
    onIfShiftChange: (value: number) => {
      const activeRx = getActiveReceiver();
      const { pbtInner, pbtOuter } = mapIfShiftToPbt(
        value,
        activeRx?.pbtInner ?? 0,
        activeRx?.pbtOuter ?? 0,
      );
      patchActiveReceiver({ pbtInner, pbtOuter }, true);
      cmd('set_pbt_inner', { value: pbtInner });
      cmd('set_pbt_outer', { value: pbtOuter });
    },
    onPbtInnerChange: (value: number) => {
      patchActiveReceiver({ pbtInner: value }, true);
      cmd('set_pbt_inner', { value });
    },
    onPbtOuterChange: (value: number) => {
      patchActiveReceiver({ pbtOuter: value }, true);
      cmd('set_pbt_outer', { value });
    },
    onPbtReset: () => {
      patchActiveReceiver({ pbtInner: 0, pbtOuter: 0 }, true);
      cmd('set_pbt_inner', { value: 0 });
      cmd('set_pbt_outer', { value: 0 });
    },
  };
}

/* ── AGC Handlers ────────────────────────────────────────────── */

export function makeAgcHandlers() {
  return {
    onAgcModeChange: (mode: number) => {
      patchActiveReceiver({ agc: mode });
      cmd('set_agc', { mode });
    },
    onAgcGainChange: (value: number) => {
      cmd('set_agc_time_constant', { value });
    },
  };
}

/* ── RIT / XIT Handlers ──────────────────────────────────────── */

export function makeRitXitHandlers() {
  return {
    onRitToggle: () => {
      cmd('set_rit_status', { on: true }); // backend toggles
    },
    onXitToggle: () => {
      cmd('set_rit_tx_status', { on: true }); // backend toggles
    },
    onRitOffsetChange: (hz: number) => {
      patchRadioState({ ritFreq: hz });
      cmd('set_rit_frequency', { freq: hz });
    },
    onXitOffsetChange: (hz: number) => {
      // RIT and ∂TX share the same offset register
      patchRadioState({ ritFreq: hz });
      cmd('set_rit_frequency', { freq: hz });
    },
    onClear: () => {
      patchRadioState({ ritFreq: 0 });
      cmd('set_rit_frequency', { freq: 0 });
    },
  };
}

/* ── DSP Handlers ────────────────────────────────────────────── */

export function makeDspHandlers() {
  return {
    onNrModeChange: (mode: number) => {
      const on = mode > 0;
      patchActiveReceiver({ nr: on });
      cmd('set_nr', { on });
    },
    onNrLevelChange: (level: number) => {
      patchActiveReceiver({ nrLevel: level }, true);
      cmd('set_nr_level', { level });
    },
    onNbToggle: (on: boolean) => {
      patchActiveReceiver({ nb: on });
      cmd('set_nb', { on });
    },
    onNbLevelChange: (level: number) => {
      patchActiveReceiver({ nbLevel: level }, true);
      cmd('set_nb_level', { level });
    },
    onNotchModeChange: (mode: string) => {
      if (mode === 'auto') {
        patchActiveReceiver({ autoNotch: true, manualNotch: false });
        cmd('set_auto_notch', { on: true });
      } else if (mode === 'manual') {
        patchActiveReceiver({ autoNotch: false, manualNotch: true });
        cmd('set_manual_notch', { on: true });
      } else {
        patchActiveReceiver({ autoNotch: false, manualNotch: false });
        cmd('set_auto_notch', { on: false });
        cmd('set_manual_notch', { on: false });
      }
    },
    onNotchFreqChange: (value: number) => {
      cmd('set_notch_filter', { value });
    },
    onCwAutoTuneToggle: (_on: boolean) => {
      // CW auto-tune not yet implemented
    },
    onCwPitchChange: (value: number) => {
      patchRadioState({ cwPitch: value });
      cmd('set_cw_pitch', { value });
    },
  };
}

/* ── TX Handlers ─────────────────────────────────────────────── */

export function makeTxHandlers() {
  return {
    onMicGainChange: (level: number) => {
      patchRadioState({ micGain: level });
      cmd('set_mic_gain', { level });
    },
    onAtuToggle: () => {
      cmd('set_tuner_status', { value: 1 }); // Toggle
    },
    onAtuTune: () => {
      cmd('set_tuner_status', { value: 2 }); // Start tuning
    },
    onVoxToggle: () => {
      cmd('set_vox', { on: true }); // backend toggles
    },
    onCompToggle: () => {
      cmd('set_compressor', { on: true }); // backend toggles
    },
    onCompLevelChange: (level: number) => {
      patchRadioState({ compressorLevel: level });
      cmd('set_compressor_level', { level });
    },
    onMonToggle: () => {
      cmd('set_monitor', { on: true }); // backend toggles
    },
    onMonLevelChange: (level: number) => {
      patchRadioState({ monitorGain: level });
      cmd('set_monitor_gain', { level });
    },
  };
}

/* ── RX Audio Handlers ───────────────────────────────────────── */

export function makeRxAudioHandlers() {
  return {
    onMonitorModeChange: (mode: string) => {
      if (mode === 'live') {
        setMuted(false);
        audioManager.startRx();
        return;
      }

      audioManager.stopRx();
      setMuted(mode === 'mute');
    },
    onAfLevelChange: (level: number) => {
      patchActiveReceiver({ afLevel: level }, true);
      cmd('set_af_level', { level });
    },
  };
}

/* ── Band Selector Handlers ──────────────────────────────────── */

export function makeBandHandlers() {
  return {
    onBandSelect: (_name: string, _freq: number, bsrCode?: number) => {
      if (bsrCode !== undefined) {
        cmd('set_band', { band: bsrCode });
      }
    },
  };
}

/* ── Meter Handlers ──────────────────────────────────────────── */

export function makeMeterHandlers() {
  return {
    onMeterSourceChange: (source: string) => {
      patchRadioState({ meterSource: source as 'S' | 'SWR' | 'POWER' });
    },
  };
}

/* ── System Handlers ─────────────────────────────────────────── */

export function makeSystemHandlers() {
  return {
    onPttOn: () => cmd('ptt_on'),
    onPttOff: () => cmd('ptt_off'),
    onDialLock: (on: boolean) => cmd('set_dial_lock', { on }),
    onPowerOff: () => cmd('set_powerstat', { on: false }),
  };
}
