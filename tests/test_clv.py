"""Unit tests for utils.clv.

Pins behavior of the CLV resolver, perspective converter, and points
formula. Cases cover the original spec plus the Marlins and Raptors
production rows that surfaced during the audit.
"""
from types import SimpleNamespace

from utils.clv import resolve_pick_side, to_picked_perspective, clv_points


def make_pick(side, home_team, away_team, line=None, closing_spread=None, pick_id='test'):
    return SimpleNamespace(
        id=pick_id,
        side=side,
        home_team=home_team,
        away_team=away_team,
        line=line,
        closing_spread=closing_spread,
    )


# ---- clv_points -------------------------------------------------------

def test_zero_crossing_dog_to_favorite():
    # pick=+1.5, close=-1.5 (picked-side); line crossed zero in our favor.
    assert clv_points(1.5, -1.5) == 3.0


def test_zero_crossing_favorite_to_dog():
    # pick=-1.5, close=+1.5; line crossed zero against us.
    assert clv_points(-1.5, 1.5) == -3.0


def test_same_side_improvement_favorite():
    # Raptors shape: pick=-3.5, close=-4.5 (picked-side, became more favored).
    assert clv_points(-3.5, -4.5) == 1.0


def test_same_side_worsening_favorite():
    # pick=-3.5, close=-2.5 (less favored at close).
    assert clv_points(-3.5, -2.5) == -1.0


def test_same_side_improvement_dog():
    # pick=+7, close=+8 (line moved away from picked side).
    assert clv_points(7, 8) == -1.0


def test_same_side_worsening_dog():
    # pick=+7, close=+6 (line moved toward picked side).
    assert clv_points(7, 6) == 1.0


def test_no_movement():
    assert clv_points(1.5, 1.5) == 0.0


def test_moneyline_pick_line_none():
    # Moneyline pick: pick.line is None. Returns None, never 0.
    assert clv_points(None, -1.5) is None


def test_missing_closing_spread():
    # closing_spread is None. Returns None.
    assert clv_points(1.5, None) is None


def test_both_none():
    assert clv_points(None, None) is None


# ---- resolve_pick_side ------------------------------------------------

def test_resolve_home_pick():
    pick = make_pick(
        side='Toronto Raptors -3.5',
        home_team='Toronto Raptors',
        away_team='Miami Heat',
    )
    assert resolve_pick_side(pick) == 'home'


def test_resolve_away_pick():
    pick = make_pick(
        side='Miami Marlins +1.5',
        home_team='Los Angeles Dodgers',
        away_team='Miami Marlins',
    )
    assert resolve_pick_side(pick) == 'away'


def test_resolve_returns_none_on_garbage():
    # Side does not start with either full team name.
    pick = make_pick(
        side='Whatever',
        home_team='Boston Celtics',
        away_team='New York Knicks',
    )
    assert resolve_pick_side(pick) is None


def test_resolve_returns_none_on_empty_side():
    pick = make_pick(side='', home_team='A', away_team='B')
    assert resolve_pick_side(pick) is None


def test_resolve_returns_none_on_missing_fields():
    pick = make_pick(side=None, home_team=None, away_team=None)
    assert resolve_pick_side(pick) is None


def test_resolve_handles_whitespace():
    pick = make_pick(
        side='  Boston Celtics -6.5  ',
        home_team='Philadelphia 76ers',
        away_team='Boston Celtics',
    )
    assert resolve_pick_side(pick) == 'away'


def test_resolve_case_insensitive():
    pick = make_pick(
        side='boston celtics -6.5',
        home_team='Boston Celtics',
        away_team='Toronto Raptors',
    )
    assert resolve_pick_side(pick) == 'home'


def test_resolve_team_name_prefix_overlap_picks_longer():
    # Synthetic edge case: away "Lakers" is a strict prefix of home
    # "Lakers City". The longer prefix should win (the actual picked
    # team's full name is what's in the side string).
    pick = make_pick(
        side='Lakers City -2',
        home_team='Lakers City',
        away_team='Lakers',
    )
    assert resolve_pick_side(pick) == 'home'


def test_resolve_team_name_prefix_overlap_picks_other_longer():
    pick = make_pick(
        side='Lakers -2',
        home_team='Lakers City',
        away_team='Lakers',
    )
    # 'Lakers' is a prefix of side, 'Lakers City' is not. Only away matches.
    assert resolve_pick_side(pick) == 'away'


# ---- to_picked_perspective --------------------------------------------

def test_perspective_home_pick_identity():
    # Home pick: picked-side line == home line. spread is home perspective.
    assert to_picked_perspective(-3.5, 'home') == -3.5


def test_perspective_away_pick_flips_sign():
    # Away pick: picked-side line == -home line.
    assert to_picked_perspective(-1.5, 'away') == 1.5
    assert to_picked_perspective(4.5, 'away') == -4.5


def test_perspective_returns_none_on_unresolved_side():
    assert to_picked_perspective(-1.5, None) is None


def test_perspective_returns_none_on_none_spread():
    assert to_picked_perspective(None, 'home') is None
    assert to_picked_perspective(None, 'away') is None


# ---- end-to-end with production rows ----------------------------------

def test_e2e_marlins_correct_close():
    # Hypothetical Marlins +1.5 with actual close at Marlins -1.5
    # (line crossed zero). closing_spread in DB would be +1.5 (home
    # perspective: Dodgers +1.5 home dog at close).
    pick = make_pick(
        side='Miami Marlins +1.5',
        home_team='Los Angeles Dodgers',
        away_team='Miami Marlins',
        line=1.5,
    )
    side = resolve_pick_side(pick)
    assert side == 'away'
    closing_picked = to_picked_perspective(1.5, side)
    assert closing_picked == -1.5
    assert clv_points(pick.line, closing_picked) == 3.0


def test_e2e_marlins_no_movement():
    # Actual production state: closing_spread stored as -1.5 (home),
    # picked-side close = +1.5, no movement from entry. CLV = 0.
    pick = make_pick(
        side='Miami Marlins +1.5',
        home_team='Los Angeles Dodgers',
        away_team='Miami Marlins',
        line=1.5,
    )
    side = resolve_pick_side(pick)
    closing_picked = to_picked_perspective(-1.5, side)
    assert closing_picked == 1.5
    assert clv_points(pick.line, closing_picked) == 0.0


def test_e2e_raptors():
    # Raptors home -3.5, close home -4.5. Both home-perspective values
    # equal picked-side values for home pick. CLV = +1.0.
    pick = make_pick(
        side='Toronto Raptors -3.5',
        home_team='Toronto Raptors',
        away_team='Miami Heat',
        line=-3.5,
    )
    side = resolve_pick_side(pick)
    assert side == 'home'
    closing_picked = to_picked_perspective(-4.5, side)
    assert closing_picked == -4.5
    assert clv_points(pick.line, closing_picked) == 1.0
