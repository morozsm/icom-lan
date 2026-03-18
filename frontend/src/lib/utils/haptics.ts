/** Lightweight haptic feedback for mobile */
export function vibrate(pattern: 'tick' | 'click' | 'tap' | 'tune' | 'ptt' = 'tick'): void {
  if (!navigator.vibrate) return;
  const duration =
    pattern === 'tick' ? 5
      : pattern === 'tap' ? 10
      : pattern === 'tune' ? 8
      : pattern === 'ptt' ? 20
      : 15;
  navigator.vibrate(duration);
}
