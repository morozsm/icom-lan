/**
 * State Adapter — maps backend ServerState + Capabilities → v2 component props.
 *
 * Pure functions, no side effects. Each function extracts exactly what
 * one v2 panel/molecule needs from the shared radio store.
 *
 * Epic #289, Phase 1.
 */

import type { ServerState, ReceiverState } from '$lib/types/state';
import type { Capabilities } from '$lib/types/capabilities';
import type { VfoStateProps } from '../layout/layout-utils';

/* ── Helpers ─────────────────────────────────────────────────── */

/** Get the active receiver state (MAIN or SUB). */
function activeRx(state: ServerState): ReceiverState {
  return state.active === 'SUB' ? state.sub : state.main;
}

/** Check capability presence (safe for null caps). */
function hasCap(caps: Capabilities | null, name: string): boolean {
  return caps?.capabilities?.includes(name) ?? false;
}

/* ── VFO ─────────────────────────────────────────────────────── */

export function toVfoProps(
  state: ServerState | null,
  receiver: 'main' | 'sub',
): VfoStateProps {
  if (!state) {
    return {
      receiver,
      freq: 14074000,
      mode: 'USB',
      filter: 'FIL1',
      sValue: 0,
      isActive: receiver === 'main',
      badges: {},
    };
  }

  const rx = state[receiver];
  const isActive = (state.active === 'SUB') === (receiver === 'sub');

  const badges: Record<string, boolean | string> = {};
  if (rx.nb) badges['NB'] = true;
  if (rx.nr) badges['NR'] = true;
  if (rx.digisel) badges['DIGI-SEL'] = true;
  if (rx.ipplus) badges['IP+'] = true;
  if (rx.autoNotch) badges['ANF'] = true;
  if (rx.manualNotch) badges['NOTCH'] = true;
  if (rx.dataMode) badges['DATA'] = true;
  if (state.split) badges['SPLIT'] = true;

  const filters = ['FIL1', 'FIL2', 'FIL3'];
  const filterLabel = filters[rx.filter - 1] ?? `FIL${rx.filter}`;

  return {
    receiver,
    freq: rx.freqHz,
    mode: rx.mode,
    filter: filterLabel,
    sValue: rx.sMeter,
    isActive,
    badges,
    rit: state.ritOn
      ? { active: true, offset: state.ritFreq ?? 0 }
      : undefined,
  };
}

/* ── RF Front End ────────────────────────────────────────────── */

export interface RfFrontEndProps {
  rfGain: number;
  att: number;
  pre: number;
  attValues: number[];
  preValues: number[];
}

export function toRfFrontEndProps(
  state: ServerState | null,
  caps: Capabilities | null,
): RfFrontEndProps {
  const rx = state ? activeRx(state) : null;
  return {
    rfGain: rx?.rfGain ?? 255,
    att: rx?.att ?? 0,
    pre: rx?.preamp ?? 0,
    attValues: caps?.attValues ?? [0, 6, 12, 18],
    preValues: caps?.preValues ?? [0, 1, 2],
  };
}

/* ── Filter ──────────────────────────────────────────────────── */

export interface FilterProps {
  filterWidth: number;
  ifShift: number;
  hasPbt: boolean;
  pbtInner: number;
  pbtOuter: number;
}

export function toFilterProps(
  state: ServerState | null,
  caps: Capabilities | null,
): FilterProps {
  const rx = state ? activeRx(state) : null;
  return {
    filterWidth: 2400, // TODO: add to ServerState when filter_width polling is implemented
    ifShift: 0,        // TODO: mapped from PBT offsets
    hasPbt: hasCap(caps, 'pbt'),
    pbtInner: rx?.pbtInner ?? 0,
    pbtOuter: rx?.pbtOuter ?? 0,
  };
}

/* ── AGC ─────────────────────────────────────────────────────── */

export interface AgcProps {
  agcMode: number;
  agcGain: number;
  agcModes: number[];
  agcLabels: Record<string, string>;
}

export function toAgcProps(
  state: ServerState | null,
  caps: Capabilities | null,
): AgcProps {
  const rx = state ? activeRx(state) : null;
  return {
    agcMode: rx?.agc ?? 2,
    agcGain: rx?.agcTimeConstant ?? 128,
    agcModes: caps?.agcModes ?? [1, 2, 3],
    agcLabels: caps?.agcLabels ?? { '1': 'FAST', '2': 'MID', '3': 'SLOW' },
  };
}

/* ── RIT / XIT ───────────────────────────────────────────────── */

export interface RitXitProps {
  ritActive: boolean;
  ritOffset: number;
  xitActive: boolean;
  xitOffset: number;
  hasRit: boolean;
  hasXit: boolean;
}

