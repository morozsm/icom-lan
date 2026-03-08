<script lang="ts">
  import DesktopLayout from './DesktopLayout.svelte';
  import MobileLayout from './MobileLayout.svelte';

  const MOBILE_BREAKPOINT = 768;

  let width = $state(window.innerWidth);

  $effect(() => {
    function onResize() {
      width = window.innerWidth;
    }
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  });

  let isMobile = $derived(width < MOBILE_BREAKPOINT);
</script>

{#if isMobile}
  <MobileLayout />
{:else}
  <DesktopLayout />
{/if}
