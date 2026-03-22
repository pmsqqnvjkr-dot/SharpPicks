# SHARPPICKS BRAND SPEC
# Last updated: March 2026 | Version 3.0
# Drop in project root. Cursor reads this for all brand/UI decisions.

---

## IDENTITY

- **Brand name:** SharpPicks (one word, capital S capital P)
- **Wordmark:** SHARP || PICKS (all caps, || signal bars as center divider)
- **App store name:** SharpPicks
- **Domain:** sharppicks.ai (app: app.sharppicks.ai)
- **Support:** support@sharppicks.ai
- **Sports:** NBA, MLB, WNBA

## TAGLINES

| Priority | Text | Usage |
|----------|------|-------|
| Primary | **One pick beats five.** | Hero, merch, social bios, marketing, OG image |
| Secondary | **Selective by design.** | Footer, landing page, supporting context |

- Render taglines: all caps, wide tracking (0.3em+), green (#5A9E72)

---

## COLORS

```css
:root {
  /* Primary */
  --sp-navy:     #111827;  /* rgb(17, 24, 39)    — primary bg, icon bg, text on light */
  --sp-white:    #E8EAED;  /* rgb(232, 234, 237) — signal bars, wordmark, UI text on dark */

  /* Accent */
  --sp-green:    #5A9E72;  /* rgb(90, 158, 114)  — positive signals, tagline, CTAs, edge detected */
  --sp-red:      #C4686B;  /* rgb(196, 104, 107) — negative signals, alerts, loss indicators */

  /* Extended */
  --sp-dark:     #0A0C10;  /* rgb(10, 12, 16)    — deep page bg */
  --sp-dark-card:#12151C;  /* rgb(18, 21, 28)    — card/surface bg */
  --sp-border:   #1E2230;  /* rgb(30, 34, 48)    — subtle borders */
  --sp-muted:    #5A6270;  /* rgb(90, 98, 112)   — muted text, secondary labels */
}
```

### Color usage rules
- Navy + white carry 90% of visual weight
- Green is ONLY for: accent, positive signals, tagline, CTAs, "edge detected" states
- Red is ONLY for: negative signals, alerts, loss indicators
- Never use green and red together as equal-weight elements (accessibility)

---

## TYPOGRAPHY

```css
:root {
  --sp-font-heading:  'IBM Plex Serif', Georgia, serif;
  --sp-font-body:     'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  --sp-font-mono:     'JetBrains Mono', 'IBM Plex Mono', 'Fira Code', monospace;
}
```

| Context | Font | Weight | Notes |
|---------|------|--------|-------|
| Wordmark | Inter | 500 (Medium) | uppercase, 0.25em tracking |
| Headlines | IBM Plex Serif | 600 | editorial, Sharp Journal, hero |
| Body | Inter | 400 | general UI, descriptions |
| Code/Data | JetBrains Mono or IBM Plex Mono | 400 | pick cards, data tables, command center |
| Tagline | Inter | 400 | uppercase, 0.3em+ tracking, green |
| Labels/Meta | IBM Plex Mono | 400-500 | small caps, wide tracking, muted color |

### CRITICAL: Never use Inter weight 300 (Light) for the wordmark.
Weight 300 fails on low-DPI screens, Android, and print/merch. Always 500.

---

## WORDMARK — SHARP || PICKS

### Specifications
- Font: Inter Medium (500)
- Case: ALL UPPERCASE
- Letter-spacing: 0.25em
- Signal bars (||): two vertical pill-shaped bars
- Bar width: matches text stroke weight (~3px at display size)
- Bar height: extends **12% beyond cap-height equally above AND below** the text
- Bar gap: ~0.22em between the two bars
- Bar border-radius: 50% of bar width (pill shape)
- Bar horizontal spacing: equal padding on both sides
- Minimum render width: 120px (below this, use icon only)

### CSS Implementation
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
  /* 12% overshoot above and below cap-height */
  height: 1.24em;
  background: currentColor;
  border-radius: 999px;
}

/* On light backgrounds */
.sp-wordmark--light .sp-wordmark__text { color: var(--sp-navy); }
.sp-wordmark--light .sp-wordmark__signal span { background: var(--sp-navy); }
```

### HTML
```html
<!-- Dark background (primary) -->
<div class="sp-wordmark">
  <span class="sp-wordmark__text">SHARP</span>
  <span class="sp-wordmark__signal"><span></span><span></span></span>
  <span class="sp-wordmark__text">PICKS</span>
</div>

<!-- Light background -->
<div class="sp-wordmark sp-wordmark--light">
  <span class="sp-wordmark__text">SHARP</span>
  <span class="sp-wordmark__signal"><span></span><span></span></span>
  <span class="sp-wordmark__text">PICKS</span>
</div>
```

### Wordmark with tagline
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
  font-size: 0.35em; /* relative to wordmark font-size */
}
```

---

## APP ICON (E1)

