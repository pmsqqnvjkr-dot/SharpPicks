"""Weekly recap data adapter.

Builds the per-send overrides for the Monday weekly recap email. The
recap is fundamentally model-centric: every user gets the same headline
stats (the model's signal count, W-L, CLV beat rate over the prior 7
days). Users who tracked at least one bet via tracked_bets also get a
short personal inset appended to the body paragraph.

The cron in app.py.send_weekly_summary_job calls compute_model_stats
once at the top of the job, then for each eligible user calls
build_recap_overrides to produce the dict that flows to
dispatch_lifecycle_email's `overrides` argument.

Routing rule: if signals_issued in the last 7 days is 0, the variant
key is 'weekly_recap_quiet'; otherwise 'weekly_recap'. The two variant
dicts in lifecycle_emails.py share the same template slots but have
different fixed copy (CTA target, principle quote, eyebrow, subject).
"""

import logging
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import text as sql_text

logger = logging.getLogger(__name__)

# Match the in-app per-sport edge floor displayed in PicksTab.jsx and
# the off-day / pass-day screens. WNBA runs a slightly higher floor
# during calibration; NBA and MLB share +3.5%.
_THRESHOLDS = {'wnba': '+4.5%', 'mlb': '+3.5%', 'nba': '+3.5%'}


def _et_today():
    """Return today's date in America/New_York. The recap cron triggers
    on Monday morning ET, and game_date / passes.date are stored as ET
    date strings, so anchoring the window in ET avoids off-by-one drift
    near midnight UTC."""
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo('America/New_York')).date()
    except Exception:
        # Fallback to UTC if zoneinfo unavailable (unlikely on Python 3.9+).
        return datetime.now(timezone.utc).date()


def _date_range_label(start, end):
    """Format 'May 5 to May 11' for the header_meta line. strftime %-d
    is GNU-specific; explicit int() avoids the platform issue."""
    if start.year != end.year:
        return f"{start.strftime('%b')} {start.day}, {start.year} to {end.strftime('%b')} {end.day}, {end.year}"
    return f"{start.strftime('%b')} {start.day} to {end.strftime('%b')} {end.day}"


def _sport_summary(sports):
    """'NBA', 'NBA and MLB', 'NBA, MLB, and WNBA' from a set of sport
    strings."""
    s = sorted({(x or '').upper() for x in sports if x})
    if not s:
        return 'NBA, MLB, and WNBA'
    if len(s) == 1:
        return s[0]
    if len(s) == 2:
        return f'{s[0]} and {s[1]}'
    return ', '.join(s[:-1]) + f', and {s[-1]}'


def _format_pick_label(side, line):
    """'Colorado Rockies +1.5' from (side='Colorado Rockies', line=1.5).
    If the side string already includes the line (rare but possible),
    don't double-print it."""
    side = side or 'Signal'
    if line is None:
        return side
    line_str = f'{"+" if line > 0 else ""}{line}'
    if line_str.lstrip('+') in side:
        return side
    return f'{side} {line_str}'


def _format_score(home_team, home_score, away_team, away_score):
    """'Phillies 6, Rockies 0' style. Falls back to 'final score
    unrecorded' if scores missing, so the body sentence never reads
    'Final was None to None'."""
    if home_score is None or away_score is None:
        return None
    return f'{home_team} {home_score}, {away_team} {away_score}'


