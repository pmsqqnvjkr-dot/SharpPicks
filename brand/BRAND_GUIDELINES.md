# SharpPicks Brand Guidelines

---

## Identity

**Full Name:** SharpPicks
**Wordmark Format:** SHARP || PICKS
**Tagline:** Beat the market, not the scoreboard.
**Category:** Sports Market Intelligence Platform

---

## Logo & Crest

The SharpPicks crest is the primary brand mark. It is always used on a dark background.

| Asset | File | Usage |
|---|---|---|
| Crest (primary) | `images/crest.png` | App header, landing page, onboarding, social |
| App Icon — iOS | `images/app-icon-ios-1024.png` | App Store, 1024×1024 |
| App Icon — Android | `images/app-icon-android.png` | Play Store, adaptive icon |
| App Icon — Foreground | `images/app-icon-foreground.png` | Android adaptive foreground layer |
| App Icon — Round | `images/app-icon-round.png` | Android round icon variant |

### Logo Usage Rules

- Crest always appears on `#0A0D14` or darker background
- Ghosted crest (2-5% opacity) used as watermark on hero sections
- Minimum clear space: crest width × 0.5 on all sides
- Never place on light backgrounds, never recolor, never stretch

### Wordmark

```
SHARP || PICKS
```

- Font: Inter, 600 weight
- Letter spacing: 3.9px
- All uppercase
- The `||` divider is rendered at reduced opacity (0.5–0.65)

---

## Color Palette

### Primary Surfaces (Dark Theme Only)

| Token | Hex | Usage |
|---|---|---|
| `--bg-primary` | `#0A0D14` | Page background |
| `--surface-0` | `#0D1017` | Elevated sections |
| `--surface-1` | `#121725` | Cards, panels |
| `--surface-2` | `#161C2E` | Hover states, active cards |

### Text Hierarchy

| Token | Hex | Usage |
|---|---|---|
| `--text-primary` | `#EEF2FF` | Headlines, key data |
| `--text-secondary` | `#9AA3B2` | Body text, descriptions |
| `--text-tertiary` | `#6B7280` | Labels, captions, metadata |

### Semantic Colors

| Token | Hex | Usage |
|---|---|---|
| `--blue-primary` | `#4F7DF3` | CTAs, links, active states |
| `--blue-deep` | `#2F5FD6` | Gradients, pressed states |
| `--color-signal` / `--green-profit` | `#5A9E72` | Edge, signal, profit, positive |
| `--green-dark` | `#3D8B5E` | Signal glow, emphasis |
| `--color-loss` / `--red-loss` | `#9E7A7C` | Loss (muted — neutral log, not alarm) |
| `--gold-pro` | `#F59E0B` | Pro badge, founding member, amber accent |
| `--withdrawn` | `#8E9AAF` | Withdrawn/invalidated signals |

### Market Regime Colors

| Regime | Color | Hex |
|---|---|---|
| Exploitable / Mispriced Board | Green | `#34D399` |
| Active / Active Board | Amber | `#FBBF24` |
| Moderate / Moderate Board | Muted | `#9AA3B2` |
| Efficient / Tight Board | Dim | `#6B7280` |

### Borders & Strokes

| Token | Value |
|---|---|
| `--stroke-subtle` | `rgba(255, 255, 255, 0.08)` |
| `--stroke-muted` | `rgba(255, 255, 255, 0.12)` |

---

## Typography

### Font Stack

| Role | Font Family | Weights | CSS Variable |
|---|---|---|---|
| Headlines & Philosophy | **IBM Plex Serif** | 400, 500, 600, 700 | `--font-serif` |
| Body & UI | **Inter** | 300–900 | `--font-sans` |
| Data & Numbers | **JetBrains Mono** | 400, 500, 600, 700 | `--font-mono` |

### Type Scale

| Token | Size | Usage |
|---|---|---|
| `--text-hero` | 28px | In-app hero headlines |
| `--text-card-title` | 18px | Card headers, section titles |
| `--text-metric` | 14px | Key numbers, data values |
| `--text-number` | 14px | Monospaced data |
| `--text-caption` | 12px | Supporting text |
| `--text-label-size` | 11px | Uppercase labels, metadata |

### Landing Page Scale (responsive)

| Element | Size |
|---|---|
| Hero headline | `clamp(32px, 4.5vw, 52px)` |
| Section headlines | `clamp(24px, 3vw, 36px)` |
| Subheadline | `clamp(15px, 1.4vw, 18px)` |

### Typography Rules

