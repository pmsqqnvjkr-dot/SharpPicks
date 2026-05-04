"""Users tab queries for the Phase 3 admin Command Center.

Backs two endpoints:
  GET /api/admin/users/activity   -> snapshot, DAU 90d, login freq, tiers, cohort retention
  GET /api/admin/users/list       -> per-user list with tags + activity

Login data comes from UserEvent rows where event_type='login' (added in
Phase 3 via a Flask-Login signal listener in app.py). The signal only
started firing on 2026-05-04, so historical retention will be sparse
for the first few weeks until the events table fills in. That's
acceptable — the bucket will populate naturally.

Internal/test users (User.is_internal == True) and soft-deleted users
(User.deleted_at IS NOT NULL) are excluded from every aggregation here.
This matches the policy applied across the existing admin metrics.
"""
from collections import Counter, defaultdict
from datetime import datetime, timedelta, date

from sqlalchemy import func, distinct, and_, or_

from models import db, User, UserEvent


# ─────────────────────────────────────────────────────────────────────────
# Shared filters
# ─────────────────────────────────────────────────────────────────────────

def _real_user_subq():
    """Subquery of user IDs that count toward customer-facing metrics."""
    return db.session.query(User.id).filter(
        User.is_internal == False,  # noqa: E712
        User.deleted_at.is_(None),
    ).subquery()


def _login_events_query(since=None, until=None):
    """Base query over UserEvent where event_type='login', scoped to real
    users only (joins to the real_user subquery)."""
    real = _real_user_subq()
    q = UserEvent.query.filter(
        UserEvent.event_type == 'login',
        UserEvent.user_id.in_(db.session.query(real.c.id)),
        UserEvent.is_internal == False,  # noqa: E712 — defensive double-filter
    )
    if since is not None:
        q = q.filter(UserEvent.created_at >= since)
    if until is not None:
        q = q.filter(UserEvent.created_at < until)
    return q


# ─────────────────────────────────────────────────────────────────────────
# Activity endpoint
# ─────────────────────────────────────────────────────────────────────────

def _snapshot(now: datetime) -> dict:
    cutoff_24h = now - timedelta(hours=24)
    cutoff_7d  = now - timedelta(days=7)
    cutoff_30d = now - timedelta(days=30)

    real = _real_user_subq()

    dau = db.session.query(func.count(distinct(UserEvent.user_id))).filter(
        UserEvent.event_type == 'login',
        UserEvent.created_at >= cutoff_24h,
        UserEvent.user_id.in_(db.session.query(real.c.id)),
        UserEvent.is_internal == False,  # noqa: E712
    ).scalar() or 0

    wau = db.session.query(func.count(distinct(UserEvent.user_id))).filter(
        UserEvent.event_type == 'login',
        UserEvent.created_at >= cutoff_7d,
        UserEvent.user_id.in_(db.session.query(real.c.id)),
        UserEvent.is_internal == False,  # noqa: E712
    ).scalar() or 0

    mau = db.session.query(func.count(distinct(UserEvent.user_id))).filter(
        UserEvent.event_type == 'login',
        UserEvent.created_at >= cutoff_30d,
        UserEvent.user_id.in_(db.session.query(real.c.id)),
        UserEvent.is_internal == False,  # noqa: E712
    ).scalar() or 0

    total_registered = db.session.query(func.count(User.id)).filter(
        User.is_internal == False,  # noqa: E712
        User.deleted_at.is_(None),
    ).scalar() or 0

    new_7d = db.session.query(func.count(User.id)).filter(
        User.is_internal == False,  # noqa: E712
        User.deleted_at.is_(None),
        User.created_at >= cutoff_7d,
    ).scalar() or 0

    stickiness_pct = round(100.0 * dau / mau, 1) if mau else 0.0

    return {
        'dau': dau,
        'wau': wau,
        'mau': mau,
        'total_registered': total_registered,
        'stickiness_pct': stickiness_pct,
        'new_7d': new_7d,
    }


