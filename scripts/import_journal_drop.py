#!/usr/bin/env python3
"""Import a Sharp Journal markdown drop into the insights table.

Reads a directory of .md files plus a CATALOG_*.md index. Each article
has YAML-ish frontmatter; the catalog supplies the curated excerpt
string for each slug. Upserts by slug so re-running is idempotent.

Usage:
    python3 scripts/import_journal_drop.py /path/to/drop_dir [--apply]

Without --apply, runs as a dry run and prints what WOULD insert/update.

Frontmatter -> Insight column mapping:
    slug                -> slug (primary identifier; idempotent key)
    title               -> title
    category            -> category (normalized: "Founder Note" -> founder_note)
    sport               -> sport (lowercased: NBA -> nba)
    status              -> status (scheduled | published | draft)
    date                -> publish_date (parsed as YYYY-MM-DD midnight UTC)
    read_time           -> reading_time_minutes (parsed "5 min" -> 5)
    [content body]      -> content
    [catalog excerpt]   -> excerpt
    author_title etc.   -> ignored (not stored on Insight)

NFL articles imported with status='scheduled' + future publish_date stay
double-gated: the insights_api _visible_filter excludes them until their
date arrives, and the public_api is_sport_publicly_visible('nfl') gate
keeps them invisible via ?sport=nfl until launch_config flips.
"""

from __future__ import annotations

import argparse
import datetime
import os
import re
import sys
import uuid


# DB key map for incoming display-cased categories.
CATEGORY_MAP = {
    "founder note":    "founder_note",
    "how it works":    "how_it_works",
    "market notes":    "market_notes",
    "philosophy":      "philosophy",
    "discipline":      "discipline",
}

VALID_SPORTS = {"nba", "mlb", "wnba", "nfl"}


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Return (frontmatter_dict, body_str). Frontmatter is between the
    first two '---' lines at the top of the file."""
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    fm_raw = parts[1].strip()
    body = parts[2].lstrip("\n")
    fm = {}
    for line in fm_raw.splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        k, _, v = line.partition(":")
        fm[k.strip().lower()] = v.strip()
    return fm, body


def parse_excerpts_from_catalog(catalog_path: str) -> dict[str, str]:
    """Parse the catalog's slug -> excerpt mapping."""
    if not os.path.isfile(catalog_path):
        return {}
    with open(catalog_path, "r") as f:
        text = f.read()
    # Each article block contains:
    #   - **Slug:** `the-slug`
    #     ... other fields ...
    #   - **Excerpt:** prose
    slugs = {}
    blocks = re.split(r"^### \d+\.", text, flags=re.MULTILINE)
    for b in blocks:
        m_slug = re.search(r"\*\*Slug:\*\*\s*`([^`]+)`", b)
        m_ex = re.search(r"\*\*Excerpt:\*\*\s*(.+?)(?=\n\n|\n###|\n---|$)", b, flags=re.DOTALL)
        if m_slug and m_ex:
            slugs[m_slug.group(1).strip()] = m_ex.group(1).strip()
    return slugs


def parse_read_minutes(raw: str | None, default: int = 4) -> int:
    if not raw:
        return default
    m = re.search(r"\d+", str(raw))
    if not m:
        return default
    return int(m.group(0))


def parse_publish_date(raw: str | None) -> datetime.datetime | None:
    if not raw:
        return None
    # Accept "2026-06-22" or "2026-06-22T00:00:00" forms.
    s = raw.strip()
    try:
        return datetime.datetime.fromisoformat(s)
    except ValueError:
        pass
    try:
        d = datetime.date.fromisoformat(s[:10])
        return datetime.datetime(d.year, d.month, d.day, 9, 0, 0)
    except ValueError:
        return None


def normalize_category(raw: str) -> str:
    if not raw:
        return "philosophy"
    return CATEGORY_MAP.get(raw.strip().lower(), raw.strip().lower().replace(" ", "_"))


def first_paragraph(body: str, max_chars: int = 240) -> str:
    """Excerpt fallback: strip h1, take first non-empty paragraph."""
    lines = body.splitlines()
    para_lines = []
    for line in lines:
        if line.startswith("#"):
            continue
        if not line.strip():
            if para_lines:
                break
            continue
        para_lines.append(line.strip())
    para = " ".join(para_lines)
    if len(para) > max_chars:
        para = para[:max_chars].rsplit(" ", 1)[0] + "..."
    return para


def build_row(md_path: str, catalog_excerpts: dict) -> dict:
    with open(md_path, "r") as f:
        text = f.read()
    fm, body = parse_frontmatter(text)
    slug = fm.get("slug") or os.path.splitext(os.path.basename(md_path))[0]
    title = fm.get("title", "").rstrip(".") or slug.replace("-", " ").title()
    category = normalize_category(fm.get("category", ""))
    sport_raw = (fm.get("sport") or "nba").strip().lower()
    sport = sport_raw if sport_raw in VALID_SPORTS else "nba"
    status = (fm.get("status") or "scheduled").strip().lower()
    if status not in ("scheduled", "published", "draft"):
        status = "scheduled"
    publish_date = parse_publish_date(fm.get("date"))
    read_minutes = parse_read_minutes(fm.get("read_time"))
    excerpt = (catalog_excerpts.get(slug) or first_paragraph(body)).strip()
    return {
        "slug": slug,
        "title": title.strip(),
        "category": category,
        "sport": sport,
        "status": status,
        "publish_date": publish_date,
        "reading_time_minutes": read_minutes,
        "excerpt": excerpt,
        "content": body.strip(),
        "_path": md_path,
    }


