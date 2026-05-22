"""Users tab queries for the Phase 3 admin Command Center.

Backs two endpoints:
  GET /api/admin/users/activity   -> snapshot, DAU 90d, login freq, tiers, cohort retention
  GET /api/admin/users/list       -> per-user list with tags + activity

Activity is measured as `session_start` events in UserEvent. session_start
has been instrumented since 2026-03-24 (~8 weeks of history at time of
writing). The newer `login` event_type, added 2026-05-04 via a
Flask-Login signal, has only a handful of rows and is too sparse to
power retention math — so the queries below intentionally key off
session_start instead. The product label "logins" is preserved in the
UI to keep operator vocabulary stable; semantically a session_start is
"user opened the app while authenticated", which matches what most ops
ask when they say "logins".

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
    """Subquery of user IDs that count toward customer-facing ACTIVITY
    metrics (DAU/WAU/MAU/cohort retention/user list). Excludes
    is_internal (employees) and deleted_at (soft-deleted spam/test).
    Comped users ARE included here — they log in, they use the app,
    they belong in retention math. Comped users are excluded only from
    PAID metrics (Stripe MRR, active paid subs) where they'd inflate
    revenue figures."""
    return db.session.query(User.id).filter(
        User.is_internal == False,  # noqa: E712
        User.deleted_at.is_(None),
    ).subquery()


# Canonical "user is active" event. session_start has the longest
# instrumented history (back to 2026-03-24); the login event is sparser
# and used only for the legacy unified-events feed. Every per-user
# activity query in this module uses session_start.
ACTIVE_EVENT_TYPE = 'session_start'


def _login_events_query(since=None, until=None):
    """Base query over UserEvent where event_type indicates active session,
    scoped to real users only (joins to the real_user subquery)."""
    real = _real_user_subq()
    q = UserEvent.query.filter(
        UserEvent.event_type == ACTIVE_EVENT_TYPE,
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
        UserEvent.event_type == ACTIVE_EVENT_TYPE,
        UserEvent.created_at >= cutoff_24h,
        UserEvent.user_id.in_(db.session.query(real.c.id)),
        UserEvent.is_internal == False,  # noqa: E712
    ).scalar() or 0

    wau = db.session.query(func.count(distinct(UserEvent.user_id))).filter(
        UserEvent.event_type == ACTIVE_EVENT_TYPE,
        UserEvent.created_at >= cutoff_7d,
        UserEvent.user_id.in_(db.session.query(real.c.id)),
        UserEvent.is_internal == False,  # noqa: E712
    ).scalar() or 0

    mau = db.session.query(func.count(distinct(UserEvent.user_id))).filter(
        UserEvent.event_type == ACTIVE_EVENT_TYPE,
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

    # Free-tier signups: never started a trial, never paid. Used by the
    # admin "what moved" Free / Trial / Paid breakdown so the operator
    # can see whether top-of-funnel growth is from free signups vs
    # checkout-paid trials vs direct paid.
    free_signups_24h = db.session.query(func.count(User.id)).filter(
        User.is_internal == False,  # noqa: E712
        User.deleted_at.is_(None),
        User.created_at >= cutoff_24h,
        User.subscription_status == 'free',
    ).scalar() or 0

    free_signups_7d = db.session.query(func.count(User.id)).filter(
        User.is_internal == False,  # noqa: E712
        User.deleted_at.is_(None),
        User.created_at >= cutoff_7d,
        User.subscription_status == 'free',
    ).scalar() or 0

    # logins_24h: total ACTIVE_EVENT_TYPE events in the last 24h (not
    # distinct users; that's dau). Used by the dashboard "what moved"
    # section to give a sense of session volume even if few people came
    # back twice.
    logins_24h = db.session.query(func.count(UserEvent.id)).filter(
        UserEvent.event_type == ACTIVE_EVENT_TYPE,
        UserEvent.created_at >= cutoff_24h,
        UserEvent.user_id.in_(db.session.query(real.c.id)),
        UserEvent.is_internal == False,  # noqa: E712
    ).scalar() or 0

    # 7-day average baseline for the "vs avg" delta. logins per day
    # over the last 7 days, used as the comparison floor.
    logins_7d = db.session.query(func.count(UserEvent.id)).filter(
        UserEvent.event_type == ACTIVE_EVENT_TYPE,
        UserEvent.created_at >= cutoff_7d,
        UserEvent.user_id.in_(db.session.query(real.c.id)),
        UserEvent.is_internal == False,  # noqa: E712
    ).scalar() or 0

    stickiness_pct = round(100.0 * dau / mau, 1) if mau else 0.0

    return {
        'dau': dau,
        'wau': wau,
        'mau': mau,
        'total_registered': total_registered,
        'stickiness_pct': stickiness_pct,
        'new_7d': new_7d,
        'free_signups_24h': free_signups_24h,
        'free_signups_7d': free_signups_7d,
        'free_signups_7d_avg': round(free_signups_7d / 7.0, 1),
        'logins_24h': logins_24h,
        'logins_7d_avg': round(logins_7d / 7.0, 1),
        'dau_7d_avg': round(wau / 7.0, 1),
    }


def _dau_daily_90d(now: datetime) -> list:
    """Distinct users who logged in per day, last 90 days, oldest first."""
    cutoff = now - timedelta(days=90)
    real = _real_user_subq()
    rows = db.session.query(
        func.date(UserEvent.created_at).label('day'),
        func.count(distinct(UserEvent.user_id)).label('users'),
    ).filter(
        UserEvent.event_type == ACTIVE_EVENT_TYPE,
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
        UserEvent.event_type == ACTIVE_EVENT_TYPE,
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
        UserEvent.event_type == ACTIVE_EVENT_TYPE,
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
        UserEvent.event_type == ACTIVE_EVENT_TYPE,
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


def _login_stats(now: datetime) -> dict:
    """avg + median logins per user across the last 30 days. Real users
    only, excludes internal. Users with 0 logins ARE counted (so the
    average reflects the full user base, not just active users)."""
    cutoff_30d = now - timedelta(days=30)
    real = _real_user_subq()
    rows = db.session.query(
        UserEvent.user_id, func.count(UserEvent.id),
    ).filter(
        UserEvent.event_type == ACTIVE_EVENT_TYPE,
        UserEvent.created_at >= cutoff_30d,
        UserEvent.user_id.in_(db.session.query(real.c.id)),
        UserEvent.is_internal == False,  # noqa: E712
    ).group_by(UserEvent.user_id).all()

    total_users = db.session.query(func.count(User.id)).filter(
        User.is_internal == False,  # noqa: E712
        User.deleted_at.is_(None),
    ).scalar() or 0
    if total_users == 0:
        return {'avg_logins': 0, 'median_logins': 0}

    counts = sorted([n for _, n in rows] + [0] * max(0, total_users - len(rows)))
    avg = round(sum(counts) / total_users, 1)
    mid = total_users // 2
    median = counts[mid] if total_users % 2 else (counts[mid - 1] + counts[mid]) / 2
    return {'avg_logins': avg, 'median_logins': median}


def fetch_activity(range_: str = '30d') -> dict:
    now = datetime.utcnow()
    return {
        'snapshot': _snapshot(now),
        'dau_daily_90d': _dau_daily_90d(now),
        'login_frequency_buckets': _login_frequency_buckets(now),
        'tier_counts': _tier_counts(now),
        'cohort_retention': _cohort_retention(now),
        **_login_stats(now),
    }


# ─────────────────────────────────────────────────────────────────────────
# Users list endpoint
# ─────────────────────────────────────────────────────────────────────────

def _user_tags(u: User, logins_30d: int, has_ios_purchase: bool, days_since_login: int = None) -> list:
    """Compute per-user tags. Returns a list of tag strings; the UI
    renders each as a chip. Most-specific billing tag wins, then
    cancel-intent overlay, then platform/internal flags.

    Billing tags (exactly one):
      founding         -- active + founding_member (paid the $99 founding rate)
      paid_annual      -- active + plan contains 'annual' or 'year' (non-founding)
      paid_monthly     -- active + plan contains 'month'
      paid             -- active but plan unknown
      trial            -- in trial period (card may or may not have been collected)
      pending_verify   -- registered, awaiting email verification
      past_due         -- payment failed; access revoked
      churned          -- cancelled or expired
      free             -- never had a paid sub or trial
    Cancel overlay (added on top of the billing tag):
      cancel_scheduled -- cancel_scheduled_at is set; will downgrade at cancel_effective_at
    Activity / platform overlays:
      power            -- logins_30d >= 15
      ios              -- pro_source == 'revenuecat'
      internal         -- u.is_internal
    """
    tags = []
    if logins_30d >= 15:
        tags.append('power')

    plan = (u.subscription_plan or '').lower()
    status = u.subscription_status or ''

    # Billing tag — most specific wins. Comped beats every other
    # billing tag because the user might have founding_member=True or
    # subscription_status='active' from the manual provisioning flow,
    # but they are not actually paying.
    if getattr(u, 'comped', False):
        tags.append('comped')
    elif status in ('active', 'cancelling'):
        if u.founding_member:
            tags.append('founding')
        elif 'annual' in plan or 'year' in plan or 'founding' in plan:
            tags.append('paid_annual')
        elif 'month' in plan:
            tags.append('paid_monthly')
        else:
            tags.append('paid')
    elif status in ('trial', 'trialing'):
        tags.append('trial')
        # Secondary indicator: what plan they're trialing into. Helps
        # the operator see at a glance whether a trial cancellation
        # is losing $19/mo or $149/yr.
        if 'founding' in plan:
            tags.append('trial_founding')
        elif 'annual' in plan or 'year' in plan:
            tags.append('trial_annual')
        elif 'month' in plan:
            tags.append('trial_monthly')
    elif status == 'pending_verification':
        tags.append('pending_verify')
    elif status == 'past_due':
        tags.append('past_due')
    elif status in ('cancelled', 'expired'):
        tags.append('churned')
    else:
        tags.append('free')

    # Cancel-intent overlay — present whenever a cancel is queued,
    # regardless of trial vs paid. Shows the user "this is going away
    # at cancel_effective_at" without burying them under just the
    # billing tag.
    if u.cancel_scheduled_at is not None:
        tags.append('cancel_scheduled')

    # Platform / role overlays
    if has_ios_purchase:
        tags.append('ios')
    if u.is_internal:
        tags.append('internal')
    return tags


SORT_KEYS = ('created', 'logins', 'last_active', 'days_active')


def fetch_list(segment: str = 'all', search: str = '', limit: int = 50, offset: int = 0,
               sort: str = 'created') -> dict:
    """Returns a filtered, paginated user list with per-user activity stats.

    Segments:
      all     — all real users
      paid    — subscription_status='active'
      trial   — subscription_status='trial'
      power   — logins_30d >= 15
      dormant — registered > 30d ago, logins_30d == 0
      churned — was active, now cancelled, > 30 days since cancellation

    Sort keys (default 'created'):
      created      — User.created_at desc (cheap; index)
      logins       — logins_30d desc (forces full-set event aggregation)
      last_active  — last_seen_at desc (forces full-set event aggregation)
      days_active  — days_active_30d desc (forces full-set event aggregation)

    Event-based sorts compute UserEvent stats across the entire filtered
    candidate set before slicing, so the cost scales with the segment
    size rather than the page size. Default 'created' keeps the fast
    path that only aggregates for the visible page.
    """
    now = datetime.utcnow()
    cutoff_30d = now - timedelta(days=30)

    if sort not in SORT_KEYS:
        sort = 'created'

    # Base query. Apple App Reviewer accounts (ar_user<digits>@icloud.com)
    # are excluded everywhere — they sign up via TestFlight / App Review
    # and would otherwise inflate user / paid metrics.
    _AR_RE = r'^ar_user[0-9]+@icloud\.com$'
    q = User.query.filter(
        User.is_internal == False,  # noqa: E712
        User.deleted_at.is_(None),
        ~User.email.op('~')(_AR_RE),
    )
    if search:
        q = q.filter(func.lower(User.email).contains(search.lower()))

    if segment == 'paid':
        # Paid = anyone actually paying us now. Includes:
        #   - active subscribers (founding annual + paid monthly + paid annual)
        #   - 'cancelling' subs that have paid through a future period_end
        #     (still using what they paid for — Cooper Reynolds case)
        # Excludes comped users (gifted access, not paying).
        q = q.filter(
            User.subscription_status.in_(('active', 'cancelling')),
            User.comped == False,  # noqa: E712
        )
    elif segment == 'trial':
        q = q.filter(User.subscription_status.in_(('trial', 'trialing')))
    elif segment == 'churned':
        q = q.filter(or_(
            User.subscription_status == 'cancelled',
            User.subscription_status == 'cancelling',
        ))
    elif segment == 'attention':
        q = q.filter(or_(
            User.cancel_scheduled_at.isnot(None),
            User.subscription_status.in_(('past_due', 'cancelling')),
        ))
    # 'power' and 'dormant' filter post-aggregation since they need login counts

    total = User.query.filter(
        User.is_internal == False,  # noqa: E712
        User.deleted_at.is_(None),
    ).count()

    # Aggregate logins_30d, bet_taps_30d, days_active_30d, last_seen for the
    # filtered set. For pagination cost, slice the user set BEFORE fetching
    # event counts (so we only aggregate over the displayed page).
    if segment == 'attention':
        # Soonest cancel first (so the most-urgent saves bubble up); fall
        # back to created_at for users without a scheduled cancel date.
        candidate_users = q.order_by(
            User.cancel_effective_at.asc().nulls_last(),
            User.created_at.desc(),
        ).all()
    else:
        candidate_users = q.order_by(User.created_at.desc()).all()

    # Tier-filter post hoc if needed. Power/dormant already need full-set
    # login_counts; we cache them in `precomputed_logins` so the sort
    # path below can reuse instead of re-querying.
    precomputed_logins = None
    precomputed_last_seen = None
    precomputed_days_active = None
    if segment in ('power', 'dormant'):
        ids = [u.id for u in candidate_users]
        precomputed_logins = dict(db.session.query(
            UserEvent.user_id, func.count(UserEvent.id),
        ).filter(
            UserEvent.event_type == ACTIVE_EVENT_TYPE,
            UserEvent.created_at >= cutoff_30d,
            UserEvent.user_id.in_(ids),
            UserEvent.is_internal == False,  # noqa: E712
        ).group_by(UserEvent.user_id).all())
        if segment == 'power':
            candidate_users = [u for u in candidate_users if precomputed_logins.get(u.id, 0) >= 15]
        else:  # dormant
            candidate_users = [
                u for u in candidate_users
                if precomputed_logins.get(u.id, 0) == 0 and u.created_at and u.created_at < cutoff_30d
            ]

    # Event-based sort: aggregate metrics for the full candidate set
    # before slicing. Cheap-sort path (created) skips this and lets the
    # default User.created_at desc order from the queries above stand.
    if sort != 'created' and candidate_users:
        ids = [u.id for u in candidate_users]
        if precomputed_logins is None:
            precomputed_logins = dict(db.session.query(
                UserEvent.user_id, func.count(UserEvent.id),
            ).filter(
                UserEvent.event_type == ACTIVE_EVENT_TYPE,
                UserEvent.created_at >= cutoff_30d,
                UserEvent.user_id.in_(ids),
                UserEvent.is_internal == False,  # noqa: E712
            ).group_by(UserEvent.user_id).all())
        if sort == 'last_active':
            precomputed_last_seen = dict(db.session.query(
                UserEvent.user_id, func.max(UserEvent.created_at),
            ).filter(
                UserEvent.user_id.in_(ids),
                UserEvent.is_internal == False,  # noqa: E712
            ).group_by(UserEvent.user_id).all())
        elif sort == 'days_active':
            precomputed_days_active = dict(db.session.query(
                UserEvent.user_id, func.count(func.distinct(func.date(UserEvent.created_at))),
            ).filter(
                UserEvent.event_type == ACTIVE_EVENT_TYPE,
                UserEvent.created_at >= cutoff_30d,
                UserEvent.user_id.in_(ids),
                UserEvent.is_internal == False,  # noqa: E712
            ).group_by(UserEvent.user_id).all())

        if sort == 'logins':
            candidate_users.sort(key=lambda u: precomputed_logins.get(u.id, 0), reverse=True)
        elif sort == 'last_active':
            far_past = datetime(1970, 1, 1)
            candidate_users.sort(key=lambda u: precomputed_last_seen.get(u.id) or far_past, reverse=True)
        elif sort == 'days_active':
            candidate_users.sort(key=lambda u: precomputed_days_active.get(u.id, 0), reverse=True)

    filtered_count = len(candidate_users)
    page = candidate_users[offset:offset + limit]
    page_ids = [u.id for u in page]

    # Aggregate per-user stats for the page only
    if page_ids:
        login_counts = dict(db.session.query(
            UserEvent.user_id, func.count(UserEvent.id),
        ).filter(
            UserEvent.event_type == ACTIVE_EVENT_TYPE,
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
            'oauth_provider': u.oauth_provider or None,
            'email_verified': bool(getattr(u, 'email_verified', False)),
            'tags': _user_tags(u, l30, u.id in ios_purchase_ids),
            'logins_30d': l30,
            'bet_taps_30d': bet_tap_counts.get(u.id, 0),
            'days_active_30d': days_active.get(u.id, 0),
            'last_seen_at': last_seen.get(u.id).isoformat() if last_seen.get(u.id) else None,
            'subscription_status': u.subscription_status,
            'subscription_plan': u.subscription_plan,
            'founding_member': bool(u.founding_member),
            'founding_number': u.founding_number,
            'cancel_scheduled_at': u.cancel_scheduled_at.isoformat() if u.cancel_scheduled_at else None,
            'cancel_effective_at': u.cancel_effective_at.isoformat() if u.cancel_effective_at else None,
            'trial_converted_at': u.trial_converted_at.isoformat() if u.trial_converted_at else None,
            'trial_end_date': u.trial_end_date.isoformat() if u.trial_end_date else None,
            'created_at': u.created_at.isoformat() if u.created_at else None,
        })

    return {
        'total': total,
        'filtered': filtered_count,
        'limit': limit,
        'offset': offset,
        'users': users_payload,
    }


def fetch_attention_segments(now: datetime = None) -> dict:
    """Compute the Needs Attention card's segment counts + top entries.

    Each segment is a distinct outreach motion: trials about to convert,
    ex-Pro users still using the product (winback candidates), accounts
    that never verified their email and are sitting unverified, payment
    failures, and scheduled cancels. Returns counts + the first two
    users per segment so the operator can take action without a second
    round trip. The full list per segment is reachable via the existing
    /api/admin/users/list endpoint once segments are wired there in a
    follow-up. Engaged → Light decay is intentionally not included; it
    requires a two-window login comparison that isn't cheap and lands
    in a follow-up alongside its UI surface."""
    now = now or datetime.utcnow()
    cutoff_48h_forward = now + timedelta(hours=48)
    cutoff_14d_back = now - timedelta(days=14)
    cutoff_7d_back = now - timedelta(days=7)

    def _serialize(u, extra=None):
        out = {
            'id': u.id,
            'email': u.email,
            'first_name': u.first_name,
            'subscription_status': u.subscription_status,
            'pro_source': u.pro_source,
            'trial_end_date': u.trial_end_date.isoformat() if u.trial_end_date else None,
            'cancel_effective_at': u.cancel_effective_at.isoformat() if u.cancel_effective_at else None,
            'created_at': u.created_at.isoformat() if u.created_at else None,
        }
        if extra:
            out.update(extra)
        return out

    # Trials ending in next 48h. Soonest-first so the most-urgent
    # outreach is at the top.
    trials_q = User.query.filter(
        User.is_internal == False,  # noqa: E712
        User.deleted_at.is_(None),
        User.subscription_status == 'trial',
        User.trial_end_date.isnot(None),
        User.trial_end_date >= now,
        User.trial_end_date <= cutoff_48h_forward,
    ).order_by(User.trial_end_date.asc())
    trials_top = trials_q.limit(4).all()
    trials_count = trials_q.count()

    # Was-Pro still active: status cancelled/expired AND has a UserEvent
    # in the last 14 days. These are users the product is still
    # holding after they stopped paying; primary winback candidate.
    real = _real_user_subq()
    recent_active_ids = db.session.query(distinct(UserEvent.user_id)).filter(
        UserEvent.created_at >= cutoff_14d_back,
        UserEvent.user_id.in_(db.session.query(real.c.id)),
        UserEvent.is_internal == False,  # noqa: E712
    )
    was_pro_q = User.query.filter(
        User.is_internal == False,  # noqa: E712
        User.deleted_at.is_(None),
        User.subscription_status.in_(('cancelled', 'expired')),
        User.id.in_(recent_active_ids),
    ).order_by(User.updated_at.desc())
    was_pro_top = was_pro_q.limit(4).all()
    was_pro_count = was_pro_q.count()

    # Unverified email for more than 7 days. The signup flow's verify
    # email step is a leak point; users who signed up over a week ago
    # and never verified are candidates for a Resend reminder.
    unverified_q = User.query.filter(
        User.is_internal == False,  # noqa: E712
        User.deleted_at.is_(None),
        User.email_verified == False,  # noqa: E712
        User.created_at < cutoff_7d_back,
    ).order_by(User.created_at.desc())
    unverified_top = unverified_q.limit(4).all()
    unverified_count = unverified_q.count()

    # Cancel scheduled (existing motion but worth surfacing in its own
    # row). Anything where cancel_effective_at is still ahead of now.
    cancel_q = User.query.filter(
        User.is_internal == False,  # noqa: E712
        User.deleted_at.is_(None),
        User.cancel_scheduled_at.isnot(None),
        or_(User.cancel_effective_at.is_(None), User.cancel_effective_at >= now),
    ).order_by(User.cancel_effective_at.asc().nulls_last())
    cancel_top = cancel_q.limit(4).all()
    cancel_count = cancel_q.count()

    # Past due / payment failures.
    past_due_q = User.query.filter(
        User.is_internal == False,  # noqa: E712
        User.deleted_at.is_(None),
        User.subscription_status == 'past_due',
    ).order_by(User.updated_at.desc())
    past_due_top = past_due_q.limit(4).all()
    past_due_count = past_due_q.count()

    # Trials specifically with cancel_scheduled. The high-signal Save
    # Window: each row is a trial that explicitly chose to cancel,
    # with a known effective date. Surfaced as a top-row tile on
    # Today's Read because the response window is finite (closes when
    # cancel_effective_at passes) and the conversion path is well-
    # defined. Distinct from the broader cancel_scheduled segment
    # below which mixes trials + active paid subs.
    trial_cancel_q = User.query.filter(
        User.is_internal == False,  # noqa: E712
        User.deleted_at.is_(None),
        User.subscription_status.in_(('trial', 'trialing')),
        User.cancel_scheduled_at.isnot(None),
        or_(User.cancel_effective_at.is_(None), User.cancel_effective_at >= now),
    ).order_by(User.cancel_effective_at.asc().nulls_last())
    trial_cancel_users = trial_cancel_q.all()
    trial_cancel_earliest = next(
        (u.cancel_effective_at for u in trial_cancel_users if u.cancel_effective_at),
        None,
    )

    return {
        'trial_cancels_queued': {
            'count': len(trial_cancel_users),
            'earliest_effective_at': trial_cancel_earliest.isoformat() if trial_cancel_earliest else None,
        },
        'segments': [
            {
                'key': 'trials_ending_48h',
                'label': 'Trials ending in 48h',
                'subtitle': 'Card on file. Auto-renew window opens soon.',
                'count': trials_count,
                'top': [_serialize(u) for u in trials_top],
            },
            {
                'key': 'was_pro_still_active',
                'label': 'Was Pro, still active',
                'subtitle': 'Cancelled but logged in within last 14d. Winback candidates.',
                'count': was_pro_count,
                'top': [_serialize(u) for u in was_pro_top],
            },
            {
                'key': 'unverified_email_7d',
                'label': 'Unverified email > 7d',
                'subtitle': 'Signed up but never verified. Resend reminder candidate.',
                'count': unverified_count,
                'top': [_serialize(u) for u in unverified_top],
            },
            {
                'key': 'cancel_scheduled',
                'label': 'Cancel scheduled',
                'subtitle': 'Active sub with cancel queued. Save window open until effective date.',
                'count': cancel_count,
                'top': [_serialize(u) for u in cancel_top],
            },
            {
                'key': 'past_due',
                'label': 'Payment failed',
                'subtitle': 'Card declined. Retry pending; access may have already been revoked.',
                'count': past_due_count,
                'top': [_serialize(u) for u in past_due_top],
            },
        ],
    }
