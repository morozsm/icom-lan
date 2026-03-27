<script lang="ts">
  import { onMount } from 'svelte';

  interface Props {
    /** FFT pixel data from AudioFftScope (0-160 range) */
    data: Uint8Array | null;
    /** Register a push callback for streaming updates */
    onRegisterPush?: (fn: (data: Uint8Array) => void) => void;
    /** Filter passband width in Hz (e.g. 2400 for SSB) */
    filterWidth?: number;
    /** IF shift in Hz (positive = up, negative = down) */
    ifShift?: number;
    /** Contour level 0=off, 1-255=active (DSP EQ curve) */
    contour?: number;
    /** Contour center frequency offset (0-255, maps to audio range) */
    contourFreq?: number;
    /** Manual notch active */
    manualNotch?: boolean;
    /** Manual notch frequency (0-255 raw, maps to audio range) */
    notchFreq?: number;
    /** Auto notch active */
    autoNotch?: boolean;
    /** Audio sample rate */
    sampleRate?: number;
    /** Center frequency in Hz for scope display */
    centerFreqHz?: number;
    /** Current mode (SSB/CW/AM/FM etc.) */
    mode?: string;
  }

  let {
    data,
    onRegisterPush,
    filterWidth = 2400,
    ifShift = 0,
    contour = 0,
    contourFreq = 128,
    manualNotch = false,
    notchFreq = 128,
    autoNotch = false,
    sampleRate = 48000,
    centerFreqHz = 0,
    mode = 'USB',
  }: Props = $props();

  let canvas: HTMLCanvasElement;
  let cssWidth = $state(1);
  let cssHeight = $state(1);
  let rafId = 0;
  let visible = true;
  let latestPixels: Uint8Array | null = null;

  // ── LCD Colors ──
  const BG = '#C8A030';
  const DARK = '#1A1000';
  const DARK_ALPHA = 'rgba(26, 16, 0,';
  const GRID_ALPHA = 0.05;
  const SCANLINE_ALPHA = 0.035;

  // ── Filter geometry ──
  const SLOPE_ANGLE = 30; // degrees
  const SLOPE_TAN = Math.tan((SLOPE_ANGLE * Math.PI) / 180);

  // ── Smoothing for FFT bars ──
  let smoothed: Float32Array | null = null;
  const SMOOTH_ATTACK = 0.4;   // how fast bars rise
  const SMOOTH_DECAY = 0.15;   // how fast bars fall (slower = smoother)

  function draw(): void {
    if (!visible) { rafId = 0; return; }
    const pixels = latestPixels ?? data;
    if (canvas && cssWidth > 0 && cssHeight > 0) {
      const ctx = canvas.getContext('2d');
      if (ctx) renderScope(ctx, pixels, cssWidth, cssHeight);
    }
    rafId = requestAnimationFrame(draw);
  }

  function renderScope(
    ctx: CanvasRenderingContext2D,
    pixels: Uint8Array | null,
    w: number,
    h: number,
  ): void {
    const maxVal = 160;
    const halfBw = sampleRate / 2;
    const topMargin = 4;
    const bottomMargin = 14; // space for freq labels
    const drawH = h - topMargin - bottomMargin;
    const drawTop = topMargin;

    // ── Background ──
    ctx.fillStyle = BG;
    ctx.fillRect(0, 0, w, h);

    // ── Grid lines (horizontal, subtle) ──
    ctx.strokeStyle = `${DARK_ALPHA} ${GRID_ALPHA})`;
    ctx.lineWidth = 1;
    for (let i = 1; i <= 4; i++) {
      const y = drawTop + (drawH * i) / 5;
      ctx.beginPath();
      ctx.moveTo(0, Math.round(y) + 0.5);
      ctx.lineTo(w, Math.round(y) + 0.5);
      ctx.stroke();
    }

    // ── Center frequency marker ──
    ctx.strokeStyle = `${DARK_ALPHA} 0.12)`;
    ctx.lineWidth = 1;
    ctx.setLineDash([2, 4]);
    ctx.beginPath();
    ctx.moveTo(w / 2, drawTop);
    ctx.lineTo(w / 2, drawTop + drawH);
    ctx.stroke();
    ctx.setLineDash([]);

    // ── Filter trapezoid ──
    const filterCenterX = w / 2 + (ifShift / halfBw) * (w / 2);
    const filterHalfW = (filterWidth / 2 / halfBw) * (w / 2);
    // Slope width = height / tan(angle)
    const slopeW = drawH / SLOPE_TAN;
    const clampedSlope = Math.min(slopeW, filterHalfW * 0.8);

    // Trapezoid points (top-left, top-right, bottom-right, bottom-left)
    const topL = filterCenterX - filterHalfW;
    const topR = filterCenterX + filterHalfW;
    const botL = topL - clampedSlope;
    const botR = topR + clampedSlope;

    // Draw trapezoid fill (very subtle)
    ctx.fillStyle = `${DARK_ALPHA} 0.04)`;
    ctx.beginPath();
    ctx.moveTo(topL, drawTop);
    ctx.lineTo(topR, drawTop);
    ctx.lineTo(botR, drawTop + drawH);
    ctx.lineTo(botL, drawTop + drawH);
    ctx.closePath();
    ctx.fill();

    // Draw trapezoid outline
    ctx.strokeStyle = `${DARK_ALPHA} 0.35)`;
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(topL, drawTop);
    ctx.lineTo(topR, drawTop);
    ctx.lineTo(botR, drawTop + drawH);
    ctx.lineTo(botL, drawTop + drawH);
    ctx.closePath();
    ctx.stroke();

    // ── Contour curve (EQ) ──
    if (contour > 0) {
      const contourCenterX = (contourFreq / 255) * w;
      const contourDepth = (contour / 255) * drawH * 0.5;
      const contourWidth = w * 0.12;

      ctx.strokeStyle = `${DARK_ALPHA} 0.25)`;
      ctx.lineWidth = 1.5;
      ctx.setLineDash([4, 3]);
      ctx.beginPath();
      for (let x = 0; x < w; x += 2) {
        const dx = x - contourCenterX;
        const gaussian = Math.exp(-(dx * dx) / (2 * contourWidth * contourWidth));
        const y = drawTop + contourDepth * gaussian;
        if (x === 0) ctx.moveTo(x, drawTop);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
      ctx.setLineDash([]);
    }

    // ── Manual notch V-shape ──
    if (manualNotch) {
      const notchX = (notchFreq / 255) * w;
      const notchDepth = drawH * 0.7;
      const notchHalfW = w * 0.015;

      ctx.strokeStyle = `${DARK_ALPHA} 0.5)`;
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(notchX - notchHalfW * 3, drawTop);
      ctx.lineTo(notchX, drawTop + notchDepth);
      ctx.lineTo(notchX + notchHalfW * 3, drawTop);
      ctx.stroke();

      // Notch label
      ctx.fillStyle = `${DARK_ALPHA} 0.35)`;
      ctx.font = '8px monospace';
      ctx.textAlign = 'center';
      ctx.fillText('N', notchX, drawTop + notchDepth + 10);
    }

    // ── FFT Bars ──
    if (!pixels || pixels.length === 0) {
      // No data — flat noise floor
      drawNoiseFloor(ctx, w, drawTop, drawH);
    } else {
      drawFftBars(ctx, pixels, w, drawTop, drawH, maxVal,
        filterCenterX, filterHalfW, clampedSlope);
    }

    // ── Scanlines overlay ──
    for (let y = 0; y < h; y += 3) {
      ctx.fillStyle = `rgba(0, 0, 0, ${SCANLINE_ALPHA})`;
      ctx.fillRect(0, y, w, 1);
    }

    // ── Frequency labels at bottom ──
    drawFreqLabels(ctx, w, h, bottomMargin);

    // ── Bandwidth label (top-right) ──
    ctx.fillStyle = `${DARK_ALPHA} 0.3)`;
    ctx.font = '9px monospace';
    ctx.textAlign = 'right';
    const bwLabel = filterWidth >= 1000
      ? `${(filterWidth / 1000).toFixed(1)}k`
      : `${filterWidth}`;
    ctx.fillText(`BW ${bwLabel}`, w - 4, 10);

    // ── Mode label (top-left) ──
    ctx.textAlign = 'left';
    ctx.fillText(mode, 4, 10);
  }

  function drawFftBars(
    ctx: CanvasRenderingContext2D,
    pixels: Uint8Array,
    w: number,
    drawTop: number,
    drawH: number,
    maxVal: number,
    filterCenterX: number,
    filterHalfW: number,
    slopeW: number,
  ): void {
    const len = pixels.length;
    // Target ~2px wide bars with 1px gap
    const barWidth = 2;
    const barGap = 1;
    const barStep = barWidth + barGap;
    const numBars = Math.floor(w / barStep);

    // Initialize smoothed array
    if (!smoothed || smoothed.length !== numBars) {
      smoothed = new Float32Array(numBars);
    }

    for (let i = 0; i < numBars; i++) {
      const x = i * barStep;
      const centerX = x + barWidth / 2;

      // Map bar position to pixel index
      const pixIdx = Math.floor((i / numBars) * len);
      const rawAmp = Math.min(pixels[pixIdx], maxVal) / maxVal;

      // Apply filter mask: attenuate outside passband
      const filterGain = getFilterGain(centerX, drawTop, drawH,
        filterCenterX, filterHalfW, slopeW);

      // Apply contour EQ
      let contourGain = 1.0;
      if (contour > 0) {
        const contourCenterX = (contourFreq / 255) * w;
        const contourWidthPx = w * 0.12;
        const dx = centerX - contourCenterX;
        const gaussian = Math.exp(-(dx * dx) / (2 * contourWidthPx * contourWidthPx));
        const depth = (contour / 255) * 0.8;
        contourGain = 1.0 - depth * gaussian;
      }

      // Apply notch
      let notchGain = 1.0;
      if (manualNotch) {
        const notchX = (notchFreq / 255) * w;
        const notchWidthPx = w * 0.015;
        const dx = centerX - notchX;
        const gaussian = Math.exp(-(dx * dx) / (2 * notchWidthPx * notchWidthPx));
        notchGain = 1.0 - 0.95 * gaussian;
      }

      const targetAmp = rawAmp * filterGain * contourGain * notchGain;

      // Smooth (attack/decay)
      const prev = smoothed[i];
      if (targetAmp > prev) {
        smoothed[i] = prev + (targetAmp - prev) * SMOOTH_ATTACK;
      } else {
        smoothed[i] = prev + (targetAmp - prev) * SMOOTH_DECAY;
      }

      const amp = smoothed[i];
      const barH = amp * drawH;
      if (barH < 1) continue;

      const y = drawTop + drawH - barH;

      // Pixelated: snap to 2px grid vertically
      const snapY = Math.round(y / 2) * 2;
      const snapH = drawTop + drawH - snapY;

      // Color intensity based on amplitude
      const alpha = 0.3 + amp * 0.55;
      ctx.fillStyle = `${DARK_ALPHA} ${alpha})`;
      ctx.fillRect(x, snapY, barWidth, snapH);
    }
  }

  function getFilterGain(
    x: number,
    drawTop: number,
    drawH: number,
    filterCenterX: number,
    filterHalfW: number,
    slopeW: number,
  ): number {
    const dist = Math.abs(x - filterCenterX);
    if (dist <= filterHalfW) return 1.0; // Inside passband
    if (dist >= filterHalfW + slopeW) return 0.04; // Outside — very attenuated
    // On the slope — linear interpolation
    const t = (dist - filterHalfW) / slopeW;
    return 1.0 - t * 0.96;
  }

  function drawNoiseFloor(
    ctx: CanvasRenderingContext2D,
    w: number,
    drawTop: number,
    drawH: number,
  ): void {
    const barWidth = 2;
    const barStep = 3;
    const numBars = Math.floor(w / barStep);
    for (let i = 0; i < numBars; i++) {
      const x = i * barStep;
      const noiseH = (Math.random() * 0.08 + 0.02) * drawH;
      const y = drawTop + drawH - noiseH;
      ctx.fillStyle = `${DARK_ALPHA} 0.12)`;
      ctx.fillRect(x, y, barWidth, noiseH);
    }
  }

  function drawFreqLabels(
    ctx: CanvasRenderingContext2D,
    w: number,
    h: number,
    bottomMargin: number,
  ): void {
    const halfBw = sampleRate / 2;
    ctx.fillStyle = `${DARK_ALPHA} 0.3)`;
    ctx.font = '8px monospace';
    ctx.textAlign = 'center';

    // Frequency ticks every 6 kHz
    const tickStep = 6000;
    for (let freq = tickStep; freq < halfBw; freq += tickStep) {
      const xRight = w / 2 + (freq / halfBw) * (w / 2);
      const xLeft = w / 2 - (freq / halfBw) * (w / 2);
      const label = `${freq / 1000}k`;

      if (xRight < w - 20) {
        ctx.fillText(label, xRight, h - 2);
        // Tick mark
        ctx.fillRect(xRight - 0.5, h - bottomMargin, 1, 3);
      }
      if (xLeft > 20) {
        ctx.fillText(label, xLeft, h - 2);
        ctx.fillRect(xLeft - 0.5, h - bottomMargin, 1, 3);
      }
    }

    // Center label
    ctx.fillText('0', w / 2, h - 2);
  }

  function onVisibilityChange() {
    visible = !document.hidden;
    if (visible && rafId === 0) rafId = requestAnimationFrame(draw);
  }

  onMount(() => {
    onRegisterPush?.((pixels: Uint8Array) => {
      latestPixels = pixels;
    });

    document.addEventListener('visibilitychange', onVisibilityChange);
    rafId = requestAnimationFrame(draw);

    const ro = new ResizeObserver((entries) => {
      const rect = entries[0]?.contentRect;
      if (!rect) return;
      cssWidth = Math.max(1, Math.floor(rect.width));
      cssHeight = Math.max(1, Math.floor(rect.height));
      const dpr = window.devicePixelRatio || 1;
      canvas.width = Math.round(cssWidth * dpr);
      canvas.height = Math.round(cssHeight * dpr);
      const ctx = canvas.getContext('2d');
      ctx?.setTransform(dpr, 0, 0, dpr, 0, 0);
    });
    ro.observe(canvas);

    return () => {
      document.removeEventListener('visibilitychange', onVisibilityChange);
      ro.disconnect();
      cancelAnimationFrame(rafId);
      rafId = 0;
    };
  });
</script>

<div class="amber-af-scope">
  <canvas bind:this={canvas}></canvas>
</div>

<style>
  .amber-af-scope {
    width: 100%;
    height: 100%;
    position: relative;
  }

  canvas {
    display: block;
    width: 100%;
    height: 100%;
    border-radius: 2px;
    image-rendering: pixelated;
  }
</style>
