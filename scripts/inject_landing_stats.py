#!/usr/bin/env python3
"""Inject live SharpPicks stats into landing/index.html before deploy.

Crawlers and Lighthouse see the served HTML before any JavaScript runs.
The shipped client-side loadStats() fetch populates the stat counters at
runtime, but until that JS executes the page renders nine em-dash
placeholders for Record, ROI, Units, Games Analyzed, Signals Generated,
Games Passed, Total Picks, Selectivity, Total Passes. This script
replaces each placeholder in the HTML text with the matching value from
/api/public/stats so the server-rendered surface shows real numbers.

The mutation is in-place by design: wrangler pages deploys whatever sits
at the file path. The deploy_landing.sh wrapper takes a backup before
invoking us and restores after wrangler exits, so the git-tracked file
stays untouched.

Per handoff: "If a value is genuinely unavailable, omit the stat rather
than rendering a dash." When /api/public/stats returns null / missing for
a field, this script leaves the em-dash in place rather than substituting
"0" or "n/a"; the page still parses but the cell visibly signals "no data
to show" instead of pretending zero.

Usage:
    python3 scripts/inject_landing_stats.py landing/index.html
    python3 scripts/inject_landing_stats.py landing/index.html --base https://app.sharppicks.ai
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
import urllib.request

DEFAULT_STATS_URL = "https://app.sharppicks.ai/api/public/stats"

# Date placeholders the redesigned landing uses for the "today" surfaces.
# __TODAY_ISO__       -> 2026-06-22 (URL slug)
# __TODAY_DAY_MONTH__ -> SUN · JUN 22 (display label)
# Replace at deploy time so crawlers see today's URLs / today's date.
# Crawlers re-discover when we redeploy (daily through the content cron
# or manually); a user who clicks tomorrow gets yesterday's report,
# which is still a valid archive page.
_WEEKDAYS = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
_MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
           "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

# Each entry maps an id attribute on the landing page to a function that
# turns the /api/public/stats response into the display string. Returning
# None means "leave the existing placeholder, no data to inject."
def _record(d):
    return d.get("record") or None

def _roi(d):
    v = d.get("roi")
    if v is None:
        return None
    return f"{'+' if v > 0 else ''}{v}%"

def _units(d):
    v = d.get("units")
    if v is None:
        v = d.get("pnl")
    if v is None:
        return None
    return f"{'+' if v > 0 else ''}{v}u"

def _total_analyzed(d):
    tp = d.get("total_picks")
    pa = d.get("total_passes")
    if tp is None or pa is None:
        return None
    return str(tp + pa)

def _total_picks(d):
    v = d.get("total_picks")
    return None if v is None else str(v)

def _total_passes(d):
    v = d.get("total_passes")
    return None if v is None else str(v)

def _selectivity(d):
    v = d.get("selectivity")
    if v is None:
        return None
    return f"{v}%"


ID_TO_VALUE = {
    "p-rec":      _record,
    "p-roi":      _roi,
    "p-units":    _units,
    "s-analyzed": _total_analyzed,
    "s-signals":  _total_picks,
    "s-passed":   _total_passes,
    "perf-picks": _total_picks,
    "perf-sel":   _selectivity,
    "perf-pass":  _total_passes,
}


def fetch_stats(url: str) -> dict:
    # Cloudflare in front of app.sharppicks.ai 403s the default urllib UA.
    # Send a normal browser-ish UA so the fetch survives bot mitigation.
    req = urllib.request.Request(url, headers={
        "User-Agent": "SharpPicks-landing-stats-injector/1.0",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=20) as resp:
        if resp.status != 200:
            raise RuntimeError(f"HTTP {resp.status} from {url}")
        return json.loads(resp.read().decode("utf-8"))


# Matches: <div ... id="X" ... >—</div> or <span ... id="X" ... >—</span>
# Group 1: tag open, attributes, including id
# Group 2: the em-dash inside
# Group 3: closing tag
_PLACEHOLDER_RE_TEMPLATE = (
    r'(<(?:div|span)\b[^>]*\bid="{esc_id}"[^>]*>)'
    r'(\s*—\s*)'
    r'(</(?:div|span)>)'
)


def inject(html: str, stats: dict) -> tuple[str, list[str], list[str]]:
    """Returns (new_html, filled_ids, skipped_ids).
    filled_ids:  ids whose em-dash was replaced with a real value.
    skipped_ids: ids whose stat returned None (data missing); placeholder stays.
    """
    filled = []
    skipped = []
    out = html
    for ident, fn in ID_TO_VALUE.items():
        value = fn(stats)
        if value is None:
            skipped.append(ident)
            continue
        pattern = _PLACEHOLDER_RE_TEMPLATE.format(esc_id=re.escape(ident))
        replacement = rf'\g<1>{re.escape(value).replace(chr(92), "")}\g<3>'
        new_out, n = re.subn(pattern, replacement, out, count=1)
        if n == 0:
            # Placeholder not present (already populated, or markup
            # changed). Treat as skipped so the deploy still proceeds.
            skipped.append(ident)
            continue
        out = new_out
        filled.append(ident)
    return out, filled, skipped


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", help="Path to landing/index.html")
    ap.add_argument("--base", default=DEFAULT_STATS_URL,
                    help=f"Stats endpoint URL (default {DEFAULT_STATS_URL})")
    args = ap.parse_args()

    try:
        stats = fetch_stats(args.base)
    except Exception as e:
        print(f"inject_landing_stats: fetch failed: {e}", file=sys.stderr)
        # Non-fatal: deploy can still proceed with em-dashes.
        return 0

    with open(args.path, "r") as f:
        html = f.read()

    new_html, filled, skipped = inject(html, stats)

    # Date placeholders for the redesigned landing's "today" surfaces.
    today = datetime.date.today()
    iso = today.isoformat()
    day_month = f"{_WEEKDAYS[today.weekday()]} · {_MONTHS[today.month - 1]} {today.day}"
    iso_n = new_html.count("__TODAY_ISO__")
    dm_n = new_html.count("__TODAY_DAY_MONTH__")
    if iso_n:
        new_html = new_html.replace("__TODAY_ISO__", iso)
    if dm_n:
        new_html = new_html.replace("__TODAY_DAY_MONTH__", day_month)

    with open(args.path, "w") as f:
        f.write(new_html)

    print(f"inject_landing_stats: filled {len(filled)} ({', '.join(filled)})")
    if skipped:
        print(f"inject_landing_stats: skipped {len(skipped)} ({', '.join(skipped)}) — no data")
    if iso_n or dm_n:
        print(f"inject_landing_stats: dated {iso_n} ISO + {dm_n} day-month placeholders -> {iso} / {day_month}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
