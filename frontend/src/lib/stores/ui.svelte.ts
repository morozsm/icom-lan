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

export function getUiState() {
  return uiState;
}

export function setActivePanel(panel: UiState['activePanel']) {
  uiState.activePanel = panel;
}

export function setLayout(layout: UiState['layout']) {
  uiState.layout = layout;
}

export function toggleSpectrumFullscreen() {
  uiState.spectrumFullscreen = !uiState.spectrumFullscreen;
}
