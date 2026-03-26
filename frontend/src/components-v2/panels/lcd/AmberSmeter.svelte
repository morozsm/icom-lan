<script lang="ts">
  import { getCalibrationPoints, getS9Raw, rawToSUnit, rawToDbm } from '../../meters/smeter-scale';

  interface Props {
    value: number;      // Raw S-meter 0-255
    txActive?: boolean;
  }

  let { value, txActive = false }: Props = $props();

  const MAX_RAW = 255;
  const SEGMENTS = 192;

  let s9Raw = $derived(getS9Raw());
  let s9Seg = $derived(Math.round((s9Raw / MAX_RAW) * SEGMENTS));

  // Build ticks from calibration
  let calPoints = $derived(getCalibrationPoints());

  let majorTicks = $derived(
    calPoints
      .filter(p => /^S[13579]$|^S9\+/.test(p.label))
      .map(p => ({ label: p.label.replace('S9+', '+').replace(/^S/, ''), raw: p.raw }))
  );

  let mediumTicks = $derived(
    calPoints
      .filter(p => /^S[2468]$/.test(p.label))
      .map(p => ({ raw: p.raw }))
  );

  // Minor ticks: subdivisions between cal points
  let minorTicks = $derived((() => {
    const ticks: number[] = [];
    for (let raw = 4; raw < MAX_RAW; raw += 4.5) {
      const r = Math.round(raw);
      const isMajor = majorTicks.some((t: any) => Math.abs(t.raw - r) < 3);
      const isMedium = mediumTicks.some((t: any) => Math.abs(t.raw - r) < 3);
      if (!isMajor && !isMedium) ticks.push(r);
    }
    return ticks;
  })());

  let filledSegs = $derived(Math.round(Math.min(SEGMENTS, Math.max(0, (value / MAX_RAW) * SEGMENTS))));

  let sReadout = $derived({
    sUnit: rawToSUnit(value),
    dbm: rawToDbm(value).toString(),
  });
</script>

<div class="lcd-smeter">
  <div class="meter-left">
    <!-- Bargraph -->
    <div class="meter-bar">
      {#each Array(SEGMENTS) as _, i}
        <div
          class="seg"
          class:filled={i < filledSegs}
          class:over-s9={i >= s9Seg}
          class:tx={txActive}
        ></div>
      {/each}
    </div>

    <!-- Scale below bar -->
    <div class="meter-scale">
      {#each minorTicks as raw}
        <div class="tick tick-minor" style="left: {(raw / MAX_RAW) * 100}%"></div>
      {/each}
      {#each mediumTicks as tick}
        <div class="tick tick-medium" style="left: {(tick.raw / MAX_RAW) * 100}%"></div>
      {/each}
      {#each majorTicks as tick}
        <div
          class="tick tick-major"
          class:over-s9={tick.raw > s9Raw}
          style="left: {(tick.raw / MAX_RAW) * 100}%"
        >
          <span class="tick-label">{tick.label}</span>
        </div>
      {/each}
      <span class="scale-s-label">S</span>
      <span class="scale-db-zone" style="left: {(s9Raw / MAX_RAW) * 100}%">dB</span>
    </div>
  </div>

  <!-- Readout -->
  <div class="meter-readout">
    <span class="readout-s">{sReadout.sUnit}</span>
    <span class="readout-dbm">{sReadout.dbm}<span class="readout-unit">dBm</span></span>
  </div>
</div>

<style>
  .lcd-smeter {
    display: flex;
    align-items: stretch;
    gap: 12px;
    width: 100%;
  }

  .meter-left {
    flex: 1 1 0;
    max-width: 88%;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  /* ── Bargraph ── */
  .meter-bar {
    display: flex;
    gap: 0.5px;
    height: 16px;
  }

  .seg {
    flex: 1;
    background: rgba(0, 0, 0, 0.06);
    border-radius: 1px;
  }

  .seg.filled {
    background: rgba(26, 16, 0, 0.8);
  }

  .seg.filled.over-s9 {
    background: rgba(80, 10, 0, 0.9);
  }

  .seg.filled.tx {
    background: rgba(80, 10, 0, 0.85);
  }

  .seg.filled.tx.over-s9 {
    background: rgba(120, 0, 0, 0.95);
  }

  /* ── Scale ── */
  .meter-scale {
    position: relative;
    height: 36px;
    border-top: 4px solid rgba(26, 16, 0, 0.5);
    margin-top: 1px;
  }

  .tick {
    position: absolute;
    top: 0;
  }

  .tick-minor {
    width: 1px;
    height: 6px;
    background: rgba(26, 16, 0, 0.25);
  }

  .tick-medium {
    width: 1.5px;
    height: 10px;
    background: rgba(26, 16, 0, 0.4);
  }

  .tick-major {
    width: 2px;
    height: 13px;
    background: rgba(26, 16, 0, 0.6);
  }

  .tick-major.over-s9 {
    background: rgba(80, 10, 0, 0.6);
  }

  .tick-label {
    position: absolute;
    top: 15px;
    left: 50%;
    transform: translateX(-50%);
    font-family: 'JetBrains Mono', 'Courier New', monospace;
    font-size: 12px;
    font-weight: 700;
    color: rgba(26, 16, 0, 0.6);
    white-space: nowrap;
  }

  .tick-major.over-s9 .tick-label {
    color: rgba(80, 10, 0, 0.65);
  }

  .scale-s-label {
    position: absolute;
    top: 18px;
    left: 0;
    font-family: 'JetBrains Mono', 'Courier New', monospace;
    font-size: 13px;
    font-weight: 700;
    color: rgba(26, 16, 0, 0.45);
  }

  .scale-db-zone {
    position: absolute;
    top: 6px;
    transform: translateX(6px);
    font-family: 'JetBrains Mono', 'Courier New', monospace;
    font-size: 10px;
    font-weight: 700;
    color: rgba(80, 10, 0, 0.4);
  }

  /* ── Readout (right, large) ── */
  .meter-readout {
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    justify-content: center;
    min-width: 80px;
    padding-left: 4px;
  }

  .readout-s {
    font-family: 'DSEG7 Classic', monospace;
    font-weight: bold;
    font-size: 28px;
    color: #1A1000;
    line-height: 1;
  }

  .readout-dbm {
    font-family: 'JetBrains Mono', 'Courier New', monospace;
    font-size: 11px;
    color: rgba(26, 16, 0, 0.45);
    line-height: 1.3;
  }

  .readout-unit {
    margin-left: 2px;
    font-size: 9px;
    color: rgba(26, 16, 0, 0.35);
  }
</style>
