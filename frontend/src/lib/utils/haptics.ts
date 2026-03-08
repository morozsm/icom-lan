export function vibrate(pattern: 'tap' | 'ptt' | 'tune' | 'error'): void {
  if (!navigator.vibrate) return;
  switch (pattern) {
    case 'tap':
      navigator.vibrate(10);
      break;
    case 'ptt':
      navigator.vibrate(50);
      break;
    case 'tune':
      navigator.vibrate([10, 30, 10]);
      break;
    case 'error':
      navigator.vibrate([100, 50, 100]);
      break;
  }
}
