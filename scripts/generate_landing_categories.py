#!/usr/bin/env python3
"""Generate /blog/category/<slug>/index.html hub pages for the Sharp Journal.

The journal index at landing/blog/index.html ships a row of category-filter
chips that work via client-side JS. Crawlers do not run the JS, so the
filtered states have no server-rendered representation. This script
materializes one static HTML page per category so each category has a
crawlable hub URL (linked from the handoff's redesigned mockup) and the
articles in that category are all reachable within two clicks of the
homepage (home -> category -> article).

URL <-> DB category mapping (URL slugs from the handoff mockup):
    /blog/category/philosophy   -> insights.category = 'philosophy'
    /blog/category/how-it-works -> insights.category = 'how_it_works'
    /blog/category/market-reads -> insights.category = 'market_notes'
    /blog/category/discipline   -> insights.category = 'discipline'
    /blog/category/founder-notes-> insights.category = 'founder_note'

For each category we emit:
- A custom <title> + meta description.
- og:* + twitter:* tags pointing at the category URL.
- A schema.org BreadcrumbList JSON-LD pointing back to /blog/.
- A schema.org ItemList JSON-LD enumerating every article in the category.
- A simple list of article cards, sorted by published_at desc.

Style: the page mirrors landing/blog/index.html's layout via inlined
styles so it ships without depending on an external stylesheet.

Usage:
    python3 scripts/generate_landing_categories.py \\
        --landing landing --db "$DATABASE_URL"
"""

from __future__ import annotations

import argparse
import datetime
import html
import json
import os
import sys


CATEGORY_DEFS = [
    {
        "slug":       "philosophy",
        "db_key":     "philosophy",
        "title":      "Philosophy",
        "meta_desc":  "Philosophy notes from the Sharp Journal. Why we pass more than we play, why volume destroys edge, why the work between games is the work.",
        "intro":      "Why we pass more than we play. Why volume destroys edge. The work between games is the work.",
        "tag_class":  "cat-ph",
    },
    {
        "slug":       "how-it-works",
        "db_key":     "how_it_works",
        "title":      "How It Works",
        "meta_desc":  "How the SharpPicks model works. Edge detection, the four-model ensemble, market intelligence, and calibration.",
        "intro":      "Edge detection, the four-model ensemble, market intelligence, and calibration. Everything that happens between the lines and your phone.",
        "tag_class":  "cat-hw",
    },
    {
        "slug":       "market-reads",
        "db_key":     "market_notes",
        "title":      "Market Reads",
        "meta_desc":  "Daily market reads from SharpPicks. What we found on the board, where the edge was, why we passed.",
        "intro":      "What we found on the board today. Where the edge was. Why we passed.",
        "tag_class":  "cat-mr",
    },
    {
        "slug":       "discipline",
        "db_key":     "discipline",
        "title":      "Discipline",
        "meta_desc":  "Discipline notes from the Sharp Journal. Losing streaks, sample size, and the math of staying patient through variance.",
        "intro":      "Losing streaks. Sample size. The math of staying patient when the data points the right way and the scoreboard does not.",
        "tag_class":  "cat-di",
    },
    {
        "slug":       "founder-notes",
        "db_key":     "founder_note",
        "title":      "Founder Notes",
        "meta_desc":  "Founder notes from SharpPicks. Operating decisions, model thinking, and behind the scenes.",
        "intro":      "Operating notes. Model thinking. Behind the scenes from the founder.",
        "tag_class":  "cat-fn",
    },
]


