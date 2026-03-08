<script lang="ts">
  interface Props {
    width?: string;
    height?: string;
    radius?: string;
  }

  let { width = '100%', height = '1rem', radius = 'var(--radius)' }: Props = $props();
</script>

<div class="skeleton" style="width: {width}; height: {height}; border-radius: {radius}" aria-busy="true"></div>

<style>
  .skeleton {
    background: linear-gradient(
      90deg,
      var(--panel) 0%,
      var(--panel-border) 50%,
      var(--panel) 100%
    );
    background-size: 200% 100%;
    animation: shimmer 1.5s ease-in-out infinite;
  }

  @media (prefers-reduced-motion: reduce) {
    .skeleton {
      animation: none;
      background: var(--panel);
    }
  }
</style>