def _dau_daily_90d(now: datetime) -> list:
    """Distinct users who logged in per day, last 90 days, oldest first."""
    cutoff = now - timedelta(days=90)
    real = _real_user_subq()
    rows = db.session.query(
        func.date(UserEvent.created_at).label('day'),
        func.count(distinct(UserEvent.user_id)).label('users'),
    ).filter(
        UserEvent.event_type == 'login',
        UserEvent.created_at >= cutoff,
        UserEvent.user_id.in_(db.session.query(real.c.id)),
        UserEvent.is_internal == False,  # noqa: E712
    ).group_by('day').order_by('day').all()

    by_day = {r.day.isoformat(): r.users for r in rows}
    out = []
    for i in range(90, -1, -1):
        d = (now - timedelta(days=i)).date().isoformat()
        out.append({'date': d, 'users': by_day.get(d, 0)})
    return out


def _login_frequency_buckets(now: datetime) -> dict:
    """Histogram: per-user login count over last 30 days, bucketed.
    Spec buckets: 0, 1, 2-3, 4-5, 6-9, 10-14, 15-19, 20-29, 30+"""
    cutoff = now - timedelta(days=30)
    real = _real_user_subq()
    rows = db.session.query(
        UserEvent.user_id,
        func.count(UserEvent.id).label('n'),
    ).filter(
        UserEvent.event_type == 'login',
        UserEvent.created_at >= cutoff,
        UserEvent.user_id.in_(db.session.query(real.c.id)),
        UserEvent.is_internal == False,  # noqa: E712
    ).group_by(UserEvent.user_id).all()

    counts = {uid: n for uid, n in rows}

    # Users who never logged in during the window (0 bucket) need to be
    # counted by total_registered minus those with logins.
    total = db.session.query(func.count(User.id)).filter(
        User.is_internal == False,  # noqa: E712
        User.deleted_at.is_(None),
    ).scalar() or 0
    zero_bucket = max(total - len(counts), 0)

    buckets = {'0': zero_bucket, '1': 0, '2-3': 0, '4-5': 0,
               '6-9': 0, '10-14': 0, '15-19': 0, '20-29': 0, '30+': 0}
    for n in counts.values():
        if n == 1:        buckets['1'] += 1
        elif n <= 3:      buckets['2-3'] += 1
        elif n <= 5:      buckets['4-5'] += 1
        elif n <= 9:      buckets['6-9'] += 1
        elif n <= 14:     buckets['10-14'] += 1
        elif n <= 19:     buckets['15-19'] += 1
        elif n <= 29:     buckets['20-29'] += 1
        else:             buckets['30+'] += 1
    return buckets


def _tier_counts(now: datetime) -> dict:
    """power/engaged/light/dormant counts based on logins_30d.
    power:    logins_30d >= 15  (spec-locked)
    engaged:  5-14
    light:    1-4
    dormant:  0 (registered > 30d ago)"""
    cutoff_30d = now - timedelta(days=30)
    real = _real_user_subq()
    rows = db.session.query(
        UserEvent.user_id,
        func.count(UserEvent.id).label('n'),
    ).filter(
        UserEvent.event_type == 'login',
        UserEvent.created_at >= cutoff_30d,
        UserEvent.user_id.in_(db.session.query(real.c.id)),
        UserEvent.is_internal == False,  # noqa: E712
    ).group_by(UserEvent.user_id).all()
    by_uid = {uid: n for uid, n in rows}

    tiers = {'power': 0, 'engaged': 0, 'light': 0, 'dormant': 0}
    users = User.query.filter(
        User.is_internal == False,  # noqa: E712
        User.deleted_at.is_(None),
    ).with_entities(User.id, User.created_at).all()
    for uid, created_at in users:
        n = by_uid.get(uid, 0)
        if n >= 15:
            tiers['power'] += 1
        elif n >= 5:
            tiers['engaged'] += 1
        elif n >= 1:
            tiers['light'] += 1
        elif created_at and created_at < (now - timedelta(days=30)):
            tiers['dormant'] += 1
        # newly-registered with no logins yet aren't 'dormant'; they're
        # just not yet bucketed, intentional.
    return tiers


