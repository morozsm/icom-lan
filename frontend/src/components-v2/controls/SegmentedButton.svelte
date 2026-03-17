<script lang="ts">
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
  }

  let {
    options,
    selected,
    onchange,
    accentColor = '#00D4FF',
    compact = false,
    disabled = false,
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
  onkeydown={handleKeydown}
>
  {#each options as option, i}
    {@const isActive = option.value === selected}
    <button
      type="button"
      class="segment"
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
    box-shadow: 0 0 0 2px var(--accent, #00D4FF);
    border-radius: 6px;
  }

  .segment {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 5px 10px;
    background-color: #0D1117;
    border: 1px solid #18202A;
    color: #6F8196;
    font-family: 'Roboto Mono', monospace;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.04em;
    cursor: pointer;
    border-radius: 0;
    transition:
      background-color 150ms ease,
      border-color 150ms ease,
      color 150ms ease,
      box-shadow 150ms ease;
    white-space: nowrap;
    line-height: 1;
  }

  .segment:focus {
    outline: none;
  }

  .segment.first {
    border-radius: 4px 0 0 4px;
  }

  .segment.last {
    border-radius: 0 4px 4px 0;
  }

  /* Single option: both sides rounded */
  .segment.first.last {
    border-radius: 4px;
  }

  .segment.active {
    background-color: color-mix(in srgb, var(--accent) 20%, #060A10);
    border-color: var(--accent, #00D4FF);
    color: #F0F5FA;
    box-shadow: 0 0 6px 0 color-mix(in srgb, var(--accent) 35%, transparent);
    z-index: 1;
    position: relative;
  }

  .segment:not(.active):hover:not(.disabled *) {
    background-color: #111820;
    color: #8DA2B8;
  }

  /* Compact mode */
  .compact .segment {
    padding: 3px 7px;
    font-size: 10px;
  }

  /* Disabled state */
  .disabled {
    opacity: 0.4;
    pointer-events: none;
  }
</style>
