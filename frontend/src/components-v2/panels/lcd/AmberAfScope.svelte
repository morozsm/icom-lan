<script lang="ts">
  import { onMount } from 'svelte';

  interface Props {
    /** FFT pixel data from AudioFftScope (0-160 range) */
    data: Uint8Array | null;
    /** Register a push callback for streaming updates */
    onRegisterPush?: (fn: (data: Uint8Array) => void) => void;
    /** Filter width — raw index from radio (e.g. 0-36 for FTX-1 SSB) or Hz */
    filterWidth?: number;
    /** Max filter width value (index or Hz) for normalization */
    filterWidthMax?: number;
    /** IF shift in Hz */
    ifShift?: number;
    /** Contour level 0=off, >0=active */
    contour?: number;
    /** Contour center frequency offset (0-255) */
    contourFreq?: number;
    /** Manual notch active */
    manualNotch?: boolean;
    /** Manual notch frequency (0-255 raw) */
    notchFreq?: number;
    /** Audio sample rate */
    sampleRate?: number;
  }

  let {
    data,
    onRegisterPush,
    filterWidth = 13,
    filterWidthMax = 36,
    ifShift = 0,
    contour = 0,
    contourFreq = 128,
    manualNotch = false,
    notchFreq = 128,
    sampleRate = 48000,
  }: Props = $props();

  let canvas: HTMLCanvasElement;
  let cssWidth = $state(1);
  let cssHeight = $state(1);
  let rafId = 0;
  let visible = true;
  let latestPixels: Uint8Array | null = null;

  // LCD dark ink color
  const INK = '#1A1000';
  const INK_A = 'rgba(26, 16, 0,';

  // FFT bar smoothing
  let smoothed: Float32Array | null = null;
  const ATTACK = 0.4;
  const DECAY = 0.15;

  // Trapezoid animation — adaptive lerp toward target filterWidth
  // Big jumps (fast knob turning) → fast animation to keep up
  // Small jumps (fine tuning) → smooth slow animation for polish
  let animatedFilterWidth = $state(filterWidth);
  let prevTargetFilter = filterWidth;
  let adaptiveLerp = 0.12;

  function draw(): void {
    if (!visible) { rafId = 0; return; }
    const pixels = latestPixels ?? data;
    let w = cssWidth;
    let h = cssHeight;
    if ((w <= 1 || h <= 1) && canvas) {
      w = canvas.clientWidth || canvas.parentElement?.clientWidth || 1;
      h = canvas.clientHeight || canvas.parentElement?.clientHeight || 1;
      if (w > 1 && h > 1) {
        cssWidth = w;
        cssHeight = h;
        const dpr = window.devicePixelRatio || 1;
        canvas.width = Math.round(w * dpr);
        canvas.height = Math.round(h * dpr);
        canvas.getContext('2d')?.setTransform(dpr, 0, 0, dpr, 0, 0);
      }
    }
    // Detect how fast the knob is turning
    if (filterWidth !== prevTargetFilter) {
      const jump = Math.abs(filterWidth - prevTargetFilter);
      prevTargetFilter = filterWidth;
      if (jump > 2) {
        // Fast turning — snap instantly, no lag
        animatedFilterWidth = filterWidth;
        adaptiveLerp = 0.5;
      } else {
        // Slow/single step — animate smoothly
        adaptiveLerp = 0.15;
      }
    }

    // Animate trapezoid toward target filter width
    const diff = filterWidth - animatedFilterWidth;
    if (Math.abs(diff) > 0.01) {
      animatedFilterWidth += diff * adaptiveLerp;
    } else {
      animatedFilterWidth = filterWidth;
    }

    if (canvas && w > 1 && h > 1) {
      const ctx = canvas.getContext('2d');
      if (ctx) render(ctx, pixels, w, h);
    }
    rafId = requestAnimationFrame(draw);
  }

  function render(
    ctx: CanvasRenderingContext2D,
    pixels: Uint8Array | null,
    w: number,
    h: number,
  ): void {
    const halfBw = sampleRate / 2;

    // Clear to transparent (amber LCD shines through)
    ctx.clearRect(0, 0, w, h);

    // ── Trapezoid geometry ──
    // The total construct (whiskers + trapezoid) has FIXED outer width.
    // The trapezoid (filter passband) grows/shrinks inside.
    // When filter narrows → trapezoid shrinks, whiskers extend.
    // When filter widens → trapezoid grows, whiskers shrink.
    const cx = w / 2 + (ifShift / halfBw) * (w / 2);

    // Fixed outer endpoints of the whiskers (total construct width)
    const totalHalfW = w * 0.42; // total half-width of entire construct

    // Slope: how much the legs flare outward
    const slopeExtra = h * 0.35;

    // Filter width → top edge width (proportional to max)
    // Use animated value for smooth transitions
    const filterRatio = Math.max(0.05, Math.min(1, animatedFilterWidth / Math.max(1, filterWidthMax)));
    const maxTopHalfW = totalHalfW - slopeExtra;
    const topHalfW = Math.max(h * 0.1, maxTopHalfW * filterRatio);

    // Trapezoid corners
    const tl = cx - topHalfW;
    const tr = cx + topHalfW;
    const bl = cx - topHalfW - slopeExtra;
    const br = cx + topHalfW + slopeExtra;

    // Fixed whisker outer endpoints
    const whiskerLeft = cx - totalHalfW;
    const whiskerRight = cx + totalHalfW;

    // ── Draw trapezoid + whiskers (fixed outer width) ──
    ctx.strokeStyle = INK;
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    // Left whisker: from fixed outer point to bottom-left of trapezoid
    ctx.moveTo(whiskerLeft, h);
    ctx.lineTo(bl, h);
    // Left leg up
    ctx.lineTo(tl, 0);
    // Flat top
    ctx.lineTo(tr, 0);
    // Right leg down
    ctx.lineTo(br, h);
    // Right whisker: from bottom-right of trapezoid to fixed outer point
    ctx.lineTo(whiskerRight, h);
    ctx.stroke();

    // ── Contour (U-shape dip from top) ──
    if (contour > 0) {
      // Map contourFreq (0-255) to position within the top edge
      const contourX = tl + (contourFreq / 255) * (tr - tl);
      const depth = (contour / 255) * h * 0.4;
      const cWidth = (tr - tl) * 0.25; // width of the U

      ctx.strokeStyle = `${INK_A} 0.6)`;
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(contourX - cWidth, 0);
      ctx.quadraticCurveTo(contourX, depth * 2, contourX + cWidth, 0);
      ctx.stroke();
    }

    // ── Manual notch (sharp V from top) ──
    if (manualNotch) {
      const notchX = tl + (notchFreq / 255) * (tr - tl);
      const depth = h * 0.55;
      const nHalfW = (tr - tl) * 0.06;

      ctx.strokeStyle = `${INK_A} 0.75)`;
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(notchX - nHalfW, 0);
      ctx.lineTo(notchX, depth);
      ctx.lineTo(notchX + nHalfW, 0);
      ctx.stroke();
    }

    // ── FFT bars INSIDE trapezoid only ──
    drawFft(ctx, pixels, w, h, cx, topHalfW, slopeExtra);
  }

  function drawFft(
    ctx: CanvasRenderingContext2D,
    pixels: Uint8Array | null,
    w: number,
    h: number,
    cx: number,
    topHalfW: number,
    slopeExtra: number,
  ): void {
    const maxVal = 160;
    const barW = 2;
    const gap = 1;
    const step = barW + gap;

    // Determine bar range: only inside trapezoid at bottom
    const botLeft = cx - topHalfW - slopeExtra;
    const botRight = cx + topHalfW + slopeExtra;
    const startX = Math.max(0, Math.floor(botLeft));
    const endX = Math.min(w, Math.ceil(botRight));
    const numBars = Math.floor((endX - startX) / step);

    if (numBars <= 0) return;

    if (!smoothed || smoothed.length !== numBars) {
      smoothed = new Float32Array(numBars);
    }

    for (let i = 0; i < numBars; i++) {
      const x = startX + i * step;
      const barCenterX = x + barW / 2;

      // Get raw amplitude
      let rawAmp: number;
      if (pixels && pixels.length > 0) {
        // Map bar position to FFT bin
        const frac = (barCenterX - startX) / (endX - startX);
        const pixIdx = Math.floor(frac * pixels.length);
        const clamped = Math.max(0, Math.min(pixels.length - 1, pixIdx));
        rawAmp = Math.min(pixels[clamped], maxVal) / maxVal;
      } else {
        rawAmp = Math.random() * 0.06 + 0.02;
      }

      // Smooth
      const prev = smoothed[i];
      smoothed[i] = rawAmp > prev
        ? prev + (rawAmp - prev) * ATTACK
        : prev + (rawAmp - prev) * DECAY;

      const amp = smoothed[i];

      // Max bar height = clipped by trapezoid at this X
      // At position x, the trapezoid edge is at:
      //   left edge: y = h * (x - botLeft) / (topLeft - botLeft + slopeExtra) ... 
      // Simpler: at x, how high is the trapezoid?
      const distFromCenter = Math.abs(barCenterX - cx);
      // At bottom (y=h): allowed if distFromCenter <= topHalfW + slopeExtra
      // At top (y=0): allowed if distFromCenter <= topHalfW
      // The trapezoid boundary at height y from bottom:
      //   maxDist(y) = topHalfW + slopeExtra * (1 - y/h)
      // Invert: max height for this x:
      //   if distFromCenter <= topHalfW: full height
      //   else: maxY = h * (1 - (distFromCenter - topHalfW) / slopeExtra)
      let maxH: number;
      if (distFromCenter <= topHalfW) {
        maxH = h;
      } else if (distFromCenter <= topHalfW + slopeExtra) {
        maxH = h * (1 - (distFromCenter - topHalfW) / slopeExtra);
      } else {
        continue; // outside trapezoid
      }

      const barH = Math.min(amp * h * 0.85, maxH);
      if (barH < 1) continue;

      const y = h - barH;

      // Snap to 2px grid for pixelated LCD look
      const snapY = Math.round(y / 2) * 2;
      const snapH = h - snapY;

      const alpha = 0.35 + amp * 0.5;
      ctx.fillStyle = `${INK_A} ${alpha})`;
      ctx.fillRect(x, snapY, barW, snapH);
    }
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
      canvas.getContext('2d')?.setTransform(dpr, 0, 0, dpr, 0, 0);
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

<div class="af-scope">
  <canvas bind:this={canvas}></canvas>
</div>

<style>
  .af-scope {
    width: 100%;
    height: 100%;
    position: relative;
  }

  canvas {
    display: block;
    width: 100%;
    height: 100%;
  }
</style>
