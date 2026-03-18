import { describe, it, expect, beforeEach, vi } from 'vitest';
import type { ServerState } from '../../types/state';

function makeState(overrides: Partial<ServerState> = {}): ServerState {
  return {
    revision: 1,
    updatedAt: '2026-03-07T00:00:00Z',
    active: 'MAIN',
    ptt: false,
    split: false,
    dualWatch: false,
    tunerStatus: 0,
    main: {
      freqHz: 14074000,
      mode: 'USB',
      filter: 1,
      dataMode: false,
      sMeter: 50,
      att: 0,
      preamp: 1,
      nb: false,
      nr: false,
      afLevel: 100,
      rfGain: 255,
      squelch: 0,
      digisel: false,
      ipplus: false,
      sMeterSqlOpen: true,
      agc: 3,
      audioPeakFilter: 0,
      autoNotch: false,
      manualNotch: false,
      twinPeakFilter: false,
      filterShape: 0,
      agcTimeConstant: 13,
      apfTypeLevel: 0,
      nrLevel: 0,
      pbtInner: 0,
      pbtOuter: 0,
      nbLevel: 0,
      digiselShift: 0,
      afMute: false,
    },
    sub: {
      freqHz: 7100000,
      mode: 'LSB',
      filter: 2,
      dataMode: false,
      sMeter: 20,
      att: 0,
      preamp: 0,
      nb: false,
      nr: false,
      afLevel: 80,
      rfGain: 255,
      squelch: 0,
      digisel: false,
      ipplus: false,
      sMeterSqlOpen: false,
      agc: 0,
      audioPeakFilter: 0,
      autoNotch: false,
      manualNotch: false,
      twinPeakFilter: false,
      filterShape: 0,
      agcTimeConstant: 13,
      apfTypeLevel: 0,
      nrLevel: 0,
      pbtInner: 0,
      pbtOuter: 0,
      nbLevel: 0,
      digiselShift: 0,
      afMute: false,
    },
    connection: { rigConnected: true, radioReady: true, controlConnected: true },
    powerLevel: 255,
    scanning: false,
    tuningStep: 0,
    overflow: false,
    txFreqMonitor: false,
    ritFreq: 0,
    ritOn: false,
    ritTx: false,
    compMeter: 0,
    vdMeter: 0,
    idMeter: 0,
    cwPitch: 0,
    micGain: 0,
    keySpeed: 0,
    notchFilter: 0,
    mainSubTracking: false,
    compressorOn: false,
    compressorLevel: 0,
    monitorOn: false,
    breakInDelay: 0,
    breakIn: 0,
    dialLock: false,
    driveGain: 0,
    monitorGain: 0,
    voxOn: false,
    voxGain: 0,
    antiVoxGain: 0,
    ssbTxBandwidth: 0,
    refAdjust: 0,
    dashRatio: 0,
    nbDepth: 0,
    nbWidth: 0,
    scopeControls: {
      receiver: 0,
      dual: false,
      mode: 0,
      span: 0,
      edge: 0,
      hold: false,
      refDb: 0,
      speed: 0,
      duringTx: false,
      centerType: 0,
      vbwNarrow: false,
      rbw: 0,
      fixedEdge: { rangeIndex: 0, edge: 0, startHz: 0, endHz: 0 },
    },
    ...overrides,
  };
}

describe('radio store', () => {
  let store: typeof import('../radio.svelte');

  beforeEach(async () => {
    vi.resetModules();
    store = await import('../radio.svelte');
  });

  it('starts with null state', () => {
    expect(store.getRadioState()).toBeNull();
  });

  it('sets state and reads it back', () => {
    const s = makeState({ revision: 1 });
    store.setRadioState(s);
    expect(store.getRadioState()).toStrictEqual(s);
  });

  it('accepts initial revision 0 state when store is empty', () => {
    const s = makeState({ revision: 0 });
    store.setRadioState(s);
    expect(store.getRadioState()?.revision).toBe(0);
  });

  it('ignores stale states (lower revision)', () => {
    store.setRadioState(makeState({ revision: 5 }));
    const stale = makeState({ revision: 3 });
    store.setRadioState(stale);
    expect(store.getRadioState()?.revision).toBe(5);
  });

  it('accepts higher revision update', () => {
    store.setRadioState(makeState({ revision: 3 }));
    store.setRadioState(makeState({ revision: 7, ptt: true }));
    expect(store.getRadioState()?.revision).toBe(7);
    expect(store.getRadioState()?.ptt).toBe(true);
  });

  it('ignores equal revision (not strictly greater)', () => {
    store.setRadioState(makeState({ revision: 5, ptt: false }));
    store.setRadioState(makeState({ revision: 5, ptt: true }));
    expect(store.getRadioState()?.ptt).toBe(false);
  });

  it('getFrequency returns active receiver frequency (MAIN)', () => {
    store.setRadioState(makeState({ active: 'MAIN' }));
    expect(store.getFrequency()).toBe(14074000);
  });

  it('getFrequency returns sub receiver frequency when active is SUB', () => {
    store.setRadioState(makeState({ active: 'SUB' }));
    expect(store.getFrequency()).toBe(7100000);
  });

  it('getMode returns active receiver mode', () => {
    store.setRadioState(makeState({ active: 'MAIN' }));
    expect(store.getMode()).toBe('USB');
  });

  it('getIsTransmitting reflects ptt state', () => {
    store.setRadioState(makeState({ ptt: true }));
    expect(store.getIsTransmitting()).toBe(true);
  });

  it('getLastRevision tracks the latest revision', () => {
    store.setRadioState(makeState({ revision: 10 }));
    expect(store.getLastRevision()).toBe(10);
  });

  it('getMainReceiver and getSubReceiver return correct receivers', () => {
    store.setRadioState(makeState());
    expect(store.getMainReceiver()?.freqHz).toBe(14074000);
    expect(store.getSubReceiver()?.freqHz).toBe(7100000);
  });

  it('detects server restart: accepts state when revision resets from high to near zero', () => {
    store.setRadioState(makeState({ revision: 100 }));
    store.setRadioState(makeState({ revision: 1, ptt: true }));
    expect(store.getRadioState()?.revision).toBe(1);
    expect(store.getRadioState()?.ptt).toBe(true);
  });

  it('does not treat small revision drop as server restart (lastRevision <= 10)', () => {
    store.setRadioState(makeState({ revision: 5 }));
    store.setRadioState(makeState({ revision: 1, ptt: true }));
    // lastRevision=5 which is NOT > 10, so treated as stale
    expect(store.getRadioState()?.revision).toBe(5);
    expect(store.getRadioState()?.ptt).toBe(false);
  });
});
