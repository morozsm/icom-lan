<script lang="ts">
  import { onMount } from 'svelte';

  interface Props {
    data: Uint8Array | null;
    onRegisterPush?: (fn: (data: Uint8Array) => void) => void;
  }

  let { data, onRegisterPush }: Props = $props();

  let canvas: HTMLCanvasElement;
  let cssWidth = $state(1);
  let cssHeight = $state(1);
  let rafId = 0;
  let visible = true;
  let latestPixels: Uint8Array | null = null;

  // Amber LCD color palette
  const AMBER = 'rgb(255, 140, 0)';
  const AMBER_DIM = 'rgba(255, 140, 0, 0.15)';
  const AMBER_GLOW = 'rgba(255, 140, 0, 0.4)';
  const BG = '#0C0A00';
  const GRID_COLOR = 'rgba(255, 140, 0, 0.06)';

  function draw(): void {
    if (!visible) { rafId = 0; return; }
    const pixels = latestPixels ?? data;
    if (canvas && cssWidth > 0 && cssHeight > 0) {
      const ctx = canvas.getContext('2d');
      if (ctx) renderAmberFft(ctx, pixels, cssWidth, cssHeight);
    }
    rafId = requestAnimationFrame(draw);
  }

  function renderAmberFft(
    ctx: CanvasRenderingContext2D,
    pixels: Uint8Array | null,
    w: number,
    h: number,
  ): void {
    // Clear
    ctx.fillStyle = BG;
    ctx.fillRect(0, 0, w, h);

    // Grid lines (horizontal)
    ctx.strokeStyle = GRID_COLOR;
    ctx.lineWidth = 1;
    for (let y = h * 0.25; y < h; y += h * 0.25) {
      ctx.beginPath();
      ctx.moveTo(0, Math.round(y) + 0.5);
      ctx.lineTo(w, Math.round(y) + 0.5);
      ctx.stroke();
    }

    if (!pixels || pixels.length === 0) {
      // No data — draw flat baseline
      ctx.strokeStyle = AMBER_DIM;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(0, h - 2);
      ctx.lineTo(w, h - 2);
      ctx.stroke();
      return;
    }

    const len = pixels.length;
    const step = w / len;
    const maxVal = 160; // scope data range 0-160

    // Filled area (dim amber)
    ctx.beginPath();
    ctx.moveTo(0, h);
    for (let i = 0; i < len; i++) {
      const x = i * step;
      const amp = Math.min(pixels[i], maxVal) / maxVal;
      const y = h - amp * (h - 4);
      if (i === 0) ctx.lineTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.lineTo(w, h);
    ctx.closePath();
    ctx.fillStyle = 'rgba(255, 140, 0, 0.08)';
    ctx.fill();

    // Main line — "LCD pixel" look with slight glow
    ctx.strokeStyle = AMBER;
    ctx.lineWidth = 1.5;
    ctx.shadowColor = AMBER_GLOW;
    ctx.shadowBlur = 4;
    ctx.beginPath();
    for (let i = 0; i < len; i++) {
      const x = i * step;
      const amp = Math.min(pixels[i], maxVal) / maxVal;
      const y = h - amp * (h - 4);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();
    ctx.shadowBlur = 0;

    // Center marker (tuned freq)
    ctx.strokeStyle = 'rgba(255, 140, 0, 0.3)';
    ctx.lineWidth = 1;
    ctx.setLineDash([3, 3]);
    ctx.beginPath();
    ctx.moveTo(w / 2, 0);
    ctx.lineTo(w / 2, h);
    ctx.stroke();
    ctx.setLineDash([]);

    // Bandwidth label
    ctx.fillStyle = 'rgba(255, 140, 0, 0.3)';
    ctx.font = '9px monospace';
    ctx.textAlign = 'right';
    ctx.fillText('48 kHz', w - 4, 10);
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
    };
  });
</script>

<div class="amber-fft-strip">
  <canvas bind:this={canvas}></canvas>
</div>

<style>
  .amber-fft-strip {
    width: 100%;
    height: 100%;
    position: relative;
  }

  canvas {
    display: block;
    width: 100%;
    height: 100%;
    border-radius: 2px;
  }
</style>