def fetch_existing_slugs(conn, slugs: list[str]) -> dict[str, dict]:
    if not slugs:
        return {}
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, slug, title, category, sport, status, publish_date, "
            "reading_time_minutes, length(content) AS content_len "
            "FROM insights WHERE slug = ANY(%s)",
            (slugs,),
        )
        cols = [c[0] for c in cur.description]
        return {r[1]: dict(zip(cols, r)) for r in cur.fetchall()}


def insert_row(conn, row: dict) -> None:
    insight_id = str(uuid.uuid4())
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO insights
                (id, slug, title, category, sport, status, publish_date,
                 reading_time_minutes, excerpt, content, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            """,
            (insight_id, row["slug"], row["title"], row["category"],
             row["sport"], row["status"], row["publish_date"],
             row["reading_time_minutes"], row["excerpt"], row["content"]),
        )


def update_row(conn, row: dict) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE insights SET
                title = %s,
                category = %s,
                sport = %s,
                status = %s,
                publish_date = %s,
                reading_time_minutes = %s,
                excerpt = %s,
                content = %s,
                updated_at = NOW()
             WHERE slug = %s
            """,
            (row["title"], row["category"], row["sport"], row["status"],
             row["publish_date"], row["reading_time_minutes"],
             row["excerpt"], row["content"], row["slug"]),
        )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("drop_dir", help="Directory of .md files + CATALOG_*.md")
    ap.add_argument("--apply", action="store_true",
                    help="Actually write to DB. Without this, runs as a dry-run.")
    ap.add_argument("--db", default=None,
                    help="Postgres URL (default: env DATABASE_URL)")
    args = ap.parse_args()

    if not os.path.isdir(args.drop_dir):
        print(f"import_journal_drop: not a directory: {args.drop_dir}", file=sys.stderr)
        return 1

    db_url = args.db or os.environ.get("DATABASE_URL") or os.environ.get("SQLALCHEMY_DATABASE_URI")
    if not db_url:
        print("import_journal_drop: DATABASE_URL required", file=sys.stderr)
        return 1

    # Catalog excerpts (any file matching CATALOG_*.md).
    catalog_excerpts = {}
    for name in os.listdir(args.drop_dir):
        if name.startswith("CATALOG_") and name.endswith(".md"):
            cat_path = os.path.join(args.drop_dir, name)
            catalog_excerpts.update(parse_excerpts_from_catalog(cat_path))
    print(f"catalog excerpts parsed: {len(catalog_excerpts)} slugs")

    md_files = sorted(
        os.path.join(args.drop_dir, n) for n in os.listdir(args.drop_dir)
        if n.endswith(".md") and not n.startswith("CATALOG_")
    )
    rows = [build_row(p, catalog_excerpts) for p in md_files]
    print(f"markdown articles found: {len(rows)}")
    print()

    import psycopg2
    conn = psycopg2.connect(db_url)
    try:
        existing = fetch_existing_slugs(conn, [r["slug"] for r in rows])

        new_rows = [r for r in rows if r["slug"] not in existing]
        update_rows = [r for r in rows if r["slug"] in existing]

        print(f"=== NEW INSERTS ({len(new_rows)}) ===")
        for r in new_rows:
            d = r["publish_date"]
            d_str = d.strftime("%Y-%m-%d") if d else "—"
            print(f"  + {r['slug']:55} {r['sport']:5} {r['category']:14} "
                  f"{r['status']:10} {d_str}  ({r['reading_time_minutes']}min, "
                  f"{len(r['content'])} content chars)")
        print()
        print(f"=== UPDATES ({len(update_rows)}) ===")
        for r in update_rows:
            e = existing[r["slug"]]
            changes = []
            if e["title"] != r["title"]:
                changes.append(f"title")
            if e["category"] != r["category"]:
                changes.append(f"category {e['category']}->{r['category']}")
            if e["sport"] != r["sport"]:
                changes.append(f"sport {e['sport']}->{r['sport']}")
            if e["status"] != r["status"]:
                changes.append(f"status {e['status']}->{r['status']}")
            ed = e["publish_date"]
            if (ed and ed.date() if ed else None) != (r["publish_date"].date() if r["publish_date"] else None):
                changes.append(f"date")
            change_str = ", ".join(changes) if changes else "no meta change"
            print(f"  ~ {r['slug']:55} {change_str}")
        print()

        if not args.apply:
            print("dry run only; rerun with --apply to write")
            return 0

        for r in new_rows:
            insert_row(conn, r)
            print(f"  inserted: {r['slug']}")
        for r in update_rows:
            update_row(conn, r)
            print(f"  updated:  {r['slug']}")
        conn.commit()
        print()
        print(f"committed: {len(new_rows)} inserted, {len(update_rows)} updated")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
