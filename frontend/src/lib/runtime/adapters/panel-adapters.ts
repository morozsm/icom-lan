/**
 * Panel adapters — derive props and handlers for self-wiring panels.
 *
 * Each panel calls its derive function inside $derived() and its
 * handler function once at init. This replaces prop-passing from sidebars.
 *
 * Add new panel adapters here as panels are migrated to self-wiring.
 */

import { runtime } from '../frontend-runtime';
import {
  toAgcProps, toModeProps, toAntennaProps,
  toRfFrontEndProps, toRitXitProps, toScanProps,
  toMeterProps, toCwProps, toDspProps, toTxProps,
  toFilterProps, toBandSelectorProps,
} from '../../../components-v2/wiring/state-adapter';
import {
  makeAgcHandlers, makeModeHandlers, makeAntennaHandlers,
  makeRfFrontEndHandlers, makeRitXitHandlers, makeScanHandlers,
  makeMeterHandlers, makeCwPanelHandlers, makeDspHandlers,
  makeTxHandlers, makeFilterHandlers, makeBandHandlers,
  makePresetHandlers,
} from '../../../components-v2/wiring/command-bus';

// Re-export types for panel imports
export type {
  AgcProps, ModeProps, AntennaProps,
  RfFrontEndProps, RitXitProps, ScanProps,
  MeterProps, CwProps, DspProps, TxProps,
  FilterProps, BandSelectorProps,
} from '../../../components-v2/wiring/state-adapter';

// ── AGC ──
export function deriveAgcProps() {
  return toAgcProps(runtime.state, runtime.caps);
}
const _agcHandlers = makeAgcHandlers();
export function getAgcHandlers() { return _agcHandlers; }

// ── Mode ──
export function deriveModeProps() {
  return toModeProps(runtime.state, runtime.caps);
}
const _modeHandlers = makeModeHandlers();
export function getModeHandlers() { return _modeHandlers; }

// ── Antenna ──
export function deriveAntennaProps() {
  return toAntennaProps(runtime.state, runtime.caps);
}
const _antennaHandlers = makeAntennaHandlers();
export function getAntennaHandlers() { return _antennaHandlers; }

// ── RF Front End ──
export function deriveRfFrontEndProps() {
  return toRfFrontEndProps(runtime.state, runtime.caps);
}
const _rfHandlers = makeRfFrontEndHandlers();
export function getRfFrontEndHandlers() { return _rfHandlers; }

// ── RIT/XIT ──
export function deriveRitXitProps() {
  return toRitXitProps(runtime.state, runtime.caps);
}
const _ritXitHandlers = makeRitXitHandlers();
export function getRitXitHandlers() { return _ritXitHandlers; }

// ── Scan ──
export function deriveScanProps() {
  return toScanProps(runtime.state);
}
const _scanHandlers = makeScanHandlers();
export function getScanHandlers() { return _scanHandlers; }

// ── Meter ──
export function deriveMeterProps() {
  return toMeterProps(runtime.state);
}
const _meterHandlers = makeMeterHandlers();
export function getMeterHandlers() { return _meterHandlers; }

// ── CW ──
export function deriveCwProps() {
  return toCwProps(runtime.state, runtime.caps);
}
const _cwHandlers = makeCwPanelHandlers();
export function getCwHandlers() { return _cwHandlers; }

// ── DSP ──
export function deriveDspProps() {
  return toDspProps(runtime.state, runtime.caps);
}
const _dspHandlers = makeDspHandlers();
export function getDspHandlers() { return _dspHandlers; }

// ── TX ──
export function deriveTxProps() {
  return toTxProps(runtime.state, runtime.caps);
}
const _txHandlers = makeTxHandlers();
export function getTxHandlers() { return _txHandlers; }

// ── Filter ──
export function deriveFilterProps() {
  return toFilterProps(runtime.state, runtime.caps);
}
const _filterHandlers = makeFilterHandlers();
export function getFilterHandlers() { return _filterHandlers; }

// ── Band Selector ──
export function deriveBandSelectorProps() {
  return toBandSelectorProps(runtime.state);
}
const _bandHandlers = makeBandHandlers();
export function getBandHandlers() { return _bandHandlers; }
const _presetHandlers = makePresetHandlers();
export function getPresetHandlers() { return _presetHandlers; }
