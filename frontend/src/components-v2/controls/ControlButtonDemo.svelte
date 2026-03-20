<script lang="ts">
  import '../theme/index';
  import './control-button.css';

  const indicatorStyles = [
    { value: 'ring', label: 'Ring' },
    { value: 'dot', label: 'Dot' },
    { value: 'edge-bottom', label: 'Edge Bottom' },
    { value: 'edge-left', label: 'Edge Left' },
    { value: 'edge-sides', label: 'Edge Sides' },
    { value: 'fill', label: 'Fill' },
  ] as const;

  const indicatorColors = ['cyan', 'green', 'amber', 'red', 'orange', 'white'] as const;
</script>

<div class="demo-root">
  <section class="demo-card">
    <h2>Indicator Styles</h2>
    <div class="demo-grid">
      {#each indicatorStyles as style}
        <button
          type="button"
          class="v2-control-button"
          data-active="true"
          data-indicator-style={style.value}
          data-indicator-color="cyan"
        >
          {style.label}
        </button>
      {/each}
    </div>
  </section>

  <section class="demo-card">
    <h2>Dot Tokens</h2>
    <div class="demo-grid">
      {#each indicatorColors as color}
        <button
          type="button"
          class="v2-control-button"
          data-active="true"
          data-indicator-style="dot"
          data-indicator-color={color}
        >
          {color}
        </button>
      {/each}
    </div>
  </section>

  <section class="demo-card">
    <h2>Custom Variable</h2>
    <div class="demo-grid">
      <button
        type="button"
        class="v2-control-button v2-control-button--pill"
        data-active="true"
        data-indicator-style="edge-bottom"
        style="--indicator-color: #7cf6ff;"
      >
        Pill Edge
      </button>
      <button
        type="button"
        class="v2-control-button v2-control-button--compact"
        data-active="true"
        data-indicator-style="dot"
        style="--indicator-color: #ffd166;"
      >
        Compact Dot
      </button>
      <button
        type="button"
        class="v2-control-button"
        data-active="false"
        data-indicator-style="dot"
        data-indicator-color="green"
      >
        Inactive Dot
      </button>
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

  .demo-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
  }
</style>
