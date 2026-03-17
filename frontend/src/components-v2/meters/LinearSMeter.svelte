<script lang="ts">
  import { onMount } from 'svelte';
  import { createSmoother } from '$lib/utils/smoothing.svelte';
  import { rawToSegments, rawToSUnit, rawToDbm, formatDbm } from './smeter-scale';

  interface Props {
    value: number;    // raw 0-255 from CI-V get_s_meter
    compact?: boolean;
    label?: string;
  }

  let { value, compact = false, label }: Props = $props();

  // ── Segment geometry ────────────────────────────────────────────────────────
  const SEG_COUNT = 20;
  const BAR_X = 8;
  const BAR_WIDTH = 484;
  const SEG_GAP = 1;
  const SEG_W = (BAR_WIDTH - (SEG_COUNT - 1) * SEG_GAP) / SEG_COUNT; // ≈ 23.05

  const READOUT_CX = BAR_X + BAR_WIDTH + 8 + 46; // ≈ 554

  function segX(i: number): number {
    return BAR_X + i * (SEG_W + SEG_GAP);
  }

  // x position (from bar left) for a given raw value
  function rawToX(raw: number): number {
    return BAR_X + rawToSegments(raw) * (SEG_W + SEG_GAP);
  }

  // ── Colors ──────────────────────────────────────────────────────────────────
  const ACTIVE_COLORS: ReadonlyArray<string> = [
    '#0D633B', '#0F7445', '#118550', '#12935A', '#14A665',
    '#16BA70', '#18CC79', '#1BE184', '#1EF18C', '#30F7A1',
    '#7CFCE5',
    '#B8A430', '#C49A28', '#D08E20', '#DC7E18',
    '#E57010', '#EB6210', '#F05418', '#F44820', '#F83C28',
  ];

  function dimColor(i: number): string {
    return i < 11 ? '#0A2415' : '#1A1008';
  }

  // ── Label marks ─────────────────────────────────────────────────────────────
  const LABEL_MARKS: ReadonlyArray<{ raw: number; text: string; color: string }> = [
    { raw: 18,  text: 'S1',  color: '#F0F5FA' },
    { raw: 54,  text: 'S3',  color: '#F0F5FA' },
    { raw: 90,  text: 'S5',  color: '#F0F5FA' },
    { raw: 126, text: 'S7',  color: '#F0F5FA' },
    { raw: 162, text: 'S9',  color: '#F0F5FA' },
    { raw: 202, text: '+20', color: '#F2CF4A' },
    { raw: 241, text: '+40', color: '#F08B31' },
    { raw: 255, text: '+60', color: '#F14C42' },
  ];

  // ── Tick marks ──────────────────────────────────────────────────────────────
  // Generate dense ticks: 9 subdivisions between each labeled S-unit position,
  // with the 5th tick (midpoint) slightly taller.
  type TickKind = 'major' | 'mid' | 'minor';
  interface Tick { raw: number; kind: TickKind; color: string }

  function generateTicks(): Tick[] {
    const ticks: Tick[] = [];
    // S-zone anchor points (raw values where labels sit)
    const sAnchors = [0, 18, 36, 54, 72, 90, 108, 126, 144, 162];
    // Over-S9 anchors
    const overAnchors = [162, 182, 202, 222, 241, 255];

    function colorForRaw(raw: number): string {
      if (raw <= 162) return '#F0F5FA';
      if (raw <= 210) return '#F2CF4A';
      if (raw <= 245) return '#F08B31';
      return '#F14C42';
    }

    function addSubdivisions(startRaw: number, endRaw: number) {
      // Major tick at start
      ticks.push({ raw: startRaw, kind: 'major', color: colorForRaw(startRaw) });
      // 9 subdivision ticks between start and end
      const step = (endRaw - startRaw) / 10;
      for (let j = 1; j <= 9; j++) {
        const raw = startRaw + step * j;
        const kind: TickKind = j === 5 ? 'mid' : 'minor';
        ticks.push({ raw, kind, color: colorForRaw(raw) });
      }
    }

    // S0-S9 subdivisions
    for (let i = 0; i < sAnchors.length - 1; i++) {
      addSubdivisions(sAnchors[i], sAnchors[i + 1]);
    }
    // Over-S9 subdivisions
    for (let i = 0; i < overAnchors.length - 1; i++) {
      addSubdivisions(overAnchors[i], overAnchors[i + 1]);
    }
    // Final tick at max
    ticks.push({ raw: 255, kind: 'major', color: '#F14C42' });

    return ticks;
  }

  const TICK_MARKS = generateTicks();

  // ── Layout (switches between full / compact) ────────────────────────────────
  //   When label is present: label at top → meter shifted down
  //   Vertical stacking: [label] → scale labels → ticks → bar
  const LABEL_OFFSET  = $derived(label ? (compact ? 10 : 14) : 0);
  const TAG_Y         = $derived(compact ? 2  : 3);   // label "MAIN"/"SUB" Y
  const TAG_FS        = $derived(compact ? 7  : 8);
  const SCALE_LABEL_Y = $derived((compact ? 2  : 3) + LABEL_OFFSET);
  const SCALE_LABEL_FS = $derived(compact ? 8  : 9);
  const TICK_MAJOR_Y1 = $derived((compact ? 14 : 18) + LABEL_OFFSET);
  const TICK_MAJOR_Y2 = $derived((compact ? 26 : 38) + LABEL_OFFSET);
  const TICK_MID_Y1   = $derived((compact ? 17 : 22) + LABEL_OFFSET);
  const TICK_MID_Y2   = $derived((compact ? 26 : 38) + LABEL_OFFSET);
  const TICK_MINOR_Y1 = $derived((compact ? 20 : 28) + LABEL_OFFSET);
  const TICK_MINOR_Y2 = $derived((compact ? 26 : 38) + LABEL_OFFSET);
  const TRACK_Y       = $derived((compact ? 28 : 40) + LABEL_OFFSET);
  const TRACK_H       = $derived(compact ? 8  : 14);
  // Readout aligned to bar: S-unit centered on bar, dBm just below
  const S_UNIT_Y      = $derived(TRACK_Y - (compact ? 1 : 2));
  const S_UNIT_FS     = $derived(compact ? 12 : 15);
  const DBM_Y         = $derived(TRACK_Y + TRACK_H + (compact ? 1 : 2));
  const DBM_FS        = $derived(compact ? 8  : 9);
  // Bottom padding symmetric to top
  const TOTAL_HEIGHT  = $derived(TRACK_Y + TRACK_H + SCALE_LABEL_Y);

  // ── Smoother ────────────────────────────────────────────────────────────────
  const smoother = createSmoother(0.06, 0.25);

  $effect(() => {
    smoother.update(rawToSegments(value));
  });

  onMount(() => {
    smoother.start();
    return () => smoother.stop();
  });

  // ── Peak hold ───────────────────────────────────────────────────────────────
  const PEAK_HOLD_MS = 1000;   // hold at peak for 1 second
  const PEAK_DECAY   = 0.0195; // segments per frame to drop after hold expires (~30% faster)

  let peakSegs   = $state(0);  // peak position in segments (0-20)
  let peakTime   = $state(0);  // timestamp when peak was set
  let peakFrameId = 0;

  $effect(() => {
    const current = smoother.value;
    if (current >= peakSegs) {
      // New peak — capture it
      peakSegs = current;
      peakTime = performance.now();
    }
  });

  onMount(() => {
    const tickPeak = (now: number) => {
      const current = smoother.value;
      const elapsed = now - peakTime;

      if (current >= peakSegs) {
        // Signal is at or above peak — update peak
        peakSegs = current;
        peakTime = now;
      } else if (elapsed > PEAK_HOLD_MS) {
        // Hold expired — decay toward current level
        peakSegs = Math.max(current, peakSegs - PEAK_DECAY * 16.67); // ~1 seg/sec at 60fps
      }
      // else: holding — do nothing

      peakFrameId = requestAnimationFrame(tickPeak);
    };
    peakFrameId = requestAnimationFrame(tickPeak);
    return () => { if (peakFrameId) cancelAnimationFrame(peakFrameId); };
  });

  // Peak X position for the vertical indicator line
  let peakX = $derived(BAR_X + peakSegs * (SEG_W + SEG_GAP));
  // Only show peak line if it's meaningfully ahead of current bar
  let showPeak = $derived(peakSegs - smoother.value > 0.3);

  // Color of peak line based on zone
  let peakColor = $derived(peakSegs <= 11 ? '#7CFCE5' : peakSegs <= 15 ? '#F2CF4A' : peakSegs <= 18 ? '#F08B31' : '#F14C42');

  // ── Reactive display values ─────────────────────────────────────────────────
  let fullSegs = $derived(Math.floor(smoother.value));
  let fracSeg  = $derived(smoother.value - Math.floor(smoother.value));

  let displaySUnit = $derived(rawToSUnit(value));
  let displayDbm   = $derived(formatDbm(rawToDbm(value)));
