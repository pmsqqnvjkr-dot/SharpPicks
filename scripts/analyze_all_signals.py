"""
Compare published-pick record vs all-signals record.

Fetches picks + model_runs from the production admin API,
parses games_detail to find every game the model flagged as a signal,
grades each against final scores fetched from ESPN,
and prints a side-by-side comparison.
"""

import json
import os
import sys
import time
import requests
from collections import defaultdict

PROD_URL = "https://app.sharppicks.ai/api/admin/export-picks"
ESPN_NBA = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
ESPN_MLB = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard"


def _get_cron_secret():
    secret = os.environ.get("CRON_SECRET", "")
    if not secret:
        dotenv = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
        if os.path.exists(dotenv):
            for line in open(dotenv):
                line = line.strip()
                if line.startswith("CRON_SECRET="):
                    secret = line.split("=", 1)[1].strip()
                    break
    return secret


def fetch_export():
    cron_secret = _get_cron_secret()
    if not cron_secret:
        print("ERROR: CRON_SECRET not found in env or .env")
        sys.exit(1)

    print(f"Fetching data from {PROD_URL} ...")
    resp = requests.get(PROD_URL, headers={"X-Cron-Secret": cron_secret}, timeout=60)
    if resp.status_code != 200:
        print(f"ERROR: API returned {resp.status_code}")
        sys.exit(1)
    return resp.json()


ESPN_TEAM_MAP = {
    "la clippers": "los angeles clippers",
    "la lakers": "los angeles lakers",
}


def normalize_team(name):
    if not name:
        return ""
    n = name.strip().lower()
    return ESPN_TEAM_MAP.get(n, n)


def fetch_espn_scores(dates, sport="nba"):
    """Fetch final scores from ESPN for a set of dates. Returns {(date, home, away): (h_score, a_score)}."""
    base_url = ESPN_NBA if sport == "nba" else ESPN_MLB
    scores = {}
    dates_sorted = sorted(dates)
    print(f"  Fetching ESPN {sport.upper()} scores for {len(dates_sorted)} dates ...")

    for date_str in dates_sorted:
        url = f"{base_url}?dates={date_str.replace('-', '')}"
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code != 200:
                continue
            data = resp.json()
            events = data.get("events", [])
            for ev in events:
                comps = ev.get("competitions", [{}])
                if not comps:
                    continue
                comp = comps[0]
                status = comp.get("status", {}).get("type", {}).get("name", "")
                if status != "STATUS_FINAL":
                    continue
                competitors = comp.get("competitors", [])
                if len(competitors) < 2:
                    continue
                home_c = next((c for c in competitors if c.get("homeAway") == "home"), None)
                away_c = next((c for c in competitors if c.get("homeAway") == "away"), None)
                if not home_c or not away_c:
                    continue
                home_name = normalize_team(home_c.get("team", {}).get("displayName", ""))
                away_name = normalize_team(away_c.get("team", {}).get("displayName", ""))
                home_score = int(home_c.get("score", 0))
                away_score = int(away_c.get("score", 0))
                key = (date_str, home_name, away_name)
                scores[key] = (home_score, away_score)
        except Exception as e:
            print(f"    Warning: ESPN fetch failed for {date_str}: {e}")
        time.sleep(0.15)

    print(f"  Loaded {len(scores)} final scores from ESPN")
    return scores


def grade_ats(pick_side, line, home_score, away_score):
    """Return 'W', 'L', or 'P' for an ATS pick."""
    spread_result = home_score - away_score
    if pick_side == "home":
        ats_margin = spread_result + line
    else:
        ats_margin = -spread_result + line

    if ats_margin == 0:
        return "P"
    elif ats_margin > 0:
        return "W"
    else:
        return "L"


def pnl_for_result(result, odds=-110):
    if result == "W":
        return 100 / abs(odds) if odds < 0 else odds / 100
    elif result == "L":
        return -1.0
    return 0.0


