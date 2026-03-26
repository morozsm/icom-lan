<script lang="ts">
  interface Props {
    value: number;      // Raw S-meter 0-260
    txActive?: boolean;
  }

  let { value, txActive = false }: Props = $props();

  // FTX-1 calibration: 0-255, S9=130, S9+40=240
  const MAX_RAW = 255;
  const SEGMENTS = 192;
  const S9_RAW = 130;
  const S9_SEG = Math.round((S9_RAW / MAX_RAW) * SEGMENTS);

  // Major ticks from FTX-1 calibration table
  const MAJOR_TICKS = [
    { label: '1', raw: 26 },
    { label: '3', raw: 52 },
    { label: '5', raw: 78 },
    { label: '7', raw: 103 },
    { label: '9', raw: 130 },
    { label: '+10', raw: 165 },
    { label: '+20', raw: 200 },
    { label: '+40', raw: 240 },
  ];

  // Medium ticks: S2, S4, S6, S8
  const MEDIUM_TICKS = [
    { raw: 39 },   // S2
    { raw: 65 },   // S4
    { raw: 91 },   // S6
    { raw: 117 },  // S8
  ];

  // Minor ticks: every 4.5 raw units (~quarter S-unit) for dense scale
  const MINOR_TICKS: number[] = [];
  for (let raw = 4; raw < MAX_RAW; raw += 4.5) {
    const r = Math.round(raw);
    // Skip positions that overlap with major/medium ticks
    const isMajor = MAJOR_TICKS.some(t => Math.abs(t.raw - r) < 3);
    const isMedium = MEDIUM_TICKS.some(t => Math.abs(t.raw - r) < 3);
    if (!isMajor && !isMedium) MINOR_TICKS.push(r);
  }

  let filledSegs = $derived(Math.round(Math.min(SEGMENTS, Math.max(0, (value / MAX_RAW) * SEGMENTS))));

  let sReadout = $derived(computeReadout(value));

  // FTX-1 calibration: S0=-54dBm, each S-unit ~6dB, S9=0dBm (relative)
  function computeReadout(raw: number): { sUnit: string; dbm: string } {
    if (raw <= 0) return { sUnit: 'S0', dbm: '-54' };
    if (raw <= S9_RAW) {
      // Linear interpolation: raw 0→S0, raw 130→S9
      const sFloat = (raw / S9_RAW) * 9;
      const sInt = Math.min(9, Math.floor(sFloat));
      const dbm = Math.round(-54 + sFloat * 6);
      return { sUnit: `S${sInt}`, dbm: dbm.toString() };
    }
    // Over S9: 130→S9(0dBm), 165→+10, 200→+20, 240→+40
    const overDb = Math.round(((raw - S9_RAW) / (MAX_RAW - S9_RAW)) * 40);
    return { sUnit: `9+${overDb}`, dbm: `+${overDb}` };
  }
</script>

<div class="lcd-smeter">
  <div class="meter-left">
    <!-- Bargraph -->
    <div class="meter-bar">
      {#each Array(SEGMENTS) as _, i}
        <div
          class="seg"
          class:filled={i < filledSegs}
          class:over-s9={i >= S9_SEG}
          class:tx={txActive}
        ></div>
      {/each}
    </div>

    <!-- Scale below bar -->
    <div class="meter-scale">
      {#each MINOR_TICKS as raw}
        <div class="tick tick-minor" style="left: {(raw / MAX_RAW) * 100}%"></div>
      {/each}
      {#each MEDIUM_TICKS as tick}
        <div class="tick tick-medium" style="left: {(tick.raw / MAX_RAW) * 100}%"></div>
      {/each}
      {#each MAJOR_TICKS as tick}
        <div
          class="tick tick-major"
          class:over-s9={tick.raw > S9_RAW}
          style="left: {(tick.raw / MAX_RAW) * 100}%"
        >
          <span class="tick-label">{tick.label}</span>
        </div>
      {/each}
      <span class="scale-s-label">S</span>
      <span class="scale-db-zone" style="left: {(S9_RAW / MAX_RAW) * 100}%">dB</span>
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
    /* Thick baseline under bargraph — ticks hang from it */
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
