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

  // Auto-gain AGC for scope display
  let agcPeak = 40; // smoothed peak value
  const AGC_ATTACK = 0.3;  // fast attack (signal appears)
  const AGC_RELEASE = 0.02; // slow release (signal fades)

  // Trapezoid animation — adaptive lerp toward target filterWidth
  // Big jumps (fast knob turning) → fast animation to keep up
  // Small jumps (fine tuning) → smooth slow animation for polish
  let animatedFilterWidth = $state(filterWidth);
  let prevTargetFilter = filterWidth;
  let adaptiveLerp = 0.12;

  let _drawCount = 0;
  function draw(): void {
    if (!visible) { rafId = 0; return; }
    const pixels = latestPixels ?? data;
    if (_drawCount < 3) {
      _drawCount++;
      console.log(`[AF-SCOPE draw#${_drawCount}] pixels=${pixels ? pixels.length : 'null'} latestPixels=${latestPixels ? latestPixels.length : 'null'} data=${data ? data.length : 'null'} w=${cssWidth} h=${cssHeight} canvas=${!!canvas}`);
    }
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
    const labelH = 22; // space for filter width label at top
    const trapTop = labelH;
    const trapH = h - labelH;

    // Clear to transparent (amber LCD shines through)
    ctx.clearRect(0, 0, w, h);

    // ── Trapezoid geometry ──
    // The total construct (whiskers + trapezoid) has FIXED outer width.
    // The trapezoid (filter passband) grows/shrinks inside.
    // When filter narrows → trapezoid shrinks, whiskers extend.
    // When filter widens → trapezoid grows, whiskers shrink.
    const cx = w / 2 + (ifShift / halfBw) * (w / 2);

    // Fixed outer endpoints of the whiskers (total construct width)
    const totalHalfW = w * 0.42;

    // Slope: how much the legs flare outward
    const slopeExtra = trapH * 0.35;

    // Filter width → top edge width (proportional to max)
    const filterRatio = Math.max(0.05, Math.min(1, animatedFilterWidth / Math.max(1, filterWidthMax)));
    const maxTopHalfW = totalHalfW - slopeExtra;
    const topHalfW = Math.max(trapH * 0.1, maxTopHalfW * filterRatio);

    // Trapezoid corners (in trapezoid zone: trapTop → h)
    const tl = cx - topHalfW;
    const tr = cx + topHalfW;
    const bl = cx - topHalfW - slopeExtra;
    const br = cx + topHalfW + slopeExtra;

    // Fixed whisker outer endpoints
    const whiskerLeft = cx - totalHalfW;
    const whiskerRight = cx + totalHalfW;

    // ── Filter width label: "Filter: 3000Hz" ──
    const filterHz = Math.round(200 + (animatedFilterWidth / 36) * 3800);
    ctx.fillStyle = INK;
    ctx.textAlign = 'center';
    // "Filter:" in regular font (slightly smaller than digits)
    ctx.font = "bold 12px 'JetBrains Mono', 'Courier New', monospace";
    const prefix = 'Filter: ';
    const prefixW = ctx.measureText(prefix).width;
    // Number in segment font
    ctx.font = "bold 14px 'DSEG7 Classic', monospace";
    const numStr = String(filterHz);
    const numW = ctx.measureText(numStr).width;
    // "Hz" in regular font
    ctx.font = "bold 12px 'JetBrains Mono', 'Courier New', monospace";
    const hzW = ctx.measureText('Hz').width;
    const totalW = prefixW + numW + hzW;
    const startX = cx - totalW / 2;
    const baseY = labelH - 6;
    // Draw prefix
    ctx.textAlign = 'left';
    ctx.font = "bold 12px 'JetBrains Mono', 'Courier New', monospace";
    ctx.fillText(prefix, startX, baseY);
    // Draw number (segment font)
    ctx.font = "bold 14px 'DSEG7 Classic', monospace";
    ctx.fillText(numStr, startX + prefixW, baseY);
    // Draw "Hz"
    ctx.font = "bold 12px 'JetBrains Mono', 'Courier New', monospace";
    ctx.fillStyle = `${INK_A} 0.6)`;
    ctx.fillText('Hz', startX + prefixW + numW, baseY);

    // ── Draw trapezoid + whiskers (thick LCD ink) ──
    ctx.strokeStyle = INK;
    ctx.lineWidth = 2.5;
    ctx.beginPath();
    ctx.moveTo(whiskerLeft, h);
    ctx.lineTo(bl, h);
    ctx.lineTo(tl, trapTop);
    ctx.lineTo(tr, trapTop);
    ctx.lineTo(br, h);
    ctx.lineTo(whiskerRight, h);
    ctx.stroke();

    // ── Contour (U-shape dip from top of trapezoid) ──
    if (contour > 0) {
      const contourX = tl + (contourFreq / 255) * (tr - tl);
      const depth = (contour / 255) * trapH * 0.4;
      const cWidth = (tr - tl) * 0.25;

      ctx.strokeStyle = `${INK_A} 0.6)`;
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(contourX - cWidth, trapTop);
      ctx.quadraticCurveTo(contourX, trapTop + depth * 2, contourX + cWidth, trapTop);
      ctx.stroke();
    }

    // ── Manual notch (sharp V from top of trapezoid) ──
    if (manualNotch) {
      const notchX = tl + (notchFreq / 255) * (tr - tl);
      const depth = trapH * 0.55;
      const nHalfW = (tr - tl) * 0.06;

      ctx.strokeStyle = `${INK_A} 0.75)`;
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(notchX - nHalfW, trapTop);
      ctx.lineTo(notchX, trapTop + depth);
      ctx.lineTo(notchX + nHalfW, trapTop);
      ctx.stroke();
    }

    // ── Auto-gain AGC ──
    const nyquist = sampleRate / 2;
    const passbandFrac = Math.min(1, filterHz / nyquist);
    let peakVal = 1;
    if (pixels && pixels.length > 0) {
      const dcIdx = Math.floor(pixels.length / 2);
      const endBin = dcIdx + Math.ceil(passbandFrac * (pixels.length - dcIdx));
      for (let j = dcIdx; j < endBin && j < pixels.length; j++) {
        if (pixels[j] > peakVal) peakVal = pixels[j];
      }
    }
    if (peakVal > agcPeak) {
      agcPeak += (peakVal - agcPeak) * AGC_ATTACK;
    } else {
      agcPeak += (peakVal - agcPeak) * AGC_RELEASE;
    }
    agcPeak = Math.max(10, agcPeak);
    const gain = 160 / agcPeak;

    // ── FFT bars INSIDE trapezoid — only passband portion of spectrum ──
    drawFft(ctx, pixels, w, h, trapTop, trapH, cx, topHalfW, slopeExtra, filterHz, gain);
  }

  function drawFft(
    ctx: CanvasRenderingContext2D,
    pixels: Uint8Array | null,
    w: number,
    h: number,
    trapTop: number,
    trapH: number,
    cx: number,
    topHalfW: number,
    slopeExtra: number,
    passbandHz: number,
    gain: number,
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

    // Only show FFT bins within the passband (0 → passbandHz)
    const nyquist = sampleRate / 2;
    const passbandFrac = Math.min(1, passbandHz / nyquist);

    // DEBUG: log first frame's data
    if (pixels && pixels.length > 0 && !drawFft._logged) {
      drawFft._logged = true;
      const dcIdx = Math.floor(pixels.length / 2);
      const first20pos = Array.from(pixels.slice(dcIdx, dcIdx + 20));
      const first20neg = Array.from(pixels.slice(0, 20));
      const mid20 = Array.from(pixels.slice(dcIdx - 10, dcIdx + 10));
      const max = Math.max(...Array.from(pixels));
      const avg = Array.from(pixels).reduce((a, b) => a + b, 0) / pixels.length;
      console.log(`[AF-SCOPE] len=${pixels.length} dcIdx=${dcIdx} max=${max} avg=${avg.toFixed(1)}`);
      console.log(`[AF-SCOPE] first20neg=`, first20neg);
      console.log(`[AF-SCOPE] around_dc=`, mid20);
      console.log(`[AF-SCOPE] first20pos=`, first20pos);
      console.log(`[AF-SCOPE] passbandHz=${passbandHz} passbandFrac=${passbandFrac.toFixed(4)} numBars=${numBars}`);
    }

    for (let i = 0; i < numBars; i++) {
      const x = startX + i * step;
      const barCenterX = x + barW / 2;

      // Get raw amplitude — map bar position to passband FFT bins only
      let rawAmp: number;
      if (pixels && pixels.length > 0) {
        // pixels[] is symmetric: [-Nyquist ... DC ... +Nyquist]
        // DC is at center (pixels.length / 2), positive freqs are right half
        const dcIdx = Math.floor(pixels.length / 2);
        const positiveLen = pixels.length - dcIdx; // DC → Nyquist

        // Bar position 0→1 within trapezoid
        const barFrac = (barCenterX - startX) / (endX - startX);
        // Map to positive-side FFT bin within passband only
        const pixIdx = dcIdx + Math.floor(barFrac * passbandFrac * positiveLen);
        const clamped = Math.max(dcIdx, Math.min(pixels.length - 1, pixIdx));
        rawAmp = Math.min(pixels[clamped] * gain, maxVal) / maxVal;
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
      const distFromCenter = Math.abs(barCenterX - cx);
      let maxBarH: number;
      if (distFromCenter <= topHalfW) {
        maxBarH = trapH;
      } else if (distFromCenter <= topHalfW + slopeExtra) {
        maxBarH = trapH * (1 - (distFromCenter - topHalfW) / slopeExtra);
      } else {
        continue;
      }

      const barH = Math.min(amp * trapH * 0.85, maxBarH);
      if (barH < 1) continue;

      const y = h - barH;
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
