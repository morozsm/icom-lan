import { describe, it, expect, beforeEach, vi } from 'vitest';

describe('ui store', () => {
  let store: typeof import('../ui.svelte');

  beforeEach(async () => {
    vi.resetModules();
    store = await import('../ui.svelte');
  });

  it('starts with desktop layout and dark theme', () => {
    const state = store.getUiState();
    expect(state.layout).toBe('desktop');
    expect(state.theme).toBe('dark');
    expect(state.activePanel).toBe('main');
  });

  it('setLayout switches layout', () => {
    store.setLayout('mobile');
    expect(store.getUiState().layout).toBe('mobile');
    store.setLayout('desktop');
    expect(store.getUiState().layout).toBe('desktop');
  });

  it('setActivePanel switches panel', () => {
    store.setActivePanel('audio');
    expect(store.getUiState().activePanel).toBe('audio');
    store.setActivePanel('settings');
    expect(store.getUiState().activePanel).toBe('settings');
  });

  it('toggleSpectrumFullscreen toggles', () => {
    expect(store.getUiState().spectrumFullscreen).toBe(false);
    store.toggleSpectrumFullscreen();
    expect(store.getUiState().spectrumFullscreen).toBe(true);
    store.toggleSpectrumFullscreen();
    expect(store.getUiState().spectrumFullscreen).toBe(false);
  });

  it('toggleFreqEntry toggles freqEntryOpen', () => {
    expect(store.getUiState().freqEntryOpen).toBe(false);
    store.toggleFreqEntry();
    expect(store.getUiState().freqEntryOpen).toBe(true);
    store.toggleFreqEntry();
    expect(store.getUiState().freqEntryOpen).toBe(false);
  });

  it('setTheme changes theme', () => {
    store.setTheme('light');
    expect(store.getUiState().theme).toBe('light');
    store.setTheme('dark');
    expect(store.getUiState().theme).toBe('dark');
  });
});
