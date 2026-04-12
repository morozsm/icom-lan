<script lang="ts">
  import { onMount } from 'svelte';
  import '../theme/index';
  import { setTheme, getTheme } from '../theme/theme-switcher';

  if (typeof window !== 'undefined') {
    setTheme(getTheme());
  }

  import { runtime } from '$lib/runtime';
  import { getKeyboardConfig } from '$lib/stores/capabilities.svelte';
  import { applyModeDefault } from '$lib/stores/tuning.svelte';
  import AmberLcdDisplay from '../panels/lcd/AmberLcdDisplay.svelte';
  import LeftSidebar from './LeftSidebar.svelte';
  import RightSidebar from './RightSidebar.svelte';
  import KeyboardHandler from './KeyboardHandler.svelte';
  import StatusBar from './StatusBar.svelte';
  import { makeKeyboardHandlers } from '../wiring/command-bus';

  let radioState = $derived(runtime.state);
  let keyboardConfig = $derived(getKeyboardConfig());
  let activeMode = $derived(radioState?.active === 'SUB' ? radioState?.sub?.mode : radioState?.main?.mode);

  const keyboardHandlers = makeKeyboardHandlers();

  async function handlePowerOn() {
    try {
      await runtime.system.powerOn();
    } catch (err) {
      alert(`Failed to power on: ${err}`);
    }
  }

  $effect(() => {
    if (activeMode) {
      applyModeDefault(activeMode);
    }
  });
</script>

<div class="lcd-layout">
  <StatusBar />
  <KeyboardHandler config={keyboardConfig} onAction={keyboardHandlers.dispatch} />

  <section class="content-row">
    <div class="content-left">
      <LeftSidebar />
    </div>

    <main class="content-center">
      <div class="lcd-slot">
        <div class="lcd-frame">
          <AmberLcdDisplay />
        </div>
      </div>
    </main>

    <div class="content-right">
      <RightSidebar />
    </div>
  </section>


</div>

{#if runtime.connection.radioPowerOn === false}
  <div class="power-off-overlay" aria-label="Radio is powered off">
    <div class="power-off-content">
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M18.36 6.64a9 9 0 1 1-12.73 0" />
        <line x1="12" y1="2" x2="12" y2="12" />
      </svg>
      <span class="power-off-label">Radio is powered off</span>
      <button class="power-on-btn" onclick={handlePowerOn}>
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M18.36 6.64a9 9 0 1 1-12.73 0" />
          <line x1="12" y1="2" x2="12" y2="12" />
        </svg>
        Power ON
      </button>
    </div>
  </div>
{/if}

<style>
  .lcd-layout {
    position: relative;
    display: grid;
    grid-template-rows: 28px minmax(0, 1fr);
    height: 100vh;
    background:
      linear-gradient(180deg, var(--v2-bg-gradient-start) 0%, var(--v2-bg-darkest) 100%),
      var(--v2-bg-app, var(--v2-bg-darker));
    gap: 5px;
    padding: 5px;
    box-sizing: border-box;
  }

  .content-row {
    display: grid;
    grid-template-columns: 228px minmax(0, 1fr) 228px;
    grid-template-rows: minmax(0, 1fr);
    gap: 5px;
    min-height: 0;
    overflow: hidden;
  }

  .content-left,
  .content-right {
    min-height: 0;
    max-height: 100%;
    overflow-y: auto;
    overflow-x: hidden;
    padding-bottom: 4px;
    border: 1px solid var(--v2-border-panel);
    border-radius: 4px;
    background:
      linear-gradient(180deg, var(--v2-panel-bg-gradient-top) 0%, var(--v2-panel-bg-gradient-bottom) 100%);
    box-shadow: var(--v2-shadow-sm);
    scrollbar-width: none;
    -ms-overflow-style: none;
  }

  .content-left::-webkit-scrollbar,
  .content-right::-webkit-scrollbar {
    display: none;
  }

  .content-center {
    min-height: 0;
    min-width: 0;
    display: flex;
    align-items: start;
  }

  .lcd-slot {
    width: 100%;
    min-height: 0;
    display: flex;
    aspect-ratio: 16 / 7.5;
    max-height: 100%;
  }

  .lcd-frame {
    flex: 1;
    min-height: 0;
    min-width: 0;
    overflow: hidden;
    background: var(--v2-bg-card);
    border: 1px solid var(--v2-border-darker);
    border-radius: 4px;
  }

  .power-off-overlay {
    position: fixed;
    inset: 0;
    z-index: 9999;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(0, 0, 0, 0.85);
    backdrop-filter: blur(8px);
  }

  .power-off-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
    color: var(--v2-text-dim);
  }

  .power-off-label {
    font-family: 'Roboto Mono', monospace;
    font-size: 16px;
    font-weight: 700;
    letter-spacing: 0.1em;
  }

  .power-on-btn {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 8px;
    padding: 10px 24px;
    font-family: 'Roboto Mono', monospace;
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 0.08em;
    color: #fff;
    background: rgba(40, 160, 40, 0.25);
    border: 1.5px solid rgba(40, 160, 40, 0.6);
    border-radius: 6px;
    cursor: pointer;
    transition: background 0.15s, border-color 0.15s;
  }
  .power-on-btn:hover {
    background: rgba(40, 160, 40, 0.4);
    border-color: rgba(40, 160, 40, 0.8);
  }
</style>
