<script lang="ts">
  import { radio } from '$lib/stores/radio.svelte';
  import { getCapabilities, hasTx, hasDualReceiver, hasAnyScope } from '$lib/stores/capabilities.svelte';
  import { getConnectionStatus, getRadioPowerOn } from '$lib/stores/connection.svelte';
  import { getAudioState } from '$lib/stores/audio.svelte';
  import { HardwareButton } from '$lib/Button';
  import SpectrumPanel from '../../components/spectrum/SpectrumPanel.svelte';
  import FrequencyDisplay from '../display/FrequencyDisplay.svelte';
  import LinearSMeter from '../meters/LinearSMeter.svelte';
  import CollapsiblePanel from '../controls/CollapsiblePanel.svelte';
  import BandSelector from '../controls/BandSelector.svelte';
  import FilterPanel from '../panels/FilterPanel.svelte';
  import RxAudioPanel from '../panels/RxAudioPanel.svelte';
  import TxPanel from '../panels/TxPanel.svelte';
  import DspPanel from '../panels/DspPanel.svelte';
  import AgcPanel from '../panels/AgcPanel.svelte';
  import RfFrontEnd from '../panels/RfFrontEnd.svelte';
  import RitXitPanel from '../panels/RitXitPanel.svelte';
  import CwPanel from '../panels/CwPanel.svelte';
  import DockMeterPanel from '../panels/DockMeterPanel.svelte';
  import KeyboardHandler from './KeyboardHandler.svelte';
  import { ValueControl, rawToPercentDisplay } from '../controls/value-control';
  import {
    Settings, ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight, Mic, MicOff,
    Sliders, Radio as RadioIcon,
  } from 'lucide-svelte';
  import {
    resolveVfoLayoutProfile,
    vfoLayoutStyleVars,
  } from './vfo-layout-tokens';
  import { getTxPermit } from '$lib/utils/tx-permit';
  import {
    toVfoProps, toVfoOpsProps, toMeterProps,
    toRfFrontEndProps, toModeProps, toFilterProps, toAgcProps, toRitXitProps,
    toBandSelectorProps, toRxAudioProps, toDspProps, toTxProps, toCwProps,
  } from '../wiring/state-adapter';
  import {
    makeVfoHandlers, makeMeterHandlers, makeKeyboardHandlers,
    makeRfFrontEndHandlers, makeModeHandlers, makeFilterHandlers,
    makeAgcHandlers, makeRitXitHandlers, makeBandHandlers, makePresetHandlers,
    makeRxAudioHandlers, makeDspHandlers, makeTxHandlers, makeCwPanelHandlers,
    makeSystemHandlers,
  } from '../wiring/command-bus';
  import { getKeyboardConfig } from '$lib/stores/capabilities.svelte';
  import { audioManager } from '$lib/audio/audio-manager';
  import { onMount, onDestroy } from 'svelte';

  // ── State ──
  let radioState = $derived(radio.current);
  let caps = $derived(getCapabilities());
  let keyboardConfig = $derived(getKeyboardConfig());
  let audioState = $derived(getAudioState());
  let txCapable = $derived(hasTx());
  let txPermit = $derived(getTxPermit(mainVfo.freq, caps?.txBands));
  let txIndicatorColor = $derived(
    (tx.txActive || pttActive) ? 'var(--v2-accent-red, #ef4444)' :
    txPermit === 'allowed' ? 'var(--v2-accent-green, #4ade80)' :
    'var(--v2-text-dim, #555)'
  );

  // ── VFO props ──
  let mainVfo = $derived(toVfoProps(radioState, 'main'));
  let subVfo = $derived(toVfoProps(radioState, 'sub'));
  let vfoOps = $derived(toVfoOpsProps(radioState, caps));
  let meter = $derived(toMeterProps(radioState));
  let mode = $derived(toModeProps(radioState, caps));
  let filter = $derived(toFilterProps(radioState, caps));
  let band = $derived(toBandSelectorProps(radioState));
  let rxAudio = $derived(toRxAudioProps(radioState, caps, audioState));
  let tx = $derived(toTxProps(radioState, caps));
  let rfFrontEnd = $derived(toRfFrontEndProps(radioState, caps));
  let agc = $derived(toAgcProps(radioState, caps));
  let ritXit = $derived(toRitXitProps(radioState, caps));
  let dsp = $derived(toDspProps(radioState, caps));
  let cw = $derived(toCwProps(radioState, caps));

  // ── Handlers ──
  const vfoHandlers = makeVfoHandlers();
  const meterHandlers = makeMeterHandlers();
  const keyboardHandlers = makeKeyboardHandlers();
  const modeHandlers = makeModeHandlers();
  const filterHandlers = makeFilterHandlers();
  const bandHandlers = makeBandHandlers();
  const presetHandlers = makePresetHandlers();
  const rxAudioHandlers = makeRxAudioHandlers();
  const txHandlers = makeTxHandlers();
  const rfHandlers = makeRfFrontEndHandlers();
  const agcHandlers = makeAgcHandlers();
  const ritXitHandlers = makeRitXitHandlers();
  const dspHandlers = makeDspHandlers();
  const cwHandlers = makeCwPanelHandlers();
  const systemHandlers = makeSystemHandlers();

  // ── VFO layout ──
  let receiverDeckElement = $state<HTMLElement | null>(null);
  let receiverDeckWidth = $state<number | null>(null);
  let vfoLayoutProfile = $derived(resolveVfoLayoutProfile(receiverDeckWidth));
  let receiverDeckStyle = $derived(vfoLayoutStyleVars(vfoLayoutProfile, {
    width: receiverDeckWidth,
    overrides: {},
  }));

  // ── Modals ──
  let settingsOpen = $state(false);
  let modeModalOpen = $state(false);
  let filterModalOpen = $state(false);
  let txSettingsOpen = $state(false);
  let powerModalOpen = $state(false);

  // ── Tuning strip ──
  // Mode-aware step presets
  const SSB_STEPS = [10, 50, 100, 500, 1000];
  const CW_STEPS  = [10, 50, 100, 500];
  const AM_STEPS  = [1000, 5000, 9000, 10000];
  const FM_STEPS  = [5000, 10000, 12500, 25000];
  const DEFAULT_STEPS = [10, 50, 100, 500, 1000, 5000, 10000, 100000];

  function getStepsForMode(m: string): number[] {
    const upper = (m || '').toUpperCase();
    if (upper === 'USB' || upper === 'LSB') return SSB_STEPS;
    if (upper === 'CW' || upper === 'CW-R') return CW_STEPS;
    if (upper === 'AM') return AM_STEPS;
    if (upper === 'FM') return FM_STEPS;
    return DEFAULT_STEPS;
  }

  let availableSteps = $derived(getStepsForMode(mode.currentMode));
  let tuningStep = $state(1000); // Hz
  let stepPickerOpen = $state(false);

  // Reset step when mode changes and current step is not in new mode's list
  $effect(() => {
    const steps = getStepsForMode(mode.currentMode);
    if (!steps.includes(tuningStep)) {
      tuningStep = steps[Math.floor(steps.length / 2)] ?? 1000;
    }
  });

  function tuneBy(delta: number) {
    const freq = mainVfo.freq + delta * tuningStep;
    vfoHandlers.onMainFreqChange(freq);
  }

  function selectStep(hz: number) {
    tuningStep = hz;
    stepPickerOpen = false;
  }

  function formatStep(hz: number): string {
    if (hz >= 1000) return `${hz / 1000} kHz`;
    return `${hz} Hz`;
  }

  // ── Quick modes (SSB operation essentials) ──
  // Quick modes — show first matching from profile (covers both CW and CW-U).
  const QUICK_MODE_CANDIDATES = ['LSB', 'USB', 'CW', 'CW-U', 'AM'];
  const QUICK_MODES = $derived(QUICK_MODE_CANDIDATES.filter((m) => mode.modes.includes(m)).slice(0, 4));

  // ── Landscape detection ──
  let isLandscape = $state(false);
  function checkOrientation() {
    const wasLandscape = isLandscape;
    isLandscape = window.innerWidth > window.innerHeight && window.innerHeight < 500;
    // Try to enter fullscreen on landscape (hides Safari chrome)
    if (isLandscape && !wasLandscape) {
      requestFullscreen();
      // iOS Safari: scroll trick to minimize chrome
      setTimeout(() => window.scrollTo(0, 1), 50);
    } else if (!isLandscape && wasLandscape) {
      exitFullscreen();
    }
  }

  function requestFullscreen() {
    const el = document.documentElement;
    // Standard Fullscreen API (not supported in iOS Safari, but works on Android Chrome)
    if (el.requestFullscreen) {
      el.requestFullscreen().catch(() => {});
    } else if ((el as any).webkitRequestFullscreen) {
      (el as any).webkitRequestFullscreen();
    }
  }

  function exitFullscreen() {
    if (document.fullscreenElement) {
      document.exitFullscreen().catch(() => {});
    } else if ((document as any).webkitFullscreenElement) {
      (document as any).webkitExitFullscreen();
    }
  }

  // ── Screen Wake Lock ──
  let wakeLock: WakeLockSentinel | null = null;
  let wakeLockRequested = false;

  async function requestWakeLock() {
    if (wakeLock) return; // already held
    try {
      if ('wakeLock' in navigator) {
        wakeLock = await navigator.wakeLock.request('screen');
        wakeLock.addEventListener('release', () => { wakeLock = null; });
        console.log('[WakeLock] acquired');
      }
    } catch (e) {
      console.warn('[WakeLock] failed:', e);
    }
  }

  // iOS Safari needs user gesture for Wake Lock — request on first touch
  function ensureWakeLock() {
    if (!wakeLockRequested) {
      wakeLockRequested = true;
      requestWakeLock();
    }
  }

  onMount(() => {
    // Orientation
    checkOrientation();
    window.addEventListener('resize', checkOrientation);

    // Try immediately (works on Chrome/Android)
    requestWakeLock();
    // Re-acquire on visibility change
    const handleVisibility = () => {
      if (document.visibilityState === 'visible') {
        requestWakeLock();
      }
    };
    document.addEventListener('visibilitychange', handleVisibility);
    // Fallback: acquire on first user interaction (iOS)
    const handleInteraction = () => {
      ensureWakeLock();
    };
    document.addEventListener('touchstart', handleInteraction, { once: true });
    document.addEventListener('click', handleInteraction, { once: true });

    // Ultimate fallback: invisible video loop keeps screen on (iOS ≤16.3 or any browser w/o Wake Lock)
    let noSleepVideo: HTMLVideoElement | null = null;
    if (!('wakeLock' in navigator)) {
      noSleepVideo = document.createElement('video');
      noSleepVideo.setAttribute('playsinline', '');
      noSleepVideo.setAttribute('muted', '');
      noSleepVideo.muted = true;
      noSleepVideo.loop = true;
      noSleepVideo.style.position = 'fixed';
      noSleepVideo.style.top = '-1px';
      noSleepVideo.style.left = '-1px';
      noSleepVideo.style.width = '1px';
      noSleepVideo.style.height = '1px';
      noSleepVideo.style.opacity = '0.01';
      // Minimal silent mp4 (1s, 1x1px)
      noSleepVideo.src = 'data:video/mp4;base64,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';
      document.body.appendChild(noSleepVideo);
      const playOnTouch = () => {
        noSleepVideo?.play().catch(() => {});
        document.removeEventListener('touchstart', playOnTouch);
      };
      document.addEventListener('touchstart', playOnTouch, { once: true });
    }

    return () => {
      window.removeEventListener('resize', checkOrientation);
      document.removeEventListener('visibilitychange', handleVisibility);
      document.removeEventListener('touchstart', handleInteraction);
      document.removeEventListener('click', handleInteraction);
      wakeLock?.release();
      if (noSleepVideo) {
        noSleepVideo.pause();
        noSleepVideo.remove();
      }
    };
  });

  // ── PTT ──
  // Modes: 'idle' | 'held' (touch held down) | 'latched' (double-tap locked)
  let pttMode = $state<'idle' | 'held' | 'latched'>('idle');
  let pttActive = $derived(pttMode !== 'idle');
  let lastPttDown = 0;
  const DOUBLE_TAP_MS = 350;
  const PTT_SAFETY_TIMEOUT_MS = 3 * 60 * 1000; // 3 minutes
  let pttSafetyTimer: ReturnType<typeof setTimeout> | null = null;

  function clearPttSafety() {
    if (pttSafetyTimer) {
      clearTimeout(pttSafetyTimer);
      pttSafetyTimer = null;
    }
  }

  function startPttSafety() {
    clearPttSafety();
    pttSafetyTimer = setTimeout(() => {
      // Safety: force PTT off after timeout
      pttMode = 'idle';
      disengageTx();
    }, PTT_SAFETY_TIMEOUT_MS);
  }

  async function engageTx() {
    systemHandlers.onPttOn();
    await audioManager.startTx();
  }

  function disengageTx() {
    systemHandlers.onPttOff();
    audioManager.stopTx();
  }

  function pttDown() {
    const now = Date.now();
    if (pttMode === 'latched') {
      // Tap while latched → unlock, go idle
      pttMode = 'idle';
      disengageTx();
      clearPttSafety();
      return;
    }
    if (now - lastPttDown < DOUBLE_TAP_MS && pttMode === 'held') {
      // Double-tap → latch
      pttMode = 'latched';
      startPttSafety();
      lastPttDown = 0;
      return;
    }
    // Normal press → held
    lastPttDown = now;
    pttMode = 'held';
    engageTx();
    startPttSafety();
  }

  function pttUp() {
    if (pttMode === 'held') {
      // Release after single tap → off
      // But give a moment for double-tap detection
      setTimeout(() => {
        if (pttMode === 'held') {
          pttMode = 'idle';
          disengageTx();
          clearPttSafety();
        }
      }, DOUBLE_TAP_MS);
    }
    // If latched, don't turn off on release
  }

  // ── ATU (long-press = tune) ──
  let atuTimer: ReturnType<typeof setTimeout> | null = null;
  let atuDidLongPress = false;

  function atuTouchStart() {
    atuDidLongPress = false;
    atuTimer = setTimeout(() => {
      atuDidLongPress = true;
      txHandlers.onAtuTune(); // Start antenna tune
    }, 600);
  }

  function atuTouchEnd() {
    if (atuTimer) {
      clearTimeout(atuTimer);
      atuTimer = null;
    }
    if (!atuDidLongPress) {
      txHandlers.onAtuToggle(); // Short press = toggle on/off
    }
  }

  // ── S-meter formatting ──
  function formatSValue(raw: number): string {
    if (raw <= 0) return 'S0';
    if (raw <= 120) {
      const s = Math.round(raw / 120 * 9);
      return `S${Math.min(9, Math.max(0, s))}`;
    }
    const over = Math.round((raw - 120) / 120 * 60);
    return `S9+${over}`;
  }

  function formatDbm(raw: number): string {
    // S9 = -73 dBm, each S-unit = 6 dB
    const dbm = -73 + (raw - 120) / 120 * 60;
    return `${Math.round(dbm)} dBm`;
  }

  // ── RF Power display ──
  function formatPower(raw: number): string {
    // 0-255 → 0-100W (approx for IC-7610)
    const watts = Math.round(raw / 255 * 100);
    return `${watts}W`;
  }

  // ── ATU status ──
  let atuStatus = $derived(tx.atuActive ? (tx.atuTuning ? 'tuning' : 'on') : 'off');
