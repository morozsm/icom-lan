export type BandSegmentMode = 'cw' | 'digital' | 'phone' | 'beacon';

export interface BandSegment {
  /** Start frequency in Hz */
  startHz: number;
  /** End frequency in Hz */
  endHz: number;
  /** Segment type */
  mode: BandSegmentMode;
  /** Human-readable label */
  label: string;
}

export interface BandPlan {
  /** Band name (e.g., "160m", "20m") */
  band: string;
  /** Band start in Hz */
  startHz: number;
  /** Band end in Hz */
  endHz: number;
  /** Segments within this band */
  segments: BandSegment[];
}

/** Segment colors for rendering */
export const SEGMENT_COLORS: Record<BandSegmentMode, string> = {
  cw:      'rgba(255, 106, 0, 0.20)',     // orange
  digital: 'rgba(74, 222, 128, 0.20)',     // green
  phone:   'rgba(96, 165, 250, 0.20)',     // blue
  beacon:  'rgba(250, 204, 21, 0.20)',     // yellow
};

/** Border colors (slightly more opaque for segment boundaries) */
export const SEGMENT_BORDER_COLORS: Record<BandSegmentMode, string> = {
  cw:      'rgba(255, 106, 0, 0.5)',
  digital: 'rgba(74, 222, 128, 0.5)',
  phone:   'rgba(96, 165, 250, 0.5)',
  beacon:  'rgba(250, 204, 21, 0.5)',
};

/** Label colors */
export const SEGMENT_LABEL_COLORS: Record<BandSegmentMode, string> = {
  cw:      'rgb(255, 150, 50)',
  digital: 'rgb(74, 222, 128)',
  phone:   'rgb(96, 165, 250)',
  beacon:  'rgb(250, 204, 21)',
};

export const ARRL_HF_BANDS: BandPlan[] = [
  {
    band: '160m',
    startHz: 1_800_000,
    endHz: 2_000_000,
    segments: [
      { startHz: 1_800_000, endHz: 1_840_000, mode: 'cw',      label: 'CW' },
      { startHz: 1_840_000, endHz: 1_850_000, mode: 'digital',  label: 'DIGI' },
      { startHz: 1_850_000, endHz: 2_000_000, mode: 'phone',    label: 'PHONE' },
    ],
  },
  {
    band: '80m',
    startHz: 3_500_000,
    endHz: 4_000_000,
    segments: [
      { startHz: 3_500_000, endHz: 3_570_000, mode: 'cw',      label: 'CW' },
      { startHz: 3_570_000, endHz: 3_600_000, mode: 'digital',  label: 'DIGI' },
      { startHz: 3_600_000, endHz: 4_000_000, mode: 'phone',    label: 'PHONE' },
    ],
  },
  {
    band: '60m',
    startHz: 5_330_500,
    endHz: 5_406_400,
    segments: [
      { startHz: 5_330_500, endHz: 5_406_400, mode: 'phone',   label: 'PHONE' },
    ],
  },
  {
    band: '40m',
    startHz: 7_000_000,
    endHz: 7_300_000,
    segments: [
      { startHz: 7_000_000, endHz: 7_070_000, mode: 'cw',      label: 'CW' },
      { startHz: 7_070_000, endHz: 7_125_000, mode: 'digital',  label: 'DIGI' },
      { startHz: 7_125_000, endHz: 7_300_000, mode: 'phone',    label: 'PHONE' },
    ],
  },
  {
    band: '30m',
    startHz: 10_100_000,
    endHz: 10_150_000,
    segments: [
      { startHz: 10_100_000, endHz: 10_130_000, mode: 'cw',     label: 'CW' },
      { startHz: 10_130_000, endHz: 10_150_000, mode: 'digital', label: 'DIGI' },
    ],
  },
  {
    band: '20m',
    startHz: 14_000_000,
    endHz: 14_350_000,
    segments: [
      { startHz: 14_000_000, endHz: 14_070_000, mode: 'cw',     label: 'CW' },
      { startHz: 14_070_000, endHz: 14_150_000, mode: 'digital', label: 'DIGI' },
      { startHz: 14_150_000, endHz: 14_350_000, mode: 'phone',   label: 'PHONE' },
    ],
  },
  {
    band: '17m',
    startHz: 18_068_000,
    endHz: 18_168_000,
    segments: [
      { startHz: 18_068_000, endHz: 18_100_000, mode: 'cw',     label: 'CW' },
      { startHz: 18_100_000, endHz: 18_110_000, mode: 'digital', label: 'DIGI' },
      { startHz: 18_110_000, endHz: 18_168_000, mode: 'phone',   label: 'PHONE' },
    ],
  },
  {
    band: '15m',
    startHz: 21_000_000,
    endHz: 21_450_000,
    segments: [
      { startHz: 21_000_000, endHz: 21_070_000, mode: 'cw',     label: 'CW' },
      { startHz: 21_070_000, endHz: 21_150_000, mode: 'digital', label: 'DIGI' },
      { startHz: 21_150_000, endHz: 21_200_000, mode: 'beacon',  label: 'BCN' },
      { startHz: 21_200_000, endHz: 21_450_000, mode: 'phone',   label: 'PHONE' },
    ],
  },
  {
    band: '12m',
    startHz: 24_890_000,
    endHz: 24_990_000,
    segments: [
      { startHz: 24_890_000, endHz: 24_920_000, mode: 'cw',     label: 'CW' },
      { startHz: 24_920_000, endHz: 24_930_000, mode: 'digital', label: 'DIGI' },
      { startHz: 24_930_000, endHz: 24_990_000, mode: 'phone',   label: 'PHONE' },
    ],
  },
  {
    band: '10m',
    startHz: 28_000_000,
    endHz: 29_700_000,
    segments: [
      { startHz: 28_000_000, endHz: 28_070_000, mode: 'cw',     label: 'CW' },
      { startHz: 28_070_000, endHz: 28_150_000, mode: 'beacon',  label: 'BCN' },
      { startHz: 28_150_000, endHz: 28_300_000, mode: 'digital', label: 'DIGI' },
      { startHz: 28_300_000, endHz: 29_700_000, mode: 'phone',   label: 'PHONE' },
    ],
  },
];

/** Find all segments visible in the given frequency range */
export function getVisibleSegments(
  startHz: number,
  endHz: number,
): { segment: BandSegment; band: string }[] {
  const result: { segment: BandSegment; band: string }[] = [];
  for (const band of ARRL_HF_BANDS) {
    // Quick range check: skip entire band if no overlap
    if (band.endHz < startHz || band.startHz > endHz) continue;
    for (const seg of band.segments) {
      if (seg.endHz > startHz && seg.startHz < endHz) {
        result.push({ segment: seg, band: band.band });
      }
    }
  }
  return result;
}
