"""Unit tests for utils.clv.compute_cover_margin.

Pins the sign convention for cover margin display. The previous
formula (away - home + line, hard-coded to away perspective) produced
wrong-sign output on home picks. Real-world bug: Pistons -3.5 winning
DET 111 - CLE 101 was rendered as Cover margin: -13.5 instead of +6.5.

Convention
----------
- Positive: bet side covered by N points
- Negative: bet side failed to cover by N points
- Zero: push (exact)
- None: not gradable (missing scores or line, or unresolvable side)
"""
from utils.clv import compute_cover_margin


# ---- Acceptance criteria from the bug report ----------------------------

def test_favorite_home_covers():
    """Pistons -3.5 (home favorite). Final DET 111 - CLE 101.
    Pistons won by 10, covered the -3.5 spread by +6.5 points."""
    margin = compute_cover_margin(
        home_score=111, away_score=101,
        line=-3.5,
        side='Detroit Pistons -3.5',
        home_team='Detroit Pistons', away_team='Cleveland Cavaliers',
    )
    assert margin == 6.5


def test_favorite_home_fails_to_cover():
    """Pistons -10 (home favorite). Final DET 111 - CLE 110.
    Pistons won by 1, failed the -10 spread by 9 points."""
    margin = compute_cover_margin(
        home_score=111, away_score=110,
        line=-10.0,
        side='Detroit Pistons -10',
        home_team='Detroit Pistons', away_team='Cleveland Cavaliers',
    )
    assert margin == -9.0


def test_underdog_away_covers():
    """Cavaliers +12 (away dog). Final DET 111 - CLE 101.
    Cavs lost by 10, covered the +12 spread by 2 points."""
    margin = compute_cover_margin(
        home_score=111, away_score=101,
        line=12.0,
        side='Cleveland Cavaliers +12',
        home_team='Detroit Pistons', away_team='Cleveland Cavaliers',
    )
    assert margin == 2.0


def test_underdog_away_fails_to_cover():
    """Cavaliers +3.5 (away dog). Final DET 111 - CLE 101.
    Cavs lost by 10, failed the +3.5 spread by 6.5 points."""
    margin = compute_cover_margin(
        home_score=111, away_score=101,
        line=3.5,
        side='Cleveland Cavaliers +3.5',
        home_team='Detroit Pistons', away_team='Cleveland Cavaliers',
    )
    assert margin == -6.5


def test_push_exact():
    """Cavaliers +10 (away dog). Final DET 111 - CLE 101.
    Cavs lost by exactly 10, pushed at +10."""
    margin = compute_cover_margin(
        home_score=111, away_score=101,
        line=10.0,
        side='Cleveland Cavaliers +10',
        home_team='Detroit Pistons', away_team='Cleveland Cavaliers',
    )
    assert margin == 0.0


# ---- Additional coverage ------------------------------------------------

def test_favorite_away_covers():
    """Lakers -7 (away favorite). Final LAL 120 - HOU 110.
    Lakers won by 10, covered -7 by +3 points."""
    margin = compute_cover_margin(
        home_score=110, away_score=120,
        line=-7.0,
        side='Los Angeles Lakers -7',
        home_team='Houston Rockets', away_team='Los Angeles Lakers',
    )
    assert margin == 3.0


def test_underdog_home_covers():
    """Rockets +14 (home dog). Final LAL 120 - HOU 110.
    Rockets lost by 10, covered +14 by +4 points."""
    margin = compute_cover_margin(
        home_score=110, away_score=120,
        line=14.0,
        side='Houston Rockets +14',
        home_team='Houston Rockets', away_team='Los Angeles Lakers',
    )
    assert margin == 4.0


def test_returns_none_when_scores_missing():
    assert compute_cover_margin(None, 101, -3.5, 'Detroit Pistons -3.5',
                                'Detroit Pistons', 'Cleveland Cavaliers') is None
    assert compute_cover_margin(111, None, -3.5, 'Detroit Pistons -3.5',
                                'Detroit Pistons', 'Cleveland Cavaliers') is None


def test_returns_none_when_line_missing():
    assert compute_cover_margin(111, 101, None, 'Detroit Pistons -3.5',
                                'Detroit Pistons', 'Cleveland Cavaliers') is None


def test_returns_none_when_side_unresolvable():
    """Empty side -> resolve_pick_side returns None -> we should bail
    rather than guess."""
    assert compute_cover_margin(111, 101, -3.5, '', 'Detroit Pistons',
                                'Cleveland Cavaliers') is None


def test_mlb_runline_home_favorite_covers():
    """MLB-style -1.5 runline. Final NYY 7 - BOS 4 (home wins by 3)."""
    margin = compute_cover_margin(
        home_score=7, away_score=4,
        line=-1.5,
        side='New York Yankees -1.5',
        home_team='New York Yankees', away_team='Boston Red Sox',
    )
    assert margin == 1.5


def test_mlb_runline_away_dog_pushes():
    """MLB +1.5 with home winning by exactly 1.5 is impossible (whole
    runs only) but pushes happen on whole-number lines. Test +1 with
    away losing by exactly 1: push."""
    margin = compute_cover_margin(
        home_score=4, away_score=3,
        line=1.0,
        side='Boston Red Sox +1',
        home_team='New York Yankees', away_team='Boston Red Sox',
    )
    assert margin == 0.0