</script>

<svg
  viewBox="0 0 600 {TOTAL_HEIGHT}"
  width="100%"
  height="auto"
  preserveAspectRatio="xMidYMid meet"
>
  <!-- Container background -->
  <rect
    x="0" y="0" width="600" height={TOTAL_HEIGHT}
    rx="8"
    fill="#07090D"
    stroke="#1E252C"
    stroke-width="1"
  />

  <!-- Optional label (horizontal, top-left) -->
  {#if label}
    <text
      x="10" y={TAG_Y}
      font-family="'Roboto Mono', monospace"
      font-size={TAG_FS}
      font-weight="700"
      letter-spacing="1.2"
      fill="#6F8196"
      dominant-baseline="text-before-edge"
    >{label}</text>
  {/if}

  <!-- Scale labels -->
  {#each LABEL_MARKS as m}
    <text
      x={rawToX(m.raw)}
      y={SCALE_LABEL_Y}
      font-family="'Roboto Mono', monospace"
      font-size={SCALE_LABEL_FS}
      font-weight="700"
      fill={m.color}
      text-anchor="middle"
      dominant-baseline="text-before-edge"
    >{m.text}</text>
  {/each}

  <!-- Tick marks -->
  {#each TICK_MARKS as t}
    {@const tx = rawToX(t.raw)}
    {@const y1 = t.kind === 'major' ? TICK_MAJOR_Y1 : t.kind === 'mid' ? TICK_MID_Y1 : TICK_MINOR_Y1}
    {@const y2 = t.kind === 'major' ? TICK_MAJOR_Y2 : t.kind === 'mid' ? TICK_MID_Y2 : TICK_MINOR_Y2}
    {@const sw = t.kind === 'major' ? 1.2 : t.kind === 'mid' ? 0.9 : 0.6}
    {@const op = t.kind === 'major' ? 0.9 : t.kind === 'mid' ? 0.6 : 0.35}
    <line
      x1={tx} y1={y1}
      x2={tx} y2={y2}
      stroke={t.color}
      stroke-width={sw}
      opacity={op}
    />
  {/each}

  <!-- Bar track background -->
  <rect
    x={BAR_X} y={TRACK_Y}
    width={BAR_WIDTH} height={TRACK_H}
    rx="1"
    fill="#04070B"
    stroke="#19212B"
    stroke-width="1"
  />

  <!-- Segments -->
  {#each Array(SEG_COUNT) as _, i}
    {@const x = segX(i)}

    <!-- Dim (inactive) -->
    <rect
      {x} y={TRACK_Y + 1}
      width={SEG_W} height={TRACK_H - 2}
      fill={dimColor(i)}
    />

    <!-- Active -->
    {#if i < fullSegs}
      <rect
        {x} y={TRACK_Y + 1}
        width={SEG_W} height={TRACK_H - 2}
        fill={ACTIVE_COLORS[i]}
      />
    {:else if i === fullSegs && fracSeg > 0.01}
      <rect
        {x} y={TRACK_Y + 1}
        width={Math.max(1, SEG_W * fracSeg)} height={TRACK_H - 2}
        fill={ACTIVE_COLORS[i]}
      />
    {/if}
  {/each}

  <!-- Peak hold indicator -->
  {#if showPeak}
    <line
      x1={peakX} y1={TRACK_Y}
      x2={peakX} y2={TRACK_Y + TRACK_H}
      stroke={peakColor}
      stroke-width="2"
      opacity="0.9"
    />
  {/if}

  <!-- Value readout: dBm aligned to bar center, S-unit above it -->
  <text
    x={READOUT_CX}
    y={TRACK_Y - (compact ? 2 : 3)}
    font-family="'Roboto Mono', monospace"
    font-size={S_UNIT_FS}
    font-weight="700"
    fill="#EAF1F8"
    text-anchor="middle"
    dominant-baseline="text-after-edge"
  >{displaySUnit}</text>

  <text
    x={READOUT_CX}
    y={TRACK_Y + TRACK_H / 2}
    font-family="'Roboto Mono', monospace"
    font-size={DBM_FS}
    fill="#6F8196"
    text-anchor="middle"
    dominant-baseline="central"
  >{displayDbm}</text>
</svg>

<style>
  svg {
    display: block;
  }
</style>
