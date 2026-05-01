"""Closing Line Value (CLV) calculation.

Single source of truth for CLV math. Replaces the brittle substring
is_home_pick detector previously inlined at three sites in app.py.

Convention
----------
- pick.line is stored in PICKED-SIDE perspective (set by
  model_service._build_games_detail and the Pick creation path in
  model_service.py: pick_spread = spread if is_home_pick else -spread).
  Negative when picked side is favored, positive when picked side is dog.
- pick.closing_spread is currently stored in HOME perspective (assigned
  directly from game['spread_home'] by the closing-lines crons).
- clv_points expects both inputs in PICKED-SIDE perspective. Callers
  convert closing_spread via to_picked_perspective() before passing in.
- Positive CLV = market moved toward the picked side after entry
  (you got the better number).
- Negative CLV = market moved away from the picked side.

TODO (out of scope for this PR): normalize closing_spread storage to
picked-side perspective at write time, then the frontend fallback
formula `pick.line - pick.closing_spread` becomes correct without a
backend lookup. Until then, frontend fallback is buggy when pick.clv
is null on away picks (mixed perspective). See ResolutionScreen.jsx,
PicksTab.jsx, PickCard.jsx.

TODO (out of scope): port these helpers to src/utils/clv.js so the
frontend has a real fallback path that also mirrors picked-side
convention.
"""
import logging

logger = logging.getLogger(__name__)


def resolve_pick_side(pick):
    """Return 'home', 'away', or None for which team the pick is on.

    Uses prefix-match against pick.home_team and pick.away_team rather
    than substring containment, which is robust to spread suffixes
    ("Toronto Raptors -3.5") but won't misclassify when one team name
    happens to appear inside another team's longer name.

    Returns None and logs a warning if neither team's full name is a
    prefix of pick.side (malformed side string, mid-season rename,
    abbreviated form, etc.). Caller should skip the row.
    """
    side = (getattr(pick, 'side', '') or '').strip().lower()
    home = (getattr(pick, 'home_team', '') or '').strip().lower()
    away = (getattr(pick, 'away_team', '') or '').strip().lower()

    if not side:
        logger.warning("resolve_pick_side: empty side on pick id=%s", getattr(pick, 'id', '?'))
        return None

    home_match = bool(home) and side.startswith(home)
    away_match = bool(away) and side.startswith(away)

    if home_match and not away_match:
        return 'home'
    if away_match and not home_match:
        return 'away'
    if home_match and away_match:
        # One team's name is a prefix of the other (extremely rare).
        # Longer prefix wins because the side string would extend further.
        return 'home' if len(home) > len(away) else 'away'

    logger.warning(
        "resolve_pick_side: no match for pick id=%s side=%r home=%r away=%r",
        getattr(pick, 'id', '?'), side, home, away,
    )
    return None


def to_picked_perspective(spread, pick_side):
    """Convert a HOME-perspective spread to PICKED-SIDE perspective.

    For a home pick, picked-side line == home line, so identity.
    For an away pick, picked-side line == -home line.

    Returns None if pick_side is None (caller couldn't resolve the side)
    or if spread is None.
    """
    if spread is None or pick_side is None:
        return None
    if pick_side == 'home':
        return spread
    if pick_side == 'away':
        return -spread
    logger.warning("to_picked_perspective: unknown pick_side=%r", pick_side)
    return None


def clv_points(pick_line, closing_picked):
    """Compute CLV in points. Both inputs are PICKED-SIDE perspective.

    Returns pick_line - closing_picked. Positive means market moved
    toward the picked side after entry (beat the close).

    Returns None if either input is None. Never coerces to 0 — moneyline
    picks (no spread) and rows with missing closing data are explicitly
    "no CLV available", not "zero CLV".
    """
    if pick_line is None or closing_picked is None:
        return None
    return float(pick_line) - float(closing_picked)
