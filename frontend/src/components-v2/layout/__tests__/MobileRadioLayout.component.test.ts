import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, unmount, flushSync } from 'svelte';

// -- Child component stubs --
vi.mock('../../../components/spectrum/SpectrumPanel.svelte', async () => {
  const s = await import('./SpectrumPanelStub.svelte');
  return { default: s.default };
});
vi.mock('../panels/lcd/AmberLcdDisplay.svelte', () => ({ default: function S() { return {}; } }));
vi.mock('../display/FrequencyDisplay.svelte', () => ({ default: function S() { return {}; } }));
vi.mock('../meters/LinearSMeter.svelte', () => ({ default: function S() { return {}; } }));
vi.mock('../controls/CollapsiblePanel.svelte', () => ({ default: function S() { return {}; } }));
vi.mock('../controls/BottomSheet.svelte', () => ({ default: function S() { return {}; } }));
vi.mock('../controls/BandSelector.svelte', () => ({ default: function S() { return {}; } }));
vi.mock('../panels/FilterPanel.svelte', () => ({ default: function S() { return {}; } }));
vi.mock('../panels/RxAudioPanel.svelte', () => ({ default: function S() { return {}; } }));
vi.mock('../panels/TxPanel.svelte', () => ({ default: function S() { return {}; } }));
vi.mock('../panels/DspPanel.svelte', () => ({ default: function S() { return {}; } }));
vi.mock('../panels/AgcPanel.svelte', () => ({ default: function S() { return {}; } }));
vi.mock('../panels/RfFrontEnd.svelte', () => ({ default: function S() { return {}; } }));
vi.mock('../panels/RitXitPanel.svelte', () => ({ default: function S() { return {}; } }));
vi.mock('../panels/AntennaPanel.svelte', () => ({ default: function S() { return {}; } }));
vi.mock('../panels/ScanPanel.svelte', () => ({ default: function S() { return {}; } }));
vi.mock('../panels/CwPanel.svelte', () => ({ default: function S() { return {}; } }));
vi.mock('../panels/DockMeterPanel.svelte', () => ({ default: function S() { return {}; } }));
vi.mock('./KeyboardHandler.svelte', () => ({ default: function S() { return {}; } }));
vi.mock('$lib/Button', () => ({ HardwareButton: function S() { return {}; } }));
vi.mock('lucide-svelte', () => {
  const S = function () { return {}; };
  return { Settings: S, ChevronLeft: S, ChevronRight: S, ChevronsLeft: S, ChevronsRight: S, Mic: S, MicOff: S, Sliders: S, Radio: S };
});
vi.mock('../controls/value-control', () => ({
  ValueControl: function S() { return {}; },
  rawToPercentDisplay: vi.fn((v: number) => `${Math.round(v / 255 * 100)}%`),
}));
vi.mock('./vfo-layout-tokens', () => ({
  resolveVfoLayoutProfile: vi.fn(() => 'baseline'),
  vfoLayoutStyleVars: vi.fn(() => ''),
}));

// -- Store mocks --
vi.mock('$lib/stores/radio.svelte', () => ({ radio: { current: null } }));
vi.mock('$lib/stores/connection.svelte', () => ({
  getConnectionStatus: vi.fn(() => ({ connected: false })),
  getRadioPowerOn: vi.fn(() => null),
}));
vi.mock('$lib/stores/audio.svelte', () => ({
  getAudioState: vi.fn(() => ({ volume: 50, muted: false, rxEnabled: false, txEnabled: false, micEnabled: false, bridgeRunning: false })),
}));
vi.mock('$lib/audio/audio-manager', () => ({
  audioManager: { start: vi.fn(), stop: vi.fn(), setVolume: vi.fn(), toggleMute: vi.fn() },
}));
vi.mock('$lib/utils/tx-permit', () => ({ getTxPermit: vi.fn(() => 'allowed') }));
vi.mock('$lib/stores/tuning.svelte', () => ({ applyModeDefault: vi.fn() }));
vi.mock('$lib/stores/capabilities.svelte', () => ({
  hasTx: vi.fn(() => true), hasDualReceiver: vi.fn(() => false), hasAnyScope: vi.fn(() => false),
  hasSpectrum: vi.fn(() => false), getCapabilities: vi.fn(() => ({ freqRanges: [], modes: [], filters: [] })),
  getKeyboardConfig: vi.fn(() => null), setCapabilities: vi.fn(), hasCapability: vi.fn(() => false),
  vfoLabel: vi.fn((s: string) => s === 'A' ? 'MAIN' : 'SUB'), isAudioFftScope: vi.fn(() => false),
  hasAudioFft: vi.fn(() => false), getScopeSource: vi.fn(() => null), hasAudio: vi.fn(() => false),
  getSmeterCalibration: vi.fn(() => null), getSmeterRedline: vi.fn(() => null),
  getMeterCalibration: vi.fn(() => null), getMeterRedline: vi.fn(() => null),
  getControlRange: vi.fn(() => ({ min: 0, max: 255 })),
  getSupportedModes: vi.fn(() => ['USB', 'LSB', 'CW', 'AM', 'FM']),
  getSupportedFilters: vi.fn(() => ['FIL1', 'FIL2', 'FIL3']),
  getAttValues: vi.fn(() => [0, 10, 20]), getAttLabels: vi.fn(() => ({ 0: '0dB', 10: '10dB', 20: '20dB' })),
  getPreValues: vi.fn(() => [0, 1, 2]), getPreLabels: vi.fn(() => ({ 0: 'OFF', 1: 'PRE1', 2: 'PRE2' })),
  getAgcModes: vi.fn(() => [0, 1, 2, 3]),
  getAgcLabels: vi.fn(() => ({ 0: 'OFF', 1: 'FAST', 2: 'MID', 3: 'SLOW' })),
  getVfoScheme: vi.fn(() => 'ab'), getAntennaCount: vi.fn(() => 1),
}));