PAGE_TMPL = """<!DOCTYPE html>
<html lang="en" style="background:#0c1018;color-scheme:dark">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="color-scheme" content="dark">
<meta name="theme-color" content="#0c1018">
<title>{title} - Sharp Journal | SharpPicks</title>
<meta name="description" content="{meta_desc}">
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="website">
<meta property="og:url" content="{canonical}">
<meta property="og:title" content="{title} - Sharp Journal | SharpPicks">
<meta property="og:description" content="{meta_desc}">
<meta property="og:site_name" content="SharpPicks">
<meta property="og:image" content="https://sharppicks.ai/og-image.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:site" content="@SharpPicksApp">
<meta name="twitter:title" content="{title} - Sharp Journal | SharpPicks">
<meta name="twitter:description" content="{meta_desc}">
<meta name="twitter:image" content="https://sharppicks.ai/og-image.png">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Serif:wght@400;500;600&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root{{--bg:#0c1018;--card:#111827;--bdr:#1e2a3a;--bdr2:#2a3654;--t1:#e8eaf0;--t2:#9098b3;--t3:#616a8a;--t4:#4a5274;--grn:#5A9E72;--sf:'IBM Plex Serif',Georgia,serif;--sn:'Inter',-apple-system,sans-serif;--mn:'JetBrains Mono','Menlo',monospace}}
*{{margin:0;padding:0;box-sizing:border-box}}
html{{scroll-behavior:smooth;background:#0c1018 !important}}
body{{font-family:var(--sn);background:#0c1018 !important;color:#e8eaf0;-webkit-font-smoothing:antialiased}}
nav{{position:fixed;top:0;left:0;right:0;z-index:100;background:rgba(12,16,24,.92);backdrop-filter:blur(24px);border-bottom:1px solid var(--bdr);height:56px;display:flex;align-items:center;justify-content:space-between;padding:0 clamp(16px,4vw,48px)}}
.logo{{font-family:var(--mn);font-weight:500;letter-spacing:.2em;color:#fff;text-decoration:none;font-size:14px}}
.logo span{{color:var(--grn)}}
.nav-c{{display:flex;gap:20px;align-items:center}}
.nav-c a{{font-family:var(--mn);font-size:11px;letter-spacing:.04em;color:var(--t2);text-decoration:none;transition:color .2s}}
.nav-c a:hover{{color:var(--t1)}}
.nav-r{{display:flex;gap:8px;align-items:center}}
@media(max-width:680px){{nav{{flex-wrap:wrap;height:auto;min-height:56px;padding-bottom:0}}.nav-c{{order:3;width:100%;padding:8px 0 10px;gap:16px;overflow-x:auto}}}}
.b{{font-family:var(--mn);font-size:11px;letter-spacing:.04em;padding:8px 18px;border-radius:6px;text-decoration:none;cursor:pointer;border:none;display:inline-block}}
.b.gh{{color:var(--t2);background:none;border:1px solid var(--bdr)}}
.b.gh:hover{{color:var(--t1);border-color:var(--bdr2)}}
.b.gr{{color:#fff;background:var(--grn)}}
.wrap{{max-width:760px;margin:0 auto;padding:96px 24px 80px}}
.crumbs{{font-family:var(--mn);font-size:11px;letter-spacing:.08em;color:var(--t3);margin-bottom:18px}}
.crumbs a{{color:var(--t2);text-decoration:none}}
.crumbs a:hover{{color:var(--t1)}}
.crumbs .sep{{color:var(--t4);margin:0 8px}}
.page-hdr{{margin-bottom:32px}}
.page-label{{font-family:var(--mn);font-size:11px;letter-spacing:.18em;color:var(--grn);margin-bottom:14px;text-transform:uppercase}}
.page-title{{font-family:var(--sf);font-size:clamp(28px,5vw,42px);font-weight:500;line-height:1.15;margin-bottom:14px}}
.page-sub{{font-size:15px;line-height:1.65;color:var(--t2)}}
.list-hdr{{font-family:var(--mn);font-size:11px;letter-spacing:.18em;color:var(--t3);margin:32px 0 16px;text-transform:uppercase}}
.article-row{{display:block;padding:18px 0;border-top:1px solid var(--bdr);text-decoration:none;color:inherit}}
.article-row:hover{{background:rgba(255,255,255,.02)}}
.row-top{{display:flex;align-items:center;gap:10px;margin-bottom:8px}}
.cat-tag{{font-family:var(--mn);font-size:10px;letter-spacing:.12em;padding:2px 8px;border-radius:4px;background:var(--card);color:var(--t2)}}
.cat-tag.cat-ph{{background:rgba(143,163,194,.12);color:#8FA3C2}}
.cat-tag.cat-hw{{background:rgba(79,134,247,.12);color:#4F86F7}}
.cat-tag.cat-mr{{background:rgba(90,158,114,.10);color:var(--grn)}}
.cat-tag.cat-di{{background:rgba(196,134,138,.12);color:#C4868A}}
.cat-tag.cat-fn{{background:rgba(201,163,92,.12);color:#C9A35C}}
.cat-time{{font-family:var(--mn);font-size:10.5px;color:var(--t3)}}
.row-title{{font-family:var(--sf);font-size:18px;font-weight:500;line-height:1.35;margin-bottom:6px}}
.row-ex{{font-size:13.5px;color:var(--t2);line-height:1.6;margin-bottom:8px}}
.row-foot{{font-family:var(--mn);font-size:10.5px;letter-spacing:.04em;color:var(--t3)}}
.empty{{padding:48px 0;text-align:center;color:var(--t3);font-size:14px}}
.cta-box{{margin-top:48px;padding:28px;background:var(--card);border:1px solid var(--bdr);border-radius:12px;text-align:center}}
.cta-title{{font-family:var(--sf);font-size:22px;font-weight:500;margin-bottom:10px}}
.cta-body{{font-size:14px;color:var(--t2);line-height:1.6;margin-bottom:18px;max-width:520px;margin-left:auto;margin-right:auto}}
.cta-btn{{display:inline-block;font-family:var(--mn);font-size:13px;letter-spacing:.04em;color:#fff;background:var(--grn);border:none;padding:14px 36px;border-radius:8px;text-decoration:none}}
footer{{border-top:1px solid var(--bdr);padding:40px 24px;text-align:center;font-size:12px;color:var(--t3)}}
footer a{{color:var(--t2);text-decoration:none;margin:0 12px}}
footer a:hover{{color:var(--t1)}}
</style>
</head>
<body>
<nav>
  <a href="/" class="logo">SHARP<span> || </span>PICKS</a>
  <div class="nav-c">
    <a href="/edges/nba-today">NBA Edges</a>
    <a href="/edges/mlb-today">MLB Edges</a>
    <a href="/tools/clv-calculator">CLV Calculator</a>
    <a href="/tools/edge-calculator">Edge Calculator</a>
  </div>
  <div class="nav-r">
    <a href="https://app.sharppicks.ai/login" class="b gh">Sign In</a>
    <a href="https://app.sharppicks.ai/signup?plan=annual" class="b gr">Start Free Trial</a>
  </div>
</nav>

<div class="wrap">
  <div class="crumbs">
    <a href="/">Home</a><span class="sep">/</span>
    <a href="/blog/">Sharp Journal</a><span class="sep">/</span>
    <span>{title}</span>
  </div>

  <div class="page-hdr">
    <div class="page-label">Category</div>
    <h1 class="page-title">{title}</h1>
    <p class="page-sub">{intro}</p>
  </div>

  <div class="list-hdr">{count} {count_word}</div>

  {articles_html}

  <div class="cta-box">
    <div class="cta-title">See signals in real time.</div>
    <div class="cta-body">Create a free account and watch the model work. Upgrade to Pro for full signal details, bet tracking, and discipline scoring.</div>
    <a class="cta-btn" href="https://app.sharppicks.ai/signup?plan=annual">Start Free Trial</a>
  </div>
</div>

<footer>
  <a href="/">Home</a>
  <a href="/blog/">Sharp Journal</a>
  <a href="/privacy.html">Privacy</a>
  <a href="/terms.html">Terms</a>
  <a href="/disclaimer.html">Disclaimer</a>
</footer>

<script type="application/ld+json">
{breadcrumb_jsonld}
</script>
<script type="application/ld+json">
{itemlist_jsonld}
</script>
</body>
</html>
"""


