/**
 * Pure rendering functions for the AudioSpectrum canvas.
 * No Svelte dependency — testable with mock contexts.
 */

// ── Types ────────────────────────────────────────────────────────────────────

export interface SpectrumState {
  /** FFT bin amplitudes (0-160 range, symmetric around DC) */
  pixels: Uint8Array | null;
  /** Effective bandwidth of the FFT data in Hz */
  bandwidth: number;
  /** Filter passband width in Hz */
  filterWidth: number;
  /** Max filter width in Hz (for PBT normalization) */
  filterWidthMax: number;
  /** PBT inner raw value (0-255, center=128) */
  pbtInner: number;
  /** PBT outer raw value (0-255, center=128) */
  pbtOuter: number;
  /** Manual notch active */
  manualNotch: boolean;
  /** Manual notch frequency (0-255 raw) */
  notchFreq: number;
  /** Contour level (0=off, >0=active) */
  contour: number;
  /** Contour center frequency offset (0-255 raw) */
  contourFreq: number;
}

export interface GridLabel {
  /** X position as fraction 0..1 of canvas width */
  xFrac: number;
  /** Label text, e.g. "-1.0k", "0", "+1.5k" */
  text: string;
}

export interface TrapezoidGeometry {
  /** Left edge of flat top (x fraction 0..1) */
  leftX: number;
  /** Right edge of flat top (x fraction 0..1) */
  rightX: number;
  /** Slope width as fraction of canvas width */
  slopeWidth: number;
}

export interface PbtOverlay {
  inner: TrapezoidGeometry;
  outer: TrapezoidGeometry;
  /** Intersection of inner and outer (effective passband) */
  intersection: { leftX: number; rightX: number; slopeWidth: number };
}

// ── Constants ────────────────────────────────────────────────────────────────

const SPECTRUM_LINE_COLOR = 'rgba(0, 220, 220, 0.9)';
const GRID_LINE_COLOR = 'rgba(255, 255, 255, 0.08)';
const GRID_LABEL_COLOR = 'rgba(255, 255, 255, 0.4)';
const NOTCH_COLOR = 'rgba(255, 80, 40, 0.35)';
const CONTOUR_COLOR = 'rgba(180, 140, 255, 0.3)';
const PBT_INNER_COLOR = 'rgba(60, 130, 255, 0.15)';
const PBT_OUTER_COLOR = 'rgba(60, 200, 100, 0.15)';
const PBT_INTERSECTION_COLOR = 'rgba(100, 200, 255, 0.2)';

const MAX_AMPLITUDE = 160;
const GRID_MARGIN_BOTTOM = 16;

// ── PBT math ─────────────────────────────────────────────────────────────────

/** Convert PBT raw (0-255, center=128) to Hz offset. */
export function pbtRawToHz(raw: number, center = 128, maxHz = 1200): number {
  return Math.round((raw - center) * (maxHz / center));
}

/**
 * Compute PBT trapezoid geometry for inner and outer PBT.
 * Returns positions as fractions of the canvas width (0..1).
 *
 * The passband center is at 0.5 (DC/center frequency).
 * PBT shifts the filter edges relative to center.
 */
export function computePbtOverlay(
  pbtInner: number,
  pbtOuter: number,
  filterWidth: number,
  bandwidth: number,
): PbtOverlay {
  const halfBw = bandwidth / 2;
  const halfFilter = filterWidth / 2;

  const innerHz = pbtRawToHz(pbtInner);
  const outerHz = pbtRawToHz(pbtOuter);

  // Inner PBT shifts one edge, outer shifts the other
  const innerLeft = (-halfFilter + innerHz) / halfBw * 0.5 + 0.5;
  const innerRight = (halfFilter + innerHz) / halfBw * 0.5 + 0.5;
  const outerLeft = (-halfFilter + outerHz) / halfBw * 0.5 + 0.5;
  const outerRight = (halfFilter + outerHz) / halfBw * 0.5 + 0.5;

  const slopeWidth = 0.03; // 3% of width for trapezoid slope

  const inner: TrapezoidGeometry = {
    leftX: Math.max(0, Math.min(1, innerLeft)),
    rightX: Math.max(0, Math.min(1, innerRight)),
    slopeWidth,
  };
  const outer: TrapezoidGeometry = {
    leftX: Math.max(0, Math.min(1, outerLeft)),
    rightX: Math.max(0, Math.min(1, outerRight)),
    slopeWidth,
  };

  // Intersection: overlap region
  const intLeft = Math.max(inner.leftX, outer.leftX);
  const intRight = Math.min(inner.rightX, outer.rightX);

  return {
    inner,
    outer,
    intersection: {
      leftX: intLeft,
      rightX: Math.max(intLeft, intRight),
      slopeWidth,
    },
  };
}

// ── Frequency grid ───────────────────────────────────────────────────────────

/**
 * Generate frequency grid labels for the given bandwidth.
 * Labels show +-Hz from center.
 */