// -- Wiring mocks --
vi.mock('../wiring/command-bus', () => {
  const n = vi.fn();
  return {
    makeVfoHandlers: () => ({ onMainFreqChange: n, onSubFreqChange: n, onVfoSwap: n, onVfoEqual: n, onReceiverSelect: n }),
    makeMeterHandlers: () => ({ onMeterSourceChange: n }), makeKeyboardHandlers: () => ({ dispatch: n }),
    makeModeHandlers: () => ({ onModeChange: n, onDataModeChange: n }),
    makeFilterHandlers: () => ({ onFilterChange: n, onFilterWidthChange: n }),
    makeBandHandlers: () => ({ onBandSelect: n }), makePresetHandlers: () => ({ onPresetSelect: n }),
    makeRxAudioHandlers: () => ({ onAfLevelChange: n, onMonitorModeChange: n }),
    makeTxHandlers: () => ({ onPttChange: n, onPowerChange: n, onTuneStart: n, onAtuToggle: n, onRfPowerChange: n, onMicGainChange: n, onAtuTune: n, onVoxToggle: n, onCompToggle: n, onCompLevelChange: n, onMonToggle: n, onMonLevelChange: n, onDriveGainChange: n }),
    makeRfFrontEndHandlers: () => ({ onAttChange: n, onPreChange: n, onRfGainChange: n }),
    makeAgcHandlers: () => ({ onAgcModeChange: n }),
    makeRitXitHandlers: () => ({ onRitToggle: n, onRitClear: n, onXitToggle: n, onXitClear: n }),
    makeDspHandlers: () => ({ onNrToggle: n, onNbToggle: n, onNotchToggle: n }),
    makeCwPanelHandlers: () => ({ onSpeedChange: n }),
    makeAntennaHandlers: () => ({ onAntennaSelect: n }),
    makeScanHandlers: () => ({ onScanStart: n, onScanStop: n, onDfSpanChange: n, onResumeChange: n }),
    makeSystemHandlers: () => ({ onPowerOff: n, onPttOn: n, onPttOff: n }),
  };
});
vi.mock('../wiring/state-adapter', () => {
  const vfo = { freq: 14074000, mode: 'USB', filter: 'FIL1', sValue: 0, badges: {}, receiver: 'main', isActive: true };
  return {
    toVfoProps: vi.fn(() => vfo), toVfoOpsProps: vi.fn(() => ({ split: false, dualWatch: false })),
    toMeterProps: vi.fn(() => ({ signal: 0, rfPower: 0, swr: 0, alc: 0, txActive: false, meterSource: 'S' })),
    toModeProps: vi.fn(() => ({ currentMode: 'USB', modes: ['USB', 'LSB', 'CW', 'AM', 'FM'], dataMode: 0 })),
    toFilterProps: vi.fn(() => ({ currentFilter: 1, filterLabels: ['FIL1', 'FIL2', 'FIL3'] })),
    toBandSelectorProps: vi.fn(() => ({ currentFreq: 14074000 })),
    toRxAudioProps: vi.fn(() => ({ afLevel: 128, monitorMode: 'local' })),
    toTxProps: vi.fn(() => ({ rfPower: 128, txActive: false, atuActive: false, atuTuning: false })),
    toRfFrontEndProps: vi.fn(() => ({ att: 0, preamp: 0, rfGain: 100 })),
    toAgcProps: vi.fn(() => ({ agcMode: 3 })), toRitXitProps: vi.fn(() => ({ ritOn: false, ritOffset: 0, xitOn: false, xitOffset: 0 })),
    toDspProps: vi.fn(() => ({ nr: false, nb: false, notch: false })), toCwProps: vi.fn(() => ({ speed: 20 })),
    toAntennaProps: vi.fn(() => ({ selected: 1 })),
    toScanProps: vi.fn(() => ({ scanning: false, scanType: 'off', scanResumeMode: 'time' })),
  };
});

