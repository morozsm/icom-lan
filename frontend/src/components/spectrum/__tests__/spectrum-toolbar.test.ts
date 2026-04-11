/**
 * Tests for SpectrumToolbar logic: layer visibility toggling,
 * scope control applicability, label lookups, and clamping helpers.
 *
 * These tests extract the pure logic from SpectrumToolbar.svelte
 * and verify it independently of DOM rendering.
 */
import { describe, it, expect } from 'vitest';
import {
  SPAN_LABELS, SPEED_LABELS, MODE_BUTTONS,
  toggleLayer, isLayerVisible,
  isSpanApplicable, isEdgeApplicable,
  clampSpan, clampSpeed, clampBrt, clampRef,
} from '../spectrum-toolbar-logic';

function nextReceiver(current: number): number {
  return current === 1 ? 0 : 1;
}

// ── Tests ──

describe('SpectrumToolbar constants', () => {
  it('SPAN_LABELS covers indices 0–7', () => {
    for (let i = 0; i <= 7; i++) {
      expect(SPAN_LABELS[i]).toBeDefined();
    }
    expect(SPAN_LABELS[8]).toBeUndefined();
  });

  it('SPEED_LABELS covers indices 0–2', () => {
    expect(SPEED_LABELS[0]).toBe('FST');
    expect(SPEED_LABELS[1]).toBe('MID');
    expect(SPEED_LABELS[2]).toBe('SLO');
  });

  it('MODE_BUTTONS has 4 entries with correct labels', () => {
    expect(MODE_BUTTONS).toHaveLength(4);
    const labels = MODE_BUTTONS.map(([, l]) => l);
    expect(labels).toEqual(['CTR', 'FIX', 'S-C', 'S-F']);
  });

  it('MODE_BUTTONS indices are 0–3', () => {
    const indices = MODE_BUTTONS.map(([m]) => m);
    expect(indices).toEqual([0, 1, 2, 3]);
  });
});

describe('Layer visibility', () => {
  it('all layers visible when hiddenLayers is empty', () => {
    expect(isLayerVisible([], 'amateur')).toBe(true);
    expect(isLayerVisible([], 'broadcast')).toBe(true);
  });

  it('hidden layer returns false', () => {
    expect(isLayerVisible(['amateur'], 'amateur')).toBe(false);
  });

  it('non-hidden layer returns true even when others hidden', () => {
    expect(isLayerVisible(['amateur'], 'broadcast')).toBe(true);
  });

  it('toggleLayer hides a visible layer', () => {
    const result = toggleLayer([], 'amateur');
    expect(result).toEqual(['amateur']);
  });

  it('toggleLayer shows a hidden layer', () => {
    const result = toggleLayer(['amateur', 'broadcast'], 'amateur');
    expect(result).toEqual(['broadcast']);
  });

  it('toggleLayer is idempotent round-trip', () => {
    const step1 = toggleLayer([], 'amateur');
    const step2 = toggleLayer(step1, 'amateur');
    expect(step2).toEqual([]);
  });

  it('toggleLayer preserves other layers', () => {
    const hidden = ['amateur', 'broadcast', 'utility'];
    const result = toggleLayer(hidden, 'broadcast');
    expect(result).toEqual(['amateur', 'utility']);
  });
});

describe('Scope mode applicability', () => {
  it('span applicable in CTR mode (0)', () => {
    expect(isSpanApplicable(0)).toBe(true);
  });

  it('span applicable in S-C mode (2)', () => {
    expect(isSpanApplicable(2)).toBe(true);
  });

  it('span not applicable in FIX mode (1)', () => {
    expect(isSpanApplicable(1)).toBe(false);
  });

  it('span not applicable in S-F mode (3)', () => {
    expect(isSpanApplicable(3)).toBe(false);
  });

  it('span not applicable when undefined', () => {
    expect(isSpanApplicable(undefined)).toBe(false);
  });

  it('edge applicable in FIX mode (1)', () => {
    expect(isEdgeApplicable(1)).toBe(true);
  });

  it('edge applicable in S-F mode (3)', () => {
    expect(isEdgeApplicable(3)).toBe(true);
  });

  it('edge not applicable in CTR (0) or S-C (2)', () => {
    expect(isEdgeApplicable(0)).toBe(false);
    expect(isEdgeApplicable(2)).toBe(false);
  });

  it('span and edge are mutually exclusive for all modes', () => {
    for (const [mode] of MODE_BUTTONS) {
      expect(isSpanApplicable(mode) !== isEdgeApplicable(mode)).toBe(true);
    }
  });
});

describe('Span clamping', () => {
  it('increments within range', () => {
    expect(clampSpan(3, 1)).toBe(4);
  });

  it('decrements within range', () => {
    expect(clampSpan(3, -1)).toBe(2);
  });

  it('clamps at upper bound (7)', () => {
    expect(clampSpan(7, 1)).toBe(7);
  });

  it('clamps at lower bound (0)', () => {
    expect(clampSpan(0, -1)).toBe(0);
  });
});

describe('Speed clamping (inverted delta)', () => {
  it('delta +1 decreases speed value (visual ▶ = faster)', () => {
    expect(clampSpeed(1, 1)).toBe(0);
  });

  it('delta -1 increases speed value (visual ◀ = slower)', () => {
    expect(clampSpeed(1, -1)).toBe(2);
  });

  it('clamps at lower bound', () => {
    expect(clampSpeed(0, 1)).toBe(0);
  });

  it('clamps at upper bound', () => {
    expect(clampSpeed(2, -1)).toBe(2);
  });
});

describe('Receiver switching', () => {
  it('switches from MAIN (0) to SUB (1)', () => {
    expect(nextReceiver(0)).toBe(1);
  });

  it('switches from SUB (1) to MAIN (0)', () => {
    expect(nextReceiver(1)).toBe(0);
  });

  it('any other value defaults to MAIN toggle (becomes 1)', () => {
    expect(nextReceiver(2)).toBe(1);
  });
});

describe('BRT level clamping', () => {

  it('increases within range', () => {
    expect(clampBrt(0, 5)).toBe(5);
  });

  it('decreases within range', () => {
    expect(clampBrt(0, -5)).toBe(-5);
  });

  it('clamps at +30', () => {
    expect(clampBrt(30, 5)).toBe(30);
  });

  it('clamps at -30', () => {
    expect(clampBrt(-30, -5)).toBe(-30);
  });
});

describe('REF level clamping', () => {

  it('REF range is -30 to +10 (asymmetric)', () => {
    expect(clampRef(10, 5)).toBe(10);
    expect(clampRef(-30, -5)).toBe(-30);
  });

  it('normal increment', () => {
    expect(clampRef(0, 5)).toBe(5);
  });

  it('normal decrement', () => {
    expect(clampRef(0, -5)).toBe(-5);
  });
});

describe('Label display formatting', () => {
  it('SPAN defaults to ±25k when index is 3', () => {
    expect(SPAN_LABELS[3]).toBe('±25k');
  });

  it('fallback for unknown span index matches component behavior', () => {
    // Component: SPAN_LABELS[scopeControls?.span ?? 3] ?? '±25k'
    const fallback = SPAN_LABELS[99] ?? '±25k';
    expect(fallback).toBe('±25k');
  });

  it('SPEED defaults to MID when index is 1', () => {
    expect(SPEED_LABELS[1]).toBe('MID');
  });

  it('fallback for unknown speed index matches component behavior', () => {
    const fallback = SPEED_LABELS[99] ?? 'MID';
    expect(fallback).toBe('MID');
  });
});