ARTICLE_ROW_TMPL = """  <a class="article-row" href="/blog/{slug}/">
    <div class="row-top">
      <span class="cat-tag {tag_class}">{cat_short}</span>
      <span class="cat-time">{read_minutes} min</span>
    </div>
    <div class="row-title">{title_html}</div>
    <div class="row-ex">{excerpt_html}</div>
    <div class="row-foot">{published_str} &middot; {author}</div>
  </a>"""

EMPTY_TMPL = """  <div class="empty">No articles in this category yet.</div>"""


CAT_SHORT = {
    "philosophy":   "PH",
    "how_it_works": "HW",
    "market_notes": "MR",
    "discipline":   "DI",
    "founder_note": "FN",
}


def short_for(db_key: str) -> str:
    return CAT_SHORT.get(db_key, db_key[:2].upper())


def fmt_date(d) -> str:
    """Render a python date/datetime as 'Mar 31, 2026'."""
    if d is None:
        return ""
    if isinstance(d, str):
        try:
            d = datetime.date.fromisoformat(d[:10])
        except ValueError:
            return d
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return f"{months[d.month - 1]} {d.day}, {d.year}"


def excerpt_from_content(content: str, max_chars: int = 200) -> str:
    if not content:
        return ""
    para = content.split("\n\n", 1)[0]
    para = para.strip().replace("\n", " ")
    if len(para) > max_chars:
        para = para[: max_chars].rsplit(" ", 1)[0] + "..."
    return para


