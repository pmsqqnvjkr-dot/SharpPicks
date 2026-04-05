"""Insert the Beginner's Guide as a published Insight article."""
from datetime import datetime
from zoneinfo import ZoneInfo
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ET = ZoneInfo('America/New_York')

TITLE = "A Beginner's Guide to SharpPicks"
SLUG = "beginners-guide"
CATEGORY = "how_it_works"
EXCERPT = (
    "Everything you need to know to read your signals, understand your results, "
    "and use the app with confidence."
)

CONTENT = r"""## What Is SharpPicks?

SharpPicks is a sports market intelligence platform. It uses a mathematical model to identify games where the betting market has gotten the number wrong. When the model finds a big enough difference, it generates a **signal**: essentially a recommendation worth considering. It currently covers the NBA (with MLB in beta and WNBA coming soon).

> A low density number means the model is being very selective.

---

## The 5 Main Tabs

---

## 1. Signals (Home Screen)

This is your daily dashboard. Here's what you'll see:

[screenshot: signals]

**Market Intelligence Banner:** A quick summary of the day's landscape. For example, "9 games · 6 edges · 2 signals · 22% density" means: out of 9 NBA games today, the model found 6 where it disagrees with the market, but only 2 were strong enough to become official signals. The 22% density tells you how active the model is. A low number means it's being very selective.

**Outcome Resolved:** This shows the result of the most recent signal. It tells you the pick, the final score, and a brief mindset note (like "No revenge bets. Next signal when the edge is there.") to encourage disciplined thinking.

**Daily Top Signal:** The main event. This is the app's strongest pick for the day. Here's what each piece means:

**Team Name + Number (e.g., Oklahoma City Thunder -8.5):** The "-8.5" is the spread. It means the model is recommending OKC, but they need to win by more than 8.5 points for the bet to pay out. A minus spread means the team is favored; a plus spread means they're the underdog.

**+12.8% (Edge):** This is the edge, the percentage difference between where the market has the line and where the model thinks it should be. Bigger = better.

**-105 (Price/Odds):** This tells you the cost of the bet. At -105, you'd risk $105 to win $100. Standard American odds: negative numbers mean you lay more than you win, positive numbers mean you win more than you lay.

**Countdown:** Time remaining until game start.

**Market vs. Model:** The market line is -8.5 (what sportsbooks are offering). The model line is -13 (what the model thinks the line should be). That gap is where the value comes from.

**Tier (STR):** Signal strength. "STR" stands for Strong, the model's highest conviction level.

**Size (2u):** The recommended bet size in units. A "unit" is your standard bet amount (e.g., if your unit is $50, a 2u bet means $100). This keeps things relative to your bankroll rather than fixed dollar amounts.

**Edge bar (+12.8pp):** A visual showing the edge in percentage points.

**Value line ("Playable down to -12"):** If the spread moves, this tells you the worst number at which the bet is still worth taking. If it moves past -12, the value is gone.

**Flat 2u vs. Kelly 5u:** Two bet-sizing strategies. "Flat" means bet the same amount every time (the conservative approach). "Kelly" is a mathematical formula that sizes bets proportional to the edge: higher confidence = bigger bet. The Kelly suggestion of 5u is more aggressive.

**Tracking button:** Tap this to log the bet in your personal tracker so you can follow your results.

**Season Performance:** A snapshot of the model's overall track record:

**Win Rate:** Percentage of signals that won.

**ROI:** Return on Investment. For every dollar wagered following the signals, you'd be up by that percentage.

**Avg CLV:** Closing Line Value. On average, how much the line moved in the model's direction after the signal was released. This is a key indicator that the model is finding real value.

**Signals:** Total number of picks made this season.

**Units:** Net profit in units across all signals.

**Signal History:** A scrollable list of every past signal with win/loss results, units gained or lost, and CLV for each.

---

## 2. Market

A deeper look at the day's full slate of games.

[screenshot: market]

**MEI (Market Efficiency Index):** A score from 0-100 measuring how much opportunity the model sees across all games today. Higher = more opportunities.

**Regime:** The model's assessment of the current market environment. "Active" means it's finding a moderate number of opportunities.

**Top Edge:** The best single edge found today.

**Signal breakdown:** How many edges exist at each confidence level. Only the strong and sometimes moderate ones become official signals.

**Line Movement:** Shows how the betting line for each game has moved, and whether it's moving toward or away from the model's prediction. "Toward model" is a positive validation sign.

**Model vs. Market Delta:** A ranked list showing the gap between the model's line and the market line for every game. The biggest gaps are at the top: these are where the model sees the most disagreement with the market.

---

## 3. Results

Your personal scoreboard.

[screenshot: results]

**Your Results:** Shows your actual profit/loss if you've been tracking bets.

**ROI:** Your personal return on investment across tracked bets.

**Equity Curve:** The line chart showing your profit over time, ideally trending upward.

**Track a Bet:** Button to manually log a bet you've placed.

**Discipline Score:** This grades how selectively you're following signals. A lower selectivity rate means you're being more choosy than the industry average, which the app considers a good thing. It awards a letter grade.

**Picks Followed vs. Passed:** How many signals you acted on versus skipped.

**Capital Preserved:** An estimate of money saved by passing on picks that turned out to be losing bets.

**Active / Settled Bets:** Active bets are still in play; settled bets show final outcomes with profit or loss in green (+) or red (-).

---

## 4. Insights (Sharp Journal)

[screenshot: insights]

Educational content and daily commentary from the founder. Articles are tagged by category: **Philosophy** (the thinking behind the approach), **Discipline** (mindset and bankroll management), **Market Notes** (daily analysis), and **How It Works** (technical explanations).

---

## 5. Account

Your personal settings and subscription management.

---

## Key Concepts Glossary

**Spread:** The number of points a team is expected to win or lose by. Betting the spread means you're not just picking a winner, you're picking whether a team will win by more (or lose by less) than the number.

**Edge:** The difference between what the model predicts and what the market offers. A bigger edge means more potential value.

**Unit (u):** A standardized bet size relative to your bankroll. Most people set 1 unit at 1-2% of their total bankroll.

**CLV (Closing Line Value):** How much the line moved in your favor between when you placed the bet and when it closed. Consistently beating the closing line is the gold standard of sharp betting: it means you're getting better numbers than the final market price.

**ROI (Return on Investment):** Your profit as a percentage of total money wagered.

**Kelly Criterion:** A mathematical formula for optimal bet sizing based on edge size and probability. It's more aggressive than flat betting.

**Signal Density:** The percentage of games that produce a signal. Low density means the model is being highly selective."""


def seed():
    from app import app, db
    from models import Insight

    with app.app_context():
        existing = Insight.query.filter_by(slug=SLUG).first()
        if existing:
            print(f"Insight '{SLUG}' already exists (id={existing.id}). Updating...")
            existing.title = TITLE
            existing.category = CATEGORY
            existing.excerpt = EXCERPT
            existing.content = CONTENT
            existing.status = 'published'
            existing.featured = True
            existing.story_type = 'how_it_works'
            existing.sport = None
            existing.reading_time_minutes = 5
            existing.publish_date = datetime.now(ET).replace(tzinfo=None)
            db.session.commit()
            print(f"Updated. id={existing.id}")
            return

        insight = Insight(
            title=TITLE,
            slug=SLUG,
            category=CATEGORY,
            excerpt=EXCERPT,
            content=CONTENT,
            status='published',
            publish_date=datetime.now(ET).replace(tzinfo=None),
            featured=True,
            story_type='how_it_works',
            sport=None,
            reading_time_minutes=5,
            related_pick_ids=[],
        )
        db.session.add(insight)
        db.session.commit()
        print(f"Created Insight: id={insight.id}, slug={insight.slug}")


if __name__ == '__main__':
    seed()
