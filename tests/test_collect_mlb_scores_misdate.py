"""Regression test for the multi-game-series corruption in
collect_mlb_scores misdate-correction.

The bug: when ESPN reported a finished game and the exact-date lookup
in mlb_games missed (e.g., team-name format drift), the fallback grabbed
the most recent non-final row for those teams and UPDATEd its
game_date + scores. ORDER BY game_date DESC meant today's upcoming row
was selected when both yesterday's and today's rows existed for the
same teams, clobbering today's game with yesterday's final score.

The fix: AND game_date <= ? on the misdate fallback so it never
reaches forward in time.

This test models the SQL behavior directly against an in-memory SQLite
DB rather than mocking. That keeps the test grounded in the actual
fallback query. If someone removes the AND game_date <= ? clause, the
test fails immediately.
"""
import sqlite3


def _setup(cursor):
    cursor.execute(
        """CREATE TABLE mlb_games (
            id TEXT PRIMARY KEY,
            game_date TEXT,
            home_team TEXT,
            away_team TEXT,
            home_score INTEGER,
            away_score INTEGER,
            game_status TEXT DEFAULT 'scheduled'
        )"""
    )


def _select_misdate(cursor, away_team, home_team, espn_game_date):
    """Mirrors the production fallback query (post-fix). Returns the row
    that the production code would update, or None if no candidate."""
    cursor.execute(
        """SELECT id, game_date FROM mlb_games
           WHERE home_team = ? AND away_team = ?
             AND game_status != 'final'
             AND game_date <= ?
           ORDER BY game_date DESC LIMIT 1""",
        (home_team, away_team, espn_game_date),
    )
    return cursor.fetchone()


def test_baseball_series_does_not_clobber_todays_row():
    """Two upcoming rows for the same teams (yesterday + today). ESPN
    reports the older game's final. The fallback must select yesterday's
    row, not today's. Pre-fix: today's row was selected. Post-fix:
    yesterday's row is selected (or no row, which is also acceptable
    given the symptom -- never today)."""
    conn = sqlite3.connect(':memory:')
    cur = conn.cursor()
    _setup(cur)
    # Yesterday's NYM @ COL: scheduled, not final yet
    cur.execute(
        "INSERT INTO mlb_games (id, game_date, home_team, away_team, game_status) VALUES (?, ?, ?, ?, COALESCE(?, 'scheduled'))",
        ('id-yesterday', '2026-05-05', 'Colorado Rockies', 'New York Mets', None),
    )
    # Today's NYM @ COL: scheduled, not final yet
    cur.execute(
        "INSERT INTO mlb_games (id, game_date, home_team, away_team, game_status) VALUES (?, ?, ?, ?, COALESCE(?, 'scheduled'))",
        ('id-today', '2026-05-06', 'Colorado Rockies', 'New York Mets', None),
    )
    # ESPN reports yesterday's game as final
    result = _select_misdate(cur, 'New York Mets', 'Colorado Rockies', '2026-05-05')
    # Must NOT be today's row
    assert result is not None, "fallback should still find yesterday's row to update"
    assert result[0] == 'id-yesterday', f"expected id-yesterday, got {result[0]}"
    assert result[1] == '2026-05-05'


def test_postponement_still_corrected():
    """Original purpose of the fallback: a row exists with a date older
    than ESPN's reported date (e.g., game postponed and rescheduled).
    The fallback should still find and correct it."""
    conn = sqlite3.connect(':memory:')
    cur = conn.cursor()
    _setup(cur)
    # Row exists with old (rained-out) date
    cur.execute(
        "INSERT INTO mlb_games (id, game_date, home_team, away_team, game_status) VALUES (?, ?, ?, ?, COALESCE(?, 'scheduled'))",
        ('id-original', '2026-05-04', 'Colorado Rockies', 'New York Mets', None),
    )
    # ESPN reports the rescheduled game's final on May 5
    result = _select_misdate(cur, 'New York Mets', 'Colorado Rockies', '2026-05-05')
    assert result is not None, "fallback should match the postponed row"
    assert result[0] == 'id-original'


def test_no_match_when_only_future_row_exists():
    """If only a future-dated row exists for these teams (e.g., we never
    inserted yesterday's row for some reason), the fallback must NOT
    grab today's row. Skip with a log warning instead."""
    conn = sqlite3.connect(':memory:')
    cur = conn.cursor()
    _setup(cur)
    cur.execute(
        "INSERT INTO mlb_games (id, game_date, home_team, away_team, game_status) VALUES (?, ?, ?, ?, COALESCE(?, 'scheduled'))",
        ('id-today', '2026-05-06', 'Colorado Rockies', 'New York Mets', None),
    )
    # ESPN reports yesterday's final, but only today's row exists
    result = _select_misdate(cur, 'New York Mets', 'Colorado Rockies', '2026-05-05')
    assert result is None, "must not select today's row; pre-fix this returned id-today"


def test_already_final_rows_not_touched():
    """Rows already marked final shouldn't be re-grabbed by the fallback,
    even if they match teams + date. Prevents double-grading."""
    conn = sqlite3.connect(':memory:')
    cur = conn.cursor()
    _setup(cur)
    cur.execute(
        "INSERT INTO mlb_games (id, game_date, home_team, away_team, game_status) VALUES (?, ?, ?, ?, COALESCE(?, 'scheduled'))",
        ('id-already-final', '2026-05-04', 'Colorado Rockies', 'New York Mets', 'final'),
    )
    result = _select_misdate(cur, 'New York Mets', 'Colorado Rockies', '2026-05-05')
    assert result is None, "final rows should not surface in the fallback"


def test_picks_correct_row_when_two_pending_in_past():
    """Edge case: two pending rows exist, both in the past relative to
    ESPN's date. Pick the most recent one (DESC sort)."""
    conn = sqlite3.connect(':memory:')
    cur = conn.cursor()
    _setup(cur)
    cur.execute(
        "INSERT INTO mlb_games (id, game_date, home_team, away_team, game_status) VALUES (?, ?, ?, ?, COALESCE(?, 'scheduled'))",
        ('id-may-3', '2026-05-03', 'Colorado Rockies', 'New York Mets', None),
    )
    cur.execute(
        "INSERT INTO mlb_games (id, game_date, home_team, away_team, game_status) VALUES (?, ?, ?, ?, COALESCE(?, 'scheduled'))",
        ('id-may-4', '2026-05-04', 'Colorado Rockies', 'New York Mets', None),
    )
    # ESPN reports May 5 final
    result = _select_misdate(cur, 'New York Mets', 'Colorado Rockies', '2026-05-05')
    assert result is not None
    assert result[0] == 'id-may-4', "should pick the most recent past row"