def fetch_articles_by_category(db_url: str, db_key: str) -> list[dict]:
    """Return rows ordered by published_at desc for one DB category."""
    import psycopg2
    import psycopg2.extras
    conn = psycopg2.connect(db_url)
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT slug, title, content, excerpt, reading_time_minutes,
                       category, publish_date AS published_at, created_at
                  FROM insights
                 WHERE status = 'published'
                   AND category = %s
                   AND slug IS NOT NULL AND slug <> ''
                 ORDER BY COALESCE(publish_date, created_at) DESC
                """,
                (db_key,),
            )
            return list(cur.fetchall())
    finally:
        conn.close()


def render_article_row(row: dict, tag_class: str) -> str:
    slug = row.get("slug") or ""
    title = (row.get("title") or "").strip()
    excerpt = (row.get("excerpt") or "").strip()
    if not excerpt:
        excerpt = excerpt_from_content(row.get("content") or "")
    read_minutes = row.get("reading_time_minutes") or 4
    pub = row.get("published_at") or row.get("created_at")
    return ARTICLE_ROW_TMPL.format(
        slug=slug,
        tag_class=tag_class,
        cat_short=short_for(row.get("category") or ""),
        read_minutes=read_minutes,
        title_html=html.escape(title),
        excerpt_html=html.escape(excerpt),
        published_str=html.escape(fmt_date(pub)),
        author="Evan Cole",
    )


def render_breadcrumb_jsonld(category_title: str, canonical: str) -> str:
    data = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": "https://sharppicks.ai/"},
            {"@type": "ListItem", "position": 2, "name": "Sharp Journal", "item": "https://sharppicks.ai/blog/"},
            {"@type": "ListItem", "position": 3, "name": category_title, "item": canonical},
        ],
    }
    return json.dumps(data, indent=2)


def render_itemlist_jsonld(category_title: str, canonical: str, rows: list[dict]) -> str:
    items = []
    for i, row in enumerate(rows, start=1):
        slug = row.get("slug") or ""
        title = (row.get("title") or "").strip()
        if not slug or not title:
            continue
        items.append({
            "@type": "ListItem",
            "position": i,
            "url": f"https://sharppicks.ai/blog/{slug}/",
            "name": title,
        })
    data = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": f"Sharp Journal: {category_title}",
        "url": canonical,
        "itemListElement": items,
    }
    return json.dumps(data, indent=2)


def render_category_page(cat: dict, rows: list[dict]) -> str:
    canonical = f"https://sharppicks.ai/blog/category/{cat['slug']}/"
    if rows:
        articles_html = "\n".join(render_article_row(r, cat["tag_class"]) for r in rows)
    else:
        articles_html = EMPTY_TMPL

    n = len(rows)
    count_word = "article" if n == 1 else "articles"

    return PAGE_TMPL.format(
        title=html.escape(cat["title"]),
        meta_desc=html.escape(cat["meta_desc"]),
        intro=html.escape(cat["intro"]),
        canonical=canonical,
        count=n,
        count_word=count_word,
        articles_html=articles_html,
        breadcrumb_jsonld=render_breadcrumb_jsonld(cat["title"], canonical),
        itemlist_jsonld=render_itemlist_jsonld(cat["title"], canonical, rows),
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--landing", default="landing", help="Path to landing/ root")
    ap.add_argument("--db", default=None,
                    help="Postgres URL (defaults to env SQLALCHEMY_DATABASE_URI or DATABASE_URL)")
    args = ap.parse_args()

    db_url = args.db or os.environ.get("SQLALCHEMY_DATABASE_URI") or os.environ.get("DATABASE_URL")
    if not db_url:
        print("generate_landing_categories: DB URL required", file=sys.stderr)
        return 1

    out_root = os.path.join(args.landing, "blog", "category")
    os.makedirs(out_root, exist_ok=True)

    total = 0
    for cat in CATEGORY_DEFS:
        rows = fetch_articles_by_category(db_url, cat["db_key"])
        page = render_category_page(cat, rows)
        cat_dir = os.path.join(out_root, cat["slug"])
        os.makedirs(cat_dir, exist_ok=True)
        out_path = os.path.join(cat_dir, "index.html")
        with open(out_path, "w") as f:
            f.write(page)
        print(f"generate_landing_categories: {cat['slug']:14} {len(rows):4d} articles -> {out_path}")
        total += len(rows)

    print(f"generate_landing_categories: total {total} article links across {len(CATEGORY_DEFS)} categories")
    return 0


if __name__ == "__main__":
    sys.exit(main())
