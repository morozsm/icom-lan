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

function activeReceiverParam(): Receiver {
  return getRadioState()?.active === 'SUB' ? 1 : 0;
}

function focusModePanel(vfo: 'MAIN' | 'SUB'): void {
  patchRadioState({ active: vfo });
  cmd('set_vfo', { vfo });

  const modePanel = document.querySelector<HTMLElement>('[data-mode-panel="true"]');
  if (!modePanel) {
    return;
  }

  modePanel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  modePanel.dataset.highlight = 'true';
  window.setTimeout(() => {
    if (modePanel.dataset.highlight === 'true') {
      delete modePanel.dataset.highlight;
    }
  }, 1200);
}

/* ── VFO Handlers ────────────────────────────────────────────── */

export function makeVfoHandlers() {
  return {
    onSwap: () => cmd('vfo_swap'),
    onCopy: () => cmd('vfo_equalize'),
    onEqual: () => cmd('vfo_equalize'),
    onSplitToggle: () => {
      const next = !(getRadioState()?.split ?? false);
      patchRadioState({ split: next });
      cmd('set_split', { on: next });
    },
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
    onMainModeClick: () => focusModePanel('MAIN'),
    onSubModeClick: () => focusModePanel('SUB'),
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

/* ── Mode Handlers ───────────────────────────────────────────── */

export function makeModeHandlers() {
  return {
    onModeChange: (mode: string) => {
      const receiver = activeReceiverParam();
      patchActiveReceiver({ mode }, true);
      cmd('set_mode', { mode, receiver });
    },
    onDataModeChange: (mode: number) => {
      const receiver = activeReceiverParam();
      patchActiveReceiver({ dataMode: mode }, true);
      cmd('set_data_mode', { mode, receiver });
    },
  };
}

/* ── RF Front End Handlers ───────────────────────────────────── */

export function makeRfFrontEndHandlers() {
  return {
    onAttChange: (db: number) => {
      patchActiveReceiver({ att: db });
      cmd('set_attenuator', { db, receiver: activeReceiverParam() });
    },
    onPreChange: (level: number) => {
      patchActiveReceiver({ preamp: level });
      cmd('set_preamp', { level, receiver: activeReceiverParam() });
    },
    onRfGainChange: (level: number) => {
      patchActiveReceiver({ rfGain: level }, true);
      cmd('set_rf_gain', { level, receiver: activeReceiverParam() });
    },
  };
}

/* ── Filter Handlers ─────────────────────────────────────────── */

export function makeFilterHandlers() {
  return {
    onFilterChange: (filter: number) => {
      patchActiveReceiver({ filter }, true);
      cmd('set_filter', { filter, receiver: activeReceiverParam() });
    },
    onFilterWidthChange: (width: number) => {
      patchActiveReceiver({ filterWidth: width }, true);
      cmd('set_filter_width', { width, receiver: activeReceiverParam() });
    },
    onFilterPresetChange: (filter: number, width: number) => {
      const receiver = activeReceiverParam();
      const activeFilter = getActiveReceiver()?.filter ?? 1;
      cmd('set_filter', { filter, receiver });
      cmd('set_filter_width', { width, receiver });
      if (activeFilter !== filter) {
        cmd('set_filter', { filter: activeFilter, receiver });
      } else {
        patchActiveReceiver({ filterWidth: width }, true);
      }
    },
    onFilterDefaults: (defaults: number[]) => {
      const receiver = activeReceiverParam();
      const activeFilter = getActiveReceiver()?.filter ?? 1;
      defaults.forEach((width, index) => {
        const filter = index + 1;
        cmd('set_filter', { filter, receiver });
        cmd('set_filter_width', { width, receiver });
      });
      cmd('set_filter', { filter: activeFilter, receiver });
      if (defaults[activeFilter - 1] !== undefined) {
        patchActiveReceiver({ filterWidth: defaults[activeFilter - 1] }, true);
      }
    },
    onIfShiftChange: (value: number) => {
      const receiver = activeReceiverParam();
      const activeRx = getActiveReceiver();
      const { pbtInner, pbtOuter } = mapIfShiftToPbt(
        value,
        activeRx?.pbtInner ?? 0,
        activeRx?.pbtOuter ?? 0,
      );
      patchActiveReceiver({ pbtInner, pbtOuter }, true);
      cmd('set_pbt_inner', { value: pbtInner, receiver });
      cmd('set_pbt_outer', { value: pbtOuter, receiver });
    },
    onPbtInnerChange: (value: number) => {
      patchActiveReceiver({ pbtInner: value }, true);
      cmd('set_pbt_inner', { value, receiver: activeReceiverParam() });
    },
    onPbtOuterChange: (value: number) => {
      patchActiveReceiver({ pbtOuter: value }, true);
      cmd('set_pbt_outer', { value, receiver: activeReceiverParam() });
    },
    onPbtReset: () => {
      const receiver = activeReceiverParam();
      patchActiveReceiver({ pbtInner: 0, pbtOuter: 0 }, true);
      cmd('set_pbt_inner', { value: 0, receiver });
      cmd('set_pbt_outer', { value: 0, receiver });
    },
  };
}

/* ── AGC Handlers ────────────────────────────────────────────── */

export function makeAgcHandlers() {
  return {
    onAgcModeChange: (mode: number) => {
      patchActiveReceiver({ agc: mode });
      cmd('set_agc', { mode, receiver: activeReceiverParam() });
    },
    onAgcGainChange: (value: number) => {
      cmd('set_agc_time_constant', { value, receiver: activeReceiverParam() });
    },
  };
}

/* ── RIT / XIT Handlers ──────────────────────────────────────── */

export function makeRitXitHandlers() {
  return {
    onRitToggle: () => {
      const next = !(getRadioState()?.ritOn ?? false);
      patchRadioState({ ritOn: next });
      cmd('set_rit_status', { on: next });
    },
    onXitToggle: () => {
      const next = !(getRadioState()?.ritTx ?? false);
      patchRadioState({ ritTx: next });
      cmd('set_rit_tx_status', { on: next });
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
      const receiver = activeReceiverParam();
      patchActiveReceiver({ nr: on });
      cmd('set_nr', { on, receiver });
    },
    onNrLevelChange: (level: number) => {
      const receiver = activeReceiverParam();
      patchActiveReceiver({ nrLevel: level }, true);
      cmd('set_nr_level', { level, receiver });
    },
    onNbToggle: (on: boolean) => {
      const receiver = activeReceiverParam();
      patchActiveReceiver({ nb: on });
      cmd('set_nb', { on, receiver });
    },
    onNbLevelChange: (level: number) => {
      const receiver = activeReceiverParam();
      patchActiveReceiver({ nbLevel: level }, true);
      cmd('set_nb_level', { level, receiver });
    },
    onNotchModeChange: (mode: string) => {
      const receiver = activeReceiverParam();
      if (mode === 'auto') {
        patchActiveReceiver({ autoNotch: true, manualNotch: false });
        cmd('set_auto_notch', { on: true, receiver });
      } else if (mode === 'manual') {
        patchActiveReceiver({ autoNotch: false, manualNotch: true });
        cmd('set_manual_notch', { on: true, receiver });
      } else {
        patchActiveReceiver({ autoNotch: false, manualNotch: false });
        cmd('set_auto_notch', { on: false, receiver });
        cmd('set_manual_notch', { on: false, receiver });
      }
    },
    onNotchFreqChange: (value: number) => {
      cmd('set_notch_filter', { value, receiver: activeReceiverParam() });
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
      const next = (getRadioState()?.tunerStatus ?? 0) > 0 ? 0 : 1;
      patchRadioState({ tunerStatus: next });
      cmd('set_tuner_status', { value: next });
    },
    onAtuTune: () => {
      cmd('set_tuner_status', { value: 2 }); // Start tuning
    },
    onVoxToggle: () => {
      const next = !(getRadioState()?.voxOn ?? false);
      patchRadioState({ voxOn: next });
      cmd('set_vox', { on: next });
    },
    onCompToggle: () => {
      const next = !(getRadioState()?.compressorOn ?? false);
      patchRadioState({ compressorOn: next });
      cmd('set_compressor', { on: next });
    },
    onCompLevelChange: (level: number) => {
      patchRadioState({ compressorLevel: level });
      cmd('set_compressor_level', { level });
    },
    onMonToggle: () => {
      const next = !(getRadioState()?.monitorOn ?? false);
      patchRadioState({ monitorOn: next });
      cmd('set_monitor', { on: next });
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
      cmd('set_af_level', { level, receiver: activeReceiverParam() });
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
