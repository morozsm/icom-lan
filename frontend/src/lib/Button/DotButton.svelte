<script lang="ts">
  import ControlButton from './ControlButton.svelte';
  import type { DotButtonProps } from './types';

  interface Props extends DotButtonProps {
    children?: any;
  }

  let {
    active = false,
    disabled = false,
    compact = false,
    color = 'cyan',
    glow = 'color',
    onclick,
    children
  }: Props = $props();
</script>

<ControlButton
  {active}
  {disabled}
  {compact}
  indicatorStyle="dot"
  indicatorColor={color}
  {glow}
  {onclick}
>
  {@render children?.()}
</ControlButton>
