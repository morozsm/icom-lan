<script lang="ts">
  /**
   * AmberIndStrip — reusable indicator (status token) strip for LCD skins.
   *
   * Indicator taxonomy (zone assignment):
   *
   * | ID       | Zone    | Notes                                         |
   * |----------|---------|-----------------------------------------------|
   * | tx       | global  | PTT active — radio-wide                       |
   * | vox      | global  | VOX mode — radio-wide                         |
   * | proc     | global  | Compressor/speech proc — radio-wide            |
   * | atu      | global  | Auto-tuner active/tuning — radio-wide         |
   * | split    | global  | Split TX/RX — radio-wide                      |
   * | lock     | global  | Dial lock — radio-wide                        |
   * | data     | global  | Data mode — issue #892 lists as global        |
   * | ipPlus   | global  | IP+ HW filter — radio-wide hardware option    |
   * | nb       | perVfo  | Noise blanker — per-receiver                   |
   * | nr       | perVfo  | Noise reduction — per-receiver                 |
   * | notch    | perVfo  | Manual notch filter — per-receiver            |
   * | anf      | perVfo  | Auto notch filter — per-receiver              |
   * | cont     | perVfo  | Contour filter — per-receiver                 |
   * | att      | perVfo  | Attenuator — per-receiver                     |
   * | pre      | perVfo  | Preamp / IPO / AMP1 / AMP2 — per-receiver    |
   * | digisel  | perVfo  | DIGI-SEL filter — per-receiver on IC-7610    |
   * | rfg      | perVfo  | RF gain below max — per-receiver              |
   * | sql      | perVfo  | Squelch active — per-receiver                 |
   * | agc      | perVfo  | AGC mode label — always shown, per-receiver   |
   * | rit      | perVfo  | RIT offset (global state, shown in VFO A)     |
   */

  export type IndTokenId =
    | 'tx' | 'vox' | 'proc' | 'atu' | 'split' | 'lock' | 'data' | 'ipPlus'
    | 'nb' | 'nr' | 'notch' | 'anf' | 'cont' | 'att' | 'pre'
    | 'digisel' | 'rfg' | 'sql' | 'agc' | 'rit';

  export interface IndToken {
    id: IndTokenId;
    label: string;
    active: boolean;
    /** If set, the token is only rendered when this capability is present. */
    capability?: string;
    /** 'tx' → red TX styling; 'tuning' → blinking animation */
    variant?: 'tx' | 'tuning';
  }

  interface Props {
    zone: 'global' | 'perVfo';
    tokens: IndToken[];
  }

  let { zone, tokens }: Props = $props();
</script>

<div class="lcd-ind-strip" class:zone-global={zone === 'global'} class:zone-per-vfo={zone === 'perVfo'}>
  {#each tokens as token (token.id)}
    <span
      class="lcd-ind"
      class:active={token.active}
      class:ind-tx={token.variant === 'tx'}
      class:ind-tuning={token.variant === 'tuning'}
    >{token.label}</span>
  {/each}
</div>

<style>
  .lcd-ind-strip {
    display: flex;
    gap: 6px;
    align-items: center;
    flex-wrap: wrap;
    position: relative;
    z-index: 2;
    padding: 2px 0;
    overflow: hidden;
  }

  /* Global strip: horizontal flex-wrap, full-width */
  .zone-global {
    flex-direction: row;
    flex-shrink: 1;
  }

  /* Per-VFO strip: compact horizontal, fits inside cockpit column */
  .zone-per-vfo {
    flex-direction: row;
    flex-shrink: 1;
    gap: 5px;
  }

  .lcd-ind {
    font-family: 'JetBrains Mono', 'Courier New', monospace;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.5px;
    color: rgba(26, 16, 0, var(--lcd-alpha-inactive));
    border: 1.5px solid rgba(26, 16, 0, var(--lcd-alpha-ghost));
    border-radius: 3px;
    padding: 1px 5px;
    user-select: none;
    white-space: nowrap;
  }

  .lcd-ind.active {
    color: rgba(26, 16, 0, var(--lcd-alpha-active));
    border-color: rgba(26, 16, 0, calc(var(--lcd-alpha-active) * 0.4));
  }

  /* TX indicator: red accent */
  .lcd-ind.ind-tx {
    color: #5A0800;
    border-color: rgba(90, 8, 0, 0.5);
    font-size: 13px;
  }

  /* ATU TUNE: blink while tuning */
  .lcd-ind.ind-tuning {
    animation: lcd-blink 0.6s steps(1) infinite;
  }

  @keyframes lcd-blink {
    0%, 50% { opacity: 1; }
    51%, 100% { opacity: 0.15; }
  }
</style>
