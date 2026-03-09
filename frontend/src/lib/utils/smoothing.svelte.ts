/**
 * Exponential smoothing for meter values.
 * React useSmoothedValue → Svelte $state + rAF loop.
 */
export function createSmoother(attack = 0.12, release = 0.32) {
  let current = 0;
  let target = 0;
  let frameId = 0;
  let lastTime = 0;

  function update(newTarget: number) {
    target = newTarget;
  }

  function start() {
    lastTime = performance.now();

    const tick = (now: number) => {
      const dt = Math.min(0.05, (now - lastTime) / 1000);
      lastTime = now;

      const tau = target >= current ? attack : release;
      const alpha = 1 - Math.exp(-dt / tau);
      current += (target - current) * alpha;

      frameId = requestAnimationFrame(tick);
    };

    frameId = requestAnimationFrame(tick);
  }

  function stop() {
    if (frameId) {
      cancelAnimationFrame(frameId);
      frameId = 0;
    }
  }

  return {
    get value() { return current; },
    update,
    start,
    stop,
  };
}