- Headlines always in IBM Plex Serif
- Philosophical/italic lines in IBM Plex Serif italic
- All data, percentages, records, edge values in JetBrains Mono
- Uppercase labels: JetBrains Mono, 700 weight, letter-spacing 0.08–0.14em
- Body copy: Inter, 400 weight, line-height 1.65–1.7
- Use `tabular-nums` for numeric columns

---

## Brand Voice & Messaging

### Category Line

> **Sports Market Intelligence**

This appears above the hero headline in uppercase monospace — it anchors the category before the reader sees anything else.

### Hero Headline

> **Beat the market, not the scoreboard.**

This is the single most important line. It appears as the largest text on the landing page and defines the brand position: market intelligence, not gambling.

### Core Taglines

| Line | Context |
|---|---|
| *Selective by design.* | Landing page, onboarding, social bios |
| *One pick beats five.* | Discipline filter, landing, social |
| *No edge, no pick.* | Market Intelligence, discipline filter, social |
| *Discipline is the product.* | Onboarding, journal, social headers |

### Footer Trinity (always together)

> Beat the market, not the scoreboard.
> One pick beats five.
> No edge, no pick.

### Product Description

> SharpPicks analyzes sports betting markets like a trading desk — identifying pricing inefficiencies, measuring probability gaps, and generating signals only when real edges appear.

### Short Bio

> Sports market intelligence. Selective by design.

### Daily Social Post Format

```
SharpPicks Market Scan

8 games analyzed
4 edges detected
3 signals generated
5 games passed

No edge. No pick.
```

---

## Brand Vocabulary

| Use | Don't Use |
|---|---|
| Signals | Picks, Locks, Plays |
| Market Intelligence | Betting tips, Predictions |
| Quant Analysis | Model likes, Model says |
| Edge | Lock of the night |
| Passed / No Action | Skip |
| Discipline Filter | — |
| Market Regime | — |
| Cover probability | Chance to win |
| Closing Line Value (CLV) | — |
| Signal generated | Pick released |

---

## Tone

- **Institutional, not promotional** — Bloomberg, not DraftKings
- **Restrained, not hype** — "Edge detected" not "LOCK OF THE CENTURY"
- **Analytical, not emotional** — Data-first language
- **Confident, not loud** — Let the numbers speak
- **Founder voice** — Evan Cole writes journal entries as a practitioner, not a marketer

---

## Design Principles

1. **Dark theme only** — `#0A0D14` base, always
2. **Data-focused visuals** — No flashy sports graphics, no team logos
3. **Minimal color** — Green for signal, blue for CTA, everything else is grayscale
4. **Right-aligned numerics** — All data columns right-aligned (trading terminal convention)
5. **Monospace for data** — Every number, percentage, and stat in JetBrains Mono
6. **Whitespace is a feature** — Let sections breathe

### Design References

The product should feel like:
- Bloomberg Terminal
- Stripe Dashboard
- Linear.app
- Koyfin

Not like: sports betting apps, tout services, or gambling platforms.

---

## Spacing & Elevation

| Token | Size |
|---|---|
| `--space-xs` | 4px |
| `--space-sm` | 8px |
| `--space-md` | 16px |
| `--space-lg` | 24px |
| `--space-xl` | 32px |

| Shadow | Value | Usage |
|---|---|---|
| `--shadow-card` | `0 2px 8px rgba(0,0,0,0.20)` | Standard cards |
| `--shadow-signal` | `0 4px 16px rgba(0,0,0,0.35)` | Signal/highlight cards |

---

## Journal Article Format

All journal content follows this template:

- `##` for section headers (not `###`)
- `---` horizontal rules between sections
- `> **CALLOUT TITLE**\n>\n> Callout body text.` for blockquote callouts
- Flowing prose paragraphs (no choppy single-line sentences)
- Author signature: `*Evan Cole*\nFounder, SharpPicks`
- Categories: `philosophy`, `discipline`, `how_it_works`, `market_notes`

---

## App Store / Play Store

**App Name:** SharpPicks (one word, no space)

**Short Description:**
> Sports market intelligence. Selective by design.

**Tone:** No gambling language. No "locks." No dollar amounts in the UI. Position as analytics/intelligence, not a betting tool.

---

## Images Directory

```
brand/
├── BRAND_GUIDELINES.md    ← this file
└── images/
    ├── crest.png                  ← Primary logo mark
    ├── app-icon-ios-1024.png      ← iOS App Store icon (1024×1024)
    ├── app-icon-android.png       ← Android adaptive icon
    ├── app-icon-foreground.png    ← Android foreground layer
    └── app-icon-round.png         ← Android round variant
```
