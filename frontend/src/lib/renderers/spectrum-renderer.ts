// Framework-agnostic spectrum renderer for radio scope data.
// Data: Uint8Array of amplitude values (0–160), mapped to canvas width.

export interface SpectrumOptions {
  bgColor: string;
  lineColor: string;
  fillColor: string;
  gridColor: string;
  textColor: string;
  refLevel: number;   // dB reference (reserved for future dB axis labels)
  spanHz: number;     // frequency span in Hz
  centerHz: number;   // center frequency in Hz
  lineWidth: number;
}

export const defaultSpectrumOptions: SpectrumOptions = {
  bgColor: 'transparent',
  lineColor: 'rgba(210,220,230,0.85)',
  fillColor: 'rgba(30,58,138,0.30)',
  gridColor: 'rgba(255,255,255,0.15)',
  textColor: 'rgba(180,200,220,0.6)',
  refLevel: 0,
  spanHz: 0,
  centerHz: 0,
  lineWidth: 1.2,
};

function clamp(v: number, lo: number, hi: number): number {
  return v < lo ? lo : v > hi ? hi : v;
}

// Cached gradient: recreated only when height or fillColor changes
let _gradCache: { grad: CanvasGradient; height: number; fillColor: string } | null = null;

/**
 * Render a spectrum line chart onto an existing 2D canvas context.
 *
 * The caller is responsible for DPR scaling: set canvas physical dimensions
 * to width*dpr × height*dpr, call ctx.setTransform(dpr,0,0,dpr,0,0) once,
 * then pass CSS logical width/height here.
 *
 * Optimization note: the $effect in SpectrumCanvas triggers on every data change;
 * for smoother perf consider throttling to requestAnimationFrame (already done via scheduleRender).
 */
export function renderSpectrum(
  ctx: CanvasRenderingContext2D,
  data: Uint8Array,
  width: number,
  height: number,
  options: SpectrumOptions,
): void {
  const n = data.length;
  if (!n || width <= 0 || height <= 0) return;

  const { bgColor, lineColor, fillColor, gridColor, textColor, spanHz, centerHz, lineWidth } =
    options;

  ctx.clearRect(0, 0, width, height);

  if (bgColor !== 'transparent') {
    ctx.fillStyle = bgColor;
    ctx.fillRect(0, 0, width, height);
  }

  // Grid
  const H_LINES = 5;
  const V_LINES = 10;
  ctx.strokeStyle = gridColor;
  ctx.lineWidth = 0.6;
  for (let i = 0; i <= H_LINES; i++) {
    const y = (i / H_LINES) * height;
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(width, y);
    ctx.stroke();
  }
  for (let i = 0; i <= V_LINES; i++) {
    const x = (i / V_LINES) * width;
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, height);
    ctx.stroke();
  }

  // Frequency labels
  if (spanHz > 0 && centerHz > 0) {
    const startHz = centerHz - spanHz / 2;
    ctx.fillStyle = textColor;
    ctx.font = '9px monospace';
    ctx.textAlign = 'center';
    for (let i = 0; i <= V_LINES; i++) {
      const hz = startHz + (i / V_LINES) * spanHz;
      const x = (i / V_LINES) * width;
      ctx.fillText((hz / 1e6).toFixed(3), clamp(x, 20, width - 20), height - 4);
    }
  }

  // Map amplitude data to canvas y-coordinates
  const yPoints = new Float32Array(width);
  for (let x = 0; x < width; x++) {
    const idx = Math.min(n - 1, Math.floor((x / width) * n));
    const amp = clamp(data[idx], 0, 160) / 160;
    yPoints[x] = height * (1 - amp);
  }

  // Filled area under spectrum (gradient cached; recreated only when height or fillColor changes)
  if (!_gradCache || _gradCache.height !== height || _gradCache.fillColor !== fillColor) {
    const grad = ctx.createLinearGradient(0, 0, 0, height);
    grad.addColorStop(0, fillColor);
    grad.addColorStop(1, 'rgba(30,58,138,0.02)');
    _gradCache = { grad, height, fillColor };
  }
  ctx.fillStyle = _gradCache.grad;
  ctx.beginPath();
  ctx.moveTo(0, height);
  for (let x = 0; x < width; x++) {
    ctx.lineTo(x, yPoints[x]);
  }
  ctx.lineTo(width, height);
  ctx.closePath();
  ctx.fill();

  // Spectrum line
  ctx.strokeStyle = lineColor;
  ctx.lineWidth = lineWidth;
  ctx.beginPath();
  for (let x = 0; x < width; x++) {
    if (x === 0) ctx.moveTo(0, yPoints[x]);
    else ctx.lineTo(x, yPoints[x]);
  }
  ctx.stroke();

  // Center frequency marker
  if (spanHz > 0) {
    ctx.strokeStyle = 'rgba(239,68,68,0.75)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(width / 2, 0);
    ctx.lineTo(width / 2, height);
    ctx.stroke();
  }
}
