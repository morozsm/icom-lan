<script lang="ts">
  import { vibrate } from '../../lib/utils/haptics';

  interface Props {
    digit: string;
    position: number; // 0=1Hz, 1=10Hz, 2=100Hz, 3=1kHz, 6=1MHz, etc.
    selected?: boolean;
    onselect?: (position: number) => void;
    onincrement?: (position: number, delta: number) => void;
  }

  let { digit, position, selected = false, onselect, onincrement }: Props = $props();

  let el = $state<HTMLSpanElement | undefined>(undefined);

  $effect(() => {
    const target = el;
    if (!target) return;
    const _position = position;
    const _onincrement = onincrement;
    const handleWheel = (e: WheelEvent) => {
      e.preventDefault();
      const delta = e.deltaY < 0 ? 1 : -1;
      vibrate('tune');
      _onincrement?.(_position, delta);
    };
    target.addEventListener('wheel', handleWheel, { passive: false });
    return () => target.removeEventListener('wheel', handleWheel);
  });

  function handleClick() {
    onselect?.(position);
  }

  function handleKeyDown(e: KeyboardEvent) {
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      vibrate('tune');
      onincrement?.(position, 1);
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      vibrate('tune');
      onincrement?.(position, -1);
    }
  }
</script>

<span
  bind:this={el}
  class="digit"
  class:selected
  role="spinbutton"
  tabindex={selected ? 0 : -1}
  aria-valuenow={Number(digit)}
  aria-label="Frequency digit, position {position}"
  onclick={handleClick}
  onkeydown={handleKeyDown}
>
  {digit}
</span>

<style>
  .digit {
    display: inline-block;
    font-family: var(--font-mono);
    font-size: 2rem;
    line-height: 1;
    cursor: pointer;
    padding: 0 2px;
    border-radius: 4px;
    user-select: none;
    transition:
      color 0.1s,
      background-color 0.1s;
    min-width: 1.2ch;
    text-align: center;
    color: inherit;
  }

  .digit:hover {
    background-color: rgba(77, 182, 255, 0.12);
    color: var(--accent);
  }

  .digit.selected {
    color: var(--accent);
    background-color: rgba(77, 182, 255, 0.2);
    outline: 1px solid var(--accent);
    outline-offset: 1px;
  }

  @media (max-width: 768px) {
    .digit {
      font-size: 1.5rem;
    }
  }
</style>