export function generateGridLabels(bandwidth: number): GridLabel[] {
  const halfBw = bandwidth / 2;
  // Choose a nice step: 500, 1000, 2000, 5000, 10000 Hz
  const steps = [100, 200, 500, 1000, 2000, 5000, 10000];
  let step = steps[0];
  for (const s of steps) {
    if (halfBw / s >= 2 && halfBw / s <= 8) {
      step = s;
      break;
    }
  }

  const labels: GridLabel[] = [];
  // Center label
  labels.push({ xFrac: 0.5, text: '0' });

  for (let hz = step; hz <= halfBw; hz += step) {
    const frac = hz / halfBw * 0.5;
    // Positive side
    labels.push({ xFrac: 0.5 + frac, text: formatHz(hz) });
    // Negative side
    labels.push({ xFrac: 0.5 - frac, text: formatHz(-hz) });
  }

  return labels.sort((a, b) => a.xFrac - b.xFrac);
}

function formatHz(hz: number): string {
  const abs = Math.abs(hz);
  const sign = hz < 0 ? '-' : '+';
  if (abs >= 1000) {
    const k = abs / 1000;
    return `${sign}${k % 1 === 0 ? k.toFixed(0) : k.toFixed(1)}k`;
  }
  return `${sign}${abs}`;
}

// ── Spectrum line coordinates ────────────────────────────────────────────────

/**
 * Compute spectrum line Y coordinates from FFT data.
 * Returns an array of {x, y} normalized to canvas dimensions.
 */
export function computeSpectrumLine(
  pixels: Uint8Array,
  width: number,
  height: number,
  gain: number = 1,
): { x: number; y: number }[] {
  const points: { x: number; y: number }[] = [];
  const usableHeight = height - GRID_MARGIN_BOTTOM;
  const len = pixels.length;
  if (len === 0) return points;

  for (let i = 0; i < width; i++) {
    // Map canvas x to pixel index
    const pixIdx = Math.floor((i / width) * len);
    const clamped = Math.max(0, Math.min(len - 1, pixIdx));
    const raw = Math.min(pixels[clamped] * gain, MAX_AMPLITUDE);
    const normalized = raw / MAX_AMPLITUDE;
    const y = usableHeight * (1 - normalized);
    points.push({ x: i, y });
  }
  return points;
}

// ── Notch position ───────────────────────────────────────────────────────────

/**
 * Compute notch X position as fraction 0..1 of canvas width.
 * notchFreq is raw 0-255, mapped across the bandwidth.
 */
export function computeNotchX(notchFreq: number, bandwidth: number): number {
  // 0-255 raw maps linearly across the passband
  // 0 = left edge of bandwidth, 255 = right edge, 128 = center
  return notchFreq / 255;
}

// ── Main render ──────────────────────────────────────────────────────────────

/** Smoothed amplitude buffer — reused across frames */
let smoothed: Float32Array | null = null;
const ATTACK = 0.4;
const DECAY = 0.15;

/** Auto-gain AGC state */
let agcPeak = 40;
const AGC_ATTACK = 0.3;
const AGC_RELEASE = 0.02;

/**
 * Full render pass: background, grid, PBT overlays, spectrum, notch, contour.
 */