def _cohort_retention(now: datetime, weeks_back: int = 8) -> list:
    """Weekly cohorts: for each of the last `weeks_back` signup-weeks,
    compute % of cohort who logged in during weeks 0..weeks_back after
    signup. weeks_back=8 means a 9-column heatmap (week 0..week 8).

    Note on cost: this is the heaviest query in the Users tab. Caches
    for 1 hour at the endpoint layer."""
    real = _real_user_subq()
    cohort_start = (now - timedelta(weeks=weeks_back)).date()
    # snap to Monday
    cohort_start -= timedelta(days=cohort_start.weekday())

    # Build user -> (signup_week_start, set(week_offsets)) maps
    users = User.query.filter(
        User.is_internal == False,  # noqa: E712
        User.deleted_at.is_(None),
        User.created_at >= datetime.combine(cohort_start, datetime.min.time()),
    ).with_entities(User.id, User.created_at).all()
    user_signup_week = {}
    cohort_sizes = Counter()
    for uid, ca in users:
        ws = ca.date()
        ws -= timedelta(days=ws.weekday())
        user_signup_week[uid] = ws
        cohort_sizes[ws] += 1

    if not user_signup_week:
        return []

    # Pull every login event for these users in the cohort window
    user_ids = list(user_signup_week.keys())
    login_rows = UserEvent.query.filter(
        UserEvent.event_type == 'login',
        UserEvent.user_id.in_(user_ids),
        UserEvent.is_internal == False,  # noqa: E712
    ).with_entities(UserEvent.user_id, UserEvent.created_at).all()

    # cohort_week -> {week_offset: set(user_ids)}
    seen = defaultdict(lambda: defaultdict(set))
    for uid, ev_at in login_rows:
        signup_ws = user_signup_week[uid]
        delta_weeks = (ev_at.date() - signup_ws).days // 7
        if 0 <= delta_weeks <= weeks_back:
            seen[signup_ws][delta_weeks].add(uid)

    out = []
    # Order cohorts oldest-first so the table reads top-down
    for ws in sorted(cohort_sizes.keys()):
        size = cohort_sizes[ws]
        retention = []
        for w in range(weeks_back + 1):
            n = len(seen.get(ws, {}).get(w, set()))
            pct = round(100.0 * n / size, 0) if size else 0
            retention.append(int(pct))
        out.append({
            'cohort_week': ws.isoformat(),
            'size': size,
            'retention_by_week': retention,
        })
    return out


def fetch_activity(range_: str = '30d') -> dict:
    now = datetime.utcnow()
    return {
        'snapshot': _snapshot(now),
        'dau_daily_90d': _dau_daily_90d(now),
        'login_frequency_buckets': _login_frequency_buckets(now),
        'tier_counts': _tier_counts(now),
        'cohort_retention': _cohort_retention(now),
    }


# ─────────────────────────────────────────────────────────────────────────
# Users list endpoint
# ─────────────────────────────────────────────────────────────────────────

def _user_tags(u: User, logins_30d: int, has_ios_purchase: bool, days_since_login: int = None) -> list:
    """Compute per-user tags. Order matters for visual hierarchy."""
    tags = []
    if logins_30d >= 15:
        tags.append('power')
    plan = (u.subscription_plan or '').lower()
    status = u.subscription_status or ''
    if status == 'active':
        if 'annual' in plan or 'year' in plan:
            tags.append('paid_yearly')
        elif 'month' in plan:
            tags.append('paid_monthly')
        else:
            tags.append('paid')
    elif status == 'trial':
        tags.append('trial')
    elif status == 'cancelling':
        tags.append('churning')
    if has_ios_purchase:
        tags.append('ios')
    if u.is_internal:
        tags.append('internal')
    return tags


