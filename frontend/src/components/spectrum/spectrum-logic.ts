/**
 * Pure logic extracted from SpectrumPanel.svelte for testability.
 */

// --- Scope frame binary protocol ---
export interface ScopeFrame {
  receiver: number;
  mode: number;       // 0=CTR, 1=FIX, 2=SCROLL-C, 3=SCROLL-F
  startFreq: number;
  endFreq: number;
  pixels: Uint8Array;
}

export function parseScopeFrame(buf: ArrayBuffer): ScopeFrame | null {
  const view = new DataView(buf);
  // Magic byte 0x01, minimum 16-byte header
  if (view.byteLength < 16 || view.getUint8(0) !== 0x01) return null;
  const receiver = view.getUint8(1);
  const mode = view.getUint8(2);
  const startFreq = view.getUint32(3, true);
  const endFreq = view.getUint32(7, true);
  const pixelCount = view.getUint16(14, true);
  if (16 + pixelCount > view.byteLength) return null;
  return {
    receiver,
    mode,
    startFreq,
    endFreq,
    pixels: new Uint8Array(buf, 16, pixelCount),
  };
}

// --- Scale helpers ---
export function formatFreqOffset(hz: number): string {
  if (hz === 0) return '0';
  const absHz = Math.abs(hz);
  const sign = hz < 0 ? '-' : '+';
  if (absHz >= 1e6) return `${sign}${(absHz / 1e6).toFixed(1)}M`;
  if (absHz >= 1e3) return `${sign}${(absHz / 1e3).toFixed(0)}k`;
  return `${sign}${absHz}`;
}

export function deriveFreqTicks(spanHz: number): { position: number; label: string }[] {
  if (spanHz <= 0) return [];
  return [-1, -0.5, 0, 0.5, 1].map((ratio) => ({
    position: (ratio + 1) * 50,
    label: formatFreqOffset((spanHz * ratio) / 2),
  }));
}

// --- Drag helpers ---
export function getDragInterval(speed: number): number {
  if (speed > 600) return 700;
  if (speed > 200) return 400;
  return 200;
}

// --- Scope mode helpers ---
export function isFixedScope(mode: number): boolean {
  return mode === 1 || mode === 3;
}

// --- Click-to-tune helpers ---
export function freqFromPixel(
  clientX: number,
  rectLeft: number,
  rectWidth: number,
  startFreq: number,
  spanHz: number,
): number {
  return startFreq + ((clientX - rectLeft) / rectWidth) * spanHz;
}
