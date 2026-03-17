export function formatFilterWidth(hz: number): string {
  if (hz < 1000) return String(hz);
  const k = hz / 1000;
  return k % 1 === 0 ? `${k}k` : `${k.toFixed(1)}k`;
}
