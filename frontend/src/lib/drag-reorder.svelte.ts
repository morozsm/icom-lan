/**
 * Shared drag-to-reorder logic for sidebar panels.
 *
 * Usage:
 *   const drag = createDragReorder({
 *     storageKey: 'icom-lan:panel-order',
 *     defaults: ['rf-front-end', 'mode', ...],
 *     containerSelector: '.left-sidebar',
 *   });
 */

// --- Pure helpers (exported for testing) ---

export function loadPanelOrder(storageKey: string, defaults: string[]): string[] {
  try {
    const stored = localStorage.getItem(storageKey);
    if (stored) {
      const parsed = JSON.parse(stored);
      if (
        Array.isArray(parsed) &&
        parsed.length === defaults.length &&
        defaults.every((id) => parsed.includes(id))
      ) {
        return parsed;
      }
    }
  } catch {
    /* ignore */
  }
  return [...defaults];
}

export function reorderPanels(order: string[], fromId: string, toIndex: number): string[] {
  const fromIndex = order.indexOf(fromId);
  if (fromIndex < 0 || fromIndex === toIndex) return order;
  const newOrder = [...order];
  const [moved] = newOrder.splice(fromIndex, 1);
  newOrder.splice(toIndex, 0, moved);
  return newOrder;
}

// --- Reactive factory ---

export interface DragReorderOptions {
  storageKey: string;
  defaults: string[];
  containerSelector: string;
}

export function createDragReorder(options: DragReorderOptions) {
  const { storageKey, defaults, containerSelector } = options;

  let order = $state(loadPanelOrder(storageKey, defaults));
  let dragPanelId = $state<string | null>(null);
  let dropTargetIndex = $state<number>(-1);

  // Persist order changes
  $effect(() => {
    try {
      localStorage.setItem(storageKey, JSON.stringify(order));
    } catch {
      /* ignore */
    }
  });

  function orderOf(panelId: string): number {
    return order.indexOf(panelId);
  }

  function dragStyle(panelId: string): string {
    const idx = `order:${orderOf(panelId)};`;
    if (dragPanelId === panelId) return idx + 'opacity:0.5;transform:scale(0.98);';
    if (dragPanelId && orderOf(panelId) === dropTargetIndex)
      return idx + 'border-top:2px solid var(--v2-accent, #4af);';
    return idx;
  }

  function handleDragStart(panelId: string, event: PointerEvent) {
    const handle = event.currentTarget as HTMLElement;
    handle.setPointerCapture(event.pointerId);
    dragPanelId = panelId;
    dropTargetIndex = order.indexOf(panelId);

    const sidebar = handle.closest(containerSelector) as HTMLElement;
    if (!sidebar) return;

    const panels = Array.from(sidebar.querySelectorAll<HTMLElement>('[data-panel-id]'));
    const rects = new Map<string, DOMRect>();
    for (const p of panels) {
      rects.set(p.dataset.panelId!, p.getBoundingClientRect());
    }

    function onMove(e: PointerEvent) {
      let closest = 0;
      let minDist = Infinity;
      for (let i = 0; i < order.length; i++) {
        const rect = rects.get(order[i]);
        if (!rect) continue;
        const dist = Math.abs(e.clientY - (rect.top + rect.height / 2));
        if (dist < minDist) {
          minDist = dist;
          closest = i;
        }
      }
      dropTargetIndex = closest;
    }

    function onUp() {
      if (dragPanelId && dropTargetIndex >= 0) {
        const newOrder = reorderPanels(order, dragPanelId, dropTargetIndex);
        if (newOrder !== order) order = newOrder;
      }
      dragPanelId = null;
      dropTargetIndex = -1;
      handle.removeEventListener('pointermove', onMove);
      handle.removeEventListener('pointerup', onUp);
      handle.removeEventListener('pointercancel', onUp);
    }

    handle.addEventListener('pointermove', onMove);
    handle.addEventListener('pointerup', onUp);
    handle.addEventListener('pointercancel', onUp);
  }

  function reset() {
    order = [...defaults];
    try {
      localStorage.removeItem(storageKey);
    } catch {
      /* ignore */
    }
  }

  return {
    get order() {
      return order;
    },
    orderOf,
    dragStyle,
    handleDragStart,
    reset,
  };
}
