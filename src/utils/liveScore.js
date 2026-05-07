// Shared helpers for ESPN scoreboard `state` classification and cover-tracker
// math. Used by PicksTab, DailyTopSignalCard, and MarketView so all three
// surfaces agree on when a game is "in play" vs final vs pre-game and how a
// pick's cover is computed against the live score.
//
// The previous bug: each surface inlined a strict whitelist
//   state in (STATUS_IN_PROGRESS, STATUS_HALFTIME, STATUS_FINAL)
// which dropped MLB-specific transient states (rain delay, end-of-inning,
// suspended) and made the live cover tracker disappear mid-game.

const PRE_GAME_STATES = new Set([
  '',
  'STATUS_SCHEDULED',
  'STATUS_TBD',
  'STATUS_TBA',
  'STATUS_POSTPONED',
  'STATUS_CANCELED',
  'STATUS_CANCELLED',
  'STATUS_FORFEIT',
]);

const FINAL_STATES = new Set([
  'STATUS_FINAL',
  'STATUS_FULL_TIME',
  'STATUS_FULL',
]);

export function isPreGameState(state) {
  return !state || PRE_GAME_STATES.has(state);
}

export function isFinalState(state) {
  return FINAL_STATES.has(state);
}

// Anything that isn't pre-game and isn't final — covers in-progress, halftime,
// end-of-period/inning, and weather/rain delays so the live block keeps
// rendering through brief pauses rather than blinking off.
export function isInPlayState(state) {
  return !isPreGameState(state) && !isFinalState(state);
}

// True when the score row should be visible at all (live or final). False
// only when the game is still pre-game, postponed, or canceled.
export function shouldShowLiveBlock(state) {
  return !isPreGameState(state);
}

// Detect whether a pick is on the home side. Two input shapes are supported:
//   1) MarketView path: `pickSide` is the explicit "home"/"away" string from
//      the model output.
//   2) DailyTopSignalCard path: `side` is a display string ("Lakers -3.5")
//      and `homeTeam` is the full home-team name. Match on the last token.
export function isHomeSidePick({ pickSide, side, homeTeam } = {}) {
  if (typeof pickSide === 'string') {
    if (/home/i.test(pickSide)) return true;
    if (/away/i.test(pickSide)) return false;
  }
  if (homeTeam && side) {
    const homeKey = String(homeTeam).split(' ').pop().toLowerCase();
    if (homeKey && String(side).toLowerCase().includes(homeKey)) return true;
  }
  return false;
}

// Compute live cover state for a pick at signal-time line vs the live score.
// `line` is the picked-side spread (negative when picked side is favored,
// positive when dog), so the same formula works for home and away picks.
// Returns null when inputs are insufficient.
export function computeLiveCover({ isHomePick, line, homeScore = 0, awayScore = 0 }) {
  const lineNum = parseFloat(line);
  if (!Number.isFinite(lineNum) || isHomePick == null) return null;
  const margin = isHomePick ? (homeScore - awayScore) : (awayScore - homeScore);
  const adjusted = margin + lineNum;
  return {
    status: adjusted > 0 ? 'covering' : 'not_covering',
    margin: Math.round(Math.abs(adjusted) * 10) / 10,
    adjusted,
  };
}