def fetch_list(segment: str = 'all', search: str = '', limit: int = 50, offset: int = 0) -> dict:
    """Returns a filtered, paginated user list with per-user activity stats.

    Segments:
      all     — all real users
      paid    — subscription_status='active'
      trial   — subscription_status='trial'
      power   — logins_30d >= 15
      dormant — registered > 30d ago, logins_30d == 0
      churned — was active, now cancelled, > 30 days since cancellation
    """
    now = datetime.utcnow()
    cutoff_30d = now - timedelta(days=30)

    # Base query
    q = User.query.filter(
        User.is_internal == False,  # noqa: E712
        User.deleted_at.is_(None),
    )
    if search:
        q = q.filter(func.lower(User.email).contains(search.lower()))

    if segment == 'paid':
        q = q.filter(User.subscription_status == 'active')
    elif segment == 'trial':
        q = q.filter(User.subscription_status == 'trial')
    elif segment == 'churned':
        q = q.filter(or_(
            User.subscription_status == 'cancelled',
            User.subscription_status == 'cancelling',
        ))
    # 'power' and 'dormant' filter post-aggregation since they need login counts

    total = User.query.filter(
        User.is_internal == False,  # noqa: E712
        User.deleted_at.is_(None),
    ).count()

    # Aggregate logins_30d, bet_taps_30d, days_active_30d, last_seen for the
    # filtered set. For pagination cost, slice the user set BEFORE fetching
    # event counts (so we only aggregate over the displayed page).
    candidate_users = q.order_by(User.created_at.desc()).all()

    # Tier-filter post hoc if needed
    if segment in ('power', 'dormant'):
        # Compute logins_30d for everyone in candidate_users to filter
        ids = [u.id for u in candidate_users]
        login_counts = dict(db.session.query(
            UserEvent.user_id, func.count(UserEvent.id),
        ).filter(
            UserEvent.event_type == 'login',
            UserEvent.created_at >= cutoff_30d,
            UserEvent.user_id.in_(ids),
            UserEvent.is_internal == False,  # noqa: E712
        ).group_by(UserEvent.user_id).all())
        if segment == 'power':
            candidate_users = [u for u in candidate_users if login_counts.get(u.id, 0) >= 15]
        else:  # dormant
            candidate_users = [
                u for u in candidate_users
                if login_counts.get(u.id, 0) == 0 and u.created_at and u.created_at < cutoff_30d
            ]

    filtered_count = len(candidate_users)
    page = candidate_users[offset:offset + limit]
    page_ids = [u.id for u in page]

    # Aggregate per-user stats for the page only
    if page_ids:
        login_counts = dict(db.session.query(
            UserEvent.user_id, func.count(UserEvent.id),
        ).filter(
            UserEvent.event_type == 'login',
            UserEvent.created_at >= cutoff_30d,
            UserEvent.user_id.in_(page_ids),
            UserEvent.is_internal == False,  # noqa: E712
        ).group_by(UserEvent.user_id).all())

        bet_tap_counts = dict(db.session.query(
            UserEvent.user_id, func.count(UserEvent.id),
        ).filter(
            UserEvent.event_type == 'bet_tap',
            UserEvent.created_at >= cutoff_30d,
            UserEvent.user_id.in_(page_ids),
            UserEvent.is_internal == False,  # noqa: E712
        ).group_by(UserEvent.user_id).all())

        days_active = dict(db.session.query(
            UserEvent.user_id,
            func.count(distinct(func.date(UserEvent.created_at))),
        ).filter(
            UserEvent.created_at >= cutoff_30d,
            UserEvent.user_id.in_(page_ids),
            UserEvent.is_internal == False,  # noqa: E712
        ).group_by(UserEvent.user_id).all())

        last_seen = dict(db.session.query(
            UserEvent.user_id, func.max(UserEvent.created_at),
        ).filter(
            UserEvent.user_id.in_(page_ids),
            UserEvent.is_internal == False,  # noqa: E712
        ).group_by(UserEvent.user_id).all())

        # iOS purchase signal: any user whose pro_source is 'revenuecat'
        ios_purchase_ids = {u.id for u in page if (u.pro_source or '').lower() == 'revenuecat'}
    else:
        login_counts = {}
        bet_tap_counts = {}
        days_active = {}
        last_seen = {}
        ios_purchase_ids = set()

    users_payload = []
    for u in page:
        l30 = login_counts.get(u.id, 0)
        users_payload.append({
            'id': u.id,
            'email': u.email,
            'first_name': u.first_name or '',
            'tags': _user_tags(u, l30, u.id in ios_purchase_ids),
            'logins_30d': l30,
            'bet_taps_30d': bet_tap_counts.get(u.id, 0),
            'days_active_30d': days_active.get(u.id, 0),
            'last_seen_at': last_seen.get(u.id).isoformat() if last_seen.get(u.id) else None,
            'subscription_status': u.subscription_status,
            'subscription_plan': u.subscription_plan,
            'created_at': u.created_at.isoformat() if u.created_at else None,
        })

    return {
        'total': total,
        'filtered': filtered_count,
        'limit': limit,
        'offset': offset,
        'users': users_payload,
    }
