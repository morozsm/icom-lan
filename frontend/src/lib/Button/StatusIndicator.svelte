<script lang="ts">
  import '../../components-v2/controls/control-button.css';

  type StatusIndicatorColor = 'cyan' | 'green' | 'orange' | 'red' | 'muted';
  type StatusIndicatorSize = 'default' | 'xs';

  interface Props {
    label: string;
    active?: boolean;
    color?: StatusIndicatorColor;
    size?: StatusIndicatorSize;
    title?: string | null;
  }

  let {
    label,
    active = false,
    color,
    size = 'default',
    title = null,
  }: Props = $props();
</script>

<span
  class="v2-status-indicator"
  class:v2-status-indicator--xs={size === 'xs'}
  data-active={active}
  data-color={color}
  title={title ?? undefined}
>
  {label}
</span>
