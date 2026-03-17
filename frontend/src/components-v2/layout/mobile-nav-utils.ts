export type TabId = 'vfo' | 'spectrum' | 'controls' | 'tx' | 'meters';

export interface TabDef {
  id: TabId;
  label: string;
  icon: string;
}

export const TABS: readonly TabDef[] = [
  { id: 'vfo',      label: 'VFO',      icon: '📻' },
  { id: 'spectrum', label: 'Spectrum', icon: '📊' },
  { id: 'controls', label: 'Controls', icon: '🎛' },
  { id: 'tx',       label: 'TX',       icon: '📡' },
  { id: 'meters',   label: 'Meters',   icon: '📈' },
] as const;

export const DEFAULT_TAB: TabId = 'spectrum';

export interface NavCapabilities {
  hasTx?: boolean;
}

export function isTabVisible(tab: TabDef, capabilities: NavCapabilities): boolean {
  if (tab.id === 'tx') {
    return capabilities.hasTx === true;
  }
  return true;
}

export function getVisibleTabs(capabilities: NavCapabilities): TabDef[] {
  return TABS.filter((tab) => isTabVisible(tab, capabilities));
}