def compute_model_stats(db, today=None):
    """Compute the model-level recap stats over the prior 7 days. Returns
    a dict the cron can reuse across every user it sends to.

    The window is (today - 7 days) inclusive through (today - 1 day)
    inclusive. Running on Monday ET, that captures the prior Monday
    through Sunday. game_date is varchar 'YYYY-MM-DD' so we compare as
    strings; that works because ISO order matches calendar order.
    """
    end = today or _et_today()
    # Window is "last 7 days ending yesterday". On Monday, that runs
    # Mon-prev through Sun-prev inclusive (7 ET dates).
    end_str = (end - timedelta(days=1)).isoformat()
    start_str = (end - timedelta(days=7)).isoformat()

    picks = db.session.execute(sql_text("""
        SELECT id, result, clv, sport, away_team, home_team,
               away_score, home_score, side, line, closing_spread,
               game_date, edge_pct
        FROM picks
        WHERE game_date >= :start AND game_date <= :end
    """), {'start': start_str, 'end': end_str}).fetchall()

    # Revoked picks never went live to users; drop them from every
    # count so the recap reflects what users actually saw.
    signals = [p for p in picks if (p.result or '') != 'revoked']
    settled = [p for p in signals if p.result in ('win', 'loss', 'push')]
    wins = sum(1 for p in settled if p.result == 'win')
    losses = sum(1 for p in settled if p.result == 'loss')

    # CLV beat rate: share of settled signals where clv > 0. Computed
    # over all settled (win/loss/push), not just wins, because CLV is
    # the institutional metric independent of outcome.
    settled_with_clv = [p for p in settled if p.clv is not None]
    clv_beats = sum(1 for p in settled_with_clv if (p.clv or 0) > 0)
    clv_beat_rate = round(100 * clv_beats / len(settled_with_clv)) if settled_with_clv else None

    # Pass days = number of ET dates in the 7-day window where the model
    # issued zero signals. The passes table is grained per (date, sport)
    # so a raw COUNT(*) would overcount; the right measure is "dates with
    # no published signal", which is computed from the picks set we
    # already have above.
    days_in_window = 7
    signal_dates = {p.game_date for p in signals if p.game_date}
    pass_days = max(days_in_window - len(signal_dates), 0)

    # Slates scanned: count of (date, sport) model runs that actually
    # had games on the slate. Used by the quiet variant.
    slates_scanned = db.session.execute(sql_text("""
        SELECT COUNT(*) FROM model_runs
        WHERE date >= :start AND date <= :end AND games_analyzed > 0
    """), {'start': start_str, 'end': end_str}).scalar() or 0

    # Dominant sport drives the qualifying-threshold label in the quiet
    # variant. If we have signals, pick the sport with the most signals;
    # otherwise the sport that scanned the most slates.
    sport_counts = {}
    for p in signals:
        s = (p.sport or '').lower()
        sport_counts[s] = sport_counts.get(s, 0) + 1
    if not sport_counts:
        slate_sports = db.session.execute(sql_text("""
            SELECT sport, COUNT(*) FROM model_runs
            WHERE date >= :start AND date <= :end AND games_analyzed > 0
            GROUP BY sport
        """), {'start': start_str, 'end': end_str}).fetchall()
        for row in slate_sports:
            sport_counts[(row[0] or '').lower()] = row[1]
    dominant_sport = max(sport_counts, key=sport_counts.get) if sport_counts else 'nba'

    # Sport summary for the subhead.
    sports = {(p.sport or '') for p in signals if p.sport}
    if not sports:
        # No signals means we fall back to whichever sports HAD slates.
        slate_sport_rows = db.session.execute(sql_text("""
            SELECT DISTINCT sport FROM model_runs
            WHERE date >= :start AND date <= :end AND games_analyzed > 0
        """), {'start': start_str, 'end': end_str}).fetchall()
        sports = {(r[0] or '') for r in slate_sport_rows}
    sport_summary = _sport_summary(sports)

    # Losing-CLV-beat story: most recent settled loss where the closing
    # line moved in the pick's direction. This is the brand-critical
    # paragraph in the standard variant. Falls back to the most recent
    # winning CLV-beat if no such loss exists.
    settled_sorted = sorted(settled, key=lambda x: x.game_date or '', reverse=True)
    loss_story = next((p for p in settled_sorted
                       if p.result == 'loss' and (p.clv or 0) > 0), None)
    if not loss_story:
        loss_story = next((p for p in settled_sorted
                           if p.result == 'win' and (p.clv or 0) > 0), None)

    return {
        'signals_issued': len(signals),
        'wins': wins,
        'losses': losses,
        'pass_days': pass_days,
        'slates_scanned': slates_scanned,
        'clv_beat_rate': clv_beat_rate,
        'sport_summary': sport_summary,
        'dominant_sport': dominant_sport,
        'loss_story': loss_story,
        'window_start': end - timedelta(days=7),
        'window_end': end - timedelta(days=1),
    }


