/** Lightweight haptic feedback for mobile */
export function vibrate(pattern: 'tick' | 'click' = 'tick'): void {
  if (!navigator.vibrate) return;
  navigator.vibrate(pattern === 'tick' ? 5 : 15);
}
