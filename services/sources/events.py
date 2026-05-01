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
            'bet_taps': _bet_taps(range_, include_internal),
            'funnel': _funnel(include_internal),
            'top_signals': _top_signals(include_internal),
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