def compute_user_inset(db, user_id, window_start, window_end):
    """Compute a per-user tracked-bets inset for the body paragraph.
    Returns None if the user tracked nothing in the window, otherwise
    a single sentence ready to append after the model story.

    `window_start` and `window_end` are date objects (inclusive). We
    filter on tracked_bets.settled_at, treating the window in ET via
    naive timestamps (the column is stored without tz; settled_at is
    written by the grading job which runs in UTC, but the 7-day window
    is wide enough that a few hours of TZ drift doesn't shift members).
    """
    rows = db.session.execute(sql_text("""
        SELECT result FROM tracked_bets
        WHERE user_id = :uid
          AND settled_at IS NOT NULL
          AND settled_at >= :start
          AND settled_at < :end
    """), {
        'uid': user_id,
        'start': datetime.combine(window_start, datetime.min.time()),
        'end': datetime.combine(window_end + timedelta(days=1), datetime.min.time()),
    }).fetchall()

    if not rows:
        return None

    wins = sum(1 for r in rows if r.result == 'win')
    losses = sum(1 for r in rows if r.result == 'loss')
    pushes = sum(1 for r in rows if r.result == 'push')
    n = len(rows)

    # Build a single sentence. If pushes exist, mention them; otherwise
    # leave them out for a tighter line.
    record = f'{wins}-{losses}' + (f' with {pushes} push' if pushes == 1 else f' with {pushes} pushes' if pushes else '')
    return f'Your tracked record: {record} on {n} signal{"" if n == 1 else "s"} last week.'


def _is_first_send(today=None):
    """When WEEKLY_RECAP_FIRST_SEND_DATE (env var, YYYY-MM-DD) matches
    today's ET date, the header_meta line gets a 'NEW' badge so the
    cold-start week doesn't surprise users. Set the env var when you
    deploy, leave unset on subsequent weeks."""
    target = os.environ.get('WEEKLY_RECAP_FIRST_SEND_DATE', '').strip()
    if not target:
        return False
    try:
        return (today or _et_today()).isoformat() == target
    except Exception:
        return False


def build_recap_overrides(model_stats, user_inset=None, today=None):
    """Return (variant_key, overrides_dict).

    variant_key is one of 'weekly_recap' / 'weekly_recap_quiet'.
    overrides_dict is the per-send field map passed to
    dispatch_lifecycle_email's `overrides` argument.

    Mutates nothing on the input; safe to call once per user inside the
    cron loop.
    """
    new_tag = ' . NEW' if _is_first_send(today) else ''
    date_label = _date_range_label(model_stats['window_start'], model_stats['window_end'])
    header_meta = f'Weekly recap{new_tag} . {date_label}'

    if model_stats['signals_issued'] == 0:
        return ('weekly_recap_quiet', _quiet_overrides(model_stats, header_meta, user_inset))
    return ('weekly_recap', _standard_overrides(model_stats, header_meta, user_inset))


def _standard_overrides(s, header_meta, user_inset):
    signals = s['signals_issued']
    wins = s['wins']
    losses = s['losses']
    record = f'{wins}-{losses}' if (wins + losses) else f'{signals} issued'
    clv_value = f'{s["clv_beat_rate"]}%' if s['clv_beat_rate'] is not None else '—'

    headline = (
        f'{signals} signal{"" if signals == 1 else "s"}. '
        f'{s["pass_days"]} day{"" if s["pass_days"] == 1 else "s"} off. '
        f'The model worked.'
    )

    pass_phrase = (
        f'passed on {s["pass_days"]} day{"" if s["pass_days"] == 1 else "s"} '
        f'and issued {signals} signal{"" if signals == 1 else "s"}'
    )
    clv_sentence = (
        f'The closing line moved in the pick\'s favor on {s["clv_beat_rate"]} percent '
        f'of settled signals, which is the metric that actually predicts long-term edge.'
        if s['clv_beat_rate'] is not None
        else 'CLV data for some picks is still settling.'
    )
    subhead = (
        f'The slate ran across {s["sport_summary"]} last week. The model {pass_phrase} '
        f'on the others. {clv_sentence}'
    )

    body = _build_loss_story(s['loss_story']) if s['loss_story'] else (
        'The model held its discipline last week. Pass days protected capital, '
        'and on the signals that did clear, the closing line moved toward the '
        'pick more often than not. Variance washes out over hundreds of bets, '
        'but closing line value compounds every time.'
    )
    if user_inset:
        body = body + '<br/><br/>' + user_inset

    return {
        'header_meta': header_meta,
        'headline': headline,
        'subhead': subhead,
        'stat1_label': 'CLV beat rate',
        'stat1_value': clv_value,
        'stat2_label': f'Record . {signals} signal{"" if signals == 1 else "s"}',
        'stat2_value': record,
        'stat3_label': 'Pass days',
        'stat3_value': f'{s["pass_days"]} of 7',
        'body_paragraph': body,
    }


