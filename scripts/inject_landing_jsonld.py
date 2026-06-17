#!/usr/bin/env python3
"""Inject a Sharp Journal ItemList into landing/index.html before deploy.

The handoff requires server-rendered structured data with "an ItemList of
recent Journal articles generated from real data, not hardcoded." The HTML
ships a placeholder ld+json block:

    <script type="application/ld+json" id="ld-journal-itemlist">
    {... "itemListElement": [] ...}
    </script>

This script fetches /api/insights, takes the most recent N, and rewrites
that one block with a real itemListElement array (Position + ListItem +
url). All other JSON-LD on the page (SoftwareApplication, Organization,
WebSite) is static and not touched here.

In-place mutation, same backup/restore pattern as inject_landing_stats.py
(deploy_landing.sh handles the snapshot).

Usage:
    python3 scripts/inject_landing_jsonld.py landing/index.html
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request

DEFAULT_API = "https://app.sharppicks.ai/api/insights?limit=8&rotate=1"
JOURNAL_BASE = "https://sharppicks.ai/blog"
DEFAULT_MAX = 8


def fetch_insights(url: str) -> list[dict]:
    req = urllib.request.Request(url, headers={
        "User-Agent": "SharpPicks-landing-jsonld-injector/1.0",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=20) as resp:
        if resp.status != 200:
            raise RuntimeError(f"HTTP {resp.status} from {url}")
        body = json.loads(resp.read().decode("utf-8"))
    return body.get("insights") or []


def build_itemlist(insights: list[dict], limit: int) -> dict:
    """Return a schema.org ItemList dict populated with up to `limit`
    article entries. Each entry is a ListItem pointing at the article's
    canonical /blog/<slug>/ URL. Insights with no slug are skipped.
    """
    items = []
    pos = 1
    for raw in insights:
        slug = (raw.get("slug") or "").strip()
        title = (raw.get("title") or "").strip()
        if not slug or not title:
            continue
        items.append({
            "@type": "ListItem",
            "position": pos,
            "url": f"{JOURNAL_BASE}/{slug}/",
            "name": title,
        })
        pos += 1
        if pos > limit:
            break
    return {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": "Sharp Journal recent articles",
        "url": f"{JOURNAL_BASE}/",
        "itemListElement": items,
    }


_BLOCK_RE = re.compile(
    r'(<script\s+type="application/ld\+json"\s+id="ld-journal-itemlist">)'
    r'.*?'
    r'(</script>)',
    re.DOTALL,
)


def inject(html: str, itemlist: dict) -> tuple[str, int]:
    pretty = json.dumps(itemlist, indent=2)
    new_html, n = _BLOCK_RE.subn(
        lambda m: f"{m.group(1)}\n{pretty}\n{m.group(2)}",
        html,
        count=1,
    )
    return new_html, n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", help="Path to landing/index.html")
    ap.add_argument("--api", default=DEFAULT_API,
                    help=f"Insights endpoint URL (default {DEFAULT_API})")
    ap.add_argument("--limit", type=int, default=DEFAULT_MAX,
                    help=f"Max items in the ItemList (default {DEFAULT_MAX})")
    args = ap.parse_args()

    try:
        insights = fetch_insights(args.api)
    except Exception as e:
        print(f"inject_landing_jsonld: fetch failed: {e}", file=sys.stderr)
        # Non-fatal: deploy can still proceed with the empty placeholder.
        return 0

    itemlist = build_itemlist(insights, args.limit)
    if not itemlist["itemListElement"]:
        print("inject_landing_jsonld: no items produced, leaving placeholder", file=sys.stderr)
        return 0

    with open(args.path, "r") as f:
        html = f.read()
    new_html, n = inject(html, itemlist)
    if n == 0:
        print("inject_landing_jsonld: placeholder block not found", file=sys.stderr)
        return 0
    with open(args.path, "w") as f:
        f.write(new_html)
    print(f"inject_landing_jsonld: filled ItemList with {len(itemlist['itemListElement'])} articles")
    return 0


if __name__ == "__main__":
    sys.exit(main())
