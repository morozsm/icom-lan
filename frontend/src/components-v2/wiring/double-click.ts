/**
 * Double-click / single-click dispatch helper.
 *
 * Returns an `onclick` handler that fires `onSingle` on a single tap,
 * and `onDouble` on two taps within `thresholdMs`.  On a double-click
 * the pending single-click is cancelled, so `onSingle` is NOT fired
 * on the first of the two taps.
 *
 * Why not `ondblclick`?  Because desktop browsers force a ~300ms delay
 * on `onclick` whenever both listeners are bound, and `ondblclick` is
 * not reliably fired on touch devices.  Rolling our own keeps the
 * single-click path instant on desktop and works on touch.
 *
 * Usage:
 * ```ts
 * const handler = withDoubleClick(
 *   () => console.log('single'),
 *   () => console.log('double'),
 * );
 * button.onclick = handler;
 * ```
 */
export function withDoubleClick(
  onSingle: () => void,
  onDouble: () => void,
  thresholdMs = 280,
): () => void {
  let pending: ReturnType<typeof setTimeout> | null = null;

  return () => {
    if (pending !== null) {
      clearTimeout(pending);
      pending = null;
      onDouble();
      return;
    }
    pending = setTimeout(() => {
      pending = null;
      onSingle();
    }, thresholdMs);
  };
}
