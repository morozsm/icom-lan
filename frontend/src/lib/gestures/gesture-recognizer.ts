// Framework-agnostic gesture recognizer using Pointer Events API.
// Handles tap, double-tap, swipe, pinch-to-zoom, drag/pan, and long press.

export interface GestureCallbacks {
  onTap?: (x: number, y: number) => void;
  onDoubleTap?: (x: number, y: number) => void;
  onSwipe?: (dir: 'left' | 'right' | 'up' | 'down', velocity: number, distance: number) => void;
  onPinch?: (scale: number, centerX: number, centerY: number) => void;
  onPan?: (dx: number, dy: number) => void;
  onPanEnd?: () => void;
  onLongPress?: (x: number, y: number) => void;
}

interface PointerState {
  id: number;
  startX: number;
  startY: number;
  currentX: number;
  currentY: number;
  startTime: number;
}

const TAP_MOVE_THRESHOLD = 10; // px — max movement for a tap
const TAP_TIME_THRESHOLD = 300; // ms — max duration for a tap
const LONG_PRESS_DELAY = 500; // ms
const PTT_HOLD_DELAY = 200; // ms — min hold before activation
const DOUBLE_TAP_WINDOW = 300; // ms between taps

export function createGestureRecognizer(
  element: HTMLElement,
  callbacks: GestureCallbacks,
): { destroy: () => void } {
  const pointers = new Map<number, PointerState>();
  let longPressTimer: ReturnType<typeof setTimeout> | null = null;
  let lastTapTime = 0;
  let lastTapX = 0;
  let lastTapY = 0;
  let isPanning = false;
  let panLastX = 0;
  let panLastY = 0;
  let pinchLastDist = 0;
  let pinchLastCx = 0;
  let pinchLastCy = 0;

  element.style.touchAction = 'none';

  function clearLongPress() {
    if (longPressTimer !== null) {
      clearTimeout(longPressTimer);
      longPressTimer = null;
    }
  }

  function distance(a: PointerState, b: PointerState): number {
    const dx = a.currentX - b.currentX;
    const dy = a.currentY - b.currentY;
    return Math.sqrt(dx * dx + dy * dy);
  }

  function midpoint(a: PointerState, b: PointerState): [number, number] {
    return [(a.currentX + b.currentX) / 2, (a.currentY + b.currentY) / 2];
  }

  function onPointerDown(e: PointerEvent) {
    element.setPointerCapture(e.pointerId);
    const state: PointerState = {
      id: e.pointerId,
      startX: e.clientX,
      startY: e.clientY,
      currentX: e.clientX,
      currentY: e.clientY,
      startTime: e.timeStamp,
    };
    pointers.set(e.pointerId, state);

    if (pointers.size === 1) {
      isPanning = false;
      panLastX = e.clientX;
      panLastY = e.clientY;

      // Long press timer
      clearLongPress();
      longPressTimer = setTimeout(() => {
        longPressTimer = null;
        const p = pointers.get(e.pointerId);
        if (p && pointers.size === 1) {
          const dx = p.currentX - p.startX;
          const dy = p.currentY - p.startY;
          const moved = Math.sqrt(dx * dx + dy * dy);
          if (moved < TAP_MOVE_THRESHOLD) {
            callbacks.onLongPress?.(p.currentX, p.currentY);
          }
        }
      }, LONG_PRESS_DELAY);
    } else if (pointers.size === 2) {
      // Starting pinch — cancel long press and pan
      clearLongPress();
      isPanning = false;
      const pts = Array.from(pointers.values());
      pinchLastDist = distance(pts[0], pts[1]);
      const [cx, cy] = midpoint(pts[0], pts[1]);
      pinchLastCx = cx;
      pinchLastCy = cy;
    }
  }

  function onPointerMove(e: PointerEvent) {
    const p = pointers.get(e.pointerId);
    if (!p) return;
    p.currentX = e.clientX;
    p.currentY = e.clientY;

    if (pointers.size === 2) {
      // Pinch
      const pts = Array.from(pointers.values());
      const dist = distance(pts[0], pts[1]);
      if (pinchLastDist > 0) {
        const scale = dist / pinchLastDist;
        const [cx, cy] = midpoint(pts[0], pts[1]);
        callbacks.onPinch?.(scale, cx, cy);
        pinchLastDist = dist;
        pinchLastCx = cx;
        pinchLastCy = cy;
      }
    } else if (pointers.size === 1) {
      const dx = e.clientX - p.startX;
      const dy = e.clientY - p.startY;
      const moved = Math.sqrt(dx * dx + dy * dy);

      if (moved > TAP_MOVE_THRESHOLD) {
        clearLongPress();
        isPanning = true;
        const pdx = e.clientX - panLastX;
        const pdy = e.clientY - panLastY;
        if (pdx !== 0 || pdy !== 0) {
          callbacks.onPan?.(pdx, pdy);
        }
        panLastX = e.clientX;
        panLastY = e.clientY;
      }
    }
  }

  function onPointerUp(e: PointerEvent) {
    const p = pointers.get(e.pointerId);
    if (!p) return;

    clearLongPress();
    const wasPanning = isPanning;
    const wasMultiTouch = pointers.size > 1;

    pointers.delete(e.pointerId);

    if (pointers.size === 0) {
      if (wasPanning) {
        callbacks.onPanEnd?.();
        isPanning = false;
        return;
      }

      if (wasMultiTouch) return;

      // Check if it's a tap
      const elapsed = e.timeStamp - p.startTime;
      const dx = e.clientX - p.startX;
      const dy = e.clientY - p.startY;
      const moved = Math.sqrt(dx * dx + dy * dy);

      if (moved < TAP_MOVE_THRESHOLD && elapsed < TAP_TIME_THRESHOLD) {
        const now = e.timeStamp;
        const dxTap = e.clientX - lastTapX;
        const dyTap = e.clientY - lastTapY;
        const distFromLast = Math.sqrt(dxTap * dxTap + dyTap * dyTap);

        if (now - lastTapTime < DOUBLE_TAP_WINDOW && distFromLast < TAP_MOVE_THRESHOLD * 3) {
          lastTapTime = 0; // reset so triple-tap doesn't trigger another double
          callbacks.onDoubleTap?.(e.clientX, e.clientY);
        } else {
          lastTapTime = now;
          lastTapX = e.clientX;
          lastTapY = e.clientY;
          callbacks.onTap?.(e.clientX, e.clientY);
        }
        return;
      }

      // Swipe detection
      if (elapsed < TAP_TIME_THRESHOLD * 2 && moved > TAP_MOVE_THRESHOLD) {
        const velocity = moved / elapsed; // px/ms
        if (Math.abs(dx) > Math.abs(dy)) {
          callbacks.onSwipe?.(dx > 0 ? 'right' : 'left', velocity, Math.abs(dx));
        } else {
          callbacks.onSwipe?.(dy > 0 ? 'down' : 'up', velocity, Math.abs(dy));
        }
      }
    } else if (pointers.size === 1) {
      // Back to single finger after pinch — reset pan tracking
      const remaining = Array.from(pointers.values())[0];
      panLastX = remaining.currentX;
      panLastY = remaining.currentY;
      pinchLastDist = 0;
    }
  }

  function onPointerCancel(e: PointerEvent) {
    clearLongPress();
    pointers.delete(e.pointerId);
    if (pointers.size === 0 && isPanning) {
      callbacks.onPanEnd?.();
      isPanning = false;
    }
  }

  element.addEventListener('pointerdown', onPointerDown);
  element.addEventListener('pointermove', onPointerMove);
  element.addEventListener('pointerup', onPointerUp);
  element.addEventListener('pointercancel', onPointerCancel);

  return {
    destroy() {
      clearLongPress();
      element.removeEventListener('pointerdown', onPointerDown);
      element.removeEventListener('pointermove', onPointerMove);
      element.removeEventListener('pointerup', onPointerUp);
      element.removeEventListener('pointercancel', onPointerCancel);
      element.style.touchAction = '';
    },
  };
}
