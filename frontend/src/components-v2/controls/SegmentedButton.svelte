<script lang="ts">
  import './control-button.css';

  interface Option {
    value: string | number;
    label: string;
  }

  interface Props {
    options: Option[];
    selected: string | number;
    onchange: (value: string | number) => void;
    accentColor?: string;
    compact?: boolean;
    disabled?: boolean;
    title?: string | null;
  }

  let {
    options,
    selected,
    onchange,
    accentColor = 'var(--v2-accent-cyan)',
    compact = false,
    disabled = false,
    title = null,
  }: Props = $props();

  function handleKeydown(event: KeyboardEvent) {
    if (disabled) return;
    const currentIndex = options.findIndex((o) => o.value === selected);
    if (event.key === 'ArrowRight' || event.key === 'ArrowDown') {
      event.preventDefault();
      onchange(options[(currentIndex + 1) % options.length].value);
    } else if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') {
      event.preventDefault();
      onchange(options[(currentIndex - 1 + options.length) % options.length].value);
    }
  }
</script>

<div
  class="segmented-button"
  class:compact
  class:disabled
  role="radiogroup"
  tabindex={disabled ? -1 : 0}
  style="--accent: {accentColor}"
  title={title ?? undefined}
  data-shortcut-hint={title ?? undefined}
  onkeydown={handleKeydown}
>
  {#each options as option, i}
    {@const isActive = option.value === selected}
    <button
      type="button"
      class="segment v2-control-button"
      class:active={isActive}
      class:first={i === 0}
      class:last={i === options.length - 1}
      role="radio"
      aria-checked={isActive}
      tabindex="-1"
      onclick={() => { if (!disabled) onchange(option.value); }}
    >
      {option.label}
    </button>
  {/each}
</div>

<style>
  .segmented-button {
    display: inline-flex;
    flex-direction: row;
    gap: 1px;
    outline: none;
    user-select: none;
  }

  .segmented-button:focus-visible {
    box-shadow: 0 0 0 2px var(--accent, var(--v2-accent-cyan));
    border-radius: 4px;
  }

  .segment {
    border-radius: 0;
  }

  .segment:focus {
    outline: none;
  }

  .segment.first {
    border-radius: 3px 0 0 3px;
  }

  .segment.last {
    border-radius: 0 3px 3px 0;
  }

  /* Single option: both sides rounded */
  .segment.first.last {
    border-radius: 3px;
  }

  .segment.active {
    z-index: 1;
    position: relative;
  }

  /* Compact mode */
  .compact .segment {
    min-height: 22px;
    padding: 2px 6px;
    font-size: 9px;
  }

  /* Disabled state */
  .disabled {
    opacity: 0.4;
    pointer-events: none;
  }
</style>
