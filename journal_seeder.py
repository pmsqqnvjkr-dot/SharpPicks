"""Seed Sharp Journal articles from markdown files in content/journal/.

Each file is YAML-frontmatter + markdown body. Frontmatter fields map to
Insight model columns; the body is everything after the closing frontmatter
delimiter. Idempotent: existing rows are matched by slug and updated in
place, missing rows are inserted.

Called from seed_database() in app.py at startup so a Railway redeploy
picks up any new or edited articles without a manual seed run.

Content format (per docs/sharp-journal-spec.md):
  ---
  slug: <kebab-case>
  title: <Sentence case with period.>
  category: <Philosophy | How It Works | Market Notes | Discipline | Founder Note>
  content_tag: <Field Guide | How it works | Editorial>
  sport: <WNBA | NBA | MLB | NBA (Playoffs)>
  status: <published | scheduled>
  read_time: <N min>
  date: <YYYY-MM-DD>
  calibration_phase: <true | false>
  author: <Name>
  author_title: <Title>
  ---
  # Title (optional, skipped at render time)

  Article body in markdown with optional locked HTML constructs for
  sharp-principle / observation / why-matters / pull-quote / .stat spans.
"""
import os
import re
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Map frontmatter category strings to the DB enum used by Insight.category
# and the SharpJournalArticle component's CATEGORY_TAG lookup.
CATEGORY_MAP = {
    'philosophy': 'philosophy',
    'how it works': 'how_it_works',
    'how_it_works': 'how_it_works',
    'market notes': 'market_notes',
    'market_notes': 'market_notes',
    'discipline': 'discipline',
    'founder note': 'founder_note',
    'founder_note': 'founder_note',
    'editorial': 'editorial',
    'field guide': 'field_guide',
    'field_guide': 'field_guide',
}

SPORT_MAP = {
    'wnba': 'wnba',
    'nba': 'nba',
    'nba (playoffs)': 'nba',
    'mlb': 'mlb',
}


def _parse_frontmatter(raw):
    """Split a markdown file into (frontmatter_dict, body_str). Returns
    ({}, raw) if there's no recognizable frontmatter block."""
    if not raw.startswith('---'):
        return {}, raw
    # Find the closing --- on its own line.
    end_match = re.search(r'\n---\s*\n', raw)
    if not end_match:
        return {}, raw
    fm_block = raw[3:end_match.start()].strip()
    body = raw[end_match.end():].lstrip('\n')
    fm = {}
    for line in fm_block.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if ':' not in line:
            continue
        key, _, value = line.partition(':')
        key = key.strip()
        value = value.strip()
        # Strip surrounding quotes if present.
        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]
        fm[key] = value
    return fm, body


def _parse_read_time(value):
    """Accept '4 min', '4', '4 min read' etc. Returns int minutes, default 3."""
    if not value:
        return 3
    m = re.match(r'\s*(\d+)', str(value))
    return int(m.group(1)) if m else 3


def _parse_date(value):
    """Accept 'YYYY-MM-DD' or full ISO. Returns naive datetime at 10am ET-ish
    (stored UTC-naive to match the rest of the publish_date column). Falls
    back to today if unparseable."""
    if not value:
        return datetime.utcnow()
    try:
        if 'T' in value:
            return datetime.fromisoformat(value.replace('Z', '+00:00')).replace(tzinfo=None)
        # YYYY-MM-DD: anchor to mid-morning so ordering matches other rows.
        d = datetime.strptime(value, '%Y-%m-%d')
        return d.replace(hour=10, minute=0, second=0)
    except (ValueError, TypeError):
        return datetime.utcnow()


def seed_journal_articles_from_dir(content_dir, Insight, db):
    """Read every .md in content_dir, upsert into the insights table.

    Idempotent. Safe to call on every app boot. Logs warnings for files
    with missing required frontmatter so authors can fix them without
    looking at SQL.
    """
    if not os.path.isdir(content_dir):
        logger.info(f'Journal seeder: content dir {content_dir} not found, skipping')
        return 0

    count = 0
    for filename in sorted(os.listdir(content_dir)):
        if not filename.endswith('.md'):
            continue
        path = os.path.join(content_dir, filename)
        try:
            with open(path, 'r', encoding='utf-8') as fh:
                raw = fh.read()
        except Exception as e:
            logger.warning(f'Journal seeder: cannot read {filename}: {e}')
            continue

        fm, body = _parse_frontmatter(raw)
        slug = fm.get('slug') or filename[:-3]
        title = fm.get('title')
        if not title:
            logger.warning(f'Journal seeder: {filename} missing title, skipping')
            continue

        category = CATEGORY_MAP.get((fm.get('category') or '').strip().lower(), 'how_it_works')
        sport = SPORT_MAP.get((fm.get('sport') or '').strip().lower(), 'nba')
        status = (fm.get('status') or 'published').strip().lower()
        if status not in ('published', 'scheduled', 'draft'):
            status = 'published'
        reading_time = _parse_read_time(fm.get('read_time'))
        publish_date = _parse_date(fm.get('date'))
        excerpt = (fm.get('excerpt') or body.split('\n\n', 1)[0]).strip()
        if len(excerpt) > 500:
            excerpt = excerpt[:497] + '...'

        existing = Insight.query.filter_by(slug=slug).first()
        if existing:
            existing.title = title
            existing.category = category
            existing.sport = sport
            existing.status = status
            existing.reading_time_minutes = reading_time
            existing.publish_date = publish_date
            existing.excerpt = excerpt
            existing.content = body.strip()
        else:
            inst = Insight(
                title=title,
                slug=slug,
                category=category,
                sport=sport,
                status=status,
                reading_time_minutes=reading_time,
                publish_date=publish_date,
                excerpt=excerpt,
                content=body.strip(),
            )
            db.session.add(inst)
        count += 1
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f'Journal seeder commit failed: {e}')
        return 0
    logger.info(f'Journal seeder: upserted {count} article(s) from {content_dir}')
    return count
