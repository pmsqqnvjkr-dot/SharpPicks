"""Postgres product-events source for the unified /api/admin/metrics endpoint.

Direct SQL against user_events (Phase 1 schema) and picks. No external
API, no cache layer — these queries are cheap with the Phase 1 indexes.

Event-name mapping vs spec terminology (see docs/command-center-audit.md):
  spec "signal_view"          -> event_type='view_pick'
  spec "bet_tap_signal_card"  -> event_type='bet_tap' AND surface='signal_card'
  spec "bet_tap_place_bet"    -> event_type='bet_tap' AND surface='place_own_bet'

"signals_issued" comes from the picks table (system-generated rows),
not user_events. The audit doc covers this.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Literal

from sqlalchemy import distinct, func

from models import db, UserEvent, Pick

logger = logging.getLogger(__name__)


def _range_cutoff(range_):
    days = 7 if range_ == '7d' else 30
    return datetime.utcnow() - timedelta(days=days)


def _signals_issued(range_):
    """Count of picks created in window, grouped by sport. include_internal
    has no effect here (picks are system-generated, not user-attributed)."""
    cutoff = _range_cutoff(range_)
    rows = db.session.query(
        Pick.sport, func.count(Pick.id),
    ).filter(Pick.published_at >= cutoff).group_by(Pick.sport).all()
    return {sport or 'unknown': count for sport, count in rows}


def _signal_record_by_sport(range_):
    """Resolved record per sport in window. Returns
    {sport: {wins, losses, pushes, revoked, pending}}.
    Surfaces alongside _signals_issued on the dashboard so the operator
    sees both volume and outcome on the same card."""
    cutoff = _range_cutoff(range_)
    rows = db.session.query(
        Pick.sport, Pick.result, func.count(Pick.id),
    ).filter(Pick.published_at >= cutoff).group_by(Pick.sport, Pick.result).all()
    out = {}
    for sport, result, count in rows:
        key = sport or 'unknown'
        bucket = out.setdefault(key, {'wins': 0, 'losses': 0, 'pushes': 0, 'revoked': 0, 'pending': 0})
        r = (result or 'pending').lower()
        if r == 'win':
            bucket['wins'] += count
        elif r == 'loss':
            bucket['losses'] += count
        elif r == 'push':
            bucket['pushes'] += count
        elif r == 'revoked':
            bucket['revoked'] += count
        else:
            bucket['pending'] += count
    return out


def _bet_taps(range_, include_internal):
    """Count of bet_tap events grouped by surface, with internal toggle."""
    cutoff = _range_cutoff(range_)
    q = db.session.query(
        UserEvent.surface, func.count(UserEvent.id),
    ).filter(
        UserEvent.event_type == 'bet_tap',
        UserEvent.created_at >= cutoff,
    )
    if not include_internal:
        q = q.filter(UserEvent.is_internal == False)  # noqa: E712 (SQLAlchemy)
    rows = q.group_by(UserEvent.surface).all()
    return {(surface or 'unknown'): count for surface, count in rows}


def _unique_tappers(range_, include_internal):
    """Distinct users who fired at least one bet_tap event in the window.
    Powers the 'Unique tappers' tile under the Bet Taps section."""
    cutoff = _range_cutoff(range_)
    q = db.session.query(func.count(distinct(UserEvent.user_id))).filter(
        UserEvent.event_type == 'bet_tap',
        UserEvent.created_at >= cutoff,
        UserEvent.user_id.isnot(None),
    )
    if not include_internal:
        q = q.filter(UserEvent.is_internal == False)  # noqa: E712
    return int(q.scalar() or 0)


def _pass_rate(range_):
    """Fraction of ET days in the window where the model issued zero
    signals across all sports, expressed as a percent (0-100). Mirrors
    the 'Pass days' computation in services/weekly_recap_data.py: a day
    is counted as a pass day only if no sport published a signal that
    date. Revoked picks don't count as published. Returns None when the
    window is degenerate (range_ unknown)."""
    days = 7 if range_ == '7d' else 30 if range_ == '30d' else None
    if days is None:
        return None
    cutoff = _range_cutoff(range_)
    rows = db.session.query(Pick.game_date).filter(
        Pick.published_at >= cutoff,
    ).distinct().all()
    # Revoked picks were already published_at-stamped before being pulled,
    # so they still count as a non-pass day for this metric. The "model
    # tried to fire" semantic is what matters here, not the final result.
    days_with_signal = len({(r[0] or '')[:10] for r in rows if r[0]})
    pass_days = max(days - days_with_signal, 0)
    return round(100.0 * pass_days / days, 1)


def _funnel(include_internal):
    """3-step funnel over the last 7 days, regardless of the dashboard
    range. Anonymous users (user_id IS NULL) are excluded from the funnel
    because we can't follow them across steps; future improvement is to
    include session-level identity for logged-out users.

    Steps:
      signal_view          -> distinct users who fired view_pick
      bet_tap_signal_card  -> distinct users who fired bet_tap surface=signal_card
      bet_tap_place_bet    -> distinct users who fired bet_tap surface=place_own_bet
    """
    cutoff = datetime.utcnow() - timedelta(days=7)

    def _distinct_users(event_type, surface=None):
        q = db.session.query(func.count(distinct(UserEvent.user_id))).filter(
            UserEvent.event_type == event_type,
            UserEvent.created_at >= cutoff,
            UserEvent.user_id.isnot(None),
        )
        if surface is not None:
            q = q.filter(UserEvent.surface == surface)
        if not include_internal:
            q = q.filter(UserEvent.is_internal == False)  # noqa: E712
        return q.scalar() or 0

    step1 = _distinct_users('view_pick')
    step2 = _distinct_users('bet_tap', surface='signal_card')
    step3 = _distinct_users('bet_tap', surface='place_own_bet')

    def _rate(num, denom):
        return round(100.0 * num / denom, 1) if denom else 0.0

    return [
        {'step': 'signal_view',          'users': step1, 'conversion_pct': None},
        {'step': 'bet_tap_signal_card',  'users': step2, 'conversion_pct': _rate(step2, step1)},
        {'step': 'bet_tap_place_bet',    'users': step3, 'conversion_pct': _rate(step3, step2)},
    ]


def _top_signals(include_internal):
    """Top 10 signal_ids by bet_tap count, last 30 days."""
    cutoff = datetime.utcnow() - timedelta(days=30)
    q = db.session.query(
        UserEvent.signal_id,
        func.count(UserEvent.id).label('taps'),
    ).filter(
        UserEvent.event_type == 'bet_tap',
        UserEvent.created_at >= cutoff,
        UserEvent.signal_id.isnot(None),
    )
    if not include_internal:
        q = q.filter(UserEvent.is_internal == False)  # noqa: E712
    rows = q.group_by(UserEvent.signal_id).order_by(
        func.count(UserEvent.id).desc()
    ).limit(10).all()
    return [{'signal_id': sid, 'taps': taps} for sid, taps in rows]


def _recent_bet_taps(include_internal, limit=5):
    """Most recent bet_tap events with surface + signal_id + timestamp."""
    cutoff = datetime.utcnow() - timedelta(days=7)
    q = db.session.query(
        UserEvent.created_at, UserEvent.surface,
        UserEvent.signal_id, UserEvent.is_internal,
    ).filter(
        UserEvent.event_type == 'bet_tap',
        UserEvent.created_at >= cutoff,
    )
    if not include_internal:
        q = q.filter(UserEvent.is_internal == False)  # noqa: E712
    rows = q.order_by(UserEvent.created_at.desc()).limit(limit).all()
    return [
        {
            'at': created_at.isoformat() if created_at else None,
            'surface': surface or 'unknown',
            'signal_id': signal_id,
            'is_internal': bool(is_internal),
        }
        for created_at, surface, signal_id, is_internal in rows
    ]


_REVOKE_TOKEN = 'REVOKED:'


def _extract_revoke_reason(notes):
    """Pull the revoke reason out of Pick.notes. The model pipeline appends
    ' | REVOKED: <reason>' to notes on revocation."""
    if not notes or _REVOKE_TOKEN not in notes:
        return None
    tail = notes.rsplit(_REVOKE_TOKEN, 1)[-1].strip()
    return tail or None


def _recent_signals(limit=10):
    """Most recent issued picks with sport + selection + line + MEI + result."""
    rows = Pick.query.order_by(Pick.published_at.desc()).limit(limit).all()
    out = []
    for p in rows:
        # 'pending' = still live; treat as no result for display
        raw_result = (p.result or '').lower()
        result = raw_result if raw_result and raw_result != 'pending' else None

        sport = (p.sport or '?').upper()
        away = (p.away_team or '').strip()
        home = (p.home_team or '').strip()
        # Pick.side is rendered as e.g. "Philadelphia 76ers +7.5" — the
        # team-with-line string the customer sees. Use it directly as the
        # picked-side label and append "@ opponent".
        side = (p.side or '').strip()
        if side and (away or home):
            opponent = home if side.startswith(away) else away
            selection = f'{side} @ {opponent}' if opponent else side
        elif away and home:
            selection = f'{away} @ {home}'
        else:
            selection = ''

        bits = [sport]
        if selection:
            bits.append(selection)
        # MEI: cover_prob (0..1) is the model's calibrated probability
        # this side covers — the right scale for the dashboard's
        # "MEI tier" visualization (≥0.85 cluster). edge_pct lives on
        # a different scale (-10..+30) and would look broken next to
        # the model perf charts that key off cover_prob buckets.
        mei = p.cover_prob if p.cover_prob is not None else p.model_confidence
        if isinstance(mei, (int, float)) and mei:
            bits.append(f'MEI {mei:.2f}')
        if result:
            bits.append(result.upper())
        out.append({
            'at': p.published_at.isoformat() if p.published_at else None,
            'sport': sport,
            'meta': ' · '.join(bits),
            'result': result,
            'revoke_reason': _extract_revoke_reason(p.notes) if result == 'revoked' else None,
        })
    return out


def fetch(range_: Literal['7d', '30d'], include_internal: bool = False) -> dict:
    """Returns the cache envelope: {payload, fetched_at, stale, last_error}.

    No caching at this layer — the queries are cheap and the unified
    endpoint already pulls all sources concurrently. The envelope shape
    matches the cache-backed sources for uniformity at the /api/admin/metrics
    response level.
    """
    if range_ not in ('7d', '30d'):
        raise ValueError(f'invalid range: {range_}')
    now = datetime.now(timezone.utc)
    try:
        payload = {
            'signals_issued': _signals_issued(range_),
            'signal_record_by_sport': _signal_record_by_sport(range_),
            'pass_rate':      _pass_rate(range_),
            'bet_taps':       _bet_taps(range_, include_internal),
            'unique_tappers': _unique_tappers(range_, include_internal),
            'funnel':         _funnel(include_internal),
            'top_signals':    _top_signals(include_internal),
            'recent_bet_taps': _recent_bet_taps(include_internal),
            'recent_signals': _recent_signals(),
        }
        return {
            'payload': payload,
            'fetched_at': now,
            'stale': False,
            'last_error': None,
        }
    except Exception as e:
        logger.exception('events.fetch failed')
        return {
            'payload': None,
            'fetched_at': None,
            'stale': True,
            'last_error': str(e)[:500] or e.__class__.__name__,
        }
