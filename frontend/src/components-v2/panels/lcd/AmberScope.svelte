<script lang="ts">
  // AmberScope — skeleton for the lcd-scope skin variant.
  // Full scope-dominant layout (60/40 grid, AF scope, waterfall) arrives in C-PR2…C-PR6.
  // No state derivations, no store imports, no FFT connection here.
</script>

<div class="amber-lcd amber-lcd-scope">
  <div class="lcd-screen">
    <div class="lcd-scanlines"></div>
    <div class="lcd-placeholder">LCD SCOPE (coming soon)</div>
  </div>
</div>

<style>
  .amber-lcd {
    width: 100%;
    height: 100%;
    display: flex;
    align-items: stretch;
    padding: 4px;
    box-sizing: border-box;
    min-height: 0;
  }

  .lcd-screen {
    /* Contrast tokens — identical defaults to AmberCockpit. */
    --lcd-alpha-active: 1;
    --lcd-alpha-inactive: 0.08;
    --lcd-alpha-ghost: 0.06;

    position: relative;
    width: 100%;
    background: #C8A030;
    border: 2px solid #8A7020;
    border-radius: 8px;
    padding: 12px 18px;
    overflow: hidden;
    box-shadow:
      inset 0 0 50px rgba(0, 0, 0, 0.06),
      0 0 8px rgba(0, 0, 0, 0.5);
    min-height: 0;

    display: flex;
    align-items: center;
    justify-content: center;
  }

  .lcd-scanlines {
    position: absolute;
    inset: 0;
    pointer-events: none;
    z-index: 1;
    background: repeating-linear-gradient(
      to bottom,
      transparent 0px,
      transparent 3px,
      rgba(0, 0, 0, 0.03) 3px,
      rgba(0, 0, 0, 0.03) 6px
    );
  }

  .lcd-placeholder {
    position: relative;
    z-index: 2;
    font-family: 'JetBrains Mono', 'Courier New', monospace;
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 0.1em;
    color: rgba(26, 16, 0, var(--lcd-alpha-ghost));
    user-select: none;
  }
</style>
