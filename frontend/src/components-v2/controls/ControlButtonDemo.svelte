<script lang="ts">
  import '../theme/index';
  import './control-button.css';
  import { DotButton, FillButton, HardwareButton, HardwarePlainButton, StatusIndicator } from '$lib/Button';
  import { PRESET_MAPPINGS, type RoleMapping } from '$lib/Button/roleMapping';

  const indicatorStyles = [
    { value: 'ring', label: 'Ring' },
    { value: 'dot', label: 'Dot' },
    { value: 'edge-bottom', label: 'Edge Bottom' },
    { value: 'edge-left', label: 'Edge Left' },
    { value: 'fill', label: 'Fill' },
  ] as const;

  const indicatorColors = ['cyan', 'green', 'amber', 'red', 'orange', 'white'] as const;

  const hardwareButtons = [
    { style: 'edge-left', color: 'cyan', label: 'NB' },
    { style: 'edge-left', color: 'amber', label: 'NR' },
    { style: 'edge-bottom', color: 'green', label: 'TUNE' },
    { style: 'dot', color: 'red', label: 'VOX' },
    { style: 'dot', color: 'green', label: 'MUTE' },
    { style: 'dot', color: 'amber', label: 'MON' },
    { style: 'edge-bottom', color: 'cyan', label: 'LOCK' },
    { style: 'edge-left', color: 'orange', label: 'SPLIT' },
  ] as const;

  // Reactive toggle state for all demo buttons
  let styleActive: Record<string, boolean> = $state({});
  let dotActive: Record<string, boolean> = $state({});
  let dotLayoutActive: Record<string, boolean> = $state({});
  let hwActive: Record<string, boolean> = $state({});
  
  // Component library states
  let compDotStates: Record<string, boolean> = $state({});
  let compFillStates: Record<string, boolean> = $state({});
  let compHwStates: Record<string, boolean> = $state({});
  let compPlainStates: Record<string, boolean> = $state({});

  // action-button role — momentary commands, no sustained on/off state
  const actionButtons = [
    { label: 'CLEAR',     color: 'amber'  },
    { label: 'TUNE',      color: 'green'  },
    { label: 'AUTO TUNE', color: 'cyan'   },
    { label: 'RESET',     color: 'red'    },
    { label: 'CENTER',    color: 'orange' },
    { label: 'SCAN',      color: 'cyan'   },
  ] as const;
  let actionFlash: Record<string, boolean> = $state({});

  function fireAction(key: string) {
    actionFlash[key] = true;
    setTimeout(() => { actionFlash[key] = false; }, 180);
  }

  // StatusBadge migration reference — status-toggle role across multiple visual families
  const statusToggleButtons = [
    { label: 'NB',   color: 'orange' },
    { label: 'ATU',  color: 'green'  },
    { label: 'VOX',  color: 'orange' },
    { label: 'COMP', color: 'orange' },
    { label: 'MON',  color: 'orange' },
    { label: 'RIT',  color: 'cyan'   },
    { label: 'XIT',  color: 'orange' },
    { label: 'NR',   color: 'cyan'   },
    { label: 'LOCK', color: 'orange' },
  ] as const;
  let fillToggleStates: Record<string, boolean> = $state({});
  let fillCompactToggleStates: Record<string, boolean> = $state({});
  let dotToggleStates: Record<string, boolean> = $state({});
  let plainToggleStates: Record<string, boolean> = $state({});

  function toggle(map: Record<string, boolean>, key: string) {
    map[key] = !map[key];
  }

  // Theme mapping proof — role → family preset selector
  let activeMapping: RoleMapping = $state(PRESET_MAPPINGS[0]);
  let mappingToggleStates: Record<string, boolean> = $state({});
  let mappingActionFlash: Record<string, boolean> = $state({});

  function fireMappingAction(key: string) {
    mappingActionFlash[key] = true;
    setTimeout(() => { mappingActionFlash[key] = false; }, 180);
  }
</script>

