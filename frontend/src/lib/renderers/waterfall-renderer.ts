// Framework-agnostic waterfall renderer for radio scope data.
// Maintains a scrolling bitmap: each pushRow() adds a new line at the top
// and shifts existing content down — no full redraw needed.

interface ColorStop {
  stop: number;
  color: string;
}

export const COLOR_SCHEMES = {
  classic: [
    { stop: 0.0, color: '#001020' }, // dark blue
    { stop: 0.2, color: '#0040A0' }, // blue
    { stop: 0.4, color: '#00C0C0' }, // cyan
    { stop: 0.6, color: '#00FF00' }, // green
    { stop: 0.8, color: '#FFFF00' }, // yellow
    { stop: 1.0, color: '#FF0000' }, // red
  ],
  thermal: [
    { stop: 0.0, color: '#000000' },
    { stop: 0.3, color: '#800080' }, // purple
    { stop: 0.5, color: '#FF0000' }, // red
    { stop: 0.7, color: '#FF8000' }, // orange
    { stop: 1.0, color: '#FFFF00' }, // yellow
  ],
  grayscale: [
    { stop: 0.0, color: '#000000' },
    { stop: 1.0, color: '#FFFFFF' },
  ],
} satisfies Record<string, ColorStop[]>;

export type ColorSchemeName = keyof typeof COLOR_SCHEMES;

export interface WaterfallOptions {
  colorScheme: ColorSchemeName;
  refLevel: number;  // -30 to +30 dB brightness offset
  speed: number;     // rows scrolled per pushRow call (1 = normal)
  centerHz: number;  // center frequency in Hz
  spanHz: number;    // frequency span in Hz
}

export const defaultWaterfallOptions: WaterfallOptions = {
  colorScheme: 'classic',
  refLevel: 0,
  speed: 1,
  centerHz: 0,
  spanHz: 0,
};

function hexToRgb(hex: string): [number, number, number] {
  const h = hex.replace('#', '');
  return [
    parseInt(h.slice(0, 2), 16),
    parseInt(h.slice(2, 4), 16),
    parseInt(h.slice(4, 6), 16),
  ];
}

// Build a 256-entry RGB lookup table from gradient color stops.
function buildColorLut(scheme: ColorSchemeName): Uint8Array {
  const lut = new Uint8Array(256 * 3);
  const palette = COLOR_SCHEMES[scheme];
  const stops = palette.map(({ stop, color }) => ({ stop, rgb: hexToRgb(color) }));

  for (let v = 0; v < 256; v++) {
    const t = v / 255;
    let r = 0, g = 0, b = 0;

    if (t <= stops[0].stop) {
      [r, g, b] = stops[0].rgb;
    } else if (t >= stops[stops.length - 1].stop) {
      [r, g, b] = stops[stops.length - 1].rgb;
    } else {
      for (let i = 0; i < stops.length - 1; i++) {
        if (t >= stops[i].stop && t <= stops[i + 1].stop) {
          const range = stops[i + 1].stop - stops[i].stop;
          const frac = range > 0 ? (t - stops[i].stop) / range : 0;
          r = Math.round(stops[i].rgb[0] + frac * (stops[i + 1].rgb[0] - stops[i].rgb[0]));
          g = Math.round(stops[i].rgb[1] + frac * (stops[i + 1].rgb[1] - stops[i].rgb[1]));
          b = Math.round(stops[i].rgb[2] + frac * (stops[i + 1].rgb[2] - stops[i].rgb[2]));
          break;
        }
      }
    }

    const i = v * 3;
    lut[i] = r;
    lut[i + 1] = g;
    lut[i + 2] = b;
  }
  return lut;
}

export class WaterfallRenderer {
  private ctx: CanvasRenderingContext2D;
  private options: WaterfallOptions;
  private lut: Uint8Array;
  private width: number;
  private height: number;
  private rowBuf: ImageData | null = null;
  private rowData: Uint8ClampedArray | null = null;
  private destroyed = false;

  constructor(canvas: HTMLCanvasElement, options: WaterfallOptions) {
    const ctx = canvas.getContext('2d');
    if (!ctx) throw new Error('Cannot get 2d context from waterfall canvas');
    this.ctx = ctx;
    this.options = { ...options };
    this.lut = buildColorLut(options.colorScheme);
    this.width = canvas.width;
    this.height = canvas.height;
    if (this.width > 0 && this.height > 0) {
      this._initBuffers();
      this.clear();
    }
  }

  private _initBuffers(): void {
    this.rowBuf = this.ctx.createImageData(this.width, 1);
    this.rowData = this.rowBuf.data;
  }

  /** Add a new scope data row at the top; shift existing content down. */
  pushRow(data: Uint8Array): void {
    if (this.destroyed) return;
    const ctx = this.ctx;
    if (!ctx) return;
    const canvas = ctx.canvas;
    const w = canvas.width;
    const h = canvas.height;
    const n = data.length;
    if (!n || w <= 0 || h <= 0) return;

    // Shift existing waterfall content down by 1 row (no full redraw)
    ctx.drawImage(canvas, 0, 0, w, h - 1, 0, 1, w, h - 1);

    // Build the new top row using the color LUT
    const rowBuf = ctx.createImageData(w, 1);
    const rowData = rowBuf.data;
    const lut = this.lut;
    // Ref level: maps -30..+30 dB → -127..+127 shift on 0-255 scale
    const refShift = Math.round((this.options.refLevel / 60) * 255);
    for (let x = 0; x < w; x++) {
      const p = data[Math.min(n - 1, Math.floor((x / w) * n))];
      // Gain boost: map 0-80 → 0-255 with sqrt curve for better contrast
      // at low signal levels (IC-7610 scope data peaks at ~55)
      const norm = Math.min(1.0, p / 80);
      const v = Math.min(255, Math.max(0, Math.floor(Math.sqrt(norm) * 255) + refShift));
      const li = v * 3;
      const pi = x * 4;
      rowData[pi] = lut[li];
      rowData[pi + 1] = lut[li + 1];
      rowData[pi + 2] = lut[li + 2];
      rowData[pi + 3] = 255;
    }
    ctx.putImageData(rowBuf, 0, 0);
  }

  /** Resize the waterfall canvas and reset buffer. Clears the display. */
  resize(width: number, height: number): void {
    if (this.destroyed) return;
    this.width = width;
    this.height = height;
    this.rowBuf = null;
    this.rowData = null;
    if (width > 0 && height > 0) {
      this._initBuffers();
      this.clear();
    }
  }

  /** Update rendering options (e.g. colorScheme, refLevel, centerHz, spanHz). */
  updateOptions(opts: Partial<WaterfallOptions>): void {
    this.options = { ...this.options, ...opts };
    if (opts.colorScheme !== undefined) {
      this.lut = buildColorLut(this.options.colorScheme);
    }
  }

  /** Map a canvas x-pixel to the corresponding frequency in Hz. */
  pixelToFreq(x: number): number {
    const { centerHz, spanHz } = this.options;
    if (spanHz <= 0 || this.width <= 0) return centerHz;
    return centerHz - spanHz / 2 + (x / this.width) * spanHz;
  }

  /** Fill the canvas with the background color. */
  clear(): void {
    if (this.destroyed || this.width <= 0 || this.height <= 0) return;
    this.ctx.fillStyle = '#001020';
    this.ctx.fillRect(0, 0, this.width, this.height);
  }

  destroy(): void {
    this.destroyed = true;
    this.rowBuf = null;
    this.rowData = null;
    this.ctx = null as unknown as CanvasRenderingContext2D;
  }
}
