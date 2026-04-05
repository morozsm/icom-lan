<script lang="ts">
  import { RefreshCw } from 'lucide-svelte';

  interface Props {
    onRefresh: () => Promise<void>;
    children?: any;
  }

  let { onRefresh, children }: Props = $props();

  const THRESHOLD = 80;

  let pulling = $state(false);
  let refreshing = $state(false);
  let pullDistance = $state(0);
  let startY = 0;
  let wrapper: HTMLDivElement | undefined = $state();

  /** Is the wrapper scrolled to the very top? */
  function isAtScrollTop(): boolean {
    if (!wrapper) return true;
    // Walk up to find the nearest scrollable ancestor
    let el: HTMLElement | null = wrapper;
    while (el) {
      if (el.scrollTop > 0) return false;
      el = el.parentElement;
    }
    return true;
  }

  function onPointerDown(e: PointerEvent) {
    // Only respond to touch (not mouse)
    if (e.pointerType !== 'touch') return;
    if (refreshing) return;
    if (!isAtScrollTop()) return;

    startY = e.clientY;
    pulling = true;
    pullDistance = 0;
  }

  function onPointerMove(e: PointerEvent) {
    if (!pulling) return;

    const dy = e.clientY - startY;
    if (dy < 0) {
      pullDistance = 0;
      return;
    }

    // Apply resistance: actual distance is 40% of finger movement
    pullDistance = dy * 0.4;
  }

  function onPointerUp() {
    if (!pulling) return;
    pulling = false;

    if (pullDistance >= THRESHOLD) {
      triggerRefresh();
    } else {
      pullDistance = 0;
    }
  }

  async function triggerRefresh() {
    refreshing = true;
    pullDistance = THRESHOLD; // Hold at threshold during refresh
    try {
      await onRefresh();
    } finally {
      refreshing = false;
      pullDistance = 0;
    }
  }

  let indicatorRotation = $derived(
    Math.min((pullDistance / THRESHOLD) * 360, 360)
  );

  let thresholdMet = $derived(pullDistance >= THRESHOLD);
</script>

<div
  class="pull-to-refresh-wrapper"
  role="region"
  aria-label="Pull to refresh"
  bind:this={wrapper}
  onpointerdown={onPointerDown}
  onpointermove={onPointerMove}
  onpointerup={onPointerUp}
  onpointercancel={onPointerUp}
>
  <div
    class="pull-indicator"
    class:visible={pullDistance > 0}
    class:threshold-met={thresholdMet}
    class:refreshing
    style:transform="translateY({pullDistance - 40}px)"
  >
    <div
      class="icon-wrap"
      class:spinning={refreshing}
      style:transform="rotate({indicatorRotation}deg)"
    >
      <RefreshCw size={20} />
    </div>
  </div>

  {@render children?.()}
</div>

<style>
  .pull-to-refresh-wrapper {
    position: relative;
    overscroll-behavior: contain;
    touch-action: pan-y;
  }

  .pull-indicator {
    position: absolute;
    top: 0;
    left: 50%;
    translate: -50% 0;
    z-index: 100;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 36px;
    border-radius: 50%;
    background: var(--v2-bg-primary, #0f0f1a);
    border: 1px solid var(--v2-text-dim, #444);
    color: var(--v2-text-dim, #444);
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.15s ease;
  }

  .pull-indicator.visible {
    opacity: 1;
  }

  .pull-indicator.threshold-met {
    color: var(--v2-accent-cyan, #22d3ee);
    border-color: var(--v2-accent-cyan, #22d3ee);
  }

  .icon-wrap {
    display: flex;
    align-items: center;
    justify-content: center;
    transition: transform 0.05s linear;
  }

  .icon-wrap.spinning {
    animation: spin 0.8s linear infinite;
    transition: none;
  }

  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }
</style>
