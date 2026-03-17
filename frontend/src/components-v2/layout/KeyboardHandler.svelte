<script lang="ts">
  import { getUiVersion } from '$lib/stores/ui-version.svelte';
  import { resolveAction, shouldIgnoreEvent } from './keyboard-map';
  import type { KeyAction } from './keyboard-map';

  interface Props {
    onTune: (direction: 'up' | 'down', fine: boolean) => void;
    onBandSelect: (index: number) => void;
    onModeSelect: (mode: string) => void;
    onPttToggle: () => void;
    onVfoSwap: () => void;
    onRitClear: () => void;
    onMonitorToggle: () => void;
    onNrToggle: () => void;
    onNbToggle: () => void;
    enabled?: boolean;
  }

  let {
    onTune,
    onBandSelect,
    onModeSelect,
    onPttToggle,
    onVfoSwap,
    onRitClear,
    onMonitorToggle,
    onNrToggle,
    onNbToggle,
    enabled = true,
  }: Props = $props();

  function dispatch(action: KeyAction): void {
    switch (action.type) {
      case 'tune':
        onTune(action.direction, action.fine);
        break;
      case 'bandSelect':
        onBandSelect(action.index);
        break;
      case 'modeSelect':
        onModeSelect(action.mode);
        break;
      case 'pttToggle':
        onPttToggle();
        break;
      case 'vfoSwap':
        onVfoSwap();
        break;
      case 'ritClear':
        onRitClear();
        break;
      case 'monitorToggle':
        onMonitorToggle();
        break;
      case 'nrToggle':
        onNrToggle();
        break;
      case 'nbToggle':
        onNbToggle();
        break;
    }
  }

  function handleKeydown(event: KeyboardEvent): void {
    if (!enabled || getUiVersion() !== 'v2') return;
    if (shouldIgnoreEvent(document.activeElement)) return;
    const action = resolveAction(event);
    if (!action) return;
    event.preventDefault();
    dispatch(action);
  }
</script>

<svelte:window onkeydown={handleKeydown} />
