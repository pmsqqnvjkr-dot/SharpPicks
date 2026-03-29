"""Seed 6 MLB Sharp Journal articles."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ET = ZoneInfo('America/New_York')

ARTICLES = [
    {
        'title': '162 Games and the Luxury of Sample Size',
        'slug': 'mlb-sample-size',
        'category': 'how_it_works',
        'story_type': 'how_it_works',
        'sport': 'mlb',
        'reading_time_minutes': 3,
        'publish_offset_days': 0,
        'excerpt': (
            'MLB gives us 2,430 regular season games. More opportunities to find edges. '
            'More opportunities to do nothing.'
        ),
        'content': r"""## 162 Games and the Luxury of Sample Size

The NBA regular season gives us 1,230 games. That is a reasonable sample to evaluate a model against. MLB gives us 2,430. That is a different universe of data.

More games means more opportunities to find edges. It also means more opportunities to do nothing. The discipline filter that sits out 40-50% of NBA slates will likely sit out an even higher percentage in baseball, because the sheer volume of games means we can afford to be pickier.

---

## What Changes

Starting pitching is the single biggest variable in baseball. A team's expected run output shifts dramatically based on who is on the mound. Our feature set accounts for this: pitcher-specific metrics, bullpen usage patterns, rest days, platoon splits, and park factors all feed the model. In the NBA, the closest equivalent would be if a team's entire offensive scheme changed based on which point guard started. That is effectively what happens every day in MLB.

Line movement also behaves differently. In the NBA, lines move primarily on public money and injury news. In MLB, lines move on pitching changes, lineup announcements, and weather. The window between lineup lock and first pitch is where the sharpest edges appear and disappear. Our pre-tip validation is even more critical here.

---

## What Stays the Same

The edge threshold is still 3.5%. The four-model ensemble still runs the same way. CLV is still the primary performance metric. If the model cannot find a mathematical edge above our minimum, no signal fires. The sport changed. The discipline did not.""",
    },
    {
        'title': 'What Calibration Phase Means (And Why You Should Care)',
        'slug': 'mlb-calibration-phase',
        'category': 'how_it_works',
        'story_type': 'how_it_works',
        'sport': 'mlb',
        'reading_time_minutes': 3,
        'publish_offset_days': -3,
        'excerpt': (
            'Calibration phase means the model is publishing real picks against real lines '
            'and grading every one. The track record builds in front of you.'
        ),
        'content': r"""## What Calibration Phase Means (And Why You Should Care)

Every MLB signal you see in the app right now has a label on it: Calibration. This is not a disclaimer. It is a statement about where the model is in its lifecycle.

Calibration phase means the model is live, generating real picks against real lines, and grading every result against the closing line. The picks are not hypothetical. They are tracked, timestamped, and published before the game starts. The only difference between calibration and deployment is how much live data the model has accumulated.

---

## Why We Do This in Public

Most services build a model, backtest it on historical data, and launch it as "proven." Backtesting is necessary, but it is not sufficient. A model that looks profitable on three years of historical data can fall apart in its first month of live play for dozens of reasons: data pipeline delays, feature drift, market regime changes, or simple overfitting.

> Calibration phase catches these problems in real time.

You can see every pick the model makes and grade it yourself. You can watch the CLV numbers accumulate. You can see whether the model's edges are real or an artifact of sample noise. We are building the track record in front of you, not behind a backtest.

---

## When Does Calibration End

We have internal criteria for promotion to deployment phase. Those criteria are based on sample size, CLV consistency, and edge-to-outcome correlation. We will not announce a specific date because the data decides, not the calendar. When the model earns deployment status, you will know.""",
    },
    {
        'title': 'The Starting Pitcher Problem',
        'slug': 'mlb-starting-pitcher',
        'category': 'market_notes',
        'story_type': 'market_notes',
        'sport': 'mlb',
        'reading_time_minutes': 3,
        'publish_offset_days': -7,
        'excerpt': (
            'In MLB, the starting pitcher can shift run expectation by 2-3 runs. '
            'No other sport has a single variable with that much influence.'
        ),
        'content': r"""## The Starting Pitcher Problem

In the NBA, you can model a team as a relatively stable unit. Rosters change, players rest, but the core identity of a team on any given night is broadly predictable. In baseball, the starting pitcher rewrites the entire equation.