export function renderAudioSpectrum(
  ctx: CanvasRenderingContext2D,
  width: number,
  height: number,
  state: SpectrumState,
): void {
  const { pixels, bandwidth, filterWidth, filterWidthMax, pbtInner, pbtOuter,
          manualNotch, notchFreq, contour, contourFreq } = state;

  // Clear
  ctx.clearRect(0, 0, width, height);

  // Background
  ctx.fillStyle = 'rgba(11, 15, 20, 0.95)';
  ctx.fillRect(0, 0, width, height);

  const usableH = height - GRID_MARGIN_BOTTOM;

  // ── Grid lines + labels ──
  const labels = generateGridLabels(bandwidth);
  ctx.strokeStyle = GRID_LINE_COLOR;
  ctx.lineWidth = 1;
  ctx.font = '10px system-ui, sans-serif';
  ctx.textAlign = 'center';
  ctx.fillStyle = GRID_LABEL_COLOR;

  for (const label of labels) {
    const x = Math.round(label.xFrac * width);
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, usableH);
    ctx.stroke();
    ctx.fillText(label.text, x, height - 3);
  }

  // ── PBT overlays ──
  if (pbtInner !== 128 || pbtOuter !== 128 || filterWidth < filterWidthMax) {
    const pbt = computePbtOverlay(pbtInner, pbtOuter, filterWidth, bandwidth);
    drawTrapezoid(ctx, pbt.inner, width, usableH, PBT_INNER_COLOR);
    drawTrapezoid(ctx, pbt.outer, width, usableH, PBT_OUTER_COLOR);
    drawTrapezoid(ctx, pbt.intersection, width, usableH, PBT_INTERSECTION_COLOR);
  }

  // ── Spectrum line ──
  if (pixels && pixels.length > 0) {
    // AGC
    let peakVal = 1;
    for (let i = 0; i < pixels.length; i++) {
      if (pixels[i] > peakVal) peakVal = pixels[i];
    }
    if (peakVal > agcPeak) {
      agcPeak += (peakVal - agcPeak) * AGC_ATTACK;
    } else {
      agcPeak += (peakVal - agcPeak) * AGC_RELEASE;
    }
    agcPeak = Math.max(10, agcPeak);
    const gain = MAX_AMPLITUDE / agcPeak;

    // Smooth
    const numPoints = width;
    if (!smoothed || smoothed.length !== numPoints) {
      smoothed = new Float32Array(numPoints);
    }

    // Draw spectrum line with gradient fill
    ctx.beginPath();
    ctx.moveTo(0, usableH);

    for (let i = 0; i < numPoints; i++) {
      const pixIdx = Math.floor((i / numPoints) * pixels.length);
      const clamped = Math.max(0, Math.min(pixels.length - 1, pixIdx));
      const rawAmp = Math.min(pixels[clamped] * gain, MAX_AMPLITUDE) / MAX_AMPLITUDE;

      // Smooth
      const prev = smoothed[i];
      smoothed[i] = rawAmp > prev
        ? prev + (rawAmp - prev) * ATTACK
        : prev + (rawAmp - prev) * DECAY;

      const y = usableH * (1 - smoothed[i]);
      ctx.lineTo(i, y);
    }

    // Close path for fill
    ctx.lineTo(width, usableH);
    ctx.closePath();

    // Gradient fill
    const grad = ctx.createLinearGradient(0, 0, 0, usableH);
    grad.addColorStop(0, 'rgba(0, 220, 180, 0.4)');
    grad.addColorStop(0.5, 'rgba(0, 180, 220, 0.2)');
    grad.addColorStop(1, 'rgba(0, 120, 200, 0.05)');
    ctx.fillStyle = grad;
    ctx.fill();

    // Spectrum line on top
    ctx.beginPath();
    ctx.moveTo(0, usableH);
    for (let i = 0; i < numPoints; i++) {
      const y = usableH * (1 - smoothed[i]);
      ctx.lineTo(i, y);
    }
    ctx.strokeStyle = SPECTRUM_LINE_COLOR;
    ctx.lineWidth = 1.5;
    ctx.stroke();
  }

  // ── Manual notch (V-shape) ──
  if (manualNotch) {
    const nx = computeNotchX(notchFreq, bandwidth) * width;
    const nHalfW = width * 0.03;
    const depth = usableH * 0.6;

    ctx.fillStyle = NOTCH_COLOR;
    ctx.beginPath();
    ctx.moveTo(nx - nHalfW * 2, 0);
    ctx.lineTo(nx, depth);
    ctx.lineTo(nx + nHalfW * 2, 0);
    ctx.closePath();
    ctx.fill();

    // Notch frequency label
    const notchHz = Math.round((notchFreq / 255 - 0.5) * bandwidth);
    ctx.fillStyle = 'rgba(255, 100, 60, 0.7)';
    ctx.font = '9px system-ui, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(`${notchHz > 0 ? '+' : ''}${notchHz} Hz`, nx, depth + 12);
  }

  // ── Contour (U-shape dip) ──
  if (contour > 0) {
    const cx = (contourFreq / 255) * width;
    const depth = (contour / 255) * usableH * 0.4;
    const cWidth = width * 0.12;

    ctx.strokeStyle = CONTOUR_COLOR;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(cx - cWidth, 0);
    ctx.quadraticCurveTo(cx, depth * 2, cx + cWidth, 0);
    ctx.stroke();

    // Fill the contour area
    ctx.fillStyle = 'rgba(180, 140, 255, 0.08)';
    ctx.beginPath();
    ctx.moveTo(cx - cWidth, 0);
    ctx.quadraticCurveTo(cx, depth * 2, cx + cWidth, 0);
    ctx.closePath();
    ctx.fill();
  }
}

/** Reset smoothing buffers (e.g. on resize or mode change) */
export function resetSmoothing(): void {
  smoothed = null;
  agcPeak = 40;
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function drawTrapezoid(
  ctx: CanvasRenderingContext2D,
  geom: TrapezoidGeometry,
  width: number,
  height: number,
  color: string,
): void {
  const { leftX, rightX, slopeWidth } = geom;
  const l = leftX * width;
  const r = rightX * width;
  const sw = slopeWidth * width;

  ctx.fillStyle = color;
  ctx.beginPath();
  // Trapezoid: wider at bottom (passband base), narrower at top (filter slope)
  ctx.moveTo(l - sw, height);
  ctx.lineTo(l, 0);
  ctx.lineTo(r, 0);
  ctx.lineTo(r + sw, height);
  ctx.closePath();
  ctx.fill();
}
