export interface BroadcastPreset {
  name: string;        // "120m", "49m", etc.
  freq: number;        // Default frequency in Hz
  mode: string;        // "AM" for all broadcast
  start: number;       // Band start in Hz
  end: number;         // Band end in Hz
}

/** LW and MW broadcast bands */
export const BROADCAST_LW_MW_BANDS: BroadcastPreset[] = [
  { name: 'LW',   freq: 198000,   mode: 'AM', start: 148500,   end: 283500   },
  { name: 'MW',   freq: 1000000,  mode: 'AM', start: 526500,   end: 1606500  },
  { name: '120m', freq: 2400000,  mode: 'AM', start: 2300000,  end: 2495000  },
  { name: '90m',  freq: 3300000,  mode: 'AM', start: 3200000,  end: 3400000  },
  { name: '75m',  freq: 3950000,  mode: 'AM', start: 3900000,  end: 4000000  },
  { name: '60m',  freq: 4900000,  mode: 'AM', start: 4750000,  end: 5060000  },
];

/** SW broadcast bands (49m and up) */
export const BROADCAST_SW_BANDS: BroadcastPreset[] = [
  { name: '49m',  freq: 6000000,  mode: 'AM', start: 5900000,  end: 6200000  },
  { name: '41m',  freq: 7300000,  mode: 'AM', start: 7200000,  end: 7450000  },
  { name: '31m',  freq: 9500000,  mode: 'AM', start: 9400000,  end: 9900000  },
  { name: '25m',  freq: 11800000, mode: 'AM', start: 11600000, end: 12100000 },
  { name: '22m',  freq: 13700000, mode: 'AM', start: 13570000, end: 13870000 },
  { name: '19m',  freq: 15400000, mode: 'AM', start: 15100000, end: 15800000 },
  { name: '16m',  freq: 17700000, mode: 'AM', start: 17480000, end: 17900000 },
  { name: '15m',  freq: 18950000, mode: 'AM', start: 18900000, end: 19020000 },
  { name: '13m',  freq: 21500000, mode: 'AM', start: 21450000, end: 21850000 },
  { name: '11m',  freq: 25800000, mode: 'AM', start: 25600000, end: 26100000 },
];

const ALL_BROADCAST = [...BROADCAST_LW_MW_BANDS, ...BROADCAST_SW_BANDS];

export function findActiveBroadcastBand(freq: number): string | null {
  for (const band of ALL_BROADCAST) {
    if (freq >= band.start && freq <= band.end) {
      return band.name;
    }
  }
  return null;
}
