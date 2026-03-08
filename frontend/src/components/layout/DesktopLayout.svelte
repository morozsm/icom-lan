<script lang="ts">
  // Desktop grid layout — placeholder
</script>

<div class="desktop-layout">
  <header class="status-bar">
    <span>IC-7610 · Desktop Layout</span>
  </header>
  <main class="main-grid">
    <section class="left-pane">
      <div class="placeholder">VFO / Spectrum area</div>
    </section>
    <aside class="right-pane">
      <div class="placeholder">Meters / Controls / DX</div>
    </aside>
  </main>
</div>

<style>
  .desktop-layout {
    display: flex;
    flex-direction: column;
    height: 100dvh;
    background-color: var(--bg);
    color: var(--text);
  }

  .status-bar {
    padding: var(--space-2) var(--space-4);
    background-color: var(--panel);
    border-bottom: 1px solid var(--panel-border);
    font-family: var(--font-mono);
    font-size: 0.875rem;
  }

  .main-grid {
    display: grid;
    grid-template-columns: 1fr var(--right-pane-width);
    flex: 1;
    overflow: hidden;
  }

  .left-pane {
    padding: var(--space-4);
    overflow: auto;
  }

  .right-pane {
    padding: var(--space-4);
    background-color: var(--panel);
    border-left: 1px solid var(--panel-border);
    overflow: auto;
  }

  .placeholder {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 200px;
    border: 1px dashed var(--panel-border);
    border-radius: var(--radius);
    color: var(--text-muted);
    font-size: 0.875rem;
  }
</style>
