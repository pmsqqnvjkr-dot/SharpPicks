"""
Comprehensive article audit fix:
1. Clean em dashes from all article content and excerpts
2. Publish 5 draft MLB articles with proper Tue/Fri 10 AM ET calendar
3. Fix mlb-shadow-mode sport tag (nba → mlb)
4. Fix market-note N/A title
5. Backfill missing story_type values
"""
from datetime import datetime
from zoneinfo import ZoneInfo
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ET = ZoneInfo('America/New_York')


def et_date(year, month, day, hour=10):
    return datetime(year, month, day, hour, 0, 0, tzinfo=ET).replace(tzinfo=None)


# Schedule the 5 draft MLB articles on Tue/Fri after the main 6 end (May 1)
DRAFT_MLB_SCHEDULE = {
    'why-mlb-is-a-quant-market':                et_date(2026, 5, 5),    # Tue
    'why-sharp-bettors-focus-on-price':          et_date(2026, 5, 8),    # Fri
    'the-problem-with-betting-big-favorites':    et_date(2026, 5, 12),   # Tue
    'why-bullpen-fatigue-creates-hidden-value':  et_date(2026, 5, 15),   # Fri
    'what-makes-an-mlb-moneyline-mispriced':     et_date(2026, 5, 19),   # Tue
}

# Map categories → story_type for articles missing it
CATEGORY_TO_STORY_TYPE = {
    'philosophy': 'philosophy',
    'how_it_works': 'how_it_works',
    'market_notes': 'market_notes',
    'discipline': 'discipline',
    'founder_note': 'founder_note',
}


def clean_em_dashes(text):
    if not text:
        return text, False
    # Replace em dash with colon or hyphen depending on context
    import re
    original = text
    # " — " → " - " (surrounded by spaces, use hyphen)
    text = text.replace(' — ', ' - ')
    # "—" at start of a clause → ": " or just remove
    text = re.sub(r'(\w)—(\w)', r'\1 - \2', text)
    # Any remaining
    text = text.replace('—', ' - ')
    return text, text != original


def run():
    from app import app, db
    from models import Insight

    with app.app_context():
        articles = Insight.query.all()
        fixed_em = 0
        fixed_draft = 0
        fixed_sport = 0
        fixed_title = 0
        fixed_story_type = 0

        for a in articles:
            changes = []

            # 1. Em dash cleanup
            new_content, changed_c = clean_em_dashes(a.content)
            new_excerpt, changed_e = clean_em_dashes(a.excerpt)
            new_title, changed_t = clean_em_dashes(a.title)
            if changed_c:
                a.content = new_content
            if changed_e:
                a.excerpt = new_excerpt
            if changed_t:
                a.title = new_title
            if changed_c or changed_e or changed_t:
                changes.append('em_dash')
                fixed_em += 1

            # 2. Publish draft MLB articles with proper dates
            if a.slug in DRAFT_MLB_SCHEDULE and a.status == 'draft':
                a.status = 'scheduled'
                a.publish_date = DRAFT_MLB_SCHEDULE[a.slug]
                changes.append(f'draft→scheduled {a.publish_date.strftime("%b %d")}')
                fixed_draft += 1

            # 3. Fix mlb-shadow-mode sport tag
            if a.slug == 'mlb-shadow-mode-what-we-learned' and a.sport != 'mlb':
                a.sport = 'mlb'
                changes.append('sport→mlb')
                fixed_sport += 1

            # 4. Fix N/A in market note title
            if a.slug == 'market-note-2026-03-22' and 'N/A' in (a.title or ''):
                a.title = 'The entire slate narrows to one game. Discipline wins.'
                changes.append('fixed_title')
                fixed_title += 1

            # 5. Backfill missing story_type
            if not a.story_type and a.category in CATEGORY_TO_STORY_TYPE:
                a.story_type = CATEGORY_TO_STORY_TYPE[a.category]
                changes.append(f'story_type→{a.story_type}')
                fixed_story_type += 1

            if changes:
                print(f'  {a.slug}: {", ".join(changes)}')

        db.session.commit()

        print()
        print(f'Em dashes cleaned:     {fixed_em}')
        print(f'Drafts → scheduled:    {fixed_draft}')
        print(f'Sport tags fixed:      {fixed_sport}')
        print(f'Titles fixed:          {fixed_title}')
        print(f'Story types filled:    {fixed_story_type}')
        print(f'Total articles:        {len(articles)}')
        print('Done.')


if __name__ == '__main__':
    run()
