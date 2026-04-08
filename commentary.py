"""
Dynamic commentary for SharpPicks Command Center admin dashboard.

Each function accepts data dicts and returns (type, label, text) for rendering.
Types: insight (neutral/positive), warning (watch), alert (critical).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

TypeStr = str  # "insight" | "warning" | "alert"


def _strong(s: Any) -> str:
    return f"<strong>{s}</strong>"


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        if v is None:
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def _safe_int(v: Any, default: int = 0) -> int:
    try:
        if v is None:
            return default
        return int(v)
    except (TypeError, ValueError):
        return default


def _parse_bucket_record(record: Any) -> Tuple[int, int, int]:
    """Parse '5-1' style record into wins, losses, total games."""
    if record is None:
        return 0, 0, 0
    s = str(record).strip()
    if not s or "-" not in s:
        return 0, 0, 0
    parts = s.split("-", 1)
    try:
        w = int(parts[0].strip())
        l = int(parts[1].strip())
        return w, l, w + l
    except (ValueError, IndexError):
        return 0, 0, 0


def _bucket_samples(
    bucket_rates: Optional[Dict[str, Any]], buckets: Optional[Dict[str, Any]]
) -> List[Tuple[str, float, int, int, int]]:
    """
    Returns list of (range_key, win_rate_pct, wins, losses, n) for buckets with n > 0.
    win_rate from bucket_rates; wins/losses from buckets record.
    """
    out: List[Tuple[str, float, int, int, int]] = []
    rates = bucket_rates or {}
    recs = buckets or {}
    keys = set(rates.keys()) | set(recs.keys())
    for k in keys:
        rate = _safe_float(rates.get(k), -1.0)
        w, l, n = _parse_bucket_record(recs.get(k))
        if n == 0 and rate >= 0:
            # infer n unknown; skip for sample-based logic unless we have record
            continue
        if rate < 0 and n > 0:
            rate = (100.0 * w / n) if n else 0.0
        elif n > 0 and k not in rates:
            rate = (100.0 * w / n) if n else 0.0
        if n > 0:
            out.append((str(k), float(rate), w, l, n))
    return out


def _best_bucket(
    bucket_rates: Optional[Dict[str, Any]], buckets: Optional[Dict[str, Any]], min_n: int = 3
) -> Optional[Tuple[str, float, int]]:
    """(range, rate, n) or None."""
    candidates = [t for t in _bucket_samples(bucket_rates, buckets) if t[4] >= min_n]
    if not candidates:
        return None
    best = max(candidates, key=lambda x: (x[1], x[4]))
    return best[0], best[1], best[4]


def _worst_bucket_under(
    bucket_rates: Optional[Dict[str, Any]],
    buckets: Optional[Dict[str, Any]],
    max_rate: float,
    min_n: int = 3,
) -> Optional[Tuple[str, float, int, int, int]]:
    """(range, rate, w, l, n) among buckets with rate < max_rate and n >= min_n."""
    candidates = [
        t
        for t in _bucket_samples(bucket_rates, buckets)
        if t[4] >= min_n and t[1] < max_rate
    ]
    if not candidates:
        return None
    worst = min(candidates, key=lambda x: (x[1], -x[4]))
    return worst[0], worst[1], worst[2], worst[3], worst[4]


def _pct_str(x: float, digits: int = 1) -> str:
    return f"{x:.{digits}f}"


def _money_str(x: float) -> str:
    return f"${x:,.2f}"


def pulse_daily_read(
    nba_data: Dict[str, Any],
    mlb_data: Dict[str, Any],
    revenue: Dict[str, Any],
    active_users: int,
    total_users: int,
) -> Tuple[TypeStr, str, str]:
    parts: List[str] = []
    result_type: TypeStr = "insight"

    nba = nba_data or {}
    nw = _safe_int(nba.get("wins"))
    nl = _safe_int(nba.get("losses"))
    nba_n = nw + nl
    nba_roi = _safe_float(nba.get("roi"))
    nba_wr = (100.0 * nw / nba_n) if nba_n else 0.0

    if nba_n > 0:
        if nba_roi > 0:
            parts.append(
                f"NBA model is running above water at {_strong(_pct_str(nba_wr))}% "
                f"with a positive ROI."
            )
        elif nba_roi < -5:
            parts.append(
                f"NBA model is underwater at {_strong(_pct_str(nba_wr))}% "
                f"with {_strong(_pct_str(nba_roi))}% ROI."
            )
        elif -5 <= nba_roi <= 0:
            parts.append(f"NBA model is flat at {_strong(_pct_str(nba_wr))}%.")

    br = nba.get("bucket_rates") if isinstance(nba.get("bucket_rates"), dict) else {}
    bk = nba.get("buckets") if isinstance(nba.get("buckets"), dict) else {}
    bb = _best_bucket(br, bk, min_n=3)
    if bb:
        rng, rate, n = bb
        parts.append(
            f"The {_strong(rng)} edge bucket is the engine at {_strong(_pct_str(rate))}% "
            f"hit rate on {_strong(n)} picks."
        )
    wb = _worst_bucket_under(br, bk, max_rate=50.0, min_n=3)
    if wb:
        rng, rate, w, l, n = wb
        parts.append(
            f"The {_strong(rng)} range is dragging at {_strong(_pct_str(rate))}% "
            f"({_strong(w)}-{_strong(l)})."
        )

    mlb = mlb_data or {}
    mw = _safe_int(mlb.get("wins"))
    ml_ = _safe_int(mlb.get("losses"))
    mlb_n = mw + ml_
    mlb_roi = _safe_float(mlb.get("roi"))
    mlb_tp = _safe_int(mlb.get("total_picks"))
    if mlb_tp <= 0:
        mlb_tp = mlb_n
    picks_ref = mlb_tp if mlb_tp else mlb_n

    if picks_ref < 15:
        parts.append(
            f"MLB is too early to judge at {_strong(picks_ref)} picks -- "
            f"sample size is noise."
        )
    else:
        mlb_wr = (100.0 * mw / mlb_n) if mlb_n else 0.0
        if mlb_roi > 0:
            parts.append(
                f"MLB running at {_strong(_pct_str(mlb_wr))}% "
                f"with {_strong(_pct_str(mlb_roi))}% ROI."
            )
        elif mlb_roi < 0:
            parts.append(
                f"MLB underwater at {_strong(_pct_str(mlb_wr))}% "
                f"with {_strong(_pct_str(mlb_roi))}% ROI."
            )

    au = _safe_int(active_users)
    tu = _safe_int(total_users)
    if tu > 0:
        act_pct = 100.0 * au / tu
        if act_pct < 30:
            parts.append(
                f"{_strong(au)} active users out of {_strong(tu)} signups. "
                f"Activation is the bottleneck, not acquisition."
            )
            result_type = "warning"
        else:
            parts.append(f"{_strong(au)} of {_strong(tu)} users active. Healthy activation.")

    rev = revenue or {}
    if "mrr" in rev:
        mrr = _safe_float(rev.get("mrr"))
        parts.append(f"MRR is {_strong(_money_str(mrr))}.")

    text = " ".join(p for p in parts if p).strip()
    if not text:
        text = "Insufficient data for a daily read."
    return result_type, "Daily Read", text


def pulse_traffic_note(
    visitors_7d: int, views_7d: int, pages_per_visit: float, total_signups: int
) -> Tuple[TypeStr, str, str]:
    v = _safe_int(visitors_7d)
    pv = _safe_float(pages_per_visit)
    su = _safe_int(total_signups)
    typ: TypeStr = "insight"
    views = _safe_int(views_7d)
    parts = [
        f"{_strong(v)} visitors (7d), {_strong(views)} views, "
        f"{_strong(_pct_str(pv, 1))} pages/visit on average."
    ]
    if su > 0 and v > 0:
        conv = 100.0 * su / v
        parts.append(f"Signup conversion {_strong(_pct_str(conv))}%.")
        if conv > 20:
            parts.append("Strong for a cold launch with no paid acquisition.")
    text = " ".join(parts).strip()
    return typ, "Traffic Note", text


def nba_model_read(nba_data: Dict[str, Any]) -> Tuple[TypeStr, str, str]:
    nba = nba_data or {}
    typ: TypeStr = "insight"
    parts: List[str] = []

    tp_clv = _safe_int(nba.get("total_picks"))
    if not tp_clv:
        tp_clv = _safe_int(nba.get("wins")) + _safe_int(nba.get("losses"))
    clv_raw = nba.get("clv_pct")
    clv = _safe_float(clv_raw)
    has_clv = clv_raw is not None
    if has_clv and tp_clv > 0:
        if clv > 40:
            parts.append(
                f"CLV+ at {_strong(_pct_str(clv))}% means the model is finding real inefficiencies "
                f"even when picks don't cash."
            )
        elif clv < 20:
            parts.append(
                f"CLV+ at {_strong(_pct_str(clv))}% is concerning -- "
                f"the market is not confirming these edges."
            )
            typ = "warning"

    br = nba.get("bucket_rates") if isinstance(nba.get("bucket_rates"), dict) else {}
    bk = nba.get("buckets") if isinstance(nba.get("buckets"), dict) else {}
    bb = _best_bucket(br, bk, min_n=3)
    if bb:
        rng, rate, n = bb
        parts.append(
            f"The {_strong(rng)} bucket is carrying at {_strong(_pct_str(rate))}% "
            f"on {_strong(n)} picks."
        )

    wb = _worst_bucket_under(br, bk, max_rate=50.0, min_n=3)
    if wb:
        rng, rate, w, l, n = wb
        parts.append(
            f"The {_strong(rng)} range is underperforming at {_strong(_pct_str(rate))}% "
            f"({_strong(w)}-{_strong(l)}), pulling overall ROI down."
        )
        if n >= 5 and rate < 45:
            parts.append(
                "Worth investigating whether the model is overvaluing large spreads in that range."
            )

    tp = tp_clv
    wr = _safe_float(nba.get("win_rate"))
    if not wr and tp:
        tw = _safe_int(nba.get("wins"))
        wr = (100.0 * tw / tp) if tp else 0.0

    if tp > 50:
        if 50 < wr <= 55:
            parts.append("Model is profitable but running on thin margins.")
        elif wr > 55:
            parts.append("Strong hit rate. Model is performing above the profitability threshold.")

    text = " ".join(parts).strip()
    if not text:
        text = "Insufficient NBA model data for commentary."
    return typ, "NBA Model Read", text


def mlb_model_read(mlb_data: Dict[str, Any]) -> Tuple[TypeStr, str, str]:
    mlb = mlb_data or {}
    typ: TypeStr = "insight"
    parts: List[str] = []

    tw = _safe_int(mlb.get("wins"))
    tl = _safe_int(mlb.get("losses"))
    n_rec = tw + tl
    tp = _safe_int(mlb.get("total_picks"))
    if tp <= 0:
        tp = n_rec
    roi = _safe_float(mlb.get("roi"))
    clv = _safe_float(mlb.get("clv_pct"))
    sel = _safe_float(mlb.get("selectivity"))

    if (mlb.get("clv_pct") is not None and clv < 10) or sel > 70 or tp < 20:
        typ = "warning"

    if tp < 15:
        parts.append(f"{_strong(tp)} picks is not a sample.")
        if roi > 0:
            parts.append(f"The {_strong(_pct_str(roi))}% ROI is noise at this volume.")
    else:
        clv_provided = mlb.get("clv_pct") is not None
        if clv_provided and clv == 0:
            parts.append(
                "CLV+ at 0% is a yellow flag -- "
                "the model isn't beating the closing line on any MLB pick yet."
            )
            typ = "warning"
        elif clv > 0 and clv < 20:
            parts.append(f"CLV+ at {_strong(_pct_str(clv))}% is marginal.")
        if sel > 70:
            parts.append(
                f"Selectivity at {_strong(_pct_str(sel))}% is unusually high -- "
                f"the model may be too aggressive for early-season baseball."
            )
        if tp >= 20 and clv > 30:
            parts.append(
                f"CLV+ at {_strong(_pct_str(clv))}% is encouraging. Market is confirming edges."
            )

    if tp >= 20:
        br = mlb.get("bucket_rates") if isinstance(mlb.get("bucket_rates"), dict) else {}
        bk = mlb.get("buckets") if isinstance(mlb.get("buckets"), dict) else {}
        bb = _best_bucket(br, bk, min_n=3)
        if bb:
            rng, rate, n = bb
            parts.append(
                f"Best edge bucket {_strong(rng)} at {_strong(_pct_str(rate))}% "
                f"({_strong(n)} picks)."
            )
        wb = _worst_bucket_under(br, bk, max_rate=50.0, min_n=3)
        if wb:
            rng, rate, w, l, n = wb
            parts.append(
                f"Weakest bucket {_strong(rng)} at {_strong(_pct_str(rate))}% "
                f"({_strong(w)}-{_strong(l)})."
            )

    text = " ".join(parts).strip()
    if not text:
        text = "Insufficient MLB model data for commentary."
    return typ, "MLB Model Read", text


def _is_refresh_lines_job(name: str) -> bool:
    n = (name or "").lower()
    return ("refresh" in n and "line" in n) or ("closing" in n and "line" in n)


def infra_note(
    cron_jobs: List[Dict[str, Any]],
    pipeline_games: Optional[int] = None,
    pipeline_duration: Optional[float] = None,
) -> Tuple[TypeStr, str, str]:
    typ: TypeStr = "insight"
    parts: List[str] = []

    jobs = list(cron_jobs or [])
    ok_health = ("healthy", "ok", "success")
    failed_24h: List[str] = []
    stale: List[Tuple[str, float]] = []
    amber_refresh_outside_window: List[str] = []

    for j in jobs:
        name = str(j.get("name") or "unknown")
        h = str(j.get("health", "")).lower()
        hours_ago = _safe_float(j.get("hours_ago"), -1.0)
        if h in ("failed", "error", "down"):
            if hours_ago < 0 or hours_ago <= 24:
                failed_24h.append(name)
        if j.get("stale") is True or h == "stale":
            if hours_ago >= 0:
                stale.append((name, hours_ago))
            else:
                stale.append((name, 0.0))
        th = _safe_float(j.get("stale_after_hours"), -1.0)
        if th > 0 and hours_ago >= th and h not in ("failed", "error", "down"):
            stale.append((name, hours_ago))
        if h == "amber" and _is_refresh_lines_job(name):
            if j.get("in_game_window") is False:
                amber_refresh_outside_window.append(name)

    if failed_24h:
        typ = "alert"
        parts.append(f"{_strong(failed_24h[0])} failed. Check logs.")
    elif jobs and all(str(j.get("health", "")).lower() in ok_health for j in jobs):
        parts.append(f"All {_strong(len(jobs))} cron jobs healthy.")

    seen_stale = set()
    for name, hours in stale:
        if name in seen_stale:
            continue
        seen_stale.add(name)
        hrs = int(hours) if hours >= 0 else 0
        parts.append(f"{_strong(name)} last ran {_strong(hrs)}h ago.")
        if typ != "alert":
            typ = "warning"
        if len(seen_stale) >= 3:
            break

    for name in amber_refresh_outside_window[:2]:
        parts.append(
            f"{_strong(name)} is idle outside the game window -- "
            f"refresh lines jobs only fire during game windows."
        )
        if typ == "insight":
            typ = "warning"

    pg = pipeline_games
    if pg is not None and _safe_int(pg) >= 0:
        dur = pipeline_duration
        if dur is not None:
            parts.append(
                f"Pipeline processed {_strong(_safe_int(pg))} games today "
                f"in {_strong(_pct_str(_safe_float(dur), 1))}s."
            )
        else:
            parts.append(f"Pipeline processed {_strong(_safe_int(pg))} games today.")

    # No failed jobs in 7d -- if we have metadata
    recent_failures = sum(
        1
        for j in jobs
        if str(j.get("health", "")).lower() in ("failed", "error", "down")
        and _safe_float(j.get("hours_ago"), 999) <= 24 * 7
    )
    if recent_failures == 0 and jobs and not failed_24h:
        parts.append("No failed jobs in the last 7 days.")

    text = " ".join(parts).strip()
    if not text:
        text = "No infra status available."
    return typ, "Infra Note", text


def revenue_read(funnel_data: Dict[str, Any], revenue: Dict[str, Any]) -> Tuple[TypeStr, str, str]:
    typ: TypeStr = "insight"
    fd = funnel_data or {}
    rev = revenue or {}

    tsu = _safe_int(fd.get("total_signups"))
    tpaid = _safe_int(fd.get("total_paid"))
    founding = _safe_int(fd.get("founding_count"))
    trial = _safe_int(fd.get("trial_count"))

    parts: List[str] = []

    if tsu > 0:
        rate = 100.0 * tpaid / tsu
        if rate > 15:
            parts.append(
                f"{_strong(_pct_str(rate))}% signup-to-paid conversion is strong for a cold launch."
            )
        elif rate >= 5:
            parts.append(
                f"{_strong(_pct_str(rate))}% signup-to-paid conversion. Room to improve."
            )
        else:
            parts.append(f"{_strong(_pct_str(rate))}% signup-to-paid is below target.")
            typ = "warning"

    if founding > trial and (founding or trial):
        tot = tpaid if tpaid else founding + trial
        parts.append(
            f"Founding Fifty price anchor is working -- {_strong(founding)} of {_strong(tot)} "
            f"paid users converted directly without trial."
        )

    if rev.get("mrr_flat") and rev.get("all_annual"):
        parts.append(
            "MRR flat because all members are annual. Next bump comes with next conversion."
        )
    elif "mrr" in rev or "arr" in rev:
        mrr = _safe_float(rev.get("mrr"))
        arr = _safe_float(rev.get("arr"))
        if "mrr" in rev and "arr" in rev:
            parts.append(
                f"MRR {_strong(_money_str(mrr))}, ARR {_strong(_money_str(arr))}."
            )
        elif "mrr" in rev:
            parts.append(f"MRR {_strong(_money_str(mrr))}.")
        elif "arr" in rev:
            parts.append(f"ARR {_strong(_money_str(arr))}.")

    text = " ".join(parts).strip()
    if not text:
        text = "Insufficient revenue funnel data."
    return typ, "Revenue Read", text


def _sessions_trend_down_days(sessions_by_day: Optional[List[Any]], min_days: int = 3) -> int:
    if not sessions_by_day or len(sessions_by_day) < min_days:
        return 0
    vals: List[float] = []
    for x in sessions_by_day:
        if isinstance(x, dict):
            vals.append(_safe_float(x.get("sessions") or x.get("count") or x.get("value")))
        else:
            vals.append(_safe_float(x))
    if len(vals) < min_days:
        return 0
    # check longest suffix of strict decrease
    n = len(vals)
    run = 1
    for i in range(n - 1, 0, -1):
        if vals[i] < vals[i - 1]:
            run += 1
        else:
            break
    return run if run >= min_days else 0


def engagement_read(eng_data: Dict[str, Any]) -> Tuple[TypeStr, str, str]:
    ed = eng_data or {}
    typ: TypeStr = "insight"
    parts: List[str] = []

    active = _safe_int(ed.get("active_users_7d"))
    total = _safe_int(ed.get("total_users"))
    spu = _safe_float(ed.get("avg_sessions_per_user"))

    ret = ed.get("retention") if isinstance(ed.get("retention"), dict) else {}
    d1 = _safe_float(ret.get("d1_rate_pct"))
    d7 = _safe_float(ret.get("d7_rate_pct"))
    d7_elig = _safe_int(ret.get("d7_eligible"))

    if total > 0:
        act_pct = 100.0 * active / total
        if act_pct < 30 or (bool(ret) and d1 < 40):
            typ = "warning"
        if act_pct < 25:
            parts.append(
                f"{_strong(active)} active users out of {_strong(total)} signups = "
                f"{_strong(_pct_str(act_pct))}% activation rate. That's the number to watch."
            )
        elif act_pct <= 50:
            parts.append(f"Activation at {_strong(_pct_str(act_pct))}%. Improving but not yet healthy.")
        else:
            parts.append(f"Activation at {_strong(_pct_str(act_pct))}%. Healthy.")

    if spu > 30:
        parts.append(
            f"Users who do engage are deeply engaged -- {_strong(_pct_str(spu, 1))} sessions per user."
        )

    if ret:
        if d1 < 45:
            parts.append(
                f"D1 at {_strong(_pct_str(d1))}% means more than half of new signups don't return "
                f"the next day. Onboarding may need work."
            )
        else:
            parts.append(
                f"D1 retention at {_strong(_pct_str(d1))}% -- acceptable for early stage."
            )

        tiny = ""
        if d7_elig < 5:
            tiny = f" -- but the sample is tiny ({_strong(d7_elig)})."

        if d7 > 60:
            parts.append(
                f"D7 retention at {_strong(_pct_str(d7))}% is excellent"
                + (tiny if tiny else ".")
            )
        elif d7 < 40:
            parts.append(
                f"D7 retention at {_strong(_pct_str(d7))}% is a red flag"
                + (tiny if tiny else ".")
            )
            typ = "alert"
        elif d7 > 0 or d7_elig > 0:
            parts.append(
                f"D7 retention at {_strong(_pct_str(d7))}%"
                + (tiny if tiny else ".")
            )

    down_n = _sessions_trend_down_days(ed.get("sessions_by_day"))
    if down_n >= 3:
        parts.append(f"Sessions trending down over the last {_strong(down_n)} days.")
        if typ == "insight":
            typ = "warning"

    text = " ".join(parts).strip()
    if not text:
        text = "Insufficient engagement data."
    return typ, "Engagement Read", text


_FEATURE_LABELS = {
    "view_article": "Journal",
    "view_market_scan": "Market Scan",
    "tap_bet_link": "Bet link taps",
}


def feature_note(
    feature_data: Dict[str, Any], active_users: int,
) -> Tuple[TypeStr, str, str]:
    typ: TypeStr = "insight"
    fd = feature_data or {}
    parts: List[str] = []

    def pct_of(entry: Any) -> float:
        if isinstance(entry, dict):
            return _safe_float(entry.get("pct_of_active"))
        return 0.0

    journal_pct = pct_of(fd.get("view_article"))
    scan_pct = pct_of(fd.get("view_market_scan"))
    bet_pct = pct_of(fd.get("tap_bet_link"))

    if journal_pct > scan_pct and (journal_pct or scan_pct):
        parts.append(
            f"Journal is the most-used feature at {_strong(_pct_str(journal_pct))}%, "
            f"outpacing the core signals product."
        )

    if bet_pct < 25 and active_users > 0:
        parts.append(
            f"Only {_strong(_pct_str(bet_pct))}% of active users are tapping through to place bets. "
            f"The gap between reading signals and acting on them may be a trust or UX issue."
        )
        typ = "warning"
    elif bet_pct > 40:
        parts.append(
            f"Bet link taps at {_strong(_pct_str(bet_pct))}% -- users are acting on signals."
        )

    for key, label in _FEATURE_LABELS.items():
        p = pct_of(fd.get(key))
        if 0 < p < 10:
            parts.append(f"{label} at {_strong(_pct_str(p))}% -- underutilized.")
            if typ == "insight":
                typ = "warning"

    text = " ".join(parts).strip()
    if not text:
        text = "No feature usage data."
    return typ, "Feature Note", text


# ---------------------------------------------------------------------------
# Email Verification
# ---------------------------------------------------------------------------

def verification_read(
    data: Dict[str, Any],
) -> Tuple[TypeStr, str, str]:
    total = _safe_int(data.get("total_users"), 1)
    unverified = _safe_int(data.get("unverified_count"))
    verified_pct = round((total - unverified) / max(total, 1) * 100, 0)
    unverified_pct = round(unverified / max(total, 1) * 100, 0)
    typ: TypeStr = "insight"
    parts: List[str] = []

    if unverified_pct > 30:
        typ = "warning"
        parts.append(
            f"Verification rate is low at {_strong(f'{verified_pct:.0f}%')}. "
            f"{_strong(unverified)} users haven't verified their email. "
            f"Consider a re-verification nudge email or in-app prompt."
        )
    elif unverified_pct > 15:
        parts.append(
            f"Verification at {_strong(f'{verified_pct:.0f}%')}. "
            f"{_strong(unverified)} unverified accounts."
        )
    else:
        parts.append(
            f"Email verification healthy at {_strong(f'{verified_pct:.0f}%')}."
        )

    spam_pattern = data.get("spam_pattern")
    if spam_pattern:
        parts.append(
            f"{_strong(spam_pattern['count'])} signups matching pattern "
            f"\"{spam_pattern['prefix']}\" look like bot/spam accounts. "
            f"Consider an IP-based signup rate limit or CAPTCHA."
        )
        if typ == "insight":
            typ = "warning"

    return typ, "Verification Read", " ".join(parts)


# ---------------------------------------------------------------------------
# Content Engine Performance
# ---------------------------------------------------------------------------

def content_engine_read(
    data: Dict[str, Any],
) -> Tuple[TypeStr, str, str]:
    views = _safe_int(data.get("total_views_7d"))
    top = data.get("top_page", "unknown")
    total_pages = _safe_int(data.get("total_pages"))
    typ: TypeStr = "insight"
    parts: List[str] = []

    if views > 500:
        parts.append(
            f"Content engine generating solid traffic at {_strong(views)} views/week. "
            f"Top page: {_strong(top)}."
        )
    elif views > 100:
        parts.append(
            f"Content engine warming up with {_strong(views)} views/week. "
            f"{_strong(top)} leading."
        )
    elif views > 0:
        parts.append(
            f"Content engine at {_strong(views)} views/week. "
            f"Early days -- SEO takes 4-8 weeks to compound."
        )
    else:
        parts.append("No content page views recorded yet. Tracking just started.")

    if total_pages:
        parts.append(f"{_strong(total_pages)} total content pages generated.")

    return typ, "Content Read", " ".join(parts)


# ---------------------------------------------------------------------------
# User Engagement (enhanced)
# ---------------------------------------------------------------------------

def user_engagement_read(
    data: Dict[str, Any],
) -> Tuple[TypeStr, str, str]:
    active = _safe_int(data.get("active_7d"))
    total = _safe_int(data.get("total_users"), 1)
    pct = round(active / max(total, 1) * 100, 0)
    power_users = _safe_int(data.get("power_user_count"))
    at_risk = _safe_int(data.get("at_risk_count"))
    bet_rate = _safe_float(data.get("bet_link_tap_rate"))

    typ: TypeStr = "insight"
    parts: List[str] = []

    parts.append(
        f"{_strong(active)} of {_strong(total)} users active in the last 7 days "
        f"({_strong(f'{pct:.0f}%')})."
    )
    if pct < 25:
        typ = "warning"

    if power_users > 0:
        parts.append(f"{_strong(power_users)} power users (10+ sessions/week).")

    if at_risk > 0:
        parts.append(
            f"{_strong(at_risk)} users at risk -- active last week but silent this week. "
            f"Consider a re-engagement push notification."
        )
        if typ == "insight":
            typ = "warning"

    if bet_rate < 10 and active > 0:
        parts.append(
            f"Bet Link Taps at {_strong(f'{bet_rate:.1f}%')} -- "
            f"users are reading signals but not acting on them. "
            f"Trust gap or UX friction."
        )

    return typ, "User Engagement Read", " ".join(parts)
