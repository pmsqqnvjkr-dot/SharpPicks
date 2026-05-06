// Fallback status inference from the scheduled start time.
// The DB cron and the live-scores ESPN endpoint normally promote a game out of
// 'scheduled' when it kicks off / finishes, but both can lag (or, for past
// slates, the live-scores fetch is skipped entirely). Without this fallback,
// games whose start time has long passed keep showing under "UPCOMING".
//
// Returns:
//   'live'      if the start time has passed within the last MAX_GAME_DURATION
//   'final'     if the start time is older than MAX_GAME_DURATION
//   null        if the start time is missing, unparseable, or still in the future

const MAX_GAME_DURATION_MS = 5 * 60 * 60 * 1000; // 5h covers OT / extra innings

export default function inferGameStatus(game) {
  const raw = game && game.game_time_sort;
  if (!raw) return null;
  const startMs = Date.parse(raw);
  if (Number.isNaN(startMs)) return null;
  const elapsedMs = Date.now() - startMs;
  if (elapsedMs < 0) return null;
  return elapsedMs > MAX_GAME_DURATION_MS ? 'final' : 'live';
}