### Structure
- Background: var(--sp-navy) / #111827
- Two vertical bars: var(--sp-white) / #E8EAED
  - Width: ~3.8% of icon size
  - Height: ~34% of icon size
  - Border-radius: 50% of width (pill)
  - Centered, offset slightly above true center
- Green accent underscore: var(--sp-green) / #5A9E72
  - Width: ~15% of icon size
  - Height: ~1.2% of icon size
  - Centered below bars

### Export sizes
| File | Size | Use |
|------|------|-----|
| icon-1024.png | 1024×1024 | App Store / Play Store |
| icon-512.png | 512×512 | Marketing |
| icon-192.png | 192×192 | Android web manifest |
| icon-180.png | 180×180 | iOS touch icon |
| favicon-32.png | 32×32 | Browser favicon (no green accent) |
| favicon-16.png | 16×16 | Browser favicon (no green accent) |

### Notes
- iOS auto-applies squircle mask — submit square PNG
- Android: use as adaptive icon foreground layer on #111827 bg
- At 32px and below, omit the green accent (too small to render)

---

## SIGNAL MARK (||)

The || signal can be used standalone:
- Social avatars
- Favicons
- Loading/spinner states
- Watermarks
- Merch (hat, tumbler, sleeve)

Available as: signal-white-transparent.png, signal-navy-transparent.png, signal-green-transparent.png (512px), merch-signal-1000.png (1000px)

---

## ASSET FILES

```
brand-assets/
├── icon-1024.png                       # App Store / Play Store
├── icon-512.png                        # Marketing
├── icon-192.png                        # Android web manifest
├── icon-180.png                        # iOS touch icon
├── favicon-32.png                      # Browser favicon
├── favicon-16.png                      # Browser favicon
│
├── wordmark-white-on-navy.png          # Primary wordmark (3000×750)
├── wordmark-navy-on-white.png          # Reversed wordmark (3000×750)
├── wordmark-white-transparent.png      # Overlay use
├── wordmark-navy-transparent.png       # Overlay use
│
├── wordmark-tagline-white-on-navy.png  # With "One pick beats five" (3000×900)
├── wordmark-tagline-navy-on-white.png  # Reversed + tagline
├── wordmark-tagline-white-transparent.png
│
├── merch-wordmark-white-4000.png       # Print-ready 4000px wide, white, transparent
├── merch-wordmark-navy-4000.png        # Print-ready 4000px wide, navy, transparent
├── merch-wordmark-tagline-white-4000.png  # Print + tagline
│
├── signal-white-transparent.png        # || mark 512px
├── signal-navy-transparent.png         # || mark 512px
├── signal-green-transparent.png        # || mark 512px
├── merch-signal-1000.png              # Large print 1000px
│
├── social-og-1200x630.png            # OG card for link previews
├── tagline-green-transparent.png      # Standalone tagline (2400×300)
└── tagline-white-transparent.png      # Standalone tagline (2400×300)
```

---

## OG / META TAGS

```html
<meta property="og:title" content="SharpPicks — One pick beats five." />
<meta property="og:description" content="AI-driven sports betting analytics. NBA, MLB, WNBA." />
<meta property="og:image" content="https://sharppicks.ai/social-og-1200x630.png" />
<meta property="og:type" content="website" />
<meta name="twitter:card" content="summary_large_image" />
```

---

## USAGE RULES

1. Never rotate, stretch, or skew the wordmark or icon
2. Never change individual element colors (e.g., green bars + white text)
3. Never add drop shadows, outer glows, or 3D effects
4. Never place on busy or low-contrast backgrounds
5. Minimum clear space = height of || bars on all sides
6. Below 120px width, use icon only — not wordmark
7. The || bars must always match text optical weight
8. The || bars must extend equally above and below text cap-height (12% overshoot)

---

## BRAND AESTHETIC

- **Terminal/institutional** — not flashy, not consumer-sportsbook
- **Dark navy base**, understated, data-focused interfaces
- **Anti-tout philosophy**: let the model speak, never oversell
- **Comparable to**: Stripe, Bloomberg Terminal aesthetic
- **NOT comparable to**: FanDuel, DraftKings, BetMGM
- Prefer IBM Plex Serif for editorial weight, JetBrains Mono for data credibility
- Prefer restraint over decoration in all UI decisions

---

## TECH STACK CONTEXT (for Cursor)

- Backend: Python/Flask + Gunicorn on Railway
- DB: PostgreSQL
- Frontend: Capacitor hybrid (iOS + Android)
- Landing page: Cloudflare Pages (sharppicks.ai)
- App: app.sharppicks.ai
- Fonts: loaded via Google Fonts (Inter, IBM Plex Serif, IBM Plex Mono)
- Billing: Stripe (web-only)
- Push: Firebase
- The || signal in HTML is two `<span>` elements — never actual pipe characters
- All transparent PNGs are Printful-upload-ready
