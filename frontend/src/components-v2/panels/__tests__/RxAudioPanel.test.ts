import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, unmount, flushSync } from 'svelte';
import type { ComponentProps } from 'svelte';
import { buildMonitorOptions, formatMonitorStatus } from '../audio-utils';
import RxAudioPanel from '../RxAudioPanel.svelte';

// ---------------------------------------------------------------------------
// Mock capabilities store so hasAudio() is controllable
// ---------------------------------------------------------------------------

const mockHasAudio = vi.fn(() => true);

vi.mock('$lib/stores/capabilities.svelte', () => ({
  hasAudio: () => mockHasAudio(),
  getKeyboardConfig: vi.fn(() => null),
}));

// ---------------------------------------------------------------------------
// buildMonitorOptions
// ---------------------------------------------------------------------------

describe('buildMonitorOptions', () => {
  it('always includes LOCAL as first option', () => {
    const options = buildMonitorOptions(false);
    expect(options[0]).toEqual({ value: 'local', label: 'LOCAL' });
  });

  it('always includes MUTE as last option when hasLive=false', () => {
    const options = buildMonitorOptions(false);
    expect(options[options.length - 1]).toEqual({ value: 'mute', label: 'MUTE' });
  });

  it('always includes MUTE as last option when hasLive=true', () => {
    const options = buildMonitorOptions(true);
    expect(options[options.length - 1]).toEqual({ value: 'mute', label: 'MUTE' });
  });

  it('excludes LIVE when hasLive=false', () => {
    const options = buildMonitorOptions(false);
    expect(options.find((o) => o.value === 'live')).toBeUndefined();
  });

  it('includes LIVE when hasLive=true', () => {
    const options = buildMonitorOptions(true);
    expect(options.find((o) => o.value === 'live')).toEqual({ value: 'live', label: 'LIVE' });
  });

  it('returns 2 options when hasLive=false', () => {
    expect(buildMonitorOptions(false)).toHaveLength(2);
  });

  it('returns 3 options when hasLive=true', () => {
    expect(buildMonitorOptions(true)).toHaveLength(3);
  });

  it('LIVE appears between LOCAL and MUTE when hasLive=true', () => {
    const options = buildMonitorOptions(true);
    expect(options.map((o) => o.value)).toEqual(['local', 'live', 'mute']);
  });

  it('all option values are strings', () => {
    const options = buildMonitorOptions(true);
    options.forEach((o) => expect(typeof o.value).toBe('string'));
  });
});

// ---------------------------------------------------------------------------
// formatMonitorStatus
// ---------------------------------------------------------------------------

describe('formatMonitorStatus', () => {
  it('returns "Radio speaker output" for local', () => {
    expect(formatMonitorStatus('local')).toBe('Radio speaker output');
  });

  it('returns "Browser audio stream" for live', () => {
    expect(formatMonitorStatus('live')).toBe('Browser audio stream');
  });

  it('returns "Audio muted" for mute', () => {
    expect(formatMonitorStatus('mute')).toBe('Audio muted');
  });

  it('returns empty string for unknown mode', () => {
    expect(formatMonitorStatus('unknown')).toBe('');
  });
});

// ---------------------------------------------------------------------------
// RxAudioPanel component
// ---------------------------------------------------------------------------

let components: ReturnType<typeof mount>[] = [];

function mountPanel(props: ComponentProps<typeof RxAudioPanel>) {
  const t = document.createElement('div');
  document.body.appendChild(t);
  const component = mount(RxAudioPanel, { target: t, props });
  flushSync();
  components.push(component);
  return t;
}

beforeEach(() => {
  components = [];
  mockHasAudio.mockReturnValue(true);
});

afterEach(() => {
  components.forEach((c) => unmount(c));
  document.body.innerHTML = '';
});

const baseProps: ComponentProps<typeof RxAudioPanel> = {
  monitorMode: 'local',
  afLevel: 128,
  hasLiveAudio: false,
  onMonitorModeChange: vi.fn(),
  onAfLevelChange: vi.fn(),
};

describe('panel visibility', () => {
  it('renders the panel when hasAudio() returns true', () => {
    mockHasAudio.mockReturnValue(true);
    const t = mountPanel(baseProps);
    expect(t.querySelector('.panel-body')).not.toBeNull();
  });

  it('does not render the panel when hasAudio() returns false', () => {
    mockHasAudio.mockReturnValue(false);
    const t = mountPanel(baseProps);
    expect(t.querySelector('.panel')).toBeNull();
  });
});

describe('panel structure', () => {
  it('renders the AF Level slider', () => {
    const t = mountPanel(baseProps);
    const labels = Array.from(t.querySelectorAll('.vc-label'));
    expect(labels.some((el) => el.textContent === 'AF Level')).toBe(true);
  });

  it('renders the output indicator element', () => {
    const t = mountPanel(baseProps);
    expect(t.querySelector('.output-indicator')).not.toBeNull();
  });

  it('output indicator shows correct status for local mode', () => {
    const t = mountPanel({ ...baseProps, monitorMode: 'local' });
    expect(t.querySelector('.output-indicator')?.textContent?.trim()).toBe('Radio speaker output');
  });

  it('output indicator shows correct status for mute mode', () => {
    const t = mountPanel({ ...baseProps, monitorMode: 'mute' });
    expect(t.querySelector('.output-indicator')?.textContent?.trim()).toBe('Audio muted');
  });

  it('output indicator shows correct status for live mode', () => {
    const t = mountPanel({ ...baseProps, monitorMode: 'live', hasLiveAudio: true });
    expect(t.querySelector('.output-indicator')?.textContent?.trim()).toBe('Browser audio stream');
  });
});

describe('monitor mode options', () => {
  it('does not show LIVE button when hasLiveAudio=false', () => {
    const t = mountPanel({ ...baseProps, hasLiveAudio: false });
    const buttons = Array.from(t.querySelectorAll('button'));
    expect(buttons.some((b) => b.textContent?.trim() === 'LIVE')).toBe(false);
  });

  it('shows LIVE button when hasLiveAudio=true', () => {
    const t = mountPanel({ ...baseProps, hasLiveAudio: true });
    const buttons = Array.from(t.querySelectorAll('button'));
    expect(buttons.some((b) => b.textContent?.trim() === 'LIVE')).toBe(true);
  });
});

describe('callbacks', () => {
  it('calls onAfLevelChange when AF Level slider changes', () => {
    const onAfLevelChange = vi.fn();
    const t = mountPanel({ ...baseProps, onAfLevelChange });
    const slider = t.querySelector<HTMLElement>('[role="slider"]');
    slider!.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true }));
    expect(onAfLevelChange).toHaveBeenCalled();
  });

  it('calls onMonitorModeChange when a mode button is clicked', () => {
    const onMonitorModeChange = vi.fn();
    const t = mountPanel({ ...baseProps, hasLiveAudio: true, onMonitorModeChange });
    const buttons = Array.from(t.querySelectorAll('button'));
    const muteBtn = buttons.find((b) => b.textContent?.trim() === 'MUTE');
    muteBtn!.click();
    expect(onMonitorModeChange).toHaveBeenCalledWith('mute');
  });
});