</script>

{#if isLandscape}
<!-- ═══ LANDSCAPE: fullscreen spectrum + VFO overlay ═══ -->
<div class="m-landscape">
  <KeyboardHandler config={keyboardConfig} onAction={keyboardHandlers.dispatch} />
  {#if hasAnyScope()}
    <div class="m-ls-spectrum">
      <SpectrumPanel />
    </div>
  {/if}
  <div class="m-ls-overlay">
    <div class="m-ls-vfo">
      <span class="m-tx-indicator" style="background: {txIndicatorColor}"></span>
      <FrequencyDisplay freq={mainVfo.freq} compact active />
    </div>
    <div class="m-ls-quick-modes">
      {#each QUICK_MODES as m}
        <button
          class="m-ls-mode-btn"
          class:m-ls-mode-active={mainVfo.mode === m}
          onclick={() => modeHandlers.onModeChange(m)}
        >{m}</button>
      {/each}
    </div>
    <div class="m-ls-meter">
      <span class="m-ls-smeter">{formatSValue(meter.signal)}</span>
      <span class="m-ls-dbm">{formatDbm(meter.signal)}</span>
    </div>
    <div class="m-ls-controls">
      <button class="m-ls-step-btn" onclick={() => (stepPickerOpen = !stepPickerOpen)}>
        {formatStep(tuningStep)}
      </button>
      <button class="m-ls-tune-btn" onclick={() => tuneBy(-1)}>
        <ChevronLeft size={20} />
      </button>
      <button class="m-ls-tune-btn" onclick={() => tuneBy(1)}>
        <ChevronRight size={20} />
      </button>
      <span class="m-ls-filter">{mainVfo.filter}</span>
      {#if txCapable}
        <button
          class="m-ls-ptt"
          class:m-ptt-held={pttMode === 'held'}
          class:m-ptt-latched={pttMode === 'latched'}
          ontouchstart={(e) => { e.preventDefault(); pttDown(); }}
          ontouchend={(e) => { e.preventDefault(); pttUp(); }}
          ontouchcancel={() => pttUp()}
        >
          {pttMode === 'latched' ? 'TX🔒' : pttMode === 'held' ? 'TX' : 'PTT'}
        </button>
      {/if}
    </div>
  </div>
  {#if stepPickerOpen}
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="m-step-picker-backdrop" onclick={() => (stepPickerOpen = false)}></div>
    <div class="m-ls-step-picker">
      {#each modeSteps as step}
        <button
          class="m-step-option"
          class:m-step-active={step === tuningStep}
          onclick={() => { tuningStep = step; stepPickerOpen = false; }}
        >{formatStep(step)}</button>
      {/each}
    </div>
  {/if}
</div>
{:else}
<!-- ═══ PORTRAIT: normal mobile layout ═══ -->
<div class="m-layout">
  <KeyboardHandler config={keyboardConfig} onAction={keyboardHandlers.dispatch} />

  <!-- ═══ STICKY VFO HEADER ═══ -->
  <header class="m-vfo-bar" bind:this={receiverDeckElement} style={receiverDeckStyle}>
    <div class="m-vfo-row">
      <span class="m-tx-indicator" style="background: {txIndicatorColor}" title={txPermit === 'allowed' ? 'TX allowed' : 'TX not allowed (out of band)'}></span>
      <div class="m-vfo-freq">
        <FrequencyDisplay freq={mainVfo.freq} compact active />
      </div>
      <button class="m-settings-btn" onclick={() => (settingsOpen = true)}>
        <Settings size={16} />
        <span>MORE</span>
      </button>
    </div>
    <div class="m-vfo-meta">
      <span class="m-vfo-mode">{mainVfo.mode}</span>
      <span class="m-vfo-filter">{mainVfo.filter}</span>
      {#if hasDualReceiver() && subVfo.freq > 0}
        <span class="m-vfo-sub">{(subVfo.freq / 1_000_000).toFixed(3)}</span>
      {/if}
    </div>
  </header>

  <!-- ═══ S-METER BAR ═══ -->
  <div class="m-smeter-bar">
    <LinearSMeter value={mainVfo.sValue} compact label="" />
  </div>

  <!-- ═══ SCROLLABLE CONTENT ═══ -->
  <main class="m-content">

    <!-- Spectrum / Waterfall -->
    {#if hasAnyScope()}
      <section class="m-spectrum">
        <SpectrumPanel />
      </section>
    {/if}

    <!-- Band -->
    <section class="m-section">
      <CollapsiblePanel title="BAND" panelId="m-band" collapsible={true}>
        <BandSelector
          currentFreq={band.currentFreq}
          onBandSelect={bandHandlers.onBandSelect}
          onPresetSelect={presetHandlers.onPresetSelect}
        />
      </CollapsiblePanel>
    </section>

    <!-- Mode (quick: LSB USB CW AM + More) -->
    <section class="m-section">
      <CollapsiblePanel title="MODE" panelId="m-mode" collapsible={true}>
        <div class="m-quick-grid">
          {#each QUICK_MODES as m}
            <HardwareButton
              active={mode.currentMode === m}
              indicator="edge-left"
              color="cyan"
              onclick={() => modeHandlers.onModeChange(m)}
            >
              {m}
            </HardwareButton>
          {/each}
          <HardwareButton
            indicator="edge-left"
            color="muted"
            onclick={() => (modeModalOpen = true)}
          >
            More…
          </HardwareButton>
        </div>
      </CollapsiblePanel>
    </section>

    <!-- Filter (quick: FIL1 FIL2 FIL3 + More) -->
    <section class="m-section">
      <CollapsiblePanel title="FILTER" panelId="m-filter" collapsible={true}>
        <div class="m-quick-grid">
          {#each (filter.filterLabels ?? ['FIL1', 'FIL2', 'FIL3']) as label, idx}
            <HardwareButton
              active={filter.currentFilter === idx + 1}
              indicator="edge-left"
              color="cyan"
              onclick={() => filterHandlers.onFilterChange?.(idx + 1)}
            >
              {label}
            </HardwareButton>
          {/each}
          <HardwareButton
            indicator="edge-left"
            color="muted"
            onclick={() => (filterModalOpen = true)}
          >
            More…
          </HardwareButton>
        </div>
      </CollapsiblePanel>
    </section>

    <!-- Audio (AF + monitor mode + DSP toggles) -->
    <section class="m-section">
      <CollapsiblePanel title="AUDIO" panelId="m-audio" collapsible={true}>
        <div class="m-audio-content">
          <div class="m-audio-buttons">
            {#each ['local', 'live', 'mute'] as opt}
              <HardwareButton
                active={rxAudio.monitorMode === opt}
                indicator="edge-left"
                color={opt === 'mute' ? 'red' : 'cyan'}
                onclick={() => rxAudioHandlers.onMonitorModeChange(opt)}
              >
                {opt === 'local' ? 'LOCAL' : opt === 'live' ? 'LIVE' : 'MUTE'}
              </HardwareButton>
            {/each}
          </div>
          <ValueControl
            label="AF Level"
            value={rxAudio.afLevel}
            min={0}
            max={255}
            step={1}
            renderer="hbar"
            displayFn={rawToPercentDisplay}
            accentColor="var(--v2-accent-cyan-alt)"
            onChange={rxAudioHandlers.onAfLevelChange}
            variant="hardware-illuminated"
          />
          <div class="m-dsp-toggles">
            <HardwareButton
              active={dsp.nbActive}
              indicator="edge-left"
              color={dsp.nbActive ? 'green' : 'muted'}
              onclick={() => dspHandlers.onNbToggle(!dsp.nbActive)}
            >
              NB
            </HardwareButton>
            <HardwareButton
              active={dsp.nrMode > 0}
              indicator="edge-left"
              color={dsp.nrMode > 0 ? 'green' : 'muted'}
              onclick={() => dspHandlers.onNrModeChange(dsp.nrMode > 0 ? 0 : 1)}
            >
              NR
            </HardwareButton>
            <HardwareButton
              active={dsp.notchMode !== 'off'}
              indicator="edge-left"
              color={dsp.notchMode !== 'off' ? 'green' : 'muted'}
              onclick={() => dspHandlers.onNotchModeChange(dsp.notchMode !== 'off' ? 'off' : 'auto')}
            >
              NOTCH
            </HardwareButton>
          </div>
        </div>
      </CollapsiblePanel>
    </section>

    <!-- RF Front End (ATT / PRE / DIGI-SEL / IP+) -->
    <section class="m-section">
      <CollapsiblePanel title="RF" panelId="m-rf-quick" collapsible={true}>
        <RfFrontEnd
          rfGain={rfFrontEnd.rfGain}
          squelch={rfFrontEnd.squelch}
          att={rfFrontEnd.att}
          pre={rfFrontEnd.pre}
          digiSel={rfFrontEnd.digiSel}
          ipPlus={rfFrontEnd.ipPlus}
          onRfGainChange={rfHandlers.onRfGainChange}
          onSquelchChange={rfHandlers.onSquelchChange}
          onAttChange={rfHandlers.onAttChange}
          onPreChange={rfHandlers.onPreChange}
          onDigiSelToggle={rfHandlers.onDigiSelToggle}
          onIpPlusToggle={rfHandlers.onIpPlusToggle}
        />
      </CollapsiblePanel>
    </section>

    <!-- TX (compact: PTT + Power readout + ATU) -->
    {#if txCapable}
      <section class="m-section">
        <CollapsiblePanel title="TX" panelId="m-tx" collapsible={true}>
          <div class="m-tx-compact">
            <!-- Power readout (tap → power modal) -->
            <!-- svelte-ignore a11y_no_static_element_interactions -->
            <div class="m-tx-info" onclick={() => (powerModalOpen = true)}>
              <span class="m-tx-power-value">{formatPower(tx.rfPower)}</span>
              {#if tx.txActive || pttActive}
                <span class="m-tx-swr-value">SWR {meter.swr > 0 ? (meter.swr / 10).toFixed(1) : '—'}</span>
              {/if}
            </div>

            <!-- ATU -->
            <button
              class="m-atu-btn"
              class:m-atu-on={atuStatus === 'on'}
              class:m-atu-tuning={atuStatus === 'tuning'}
              ontouchstart={atuTouchStart}
              ontouchend={atuTouchEnd}
              ontouchcancel={atuTouchEnd}
              onmousedown={atuTouchStart}
              onmouseup={atuTouchEnd}
            >
              ATU
            </button>

            <!-- TX settings -->
            <button class="m-tx-settings-btn" onclick={() => (txSettingsOpen = true)}>
              <Sliders size={14} />
            </button>

            <!-- PTT (wider) -->
            <button
              class="m-ptt-btn"
              class:m-ptt-held={pttMode === 'held'}
              class:m-ptt-latched={pttMode === 'latched'}
              ontouchstart={(e) => { e.preventDefault(); pttDown(); }}
              ontouchend={(e) => { e.preventDefault(); pttUp(); }}
              ontouchcancel={() => pttUp()}
              onmousedown={pttDown}
              onmouseup={pttUp}
              onmouseleave={() => { if (pttMode === 'held') pttUp(); }}
            >
              {#if pttMode === 'latched'}
                <MicOff size={18} />
                TX LOCK
              {:else if pttMode === 'held'}
                TX
              {:else}
                <Mic size={18} />
                PTT
              {/if}
            </button>
          </div>
          {#if tx.txActive || pttActive}
            <div class="m-tx-meter">
              <DockMeterPanel
                sValue={mainVfo.sValue}
                rfPower={meter.rfPower ?? 0}
                swr={meter.swr}
                alc={meter.alc ?? 0}
                txActive={true}
                meterSource="po"
                onMeterSourceChange={() => {}}
              />
            </div>
          {/if}
        </CollapsiblePanel>
      </section>
    {/if}

    <!-- Spacer for tuning strip -->
    <div class="m-bottom-spacer"></div>
  </main>

  <!-- ═══ TUNING STRIP (FIXED BOTTOM) ═══ -->
  <nav class="m-tuning-strip">
    <button class="m-tune-btn m-tune-fast" onclick={() => tuneBy(-10)}>
      <ChevronsLeft size={18} />
    </button>
    <button class="m-tune-btn" onclick={() => tuneBy(-1)}>
      <ChevronLeft size={22} />
    </button>
    <div class="m-tune-step-wrapper">
      <button class="m-tune-step" onclick={() => (stepPickerOpen = !stepPickerOpen)}>
        {formatStep(tuningStep)}
      </button>
      {#if stepPickerOpen}
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div class="m-step-picker-backdrop" onclick={() => (stepPickerOpen = false)}></div>
        <div class="m-step-picker">
          {#each availableSteps as s}
            <button
              class="m-step-option"
              class:m-step-active={s === tuningStep}
              onclick={() => selectStep(s)}
            >
              {formatStep(s)}
            </button>
          {/each}
        </div>
      {/if}
    </div>
    <button class="m-tune-btn" onclick={() => tuneBy(1)}>
      <ChevronRight size={22} />
    </button>
    <button class="m-tune-btn m-tune-fast" onclick={() => tuneBy(10)}>
      <ChevronsRight size={18} />
    </button>
  </nav>

  <!-- ═══ SETTINGS BOTTOM SHEET ═══ -->
  {#if settingsOpen}
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="m-sheet-backdrop" onclick={() => (settingsOpen = false)}>
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <div class="m-sheet" onclick={(e) => e.stopPropagation()}>
        <div class="m-sheet-handle"></div>
        <div class="m-sheet-title">SETTINGS</div>
        <div class="m-sheet-content">
          <CollapsiblePanel title="VFO / BAND" panelId="m-vfo-ops">
            <div class="m-vfo-ops-row">
              <HardwareButton
                active={vfoOps.splitActive}
                indicator="edge-left"
                color={vfoOps.splitActive ? 'yellow' : 'muted'}
                onclick={vfoHandlers.onSplitToggle}
              >
                SPLIT
              </HardwareButton>
              <HardwareButton
                indicator="edge-left"
                color="cyan"
                onclick={vfoHandlers.onSwap}
              >
                A↔B
              </HardwareButton>
              <HardwareButton
                indicator="edge-left"
                color="cyan"
                onclick={vfoHandlers.onEqual}
              >
                A=B
              </HardwareButton>
            </div>
            <BandSelector
              currentFreq={band.currentFreq}
              onBandSelect={bandHandlers.onBandSelect}
              onFreqPreset={presetHandlers.onFreqPreset}
            />
          </CollapsiblePanel>

          <CollapsiblePanel title="DSP" panelId="m-dsp">
            <DspPanel
              nrMode={dsp.nrMode}
              nrLevel={dsp.nrLevel}
              nbActive={dsp.nbActive}
              nbLevel={dsp.nbLevel}
              notchMode={dsp.notchMode}
              notchFreq={dsp.notchFreq}
              onNrModeChange={dspHandlers.onNrModeChange}
              onNrLevelChange={dspHandlers.onNrLevelChange}
              onNbToggle={dspHandlers.onNbToggle}
              onNbLevelChange={dspHandlers.onNbLevelChange}
              onNotchModeChange={dspHandlers.onNotchModeChange}
              onNotchFreqChange={dspHandlers.onNotchFreqChange}
            />
          </CollapsiblePanel>

          <CollapsiblePanel title="AGC" panelId="m-agc">
            <AgcPanel
              agcMode={agc.agcMode}
              onAgcModeChange={agcHandlers.onAgcModeChange}
            />
          </CollapsiblePanel>

          <CollapsiblePanel title="RF FRONT END" panelId="m-rf">
            <RfFrontEnd
              rfGain={rfFrontEnd.rfGain}
              squelch={rfFrontEnd.squelch}
              att={rfFrontEnd.att}
              pre={rfFrontEnd.pre}
              digiSel={rfFrontEnd.digiSel}
              ipPlus={rfFrontEnd.ipPlus}
              onRfGainChange={rfHandlers.onRfGainChange}
              onSquelchChange={rfHandlers.onSquelchChange}
              onAttChange={rfHandlers.onAttChange}
              onPreChange={rfHandlers.onPreChange}
              onDigiSelToggle={rfHandlers.onDigiSelToggle}
              onIpPlusToggle={rfHandlers.onIpPlusToggle}
            />
          </CollapsiblePanel>

          <CollapsiblePanel title="RIT / XIT" panelId="m-rit">
            <RitXitPanel
              ritActive={ritXit.ritActive}
              ritOffset={ritXit.ritOffset}
              xitActive={ritXit.xitActive}
              xitOffset={ritXit.xitOffset}
              hasRit={ritXit.hasRit}
              hasXit={ritXit.hasXit}
              onRitToggle={ritXitHandlers.onRitToggle}
              onXitToggle={ritXitHandlers.onXitToggle}
              onRitOffsetChange={ritXitHandlers.onRitOffsetChange}
              onXitOffsetChange={ritXitHandlers.onXitOffsetChange}
              onClear={ritXitHandlers.onClear}
            />
          </CollapsiblePanel>

          <CollapsiblePanel title="CW" panelId="m-cw">
            <CwPanel
              wpm={cw.wpm}
              breakInActive={cw.breakInActive}
              breakInDelay={cw.breakInDelay}
              sidetonePitch={cw.sidetonePitch}
              sidetoneLevel={cw.sidetoneLevel}
              reversePaddle={cw.reversePaddle}
              keyerType={cw.keyerType}
              hasCw={cw.hasCw}
              onWpmChange={cwHandlers.onWpmChange}
              onBreakInToggle={cwHandlers.onBreakInToggle}
              onBreakInDelayChange={cwHandlers.onBreakInDelayChange}
              onSidetonePitchChange={cwHandlers.onSidetonePitchChange}
              onSidetoneLevelChange={cwHandlers.onSidetoneLevelChange}
              onReversePaddleToggle={cwHandlers.onReversePaddleToggle}
              onKeyerTypeChange={cwHandlers.onKeyerTypeChange}
            />
          </CollapsiblePanel>
        </div>
      </div>
    </div>
  {/if}

  <!-- ═══ MODE MODAL ═══ -->
  {#if modeModalOpen}
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="m-sheet-backdrop" onclick={() => (modeModalOpen = false)}>
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <div class="m-sheet m-sheet--compact" onclick={(e) => e.stopPropagation()}>
        <div class="m-sheet-handle"></div>
        <div class="m-sheet-title">ALL MODES</div>
        <div class="m-sheet-content">
          <div class="m-mode-grid">
            {#each mode.modes as m}
              <HardwareButton
                active={mode.currentMode === m}
                indicator="edge-left"
                color="cyan"
                onclick={() => { modeHandlers.onModeChange(m); modeModalOpen = false; }}
              >
                {m}
              </HardwareButton>
            {/each}
          </div>
          {#if mode.hasDataMode}
            <div class="m-sheet-subtitle">DATA MODE</div>
            <div class="m-mode-grid">
              {#each Array.from({ length: Math.max(0, (mode.dataModeCount ?? 0)) + 1 }, (_, i) => i) as d}
                <HardwareButton
                  active={mode.dataMode === d}
                  indicator="edge-left"
                  color="cyan"
                  onclick={() => { modeHandlers.onDataModeChange(d); }}
                >
                  {d === 0 ? 'OFF' : `D${d}`}
                </HardwareButton>
              {/each}
            </div>
          {/if}
        </div>
      </div>
    </div>
  {/if}

  <!-- ═══ FILTER MODAL ═══ -->
  {#if filterModalOpen}
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="m-sheet-backdrop" onclick={() => (filterModalOpen = false)}>
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <div class="m-sheet" onclick={(e) => e.stopPropagation()}>
        <div class="m-sheet-handle"></div>
        <div class="m-sheet-title">FILTER SETTINGS</div>
        <div class="m-sheet-content">
          <FilterPanel
            currentMode={filter.currentMode}
            currentFilter={filter.currentFilter}
            filterShape={filter.filterShape}
            filterLabels={filter.filterLabels}
            filterWidth={filter.filterWidth}
            filterWidthMin={filter.filterWidthMin}
            filterWidthMax={filter.filterWidthMax}
            filterConfig={filter.filterConfig}
            ifShift={filter.ifShift}
            hasPbt={filter.hasPbt}
            pbtInner={filter.pbtInner}
            pbtOuter={filter.pbtOuter}
            onFilterChange={filterHandlers.onFilterChange}
            onFilterWidthChange={filterHandlers.onFilterWidthChange}
            onFilterShapeChange={filterHandlers.onFilterShapeChange}
            onFilterPresetChange={filterHandlers.onFilterPresetChange}
            onFilterDefaults={filterHandlers.onFilterDefaults}
            onIfShiftChange={filterHandlers.onIfShiftChange}
            onPbtInnerChange={filterHandlers.onPbtInnerChange}
            onPbtOuterChange={filterHandlers.onPbtOuterChange}
            onPbtReset={filterHandlers.onPbtReset}
          />
        </div>
      </div>
    </div>
  {/if}

  <!-- ═══ POWER MODAL ═══ -->
  {#if powerModalOpen}
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="m-sheet-backdrop" onclick={() => (powerModalOpen = false)}>
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <div class="m-sheet m-sheet--compact" onclick={(e) => e.stopPropagation()}>
        <div class="m-sheet-handle"></div>
        <div class="m-sheet-title">RF POWER</div>
        <div class="m-sheet-content" style="padding: 12px;">
          <ValueControl
            label="RF Power"
            value={tx.rfPower}
            min={0}
            max={255}
            step={1}
            renderer="hbar"
            displayFn={rawToPercentDisplay}
            accentColor="var(--v2-accent-red)"
            onChange={txHandlers.onRfPowerChange}
            variant="hardware-illuminated"
          />
        </div>
      </div>
    </div>
  {/if}

  <!-- ═══ TX SETTINGS MODAL ═══ -->
  {#if txSettingsOpen}
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="m-sheet-backdrop" onclick={() => (txSettingsOpen = false)}>
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <div class="m-sheet" onclick={(e) => e.stopPropagation()}>
        <div class="m-sheet-handle"></div>
        <div class="m-sheet-title">TX SETTINGS</div>
        <div class="m-sheet-content">
          <TxPanel
            txActive={tx.txActive}
            rfPower={tx.rfPower}
            micGain={tx.micGain}
            atuActive={tx.atuActive}
            atuTuning={tx.atuTuning}
            voxActive={tx.voxActive}
            compActive={tx.compActive}
            compLevel={tx.compLevel}
            monActive={tx.monActive}
            monLevel={tx.monLevel}
            driveGain={tx.driveGain}
            onRfPowerChange={txHandlers.onRfPowerChange}
            onMicGainChange={txHandlers.onMicGainChange}
            onAtuToggle={txHandlers.onAtuToggle}
            onAtuTune={txHandlers.onAtuTune}
            onVoxToggle={txHandlers.onVoxToggle}
            onCompToggle={txHandlers.onCompToggle}
            onCompLevelChange={txHandlers.onCompLevelChange}
            onMonToggle={txHandlers.onMonToggle}
            onMonLevelChange={txHandlers.onMonLevelChange}
            onDriveGainChange={txHandlers.onDriveGainChange}
          />
        </div>
      </div>
    </div>
  {/if}
</div>
{/if}

<style>
  /* ── Landscape layout ── */
  .m-landscape {
    position: fixed;
    top: 0;
    left: 0;
    width: 100dvw;
    height: 100dvh;
    background: #000;
    z-index: 50;
    display: flex;
    flex-direction: column;
  }

  .m-ls-spectrum {
    flex: 1;
    min-height: 0;
    position: relative;
  }

  .m-ls-spectrum > :global(.spectrum-panel) {
    height: 100% !important;
    border: none !important;
    border-radius: 0 !important;
  }

  .m-ls-overlay {
    position: absolute;
    top: env(safe-area-inset-top, 0px);
    left: env(safe-area-inset-left, 0px);
    right: env(safe-area-inset-right, 0px);
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 4px 8px;
    background: rgba(0, 0, 0, 0.65);
    backdrop-filter: blur(4px);
    -webkit-backdrop-filter: blur(4px);
    z-index: 60;
    pointer-events: auto;
  }

  .m-ls-vfo {
    display: flex;
    align-items: baseline;
    gap: 8px;
    flex: 1;
    min-width: 0;
  }

  .m-ls-vfo > :global(:first-child) {
    flex-shrink: 0;
  }

  .m-ls-quick-modes {
    display: flex;
    gap: 2px;
  }

  .m-ls-mode-btn {
    font-family: 'Roboto Mono', monospace;
    font-size: 10px;
    font-weight: 700;
    padding: 3px 8px;
    border-radius: 3px;
    border: 1px solid rgba(0, 212, 255, 0.3);
    background: transparent;
    color: rgba(0, 212, 255, 0.6);
    cursor: pointer;
    -webkit-tap-highlight-color: transparent;
    transition: all 0.15s;
    letter-spacing: 0.06em;
  }

  .m-ls-mode-active {
    background: rgba(0, 212, 255, 0.25);
    color: #00d4ff;
    border-color: #00d4ff;
  }

  .m-ls-filter {
    font-family: 'Roboto Mono', monospace;
    font-size: 10px;
    font-weight: 700;
    padding: 3px 6px;
    border-radius: 3px;
    background: rgba(156, 163, 175, 0.15);
    color: #9ca3af;
    letter-spacing: 0.06em;
  }

  .m-ls-meter {
    display: flex;
    align-items: baseline;
    gap: 6px;
  }

  .m-ls-smeter {
    font-family: 'Roboto Mono', monospace;
    font-size: 13px;
    font-weight: 700;
    color: #4ade80;
  }

  .m-ls-dbm {
    font-family: 'Roboto Mono', monospace;
    font-size: 10px;
    color: #9ca3af;
  }

  .m-ls-controls {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .m-ls-step-btn {
    font-family: 'Roboto Mono', monospace;
    font-size: 10px;
    font-weight: 700;
    color: #e0e0e0;
    background: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 4px;
    padding: 4px 8px;
    cursor: pointer;
    min-height: 32px;
    -webkit-tap-highlight-color: transparent;
  }

  .m-ls-tune-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 32px;
    border-radius: 4px;
    border: 1px solid rgba(255, 255, 255, 0.2);
    background: rgba(255, 255, 255, 0.08);
    color: #e0e0e0;
    cursor: pointer;
    -webkit-tap-highlight-color: transparent;
  }

  .m-ls-tune-btn:active {
    background: rgba(255, 255, 255, 0.2);
  }

  .m-ls-ptt {
    font-family: 'Roboto Mono', monospace;
    font-size: 11px;
    font-weight: 700;
    min-width: 52px;
    min-height: 32px;
    padding: 4px 10px;
    border-radius: 4px;
    border: 2px solid var(--v2-accent-red, #ef4444);
    background: rgba(239, 68, 68, 0.15);
    color: var(--v2-accent-red, #ef4444);
    cursor: pointer;
    -webkit-tap-highlight-color: transparent;
    transition: background 0.15s, color 0.15s;
  }

  .m-ls-ptt.m-ptt-held {
    background: var(--v2-accent-red, #ef4444);
    color: #fff;
    box-shadow: 0 0 16px rgba(239, 68, 68, 0.5);
  }

  .m-ls-ptt.m-ptt-latched {
    background: #dc2626;
    color: #fff;
    box-shadow: 0 0 20px rgba(220, 38, 38, 0.6);
    animation: ptt-latch-pulse 1s ease-in-out infinite;
  }

  .m-ls-step-picker {
    position: fixed;
    bottom: 50%;
    right: env(safe-area-inset-right, 8px);
    z-index: 1000;
    display: flex;
    flex-direction: column;
    gap: 2px;
    background: rgba(10, 10, 15, 0.95);
    border: 1px solid rgba(42, 42, 62, 0.8);
    border-radius: 6px;
    padding: 4px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.6);
  }

  /* ── Base layout ── */
  .m-layout {
    display: flex;
    flex-direction: column;
    height: 100vh;
    height: 100dvh;
    background: linear-gradient(180deg, var(--v2-bg-gradient-start) 0%, var(--v2-bg-darkest) 100%);
    overflow: hidden;
    padding-top: env(safe-area-inset-top, 0px);
  }

  /* ── Sticky VFO header ── */
  .m-vfo-bar {
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    gap: 2px;
    padding: 8px 10px 4px;
    background: var(--v2-bg-card, #111);
    border-bottom: 1px solid var(--v2-border-panel, #333);
    z-index: 10;
  }

  .m-tx-indicator {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
    transition: background 0.2s, box-shadow 0.2s;
  }

  .m-vfo-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  .m-vfo-freq {
    line-height: 1;
    flex: 1;
  }

  .m-vfo-freq :global(.freq) {
    font-size: 28px;
  }

  .m-settings-btn {
    display: flex;
    align-items: center;
    gap: 4px;
    height: 32px;
    padding: 0 10px;
    border-radius: 4px;
    border: 1px solid var(--v2-border-darker, #333);
    background: var(--v2-bg-input, #1a1a2e);
    color: var(--v2-text-secondary, #aaa);
    font-family: 'Roboto Mono', monospace;
    font-weight: 700;
    font-size: 9px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    cursor: pointer;
    -webkit-tap-highlight-color: transparent;
    flex-shrink: 0;
  }

  .m-settings-btn:active {
    background: var(--v2-bg-card, #222);
  }

  .m-vfo-meta {
    display: flex;
    align-items: center;
    gap: 8px;
    font-family: 'Roboto Mono', monospace;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--v2-text-muted, #888);
  }

  .m-vfo-mode {
    color: var(--v2-accent-cyan, #22d3ee);
    padding: 2px 8px;
    border: 1px solid var(--v2-accent-cyan, #22d3ee);
    border-radius: 3px;
    font-size: 11px;
  }

  .m-vfo-filter {
    color: var(--v2-text-secondary, #aaa);
    font-size: 11px;
  }

  .m-vfo-sub {
    font-family: 'Roboto Mono', monospace;
    font-size: 10px;
    color: var(--v2-text-dim, #666);
    margin-left: auto;
    letter-spacing: 0.02em;
  }

  .m-vfo-sub::before {
    content: 'SUB ';
    font-size: 8px;
    font-weight: 700;
    color: var(--v2-text-dim, #555);
    letter-spacing: 0.08em;
  }

  /* ── S-meter bar (full width, below VFO) ── */
  .m-vfo-ops-row {
    display: flex;
    gap: 4px;
    margin-bottom: 8px;
  }

  .m-vfo-ops-row > :global(button) {
    flex: 1 1 0;
    min-width: 0;
    min-height: 36px;
  }

  .m-tx-meter {
    padding: 4px 8px 0;
    border-top: 1px solid var(--v2-border-darker, #1a1a2e);
  }

  .m-smeter-bar {
    flex-shrink: 0;
    padding: 2px 4px;
    background: var(--v2-bg-darker, #0a0a14);
    border-bottom: 1px solid var(--v2-border-darker, #1a1a2e);
  }

  /* ── Scrollable content ── */
  .m-content {
    flex: 1;
    overflow-y: auto;
    overflow-x: hidden;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: none;
  }

  .m-content::-webkit-scrollbar {
    display: none;
  }

  /* ── Spectrum ── */
  .m-spectrum {
    height: 220px;
    min-height: 180px;
    border-bottom: 1px solid var(--v2-border-darker, #222);
  }

  .m-spectrum :global(.spectrum-panel) {
    height: 100%;
    border: none;
    border-radius: 0;
    box-shadow: none;
  }

  /* ── Sections ── */
  .m-section {
    display: flex;
    flex-direction: column;
  }

  .m-section :global(.collapsible-panel) {
    border-radius: 0;
    border-left: none;
    border-right: none;
  }

  /* ── Quick grid (mode, filter quick buttons) ── */
  .m-quick-grid {
    display: flex;
    gap: 4px;
    padding: 7px 8px;
    flex-wrap: wrap;
  }

  .m-quick-grid > :global(button) {
    flex: 1 1 auto;
    min-width: 52px;
    min-height: 40px;
  }

  /* ── Audio content ── */
  .m-audio-content {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 7px 8px;
  }

  .m-audio-buttons {
    display: flex;
    gap: 4px;
  }

  .m-audio-buttons > :global(button) {
    flex: 1 1 0;
    min-width: 0;
    min-height: 36px;
  }

  .m-dsp-toggles {
    display: flex;
    gap: 4px;
  }

  .m-dsp-toggles > :global(button) {
    flex: 1 1 0;
    min-width: 0;
    min-height: 36px;
  }

  /* ── TX compact section ── */
  .m-tx-compact {
    display: flex;
    align-items: stretch;
    gap: 4px;
    padding: 8px;
    min-height: 44px;
  }

  

  .m-ptt-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    flex: 1.5;
    min-height: 44px;
    padding: 4px 16px;
    border-radius: 4px;
    border: 2px solid var(--v2-accent-red, #ef4444);
    background: rgba(239, 68, 68, 0.15);
    color: var(--v2-accent-red, #ef4444);
    font-family: 'Roboto Mono', monospace;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.08em;
    cursor: pointer;
    -webkit-tap-highlight-color: transparent;
    transition: background 0.15s, border-color 0.15s, color 0.15s, box-shadow 0.15s;
    user-select: none;
    -webkit-user-select: none;
    flex-shrink: 0;
  }

  .m-ptt-held {
    background: var(--v2-accent-red, #ef4444);
    border-color: var(--v2-accent-red, #ef4444);
    color: #fff;
    box-shadow: 0 0 20px rgba(239, 68, 68, 0.5);
  }

  .m-ptt-latched {
    background: #dc2626;
    border-color: #dc2626;
    color: #fff;
    box-shadow: 0 0 24px rgba(220, 38, 38, 0.6);
    animation: ptt-latch-pulse 1s ease-in-out infinite;
  }

  @keyframes ptt-latch-pulse {
    0%, 100% { box-shadow: 0 0 24px rgba(220, 38, 38, 0.6); }
    50% { box-shadow: 0 0 32px rgba(220, 38, 38, 0.8); }
  }

  .m-tx-info {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-width: 44px;
    min-height: 44px;
    padding: 4px 8px;
    border-radius: 4px;
    border: 1px solid var(--v2-border-darker, #333);
    background: var(--v2-bg-input, #1a1a2e);
    cursor: pointer;
    -webkit-tap-highlight-color: transparent;
  }

  .m-tx-info:active {
    background: var(--v2-bg-card, #222);
  }

  .m-tx-power-value {
    font-family: 'Roboto Mono', monospace;
    font-size: 13px;
    font-weight: 700;
    color: var(--v2-text-primary, #ddd);
    letter-spacing: 0.02em;
    white-space: nowrap;
  }

  .m-tx-swr-value {
    font-family: 'Roboto Mono', monospace;
    font-size: 9px;
    color: var(--v2-text-dim, #888);
    white-space: nowrap;
  }

  .m-atu-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 4px;
    min-width: 44px;
    min-height: 44px;
    padding: 4px 10px;
    border-radius: 4px;
    border: 1px solid var(--v2-text-dim, #444);
    background: var(--v2-bg-input, #1a1a2e);
    color: var(--v2-text-muted, #888);
    font-family: 'Roboto Mono', monospace;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.06em;
    cursor: pointer;
    -webkit-tap-highlight-color: transparent;
    transition: all 0.15s;
  }

  .m-atu-on {
    border-color: var(--v2-accent-green, #4ade80);
    color: var(--v2-accent-green, #4ade80);
    background: rgba(74, 222, 128, 0.1);
  }

  .m-atu-tuning {
    border-color: var(--v2-accent-yellow, #facc15);
    color: var(--v2-accent-yellow, #facc15);
    background: rgba(250, 204, 21, 0.1);
    animation: atu-pulse 0.6s ease-in-out infinite;
  }

  @keyframes atu-pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
  }

  .m-tx-settings-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    min-width: 44px;
    min-height: 44px;
    padding: 4px 8px;
    border-radius: 4px;
    border: 1px solid var(--v2-border-darker, #333);
    background: var(--v2-bg-input, #1a1a2e);
    color: var(--v2-text-muted, #888);
    font-family: 'Roboto Mono', monospace;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.06em;
    cursor: pointer;
    -webkit-tap-highlight-color: transparent;
  }

  .m-tx-settings-btn:active {
    background: var(--v2-bg-card, #222);
  }

  /* ── Bottom spacer ── */
  .m-bottom-spacer {
    height: calc(52px + env(safe-area-inset-bottom, 0px));
    flex-shrink: 0;
  }

  /* ── Tuning strip ── */
  .m-tuning-strip {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    display: flex;
    align-items: stretch;
    height: 52px;
    padding-bottom: env(safe-area-inset-bottom, 0px);
    background: var(--v2-bg-card, #111);
    border-top: 1px solid var(--v2-border-panel, #333);
    z-index: 100;
    gap: 1px;
  }

  .m-tune-btn {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--v2-bg-input, #1a1a2e);
    border: none;
    color: var(--v2-text-primary, #ddd);
    cursor: pointer;
    -webkit-tap-highlight-color: transparent;
    transition: background 0.1s;
    min-height: 44px;
  }

  .m-tune-btn:active {
    background: var(--v2-accent-cyan, #22d3ee);
    color: var(--v2-bg-darkest, #000);
  }

  .m-tune-fast {
    flex: 0.7;
    color: var(--v2-text-muted, #888);
  }

  .m-tune-fast:active {
    background: var(--v2-accent-cyan, #22d3ee);
    color: var(--v2-bg-darkest, #000);
  }

  .m-tune-step {
    flex: 1.2;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--v2-bg-darker, #0a0a14);
    border: 1px solid var(--v2-border-panel, #333);
    border-top: none;
    border-bottom: none;
    color: var(--v2-accent-cyan, #22d3ee);
    font-family: 'Roboto Mono', monospace;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.04em;
    cursor: pointer;
    -webkit-tap-highlight-color: transparent;
    min-height: 44px;
  }

  .m-tune-step:active {
    background: var(--v2-bg-input, #1a1a2e);
  }

  .m-tune-step-wrapper {
    position: relative;
    flex: 1.2;
    display: flex;
  }

  .m-tune-step-wrapper .m-tune-step {
    flex: 1;
  }

  .m-step-picker-backdrop {
    position: fixed;
    inset: 0;
    z-index: 149;
  }

  .m-step-picker {
    position: absolute;
    bottom: 100%;
    left: 50%;
    transform: translateX(-50%);
    margin-bottom: 4px;
    display: flex;
    flex-direction: column;
    gap: 1px;
    background: var(--v2-bg-primary, #0f0f1a);
    border: 1px solid var(--v2-border-panel, #333);
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 -8px 24px rgba(0, 0, 0, 0.5);
    z-index: 150;
    min-width: 100px;
  }

  .m-step-option {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 10px 16px;
    background: var(--v2-bg-card, #111);
    border: none;
    color: var(--v2-text-primary, #ddd);
    font-family: 'Roboto Mono', monospace;
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.04em;
    cursor: pointer;
    -webkit-tap-highlight-color: transparent;
    min-height: 44px;
  }

  .m-step-option:active {
    background: var(--v2-bg-input, #1a1a2e);
  }

  .m-step-active {
    color: var(--v2-accent-cyan, #22d3ee);
    background: rgba(34, 211, 238, 0.1);
    font-weight: 700;
  }

  /* ── Bottom sheets ── */
  .m-sheet-backdrop {
    position: fixed;
    inset: 0;
    z-index: 200;
    background: rgba(0, 0, 0, 0.5);
    backdrop-filter: blur(2px);
  }

  .m-sheet {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    max-height: 80vh;
    background: var(--v2-bg-primary, #0f0f1a);
    border-top: 1px solid var(--v2-border-panel, #333);
    border-radius: 16px 16px 0 0;
    overflow-y: auto;
    -webkit-overflow-scrolling: touch;
    z-index: 201;
    padding-bottom: env(safe-area-inset-bottom, 0px);
  }

  .m-sheet--compact {
    max-height: 50vh;
  }

  .m-sheet-handle {
    width: 36px;
    height: 4px;
    background: var(--v2-text-dim, #444);
    border-radius: 2px;
    margin: 10px auto 6px;
  }

  .m-sheet-title {
    text-align: center;
    font-family: 'Roboto Mono', monospace;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.12em;
    color: var(--v2-text-secondary, #aaa);
    padding: 0 0 8px;
    border-bottom: 1px solid var(--v2-border-darker, #222);
  }

  .m-sheet-subtitle {
    font-family: 'Roboto Mono', monospace;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.08em;
    color: var(--v2-text-dim, #555);
    padding: 10px 10px 4px;
    text-transform: uppercase;
  }

  .m-sheet-content {
    display: flex;
    flex-direction: column;
    gap: 0;
    padding: 4px 0;
  }

  .m-sheet-content :global(.collapsible-panel) {
    border-radius: 0;
    border-left: none;
    border-right: none;
  }

  /* ── Mode grid (in modal) ── */
  .m-mode-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 4px;
    padding: 8px 10px;
  }

  .m-mode-grid > :global(button) {
    min-height: 44px;
  }
</style>
