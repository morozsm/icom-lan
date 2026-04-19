<!--
  AmberTelemetryStrip — 3 compact tiles (VD · TEMP · ID) with inline
  sparklines showing the last ~30 samples. Mounted in the LCD aux
  grid-area (#894 reserved the slot; #887 twin-skin lays the cockpit).

  Data source: `ServerState.vdMeter` / `idMeter` and `tempMeter`
  (when the backend surfaces it — not all rigs do). Missing fields
  produce a "—" placeholder tile but keep the strip visible so the
  grid row doesn't collapse under the user.

  Sample history is kept per-tile in a local ring buffer (no store).
  `$effect` watches the live values and pushes new samples when they
  change materially (avoids building buffers of identical readings).

  Part of #837 / epic #818 LCD telemetry strip.
-->
<script lang="ts">
  import { radio } from '$lib/stores/radio.svelte';
  import AmberSparkline from './AmberSparkline.svelte';

  const BUFFER_SIZE = 30;
  const PUSH_EPSILON = 1;    // ignore changes < 1 raw unit (stabilises sparklines)

  let radioState = $derived(radio.current);

  // Raw readings (nullable — backend may not provide all three).
  let vdRaw = $derived<number | null>(radioState?.vdMeter ?? null);
  let idRaw = $derived<number | null>(radioState?.idMeter ?? null);
  // TEMP isn't yet on ServerState; read defensively for forward compat.
  let tempRaw = $derived<number | null>(
    (radioState as { tempMeter?: number } | null)?.tempMeter ?? null,
  );

  // Local ring buffers — $state so Svelte tracks them as arrays.
  let vdHistory = $state<number[]>([]);
  let idHistory = $state<number[]>([]);
  let tempHistory = $state<number[]>([]);

  function pushBuffer(buf: number[], value: number): number[] {
    const last = buf.length ? buf[buf.length - 1] : null;
    if (last !== null && Math.abs(value - last) < PUSH_EPSILON) return buf;
    const next = buf.length >= BUFFER_SIZE ? buf.slice(1) : [...buf];
    next.push(value);
    return next;
  }

  $effect(() => {
    if (vdRaw === null) return;
    vdHistory = pushBuffer(vdHistory, vdRaw);
  });
  $effect(() => {
    if (idRaw === null) return;
    idHistory = pushBuffer(idHistory, idRaw);
  });
  $effect(() => {
    if (tempRaw === null) return;
    tempHistory = pushBuffer(tempHistory, tempRaw);
  });

  // Display conversions — rigs report raw 0..255; label text is best-effort.
  function vdLabel(raw: number | null): string {
    if (raw === null) return '—';
    // Rough linear mapping 0..255 → 0..16 V. Adjust per rig in a followup.
    return `${((raw / 255) * 16).toFixed(1)}V`;
  }
  function idLabel(raw: number | null): string {
    if (raw === null) return '—';
    return `${((raw / 255) * 25).toFixed(1)}A`;
  }
  function tempLabel(raw: number | null): string {
    if (raw === null) return '—';
    return `${Math.round((raw / 255) * 100)}°`;
  }
</script>

<div class="amber-telemetry-strip">
  <div class="tile" class:tile-empty={vdRaw === null}>
    <div class="tile-head">
      <span class="tile-tag">VD</span>
      <span class="tile-value">{vdLabel(vdRaw)}</span>
    </div>
    <div class="tile-spark">
      <AmberSparkline data={vdHistory} min={0} max={255} />
    </div>
  </div>

  <div class="tile" class:tile-empty={tempRaw === null}>
    <div class="tile-head">
      <span class="tile-tag">TEMP</span>
      <span class="tile-value">{tempLabel(tempRaw)}</span>
    </div>
    <div class="tile-spark">
      <AmberSparkline data={tempHistory} min={0} max={255} />
    </div>
  </div>

  <div class="tile" class:tile-empty={idRaw === null}>
    <div class="tile-head">
      <span class="tile-tag">ID</span>
      <span class="tile-value">{idLabel(idRaw)}</span>
    </div>
    <div class="tile-spark">
      <AmberSparkline data={idHistory} min={0} max={255} />
    </div>
  </div>
</div>

<style>
  .amber-telemetry-strip {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 6px;
    width: 100%;
    height: 100%;
    min-height: 22px;
    /* Uses the ambient warm-amber ink via --lcd-alpha-active from .lcd-screen. */
    color: rgba(26, 16, 0, var(--lcd-alpha-active));
  }

  .tile {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 0 4px;
    min-width: 0;
    border: 1px solid rgba(26, 16, 0, calc(var(--lcd-alpha-active) * 0.2));
    border-radius: 3px;
    overflow: hidden;
  }

  .tile-empty {
    opacity: 0.45;
  }

  .tile-head {
    display: flex;
    align-items: baseline;
    gap: 3px;
    flex-shrink: 0;
    font-family: 'JetBrains Mono', 'Courier New', monospace;
  }

  .tile-tag {
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.08em;
    color: rgba(26, 16, 0, calc(var(--lcd-alpha-active) * 0.6));
  }

  .tile-value {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.02em;
  }

  .tile-spark {
    flex: 1;
    min-width: 0;
    height: 14px;
  }
</style>
