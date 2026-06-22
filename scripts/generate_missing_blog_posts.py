"""Generate static HTML for published Insight rows that don't already
exist as static blog posts under landing/blog/<slug>/.

KNOWN ARCHITECTURAL DEBT (flag this when re-discovered):
Sharp Journal has TWO parallel content stores:
  1. Static HTML at landing/blog/<slug>/index.html (committed, served
     by Cloudflare Pages at sharppicks.ai)
  2. Insight rows in Postgres (status='published'), served by the React
     app at app.sharppicks.ai

Each blog post should ideally live in one place. Right now ~32 slugs
are committed as static HTML while ~10 others live ONLY in the DB,
which means Google indexes URLs like /blog/<db-only-slug>/ that 404
into the homepage SPA fallback. This script is the temporary bridge:
generate-on-deploy fills the missing static files from DB content so
both surfaces stay in sync. The proper long-term fix is to pick ONE
content store and migrate the other, which is bigger work.

Usage:
  python3 scripts/generate_missing_blog_posts.py [--target DIR] [--all]

  --target DIR: output dir (default landing/blog). The script ONLY
                writes to slugs that don't already have a directory.
  --all:        regenerate every published slug, overwriting existing
                static files. Default is missing-only.

Output: writes index.html files. Does NOT commit anything; the deploy
wrapper (scripts/deploy_landing.sh) calls this then runs
`git clean -fd landing/blog/` after deploy to remove generated files.
"""
import os
import re
import sys
import argparse
import html
from datetime import datetime

# Stand-up Flask app context so we can query the Insight model. Reuses
# the app's existing DB config and SQLAlchemy session rather than
# duplicating connection plumbing.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


CATEGORY_LABELS = {
    'philosophy': 'Philosophy',
    'discipline': 'Discipline',
    'how_it_works': 'How It Works',
    'market_notes': 'Market Notes',
    'beginners_guide': 'Beginner\'s Guide',
}

MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
         'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


def md_to_html(md):
    """Minimal markdown to HTML for journal articles. Handles paragraphs,
    headings (h1-h3), horizontal rule, bold, italic, and links. The
    journal authors hand-write in this restricted dialect so the
    converter doesn't need to be exhaustive."""
    if not md:
        return ''
    text = md.replace('\r\n', '\n').strip()

    def inline(s):
        # Links [text](url) before bold/italic to avoid mangling
        s = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', s)
        # Bold ** before italic *
        s = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', s)
        s = re.sub(r'(?<!\*)\*([^*\n]+)\*(?!\*)', r'<em>\1</em>', s)
        return s

    blocks = re.split(r'\n\s*\n', text)
    out = []
    for raw in blocks:
        block = raw.strip()
        if not block:
            continue
        # Horizontal rule
        if re.fullmatch(r'-{3,}', block):
            out.append('<hr>')
            continue
        # Heading
        m = re.match(r'^(#{1,3})\s+(.+)', block)
        if m:
            level = len(m.group(1))
            out.append(f'<h{level}>{inline(html.escape(m.group(2)))}</h{level}>')
            continue
        # Blockquote (treat each line)
        if block.startswith('>'):
            lines = [line.lstrip('>').strip() for line in block.splitlines()]
            inner = ' '.join(inline(html.escape(line)) for line in lines if line)
            out.append(f'<blockquote><p>{inner}</p></blockquote>')
            continue
        # Default: paragraph. Preserve inline newlines as spaces.
        paragraph = ' '.join(line.strip() for line in block.splitlines())
        out.append(f'<p>{inline(html.escape(paragraph))}</p>')
    return '\n'.join(out)


def fmt_publish_date(dt):
    """Mar 14, 2026"""
    if not dt:
        return ''
    return f'{MONTHS[dt.month - 1]} {dt.day}, {dt.year}'


def fmt_iso_offset(dt):
    """2026-02-01T12:00:00-04:00 for article:published_time."""
    if not dt:
        return ''
    return dt.strftime('%Y-%m-%dT%H:%M:%S') + '-04:00'


def fmt_iso_date(dt):
    """2026-02-01 for JSON-LD datePublished."""
    if not dt:
        return ''
    return dt.strftime('%Y-%m-%d')


TEMPLATE_PATH = os.path.join(ROOT, 'landing', 'blog', 'the-sharp-manifesto', 'index.html')


