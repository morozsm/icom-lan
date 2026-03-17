const STORAGE_KEY = 'icom-lan-ui-version';

type UiVersion = 'v1' | 'v2';

let uiVersion = $state<UiVersion>('v1');

export function getUiVersion(): UiVersion {
  return uiVersion;
}

export function setUiVersion(v: UiVersion): void {
  uiVersion = v;
  if (typeof localStorage !== 'undefined') {
    localStorage.setItem(STORAGE_KEY, v);
  }
}

export function toggleUiVersion(): void {
  setUiVersion(uiVersion === 'v1' ? 'v2' : 'v1');
}

export function initUiVersion(): void {
  // URL param takes priority
  if (typeof window !== 'undefined') {
    const params = new URLSearchParams(window.location.search);
    const param = params.get('ui');
    if (param === 'v1' || param === 'v2') {
      setUiVersion(param);
      return;
    }
  }

  // Then localStorage
  if (typeof localStorage !== 'undefined') {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === 'v1' || stored === 'v2') {
      uiVersion = stored;
      return;
    }
  }

  // Default
  uiVersion = 'v1';
}
