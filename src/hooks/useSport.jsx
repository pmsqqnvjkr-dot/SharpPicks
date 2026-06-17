import { createContext, useContext, useState } from 'react';

const SportContext = createContext({ sport: 'mlb', setSport: () => {} });

const VALID_SPORTS = new Set(['nba', 'mlb', 'wnba', 'nfl']);

// Seed the initial sport from ?sport= on first mount so deep-links from
// the HQ market-read tweets (e.g. app.sharppicks.ai/?sport=wnba) drop
// the user straight onto the right tab. Falls back to mlb when the
// param is missing or invalid. Subsequent setSport calls update state
// only; the URL is not rewritten so navigating away from the seeded
// tab does not desync history.
function readSportFromUrl() {
  if (typeof window === 'undefined') return null;
  try {
    const params = new URLSearchParams(window.location.search);
    const raw = (params.get('sport') || '').toLowerCase().trim();
    return VALID_SPORTS.has(raw) ? raw : null;
  } catch { return null; }
}

export function SportProvider({ children }) {
  const [sport, setSport] = useState(() => readSportFromUrl() || 'mlb');
  return (
    <SportContext.Provider value={{ sport, setSport }}>
      {children}
    </SportContext.Provider>
  );
}

export function useSport() {
  return useContext(SportContext);
}

export function sportQuery(endpoint, sport) {
  if (!sport || sport === 'all') return endpoint;
  const sep = endpoint.includes('?') ? '&' : '?';
  return `${endpoint}${sep}sport=${sport}`;
}
