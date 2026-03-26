<script lang="ts">
  interface Props {
    value: number;      // Raw S-meter 0-260
    txActive?: boolean;
  }

  let { value, txActive = false }: Props = $props();

  // S-meter calibration: S0=0, S1=18 ... S9=162, +10=180, +20=198, +40=234, +60=260
  const MAX_RAW = 260;
  const SEGMENTS = 40;
  const S9_RAW = 162;
  const S9_SEG = Math.round((S9_RAW / MAX_RAW) * SEGMENTS);

  // Major tick marks with labels
  const MAJOR_TICKS = [
    { label: '1', raw: 18 },
    { label: '2', raw: 36 },
    { label: '3', raw: 54 },
    { label: '4', raw: 72 },
    { label: '5', raw: 90 },
    { label: '6', raw: 108 },
    { label: '7', raw: 126 },
    { label: '8', raw: 144 },
    { label: '9', raw: 162 },
    { label: '+20', raw: 198 },
    { label: '+40', raw: 234 },
    { label: '+60', raw: 260 },
  ];

  // Minor ticks (between majors, no label)
  const MINOR_TICKS = [
    9, 27, 45, 63, 81, 99, 117, 135, 153, 171, 189, 207, 216, 225, 243, 252,
  ];

  let filledSegs = $derived(Math.round(Math.min(SEGMENTS, Math.max(0, (value / MAX_RAW) * SEGMENTS))));

  // S-unit and dBm readout
  let sReadout = $derived(computeReadout(value));

  function computeReadout(raw: number): { sUnit: string; dbm: string } {
    if (raw <= 0) return { sUnit: 'S0', dbm: '-127' };
    // S1=-121, S2=-115, S3=-109 ... S9=-73, each S-unit = 6 dB
    const sFloat = Math.min(9, (raw / S9_RAW) * 9);
    const sInt = Math.floor(sFloat);
    if (raw <= S9_RAW) {
      const dbm = -127 + sInt * 6;
      return { sUnit: `S${sInt}`, dbm: dbm.toString() };
    }
    // Over S9: +dB
    const overDb = Math.round(((raw - S9_RAW) / (MAX_RAW - S9_RAW)) * 60);
    return { sUnit: `S9+${overDb}`, dbm: (-73 + overDb).toString() };
  }
</script>

<div class="lcd-smeter">
  <div class="meter-left">
    <!-- Bargraph segments -->
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

    <!-- Scale with tick marks below the bar -->
    <div class="meter-scale">
    <!-- Minor ticks -->
    {#each MINOR_TICKS as raw}
      <div class="tick tick-minor" style="left: {(raw / MAX_RAW) * 100}%"></div>
    {/each}
    <!-- Major ticks + labels -->
    {#each MAJOR_TICKS as tick}
      <div
        class="tick tick-major"
        class:over-s9={tick.raw > S9_RAW}
        style="left: {(tick.raw / MAX_RAW) * 100}%"
      >
        <span class="tick-label">{tick.label}</span>
      </div>
    {/each}
    <!-- S prefix at the start -->
    <span class="scale-prefix">S</span>
    <!-- dB label at over-S9 zone start -->
    <span class="scale-db-label" style="left: {(S9_RAW / MAX_RAW) * 100}%">dB</span>
    </div>
  </div>

  <!-- Readout: S-unit + dBm -->
  <div class="meter-readout">
    <span class="readout-s">{sReadout.sUnit}</span>
    <span class="readout-dbm">{sReadout.dbm} dBm</span>
  </div>
</div>

<style>
  .lcd-smeter {
    display: flex;
    align-items: stretch;
    gap: 8px;
    width: 100%;
  }

  /* ── Bargraph + scale wrapper ── */
  .meter-left {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 0;
  }

  .meter-bar {
    display: flex;
    gap: 1.5px;
    height: 14px;
  }

  .seg {
    flex: 1;
    background: rgba(0, 0, 0, 0.06);
    border-radius: 1px;
  }

  .seg.filled {
    background: rgba(26, 16, 0, 0.75);
  }

  .seg.filled.over-s9 {
    background: rgba(80, 10, 0, 0.85);
  }

  .seg.filled.tx {
    background: rgba(80, 10, 0, 0.8);
  }

  .seg.filled.tx.over-s9 {
    background: rgba(120, 0, 0, 0.9);
  }

  /* ── Scale below bar ── */
  .meter-scale {
    position: relative;
    height: 22px;
    flex: 1;
    min-width: 0;
  }

  .tick {
    position: absolute;
    top: 0;
  }

  .tick-minor {
    width: 1px;
    height: 4px;
    background: rgba(26, 16, 0, 0.25);
  }

  .tick-major {
    width: 1px;
    height: 7px;
    background: rgba(26, 16, 0, 0.45);
  }

  .tick-major.over-s9 {
    background: rgba(80, 10, 0, 0.5);
  }

  .tick-label {
    position: absolute;
    top: 9px;
    left: 50%;
    transform: translateX(-50%);
    font-family: 'JetBrains Mono', 'Courier New', monospace;
    font-size: 10px;
    font-weight: 600;
    color: rgba(26, 16, 0, 0.5);
    white-space: nowrap;
  }

  .tick-major.over-s9 .tick-label {
    color: rgba(80, 10, 0, 0.6);
  }

  .scale-prefix {
    position: absolute;
    top: 8px;
    left: -2px;
    font-family: 'JetBrains Mono', 'Courier New', monospace;
    font-size: 11px;
    font-weight: 700;
    color: rgba(26, 16, 0, 0.4);
  }

  .scale-db-label {
    position: absolute;
    top: 0px;
    transform: translateX(4px);
    font-family: 'JetBrains Mono', 'Courier New', monospace;
    font-size: 9px;
    font-weight: 600;
    color: rgba(80, 10, 0, 0.4);
  }

  /* ── Readout (right side, large) ── */
  .meter-readout {
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    justify-content: center;
    min-width: 64px;
  }

  .readout-s {
    font-family: 'DSEG7 Classic', monospace;
    font-weight: bold;
    font-size: 22px;
    color: #1A1000;
    line-height: 1;
  }

  .readout-dbm {
    font-family: 'JetBrains Mono', 'Courier New', monospace;
    font-size: 10px;
    color: rgba(26, 16, 0, 0.45);
    line-height: 1.2;
  }
</style>
