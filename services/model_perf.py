"""Model performance metrics for the Phase 3 admin Model tab.

Backs:
  GET /api/admin/model/perf?range=90d -> {win_rate_by_sport_daily,
                                          hit_rate_by_mei_tier,
                                          calibration,
                                          edge_distribution,
                                          last_10_signals}

Reads from Pick table only — picks store both the model's prediction
fields (edge_pct, cover_prob, model_confidence, predicted_margin) and
the resolved outcome fields (result, result_ats, home_score, away_score)
on the same row, so no join is needed.

NOTE on "MEI": the spec calls for hit-rate-by-MEI-tier, but the Pick
schema does not have a dedicated mei_score column. We use edge_pct as
the MEI proxy here. Tier definitions are taken from where edge_pct
typically lands; can be tuned later.
"""
from datetime import datetime, timedelta
from collections import defaultdict

from sqlalchemy import func

from models import db, Pick, Pass


# Resolved means we know the outcome (not pending and not push).
# Pick.result enum is ('win' | 'loss' | 'push' | 'revoked' | 'pending').
# Earlier versions of this module used ('won', 'lost') which silently
# matched no rows — every aggregate downstream came back empty. Match
# the actual schema.
RESOLVED = ('win', 'loss')


def _win_rate_by_sport_daily(now: datetime, days: int = 90, window: int = 14) -> dict:
    """Rolling `window`-day win rate per sport, last `days` days, day-by-day.
    Returns {sport: [{date, win_rate, sample_n}]}."""
    cutoff = now - timedelta(days=days + window)
    rows = db.session.query(
        Pick.sport,
        func.date(Pick.game_date).label('day'),
        Pick.result,
    ).filter(
        Pick.published_at >= cutoff,
        Pick.result.in_(RESOLVED),
    ).all()

    # Group: (sport, day) -> [win_count, total]
    by_day = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for sport, day, result in rows:
        s = sport or 'unknown'
        d = day if isinstance(day, str) else day.isoformat()
        by_day[s][d][1] += 1
        if result == 'win':
            by_day[s][d][0] += 1

    out = {}
    for sport in by_day:
        series = []
        for i in range(days, -1, -1):
            anchor = (now - timedelta(days=i)).date()
            window_wins = 0
            window_total = 0
            for w in range(window):
                d = (anchor - timedelta(days=w)).isoformat()
                bucket = by_day[sport].get(d)
                if bucket:
                    window_wins += bucket[0]
                    window_total += bucket[1]
            rate = (100.0 * window_wins / window_total) if window_total else None
            series.append({
                'date': anchor.isoformat(),
                'win_rate': round(rate, 1) if rate is not None else None,
                'sample_n': window_total,
            })
        out[sport] = series
    return out


def _hit_rate_by_edge_tier(now: datetime, days: int = 90) -> list:
    """Bucket picks by edge_pct, compute win rate per bucket. Tiers picked
    to roughly split the population evenly."""
    cutoff = now - timedelta(days=days)
    rows = db.session.query(Pick.edge_pct, Pick.result).filter(
        Pick.published_at >= cutoff,
        Pick.result.in_(RESOLVED),
    ).all()

    TIERS = [
        ('< 4%',     lambda e: e is not None and e < 4.0),
        ('4-6%',     lambda e: e is not None and 4.0 <= e < 6.0),
        ('6-9%',     lambda e: e is not None and 6.0 <= e < 9.0),
        ('9%+',      lambda e: e is not None and e >= 9.0),
    ]
    out = []
    for label, predicate in TIERS:
        sample = [r for r in rows if predicate(r.edge_pct)]
        n = len(sample)
        wins = sum(1 for r in sample if r.result == 'win')
        rate = round(100.0 * wins / n, 1) if n else None
        out.append({'tier': label, 'hit_rate': rate, 'sample_n': n})
    return out


def _calibration(now: datetime, days: int = 180) -> dict:
    """Predicted cover probability vs observed win rate, bucketed.
    Returns {sport: [{predicted, observed, sample_n}]}.
    Buckets the cover_prob into 5% bins centered at 47.5..82.5%."""
    cutoff = now - timedelta(days=days)
    rows = db.session.query(Pick.sport, Pick.cover_prob, Pick.result).filter(
        Pick.published_at >= cutoff,
        Pick.result.in_(RESOLVED),
        Pick.cover_prob.isnot(None),
    ).all()

    BINS = [(0.45, 0.50), (0.50, 0.55), (0.55, 0.60), (0.60, 0.65),
            (0.65, 0.70), (0.70, 0.75), (0.75, 0.80), (0.80, 0.85)]
    by_sport = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for sport, cp, result in rows:
        for lo, hi in BINS:
            if lo <= cp < hi:
                by_sport[sport][(lo + hi) / 2][1] += 1
                if result == 'win':
                    by_sport[sport][(lo + hi) / 2][0] += 1
                break

    out = {}
    for sport, bins in by_sport.items():
        series = []
        for center in sorted(bins.keys()):
            wins, total = bins[center]
            observed = round(100.0 * wins / total, 1) if total else None
            series.append({
                'predicted': round(center * 100, 1),
                'observed': observed,
                'sample_n': total,
            })
        out[sport] = series
    return out


