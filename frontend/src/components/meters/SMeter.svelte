<script lang="ts">
  import { onMount } from 'svelte';
  import { arcPath, polar, valueToAngle } from '../../lib/utils/meter-utils';
  import { createSmoother } from '../../lib/utils/smoothing.svelte';

  interface Props {
    value: number; // raw backend value 0-255
    tx?: boolean;
  }

  let { value, tx = false }: Props = $props();

  const S_UNIT = 17;
  const S9_RAW = 153;

  const width = 860;
  const height = 470;
  const cx = width / 2;
  const cy = 310;
  const outerR = 255;
  const tickInner = 190;
  const tickOuter = 214;
  const labelR = 238;

  const MAIN_MARKS = [
    { value: 1, label: '1', color: '#f8fafc' },
    { value: 3, label: '3', color: '#f8fafc' },
    { value: 5, label: '5', color: '#f8fafc' },
    { value: 7, label: '7', color: '#f8fafc' },
    { value: 9, label: '9', color: '#f8fafc' },
    { value: 10, label: '+20', color: '#ef4444' },
    { value: 11, label: '+40', color: '#ef4444' },
    { value: 12, label: '+60dB', color: '#ef4444' },
  ];

  const ticks = Array.from({ length: 61 }, (_, i) => {
    const scaleValue = (i / 60) * 12;
    return {
      angle: valueToAngle(scaleValue),
      major: i % 5 === 0,
      red: scaleValue > 9,
    };
  });

  // Map raw 0-255 to 0-12 internal scale
  let scaledValue = $derived((() => {
    if (value <= 0) return 0;
    if (value <= S9_RAW) return value / S_UNIT; // 0-9
    const above = value - S9_RAW;
    if (above <= S_UNIT) return 10; // +20dB
    if (above <= 2 * S_UNIT) return 11; // +40dB
    return 12; // +60dB
  })());

  const smoother = createSmoother(0.08, 0.38);

  $effect(() => {
    smoother.update(scaledValue);
  });

  onMount(() => {
    smoother.start();
    return () => smoother.stop();
  });

  let angle = $derived(valueToAngle(smoother.value));
</script>

