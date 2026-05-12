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

from models import db, Pick


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


def _last_10_signals(now: datetime) -> list:
    """Most recent 10 picks ordered by published_at desc."""
    rows = Pick.query.order_by(Pick.published_at.desc()).limit(10).all()
    out = []
    for p in rows:
        result = p.result if p.result in ('win', 'loss', 'push') else 'pending'
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
        })
    return out


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
        'note': (
            'edge_pct used as MEI proxy. Pick schema has no dedicated '
            'mei_score column today; tune _hit_rate_by_edge_tier bucket '
            'thresholds once a real MEI definition lands.'
        ),
    }
