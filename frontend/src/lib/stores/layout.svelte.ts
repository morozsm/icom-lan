/**
 * Layout preference store.
 * 'auto' = use spectrum if available, LCD otherwise
 * 'lcd'  = force LCD layout
 * 'spectrum' = force spectrum layout (only if hardware supports it)
 */

const STORAGE_KEY = 'icom-lan-layout';

type LayoutMode = 'auto' | 'lcd' | 'spectrum';

let mode = $state<LayoutMode>(loadMode());

function loadMode(): LayoutMode {
  if (typeof window === 'undefined') return 'auto';
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved === 'lcd' || saved === 'spectrum') return saved;
  return 'auto';
}

export function getLayoutMode(): LayoutMode {
  return mode;
}

export function setLayoutMode(m: LayoutMode): void {
  mode = m;
  if (typeof window !== 'undefined') {
    localStorage.setItem(STORAGE_KEY, m);
  }
}

export function cycleLayoutMode(hasHwSpectrum: boolean): void {
  if (hasHwSpectrum) {
    // auto → lcd → spectrum → auto
    const order: LayoutMode[] = ['auto', 'lcd', 'spectrum'];
    const idx = order.indexOf(mode);
    setLayoutMode(order[(idx + 1) % order.length]);
  } else {
    // No spectrum hardware: always LCD, no toggle needed
    setLayoutMode('lcd');
  }
}

/** Resolve whether to use LCD layout given hardware capabilities. */
export function useLcdLayout(hasHwSpectrum: boolean): boolean {
  if (mode === 'lcd') return true;
  if (mode === 'spectrum') return false;
  // auto: LCD when no hardware spectrum
  return !hasHwSpectrum;
}