<svg viewBox="0 0 {width} {height}" class="w-full">
  <defs>
    <filter id="glowW">
      <feGaussianBlur stdDeviation="1.5" result="b" />
      <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
    </filter>
    <filter id="glowR">
      <feGaussianBlur stdDeviation="2" result="b" />
      <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
    </filter>
    <linearGradient id="panel" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#0c0c0d" />
      <stop offset="100%" stop-color="#050505" />
    </linearGradient>
  </defs>

  <rect x="0" y="0" {width} {height} rx="28" fill="url(#panel)" />

  <!-- Main arc: white S0-S9, red S9+ -->
  <path d={arcPath(cx, cy, outerR, -126, -18)} stroke="#f8fafc" stroke-width="5" fill="none" />
  <path d={arcPath(cx, cy, outerR, -18, 18)} stroke="#ef4444" stroke-width="5" fill="none" filter="url(#glowR)" />

  <!-- Tick marks -->
  {#each ticks as t}
    {@const p1 = polar(cx, cy, t.major ? tickInner : tickInner + 10, t.angle)}
    {@const p2 = polar(cx, cy, tickOuter, t.angle)}
    <line
      x1={p1.x} y1={p1.y}
      x2={p2.x} y2={p2.y}
      stroke={t.red ? '#ef4444' : '#f8fafc'}
      stroke-width={t.major ? 3 : 1.4}
      opacity="0.96"
    />
  {/each}

  <!-- Scale labels -->
  {#each MAIN_MARKS as m}
    {@const p = polar(cx, cy, labelR, valueToAngle(m.value))}
    <text
      x={p.x} y={p.y}
      text-anchor="middle"
      dominant-baseline="middle"
      font-size={m.value <= 9 ? 30 : 24}
      font-weight="700"
      fill={m.color}
      filter={m.color === '#ef4444' ? 'url(#glowR)' : 'url(#glowW)'}
    >{m.label}</text>
  {/each}

  <!-- Meter type labels -->
  <text x="64" y="146" font-size="36" font-weight="700" fill="#f8fafc">S</text>
  <text x="60" y="237" font-size="24" font-weight="700" fill="#f8fafc">Po</text>
  <text x="48" y="316" font-size="28" font-weight="700" fill="#f8fafc">SWR</text>
  <text x="93" y="344" font-size="20" font-weight="700" fill="#60a5fa">COMP</text>

  <!-- Inner arcs (Po, SWR, COMP) -->
  <path d={arcPath(cx, cy, 184, -123, 14)} stroke="#e5e7eb" stroke-width="2.2" fill="none" opacity="0.95" />
  <path d={arcPath(cx, cy, 139, -120, 16)} stroke="#e5e7eb" stroke-width="2.1" fill="none" opacity="0.95" />
  <path d={arcPath(cx, cy, 88, -116, 4)} stroke="#60a5fa" stroke-width="3.6" fill="none" opacity="0.95" />
  <path d={arcPath(cx, cy, 88, 4, 16)} stroke="#ef4444" stroke-width="3.6" fill="none" opacity="0.95" />

  <!-- Po labels -->
  {#each [{ a: -111, l: '0' }, { a: -84, l: '10' }, { a: -56, l: '20' }, { a: -28, l: '50' }, { a: 1, l: '100' }, { a: 15, l: '30' }] as m}
    {@const p = polar(cx, cy, 141, m.a)}
    <text x={p.x} y={p.y} font-size="19" font-weight="700" fill="#f8fafc" text-anchor="middle">{m.l}</text>
  {/each}

  <!-- COMP/SWR labels -->
  {#each [{ a: -112, l: '0', c: '#60a5fa' }, { a: -85, l: '10', c: '#60a5fa' }, { a: -58, l: '20', c: '#60a5fa' }, { a: -12, l: '10', c: '#f8fafc' }, { a: 14, l: '16V', c: '#f8fafc' }, { a: 24, l: 'Vd', c: '#f8fafc' }] as m}
    {@const p = polar(cx, cy, 92, m.a)}
    <text x={p.x} y={p.y + 6} font-size="18" font-weight="700" fill={m.c} text-anchor="middle">{m.l}</text>
  {/each}

  <!-- SWR scale numbers -->
  <text x="294" y="349" font-size="18" font-weight="700" fill="#f8fafc">1</text>
  <text x="347" y="349" font-size="18" font-weight="700" fill="#f8fafc">2</text>
  <text x="397" y="349" font-size="18" font-weight="700" fill="#f8fafc">3</text>
  <text x="582" y="346" font-size="24" font-weight="700" fill="#60a5fa">20</text>
  <text x="706" y="345" font-size="22" font-weight="700" fill="#f8fafc">∞</text>
  <text x="732" y="345" font-size="16" font-weight="700" fill="#f8fafc">dB</text>

  <!-- Needle -->
  <g transform="rotate({angle} {cx} {cy})">
    <line x1={cx - 20} y1={cy} x2={cx + 214} y2={cy} stroke="#f8fafc" stroke-width="5" stroke-linecap="round" />
    <polygon points="{cx + 222},{cy} {cx + 197},{cy - 6} {cx + 197},{cy + 6}" fill="#f8fafc" />
  </g>
  <circle {cx} {cy} r="13" fill="#d4d4d8" />
  <circle {cx} {cy} r="5" fill="#09090b" />

  <!-- TX indicator -->
  <g transform="translate(30 300)">
    <rect x="0" y="0" width="72" height="46" rx="8" fill={tx ? '#991b1b' : '#27272a'} stroke={tx ? '#fb7185' : '#52525b'} stroke-width="2" />
    <text x="36" y="30" text-anchor="middle" font-size="28" font-weight="800" fill={tx ? '#fee2e2' : '#d4d4d8'}>TX</text>
  </g>
</svg>

<style>
  svg {
    display: block;
  }
</style>
