import { describe, expect, it } from 'vitest';

/** Mirrors formatFreq() in EiBiBrowser.svelte */
function formatFreq(khz: number): string {
  return khz >= 1000 ? `${(khz / 1000).toFixed(3)} MHz` : `${khz.toFixed(1)} kHz`;
}

/** Mirrors favouriteKey() in EiBiBrowser.svelte */
function favouriteKey(s: { freq_khz: number; station: string; time_str: string }): string {
  return `${s.freq_khz}:${s.station}:${s.time_str}`;
}

/** Mirrors the URL params builder in loadStations() */
function buildStationParams(opts: {
  onAirOnly: boolean; selectedBand: string; selectedLang: string;
  selectedCountry: string; searchQuery: string; sortBy: string;
  page: number; limit: number;
}): URLSearchParams {
  const p = new URLSearchParams();
  if (opts.onAirOnly) p.set('on_air', 'true');
  if (opts.selectedBand) p.set('band', opts.selectedBand);
  if (opts.selectedLang) p.set('lang', opts.selectedLang);
  if (opts.selectedCountry) p.set('country', opts.selectedCountry);
  if (opts.searchQuery) p.set('q', opts.searchQuery);
  p.set('sort', opts.sortBy);
  p.set('page', String(opts.page));
  p.set('limit', String(opts.limit));
  return p;
}

const defaults = {
  onAirOnly: false, selectedBand: '', selectedLang: '',
  selectedCountry: '', searchQuery: '', sortBy: 'freq', page: 1, limit: 100,
};

describe('EiBiBrowser formatFreq', () => {
  it('formats MHz for frequencies >= 1000 kHz', () => {
    expect(formatFreq(7200)).toBe('7.200 MHz');
    expect(formatFreq(15400)).toBe('15.400 MHz');
  });

  it('formats kHz for frequencies < 1000', () => {
    expect(formatFreq(500)).toBe('500.0 kHz');
    expect(formatFreq(153)).toBe('153.0 kHz');
  });

  it('boundary: 1000 kHz = 1.000 MHz', () => {
    expect(formatFreq(1000)).toBe('1.000 MHz');
  });

  it('handles fractional kHz', () => {
    expect(formatFreq(999.5)).toBe('999.5 kHz');
  });
});

describe('EiBiBrowser favouriteKey', () => {
  it('builds key from freq_khz, station, and time_str', () => {
    expect(favouriteKey({ freq_khz: 9505, station: 'BBC WS', time_str: '0600-0700' }))
      .toBe('9505:BBC WS:0600-0700');
  });

  it('produces unique keys for different stations/times', () => {
    const a = favouriteKey({ freq_khz: 9505, station: 'BBC WS', time_str: '0600-0700' });
    const b = favouriteKey({ freq_khz: 9505, station: 'VOA', time_str: '0600-0700' });
    const c = favouriteKey({ freq_khz: 9505, station: 'BBC WS', time_str: '1800-1900' });
    expect(a).not.toBe(b);
    expect(a).not.toBe(c);
  });
});

describe('EiBiBrowser favourites filtering', () => {
  const stations = [
    { freq_khz: 9505, station: 'BBC WS', time_str: '0600-0700' },
    { freq_khz: 6070, station: 'CFRX', time_str: '0000-2400' },
    { freq_khz: 15400, station: 'BBC WS', time_str: '1200-1300' },
  ];

  it('returns only favourited stations', () => {
    const favs = new Set(['9505:BBC WS:0600-0700']);
    const result = stations.filter((s) => favs.has(favouriteKey(s)));
    expect(result).toHaveLength(1);
    expect(result[0].station).toBe('BBC WS');
  });

  it('returns empty when no favourites match', () => {
    const favs = new Set(['9999:Unknown:0000-0000']);
    expect(stations.filter((s) => favs.has(favouriteKey(s)))).toEqual([]);
  });
});

describe('EiBiBrowser station query params', () => {
  it('includes sort, page, limit always', () => {
    const p = buildStationParams(defaults);
    expect(p.get('sort')).toBe('freq');
    expect(p.get('page')).toBe('1');
    expect(p.get('limit')).toBe('100');
  });

  it('omits optional filters when empty', () => {
    const p = buildStationParams(defaults);
    expect(p.has('on_air')).toBe(false);
    expect(p.has('band')).toBe(false);
    expect(p.has('q')).toBe(false);
  });

  it('includes all filters when set', () => {
    const p = buildStationParams({
      ...defaults, onAirOnly: true, selectedBand: '31m',
      selectedLang: 'English', selectedCountry: 'G', searchQuery: 'BBC',
    });
    expect(p.get('on_air')).toBe('true');
    expect(p.get('band')).toBe('31m');
    expect(p.get('lang')).toBe('English');
    expect(p.get('country')).toBe('G');
    expect(p.get('q')).toBe('BBC');
  });
});