export function toRitXitProps(
  state: ServerState | null,
  caps: Capabilities | null,
): RitXitProps {
  return {
    ritActive: state?.ritOn ?? false,
    ritOffset: state?.ritFreq ?? 0,
    xitActive: state?.ritTx ?? false,
    xitOffset: state?.ritFreq ?? 0, // RIT and ∂TX share the frequency offset
    hasRit: hasCap(caps, 'rit'),
    hasXit: hasCap(caps, 'xit'),
  };
}

/* ── DSP Panel ───────────────────────────────────────────────── */

export interface DspProps {
  nrMode: number;
  nrLevel: number;
  nbActive: boolean;
  nbLevel: number;
  notchMode: string;
  notchFreq: number;
  cwAutoTune: boolean;
  cwPitch: number;
  currentMode: string;
}

export function toDspProps(
  state: ServerState | null,
  _caps: Capabilities | null,
): DspProps {
  const rx = state ? activeRx(state) : null;

  // Notch mode: off / auto / manual
  let notchMode: string = 'off';
  if (rx?.autoNotch) notchMode = 'auto';
  else if (rx?.manualNotch) notchMode = 'manual';

  return {
    nrMode: rx?.nr ? 1 : 0,
    nrLevel: rx?.nrLevel ?? 0,
    nbActive: rx?.nb ?? false,
    nbLevel: rx?.nbLevel ?? 0,
    notchMode,
    notchFreq: state?.notchFilter ?? 0,
    cwAutoTune: false, // Not currently in ServerState
    cwPitch: state?.cwPitch ?? 600,
    currentMode: rx?.mode ?? 'USB',
  };
}

/* ── TX Panel ────────────────────────────────────────────────── */

export interface TxProps {
  txActive: boolean;
  micGain: number;
  atuActive: boolean;
  atuTuning: boolean;
  voxActive: boolean;
  compActive: boolean;
  compLevel: number;
  monActive: boolean;
  monLevel: number;
}

export function toTxProps(
  state: ServerState | null,
  _caps: Capabilities | null,
): TxProps {
  return {
    txActive: state?.ptt ?? false,
    micGain: state?.micGain ?? 128,
    atuActive: (state?.tunerStatus ?? 0) > 0,
    atuTuning: (state?.tunerStatus ?? 0) === 2,
    voxActive: state?.voxOn ?? false,
    compActive: state?.compressorOn ?? false,
    compLevel: state?.compressorLevel ?? 0,
    monActive: state?.monitorOn ?? false,
    monLevel: state?.monitorGain ?? 128,
  };
}

/* ── Meter Panel ─────────────────────────────────────────────── */

export interface MeterProps {
  sValue: number;
  rfPower: number;
  swr: number;
  alc: number;
  comp: number;
  vd: number;
  id: number;
  txActive: boolean;
  meterSource: string;
}

export function toMeterProps(state: ServerState | null): MeterProps {
  const mainRx = state?.main;
  return {
    sValue: mainRx?.sMeter ?? 0,
    rfPower: 0,   // Power meter comes from 0x15 0x11, stored separately
    swr: 0,       // SWR from 0x15 0x12
    alc: 0,       // ALC from 0x15 0x13
    comp: state?.compMeter ?? 0,
    vd: state?.vdMeter ?? 0,
    id: state?.idMeter ?? 0,
    txActive: state?.ptt ?? false,
    meterSource: 'S',
  };
}

/* ── RX Audio Panel ──────────────────────────────────────────── */

export interface RxAudioProps {
  monitorMode: string;
  afLevel: number;
  hasLiveAudio: boolean;
}

export function toRxAudioProps(
  state: ServerState | null,
  caps: Capabilities | null,
): RxAudioProps {
  const rx = state ? activeRx(state) : null;
  return {
    monitorMode: 'local',
    afLevel: rx?.afLevel ?? 128,
    hasLiveAudio: hasCap(caps, 'audio'),
  };
}

/* ── Band Selector ───────────────────────────────────────────── */

export interface BandSelectorProps {
  currentFreq: number;
}

export function toBandSelectorProps(
  state: ServerState | null,
): BandSelectorProps {
  return {
    currentFreq: state?.main?.freqHz ?? 14074000,
  };
}

/* ── VFO Ops (split / swap / etc.) ───────────────────────────── */

export interface VfoOpsProps {
  splitActive: boolean;
  txVfo: 'main' | 'sub';
  dualWatch: boolean;
  mainSubTracking: boolean;
}

export function toVfoOpsProps(
  state: ServerState | null,
  caps: Capabilities | null,
): VfoOpsProps {
  return {
    splitActive: state?.split ?? false,
    txVfo: 'main', // Currently not tracked in ServerState
    dualWatch: state?.dualWatch ?? false,
    mainSubTracking: state?.mainSubTracking ?? false,
  };
}