def _edge_distribution(now: datetime, days: int = 30) -> list:
    """Histogram of edge_pct values across all picks last `days` days.
    Buckets at 1% wide from 0..15%."""
    cutoff = now - timedelta(days=days)
    rows = db.session.query(Pick.edge_pct).filter(
        Pick.published_at >= cutoff,
        Pick.edge_pct.isnot(None),
    ).all()

    buckets = {f'{i}-{i+1}%': 0 for i in range(0, 15)}
    buckets['15%+'] = 0
    for (e,) in rows:
        if e >= 15:
            buckets['15%+'] += 1
        else:
            buckets[f'{int(e)}-{int(e)+1}%'] += 1

    return [{'tier': k, 'count': v} for k, v in buckets.items()]


_REVOKE_TOKEN = 'REVOKED:'


def _extract_revoke_reason(notes):
    """Parse the revoke reason out of the Pick.notes string. The model
    pipeline appends ' | REVOKED: <reason>' to notes when a signal is
    revoked pre-tip (line move, scratched starter, weather, injury).
    Returns the trimmed reason or None if the marker is absent."""
    if not notes or _REVOKE_TOKEN not in notes:
        return None
    tail = notes.rsplit(_REVOKE_TOKEN, 1)[-1].strip()
    return tail or None


def _last_10_signals(now: datetime) -> list:
    """Most recent 10 picks ordered by published_at desc. Preserves the
    'revoked' status so the operator sees revoked signals on the Last 10
    table; the prior mapping silently converted 'revoked' to 'pending'
    and hid an important class of model behavior. revoke_reason is
    parsed from the notes column when present."""
    rows = Pick.query.order_by(Pick.published_at.desc()).limit(10).all()
    out = []
    for p in rows:
        result = p.result if p.result in ('win', 'loss', 'push', 'revoked') else 'pending'
        out.append({
            'id': p.id,
            'sport': p.sport,
            'matchup': f'{p.away_team} @ {p.home_team}',
            'side': p.side,
            'line': p.line,
            'edge_pct': p.edge_pct,
            'cover_prob': p.cover_prob,
            'published_at': p.published_at.isoformat() if p.published_at else None,
            'result': result,
            'profit_units': p.profit_units,
            'revoke_reason': _extract_revoke_reason(p.notes) if result == 'revoked' else None,
        })
    return out


def _revoke_rate(now: datetime, days: int) -> dict:
    """Revoke rate over the trailing `days` window. Top-line metric for
    the Model tab. Returns {'rate': float|None, 'revoked': int,
    'total': int}. Revoke rate = revoked / (total non-pending picks).
    Pending picks excluded because their final state is unknown."""
    cutoff = now - timedelta(days=days)
    total = Pick.query.filter(
        Pick.published_at >= cutoff,
        Pick.result.in_(('win', 'loss', 'push', 'revoked', 'postponed')),
    ).count()
    revoked = Pick.query.filter(
        Pick.published_at >= cutoff,
        Pick.result == 'revoked',
    ).count()
    rate = round(100.0 * revoked / total, 1) if total else None
    return {'rate': rate, 'revoked': revoked, 'total': total}


def _clv_avg_by_sport(now: datetime, days: int = 90) -> dict:
    """Average CLV per sport over the window, plus the settled sample
    size used to compute it. Powers the 'NBA CLV avg' / 'MLB CLV avg'
    rows on the Model tab. NULL clv values are excluded from the mean
    so picks awaiting closing-line capture don't poison the average.

    Returns {sport: {'avg_clv': float|None, 'sample_n': int}}.
    """
    cutoff = now - timedelta(days=days)
    rows = db.session.query(Pick.sport, Pick.clv).filter(
        Pick.published_at >= cutoff,
        Pick.result.in_(RESOLVED),
        Pick.clv.isnot(None),
    ).all()
    bucket = defaultdict(list)
    for sport, clv in rows:
        bucket[(sport or 'unknown').lower()].append(float(clv))
    out = {}
    for sport, vals in bucket.items():
        if not vals:
            out[sport] = {'avg_clv': None, 'sample_n': 0}
            continue
        out[sport] = {
            'avg_clv':  round(sum(vals) / len(vals), 2),
            'sample_n': len(vals),
        }
    return out


