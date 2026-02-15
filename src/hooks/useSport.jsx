import { createContext, useContext, useState } from 'react';

const SportContext = createContext({ sport: 'nba', setSport: () => {} });

export function SportProvider({ children }) {
  const [sport, setSport] = useState('nba');
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
