"""Unit tests for the live cover-tracker calculation in picks_api._compute_cover.

Pins production behavior after the fix that mirrored the home branch's
'margin + spread_val' formula in the away branch (previously was using
the live r['spread_away'] which floats with market movement).

ma['line'] is picked-side perspective (see model_service._build_games_detail):
  - Away pick at -6.5 -> spread_val = -6.5
  - Away pick at +7   -> spread_val = +7
  - Home pick at -3.5 -> spread_val = -3.5
"""
from picks_api import _compute_cover


def test_away_favorite_covering():
    # Away -6.5, away leads 110-100 (margin +10) -> adjusted = +10 + (-6.5) = +3.5
    assert _compute_cover('away', -6.5, h_score=100, a_score=110) == {
        'status': 'covering', 'margin': 3.5,
    }


def test_away_favorite_failing_celtics_case():
    # Production bug repro: BOS -6.5 away, BOS 93, PHI 106.
    # Old code (using live r['spread_away']=+14.5) reported covering by 1.5.
    # Correct: not_covering by 19.5.
    assert _compute_cover('away', -6.5, h_score=106, a_score=93) == {
        'status': 'not_covering', 'margin': 19.5,
    }


def test_away_dog_covering():
    # Away +7, away losing 95-100 (margin -5) -> adjusted = -5 + 7 = +2
    assert _compute_cover('away', 7, h_score=100, a_score=95) == {
        'status': 'covering', 'margin': 2.0,
    }


def test_away_dog_failing():
    # Away +7, away losing 90-110 (margin -20) -> adjusted = -20 + 7 = -13
    assert _compute_cover('away', 7, h_score=110, a_score=90) == {
        'status': 'not_covering', 'margin': 13.0,
    }


def test_home_favorite_covering():
    # Home -3.5, home leads 105-100 (margin +5) -> adjusted = +5 + (-3.5) = +1.5
    assert _compute_cover('home', -3.5, h_score=105, a_score=100) == {
        'status': 'covering', 'margin': 1.5,
    }


def test_home_favorite_failing():
    # Home -3.5, home losing 100-110 (margin -10) -> adjusted = -10 + (-3.5) = -13.5
    assert _compute_cover('home', -3.5, h_score=100, a_score=110) == {
        'status': 'not_covering', 'margin': 13.5,
    }


def test_pickem_away_tied():
    # Away pick'em at 0, tied 100-100 -> adjusted = 0.
    # Per current convention, adjusted == 0 maps to 'not_covering' with margin 0
    # (renderer has no 'push' branch for cover.status).
    assert _compute_cover('away', 0, h_score=100, a_score=100) == {
        'status': 'not_covering', 'margin': 0.0,
    }


def test_away_favorite_tied_early():
    # Away -6.5, tied 50-50 early -> adjusted = 0 + (-6.5) = -6.5
    assert _compute_cover('away', -6.5, h_score=50, a_score=50) == {
        'status': 'not_covering', 'margin': 6.5,
    }
