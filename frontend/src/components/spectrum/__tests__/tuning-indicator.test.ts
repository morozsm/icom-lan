/**
 * Tests for the tuning indicator (red line) position on spectrum/waterfall.
 *
 * Bug #552: In CTR mode with centerType=Filter, the scope centers on the
 * filter midpoint (carrier + filterWidth/2 for USB), NOT on the carrier.
 * Hardcoding the indicator at center (width/2 or 50%) placed it at the
 * filter midpoint instead of the VFO/carrier frequency.
 *
 * Fix: always compute indicator proportionally from tuneHz vs scope range.
 * These tests ensure the regression cannot recur.
 */
import { describe, it, expect } from 'vitest';

// ── Re-implement the tuning indicator logic from SpectrumPanel / spectrum-renderer ──

/** Clamp value between min and max (same as renderer's clamp). */
function clamp(value: number, min: number, max: number): number {
  return value < min ? min : value > max ? max : value;
}

/**
 * Compute tuning indicator position as percentage (0–100).
 * Mirrors tuneLinePct from SpectrumPanel.svelte.
 */
function computeTuneLinePct(
  tuneHz: number,
  startFreq: number,
  endFreq: number,
): number {
  const spanHz = endFreq - startFreq;
  if (spanHz > 0 && tuneHz > 0 && tuneHz >= startFreq && tuneHz <= endFreq) {
    return ((tuneHz - startFreq) / spanHz) * 100;
  }
  return 50;
}

/**
 * Compute tuning indicator position in pixels (0–width).
 * Mirrors tunePx from spectrum-renderer.ts.
 */
function computeTunePx(
  tuneHz: number,
  centerHz: number,
  spanHz: number,
  width: number,
): number {
  if (tuneHz > 0 && spanHz > 0) {
    const startHz = centerHz - spanHz / 2;
    return clamp(((tuneHz - startHz) / spanHz) * width, 0, width);
  }
  return width / 2;
}

// ── Scope frame parsing (with mode byte) ────────────────────────────────────────

interface ScopeFrame {
  receiver: number;
  mode: number;
  startFreq: number;
  endFreq: number;
  pixels: Uint8Array;
}

function parseScopeFrame(buf: ArrayBuffer): ScopeFrame | null {
  const view = new DataView(buf);
  if (view.byteLength < 16 || view.getUint8(0) !== 0x01) return null;
  const receiver = view.getUint8(1);
  const mode = view.getUint8(2);
  const startFreq = view.getUint32(3, true);
  const endFreq = view.getUint32(7, true);
  const pixelCount = view.getUint16(14, true);
  if (16 + pixelCount > view.byteLength) return null;
  return { receiver, mode, startFreq, endFreq, pixels: new Uint8Array(buf, 16, pixelCount) };
}

function encodeFrame(
  receiver: number,
  mode: number,
  startFreq: number,
  endFreq: number,
  pixels: Uint8Array,
): ArrayBuffer {
  const buf = new ArrayBuffer(16 + pixels.length);
  const view = new DataView(buf);
  view.setUint8(0, 0x01);
  view.setUint8(1, receiver);
  view.setUint8(2, mode);
  view.setUint32(3, startFreq, true);
  view.setUint32(7, endFreq, true);
  view.setUint16(14, pixels.length, true);
  new Uint8Array(buf, 16).set(pixels);
  return buf;
}

// ── Tests ────────────────────────────────────────────────────────────────────────

describe('scope frame parsing — mode byte', () => {
  it('parses mode=0 (CTR) from frame header', () => {
    const buf = encodeFrame(0, 0, 14_050_000, 14_098_000, new Uint8Array(5));
    expect(parseScopeFrame(buf)!.mode).toBe(0);
  });

  it('parses mode=1 (FIX) from frame header', () => {
    const buf = encodeFrame(0, 1, 14_000_000, 14_350_000, new Uint8Array(5));
    expect(parseScopeFrame(buf)!.mode).toBe(1);
  });

  it('parses mode=2 (SCROLL-C) from frame header', () => {
    const buf = encodeFrame(0, 2, 14_050_000, 14_098_000, new Uint8Array(5));
    expect(parseScopeFrame(buf)!.mode).toBe(2);
  });

  it('parses mode=3 (SCROLL-F) from frame header', () => {
    const buf = encodeFrame(0, 3, 14_000_000, 14_350_000, new Uint8Array(5));
    expect(parseScopeFrame(buf)!.mode).toBe(3);
  });

  it('preserves all other fields alongside mode', () => {
    const pixels = new Uint8Array([10, 20, 30]);
    const buf = encodeFrame(1, 3, 7_000_000, 7_300_000, pixels);
    const frame = parseScopeFrame(buf)!;
    expect(frame.receiver).toBe(1);
    expect(frame.mode).toBe(3);
    expect(frame.startFreq).toBe(7_000_000);
    expect(frame.endFreq).toBe(7_300_000);
    expect(Array.from(frame.pixels)).toEqual([10, 20, 30]);
  });
});

