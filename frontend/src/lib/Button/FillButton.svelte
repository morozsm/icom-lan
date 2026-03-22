<script lang="ts">
  import ControlButton from './ControlButton.svelte';
  import type { FillButtonProps } from './types';

  interface Props extends FillButtonProps {
    children?: any;
  }

  let {
    active = false,
    disabled = false,
    compact = false,
    color = 'cyan',
    title = null,
    shortcutHint = null,
    onclick,
    children
  }: Props = $props();
</script>

<ControlButton
  {active}
  {disabled}
  {compact}
  indicatorStyle="fill"
  indicatorColor={color}
  {title}
  {shortcutHint}
  {onclick}
>
  {@render children?.()}
</ControlButton>