A team with a Cy Young-caliber ace on the mound is a fundamentally different proposition than the same team with a fifth starter making his third appearance in a week. The run expectation can shift by two or three runs based on the pitching matchup alone. No other major sport has a single variable with that much influence on the outcome.

---

## How the Model Handles This

Pitcher-specific features are the most heavily weighted inputs in the MLB model. We track recent performance (last 5 starts), season-long metrics, platoon splits against the opposing lineup, pitch mix evolution, and rest days. We also track bullpen state: a team with an overworked bullpen behind a short-start pitcher is a different risk profile than the same team with a fully rested pen.

The market generally prices starting pitching correctly for aces and established veterans. Where the model finds edges is in the middle tier: the fourth and fifth starters, the recently promoted prospect, the veteran coming off an IL stint. These are the matchups where the market is relying on name recognition and the model is relying on recent data.

---

## Late Scratches

When a starting pitcher is scratched late, the line moves fast. Our pre-tip validation checks for this. If the original edge was built on a specific pitching matchup and that matchup changes, the signal is withdrawn. You will see a pick withdrawn notification. This is the system working. The model had an edge against the original starter. It does not have an opinion on the replacement.""",
    },
    {
        'title': 'Run Lines Are Not Spreads (And That Matters)',
        'slug': 'mlb-run-lines',
        'category': 'how_it_works',
        'story_type': 'how_it_works',
        'sport': 'mlb',
        'reading_time_minutes': 3,
        'publish_offset_days': -10,
        'excerpt': (
            'NBA edges live in the number. MLB edges live in the price. '
            'Same math, different expression.'
        ),
        'content': r"""## Run Lines Are Not Spreads (And That Matters)

If you are coming from NBA betting, you are used to spreads that move in half-point increments across a wide range. A team can be favored by 1.5 or by 14.5. The spread reflects the expected margin of victory, and it moves fluidly based on money and information.

MLB run lines work differently. The standard run line is -1.5 / +1.5 for almost every game. Instead of adjusting the spread, the market adjusts the price. A heavy favorite might be -1.5 at -180 (you risk $180 to win $100). An underdog might be +1.5 at -120. The run line itself rarely changes. The juice does.

---

## What This Means for Edge Detection

In the NBA, the model finds edges in the number: the market says -7.5 and the model says -10. The edge is in the 2.5-point gap. In MLB, the model more often finds edges in the price: the market says -1.5 at -150 and the model says that price should be -130. The edge is in the 20-cent gap on the juice.

> MLB edges tend to be more subtle. A 3.5% edge on a run line looks different than a 3.5% edge on an NBA spread.

Both are mathematically equivalent in expected value, but the run line edge requires more precision because the model is disagreeing with the market on probability, not on margin.

---

## Moneylines

The MLB model also evaluates moneyline odds (straight win/loss, no spread). Some of our strongest edges may come on the moneyline rather than the run line, particularly in games with closely matched pitching. When you see a moneyline signal, the model is saying the probability of one team winning is meaningfully different from what the market implies. No spread involved, just pure probability disagreement.""",
    },
    {
        'title': '15 Games a Day and the Discipline to Pass on 14',
        'slug': 'mlb-discipline-pass',
        'category': 'philosophy',
        'story_type': 'philosophy',
        'sport': 'mlb',
        'reading_time_minutes': 3,
        'publish_offset_days': -14,
        'excerpt': (
            'MLB has 15 games a day, six months straight. If none of that math '
            'produces an edge above 3.5%, you get a pass notification. That is the product.'
        ),
        'content': r"""## 15 Games a Day and the Discipline to Pass on 14

A full MLB slate can have 15 or 16 games. That is every single day, six months straight, from late March through September. Compare that to the NBA, where a full slate is 10-12 games and there are off days built into the schedule.

The volume is a gift and a trap. It is a gift because more games means a larger sample to evaluate the model. It is a trap because more games creates the illusion that there must be value somewhere every single day. There does not have to be.

---

## The Pass Day Is Still the Product

We built the entire SharpPicks brand around the idea that doing nothing is the correct action most of the time. That philosophy becomes even more important with 15 daily games to analyze. The temptation to manufacture a signal when none exists is stronger when there are more games to choose from. The model does not feel temptation. It runs the numbers, applies the 3.5% threshold, and either fires or does not.

