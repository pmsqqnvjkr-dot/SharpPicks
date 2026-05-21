"""Closing Line Value (CLV) calculation.

Two parallel CLV measurements per pick:

1. Spread CLV (clv_points, stored on Pick.clv)
   - Points-space delta in PICKED-SIDE perspective.
   - Works well for NBA / WNBA where spreads drift continuously.
   - Reads ~0 across MLB picks because MLB run lines are structurally
     fixed at ±1.5 — they almost never drift.

2. Moneyline CLV (clv_ml_prob, stored on Pick.clv_ml; added 2026-05-21)
   - Implied-probability-points delta computed from American odds.
   - Continuous across all sports; the canonical sharp-money signal
     for MLB and a useful complement for NBA / WNBA.
   - Picked-side closing odds stored on Pick.closing_ml.

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
- pick.market_odds and pick.closing_ml are American odds (negative
  favorite, positive dog) for the picked side specifically.
- clv_ml_prob takes the picked-side closing odds; picked_ml() resolves
  which of home_ml_close / away_ml_close to feed in.
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
convention. clv_ml_prob is especially valuable on the frontend for
MLB where spread CLV is structurally uninformative.
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


# ─────────────────────────────────────────────────────────────────────
# Moneyline CLV (clv_ml)
# ─────────────────────────────────────────────────────────────────────
#
# Spread CLV (clv_points above) returns 0 for nearly every MLB pick
# because MLB run-lines are structurally fixed at +/-1.5 — they almost
# never drift the way NBA spreads do. The real MLB sharp-money signal
# lives in moneyline movement, which is continuous.
#
# We compute moneyline CLV in two forms:
#   1. clv_ml_cents: American-odds delta (closing_odds_picked - pick_odds).
#      Positive means we got a better price than the close. Reported
#      directly as "cents beat the close" (e.g. +15 = got 15 cents
#      better than the closing line).
#   2. clv_ml_prob: implied-probability delta (in percentage points).
#      Probability-space is easier to average across odds ranges
#      because cent-deltas don't scale linearly between -110 and -300.
#      Positive means closing implied probability was higher than our
#      entry implied probability — i.e. the market moved toward us.
#
# The Pick model carries `clv_ml` as the probability-space delta
# (clv_ml_prob) because it averages cleanly and matches the convention
# in the spread-CLV column. clv_ml_cents is available for display.
#
# We use the simple "no-vig dropped" implied probability rather than
# the consensus-vig-removed probability for now; the bias washes out
# in deltas. If we add a sharp/efficient-line normalization later, this
# is the function to swap.

def implied_prob(american_odds):
    """American odds -> implied probability (0..1).

    Returns None if input is None or zero (zero is not a valid line).
    """
    if american_odds is None:
        return None
    try:
        o = float(american_odds)
    except (TypeError, ValueError):
        return None
    if o == 0:
        return None
    if o < 0:
        return (-o) / ((-o) + 100.0)
    return 100.0 / (o + 100.0)


def picked_ml(pick, home_ml_close, away_ml_close):
    """Return the closing moneyline for the side the pick is on.

    Returns None if pick side cannot be resolved or the relevant
    closing odds column is null.
    """
    side = resolve_pick_side(pick)
    if side == 'home':
        return home_ml_close
    if side == 'away':
        return away_ml_close
    return None


def clv_ml_cents(pick_odds, closing_odds_picked):
    """Moneyline CLV in American-odds cents.

    Positive means our entry odds were better (higher payout) than the
    close. Note: American odds aren't linear, so cents differ in value
    at different ranges. Use clv_ml_prob for averaging.

    Returns None on missing inputs.
    """
    if pick_odds is None or closing_odds_picked is None:
        return None
    try:
        return float(pick_odds) - float(closing_odds_picked)
    except (TypeError, ValueError):
        return None


def clv_ml_prob(pick_odds, closing_odds_picked):
    """Moneyline CLV in implied-probability percentage points.

    closing_implied - entry_implied. Positive = market shifted toward
    the picked side after entry (closing line agrees with us more than
    our entry line did). Multiplied by 100 so the value reads as
    percentage points (e.g. +2.4 = "the close priced our side 2.4
    points higher than our entry did").

    Use this for averaging across picks — it scales linearly and
    behaves well in the typical -300 .. +300 American-odds range.

    Returns None on missing inputs.
    """
    p_entry = implied_prob(pick_odds)
    p_close = implied_prob(closing_odds_picked)
    if p_entry is None or p_close is None:
        return None
    return round((p_close - p_entry) * 100.0, 3)


def compute_cover_margin(home_score, away_score, line, side, home_team, away_team):
    """Cover margin in points, from the bet side's perspective.

    Convention
    ----------
    - Positive: bet side covered the spread by N points.
    - Negative: bet side failed to cover by N points.
    - Zero: push (exact).
    - None: not gradable (missing scores or line, or `side` does not
      resolve to home / away).

    Formula: team_margin + line, where team_margin is the bet side's
    score margin (their score minus opponent's). `line` is in
    PICKED-SIDE perspective per the clv.py convention (negative when
    picked side is favored, positive when picked side is dog).

    Examples (Pistons -3.5 home, final DET 111 - CLE 101):
        home pick:  team_margin = 111 - 101 = +10, line = -3.5
                    cover = +10 + (-3.5) = +6.5  (covered)
        away pick:  team_margin = 101 - 111 = -10, line = +3.5
                    cover = -10 + 3.5 = -6.5  (failed to cover)
    """
    if home_score is None or away_score is None or line is None:
        return None

    from types import SimpleNamespace
    pick_like = SimpleNamespace(side=side, home_team=home_team, away_team=away_team)
    side_label = resolve_pick_side(pick_like)
    if side_label is None:
        return None

    if side_label == 'home':
        team_margin = float(home_score) - float(away_score)
    else:
        team_margin = float(away_score) - float(home_score)

    return round(team_margin + float(line), 1)
