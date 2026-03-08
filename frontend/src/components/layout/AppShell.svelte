<script lang="ts">
  import DesktopLayout from './DesktopLayout.svelte';
  import MobileLayout from './MobileLayout.svelte';
  import { setLayout } from '../../lib/stores/ui.svelte';
  import InstallPrompt from '../shared/InstallPrompt.svelte';
  import OfflineIndicator from '../shared/OfflineIndicator.svelte';
  import SwUpdateToast from '../shared/SwUpdateToast.svelte';

  const MOBILE_BREAKPOINT = 768;

  let width = $state(typeof window !== 'undefined' ? window.innerWidth : 1024);

  $effect(() => {
    function onResize() {
      width = window.innerWidth;
      setLayout(width < MOBILE_BREAKPOINT ? 'mobile' : 'desktop');
    }
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  });

  let isMobile = $derived(width < MOBILE_BREAKPOINT);
</script>

<OfflineIndicator />
<SwUpdateToast />

{#if isMobile}
  <MobileLayout />
{:else}
  <DesktopLayout />
{/if}

<InstallPrompt />