def load_template():
    """Read the manifesto post and emit a template string with
    __TOKEN__ placeholders. We use distinctive tokens (not Python's
    str.format mini-language) because the template HTML embeds JSON-LD
    which contains literal { and } that would otherwise need escaping.
    Substituted via plain str.replace at render time."""
    with open(TEMPLATE_PATH, 'r', encoding='utf-8') as fh:
        tpl = fh.read()

    subs = [
        ('The Sharp Manifesto · Sharp Journal | SharpPicks', '__TITLE__ · Sharp Journal | SharpPicks'),
        ('content="When I started building SharpPicks, I wasn&#39;t trying to create another betting app. The market already has plenty of those."', 'content="__DESCRIPTION__"'),
        ('"description": "When I started building SharpPicks, I wasn&#39;t trying to create another betting app. The market already has plenty of those."', '"description": "__DESCRIPTION_JSON__"'),
        ('https://sharppicks.ai/blog/the-sharp-manifesto/', 'https://sharppicks.ai/blog/__SLUG__/'),
        ('content="The Sharp Manifesto"', 'content="__TITLE__"'),
        ('"headline": "The Sharp Manifesto"', '"headline": "__TITLE_JSON__"'),
        ('content="2026-02-01T12:00:00-04:00"', 'content="__PUBLISHED_ISO_OFFSET__"'),
        ('"datePublished": "2026-02-01"', '"datePublished": "__PUBLISHED_ISO_DATE__"'),
        ('"dateModified": "2026-04-02"', '"dateModified": "__MODIFIED_ISO_DATE__"'),
        ('<span class="cat-tag">Philosophy</span>', '<span class="cat-tag">__CATEGORY_LABEL__</span>'),
        ('<span class="hero-line">Sharp Journal &middot; 2 min read</span>', '<span class="hero-line">Sharp Journal &middot; __READING_TIME__ min read</span>'),
        ('<h1>The Sharp Manifesto</h1>', '<h1>__TITLE__</h1>'),
        ('<p class="hero-date">Feb 1, 2026</p>', '<p class="hero-date">__PUBLISH_DATE_STR__</p>'),
    ]
    for old, new in subs:
        if old not in tpl:
            raise RuntimeError(f'Template substitution failed: pattern not found: {old[:60]}...')
        # No count argument: og:title + twitter:title (and og:url +
        # canonical + JSON-LD @id) repeat the same content string. Need
        # replace-all so every meta-tag instance gets templated.
        tpl = tpl.replace(old, new)

    # Swap the entire <article class="article-body">...</article> body
    # for a single __ARTICLE_HTML__ token. Safest to splice on opening
    # and closing tag positions rather than regex over the markup.
    article_open = '<article class="article-body">'
    article_close = '</article>'
    start = tpl.index(article_open) + len(article_open)
    end = tpl.index(article_close, start)
    tpl = tpl[:start] + '\n__ARTICLE_HTML__\n  ' + tpl[end:]

    return tpl


def slug_to_url_safe(slug):
    return slug


def make_excerpt_for_meta(excerpt):
    """Strip newlines + collapse whitespace. HTML escape for meta safety."""
    one_line = ' '.join((excerpt or '').split()).strip()
    return html.escape(one_line, quote=True)


def render(insight, template):
    pub = insight.publish_date
    mod = insight.updated_at or pub
    category_label = CATEGORY_LABELS.get((insight.category or '').lower(), (insight.category or '').title())
    rt = int(insight.reading_time_minutes or 3)
    excerpt_meta = make_excerpt_for_meta(insight.excerpt or '')
    # Description in JSON-LD has to escape backslashes and quotes (JSON
    # string rules). Other meta tags use HTML escape only.
    desc_json = excerpt_meta.replace('\\', '\\\\').replace('"', '\\"')
    title_json = html.escape(insight.title or '', quote=True).replace('\\', '\\\\').replace('"', '\\"')

    body_html = md_to_html(insight.content)

    replacements = [
        ('__TITLE__', html.escape(insight.title or '', quote=True)),
        ('__TITLE_JSON__', title_json),
        ('__SLUG__', insight.slug),
        ('__DESCRIPTION__', excerpt_meta),
        ('__DESCRIPTION_JSON__', desc_json),
        ('__PUBLISHED_ISO_OFFSET__', fmt_iso_offset(pub)),
        ('__PUBLISHED_ISO_DATE__', fmt_iso_date(pub)),
        ('__MODIFIED_ISO_DATE__', fmt_iso_date(mod)),
        ('__CATEGORY_LABEL__', html.escape(category_label, quote=True)),
        ('__READING_TIME__', str(rt)),
        ('__PUBLISH_DATE_STR__', fmt_publish_date(pub)),
        ('__ARTICLE_HTML__', body_html),
    ]
    out = template
    for token, value in replacements:
        out = out.replace(token, value)
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', default=os.path.join(ROOT, 'landing', 'blog'),
                        help='Output directory (default landing/blog)')
    parser.add_argument('--all', action='store_true',
                        help='Regenerate every published slug, overwriting existing')
    args = parser.parse_args()

    from app import app
    from models import Insight

    template = load_template()
    written = []
    skipped = []
    with app.app_context():
        # Match the runtime visibility rule from insights_api._visible_filter:
        # published OR (scheduled AND publish_date <= now). Without the
        # scheduled branch, scheduled-for-today articles would be served
        # by the API but absent from the static landing/blog/<slug>/ tree.
        from datetime import datetime as _dt
        now_naive = _dt.utcnow()
        from sqlalchemy import or_, and_
        rows = Insight.query.filter(
            or_(
                Insight.status == 'published',
                and_(Insight.status == 'scheduled', Insight.publish_date <= now_naive),
            )
        ).all()
        for ins in rows:
            slug = ins.slug
            # Skip daily market-note dailies. They live in the SPA, not
            # in the indexable static-blog surface. Dozens of date-stamped
            # near-duplicate pages would dilute Google's index for the
            # evergreen articles we actually want to rank.
            if slug.startswith('market-note-'):
                continue
            dest_dir = os.path.join(args.target, slug)
            dest_file = os.path.join(dest_dir, 'index.html')
            already_exists = os.path.exists(dest_file)
            if already_exists and not args.all:
                skipped.append(slug)
                continue
            os.makedirs(dest_dir, exist_ok=True)
            try:
                rendered = render(ins, template)
            except Exception as e:
                print(f'  FAIL {slug}: {e}', file=sys.stderr)
                continue
            with open(dest_file, 'w', encoding='utf-8') as fh:
                fh.write(rendered)
            written.append(slug)

    print(f'Generated {len(written)} static post(s) in {args.target}')
    for s in written:
        print(f'  + {s}')
    if skipped:
        print(f'Skipped {len(skipped)} (already had static file; pass --all to overwrite)')


if __name__ == '__main__':
    main()
