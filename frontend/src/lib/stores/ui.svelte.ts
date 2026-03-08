import type { UiState } from '../types/state';

// $uiState — client-only UI state (layout, panels, gestures)
let uiState = $state<UiState>({
  layout: typeof window !== 'undefined' && window.innerWidth < 768 ? 'mobile' : 'desktop',
  activePanel: 'main',
  spectrumFullscreen: false,
  freqEntryOpen: false,
  theme: 'dark',
  gestures: {
    tuning: false,
    draggingSpectrum: false,
  },
});

export function getUiState(): UiState {
  return uiState;
}

export function setLayout(layout: UiState['layout']): void {
  uiState.layout = layout;
}

export function setActivePanel(panel: UiState['activePanel']): void {
  uiState.activePanel = panel;
}

export function toggleSpectrumFullscreen(): void {
  uiState.spectrumFullscreen = !uiState.spectrumFullscreen;
}

export function toggleFreqEntry(): void {
  uiState.freqEntryOpen = !uiState.freqEntryOpen;
}

export function setTheme(theme: UiState['theme']): void {
  uiState.theme = theme;
}