def _clv_daily_by_sport(now: datetime, days: int = 30) -> dict:
    """Per-league daily CLV series for the Model Read v2 sparklines on the
    CLV trajectory cards. Each entry is an individual resolved signal
    plotted in chronological order (not a per-day average), so the line
    moves point-to-point across the window. Returns
    {sport: [{date: YYYY-MM-DD, clv: float}]}.

    Reads the same set the CLV avg uses (RESOLVED + clv not null) so the
    sparkline endpoints reconcile with the headline avg value.
    """
    cutoff = now - timedelta(days=days)
    rows = db.session.query(Pick.sport, Pick.game_date, Pick.clv).filter(
        Pick.published_at >= cutoff,
        Pick.result.in_(RESOLVED),
        Pick.clv.isnot(None),
    ).order_by(Pick.game_date.asc(), Pick.id.asc()).all()
    out = defaultdict(list)
    for sport, game_date, clv in rows:
        s = (sport or 'unknown').lower()
        d = game_date if isinstance(game_date, str) else (game_date.isoformat() if game_date else '')
        out[s].append({'date': d[:10], 'clv': round(float(clv), 2)})
    return dict(out)


def _revoke_timeline(now: datetime, days: int = 30) -> dict:
    """Per-day stacked bars + 7d rolling revoke-rate overlay for the
    Model Read v2 revoke timeline chart. Returns:

      {
        'daily':      [{date, resolved, revoked, total}],
        'rolling_7d': [{date, rate}]   # revoked/total over trailing 7d
      }

    Aligned on game_date (not published_at) so each bar corresponds to
    the slate's date rather than when the pick first hit the queue.
    Resolved = win + loss + push + postponed. Pending excluded.
    """
    cutoff = now - timedelta(days=days)
    rows = db.session.query(Pick.game_date, Pick.result).filter(
        Pick.published_at >= cutoff,
        Pick.result.in_(('win', 'loss', 'push', 'revoked', 'postponed')),
    ).all()

    by_day = defaultdict(lambda: [0, 0])  # [resolved, revoked]
    for game_date, result in rows:
        d = game_date if isinstance(game_date, str) else (game_date.isoformat() if game_date else '')
        d = d[:10]
        if not d:
            continue
        if result == 'revoked':
            by_day[d][1] += 1
        else:
            by_day[d][0] += 1

    today = now.date()
    daily = []
    for i in range(days - 1, -1, -1):
        d = (today - timedelta(days=i)).isoformat()
        resolved, revoked = by_day.get(d, [0, 0])
        total = resolved + revoked
        daily.append({
            'date':     d,
            'resolved': resolved,
            'revoked':  revoked,
            'total':    total,
        })

    rolling = []
    window = 7
    for i, _ in enumerate(daily):
        lo = max(0, i - window + 1)
        slice_ = daily[lo:i + 1]
        sum_total   = sum(x['total']   for x in slice_)
        sum_revoked = sum(x['revoked'] for x in slice_)
        rate = round(100.0 * sum_revoked / sum_total, 1) if sum_total else None
        rolling.append({'date': daily[i]['date'], 'rate': rate})

    return {'daily': daily, 'rolling_7d': rolling}


def _pass_rate(now: datetime, days: int = 7, sport: str = None) -> dict:
    """Pass rate over the trailing `days` window for the hero cell.
    pass_rate = passes / (picks + passes). Sport=None aggregates across
    sports; pass a specific sport to narrow.

    Returns {'rate', 'passes', 'picks', 'total_days', 'sport'}.
    """
    cutoff_date = (now - timedelta(days=days)).strftime('%Y-%m-%d')

    pq = Pass.query.filter(Pass.date >= cutoff_date)
    pickq = Pick.query.filter(Pick.game_date >= cutoff_date)
    if sport:
        pq = pq.filter(Pass.sport == sport)
        pickq = pickq.filter(Pick.sport == sport)

    passes = pq.count()
    picks = pickq.count()
    denom = picks + passes
    rate = round(100.0 * passes / denom, 1) if denom else None
    return {
        'rate':       rate,
        'passes':     passes,
        'picks':      picks,
        'total_days': denom,
        'sport':      sport,
    }


def fetch(range_: str = '90d') -> dict:
    days = {'7d': 7, '30d': 30, '90d': 90}.get(range_, 90)
    now = datetime.utcnow()
    return {
        'win_rate_by_sport_daily': _win_rate_by_sport_daily(now, days=days),
        'hit_rate_by_edge_tier':   _hit_rate_by_edge_tier(now, days=days),
        'calibration':             _calibration(now, days=180),
        'edge_distribution':       _edge_distribution(now, days=30),
        'last_10_signals':         _last_10_signals(now),
        'clv_avg_by_sport':        _clv_avg_by_sport(now, days=days),
        'clv_daily_by_sport':      _clv_daily_by_sport(now, days=30),
        'revoke_rate_7d':          _revoke_rate(now, days=7),
        'revoke_rate_30d':         _revoke_rate(now, days=30),
        'revoke_timeline_30d':     _revoke_timeline(now, days=30),
        'pass_rate_7d':            _pass_rate(now, days=7),
        'note': (
            'edge_pct used as MEI proxy. Pick schema has no dedicated '
            'mei_score column today; tune _hit_rate_by_edge_tier bucket '
            'thresholds once a real MEI definition lands.'
        ),
    }
