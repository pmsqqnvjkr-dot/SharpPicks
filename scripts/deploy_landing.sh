#!/usr/bin/env bash
#
# Deploy the sharppicks.ai landing site to Cloudflare Pages.
#
# 1. Generates static HTML for every published Insight that doesn't
#    already exist under landing/blog/<slug>/.
# 2. Runs wrangler pages deploy.
# 3. Cleans the generated files (untracked-only via git clean -fd).
#
# Generated blog posts are NEVER committed. The script bridges the
# current architectural debt where some Sharp Journal posts live in
# Postgres only while others are committed as static HTML; the proper
# long-term fix is to consolidate. See scripts/generate_missing_blog_posts.py
# for the full context.
#
# Required env vars (read from the Railway production project for the
# canonical Insight rows):
#   SQLALCHEMY_DATABASE_URI   prod Postgres connection string
#
# Optional env vars:
#   CLOUDFLARE_API_TOKEN      if set, used by wrangler non-interactively
#
# Usage:
#   ./scripts/deploy_landing.sh
#

set -euo pipefail

cd "$(dirname "$0")/.."
ROOT="$(pwd)"

if [ -z "${SQLALCHEMY_DATABASE_URI:-}" ]; then
  echo "ERROR: SQLALCHEMY_DATABASE_URI must be set (prod Postgres URL)." >&2
  exit 1
fi

# Snapshot the tracked state of landing/blog before generating so we
# can confidently clean up afterwards. git clean -fd removes only
# untracked files / directories, which is what we want, but the
# snapshot is belt-and-suspenders against accidental commits.
TRACKED_SLUGS=$(git -C "$ROOT" ls-files landing/blog | awk -F/ '{print $3}' | sort -u)
echo "Tracked static slugs in git: $(echo "$TRACKED_SLUGS" | wc -l | tr -d ' ')"

echo
echo "==> Generating missing blog posts from DB..."
python3 scripts/generate_missing_blog_posts.py --target landing/blog

echo
echo "==> Snapshotting tracked landing/index.html..."
# Crawlers + Lighthouse see the served HTML before any JS runs. The
# shipped loadStats() handles browsers but cannot help bots, so we
# pre-render the nine stat counters AND the Sharp Journal ItemList
# JSON-LD at deploy time. Backup the tracked file first; restore after
# wrangler exits so the git-tracked file stays clean regardless of
# whether the deploy succeeded.
STATS_BACKUP="$(mktemp -t landing-index.XXXXXX)"
trap 'cp "$STATS_BACKUP" "$ROOT/landing/index.html" 2>/dev/null; rm -f "$STATS_BACKUP"; rm -f "$ROOT/landing/sitemap.xml" 2>/dev/null' EXIT
cp "$ROOT/landing/index.html" "$STATS_BACKUP"

echo
echo "==> Injecting live stats into landing/index.html..."
python3 scripts/inject_landing_stats.py landing/index.html

echo
echo "==> Injecting Sharp Journal ItemList JSON-LD..."
python3 scripts/inject_landing_jsonld.py landing/index.html

echo
echo "==> Generating landing/sitemap.xml..."
python3 scripts/generate_landing_sitemap.py landing

echo
echo "==> Deploying to Cloudflare Pages..."
# Clear CLOUDFLARE_API_TOKEN for the wrangler invocation only. If it's
# set in the shell (e.g. via .zshrc) with IP allowlist restrictions,
# wrangler picks it up and hits code 9109 / 10000 errors. Empty value
# tells wrangler to fall back to cached OAuth credentials in
# ~/.wrangler/config/default.toml (set up via `npx wrangler login`).
CLOUDFLARE_API_TOKEN= npx wrangler pages deploy landing --project-name sharppicks --commit-dirty=true --branch main

echo
echo "==> Restoring git-tracked landing/index.html + removing generated sitemap..."
cp "$STATS_BACKUP" "$ROOT/landing/index.html"
rm -f "$STATS_BACKUP"
rm -f "$ROOT/landing/sitemap.xml"
trap - EXIT

echo
echo "==> Cleaning generated (untracked) blog posts..."
# -f force, -d directories. ONLY removes untracked files; tracked
# static posts and other tracked files are untouched.
git -C "$ROOT" clean -fd landing/blog

echo
echo "Done. Tracked landing/blog/ slugs after cleanup:"
git -C "$ROOT" ls-files landing/blog | awk -F/ '{print $3}' | sort -u | wc -l | tr -d ' '
