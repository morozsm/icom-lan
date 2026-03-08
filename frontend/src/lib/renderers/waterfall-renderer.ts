// Framework-agnostic waterfall renderer for radio scope data.
// Maintains a scrolling bitmap: each pushRow() adds a new line at the top
// and shifts existing content down — no full redraw needed.

export interface WaterfallOptions {
  colorMap: 'default' | 'grayscale' | 'heat';
  speed: number;    // rows scrolled per pushRow call (1 = normal)
  centerHz: number; // center frequency in Hz
  spanHz: number;   // frequency span in Hz
}

export const defaultWaterfallOptions: WaterfallOptions = {
  colorMap: 'default',
  speed: 1,
  centerHz: 0,
  spanHz: 0,
};

// Build a 256-entry RGB lookup table for amplitude → color mapping.
function buildColorLut(colorMap: WaterfallOptions['colorMap']): Uint8Array {
  const lut = new Uint8Array(256 * 3);
  for (let v = 0; v < 256; v++) {
    let r = 0,
      g = 0,
      b = 0;
    if (colorMap === 'grayscale') {
      r = g = b = v;
    } else if (colorMap === 'heat') {
      // black → red → yellow → white
      if (v < 85) {
        r = Math.floor(v * 3);
      } else if (v < 170) {
        r = 255;
        g = Math.floor((v - 85) * 3);
      } else {
        r = 255;
        g = 255;
        b = Math.floor((v - 170) * 3);
      }
    } else {
      // default: black-blue → green → yellow → red → white
      // Ported from legacy icom-lan UI (WF_LUT)
      if (v < 50) {
        b = Math.floor(v * 2.5);
      } else if (v < 100) {
        g = Math.floor((v - 50) * 4);
        b = Math.floor(125 - (v - 50) * 2);
      } else if (v < 160) {
        r = Math.floor((v - 100) * 3);
        g = 200;
      } else if (v < 220) {
        r = 255;
        g = Math.floor(200 - (v - 160) * 3);
      } else {
        r = 255;
        g = Math.floor(v - 120);
        b = Math.floor(v - 120);
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
    this.lut = buildColorLut(options.colorMap);
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

    // Build the new top row using the color LUT — fresh ImageData each time
    // (avoids stale buffer issues after resize)
    const rowBuf = ctx.createImageData(w, 1);
    const rowData = rowBuf.data;
    const lut = this.lut;
    for (let x = 0; x < w; x++) {
      const p = data[Math.min(n - 1, Math.floor((x / w) * n))];
      const v = Math.min(255, Math.floor((Math.min(p, 160) / 160) * 255));
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

  /** Update rendering options (e.g. colorMap, centerHz, spanHz). */
  updateOptions(opts: Partial<WaterfallOptions>): void {
    this.options = { ...this.options, ...opts };
    if (opts.colorMap !== undefined) {
      this.lut = buildColorLut(this.options.colorMap);
    }
  }

  /** Map a canvas x-pixel to the corresponding frequency in Hz. */
  pixelToFreq(x: number): number {
    const { centerHz, spanHz } = this.options;
    if (spanHz <= 0 || this.width <= 0) return centerHz;
    return centerHz - spanHz / 2 + (x / this.width) * spanHz;
  }

  /** Fill the canvas with black. */
  clear(): void {
    if (this.destroyed || this.width <= 0 || this.height <= 0) return;
    this.ctx.fillStyle = '#000';
    this.ctx.fillRect(0, 0, this.width, this.height);
  }

  destroy(): void {
    this.destroyed = true;
    this.rowBuf = null;
    this.rowData = null;
    this.ctx = null as unknown as CanvasRenderingContext2D;
  }
}
