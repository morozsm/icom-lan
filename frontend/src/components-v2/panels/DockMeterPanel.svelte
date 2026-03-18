<script lang="ts">
  import {
    formatAlc,
    formatPowerWatts,
    formatSMeter,
    formatSwr,
    normalize,
    type MeterSource,
  } from './meter-utils';

  interface Props {
    sValue: number;
    rfPower: number;
    swr: number;
    alc: number;
    txActive: boolean;
    meterSource: MeterSource;
    onMeterSourceChange: (v: string) => void;
  }

  let { sValue, rfPower, swr, alc, txActive, meterSource, onMeterSourceChange }: Props = $props();

  const scaleLabels = [
    { label: '0', left: '11%' },
    { label: '10', left: '27%' },
    { label: '25', left: '43%' },
    { label: '50', left: '63%' },
    { label: '100', left: '86%' },
    { label: '%', left: '97%' },
  ] as const;

  let sourceSummary = $derived(
    meterSource === 'S'
      ? { label: 'S', value: formatSMeter(sValue) }
      : meterSource === 'SWR'
        ? { label: 'SWR', value: formatSwr(swr) }
        : { label: 'Po', value: formatPowerWatts(rfPower) },
  );

  let rows = $derived([
    {
      key: 'S',
      label: 'S',
      value: sValue,
      display: formatSMeter(sValue),
      fill: 'linear-gradient(90deg, #65d8ff 0%, #82f2ff 60%, #e6f7ff 100%)',
      track: 'linear-gradient(90deg, rgba(21,82,97,0.38) 0%, rgba(34,116,135,0.26) 60%, rgba(230,247,255,0.14) 100%)',
      valueClass: 's',
    },
    {
      key: 'POWER',
      label: 'Po',
      value: rfPower,
      display: formatPowerWatts(rfPower),
      fill: 'linear-gradient(90deg, #f4f7fb 0%, #f4f7fb 35%, #e3ae3a 35%, #a63514 100%)',
      track: 'linear-gradient(90deg, rgba(255,255,255,0.08) 0%, rgba(255,255,255,0.08) 35%, rgba(227,174,58,0.14) 35%, rgba(166,53,20,0.2) 100%)',
      valueClass: 'po',
    },
    {
      key: 'SWR',
      label: 'SWR',
      value: swr,
      display: formatSwr(swr),
      fill: 'linear-gradient(90deg, #0f5a37 0%, #18c36f 52%, #a48712 68%, #7e180f 100%)',
      track: 'linear-gradient(90deg, rgba(15,90,55,0.35) 0%, rgba(24,195,111,0.22) 52%, rgba(164,135,18,0.16) 68%, rgba(126,24,15,0.2) 100%)',
      valueClass: 'swr',
    },
    {
      key: 'alc',
      label: 'ALC',
      value: alc,
      display: formatAlc(alc).replace('%', ''),
      fill: 'linear-gradient(90deg, #0d4b31 0%, #3e8b29 32%, #e1b43c 58%, #9e2710 100%)',
      track: 'linear-gradient(90deg, rgba(13,75,49,0.34) 0%, rgba(62,139,41,0.2) 32%, rgba(225,180,60,0.17) 58%, rgba(158,39,16,0.2) 100%)',
      valueClass: 'alc',
    },
  ]);
</script>

