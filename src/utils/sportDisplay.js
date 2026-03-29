/**
 * Centralized sport-specific display logic.
 * All NBA vs MLB formatting differences live here so component code
 * never has to branch on sport strings directly.
 */

const SPORT_CONFIG = {
  nba: {
    periodLabel: (period) => {
      if (!period) return '';
      return period <= 4 ? `Q${period}` : `OT${period - 4}`;
    },
    showClock: true,
    preGameVerb: 'Tips',
    tipLabel: 'Tip',
    tipoffLabel: 'Tipoff',
    halftimeLabel: 'HALF',
    spreadLabel: 'Spread',
    tomorrowLabel: 'Tips tomorrow',
  },
  mlb: {
    periodLabel: (period) => {
      if (!period) return '';
      return `Inn ${period}`;
    },
    showClock: false,
    preGameVerb: 'First pitch',
    tipLabel: 'First pitch',
    tipoffLabel: 'First Pitch',
    halftimeLabel: 'BREAK',
    spreadLabel: 'RL',
    tomorrowLabel: 'Tomorrow',
  },
};

const DEFAULT_SPORT = 'nba';

export default function sportDisplay(sport) {
  const key = (sport || DEFAULT_SPORT).toLowerCase();
  return SPORT_CONFIG[key] || SPORT_CONFIG[DEFAULT_SPORT];
}
