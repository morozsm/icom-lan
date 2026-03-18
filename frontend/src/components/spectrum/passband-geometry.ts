import { clampFilterWidth } from '../../components-v2/panels/filter-controls';

export interface PassbandGeometry {
  leftPx: number;
  rightPx: number;
  widthPx: number;
}

function clamp(value: number, min: number, max: number): number {
  return value < min ? min : value > max ? max : value;
}

export function getPassbandEdgesHz(mode: string, passbandHz: number, shiftHz: number): {
  leftHz: number;
  rightHz: number;
} {
  const normalizedMode = mode.toUpperCase();

  if (normalizedMode === 'LSB') {
    return {
      leftHz: shiftHz - passbandHz,
      rightHz: shiftHz,
    };
  }

  if (
    normalizedMode === 'CW' ||
    normalizedMode === 'CW-R' ||
    normalizedMode === 'RTTY' ||
    normalizedMode === 'RTTY-R' ||
    normalizedMode === 'AM'
  ) {
    return {
      leftHz: shiftHz - passbandHz / 2,
      rightHz: shiftHz + passbandHz / 2,
    };
  }

  return {
    leftHz: shiftHz,
    rightHz: shiftHz + passbandHz,
  };
}

export function getPassbandGeometry(
  mode: string,
  passbandHz: number,
  shiftHz: number,
  spanHz: number,
  widthPx: number,
): PassbandGeometry | null {
  if (passbandHz <= 0 || spanHz <= 0 || widthPx <= 0) {
    return null;
  }

  const { leftHz, rightHz } = getPassbandEdgesHz(mode, passbandHz, shiftHz);
  const centerPx = widthPx / 2;
  const hzToPx = widthPx / spanHz;

  const unclampedLeftPx = centerPx + leftHz * hzToPx;
  const unclampedRightPx = centerPx + rightHz * hzToPx;
  const sortedLeftPx = Math.min(unclampedLeftPx, unclampedRightPx);
  const sortedRightPx = Math.max(unclampedLeftPx, unclampedRightPx);
  const leftPx = clamp(sortedLeftPx, 0, widthPx);
  const rightPx = clamp(sortedRightPx, 0, widthPx);

  return {
    leftPx,
    rightPx,
    widthPx: Math.max(0, rightPx - leftPx),
  };
}

export function canResizeFromRightEdge(mode: string): boolean {
  return mode.toUpperCase() !== 'LSB';
}

export function getFilterWidthFromRightEdgePx(
  mode: string,
  shiftHz: number,
  spanHz: number,
  widthPx: number,
  rightEdgePx: number,
): number | null {
  if (spanHz <= 0 || widthPx <= 0 || !canResizeFromRightEdge(mode)) {
    return null;
  }

  const hzPerPx = spanHz / widthPx;
  const rightEdgeHz = (rightEdgePx - widthPx / 2) * hzPerPx;
  const normalizedMode = mode.toUpperCase();

  let widthHz: number;
  if (
    normalizedMode === 'CW' ||
    normalizedMode === 'CW-R' ||
    normalizedMode === 'RTTY' ||
    normalizedMode === 'RTTY-R' ||
    normalizedMode === 'AM'
  ) {
    widthHz = (rightEdgeHz - shiftHz) * 2;
  } else {
    widthHz = rightEdgeHz - shiftHz;
  }

  return clampFilterWidth(widthHz);
}