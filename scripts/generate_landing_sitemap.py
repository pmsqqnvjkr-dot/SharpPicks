#!/usr/bin/env python3
"""Generate landing/sitemap.xml from the static apex pages.

Reads the landing/ directory tree to enumerate every page worth indexing:
- The hand-authored static pages at landing/<name>.html (homepage, guide,
  legal, support).
- Every Sharp Journal post at landing/blog/<slug>/index.html (both
  git-tracked and the build-time-generated ones from
  scripts/generate_missing_blog_posts.py if it has already run).
- The /llms.txt and /llms-full.txt citation files.

Skips:
- landing/blog/index.html (covered explicitly as /blog/).
- 404.html (don't index error pages).
- card-generator.html (internal dev tool).

The robots.txt already references the sitemap URL, so no extra wiring is
needed once this file lands on Cloudflare Pages.

Usage:
    python3 scripts/generate_landing_sitemap.py landing/
"""

from __future__ import annotations

import argparse
import datetime
import os
import sys
import xml.sax.saxutils

BASE = "https://sharppicks.ai"

# Per-URL priority + changefreq, by canonical path. Anything not listed
# falls back to a sensible default for its category.
EXPLICIT = {
    "/":                {"priority": "1.0", "changefreq": "daily"},
    "/guide.html":      {"priority": "0.9", "changefreq": "monthly"},
    "/blog/":           {"priority": "0.9", "changefreq": "daily"},
    "/support":         {"priority": "0.6", "changefreq": "monthly"},
    "/privacy.html":    {"priority": "0.3", "changefreq": "yearly"},
    "/terms.html":      {"priority": "0.3", "changefreq": "yearly"},
    "/disclaimer.html": {"priority": "0.3", "changefreq": "yearly"},
    "/llms.txt":        {"priority": "0.5", "changefreq": "weekly"},
    "/llms-full.txt":   {"priority": "0.5", "changefreq": "weekly"},
}
BLOG_POST_DEFAULTS = {"priority": "0.7", "changefreq": "monthly"}

# Files at landing/ root that are not human-facing pages.
ROOT_SKIP = {
    "index.html",            # canonicalized as "/"
    "404.html",              # error page
    "card-generator.html",   # internal dev tool
    "evan-chat-mockup.html", # internal mockup, not shipped IA
    "ios-screenshot-builder.html",  # internal tool
    "noedge-mockup.html",    # internal mockup
    "robots.txt",
    "sitemap.xml",           # don't index the sitemap itself
    "_headers",
    "_redirects",
}

# Notably MISSING from this list: support.html — it gets canonicalized
# to /support below. If a /support.html link survives in the wild it
# still serves (Pages 404 redirect path), but the canonical URL the
# rest of the site uses is the suffix-less one.


def iso_lastmod(path: str) -> str:
    try:
        ts = os.path.getmtime(path)
        return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
    except OSError:
        return datetime.date.today().strftime("%Y-%m-%d")


def enumerate_urls(landing_dir: str) -> list[dict]:
    """Returns a list of {loc, lastmod, priority, changefreq} dicts."""
    urls: list[dict] = []

    # 1. Homepage.
    home = os.path.join(landing_dir, "index.html")
    urls.append({
        "loc": f"{BASE}/",
        "lastmod": iso_lastmod(home),
        **EXPLICIT["/"],
    })

    # 2. Top-level .html and .txt pages.
    for name in sorted(os.listdir(landing_dir)):
        full = os.path.join(landing_dir, name)
        if not os.path.isfile(full):
            continue
        if name in ROOT_SKIP:
            continue
        if not (name.endswith(".html") or name.endswith(".txt")):
            continue
        canonical = f"/{name}"
        # /support is served from support.html but the canonical path
        # the rest of the site links to does NOT include the .html.
        # Other pages (.html files) keep the suffix.
        if name == "support.html":
            canonical = "/support"
        meta = EXPLICIT.get(canonical, {"priority": "0.5", "changefreq": "monthly"})
        urls.append({
            "loc": f"{BASE}{canonical}",
            "lastmod": iso_lastmod(full),
            **meta,
        })

    # 3. Journal index (/blog/) + every post directory.
    blog_dir = os.path.join(landing_dir, "blog")
    if os.path.isdir(blog_dir):
        blog_index = os.path.join(blog_dir, "index.html")
        if os.path.isfile(blog_index):
            urls.append({
                "loc": f"{BASE}/blog/",
                "lastmod": iso_lastmod(blog_index),
                **EXPLICIT["/blog/"],
            })
        for slug in sorted(os.listdir(blog_dir)):
            sub = os.path.join(blog_dir, slug)
            if not os.path.isdir(sub):
                continue
            post = os.path.join(sub, "index.html")
            if not os.path.isfile(post):
                continue
            urls.append({
                "loc": f"{BASE}/blog/{slug}/",
                "lastmod": iso_lastmod(post),
                **BLOG_POST_DEFAULTS,
            })

    return urls


def render_xml(urls: list[dict]) -> str:
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        loc = xml.sax.saxutils.escape(u["loc"])
        lines.append("  <url>")
        lines.append(f"    <loc>{loc}</loc>")
        lines.append(f"    <lastmod>{u['lastmod']}</lastmod>")
        lines.append(f"    <changefreq>{u['changefreq']}</changefreq>")
        lines.append(f"    <priority>{u['priority']}</priority>")
        lines.append("  </url>")
    lines.append("</urlset>")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("landing_dir", help="Path to the landing/ directory")
    args = ap.parse_args()

    if not os.path.isdir(args.landing_dir):
        print(f"generate_landing_sitemap: not a directory: {args.landing_dir}", file=sys.stderr)
        return 1

    urls = enumerate_urls(args.landing_dir)
    xml_body = render_xml(urls)
    out_path = os.path.join(args.landing_dir, "sitemap.xml")
    with open(out_path, "w") as f:
        f.write(xml_body)
    print(f"generate_landing_sitemap: wrote {out_path} ({len(urls)} urls)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
