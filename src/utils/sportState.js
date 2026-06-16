// Resolves the special empty-state for a sport that should short-circuit
// the normal pass-day / off-day / pre-game / pick pageState logic.
//
// Returns one of:
//   'calibration'  the sport is in a pre-launch calibration phase
//                  (NFL while config.sports.nfl.launched is false; also
//                  fires for any future sport with launched: false set)
//   'offseason'    the sport is outside its season window
//                  (config.sports.<sport>.in_season is false)
//   null           the sport is in season and live; fall through to the
//                  normal PicksTab pageState selector (pass / off / pick)
//
// Selection priority follows the handoff:
//   CALIBRATION beats OFF-SEASON. NFL stays in calibration year-round
//   while the launch flag is off, regardless of whether the NFL season
//   has started.
//
// Inputs:
//   sport    'nba' | 'mlb' | 'wnba' | 'nfl' (case insensitive)
//   config   The /api/public/launch-config response shape:
//              { sports: { nba: {in_season}, nfl: {launched}, ... } }
//   today    Reserved for future season-window window math when a sport
//            has explicit season_start / season_end dates but no
//            in_season flag. Currently unused; in_season is the gate.
//
// If config is missing or malformed, returns null so the existing
// pageState selector handles every sport (graceful degradation).

export function resolveSportEmptyState(sport, config /*, today */) {
  if (!sport || !config || !config.sports) return null;
  const s = String(sport).toLowerCase();
  const entry = config.sports[s];
  if (!entry) return null;

  // Pre-launch calibration: explicit launched flag on a sport entry.
  // Currently only NFL carries this, but the check is generic so the
  // same flag works for any future pre-launch sport.
  if (entry.launched === false) return 'calibration';

  // Off-season: in_season === false. Distinct from a regular off-day.
  if (entry.in_season === false) return 'offseason';

  return null;
}