def _quiet_overrides(s, header_meta, user_inset):
    threshold = _THRESHOLDS.get(s['dominant_sport'], '+3.5%')
    headline = (
        f'{s["pass_days"]} pass day{"" if s["pass_days"] == 1 else "s"}. '
        f'No signal. Capital preserved.'
    )
    subhead = (
        f'The model scanned every slate across {s["sport_summary"]} last week. '
        f'No edge cleared the qualifying threshold on any day. This is not a bug '
        f'or an outage. The market was efficient last week, and the system refused '
        f'to manufacture signals where the data did not support them. Most weeks '
        f'include at least one signal. Some weeks do not. The institutional '
        f'discipline is the same.'
    )
    body = (
        f'Coming in below the {threshold} qualifying threshold on every slate is '
        f'the difference between disciplined and undisciplined betting. Most '
        f'platforms issue picks every day because subscribers expect content. That '
        f'is the business model, not the math. {s["pass_days"]} pass day'
        f'{"" if s["pass_days"] == 1 else "s"} in a week is not the system being '
        f'lazy. It is the system refusing to manufacture edge that does not exist.'
    )
    if user_inset:
        body = body + '<br/><br/>' + user_inset

    return {
        'header_meta': header_meta,
        'headline': headline,
        'subhead': subhead,
        'stat1_label': 'Slates scanned',
        'stat1_value': str(s['slates_scanned']),
        'stat2_label': 'Pass days',
        'stat2_value': f'{s["pass_days"]} of 7',
        'stat3_label': 'Qualifying threshold',
        'stat3_value': threshold,
        'body_paragraph': body,
    }


def _build_loss_story(pick):
    """The brand-critical paragraph: a loss that beat the closing line.
    Falls back to a win-with-CLV-beat if no qualifying loss exists; that
    path is invoked by the caller via the same loss_story field."""
    label = _format_pick_label(pick.side, pick.line)
    score = _format_score(pick.home_team, pick.home_score, pick.away_team, pick.away_score)
    clv = pick.clv or 0
    entry = pick.line
    closing = pick.closing_spread

    line_movement = ''
    if entry is not None and closing is not None:
        # closing_spread is stored in home perspective; the CLV value
        # already reflects the picked-side delta, so reuse it for the
        # narrative without re-deriving perspective here.
        line_movement = (
            f' The line closed having moved {abs(clv):.1f} '
            f'point{"" if abs(clv) == 1 else "s"} '
            f'in the pick\'s favor.'
        )

    if pick.result == 'loss':
        opener = (
            f'The losing signal was {label}. '
            f'{("Final was " + score + ". ") if score else ""}'
            f'The bet did not cover, but the closing line value was +{abs(clv):.1f}.'
        )
        return (
            opener + line_movement +
            ' Losing a bet that beat the closing line is the textbook example of '
            'process working without the outcome following. CLV compounds every '
            'time, even when the scoreboard does not.'
        )

    opener = (
        f'A representative signal last week was {label}, settled as a win. '
        f'{("Final was " + score + ". ") if score else ""}'
        f'CLV closed at +{abs(clv):.1f}.'
    )
    return (
        opener + line_movement +
        ' Wins that also beat the closing line are the version of "process and '
        'outcome aligned" the model is built to produce.'
    )
