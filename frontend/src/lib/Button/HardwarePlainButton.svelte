<script lang="ts">
  import ControlButton from './ControlButton.svelte';
  import type { HardwarePlainButtonProps } from './types';

  interface Props extends HardwarePlainButtonProps {
    children?: any;
  }

  let {
    active = false,
    disabled = false,
    compact = false,
    glow = 'warm',
    onclick,
    children
  }: Props = $props();
</script>

<ControlButton
  {active}
  {disabled}
  {compact}
  surface="hardware"
  {glow}
  {onclick}
>
  {@render children?.()}
</ControlButton>