import MobileRadioLayout from '../MobileRadioLayout.svelte';
import { hasTx } from '$lib/stores/capabilities.svelte';

let components: ReturnType<typeof mount>[] = [];

function mountMobile(): HTMLElement {
  const t = document.createElement('div');
  document.body.appendChild(t);
  components.push(mount(MobileRadioLayout, { target: t }));
  flushSync();
  return t;
}

beforeEach(() => {
  components = [];
  Object.defineProperty(window, 'innerWidth', { writable: true, configurable: true, value: 390 });
  Object.defineProperty(window, 'innerHeight', { writable: true, configurable: true, value: 844 });
  vi.mocked(hasTx).mockReturnValue(true);
});

afterEach(() => {
  components.forEach((c) => unmount(c));
  document.body.innerHTML = '';
});

describe('MobileRadioLayout structure', () => {
  it('mounts without errors', () => {
    expect(mountMobile().children.length).toBeGreaterThan(0);
  });

  it('renders .m-layout root in portrait mode', () => {
    expect(mountMobile().querySelector('.m-layout')).not.toBeNull();
  });

  it('renders VFO header bar', () => {
    expect(mountMobile().querySelector('.m-vfo-bar')).not.toBeNull();
  });

  it('renders VFO frequency row', () => {
    expect(mountMobile().querySelector('.m-vfo-row')).not.toBeNull();
  });

  it('renders S-meter bar', () => {
    expect(mountMobile().querySelector('.m-smeter-bar')).not.toBeNull();
  });

  it('renders scrollable main content area', () => {
    expect(mountMobile().querySelector('.m-content')).not.toBeNull();
  });

  it('renders tuning strip', () => {
    expect(mountMobile().querySelector('.m-tuning-strip')).not.toBeNull();
  });

  it('renders chip-bar nav inside m-content', () => {
    expect(mountMobile().querySelector('.m-content .m-chip-bar')).not.toBeNull();
  });

  it('renders active chip content area', () => {
    expect(mountMobile().querySelector('.m-content .m-chip-content')).not.toBeNull();
  });

  it('renders TX indicator', () => {
    expect(mountMobile().querySelector('.m-tx-indicator')).not.toBeNull();
  });

  it('renders settings button', () => {
    expect(mountMobile().querySelector('.m-settings-btn')).not.toBeNull();
  });
});

describe('MobileRadioLayout TX gating', () => {
  it('exposes TX chip when hasTx is true', () => {
    vi.mocked(hasTx).mockReturnValue(true);
    const chips = Array.from(mountMobile().querySelectorAll('.m-chip')) as HTMLButtonElement[];
    expect(chips.some((c) => c.textContent?.trim() === 'TX')).toBe(true);
  });

  it('hides TX chip when hasTx is false', () => {
    vi.mocked(hasTx).mockReturnValue(false);
    const chips = Array.from(mountMobile().querySelectorAll('.m-chip')) as HTMLButtonElement[];
    expect(chips.some((c) => c.textContent?.trim() === 'TX')).toBe(false);
  });

  it('renders PTT button when TX chip selected', () => {
    vi.mocked(hasTx).mockReturnValue(true);
    const root = mountMobile();
    const txChip = Array.from(root.querySelectorAll('.m-chip')).find(
      (c) => c.textContent?.trim() === 'TX',
    ) as HTMLButtonElement | undefined;
    txChip?.click();
    flushSync();
    expect(root.querySelector('.m-ptt-btn')).not.toBeNull();
  });
});

describe('MobileRadioLayout unmount', () => {
  it('unmounts cleanly without errors', () => {
    const t = mountMobile();
    expect(t.querySelector('.m-layout')).not.toBeNull();
    expect(() => unmount(components.pop()!)).not.toThrow();
  });
});