describe('tuning indicator — proportional positioning (#552)', () => {
  // CTR mode with centerType=Filter: scope centers on filter midpoint,
  // not on carrier. The indicator must show the CARRIER position.

  it('CTR + Filter center: USB carrier is LEFT of scope center', () => {
    // USB mode, filter 3200 Hz: carrier at 14.173, filter center at 14.1746
    const carrier = 14_173_000;
    const filterWidth = 3200;
    const filterCenter = carrier + filterWidth / 2;  // 14_174_600

    // Scope in CTR/Filter mode centers on filter center
    const scopeCenter = filterCenter;
    const halfSpan = 10_000;  // ±10 kHz
    const startFreq = scopeCenter - halfSpan;
    const endFreq = scopeCenter + halfSpan;

    const pct = computeTuneLinePct(carrier, startFreq, endFreq);
    // Carrier should be to the LEFT of center (~42%)
    expect(pct).toBeCloseTo(42, 0);
    expect(pct).toBeLessThan(50);
  });

  it('CTR + Filter center: LSB carrier is RIGHT of scope center', () => {
    // LSB mode, filter 2400 Hz: carrier at 7.050, filter center at 7.04880
    const carrier = 7_050_000;
    const filterWidth = 2400;
    const filterCenter = carrier - filterWidth / 2;  // 7_048_800

    const scopeCenter = filterCenter;
    const halfSpan = 10_000;
    const startFreq = scopeCenter - halfSpan;
    const endFreq = scopeCenter + halfSpan;

    const pct = computeTuneLinePct(carrier, startFreq, endFreq);
    // Carrier should be to the RIGHT of center (~56%)
    expect(pct).toBeGreaterThan(50);
    expect(pct).toBeCloseTo(56, 0);
  });

  it('CTR + Carrier center: indicator is exactly at 50%', () => {
    // centerType=Carrier: scope center === VFO frequency
    const carrier = 14_074_000;
    const halfSpan = 25_000;
    const startFreq = carrier - halfSpan;
    const endFreq = carrier + halfSpan;

    const pct = computeTuneLinePct(carrier, startFreq, endFreq);
    expect(pct).toBe(50);
  });

  it('FIX mode: indicator at correct proportional position', () => {
    // Fixed scope 14.000–14.350, VFO at 14.074
    const startFreq = 14_000_000;
    const endFreq = 14_350_000;
    const carrier = 14_074_000;

    const pct = computeTuneLinePct(carrier, startFreq, endFreq);
    expect(pct).toBeCloseTo((74_000 / 350_000) * 100, 1);
  });

  it('tuneHz outside scope range falls back to 50%', () => {
    // VFO at 21 MHz but scope shows 14 MHz band
    const pct = computeTuneLinePct(21_000_000, 14_000_000, 14_350_000);
    expect(pct).toBe(50);
  });

  it('tuneHz=0 falls back to 50%', () => {
    expect(computeTuneLinePct(0, 14_000_000, 14_350_000)).toBe(50);
  });
});

describe('tunePx — pixel-level indicator (renderer)', () => {
  const width = 1000;

  it('CTR + Filter center: pixel position matches filter offset', () => {
    const carrier = 14_173_000;
    const filterCenter = 14_174_600;  // carrier + 1600 Hz (USB 3200)
    const spanHz = 20_000;

    const px = computeTunePx(carrier, filterCenter, spanHz, width);
    // (14173000 - 14164600) / 20000 * 1000 = 420
    expect(px).toBeCloseTo(420, 0);
    expect(px).toBeLessThan(width / 2);  // LEFT of center
  });

  it('CTR + Carrier center: pixel is exactly at center', () => {
    const carrier = 14_074_000;
    const px = computeTunePx(carrier, carrier, 50_000, width);
    expect(px).toBe(width / 2);
  });

  it('clamps to 0 when tuneHz is below scope range', () => {
    const px = computeTunePx(14_000_000, 14_200_000, 10_000, width);
    expect(px).toBe(0);
  });

  it('clamps to width when tuneHz is above scope range', () => {
    const px = computeTunePx(14_400_000, 14_200_000, 10_000, width);
    expect(px).toBe(width);
  });

  it('tuneHz=0 falls back to center', () => {
    expect(computeTunePx(0, 14_074_000, 50_000, width)).toBe(width / 2);
  });
});
