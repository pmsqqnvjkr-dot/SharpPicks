# SHARPPICKS BRAND GUIDE
### Complete Brand Specification · March 2026 · v3.0

---

# 1. IDENTITY

- **Brand name:** SharpPicks (one word, capital S capital P)
- **Wordmark:** SHARP || PICKS (all caps, || signal bars as center divider)
- **App store name:** SharpPicks
- **Domain:** sharppicks.ai (app: app.sharppicks.ai)
- **Support:** support@sharppicks.ai
- **Sports:** NBA, MLB, WNBA

---

# 2. TAGLINES

| Priority | Text | Usage |
|----------|------|-------|
| Primary | **One pick beats five.** | Hero, merch, social bios, marketing, OG image |
| Secondary | **Selective by design.** | Footer, landing page, supporting context |

- Render taglines: all caps, wide tracking (0.3em+), green (#5A9E72)

---

# 3. THE ONE-LINE PITCH

**SharpPicks is the first sports market intelligence platform.**

Not a picks service. Not a tout sheet. Not entertainment. SharpPicks is a decision-support system that tells you what the model sees, why it sees it, where the edge invalidates, and whether you're disciplined enough to capture it.

---

# 4. COLOR PALETTE

## Primary

| Swatch | Name | Hex | RGB | Usage |
|--------|------|-----|-----|-------|
| ⬛ | Navy | #111827 | 17, 24, 39 | Primary bg, icon bg, text on light |
| ⬜ | White | #E8EAED | 232, 234, 237 | Signal bars, wordmark, UI text on dark |

## Accent

| Swatch | Name | Hex | RGB | Usage |
|--------|------|-----|-----|-------|
| 🟩 | Green | #5A9E72 | 90, 158, 114 | Positive signals, tagline, CTAs, edge detected |
| 🟥 | Red | #C4686B | 196, 104, 107 | Negative signals, alerts, loss indicators |

## Extended

| Name | Hex | RGB | Usage |
|------|-----|-----|-------|
| Deep BG | #0A0C10 | 10, 12, 16 | Deep page background |
| Card BG | #12151C | 18, 21, 28 | Card/surface background |
| Border | #1E2230 | 30, 34, 48 | Subtle borders |
| Muted | #5A6270 | 90, 98, 112 | Muted text, secondary labels |

## CSS Variables

```css
:root {
  --sp-navy:     #111827;
  --sp-white:    #E8EAED;
  --sp-green:    #5A9E72;
  --sp-red:      #C4686B;
  --sp-dark:     #0A0C10;
  --sp-dark-card:#12151C;
  --sp-border:   #1E2230;
  --sp-muted:    #5A6270;
}
```

## Color Rules

- Navy + white carry 90% of visual weight
- Green is ONLY for: accent, positive signals, tagline, CTAs, "edge detected" states
- Red is ONLY for: negative signals, alerts, loss indicators
- Never use green and red together as equal-weight elements (accessibility)

---

# 5. TYPOGRAPHY

## Font Stack

| Context | Font | Weight | Notes |
|---------|------|--------|-------|
| Wordmark | Inter | 500 (Medium) | Uppercase, 0.25em tracking |
| Headlines | IBM Plex Serif | 600 | Editorial, Sharp Journal, hero |
| Body | Inter | 400 | General UI, descriptions |
| Code/Data | JetBrains Mono | 400 | Pick cards, data tables, command center |
| Tagline | Inter | 400 | Uppercase, 0.3em+ tracking, green |
| Labels/Meta | IBM Plex Mono | 400-500 | Small caps, wide tracking, muted color |

## CSS Variables

```css
:root {
  --sp-font-heading: 'IBM Plex Serif', Georgia, serif;
  --sp-font-body:    'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  --sp-font-mono:    'JetBrains Mono', 'IBM Plex Mono', 'Fira Code', monospace;
}
```

## Google Fonts Import

```html
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=IBM+Plex+Serif:wght@400;600;700&family=JetBrains+Mono:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
```

**CRITICAL:** Never use Inter weight 300 (Light) for the wordmark. Weight 300 fails on low-DPI screens, Android, and print/merch. Always 500.

---

# 6. WORDMARK — SHARP || PICKS

## Specifications

- Font: Inter Medium (500)
- Case: ALL UPPERCASE
- Letter-spacing: 0.25em
- Signal bars (||): two vertical pill-shaped bars
- Bar width: matches text stroke weight (~3px at display size)
- Bar height: extends 12% beyond cap-height equally above AND below the text
- Bar gap: ~0.22em between the two bars
- Bar border-radius: 50% of bar width (pill shape)
- Bar horizontal spacing: equal padding on both sides
- Minimum render width: 120px (below this, use icon only)

## CSS Implementation

```css
.sp-wordmark {
  display: inline-flex;
  align-items: center;
  gap: 0;
  line-height: 1;
}

.sp-wordmark__text {
  font-family: var(--sp-font-body);
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.25em;
  color: var(--sp-white);
}

.sp-wordmark__signal {
  display: inline-flex;
  gap: 0.18em;
  margin: 0 0.4em;
  align-self: center;
}

.sp-wordmark__signal span {
  display: block;
  width: 0.08em;
  height: 1.24em; /* 12% overshoot above and below cap-height */
  background: currentColor;
  border-radius: 999px;
}

/* On light backgrounds */
.sp-wordmark--light .sp-wordmark__text { color: var(--sp-navy); }
.sp-wordmark--light .sp-wordmark__signal span { background: var(--sp-navy); }
```

## HTML

```html
<!-- Dark background (primary) -->
<div class="sp-wordmark">
  <span class="sp-wordmark__text">SHARP</span>
  <span class="sp-wordmark__signal"><span></span><span></span></span>
  <span class="sp-wordmark__text">PICKS</span>
</div>
```

## Wordmark + Tagline Lockup

```html
<div class="sp-wordmark-lockup">
  <div class="sp-wordmark">
    <span class="sp-wordmark__text">SHARP</span>
    <span class="sp-wordmark__signal"><span></span><span></span></span>
    <span class="sp-wordmark__text">PICKS</span>
  </div>
  <div class="sp-tagline">ONE PICK BEATS FIVE</div>
</div>
```

```css
.sp-wordmark-lockup {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5em;
}
.sp-tagline {
  font-family: var(--sp-font-body);
  font-weight: 400;
  text-transform: uppercase;
  letter-spacing: 0.35em;
  color: var(--sp-green);
  font-size: 0.35em;
}
```

---

# 7. APP ICON

## Structure

- Background: #111827 (navy)
- Two vertical bars: #E8EAED (white), pill-shaped
  - Width: ~3.8% of icon size
  - Height: ~34% of icon size
  - Border-radius: 50% of width
  - Centered, vertically centered
- Green accent underscore: #5A9E72
  - Width: ~15% of icon size
  - Height: ~1.2% of icon size
  - Centered below bars

## Export Sizes

| File | Size | Use |
|------|------|-----|
| icon-1024.png | 1024x1024 | App Store / Play Store |
| icon-512.png | 512x512 | Marketing |
| icon-192.png | 192x192 | Android web manifest |
| icon-180.png | 180x180 | iOS touch icon |
| favicon-32.png | 32x32 | Browser favicon (no green accent) |
| favicon-16.png | 16x16 | Browser favicon (no green accent) |

## Notes

- iOS auto-applies squircle mask. Submit square PNG
- Android: use as adaptive icon foreground layer on #111827 background
- At 32px and below, omit the green accent (too small to render)

---

# 8. SIGNAL MARK (||)

The || signal can be used standalone:

- Social avatars
- Favicons
- Loading/spinner states
- Watermarks
- Merch (hat, tumbler, sleeve)

Available as: signal-white-transparent.png, signal-navy-transparent.png, signal-green-transparent.png (512px), merch-signal-1000.png (1000px)

---

# 9. ASSET FILE INDEX

All assets are included in the `SharpPicks-Brand-Kit/` folder alongside this guide.

```
SharpPicks-Brand-Kit/
│
├── SharpPicks-Brand-Guide.md              ← This file
├── social-og-1200x630.png                 OG card for link previews
│
├── app-icons/
│   ├── icon-1024.png                      App Store / Play Store (1024x1024)
│   ├── icon-512.png                       Marketing (512x512)
│   ├── icon-192.png                       Android web manifest (192x192)
│   ├── apple-touch-icon-180.png           iOS touch icon (180x180)
│   ├── favicon-32.png                     Browser favicon (32x32)
│   └── favicon-16.png                     Browser favicon (16x16)
│
├── signal-marks/                          || signal mark, standalone
│   ├── signal-white-1000.png              White on transparent (1000px)
│   ├── signal-white-2000.png              White on transparent (2000px)
│   ├── signal-navy-2000.png               Navy on transparent (2000px)
│   ├── signal-green-2000.png              Green on transparent (2000px)
│   ├── signal-white-green-500.png         White bars + green accent (500px)
│   ├── signal-white-green-1000.png        White bars + green accent (1000px)
│   ├── signal-white-green-2000.png        White bars + green accent (2000px)
│   ├── signal-navy-green-1000.png         Navy bars + green accent (1000px)
│   └── signal-navy-green-2000.png         Navy bars + green accent (2000px)
│
├── wordmarks/                             SHARP || PICKS horizontal
│   ├── wordmark-white-2000.png            White on transparent (2000px wide)
│   ├── wordmark-white-3000.png            White on transparent (3000px wide)
│   ├── wordmark-white-4000.png            Print-ready (4000px wide)
│   ├── wordmark-navy-3000.png             Navy on transparent (3000px wide)
│   └── wordmark-navy-4000.png             Print-ready (4000px wide)
│
├── wordmarks-tagline/                     SHARP || PICKS + ONE PICK BEATS FIVE
│   ├── wordmark-tagline-white-3000.png    White on transparent (3000px)
│   ├── wordmark-tagline-white-4000.png    Print-ready (4000px)
│   └── wordmark-tagline-navy-4000.png     Navy on transparent (4000px)
│
├── taglines/                              Standalone tagline text
│   ├── mono-tagline-white-3000.png        Mono font, white (3000px)
│   ├── mono-tagline-green-3000.png        Mono font, green (3000px)
│   ├── mono-tagline-navy-3000.png         Mono font, navy (3000px)
│   ├── serif-tagline-white-2000.png       Serif font, white (2000px)
│   ├── serif-tagline-white-3000.png       Serif font, white (3000px)
│   └── serif-tagline-navy-3000.png        Serif font, navy (3000px)
│
├── stacked-lockups/                       Vertical: signal + wordmark + tagline
│   ├── stacked-white-2000x3000.png        White on transparent (2000x3000)
│   └── stacked-navy-2000x3000.png         Navy on transparent (2000x3000)
│
├── positioning/                           "SPORTS MARKET INTELLIGENCE" text
│   ├── positioning-white-3000.png         White on transparent
│   ├── positioning-green-3000.png         Green on transparent
│   └── positioning-navy-3000.png          Navy on transparent
│
└── urls/                                  "sharppicks.ai" text
    ├── url-white-2000.png                 White on transparent
    └── url-navy-2000.png                  Navy on transparent
```

---

# 10. OG / META TAGS

```html
<meta property="og:title" content="SharpPicks — One pick beats five." />
<meta property="og:description" content="AI-driven sports betting analytics. NBA, MLB, WNBA." />
<meta property="og:image" content="https://sharppicks.ai/social-og-1200x630.png" />
<meta property="og:type" content="website" />
<meta name="twitter:card" content="summary_large_image" />
```

---

# 11. USAGE RULES

1. Never rotate, stretch, or skew the wordmark or icon
2. Never change individual element colors (e.g., green bars + white text)
3. Never add drop shadows, outer glows, or 3D effects
4. Never place on busy or low-contrast backgrounds
5. Minimum clear space = height of || bars on all sides
6. Below 120px width, use icon only, not wordmark
7. The || bars must always match text optical weight
8. The || bars must extend equally above and below text cap-height (12% overshoot)
9. Replace em dashes with mid-dots ( · ) in all brand copy
10. Never write "Sharp Picks" (two words). Always "SharpPicks" (one word)

---

# 12. BRAND AESTHETIC

- **Terminal/institutional** — not flashy, not consumer-sportsbook
- **Dark navy base**, understated, data-focused interfaces
- **Anti-tout philosophy**: let the model speak, never oversell
- **Comparable to**: Stripe, Bloomberg Terminal aesthetic
- **NOT comparable to**: FanDuel, DraftKings, BetMGM
- Prefer IBM Plex Serif for editorial weight, JetBrains Mono for data credibility
- Prefer restraint over decoration in all UI decisions

---

# 13. WHAT SETS US APART — THE FOUR LAYERS

## Layer 1: Market Intelligence

What the market looks like today, before you bet anything.

- **MEI (Market Edge Index):** A single number that quantifies today's overall market opportunity. Not every day is a betting day. MEI tells you before you look at a single game.
- **Regime Classification:** Is the market normal, volatile, or compressed? This changes how aggressively the model acts.
- **Market Signal:** A plain-language narrative explaining what the model isolated and why.
- **Line Movement Tracker:** Which lines moved toward model, away from model, or stayed flat.
- **Model vs Market Delta:** Visual bars showing the gap between model projection and market line for every game.

*No other sports app gives you a daily market briefing before you see a single pick.*

## Layer 2: Quantitative Edge Detection

Every signal comes with full model transparency.

- **Four-Model Ensemble:** GBM, Random Forest, XGBoost, AdaBoost. All must agree before a signal fires. Consensus, not conviction from a single model.
- **56 Features:** The models analyze 56 quantifiable features per game. No gut feel. No narratives. Data.
- **Adjusted Edge:** The final edge after shrinkage blend (30/70 model-to-market).
- **Cover Probability:** The actual model-estimated probability of covering, shown against the implied market probability.
- **Value Range:** "Playable down to -12. Edge invalidates beyond." The exact line where the bet stops being worth it.
- **Quant Reasoning:** Plain-language explanation of the matchup math.
- **3.5% Minimum Edge Threshold:** If the model doesn't find at least 3.5% edge, nothing gets sent. Silence is a signal.

*No other sports app shows you where the edge invalidates or gives you a playable value range.*

## Layer 3: Behavioral Edge

The feature nobody else has: it measures the bettor, not just the bet.

- **Discipline Score:** A letter grade (A through F) based on how selectively you follow signals.
- **Selectivity Rate:** What percentage of model signals you actually bet on. Lower is usually better.
- **Capital Preserved:** The dollar amount your bankroll saved by passing on picks you didn't follow.
- **Selectivity Spectrum:** A visual scale from "Sharp (Selective)" to "Square (Volume)."
- **Bankroll Tracking:** Actual P&L curve with real stakes, ROI, unit tracking, and record.
- **Model vs Off-Model:** Compare your results when following the model vs going off-script.

*No other sports app tells you the value of the bets you didn't make.*

## Layer 4: Sharp Journal

The editorial layer that builds conviction and educates.

- **Founder Letters:** Covering model philosophy, market mechanics, and discipline.
- **Market Notes:** Same-day analysis explaining what the model saw and why.
- **Philosophy & Discipline:** Content designed to make users better bettors by helping them understand when not to bet.

*No other sports app has an editorial layer that actively discourages unnecessary betting.*

---

# 14. COMPETITIVE DIFFERENTIATION

| Feature | SharpPicks | Sharp App | Action Network | DraftKings | Tout Services |
|---------|-----------|-----------|----------------|------------|---------------|
| Daily market briefing (MEI) | ✓ | ✗ | ✗ | ✗ | ✗ |
| Regime classification | ✓ | ✗ | ✗ | ✗ | ✗ |
| Model transparency (full) | ✓ | Partial | ✗ | ✗ | ✗ |
| Value range / invalidation | ✓ | ✗ | ✗ | ✗ | ✗ |
| Quant reasoning per pick | ✓ | ✗ | ✗ | ✗ | ✗ |
| Minimum edge threshold | ✓ (3.5%) | ✗ | ✗ | ✗ | ✗ |
| Discipline scoring | ✓ | ✗ | ✗ | ✗ | ✗ |
| Capital preserved metric | ✓ | ✗ | ✗ | ✗ | ✗ |
| Selectivity spectrum | ✓ | ✗ | ✗ | ✗ | ✗ |
| Model vs off-model tracking | ✓ | ✗ | ✗ | ✗ | ✗ |
| Editorial / Journal layer | ✓ | ✗ | ✓ | ✗ | Partial |
| Multi-sport AI ensemble | ✓ | ✓ | ✗ | ✗ | ✗ |

---

# 15. POSITIONING STATEMENTS

**App Store:**
SharpPicks is sports market intelligence, not a picks service. Our AI analyzes 56 features across NBA, MLB, and WNBA games using a four-model ensemble, surfacing only the signals that cross a verified edge threshold. Every pick shows you the model's math, the value range where it's playable, and the exact point where the edge disappears. Track your discipline, measure your selectivity, and see the bankroll impact of the bets you didn't take. One pick beats five.

**Landing Page Hero:**
Market intelligence for sports. AI-powered edge detection across NBA, MLB, and WNBA. Not a picks service. A decision-support system.

**Social Bio:**
Market intelligence for sports. AI edge detection. NBA · MLB · WNBA. One pick beats five. sharppicks.ai

**Pitch / Investor:**
SharpPicks is the first sports market intelligence platform. While competitors sell picks, we sell a decision framework: quantified edge detection, full model transparency, and behavioral analytics that measure bettor discipline. Our four-model ensemble analyzes 56 features per game across NBA, MLB, and WNBA, surfacing signals only when edge exceeds 3.5%. The behavioral layer, which tracks selectivity, capital preserved, and discipline scoring, is our primary differentiator and the foundation of long-term user retention.

---

# 16. COPY SYSTEM

## Screenshot Headlines (App Store, in order)

1. **Market Intelligence for Sports.** · Daily briefings. Edge detection. Line movement. Before you bet anything.
2. **One Pick Beats Five.** · The first sports market intelligence platform. NBA · MLB · WNBA
3. **See Where the Edge Disappears.** · Value range, cover probability, and the exact line where it stops being worth it.
4. **Your Discipline Is Your Edge.** · Track selectivity, capital preserved, and the bets that protected your bankroll.
5. **The Model Shows Its Work.** · 56 features. Four models. Full reasoning on every signal.
6. **Not Every Day Is a Betting Day.** · MEI tells you the market opportunity before you look at a single game.
7. **If It's Not Sharp, It's Not Sent.** · 3.5% minimum edge threshold. Below that, silence.
8. **Money Saved Compounds Too.** · See the bankroll impact of the bets you didn't take.
9. **Three Markets. One Standard.** · NBA. MLB. WNBA. Same model discipline across every sport.
10. **Signal Over Noise.** · Market intelligence, not market noise. Process over hype.

## Brand Copy Lines

**Tier 1 — Lead with these:**
- Market intelligence for sports.
- One pick beats five.
- If it's not sharp, it's not sent.
- Not a picks service. An intelligence platform.
- Signal over noise.

**Tier 2 — Section headers:**
- See where the edge disappears.
- Your discipline is your edge.
- The model shows its work.
- Not every day is a betting day.
- Money saved compounds too.
- Data decides. Always.

**Tier 3 — Body copy / social / Journal:**
- Fewer decisions, better decisions.
- The sharp side of the market.
- Process over hype.
- Edges only. Always.
- Where data meets conviction.
- Quantified edge or silence.
- Built for bettors who treat their bankroll like a portfolio.

---

# 17. TECH STACK

- Backend: Python/Flask + Gunicorn on Railway
- Database: PostgreSQL
- Frontend: Capacitor hybrid (iOS + Android)
- Landing page: Cloudflare Pages (sharppicks.ai)
- App: app.sharppicks.ai
- Fonts: Google Fonts (Inter, IBM Plex Serif, JetBrains Mono)
- Billing: Stripe (web-only)
- Push notifications: Firebase
- The || signal in HTML is two `<span>` elements, never actual pipe characters
- All transparent PNGs are Printful-upload-ready

---

*SharpPicks · sharppicks.ai · One pick beats five.*
