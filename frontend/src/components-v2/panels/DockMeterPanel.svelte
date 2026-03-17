<script lang="ts">
  import { formatAlc, formatPowerWatts, formatSwr, normalize } from './meter-utils';

  interface Props {
    rfPower: number;
    swr: number;
    alc: number;
    txActive: boolean;
  }

  let { rfPower, swr, alc, txActive }: Props = $props();

  const scaleLabels = [
    { label: '0', left: '11%' },
    { label: '10', left: '27%' },
    { label: '25', left: '43%' },
    { label: '50', left: '63%' },
    { label: '100', left: '86%' },
    { label: '%', left: '97%' },
  ] as const;

  let rows = $derived([
    {
      key: 'po',
      label: 'Po',
      value: rfPower,
      display: formatPowerWatts(rfPower),
      fill: 'linear-gradient(90deg, #f4f7fb 0%, #f4f7fb 35%, #e3ae3a 35%, #a63514 100%)',
      track: 'linear-gradient(90deg, rgba(255,255,255,0.08) 0%, rgba(255,255,255,0.08) 35%, rgba(227,174,58,0.14) 35%, rgba(166,53,20,0.2) 100%)',
      valueClass: 'po',
    },
    {
      key: 'swr',
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
      <span class="status-tag swr">SWR {formatSwr(swr)}</span>
      <span class="status-tag tx" data-active={txActive}>{txActive ? 'TX' : 'RX'}</span>
    </div>
  </div>

  <div class="dock-rows">
    {#each rows as row (row.key)}
      <div class="dock-row">
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

  .status-tag.swr {
    border-color: #2c6d3f;
    color: #8ef7a8;
    background: rgba(18, 79, 35, 0.52);
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

  .dock-row {
    display: grid;
    grid-template-columns: 30px minmax(0, 1fr) 48px;
    align-items: center;
    gap: 10px;
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