<article class="dock-meter-panel dock-meter-card">
  <div class="dock-topline">
    <span class="dock-title">METER</span>
    <div class="dock-scale">
      {#each scaleLabels as item (item.label)}
        <span class="dock-scale-label" style:left={item.left}>{item.label}</span>
      {/each}
    </div>
    <div class="dock-status">
      <span class="status-tag source" data-source={meterSource}>{sourceSummary.label} {sourceSummary.value}</span>
      <span class="status-tag tx" data-active={txActive}>{txActive ? 'TX' : 'RX'}</span>
    </div>
  </div>

  <div class="meter-source-selector" role="group" aria-label="Meter source selector">
    <button
      type="button"
      class="meter-source-btn"
      class:active={meterSource === 'S'}
      onclick={() => onMeterSourceChange('S')}
    >S</button>
    <button
      type="button"
      class="meter-source-btn"
      class:active={meterSource === 'SWR'}
      onclick={() => onMeterSourceChange('SWR')}
    >SWR</button>
    <button
      type="button"
      class="meter-source-btn"
      class:active={meterSource === 'POWER'}
      onclick={() => onMeterSourceChange('POWER')}
    >Po</button>
  </div>

  <div class="dock-rows">
    {#each rows as row (row.key)}
      <div class="dock-row" data-active={row.key === meterSource}>
        <span class="dock-row-label">{row.label}</span>
        <div class="dock-bar" style:background={row.track}>
          <div class="dock-bar-fill" style:width={`${normalize(row.value) * 100}%`} style:background={row.fill}></div>
        </div>
        <span class={`dock-row-value ${row.valueClass}`}>{row.display}</span>
      </div>
    {/each}
  </div>
</article>

<style>
  .dock-meter-panel {
    flex: 0 0 420px;
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 8px;
    border: 1px solid #1a2531;
    border-radius: 4px;
    background: linear-gradient(180deg, #091018 0%, #060b12 100%);
    box-sizing: border-box;
  }

  .dock-topline {
    display: grid;
    grid-template-columns: 30px minmax(0, 1fr) auto;
    align-items: center;
    gap: 10px;
  }

  .dock-title,
  .dock-scale-label,
  .status-tag,
  .dock-row-label,
  .dock-row-value {
    font-family: 'Roboto Mono', monospace;
  }

  .dock-title {
    color: #dbe8f7;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.16em;
  }

  .dock-scale {
    position: relative;
    height: 18px;
  }

  .dock-scale-label {
    position: absolute;
    top: 0;
    transform: translateX(-50%);
    color: #d7e3f1;
    font-size: 9px;
    font-weight: 700;
    opacity: 0.92;
  }

  .dock-status {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .status-tag {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-height: 18px;
    padding: 0 8px;
    border: 1px solid transparent;
    border-radius: 4px;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.08em;
  }

  .status-tag.source {
    border-color: #235873;
    color: #92eaff;
    background: rgba(12, 54, 76, 0.52);
  }

  .status-tag.source[data-source='SWR'] {
    border-color: #2c6d3f;
    color: #8ef7a8;
    background: rgba(18, 79, 35, 0.52);
  }

  .status-tag.source[data-source='POWER'] {
    border-color: rgba(195, 146, 48, 0.82);
    color: #ffdca0;
    background: rgba(95, 60, 8, 0.48);
  }

  .status-tag.tx {
    border-color: rgba(189, 59, 29, 0.78);
    color: #ffc4b8;
    background: rgba(93, 20, 12, 0.5);
  }

  .status-tag.tx[data-active='true'] {
    color: #fff2ed;
    background: rgba(132, 25, 13, 0.82);
  }

  .dock-rows {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .meter-source-selector {
    display: inline-flex;
    align-self: flex-start;
    gap: 6px;
  }

  .meter-source-btn {
    min-height: 22px;
    padding: 0 10px;
    border: 1px solid #233241;
    border-radius: 999px;
    background: transparent;
    color: #7f93a7;
    font-family: 'Roboto Mono', monospace;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.08em;
    cursor: pointer;
    transition: border-color 150ms ease, color 150ms ease, background 150ms ease;
  }

  .meter-source-btn:hover {
    border-color: #3d556d;
    color: #c8d8e8;
  }

  .meter-source-btn.active {
    border-color: #5fdcff;
    color: #effaff;
    background: rgba(0, 180, 255, 0.14);
  }

  .dock-row {
    display: grid;
    grid-template-columns: 30px minmax(0, 1fr) 48px;
    align-items: center;
    gap: 10px;
  }

  .dock-row[data-active='true'] .dock-row-label,
  .dock-row[data-active='true'] .dock-row-value {
    color: #eff8ff;
  }

  .dock-row[data-active='true'] .dock-bar {
    border-color: #2d465e;
    box-shadow: inset 0 0 0 1px rgba(111, 194, 255, 0.08);
  }

  .dock-row-label {
    color: #eef4fc;
    font-size: 11px;
    font-weight: 700;
  }

  .dock-bar {
    position: relative;
    height: 8px;
    border: 1px solid #17202a;
    border-radius: 1px;
    overflow: hidden;
    background-size: 100% 100%;
  }

  .dock-bar-fill {
    height: 100%;
    border-right: 1px solid rgba(255, 255, 255, 0.2);
  }

  .dock-row-value {
    text-align: right;
    font-size: 11px;
    font-weight: 700;
  }

  .dock-row-value.po {
    color: #f8fafd;
  }

  .dock-row-value.s {
    color: #9befff;
  }

  .dock-row-value.swr {
    color: #57f0a5;
  }

  .dock-row-value.alc {
    color: #ffba4e;
  }

  @media (max-width: 1200px) {
    .dock-meter-panel {
      flex-basis: 100%;
    }
  }
</style>