<div class="demo-root">
  <section class="demo-card">
    <h2>Indicator Styles <span class="hint">(click to toggle)</span></h2>
    <div class="demo-grid">
      {#each indicatorStyles as style}
        <button
          type="button"
          class="v2-control-button"
          data-active={styleActive[style.value] ?? false}
          data-indicator-style={style.value}
          data-indicator-color="cyan"
          onclick={() => toggle(styleActive, style.value)}
        >
          {style.label}
        </button>
      {/each}
    </div>
  </section>

  <section class="demo-card">
    <h2>Dot Colors <span class="hint">(click to toggle)</span></h2>
    <div class="demo-grid">
      {#each indicatorColors as color}
        <button
          type="button"
          class="v2-control-button"
          data-active={dotActive[color] ?? false}
          data-indicator-style="dot"
          data-indicator-color={color}
          onclick={() => toggle(dotActive, color)}
        >
          {color}
        </button>
      {/each}
    </div>
  </section>

  <section class="demo-card">
    <h2>Fill Colors <span class="hint">(click to toggle)</span></h2>
    <div class="demo-grid">
      {#each hardwareButtons as btn}
        <button
          type="button"
          class="v2-control-button"
          data-active={dotActive[`${btn.label}-fill`] ?? false}
          data-indicator-style="fill"
          data-indicator-color={btn.color}
          onclick={() => toggle(dotActive, `${btn.label}-fill`)}
        >
          {btn.label}
        </button>
      {/each}
    </div>
  </section>

  <section class="demo-card">
    <h2>Hardware Surface <span class="hint">(click to toggle)</span></h2>
    <div class="demo-grid">
      {#each hardwareButtons as btn}
        <button
          type="button"
          class="v2-control-button"
          data-active={hwActive[btn.label] ?? false}
          data-surface="hardware"
          data-indicator-style={btn.style}
          data-indicator-color={btn.color}
          onclick={() => toggle(hwActive, btn.label)}
        >
          {btn.label}
        </button>
      {/each}
    </div>
  </section>

<section class="demo-card">
    <h2>Hardware Plain + Warm Glow <span class="hint">(click to toggle)</span></h2>
    <div class="demo-grid">
      {#each hardwareButtons as btn}
        <button
          type="button"
          class="v2-control-button"
          data-active={hwActive[`${btn.label}-plain`] ?? false}
          data-surface="hardware"
          data-glow="warm"
          onclick={() => toggle(hwActive, `${btn.label}-plain`)}
        >
          {btn.label}
        </button>
      {/each}
    </div>
  </section>

  <hr style="margin: 32px 0; border: 0; border-top: 1px solid var(--v2-border-panel);">

  <section class="demo-card">
    <h2>🎨 Component Library v2 <span class="hint">(Svelte components)</span></h2>
    <p style="margin: 0 0 16px; color: var(--v2-text-subdued); font-size: 11px;">
      Same styles, cleaner API. Import from <code>$lib/Button</code>
    </p>
  </section>

  <section class="demo-card">
    <h2>DotButton <span class="hint">(component)</span></h2>
    <div class="demo-grid">
      {#each indicatorColors as color}
        <DotButton 
          active={compDotStates[color] ?? false}
          {color}
          onclick={() => compDotStates[color] = !compDotStates[color]}
        >
          {color}
        </DotButton>
      {/each}
    </div>
  </section>

  <section class="demo-card">
    <h2>FillButton <span class="hint">(component)</span></h2>
    <div class="demo-grid">
      {#each hardwareButtons as btn}
        <FillButton 
          active={compFillStates[btn.label] ?? false}
          color={btn.color}
          onclick={() => compFillStates[btn.label] = !compFillStates[btn.label]}
        >
          {btn.label}
        </FillButton>
      {/each}
    </div>
  </section>

  <section class="demo-card">
    <h2>HardwareButton <span class="hint">(component)</span></h2>
    <div class="demo-grid">
      {#each hardwareButtons as btn}
        <HardwareButton
          active={compHwStates[btn.label] ?? false}
          indicator={btn.style as any}
          color={btn.color}
          onclick={() => compHwStates[btn.label] = !compHwStates[btn.label]}
        >
          {btn.label}
        </HardwareButton>
      {/each}
    </div>
  </section>

  <section class="demo-card">
    <h2>HardwarePlainButton <span class="hint">(component)</span></h2>
    <div class="demo-grid">
      {#each hardwareButtons as btn}
        <HardwarePlainButton
          active={compPlainStates[btn.label] ?? false}
          onclick={() => compPlainStates[btn.label] = !compPlainStates[btn.label]}
        >
          {btn.label}
        </HardwarePlainButton>
      {/each}
    </div>
  </section>

  <hr style="margin: 32px 0; border: 0; border-top: 1px solid var(--v2-border-panel);">

  <!-- ── StatusBadge migration reference ─────────────────────────────────── -->

  <section class="demo-card">
    <h2>StatusBadge Migration Reference <span class="hint">(semantic split + visual candidates)</span></h2>
    <p class="lab-note">
      <code>StatusBadge</code> is legacy/transitional. It conflates two separate concerns that must split:<br/><br/>
      <strong>Display path</strong> → <code>StatusIndicator</code> — a read-only display primitive (CSS class, <code>&lt;span&gt;</code>).
      No interactivity. Use for TX state, VFO header mode/filter badges, any status that is set by the radio, not the user.<br/><br/>
      <strong>Interactive path</strong> → <code>status-toggle</code> — a <em>semantic role</em>, not a fixed visual component.
      A status-toggle may be rendered using any approved button family depending on theme/design choice:
      Fill (current default), Dot, Hardware Plain + Warm Glow, or others.
      The architecture must not assume <code>status-toggle === FillButton</code> forever.
    </p>
  </section>

  <!-- ── Interactive path: status-toggle role across visual families ── -->

  <section class="demo-card">
    <h2>status-toggle / Fill family <span class="hint">(click to toggle)</span></h2>
    <p class="lab-note">
      <strong>Semantic role:</strong> status-toggle &nbsp;·&nbsp; <strong>Visual family:</strong> FillButton<br/>
      Current recommended default for interactive StatusBadge migration.
      Proper <code>&lt;button&gt;</code> semantics, token-driven glow, no inline styles.
    </p>
    <div class="demo-grid">
      {#each statusToggleButtons as btn}
        <FillButton
          active={fillToggleStates[btn.label] ?? false}
          color={btn.color}
          onclick={() => fillToggleStates[btn.label] = !fillToggleStates[btn.label]}
        >
          {btn.label}
        </FillButton>
      {/each}
    </div>
  </section>

  <section class="demo-card">
    <h2>status-toggle / Fill family compact <span class="hint">(click to toggle)</span></h2>
    <p class="lab-note">
      Same role, same visual family, <code>compact</code> sizing.
      For tighter panel rows where the current 22px badge height is more appropriate.
    </p>
    <div class="demo-grid">
      {#each statusToggleButtons as btn}
        <FillButton
          active={fillCompactToggleStates[btn.label] ?? false}
          color={btn.color}
          compact
          onclick={() => fillCompactToggleStates[btn.label] = !fillCompactToggleStates[btn.label]}
        >
          {btn.label}
        </FillButton>
      {/each}
    </div>
  </section>

  <section class="demo-card">
    <h2>status-toggle / Dot family <span class="hint">(click to toggle)</span></h2>
    <p class="lab-note">
      <strong>Semantic role:</strong> status-toggle &nbsp;·&nbsp; <strong>Visual family:</strong> DotButton<br/>
      Same radio toggles, different approved visual family. Shows that the role is not locked to Fill.
      A theme could map status-toggle here instead — e.g. a more minimal or monochrome panel theme.
    </p>
    <div class="demo-grid">
      {#each statusToggleButtons as btn}
        <DotButton
          active={dotToggleStates[btn.label] ?? false}
          color={btn.color}
          onclick={() => dotToggleStates[btn.label] = !dotToggleStates[btn.label]}
        >
          {btn.label}
        </DotButton>
      {/each}
    </div>
  </section>

  <section class="demo-card">
    <h2>status-toggle / HardwarePlain family <span class="hint">(click to toggle)</span></h2>
    <p class="lab-note">
      <strong>Semantic role:</strong> status-toggle &nbsp;·&nbsp; <strong>Visual family:</strong> HardwarePlainButton + Warm Glow<br/>
      Incandescent / instrument-panel feel. A vintage or hardware-skeuomorphic theme could prefer this
      over Fill for the same toggles. The role maps; the visual family changes.
    </p>
    <div class="demo-grid">
      {#each statusToggleButtons as btn}
        <HardwarePlainButton
          active={plainToggleStates[btn.label] ?? false}
          onclick={() => plainToggleStates[btn.label] = !plainToggleStates[btn.label]}
        >
          {btn.label}
        </HardwarePlainButton>
      {/each}
    </div>
  </section>

  <section class="demo-card">
    <h2>status-toggle / Hardware Left <span class="hint">(click to toggle)</span></h2>
    <p class="lab-note">
      <strong>Semantic role:</strong> status-toggle &nbsp;·&nbsp; <strong>Visual family:</strong> Hardware + Left Edge<br/>
      Hardware surface with left-edge accent as the sustained state indicator. Good candidate for hardware themes
      where a more instrument-like active marker is preferable to fill.
    </p>
    <div class="demo-grid">
      {#each statusToggleButtons as btn}
        <button
          type="button"
          class="v2-control-button"
          data-active={compHwStates[`status-left-${btn.label}`] ?? false}
          data-surface="hardware"
          data-indicator-style="edge-left"
          data-indicator-color={btn.color}
          onclick={() => compHwStates[`status-left-${btn.label}`] = !compHwStates[`status-left-${btn.label}`]}
        >
          {btn.label}
        </button>
      {/each}
    </div>
  </section>

  <section class="demo-card">
    <h2>status-toggle / Hardware Bottom <span class="hint">(click to toggle)</span></h2>
    <p class="lab-note">
      <strong>Semantic role:</strong> status-toggle &nbsp;·&nbsp; <strong>Visual family:</strong> Hardware + Bottom Edge<br/>
      Hardware surface with bottom-edge accent as the sustained state indicator. Another strong candidate for
      skeuomorphic themes where the active state should read as panel illumination rather than fill.
    </p>
    <div class="demo-grid">
      {#each statusToggleButtons as btn}
        <button
          type="button"
          class="v2-control-button"
          data-active={compHwStates[`status-bottom-${btn.label}`] ?? false}
          data-surface="hardware"
          data-indicator-style="edge-bottom"
          data-indicator-color={btn.color}
          onclick={() => compHwStates[`status-bottom-${btn.label}`] = !compHwStates[`status-bottom-${btn.label}`]}
        >
          {btn.label}
        </button>
      {/each}
    </div>
  </section>

  <hr style="margin: 32px 0; border: 0; border-top: 1px solid var(--v2-border-panel);">

  <!-- ── action-button role exploration ───────────────────────────────────── -->

  <section class="demo-card">
    <h2>Action Button Role <span class="hint">(approved semantic role reference)</span></h2>
    <p class="lab-note">
      <strong>action-button</strong> is a semantic role for momentary command-style controls.<br/><br/>
      Key distinction vs <code>status-toggle</code>: an action-button <em>does not maintain sustained on/off state</em>.
      Clicking fires a command (CLEAR, TUNE, RESET…) and the button returns to idle immediately.
      The brief press-flash below is intentional — it confirms the action fired, but the control is not "on".<br/><br/>
      Same semantic role, three approved visual families shown below. A theme may pick any family.
    </p>
  </section>

  <section class="demo-card">
    <h2>action-button / Fill <span class="hint">(momentary — press flashes, then returns to idle)</span></h2>
    <p class="lab-note">
      <strong>Semantic role:</strong> action-button &nbsp;·&nbsp; <strong>Visual family:</strong> FillButton<br/>
      Strong visual confirmation on press. Color identity helps distinguish command type at a glance.
      Recommended for prominent command controls in dense panels.
    </p>
    <div class="demo-grid">
      {#each actionButtons as btn}
        <button
          type="button"
          class="v2-control-button"
          data-active={actionFlash[`fill-${btn.label}`] ?? false}
          data-indicator-style="fill"
          data-indicator-color={btn.color}
          onclick={() => fireAction(`fill-${btn.label}`)}
        >
          {btn.label}
        </button>
      {/each}
    </div>
  </section>

  <section class="demo-card">
    <h2>action-button / Dot <span class="hint">(momentary — press flashes, then returns to idle)</span></h2>
    <p class="lab-note">
      <strong>Semantic role:</strong> action-button &nbsp;·&nbsp; <strong>Visual family:</strong> DotButton<br/>
      Dot family gives a subtle color cue without full-fill weight. Works well when action buttons
      need to coexist with status-toggle controls in the same panel row without visual competition.
    </p>
    <div class="demo-grid">
      {#each actionButtons as btn}
        <button
          type="button"
          class="v2-control-button"
          data-active={actionFlash[`dot-${btn.label}`] ?? false}
          data-indicator-style="dot"
          data-indicator-color={btn.color}
          onclick={() => fireAction(`dot-${btn.label}`)}
        >
          {btn.label}
        </button>
      {/each}
    </div>
  </section>

  <section class="demo-card">
    <h2>action-button / HardwarePlain <span class="hint">(momentary — press flashes, then returns to idle)</span></h2>
    <p class="lab-note">
      <strong>Semantic role:</strong> action-button &nbsp;·&nbsp; <strong>Visual family:</strong> HardwarePlainButton + Warm Glow<br/>
      Incandescent flash on press; returns to unlit hardware surface. Strong instrument-panel feel.
      A vintage or hardware-skeuomorphic theme could use this family for all command actions.
    </p>
    <div class="demo-grid">
      {#each actionButtons as btn}
        <button
          type="button"
          class="v2-control-button"
          data-active={actionFlash[`plain-${btn.label}`] ?? false}
          data-surface="hardware"
          data-glow="warm"
          onclick={() => fireAction(`plain-${btn.label}`)}
        >
          {btn.label}
        </button>
      {/each}
    </div>
  </section>

  <section class="demo-card">
    <h2>action-button / Hardware Left <span class="hint">(momentary — press flashes, then returns to idle)</span></h2>
    <p class="lab-note">
      <strong>Semantic role:</strong> action-button &nbsp;·&nbsp; <strong>Visual family:</strong> Hardware Surface + Left Edge Accent<br/>
      Left-edge indicator lights on press; hardware surface returns to neutral on release.
      Suits command controls sharing a panel row with left-edge status-toggles (NB, NR, SPLIT).
    </p>
    <div class="demo-grid">
      {#each actionButtons as btn}
        <button
          type="button"
          class="v2-control-button"
          data-active={actionFlash[`hw-left-${btn.label}`] ?? false}
          data-surface="hardware"
          data-indicator-style="edge-left"
          data-indicator-color={btn.color}
          onclick={() => fireAction(`hw-left-${btn.label}`)}
        >
          {btn.label}
        </button>
      {/each}
    </div>
  </section>

  <section class="demo-card">
    <h2>action-button / Hardware Bottom <span class="hint">(momentary — press flashes, then returns to idle)</span></h2>
    <p class="lab-note">
      <strong>Semantic role:</strong> action-button &nbsp;·&nbsp; <strong>Visual family:</strong> Hardware Surface + Bottom Edge Accent<br/>
      Bottom-edge indicator lights on press; hardware surface returns to neutral on release.
      Suits command controls sharing a panel row with bottom-edge status-toggles (TUNE, LOCK).
    </p>
    <div class="demo-grid">
      {#each actionButtons as btn}
        <button
          type="button"
          class="v2-control-button"
          data-active={actionFlash[`hw-bottom-${btn.label}`] ?? false}
          data-surface="hardware"
          data-indicator-style="edge-bottom"
          data-indicator-color={btn.color}
          onclick={() => fireAction(`hw-bottom-${btn.label}`)}
        >
          {btn.label}
        </button>
      {/each}
    </div>
  </section>

  <hr style="margin: 32px 0; border: 0; border-top: 1px solid var(--v2-border-panel);">

  <!-- ── Display path: StatusIndicator primitive ── -->

  <hr style="margin: 32px 0; border: 0; border-top: 1px solid var(--v2-border-panel);">

  <!-- ── Theme Mapping Proof ──────────────────────────────────────────────── -->

  <section class="demo-card">
    <h2>Theme Mapping Proof <span class="hint">(role → family preset)</span></h2>
    <p class="lab-note">
      Select a preset mapping. Both semantic roles — <code>status-toggle</code> and <code>action-button</code> —
      render via the mapped visual family. The <strong>mixed</strong> preset is most instructive:
      it assigns different families to each role, making the semantic distinction visually legible.<br/><br/>
      Mapping lives in <code>$lib/Button/roleMapping.ts</code>. No production panels changed.
    </p>
    <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 20px;">
      {#each PRESET_MAPPINGS as preset}
        <button
          type="button"
          class="v2-control-button"
          data-active={activeMapping.name === preset.name}
          data-indicator-style="fill"
          data-indicator-color="cyan"
          onclick={() => { activeMapping = preset; mappingToggleStates = {}; mappingActionFlash = {}; }}
        >
          {preset.name}
        </button>
      {/each}
    </div>

    <p class="lab-note" style="margin-bottom: 8px;">
      <strong>status-toggle</strong> → <code>{activeMapping.statusToggle}</code>
    </p>
    <div class="demo-grid" style="margin-bottom: 20px;">
      {#if activeMapping.statusToggle === 'fill'}
        {#each statusToggleButtons as btn}
          <FillButton
            active={mappingToggleStates[btn.label] ?? false}
            color={btn.color}
            onclick={() => toggle(mappingToggleStates, btn.label)}
          >{btn.label}</FillButton>
        {/each}
      {:else if activeMapping.statusToggle === 'dot'}
        {#each statusToggleButtons as btn}
          <DotButton
            active={mappingToggleStates[btn.label] ?? false}
            color={btn.color}
            onclick={() => toggle(mappingToggleStates, btn.label)}
          >{btn.label}</DotButton>
        {/each}
      {:else if activeMapping.statusToggle === 'hardware-plain'}
        {#each statusToggleButtons as btn}
          <HardwarePlainButton
            active={mappingToggleStates[btn.label] ?? false}
            onclick={() => toggle(mappingToggleStates, btn.label)}
          >{btn.label}</HardwarePlainButton>
        {/each}
      {:else if activeMapping.statusToggle === 'hardware'}
        {#each statusToggleButtons as btn}
          <HardwareButton
            active={mappingToggleStates[btn.label] ?? false}
            indicator="edge-left"
            color={btn.color}
            onclick={() => toggle(mappingToggleStates, btn.label)}
          >{btn.label}</HardwareButton>
        {/each}
      {/if}
    </div>

    <p class="lab-note" style="margin-bottom: 8px;">
      <strong>action-button</strong> → <code>{activeMapping.actionButton}</code>
    </p>
    <div class="demo-grid">
      {#if activeMapping.actionButton === 'fill'}
        {#each actionButtons as btn}
          <FillButton
            active={mappingActionFlash[btn.label] ?? false}
            color={btn.color}
            onclick={() => fireMappingAction(btn.label)}
          >{btn.label}</FillButton>
        {/each}
      {:else if activeMapping.actionButton === 'dot'}
        {#each actionButtons as btn}
          <DotButton
            active={mappingActionFlash[btn.label] ?? false}
            color={btn.color}
            onclick={() => fireMappingAction(btn.label)}
          >{btn.label}</DotButton>
        {/each}
      {:else if activeMapping.actionButton === 'hardware-plain'}
        {#each actionButtons as btn}
          <HardwarePlainButton
            active={mappingActionFlash[btn.label] ?? false}
            onclick={() => fireMappingAction(btn.label)}
          >{btn.label}</HardwarePlainButton>
        {/each}
      {:else if activeMapping.actionButton === 'hardware'}
        {#each actionButtons as btn}
          <HardwareButton
            active={mappingActionFlash[btn.label] ?? false}
            indicator="edge-bottom"
            color={btn.color}
            onclick={() => fireMappingAction(btn.label)}
          >{btn.label}</HardwareButton>
        {/each}
      {/if}
    </div>
  </section>

  <section class="demo-card">
    <h2>StatusIndicator <span class="hint">(display-only component)</span></h2>
    <p class="lab-note">
      Read-only status/mode display. No <code>onclick</code>, rendered as a dedicated primitive.
      Replaces the old <code>badgeStyleString()</code> inline style path for display cases.
      Standard size (top row) and XS for VFO header display (bottom row).
    </p>
    <div class="demo-grid" style="margin-bottom: 8px;">
      <StatusIndicator label="TX ACTIVE" active color="red" />
      <StatusIndicator label="TX IDLE" color="muted" />
      <StatusIndicator label="RX READY" active color="cyan" />
      <StatusIndicator label="ATU OK" active color="green" />
      <StatusIndicator label="AGC" />
      <StatusIndicator label="CLEAR" active color="muted" />
    </div>
    <div class="demo-grid">
      <StatusIndicator label="USB" active color="cyan" size="xs" />
      <StatusIndicator label="FIL1" active color="green" size="xs" />
      <StatusIndicator label="SPLIT" active color="orange" size="xs" />
      <StatusIndicator label="RIT" active color="orange" size="xs" />
      <StatusIndicator label="NR" size="xs" />
      <StatusIndicator label="NB" size="xs" />
    </div>
  </section>

</div>

<style>
  .demo-root {
    min-height: 100vh;
    padding: 24px;
    display: grid;
    gap: 16px;
    background:
      radial-gradient(circle at top, rgba(0, 212, 255, 0.08), transparent 36%),
      linear-gradient(180deg, var(--v2-bg-gradient-start) 0%, var(--v2-bg-darkest) 100%);
  }

  .demo-card {
    padding: 16px;
    border: 1px solid var(--v2-border-panel);
    border-radius: 8px;
    background: linear-gradient(180deg, var(--v2-panel-bg-gradient-top) 0%, var(--v2-panel-bg-gradient-bottom) 100%);
    box-shadow: var(--v2-shadow-sm);
  }

  h2 {
    margin: 0 0 12px;
    color: var(--v2-text-bright);
    font-family: var(--v2-font-mono);
    font-size: 12px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  .hint {
    color: var(--v2-text-dim);
    font-weight: 400;
    font-size: 10px;
    letter-spacing: 0.02em;
    text-transform: none;
  }

  .demo-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
  }

  .lab-note {
    margin: 0 0 14px;
    color: var(--v2-text-subdued);
    font-size: 10px;
    line-height: 1.6;
  }

  .lab-note strong {
    color: var(--v2-text-bright);
    font-weight: 700;
  }

  code {
    padding: 2px 6px;
    background: var(--v2-bg-darker);
    border: 1px solid var(--v2-border-dark);
    border-radius: 3px;
    font-family: var(--v2-font-mono);
    font-size: 10px;
    color: var(--v2-accent-cyan);
  }

  hr {
    opacity: 0.3;
  }
</style>
