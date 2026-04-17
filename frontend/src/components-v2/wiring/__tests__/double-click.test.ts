import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

import { withDoubleClick } from '../double-click';

describe('withDoubleClick', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('fires onSingle once the threshold passes without a second tap', () => {
    const onSingle = vi.fn();
    const onDouble = vi.fn();
    const handler = withDoubleClick(onSingle, onDouble, 280);

    handler();
    expect(onSingle).not.toHaveBeenCalled();
    expect(onDouble).not.toHaveBeenCalled();

    vi.advanceTimersByTime(280);
    expect(onSingle).toHaveBeenCalledTimes(1);
    expect(onDouble).not.toHaveBeenCalled();
  });

  it('fires onDouble (not onSingle) when a second tap arrives within threshold', () => {
    const onSingle = vi.fn();
    const onDouble = vi.fn();
    const handler = withDoubleClick(onSingle, onDouble, 280);

    handler();
    vi.advanceTimersByTime(100);
    handler();

    expect(onDouble).toHaveBeenCalledTimes(1);
    // Flush any pending timers — onSingle must not fire.
    vi.advanceTimersByTime(500);
    expect(onSingle).not.toHaveBeenCalled();
  });

  it('treats a third tap as the start of a new single-click cycle', () => {
    const onSingle = vi.fn();
    const onDouble = vi.fn();
    const handler = withDoubleClick(onSingle, onDouble, 280);

    handler();
    vi.advanceTimersByTime(50);
    handler();
    vi.advanceTimersByTime(50);
    handler();

    expect(onDouble).toHaveBeenCalledTimes(1);
    expect(onSingle).not.toHaveBeenCalled();

    vi.advanceTimersByTime(280);
    expect(onSingle).toHaveBeenCalledTimes(1);
    expect(onDouble).toHaveBeenCalledTimes(1);
  });

  it('does not fire onSingle if the second tap arrives exactly at the boundary', () => {
    const onSingle = vi.fn();
    const onDouble = vi.fn();
    const handler = withDoubleClick(onSingle, onDouble, 200);

    handler();
    vi.advanceTimersByTime(199);
    handler();

    expect(onDouble).toHaveBeenCalledTimes(1);
    expect(onSingle).not.toHaveBeenCalled();
  });

  it('defaults threshold to 280ms when not provided', () => {
    const onSingle = vi.fn();
    const onDouble = vi.fn();
    const handler = withDoubleClick(onSingle, onDouble);

    handler();
    vi.advanceTimersByTime(279);
    handler();
    expect(onDouble).toHaveBeenCalledTimes(1);
    expect(onSingle).not.toHaveBeenCalled();
  });
});
