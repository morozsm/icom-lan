// Svelte action wrapper around createGestureRecognizer.
// Usage: <div use:gesture={callbacks}>

import { createGestureRecognizer, type GestureCallbacks } from './gesture-recognizer';

export type { GestureCallbacks };

export function gesture(
  node: HTMLElement,
  callbacks: GestureCallbacks,
): { update: (newCallbacks: GestureCallbacks) => void; destroy: () => void } {
  let current = callbacks;
  // Proxy object — we pass stable references that delegate to `current`
  const proxy: GestureCallbacks = {
    onTap: (x, y) => current.onTap?.(x, y),
    onDoubleTap: (x, y) => current.onDoubleTap?.(x, y),
    onSwipe: (dir, vel, dist) => current.onSwipe?.(dir, vel, dist),
    onPinch: (scale, cx, cy) => current.onPinch?.(scale, cx, cy),
    onPan: (dx, dy) => current.onPan?.(dx, dy),
    onPanEnd: () => current.onPanEnd?.(),
    onLongPress: (x, y) => current.onLongPress?.(x, y),
  };

  const recognizer = createGestureRecognizer(node, proxy);

  return {
    update(newCallbacks: GestureCallbacks) {
      current = newCallbacks;
    },
    destroy() {
      recognizer.destroy();
    },
  };
}