> Expect pass days. Expect multiple consecutive pass days.

The model is evaluating 15 pitching matchups, 30 bullpen states, 30 lineup configurations, and dozens of park and weather variables. If none of that math produces a qualifying edge, you will get a notification that says so, and that notification is the product working exactly as designed.

---

## Selectivity Will Be Different

In the NBA, we act on roughly 40-50% of slates. In MLB, the selectivity rate may be lower. More games per day means more chances to find nothing above threshold. A 30% selectivity rate in MLB, sustained over a 162-game season, would still produce a meaningful number of signals. We do not need to force action to justify the subscription. The math either works or it does not.""",
    },
    {
        'title': 'Coors Field, Wind, and the Variables the Market Underprices',
        'slug': 'mlb-park-weather-factors',
        'category': 'market_notes',
        'story_type': 'market_notes',
        'sport': 'mlb',
        'reading_time_minutes': 3,
        'publish_offset_days': -17,
        'excerpt': (
            'The market prices Coors Field. It is less efficient at pricing the interaction '
            'between a ground ball pitcher, a flyball-averse lineup, and 12 mph wind blowing in.'
        ),
        'content': r"""## Coors Field, Wind, and the Variables the Market Underprices

Every MLB ballpark plays differently. Coors Field in Denver inflates run totals by 20-30% compared to league average. Oracle Park in San Francisco suppresses them. Yankee Stadium's short right field porch turns routine fly balls into home runs for left-handed hitters. These are not small effects. They are structural features of the game that persist over decades.

The market knows about park factors. Every sportsbook adjusts their lines for Coors, for Petco, for Wrigley with the wind blowing out. What the market is less efficient at pricing is the interaction between park factors and specific pitcher profiles, lineup compositions, and day-of weather conditions.

---

## Where the Edges Hide

A fly ball pitcher throwing in Coors is not a revelation. The market adjusts for that. But a ground ball pitcher throwing in Coors against a lineup that is struggling to elevate the ball? That interaction is more nuanced than a simple park adjustment. The model evaluates these compound variables: pitcher tendency, opposing lineup batted ball profile, park dimensions, wind speed and direction, temperature, and humidity. The edge is often not in any single variable but in the combination.

> The edge is not in any single variable but in the combination.

Weather is the most volatile input. A game-time forecast showing 15 mph wind blowing out at Wrigley changes the run expectation materially. Lines adjust, but not always fast enough. Our data pipeline ingests weather data as close to first pitch as possible, which means the pre-tip validation step is checking whether the conditions that created the original edge are still present.

---

## Why This Matters for You

You will occasionally see signals on games that look obvious: a high total at Coors, a low total at Petco. The model is not finding those because it is smarter than everyone else about park factors. It is finding them because the specific intersection of pitcher, lineup, park, and weather on that particular day creates an edge the market has not fully priced. If the edge is not there, neither is the signal.""",
    },
]


def seed():
    from app import app, db
    from models import Insight

    with app.app_context():
        now = datetime.now(ET).replace(tzinfo=None)
        for art in ARTICLES:
            pub_date = now + timedelta(days=art['publish_offset_days'])
            existing = Insight.query.filter_by(slug=art['slug']).first()
            if existing:
                print(f"Updating '{art['slug']}' (id={existing.id})")
                existing.title = art['title']
                existing.category = art['category']
                existing.excerpt = art['excerpt']
                existing.content = art['content']
                existing.status = 'published'
                existing.featured = False
                existing.story_type = art['story_type']
                existing.sport = art['sport']
                existing.reading_time_minutes = art['reading_time_minutes']
                existing.publish_date = pub_date
            else:
                insight = Insight(
                    title=art['title'],
                    slug=art['slug'],
                    category=art['category'],
                    excerpt=art['excerpt'],
                    content=art['content'],
                    status='published',
                    publish_date=pub_date,
                    featured=False,
                    story_type=art['story_type'],
                    sport=art['sport'],
                    reading_time_minutes=art['reading_time_minutes'],
                    related_pick_ids=[],
                )
                db.session.add(insight)
                print(f"Created '{art['slug']}'")
        db.session.commit()
        print(f"\nDone. {len(ARTICLES)} MLB articles seeded.")


if __name__ == '__main__':
    seed()
