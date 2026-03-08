<script lang="ts">
  // Mobile stacked layout — placeholder
</script>

<div class="mobile-layout">
  <header class="status-bar">
    <span>IC-7610 · Mobile Layout</span>
  </header>
  <main class="stack">
    <div class="placeholder">VFO area</div>
    <div class="placeholder">Spectrum area</div>
    <div class="placeholder">S-meter / Controls</div>
  </main>
  <footer class="bottom-bar">
    <div class="placeholder">PTT / Audio</div>
  </footer>
</div>

<style>
  .mobile-layout {
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

  .stack {
    flex: 1;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
    padding: var(--space-2);
  }

  .bottom-bar {
    height: var(--bottom-bar-height);
    background-color: var(--panel);
    border-top: 1px solid var(--panel-border);
    padding: var(--space-2) var(--space-4);
  }

  .placeholder {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 120px;
    border: 1px dashed var(--panel-border);
    border-radius: var(--radius);
    color: var(--text-muted);
    font-size: 0.875rem;
  }
</style>