def analyze(data):
    picks = data.get("picks", [])
    runs = data.get("model_runs", [])

    # Collect all dates and sports that have signals
    signal_dates_by_sport = defaultdict(set)
    for r in runs:
        detail_raw = r.get("games_detail")
        if not detail_raw:
            continue
        try:
            detail = json.loads(detail_raw) if isinstance(detail_raw, str) else detail_raw
        except (json.JSONDecodeError, TypeError):
            continue
        for g in detail:
            if g.get("passes"):
                signal_dates_by_sport[r.get("sport", "nba")].add(r["date"])

    # Fetch ESPN scores for all needed dates
    all_scores = {}
    for sport, dates in signal_dates_by_sport.items():
        scores = fetch_espn_scores(dates, sport)
        all_scores.update(scores)

    # Also add scores from graded picks (as fallback)
    for p in picks:
        if p.get("home_score") is not None and p.get("away_score") is not None:
            key = (p["game_date"], normalize_team(p.get("home_team", "")), normalize_team(p.get("away_team", "")))
            if key not in all_scores:
                all_scores[key] = (p["home_score"], p["away_score"])

    # --- Published picks record ---
    pub_results = {"W": 0, "L": 0, "P": 0, "pending": 0, "revoked": 0}
    pub_pnl = 0.0
    pub_by_sport = defaultdict(lambda: {"W": 0, "L": 0, "P": 0})

    for p in picks:
        result = p.get("result", "pending")
        sport = p.get("sport", "nba")
        if result == "revoked":
            pub_results["revoked"] += 1
            continue
        ats = p.get("result_ats")
        if ats in ("W", "L", "P"):
            pub_results[ats] += 1
            pub_by_sport[sport][ats] += 1
            pub_pnl += pnl_for_result(ats, p.get("market_odds", -110) or -110)
        else:
            pub_results["pending"] += 1

    # --- All signals record (from games_detail) ---
    all_results = {"W": 0, "L": 0, "P": 0, "no_score": 0}
    all_pnl = 0.0
    all_by_sport = defaultdict(lambda: {"W": 0, "L": 0, "P": 0})
    unpub_results = {"W": 0, "L": 0, "P": 0, "no_score": 0}
    unpub_pnl = 0.0
    signal_details = []

    for r in runs:
        detail_raw = r.get("games_detail")
        if not detail_raw:
            continue
        try:
            detail = json.loads(detail_raw) if isinstance(detail_raw, str) else detail_raw
        except (json.JSONDecodeError, TypeError):
            continue

        run_date = r.get("date", "")
        sport = r.get("sport", "nba")

        # Find the published pick for this date+sport by matching team names
        day_picks = [p for p in picks if p.get("game_date") == run_date
                     and p.get("sport", "nba") == sport
                     and p.get("result") != "revoked"]
        pub_games = set()
        for p in day_picks:
            pub_games.add((normalize_team(p.get("home_team", "")),
                           normalize_team(p.get("away_team", ""))))

        for g in detail:
            if not g.get("passes"):
                continue

            home = normalize_team(g.get("home", g.get("home_team", "")))
            away = normalize_team(g.get("away", g.get("away_team", "")))
            pick_side = g.get("pick_side", "")
            line = g.get("line", 0) or 0
            edge = g.get("edge", 0) or 0

            score_key = (run_date, home, away)
            score = all_scores.get(score_key)
            if not score:
                score_key_alt = (run_date, away, home)
                score_alt = all_scores.get(score_key_alt)
                if score_alt:
                    score = (score_alt[1], score_alt[0])

            is_published = (home, away) in pub_games

            if not score:
                all_results["no_score"] += 1
                if not is_published:
                    unpub_results["no_score"] += 1
                continue

            home_score, away_score = score
            result = grade_ats(pick_side, line, home_score, away_score)

            all_results[result] += 1
            all_by_sport[sport][result] += 1
            all_pnl += pnl_for_result(result)

            pick_team = home if pick_side == "home" else away
            signal_details.append({
                "date": run_date, "sport": sport, "pick": pick_team.title(),
                "line": line, "edge": edge, "result": result,
                "score": f"{away_score}-{home_score}" if pick_side == "home" else f"{home_score}-{away_score}",
                "published": is_published,
            })

            if not is_published:
                unpub_results[result] += 1
                unpub_pnl += pnl_for_result(result)

    # --- Print results ---
    print("\n" + "=" * 65)
    print("  SHARPPICKS — ALL-SIGNALS RECORD ANALYSIS")
    print("=" * 65)

    def print_record(label, rec, pnl_val=None):
        w, l, p = rec.get("W", 0), rec.get("L", 0), rec.get("P", 0)
        total = w + l + p
        wr = (w / (w + l) * 100) if (w + l) > 0 else 0
        roi = (pnl_val / total * 100) if total > 0 and pnl_val is not None else 0
        print(f"\n  {label}")
        print(f"  {'─' * 50}")
        print(f"  Record:    {w}-{l}-{p}  ({total} graded)")
        print(f"  Win Rate:  {wr:.1f}%")
        if pnl_val is not None:
            print(f"  PnL:       {pnl_val:+.2f}u")
            print(f"  ROI:       {roi:+.1f}%")

    print_record("PUBLISHED PICKS ONLY (signal of the day)", pub_results, pub_pnl)
    if pub_results.get("pending"):
        print(f"  Pending:   {pub_results['pending']}")
    if pub_results.get("revoked"):
        print(f"  Revoked:   {pub_results['revoked']}")

    print_record("ALL SIGNALS (every game model flagged)", all_results, all_pnl)
    if all_results.get("no_score"):
        print(f"  No score:  {all_results['no_score']} (today/future/not found)")

    print_record("UNPUBLISHED SIGNALS ONLY (qualified but not top pick)", unpub_results, unpub_pnl)
    if unpub_results.get("no_score"):
        print(f"  No score:  {unpub_results['no_score']}")

    # Sport breakdown
    all_sports = sorted(set(list(pub_by_sport.keys()) + list(all_by_sport.keys())))
    if len(all_sports) > 1:
        print(f"\n  BY SPORT")
        print(f"  {'─' * 50}")
        for sport in all_sports:
            pr = pub_by_sport.get(sport, {"W": 0, "L": 0, "P": 0})
            ar = all_by_sport.get(sport, {"W": 0, "L": 0, "P": 0})
            pw, pl = pr.get("W", 0), pr.get("L", 0)
            aw, al = ar.get("W", 0), ar.get("L", 0)
            pwr = (pw / (pw + pl) * 100) if (pw + pl) > 0 else 0
            awr = (aw / (aw + al) * 100) if (aw + al) > 0 else 0
            print(f"  {sport.upper():5s}  Published: {pw}-{pl}-{pr.get('P',0)} ({pwr:.0f}%)   "
                  f"All Signals: {aw}-{al}-{ar.get('P',0)} ({awr:.0f}%)")

    # Detail log
    if signal_details:
        print(f"\n  SIGNAL-BY-SIGNAL LOG")
        print(f"  {'─' * 50}")
        print(f"  {'Date':<12} {'Pick':<22} {'Line':>6} {'Edge':>6} {'Result':>6} {'Pub?'}")
        print(f"  {'─'*12} {'─'*22} {'─'*6} {'─'*6} {'─'*6} {'─'*4}")
        for s in sorted(signal_details, key=lambda x: x["date"]):
            pub_mark = " *" if s["published"] else ""
            print(f"  {s['date']:<12} {s['pick']:<22} {s['line']:>+6.1f} {s['edge']:>+5.1f}% {s['result']:>6}{pub_mark}")

    # Verdict
    pub_w, pub_l = pub_results.get("W", 0), pub_results.get("L", 0)
    all_w, all_l = all_results.get("W", 0), all_results.get("L", 0)
    pub_wr = (pub_w / (pub_w + pub_l) * 100) if (pub_w + pub_l) > 0 else 0
    all_wr = (all_w / (all_w + all_l) * 100) if (all_w + all_l) > 0 else 0

    print(f"\n  {'=' * 50}")
    if all_wr > pub_wr:
        diff = all_wr - pub_wr
        print(f"  VERDICT: All-signals record is BETTER")
        print(f"           {all_wr:.1f}% vs {pub_wr:.1f}% (+{diff:.1f}pp)")
    elif all_wr < pub_wr:
        diff = pub_wr - all_wr
        print(f"  VERDICT: Published-only record is BETTER")
        print(f"           {pub_wr:.1f}% vs {all_wr:.1f}% (+{diff:.1f}pp)")
    else:
        print(f"  VERDICT: Records are EQUAL ({pub_wr:.1f}%)")
    print(f"  {'=' * 50}\n")


if __name__ == "__main__":
    data = fetch_export()
    analyze(data)
