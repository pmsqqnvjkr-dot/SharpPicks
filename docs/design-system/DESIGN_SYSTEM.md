# SharpPicks Design System

**Version:** 1.0
**Status:** LOCKED
**Last updated:** May 6, 2026
**Brand spec dependency:** BRAND_SPEC.md v4.2

---

## Foreword

This document is the canonical source of truth for how SharpPicks looks and feels across every surface — mobile app, web, email, social, and marketing. It supersedes prior partial documents (BRAND_SPEC.md, marks.html, tokens.css) and absorbs them as foundation chapters.

Every pattern documented here is locked. New patterns should be proposed by updating this document, not by improvising in code. When in doubt, this document wins.

The design system serves three audiences:

1. **You (Erin/Evan, founder)** — to make consistent product decisions without re-deriving rules each time
2. **Claude Code sessions** — to apply locked patterns without inventing variations
3. **Future contractors or designers** — to onboard without losing the institutional voice

---

## Table of Contents

**Part I — Foundation**
1. Brand positioning and voice
2. Color system
3. Typography
4. Spacing and layout
5. Iconography

**Part II — The wordmark and signal mark**
6. Wordmark geometry
7. Signal mark (the ||)
8. App icon
9. Usage rules

**Part III — Components**
10. Cards
11. Buttons and CTAs
12. Tags and pills
13. Stat displays
14. Tables
15. Bars and visualizations
16. Banners and notes
17. Navigation

**Part IV — Page patterns**
18. Sharp Journal article layout
19. Signal card layout
20. Market Intelligence report layout
21. Mobile home (Signals tab)
22. Pre-launch / Calibration tab states
23. Email lifecycle templates

**Part V — Content**
24. Voice rules
25. Headline patterns
26. Eyebrow labels
27. Numbers and units
28. Sharp Principles (locked content)
29. Evan Cole canonical attributes

**Part VI — System**
30. Calibration phase patterns
31. Live state and timing patterns
32. Empty states and pass days
33. Error states
34. Motion and animation
35. Accessibility

**Part VII — Operations**
36. File locations and source of truth
37. How to add new patterns
38. Brand audit checklist

**Part VIII — Open questions**
39. Known gaps and unresolved decisions

---

# PART I — FOUNDATION

## 1. Brand positioning and voice

SharpPicks is a sports betting market intelligence platform. It is NOT a sportsbook, NOT a tipster service, and NOT a hype-driven content brand.

The institutional voice is the moat. Every other betting account on Twitter sells lottery tickets ("LOCK OF THE NIGHT 🔒🔥"). SharpPicks shows the math. The audience SharpPicks earns by being disciplined is higher-quality than any audience earned by being loud.

**The register:** Bloomberg analyst, not ESPN personality.

**The promise:** Verified by data, not talk.

**The positioning summary in one sentence:** "We do not issue daily picks. We issue signals when the math says there is an edge, with full closing line audit on every read, including the misses."

---

## 2. Color system

### 2.1 Surfaces

| Token | Value | Usage |
|---|---|---|
| `--sp-bg` | `#0A0D14` | Outer page background, email body, root canvas |
| `--sp-surface` | `#121725` | Cards, modals, sheets, sections |
| `--sp-surface-2` | `#1B2030` | Elevated surface, bar tracks, inactive states |
| `--sp-border` | `rgba(255, 255, 255, 0.08)` | Default border on dark |
| `--sp-border-strong` | `rgba(255, 255, 255, 0.15)` | Emphasized border, dividers |

### 2.2 Brand colors

| Token | Value | Usage |
|---|---|---|
| `--sp-signal-blue` | `#4F86F7` | Active signals, primary CTA, links, navigation accent |
| `--sp-signal-blue-hover` | `#3D72E0` | CTA hover state |
| `--sp-edge-green` | `#5A9E72` | Verified results, positive deltas, signal mark underline |
| `--sp-edge-green-soft` | `rgba(90, 158, 114, 0.12)` | Edge Green tinted backgrounds |

**Critical color rules:**

- **Signal Blue means "active signal."** Never use it for calibration framing, never for educational content, never as decoration. When you see Signal Blue on a surface, it should mean an active signal exists.
- **Edge Green means "positive result, verified."** Used for closing line wins, positive deltas, and the wordmark underline. Never use for "active" framing — that is Signal Blue's job.

### 2.3 Text

| Token | Value | Usage |
|---|---|---|
| `--sp-text-primary` | `#E8EAED` | Body text, headlines, primary readable surface (Sharp White) |
| `--sp-text-secondary` | `rgba(232, 234, 237, 0.7)` | Subheads, descriptions |
| `--sp-text-tertiary` | `rgba(232, 234, 237, 0.5)` | Captions, secondary metadata |
| `--sp-text-quaternary` | `rgba(232, 234, 237, 0.35)` | Footer text, very low-emphasis |
| `--sp-text-muted` | `rgba(232, 234, 237, 0.25)` | Placeholder text, disabled |

### 2.4 Semantic colors

| Token | Value | Usage |
|---|---|---|
| `--sp-positive` | `#5A9E72` | Wins, gains, positive ROI (alias of Edge Green) |
| `--sp-negative` | `#C4868A` | Losses, errors, away-from-model moves (muted by design) |
| `--sp-warning` | `#F59E0B` | Calibration phase, live states, in-progress indicators |
| `--sp-warning-soft` | `rgba(245, 158, 11, 0.08)` | Calibration banner backgrounds |

**Critical semantic rules:**

- **Negative is muted, not red.** `#C4868A` is a desaturated rose, not a fire-truck red. Losses do not deserve aggressive visual punishment. The brand respects users who have a losing slate.
- **Warning amber is the calibration color.** Used for "early-stage signal," "slate in progress," "live game," and "first reads coming." Never use amber for errors. Errors are negative.
- **Never use red `L` badges on withdrawn picks.** Capital was preserved when a pick was withdrawn, that is positive framing. Use a neutral blue "Withdrawn" pill instead.

### 2.5 Sharp Navy (limited use)

| Token | Value | Usage |
|---|---|---|
| `--sp-navy` | `#111827` | App icon background ONLY |

Sharp Navy is restricted to the app icon background where it must hold against arbitrary home screen wallpapers. Do not use elsewhere.

---

## 3. Typography

### 3.1 Type stack

| Family | Use |
|---|---|
| `IBM Plex Serif` | Hero headlines, editorial moments, principle quotes (italic), section titles |
| `JetBrains Mono` | Numbers, units, ROI, stat values, percentages, line values |
| `Inter` | Body text, UI, button labels, wordmark |
| `Courier New` | Uppercase eyebrow labels, status badges, footer meta |

### 3.2 Weight rules

- **IBM Plex Serif headlines:** 600 (Semibold) for primary, 700 (Bold) for hero, 400 (Regular) for principle quotes
- **JetBrains Mono numbers:** 500 (Medium)
- **Inter body:** 400 (Regular), 500 (Medium) for buttons and emphasis, 600 (Semibold) for navigation labels
- **Inter wordmark:** 500 (Medium) — never 300, never 600
- **Courier New labels:** Regular weight, always uppercase, letter-spacing 0.18em–0.28em depending on size

### 3.3 Type scale

| Use | Family | Size | Weight | Tracking | Line height |
|---|---|---|---|---|---|
| Hero headline | IBM Plex Serif | 30–56px | 700 | -0.01em | 1.05–1.15 |
| Section title | IBM Plex Serif | 20–22px | 600 | -0.01em | 1.2–1.3 |
| Card title | IBM Plex Serif | 16–20px | 600 | normal | 1.3 |
| Body | Inter | 14–16px | 400 | normal | 1.5 |
| Subhead | Inter | 13–15px | 400 | normal | 1.45 |
| UI button | Inter | 14px | 600 | 0.01em | normal |
| Number / stat | JetBrains Mono | 14–32px | 500 | normal | 1 |
| Eyebrow label | Courier New | 9–13px | 500 | 0.18–0.28em | 1.2 |
| Footer meta | Courier New | 9–11px | 400 | 0.16–0.22em | 1.4 |

### 3.4 Type rules

- **Never mix Inter and IBM Plex Serif within a single sentence** unless one is a number (then use JetBrains Mono inline)
- **Eyebrows are always uppercase** with letter-spacing 0.18em or higher
- **Numbers are always JetBrains Mono** when displayed as data. Numbers within prose can use the surrounding font
- **Italic is reserved for emphasis within Sharp Principles and Observation blocks** — not for casual use

---

## 4. Spacing and layout

### 4.1 Spacing scale

Use multiples of 4px for spacing. Common values:

- 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 28, 32, 36, 40, 48, 56, 64

### 4.2 Padding rules by surface

| Surface | Outer padding | Inner padding |
|---|---|---|
| Mobile screen edge | 18–22px | n/a |
| Card | n/a | 18–22px |
| Card with header | n/a | 22px header, 22px body |
| Email body | 24px (mobile), 40px (desktop) | n/a |
| Section spacer | 28–36px between major sections | n/a |

### 4.3 Border radius

| Element | Radius |
|---|---|
| Cards | 12–16px |
| Buttons | 10px |
| Pills (tags, version badges) | 4px |
| Bars | 2–3px |
| Bar tracks | 2–3px |
| Avatar / status dots | 999px (full circle) |
| Modal sheets (mobile) | 20px top corners only |

### 4.4 Mobile container

- Max width: 480px
- Centered with subtle 1px border on left/right at `rgba(255,255,255,0.04)` for desktop preview only
- Safe area padding via `env(safe-area-inset-top)` and `env(safe-area-inset-bottom)`

---

## 5. Iconography

SharpPicks uses **stroke-based line icons** at 2px stroke width consistently. No filled icons except in specific high-emphasis contexts (active nav state).

**Source:** Lucide React (https://lucide.dev) is the canonical icon library. Do not mix icon libraries.

**Sizes:**
- Inline with body text: 14–16px
- Standalone in UI: 18–22px
- Hero or emphasis: 24px
- Bottom nav: 20px

**Color:**
- Default: `--sp-text-tertiary` (50% white)
- Active: `--sp-edge-green` or `--sp-signal-blue` depending on context
- Disabled: `--sp-text-quaternary`

**Critical rule:** Never use emoji in product UI. Voice rules apply — Bloomberg, not ESPN.

---

# PART II — THE WORDMARK AND SIGNAL MARK

## 6. Wordmark geometry

The locked wordmark is `SHARP || PICKS` in Inter 500, all caps, 0.25em letter-spacing, with the signal mark `||` set inline between SHARP and PICKS.

**Locked geometry (v4.3, M2 medium weight):**

- Bar width: `0.12em`
- Bar height: `1.30em` (15% overshoot above and below cap-height)
- Bar gap: `0.20em`
- Margin around signal cluster: `0 0.5em 0 0.22em` (asymmetric, optical correction)
- Border-radius: `999px` (full pill)

The asymmetric margin compensates for letter-spacing imbalance — the trailing edge of `P` (in SHARP) carries more visible space than the leading edge of `P` (in PICKS).

### 6.1 Canonical construction (modern browsers)

The canonical implementation uses `display: inline-flex` with `align-items: center`. Cleanest code, holds up reliably in any modern browser context.

```html
<span class="wordmark">
  <span class="wordmark__text">SHARP</span>
  <span class="wordmark__signal">
    <span class="wordmark__bars"><span></span><span></span></span>
    <span class="wordmark__underline"></span>
  </span>
  <span class="wordmark__text">PICKS</span>
</span>
```

```css
.wordmark {
  display: inline-flex;
  align-items: center;
  font-family: 'Inter', sans-serif;
  font-weight: 500;
  letter-spacing: 0.25em;
  line-height: 1;
  color: #E8EAED;
  text-transform: uppercase;
}

.wordmark__signal {
  position: relative;
  display: inline-flex;
  align-items: center;
  margin: 0 0.5em 0 0.22em;
}

.wordmark__bars {
  display: inline-flex;
  align-items: center;
  gap: 0.20em;
}

.wordmark__bars span {
  display: block;
  width: 0.12em;
  height: 1.30em;
  background: currentColor;
  border-radius: 999px;
}

.wordmark__underline {
  position: absolute;
  left: 50%;
  top: 100%;
  transform: translateX(-50%);
  margin-top: 0.06em;
  width: 0.5em;
  height: 0.07em;
  background: #5A9E72;
  border-radius: 999px;
}
```

### 6.2 Fallback construction (render-anywhere)

Use this when targeting PDF generators (`wkhtmltoimage`, `wkhtmltopdf`), server-side image renderers, or older WebKit. The flexbox `align-items: center` aligns to the lowercase x-height midline in these engines, making bars hang low. Absolute positioning forces cap-line-to-baseline placement.

```css
.wordmark {
  display: inline-block;
  font-weight: 500;
  letter-spacing: 0.25em;
  color: #E8EAED;
  line-height: 1;
  white-space: nowrap;
}
.wordmark > span { vertical-align: baseline; }

.wordmark__signal {
  position: relative;
  display: inline-block;
  margin: 0 0.5em 0 0.22em;
  vertical-align: baseline;
  width: 0.44em;             /* bars (0.12em × 2) + gap (0.20em) */
  height: 0;
}

.wordmark__bars {
  position: absolute;
  bottom: 0.02em;
  left: 0; right: 0;
  height: 0.85em;
}

.wordmark__bars .bar {
  position: absolute;
  top: 0; bottom: 0;
  width: 0.12em;
  background: currentColor;
  border-radius: 999px;
}
.wordmark__bars .bar:nth-child(1) { left: 0; }
.wordmark__bars .bar:nth-child(2) { right: 0; }

.wordmark__underline {
  position: absolute;
  left: 50%;
  bottom: -0.18em;
  transform: translateX(-50%);
  width: 0.5em;
  height: 0.07em;
  background: #5A9E72;
  border-radius: 999px;
}
```

### 6.3 Color rules

- On dark backgrounds: `SHARP` and `PICKS` in Sharp White `#E8EAED`, signal bars in Sharp White, underline in Edge Green `#5A9E72`
- On light backgrounds: `SHARP` and `PICKS` in Sharp Navy `#111827`, signal bars in Sharp Navy, underline in Edge Green `#5A9E72`

### 6.4 Tagline lockup (locked component)

When pairing the wordmark with a tagline:

- Text: "ONE PICK BEATS FIVE" (uppercase) — or rotates through Sharp Principles
- Font: Inter weight 400
- Letter-spacing: `0.35em`
- Color: Edge Green `#5A9E72`
- Size: 35% of wordmark font-size
- Position: centered below wordmark, gap of `1.4em` (relative to wordmark size)

### 6.5 Size rules

- Minimum render width: 120px total
- Below 120px: switch to standalone signal mark (see section 7)
- Common sizes: 18px (UI footer), 22–30px (mobile app header, email header), 60–88px (hero contexts)

### 6.6 Forbidden uses

- Do not change the letter-spacing
- Do not swap the `||` for a single `|` or three `|||`
- Do not remove the Edge Green underline
- Do not italicize
- Do not place on photographs without sufficient contrast
- Do not animate the wordmark itself (the underline can pulse for special states)
- Do not symmetrize the asymmetric margin around the signal cluster

---

## 7. Signal mark (the ||)

The two-bar pill cluster is THE SIGNAL — the standalone brand signature. Used as favicon, social avatar, watermark, and merchandise.

**Locked geometry (v4.3, slightly heavier than wordmark inline bars):**

- Bar width: `0.15em`
- Bar height: `1em`
- Gap between bars: `0.22em`
- Edge Green underline: `0.5em` wide, `0.07em` tall, `0.18em` margin-top, **always present**

The standalone signal mark uses bars `0.15em` wide rather than the wordmark's `0.12em` because the standalone context has no surrounding letterforms to provide visual weight. Without the heavier bar, a 24px favicon disappears.

### 7.1 Construction

```html
<span class="signal-mark">
  <span class="signal-mark__bars"><span></span><span></span></span>
  <span class="signal-mark__underline"></span>
</span>
```

```css
.signal-mark {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  color: #E8EAED;
  line-height: 1;
}

.signal-mark__bars {
  display: flex;
  gap: 0.22em;
  align-items: center;
}

.signal-mark__bars span {
  display: block;
  width: 0.15em;
  height: 1em;
  background: currentColor;
  border-radius: 999px;
}

.signal-mark__underline {
  width: 0.5em;
  height: 0.07em;
  background: #5A9E72;
  border-radius: 999px;
  margin-top: 0.18em;
}
```

### 7.2 The Edge Green underline is non-negotiable

Without the underline, the standalone signal mark is just a generic vertical-bars glyph. The underline is what distinguishes brand use. Never remove it on standalone usage.

### 7.3 Common sizes

| Size | Usage |
|---|---|
| 24px | Email footer, in-line UI marker |
| 40px | Avatar in compact contexts, mention chips |
| 64px | Profile circle, watermark |
| 96px | Loading state, splash screen |
| 160px+ | Hero, brand canvas |

---

## 8. App icon

The app icon uses **light bar weight by deliberate design**, intentionally different from the wordmark and standalone signal mark. This is the two-spec system locked in v4.3.

**Geometry (v4.3, light weight):**

- Background: Sharp Navy `#111827` (the only place this color appears in the system)
- Bars: Sharp White, `3.8%` width × `34%` height of icon
- Bar gap: `~3.9%` of icon width
- Edge Green accent: `15%` width × `1.2%` height, centered below bars
- Below 40×40px: omit the accent

```css
.app-icon {
  width: 1024px;              /* 1024 master, scale down for export */
  height: 1024px;
  background: #111827;        /* Sharp Navy */
  border-radius: 22.37%;      /* iOS standard */
  position: relative;
}

.app-icon__bars {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  gap: 3.9%;
}

.app-icon__bars span {
  width: 3.8%;
  height: 34%;
  background: #E8EAED;
  border-radius: 999px;
}

.app-icon__accent {
  position: absolute;
  bottom: 32%;
  left: 50%;
  transform: translateX(-50%);
  width: 15%;
  height: 1.2%;
  background: #5A9E72;
  border-radius: 999px;
}
```

### 8.1 Size rules

- Master size: 1024×1024
- Required exports: 1024, 512, 256, 180, 167, 152, 120, 87, 80, 76, 60, 58, 40, 29, 20
- **Below 40×40px: omit the Edge Green accent** (it becomes too thin to render cleanly)

### 8.2 Pixel reference table

| Size | Bar (W × H) | Accent (W × H) |
|---|---|---|
| 1024 | 39 × 348 | 154 × 12 |
| 512 | 19.5 × 174 | 77 × 6 |
| 256 | 9.7 × 87 | 38 × 3 |
| 128 | 4.9 × 44 | 19 × 1.5 |
| 96 | 3.7 × 33 | 14 × 1.2 |
| 64 | 2.5 × 22 | 9.5 × 1 |
| 40 | 1.6 × 14 | (omit) |
| 29 | 1.1 × 10 | (omit) |
| 20 | 0.8 × 7 | (omit) |

### 8.3 Why the two-spec system

This is the most important call-out in Part II. Read it carefully.

**The wordmark and standalone signal mark use M2 medium weight. The app icon uses light weight. Do not "harmonize" them.**

The reasoning:

- **App icon renders at fractional-pixel sizes.** At 29×29px (notification badge) the bar width is 1.1px. At 20×20px (Spotlight result) it is 0.8px. Anything heavier than 3.8% width turns these into chunky rectangles that lose typographic identity.
- **The wordmark and signal mark render in typographic contexts.** At 24–88px wordmark sizes, the bars sit next to letterforms with their own visual weight. M2 medium harmonizes with that letter weight without dominating. Light weight at 16–18px wordmark sizes (UI headers, email signatures) collapses visually.

These are different rendering contexts and need different geometry. A future contractor or designer should never "fix" what looks like an inconsistency — the inconsistency is the system.

### 8.4 Why Sharp Navy and not warmer black

The app icon must hold against arbitrary home screen wallpapers — bright photos, gradients, light themes. Sharp Navy `#111827` has a slight cool tint that reads as "deliberately dark" rather than blending into wallpaper darkness. Tested against ~30 common wallpaper photos.

---

## 9. Wordmark and signal mark usage rules

| Surface | Use |
|---|---|
| App icon | Standalone signal mark on Sharp Navy, with Edge Green accent below |
| Mobile app header | Wordmark at 18–22px Inter |
| Email header | Wordmark at 26–30px, centered or left-aligned |
| Twitter / social cards | Wordmark in card header, 20–30px |
| Favicon | Standalone signal mark |
| Avatar (X, social) | Standalone signal mark on solid Sharp Navy |
| Loading state / splash | Standalone signal mark, optionally with pulse animation on underline |

---

# PART III — COMPONENTS

## 10. Cards

Cards are the primary content container. Three card patterns are locked.

### 10.1 Standard card

```css
.card {
  background: var(--sp-surface);
  border: 1px solid var(--sp-border);
  border-radius: 14px;
  padding: 22px;
}
```

Used for: stat displays, observation blocks, generic content containers.

### 10.2 Accented card (with top accent line)

```css
.card-accented {
  background: var(--sp-surface);
  border: 1px solid var(--sp-border);
  border-radius: 14px;
  padding: 22px;
  position: relative;
  overflow: hidden;
}

.card-accented::before {
  content: '';
  position: absolute;
  top: 0;
  left: 20px;
  right: 20px;
  height: 2px;
  background: linear-gradient(90deg, transparent, var(--sp-edge-green) 20%, var(--sp-edge-green) 80%, transparent);
}
```

Used for: hero cards, daily top signal, primary content. The accent is Edge Green by default; use Signal Blue for active-signal contexts and amber for calibration contexts.

### 10.3 Bordered-left card (the "Observation" pattern)

```css
.card-observation {
  background: var(--sp-edge-green-soft);
  border-left: 2px solid var(--sp-edge-green);
  border-radius: 0 10px 10px 0;
  padding: 18px 20px;
}
```

Used for: Sharp Journal observation paragraphs, "Why this signal" blocks, implications, principle quotes. The left edge accent + tinted background is the "this is editorial commentary" signal across the system.

---

## 11. Buttons and CTAs

### 11.1 Primary button

```css
.btn-primary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 14px 16px;
  background: var(--sp-edge-green);
  border: none;
  border-radius: 10px;
  font-family: 'Inter', sans-serif;
  font-size: 14px;
  font-weight: 600;
  color: #062019;
  letter-spacing: 0.01em;
  cursor: pointer;
}
```

Used for: "Track this signal," "Notify me," "Subscribe." Edge Green background with very dark text for contrast (not Sharp White — too low contrast on green).

### 11.2 Secondary button (tracking confirmed state)

```css
.btn-tracking {
  background: rgba(90, 158, 114, 0.1);
  border: 1px solid rgba(90, 158, 114, 0.4);
  color: var(--sp-edge-green);
}
```

Used for: a button that has been activated and is now confirming state. The hollow outline + checkmark glyph indicates "this is done."

### 11.3 Ghost / tertiary button

```css
.btn-ghost {
  background: transparent;
  border: 1px solid var(--sp-border);
  color: var(--sp-text-secondary);
}
```

Used for: secondary actions, dismissals, "less" toggles.

### 11.4 Critical button rules

- **Buttons are always full-width on mobile** unless they are sizing toggles or paired actions
- **No exclamation marks in button copy** ever
- **Use verbs not adjectives:** "Track this signal" not "Awesome edge!"
- **Tracking state confirms what was tracked:** "Tracking · TEX +1.5 · 1.5u" not just "Tracking"

---

## 12. Tags and pills

Three pill patterns are locked.

### 12.1 Outlined tag (sport, content type, status)

```css
.tag-outlined {
  display: inline-flex;
  align-items: center;
  padding: 5px 11px;
  border: 1px solid var(--sp-edge-green);    /* color varies */
  border-radius: 4px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  font-weight: 500;
  letter-spacing: 0.20em;
  text-transform: uppercase;
  color: var(--sp-edge-green);               /* matches border */
}
```

Used for: "MLB", "NBA", "Slate Recap", "Calibration Phase", "Verified Result." Color varies by context — green for content tags, amber for calibration phase, blue for active signal indicator.

### 12.2 Solid pill (count badges, status)

```css
.pill-solid {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  background: rgba(79, 134, 247, 0.12);     /* tinted by context */
  border-radius: 999px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  font-weight: 500;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--sp-signal-blue);             /* matches tint */
}
```

Used for: navigation tabs, count badges, soft status indicators.

### 12.3 Result pill (Win / Loss / Push / Withdrawn)

```css
.pill-result-win {
  background: rgba(90, 158, 114, 0.1);
  border: 1px solid rgba(90, 158, 114, 0.3);
  color: var(--sp-edge-green);
}
.pill-result-loss {
  background: rgba(196, 134, 138, 0.1);
  border: 1px solid rgba(196, 134, 138, 0.3);
  color: var(--sp-negative);
}
.pill-result-push {
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid var(--sp-border);
  color: var(--sp-text-secondary);
}
.pill-result-withdrawn {
  background: rgba(79, 134, 247, 0.08);
  border: 1px solid rgba(79, 134, 247, 0.25);
  color: var(--sp-signal-blue);
}
```

**Critical rule: Withdrawn picks are blue, not red.** Capital was preserved when a pick was withdrawn — that is positive framing. Never use loss styling for withdrawn picks.

---

## 13. Stat displays

### 13.1 N-up stat grid

The locked pattern for displaying 3–5 related stats horizontally:

```css
.stat-grid {
  display: grid;
  grid-template-columns: 1fr 1px 1fr 1px 1fr 1px 1fr;   /* 4-up with dividers */
  background: var(--sp-surface);
  border: 1px solid var(--sp-border);
  border-radius: 14px;
  overflow: hidden;
}
.stat-cell {
  padding: 18px 12px 16px;
  text-align: center;
}
.stat-divider { background: var(--sp-border); }
.stat-eyebrow {
  font-family: 'JetBrains Mono', monospace;
  font-size: 9px;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--sp-text-tertiary);
  margin-bottom: 8px;
}
.stat-value {
  font-family: 'IBM Plex Serif', Georgia, serif;
  font-size: 32px;
  font-weight: 700;
  color: var(--sp-edge-green);
  line-height: 1;
  letter-spacing: -0.02em;
  margin-bottom: 6px;
}
.stat-suffix {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: var(--sp-text-tertiary);
}
```

**Rules:**
- 3-up for headline summaries (MEI / Regime / Top Edge)
- 4-up for secondary breakdowns (Net / Record / CLV / Beat)
- Dividers between cells using 1px columns at `--sp-border` color
- Eyebrows always uppercase Courier mono
- Values in IBM Plex Serif at 28–32px
- Suffix in JetBrains Mono for context units ("of 100", "single signal")

---

## 14. Tables

Tables in SharpPicks are mostly read-only data displays. The locked pattern uses borderless rows separated by 1px dividers, with the option for "significant" rows to receive a left-edge accent.

### 14.1 Standard table row

```css
.table-row {
  padding: 12px 16px;
  border-bottom: 1px solid var(--sp-border-2);
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 10px;
  align-items: center;
}
.table-row:last-child { border-bottom: none; }
```

### 14.2 Significant row (large move, sharp move, signal fired)

```css
.table-row-significant {
  background: var(--sp-edge-green-soft);
  border-left: 2px solid var(--sp-edge-green);
  padding-left: 14px;
}
.table-row-significant.away {
  background: rgba(196, 134, 138, 0.06);
  border-left-color: var(--sp-negative);
}
```

Used for: moneyline movements ≥20¢, signal-fired games, anything the eye should catch first.

### 14.3 Critical table rules

- **Never use alternating row backgrounds** ("zebra striping"). The dividers are sufficient.
- **Significant rows are subtle** — a tinted background and 2px left accent, not loud color blocks
- **Numbers right-aligned, labels left-aligned**, always

---

## 15. Bars and visualizations

The diverging-axis bar is the SIGNATURE visualization pattern across SharpPicks. Used in Edge Map, Model vs Market Delta, Bias indicator, and Signal Card edge display.

### 15.1 Diverging bar

```css
.bar-track {
  position: relative;
  height: 8px;
  background: var(--sp-surface-2);
  border-radius: 2px;
  overflow: hidden;
}
.bar-track::after {
  content: '';
  position: absolute;
  left: 50%;
  top: -2px;
  bottom: -2px;
  width: 1px;
  background: var(--sp-text-muted);
}
.bar-fill {
  position: absolute;
  top: 0;
  bottom: 0;
  border-radius: 2px;
}
.bar-fill.pos { left: 50%; background: var(--sp-edge-green); }
.bar-fill.neg { right: 50%; background: var(--sp-negative); }
.bar-fill.zero {
  left: calc(50% - 1px);
  width: 2px;
  background: var(--sp-text-tertiary);
  border-radius: 0;
}
```

**Rules:**
- Center axis ALWAYS visible (1px line at `--sp-text-muted`)
- Positive fills extend RIGHT from center
- Negative fills extend LEFT from center
- Zero state shows a small marker at center, not an empty bar
- Bar height 7–12px depending on context

### 15.2 Single-direction progress bar

For things that only go one direction (calibration progress, MEI score, weight indicators):

```css
.progress-bar {
  height: 6px;
  background: var(--sp-surface-2);
  border-radius: 3px;
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  background: var(--sp-edge-green);
  border-radius: 3px;
}
```

### 15.3 Gradient scale bar (with marker)

For things measured against a known scale (MEI 0–100, confidence levels):

```css
.scale-bar {
  position: relative;
  height: 6px;
  background: linear-gradient(90deg,
    rgba(196, 134, 138, 0.3) 0%,
    rgba(245, 158, 11, 0.3) 50%,
    rgba(90, 158, 114, 0.3) 100%);
  border-radius: 3px;
}
.scale-marker {
  position: absolute;
  top: -3px;
  width: 4px;
  height: 12px;
  background: var(--sp-edge-green);
  border-radius: 2px;
  transform: translateX(-50%);
}
```

The gradient communicates "low → medium → high" without requiring the user to read axis labels.

---

## 16. Banners and notes

### 16.1 Calibration banner (locked pattern)

```html
<div class="banner-calibration">
  <div class="banner-pulse"></div>
  <div class="banner-content">
    <div class="banner-eyebrow">Calibration Phase</div>
    <div class="banner-text">Edges tracked live. Confidence intervals widen during early-season validation. Closing line audit publishes on every signal.</div>
  </div>
</div>
```

```css
.banner-calibration {
  background: var(--sp-warning-soft);
  border: 1px solid rgba(245, 158, 11, 0.22);
  border-radius: 10px;
  padding: 14px 16px;
  display: flex;
  align-items: flex-start;
  gap: 12px;
}
.banner-pulse {
  flex-shrink: 0;
  width: 8px;
  height: 8px;
  margin-top: 4px;
  background: var(--sp-warning);
  border-radius: 50%;
  animation: pulse 2s infinite;
}
@keyframes pulse {
  0%   { box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.6); }
  70%  { box-shadow: 0 0 0 8px rgba(245, 158, 11, 0); }
  100% { box-shadow: 0 0 0 0 rgba(245, 158, 11, 0); }
}
.banner-eyebrow {
  font-family: 'JetBrains Mono', monospace;
  font-size: 9px;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--sp-warning);
  margin-bottom: 4px;
}
.banner-text {
  font-size: 12px;
  line-height: 1.45;
  color: var(--sp-text-secondary);
}
```

This pattern is used everywhere a "live / in-progress / calibration" state needs to be communicated. Same visual vocabulary across signal cards, Sharp Journal evening edition, market intelligence reports, and the WNBA pre-launch page.

### 16.2 Live indicator (inline, smaller)

```css
.live-indicator {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--sp-warning);
}
.live-indicator::before {
  content: '';
  width: 6px;
  height: 6px;
  background: var(--sp-warning);
  border-radius: 50%;
  animation: pulse 2s infinite;
}
```

Used for: in-line "Live · B7" inning state in Edge Map, "Live signals" footer markers.

---

## 17. Navigation

### 17.1 Bottom tab nav (mobile)

```css
.bottom-nav {
  position: fixed;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 100%;
  max-width: 480px;
  background: rgba(10, 13, 20, 0.95);
  backdrop-filter: blur(20px);
  border-top: 1px solid var(--sp-border);
  padding: 10px 0 calc(10px + env(safe-area-inset-bottom));
  display: flex;
  justify-content: space-around;
}
.bn-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  color: var(--sp-text-tertiary);
  font-family: 'JetBrains Mono', monospace;
  font-size: 9px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  padding: 6px 14px;
  position: relative;
}
.bn-item.active { color: var(--sp-edge-green); }
.bn-item.active::before {
  content: '';
  position: absolute;
  top: -10px;
  width: 24px;
  height: 2px;
  background: var(--sp-edge-green);
  border-radius: 0 0 2px 2px;
}
```

**Locked tab order:** Signals · Track · Journal · Account

(Note: the current shipped version shows "Signals · Results · Insights · Account." The redesigned home and signal cards reference the new "Signals · Track · Journal · Account" order. This is an open decision — see Open Questions section.)

### 17.2 Sport tabs (top of Signals screen)

```css
.sport-tabs {
  display: flex;
  gap: 6px;
}
.sport-tab {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  padding: 8px 14px;
  border-radius: 999px;
  color: var(--sp-text-tertiary);
}
.sport-tab.active.nba    { background: rgba(255, 138, 0, 0.12); color: #FF8A00; }
.sport-tab.active.mlb    { background: rgba(79, 134, 247, 0.12); color: var(--sp-signal-blue); }
.sport-tab.active.wnba   { background: rgba(255, 138, 0, 0.12); color: #FF8A00; }
```

Sport-specific accent colors are locked: MLB blue, NBA/WNBA orange.

---

# PART IV — PAGE PATTERNS

## 18. Sharp Journal article layout

The locked structure for any Sharp Journal article (morning or evening edition):

1. **Nav bar** — back arrow + "SHARP JOURNAL" mono caps title
2. **Live banner** (only if mixed state) — pulsing amber banner
3. **Meta row** — content tag (e.g., "Slate Recap"), section name, edition, read time
4. **Headline** — IBM Plex Serif, 30–32px, line height 1.1
5. **Date line** — JetBrains Mono, format "May 6, 2026 · 11:47 PM ET"
6. **Byline** — Author name + "·" + "Head of Signal Intelligence"
7. **Article divider** — 1px horizontal rule
8. **Observation** — section eyebrow + IBM Plex Serif body
9. **Stat cards** — 4-up Slate Result grid, Bias bar, Top Edge with explainer
10. **Edge Map** — diverging-axis bar list of all games
11. **Closing Line Audit** — table with verdict pills
12. **Near Misses** — list with edge values
13. **Implication** — bordered-left card with green accent dot
14. **Sharp Principle** — italic IBM Plex Serif quote
15. **Cross-edition link** — to morning OR evening counterpart
16. **Auto-refresh note** (evening only, mixed state)

Each section has a fixed eyebrow color: green for editorial sections, amber for live-state sections, blue for cross-content links.

## 19. Signal card layout

The Daily Top Signal card has a strict section order:

1. **Header** — sport tag, calibration version tag (if applicable), matchup
2. **Pick row** — pick text in IBM Plex Serif + edge percentage in JetBrains Mono
3. **Game time + price** — JetBrains Mono detail line
4. **First-pitch chip** — pulsing amber countdown chip
5. **4-cell stat grid** — Market / Model / Tier / Size
6. **Observation block** — bordered-left card explaining the signal
7. **Diverging edge bar** — with -10pp / 0 / +10pp scale
8. **Calibration disclosure** (if applicable) — amber tinted note
9. **Playability range** — target + floor with marker
10. **Sizing block** — Flat + Kelly with toggle
11. **Market context** — single sentence about slate-wide pattern
12. **Signal reasoning** — collapsed accordion (expanded on tap)
13. **Market timing footer** — "2h before tip · Best at BetMGM"
14. **Track button** — primary green CTA
15. **Sharp Journal cross-link** (separate card below) — link to today's morning report

## 20. Market Intelligence report layout

Article-styled market data report:

1. **Nav bar** — "MARKET INTELLIGENCE" caps title
2. **Article meta** — sport tag, "Market Report" subtitle, game count
3. **Article title** — IBM Plex Serif headline summarizing the regime
4. **Date line** — JetBrains Mono "May 6, 2026 · Updated 11:00 AM ET"
5. **Calibration banner** (if model in calibration)
6. **3-up headline grid** — MEI / Regime / Top Edge
7. **MEI scale strip** — gradient bar with marker showing today's score in context
8. **Edge breakdown** — proportional bar + 3-cell legend (Signals / Qualifying / Below)
9. **Observation** — bordered-left summary
10. **Section: Moneyline Movement** — table of every game with movement annotation
11. **Movement summary** — Toward / Away / No movement counts
12. **Section: Model vs Market Delta** — diverging bars sorted by magnitude with "below threshold" divider
13. **Footer summary** — "Avg model-market delta: 0.7 runs"
14. **Sharp Journal cross-link** — to today's morning article
15. **Footer meta** — last update + next refresh time

## 21. Mobile home (Signals tab)

The home screen "Signals" tab structure:

1. **Status bar + nav bar** — sport tabs (NBA/MLB/WNBA) + bell + clock icons
2. **Market Pulse strip** — 3-cell stat strip (pass days / last signal / CLV 30d)
3. **Daily recap card** — combined recap (replaces double-negative pass-day cards)
4. **Upcoming slate countdown** — game count + tipoff time
5. **Daily Top Signal** — full signal card if signal exists, else "No signal cleared the threshold"
6. **Market Intelligence preview** — 2-line summary linking to full report
7. **While You Wait — 3-card stack:**
   - Card 1: "What the model is watching" (tonight's slate preview)
   - Card 2: Sharp Journal entry from Evan Cole
   - Card 3: Field Guide article rotator
8. **Last night's read CTA** — full-width card linking to Sharp Journal evening edition

## 22. Pre-launch / Calibration tab states

For sports where the model has not yet shipped signals (pre-launch state), the tab displays:

1. **Status bar + nav bar**
2. **Countdown strip** — pulsing amber "Signals go live · 2 days until tipoff"
3. **Hero** — calibration phase tag + IBM Plex Serif headline
4. **First reads card** — timeline of what publishes on launch day
5. **"How the model thinks about [SPORT]"** — 4 numbered inputs with weight bars
6. **"Meet the model" methodology card** — 3-cell stat row + IBM Plex Serif body
7. **Comparison block** — "What other accounts do" vs "What we are doing"
8. **Sample format preview** — locked Calibration Log preview
9. **Notify CTA** — "Get notified when the first signal fires"
10. **Footer principle** — "Calibration phase. Live signals. Receipts tracked publicly."

This pattern is reusable for any future sport that enters calibration phase.

## 23. Email lifecycle templates

All transactional and lifecycle emails use the same master template (`email-master.html`):

1. **Header** — wordmark with `||` signal mark and Edge Green underline (built as nested tables for Outlook compatibility — never CSS-only divs)
2. **Hero** — IBM Plex Serif headline + body paragraph
3. **Optional content blocks** — stat grid, link card, principle quote
4. **CTA button** — Edge Green primary button
5. **Footer** — Sharp Principle + unsubscribe + List-Unsubscribe headers

Variants are content-only — same master, different merge tokens.

---

# PART V — CONTENT

## 24. Voice rules

### 24.1 Forbidden in all copy

- **No em-dashes.** Use periods instead.
- **No exclamation marks.** Zero exceptions.
- **No emoji.** Anywhere. Ever.
- **No hyphens-as-sentence-separators.** Use periods.
- **No AI-speak.** "Let's dive in," "happy to help," "great question," "it's worth noting" — banned.
- **No capital letters for emphasis.**
- **No gambling slang.** No "lock," no "hammer," no "bag," no "smash," no "cash."
- **No hype words.** No "incredible," "huge," "massive," "fire," "loaded."

### 24.2 Required posture

- **Bloomberg analyst, not ESPN personality.**
- **Specific over general.** "10 of 14 edges on dogs" not "lots of underdog action."
- **Falsifiable over vague.** "The market catches up by Memorial Day" not "the market eventually adjusts."
- **Short over long.** Cut every word that does not earn its place.

## 25. Headline patterns

### 25.1 The four locked headline structures

1. **Declarative observation** — "Two signals on the board. Three games still running on the West Coast."
2. **Question framing** — "Is the edge holding up?"
3. **Subject + state** — "Active regime, moderate opportunity."
4. **Subject + verb** — "WNBA signals go live."

### 25.2 Critical headline rules

- IBM Plex Serif at 700 weight
- Line height 1.05–1.15 depending on size
- Letter-spacing -0.01em to -0.02em (tightening)
- Periods at end of complete sentences (yes, periods are required)
- No subheadings within a single headline — break into two sentences if needed

## 26. Eyebrow labels

Eyebrow labels precede every section title or content block. They are functional metadata, not decoration.

### 26.1 Locked eyebrow inventory

- `OBSERVATION` — green, precedes editorial commentary
- `IMPLICATION` — green, precedes a takeaway
- `SHARP PRINCIPLE` — gray/tertiary, precedes a locked principle quote
- `CALIBRATION PHASE` — amber, precedes calibration-state content
- `OPENING NIGHT` — amber, precedes first-game-of-season content
- `MARKET SIGNAL` — green, precedes signal-fired summary
- `MARKET CONTEXT` — gray/tertiary, precedes slate-wide pattern
- `MARKET INTELLIGENCE` — green, precedes a market report
- `SLATE RESULT` — green, precedes outcome stats
- `SAMPLE FORMAT` — green, precedes a preview-only example
- `WHAT TO EXPECT` — blue, precedes timeline content

### 26.2 Eyebrow construction

- Always uppercase
- Always Courier New or JetBrains Mono
- Letter-spacing 0.18em–0.28em depending on size
- Color matches semantic context (see inventory)
- Optional preceding dot (●) for emphasis on calibration / live states

## 27. Numbers and units

### 27.1 Format rules

- **Percentages:** "+6.0%" not "+6.00%" — one decimal for edges
- **Edge points:** "+6.0pp" — "pp" suffix for percentage-point differences
- **Units:** "1.5u" lowercase u, no space
- **Currency:** "+204¢" not "+$2.04" for line moves under $10
- **Scores:** "TOR 4-3" not "Toronto 4 Minnesota 3"
- **Dates:** "May 6, 2026" or "Fri May 8" — never numeric like "5/6/26"
- **Times:** "11:47 PM ET" — always include timezone
- **Spreads:** "+1.5" with explicit sign, even for favorites ("-1.5")

### 27.2 Critical number rules

- **JetBrains Mono for all data numbers**
- **Never abbreviate units in stat displays** ("units" not "u" in eyebrows, "u" only inline with values)
- **Always show the sign** on edges, deltas, and movements (+6.0%, -2.8%)

## 28. Sharp Principles (locked content)

These are functional copy across product, marketing, and email. They never change.

- One pick beats five.
- Discipline is the edge.
- Verified by data, not talk.
- Pass days are not missed opportunities. They are proof the system is working.
- No edge, no pick.
- Calibration phase. Live signals. Receipts tracked publicly. *(WNBA-specific, season 2026)*

## 29. Evan Cole canonical attributes

The Evan Cole AI operator is the editorial voice of SharpPicks. Locked:

- **Name:** Evan Cole
- **Title:** Head of Signal Intelligence
- **Voice:** Bloomberg analyst, institutional, data-forward
- **System prompt source of truth:** `docs/evan-cole-system-prompt.md`
- **Signature surfaces:** Sharp Journal bylines, transactional email signatures, X bio, in-app journal entries

The title "Head of Signal Intelligence" supersedes any prior variants ("Founder," "Chief Analyst," "Senior Analyst," etc.). All future copy must use this exact title.

---

# PART VI — SYSTEM

## 30. Calibration phase patterns

When a model is in calibration phase (early-season validation, expansion sport, new methodology):

### 30.1 Visual indicators

- **Color:** Amber `#F59E0B` for all calibration framing
- **Tag pattern:** Outlined amber pill with "CALIBRATION PHASE" or "CALIBRATION v1" label
- **Banner pattern:** Amber-tinted banner with pulsing dot (see section 16.1)
- **Suffix on signals:** Status pills read "Signal · Calibration" instead of just "Signal"

### 30.2 Content patterns

Required language:
- "Calibration phase. Live signals. Receipts tracked publicly." (footer mantra)
- "Confidence intervals widen during early-season validation."
- "Closing line audit publishes on every signal."

Required disclosures:
- Banner appears on every signal card during calibration
- Banner appears on Market Intelligence reports during calibration
- Banner appears on Sharp Journal articles during calibration

### 30.3 Lifecycle

When does calibration end?

- A model exits calibration after meeting the validation threshold defined per sport
- Threshold is documented per sport in `docs/calibration-thresholds.md` (separate spec)
- When calibration ends, the amber tag and banner stop rendering — no migration needed beyond a feature flag flip

## 31. Live state and timing patterns

### 31.1 Time markers

- **Pre-game:** "First pitch in 5h 36m" — pulsing amber chip
- **In-progress:** "Live · B7" with pulsing amber dot inline
- **Settled:** "Final · TOR 4-3" in JetBrains Mono
- **Pending grading:** "Push" or specific outcome pill

### 31.2 Mixed-state handling

When a slate is partially settled (some games done, some live):

- **Pulsing amber banner** at top: "X of Y games settled. Numbers below are preliminary and update as remaining games close."
- **"Preliminary · X of Y"** marker on every aggregate stat that depends on full-slate data
- **Mixed Edge Map:** settled games show "Final · TOR 4-3", live games show pulsing amber dot + "Live · B7"
- **Dedicated "Still in progress" section** below the Edge Map listing live games individually
- **Auto-refresh footer note:** "● This report updates automatically when games settle"

This is the locked pattern from `sharp-journal-evening.html`.

## 32. Empty states and pass days

A "pass day" is a day where no signal cleared the threshold. SharpPicks treats this as **proof the system is working**, not as a failure.

### 32.1 Pass day card pattern

```html
<div class="card-accented">
  <div class="eyebrow-blue">Capital preserved</div>
  <h2 class="card-title">No signals cleared the threshold today.</h2>
  <p class="card-body">The slate did not produce edges meeting the discipline filter. Capital preserved for tomorrow.</p>
</div>
```

### 32.2 Critical rules

- **Eyebrow always reads "Capital preserved"** — never "No signal" or "Pass day" as the primary framing
- **Never use red** anywhere on a pass day card
- **Never combine multiple negative cards** ("Withdrawn" + "No Signal" + "Full Slate Results" is the old triple-negative pattern that was deprecated)
- **Always reference the Sharp Principle** within 1-2 sentences of any pass day messaging: "Pass days are not missed opportunities. They are proof the system is working."

## 33. Error states

Errors in SharpPicks are rare and should be handled with restraint, not panic.

### 33.1 Inline error pattern

```css
.error-inline {
  background: rgba(196, 134, 138, 0.06);
  border: 1px solid rgba(196, 134, 138, 0.25);
  border-radius: 8px;
  padding: 12px 14px;
  font-size: 13px;
  color: var(--sp-text-secondary);
}
```

Use `--sp-negative` `#C4868A` (muted rose), never a fire-truck red.

### 33.2 Connection / sync errors

When data is stale or connection is lost:
- Show a small pill in the page footer: "Last synced 11:00 AM ET · ●" (with red dot)
- Do not block UI rendering with cached data
- Include "Retry" affordance only after 30 seconds — early retries are noise

### 33.3 Critical error rules

- **Never use modal dialogs for transient errors**
- **Never use exclamation marks in error copy**
- **State what happened, then state what to do** — "Sync failed. Pull to refresh."
- **Errors in user input are not displayed in red** — use amber, since they are recoverable

## 34. Motion and animation

Motion in SharpPicks is restrained. The institutional voice extends to interaction — nothing bouncy, no spring physics, no parallax.

### 34.1 Locked animations

- **Pulse** (calibration / live indicator):
  ```css
  @keyframes pulse {
    0%   { box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.6); }
    70%  { box-shadow: 0 0 0 8px rgba(245, 158, 11, 0); }
    100% { box-shadow: 0 0 0 0 rgba(245, 158, 11, 0); }
  }
  ```
  2 second cycle, applied to amber dots only

- **Fade in** (page loads, modal opens):
  - 200ms ease-out
  - opacity 0 → 1, no transform

- **Slide up** (mobile sheets, signal card details expand):
  - 240ms ease-out
  - transform translateY(8px) → 0

### 34.2 Forbidden motion

- Bounce / spring physics
- Parallax scrolling
- Animated number counters (count-up effects)
- Hover lifts (translate / scale on hover)
- Loading spinners with brand colors (use a neutral 1px circle outline at `--sp-text-tertiary`)
- Confetti, particles, or celebration animations of any kind

## 35. Accessibility

### 35.1 Color contrast

Every text-on-surface combination must meet WCAG AA at minimum (4.5:1 for body, 3:1 for large text).

Verified compliant pairings:
- `#E8EAED` on `#0A0D14` — 16.3:1 (AAA)
- `#E8EAED` on `#121725` — 14.7:1 (AAA)
- `#5A9E72` on `#121725` — 4.7:1 (AA)
- `#4F86F7` on `#0A0D14` — 5.9:1 (AA)

Failing pairings to avoid:
- `#5A9E72` on `#0A0D14` for body text — 5.0:1, marginal. Use for accent/eyebrow only, not body.
- `#C4868A` on `#0A0D14` for body text — 5.4:1, acceptable for short labels but not extended copy

### 35.2 Touch targets

- Minimum 44×44px tap target on mobile (iOS HIG standard)
- Spacing: 8px minimum between adjacent tap targets

### 35.3 Critical accessibility rules

- **Never use color alone to convey meaning** — pair with icon, label, or position
- **All interactive elements have a visible focus state** — 2px outline at `--sp-signal-blue`
- **Reduced motion preference is respected** — `@media (prefers-reduced-motion: reduce)` disables pulse and slide animations
- **Status updates are announced to screen readers** via `aria-live="polite"` regions for live-state banners

---

# PART VII — OPERATIONS

## 36. File locations and source of truth

| Document | Location | Authority |
|---|---|---|
| This design system | `docs/design-system/DESIGN_SYSTEM.md` | Canonical |
| Brand spec (subset) | `docs/brand/BRAND_SPEC.md` | Subordinate to design system |
| CSS tokens | `static/css/tokens.css` (SharpPicks), `styles/tokens.css` (evan_cole_hq) | Subordinate |
| Wordmark / signal mark | `docs/brand/marks.html` | Subordinate, visual reference only |
| Evan Cole system prompt | `docs/evan-cole-system-prompt.md` | Linked, separate authority |
| Calibration thresholds | `docs/calibration-thresholds.md` | Linked, separate authority (TBD) |

When these documents conflict, this design system wins. Update subordinate documents to match.

## 37. How to add new patterns

When proposing a new pattern (new component, new banner, new icon usage):

1. **Check first** — is there an existing pattern that solves this? Default to reuse.
2. **If genuinely new** — propose by updating this document with:
   - The pattern name
   - The use case (one paragraph)
   - The locked construction (HTML + CSS)
   - The forbidden uses (what NOT to do with this pattern)
   - The visual reference (link to the mockup file)
3. **Validate** — does it pass all voice rules? Does it use only locked color tokens? Does it work at mobile and desktop?
4. **Commit** — add a changelog entry with the date and reasoning

Proposing new patterns should feel slightly difficult. If a new pattern is being created, it should be because no existing pattern fits. The discipline is the moat.

## 38. Brand audit checklist

Run this checklist before shipping any new surface (mockup, code, marketing asset):

- [ ] Colors come exclusively from `tokens.css` (no hardcoded hex values)
- [ ] Typography uses only the four locked families
- [ ] Wordmark renders with proper geometry (locked construction from section 6.1)
- [ ] Edge Green is `#5A9E72`, not `#34D399` (v4.2 lock)
- [ ] Background is `#0A0D14`, surface is `#121725`
- [ ] No em-dashes in any copy
- [ ] No exclamation marks anywhere
- [ ] No emoji anywhere
- [ ] No hyphens as sentence separators
- [ ] No "L" badges on withdrawn picks
- [ ] No "weak" or "loss" framing on pass days — use "capital preserved"
- [ ] Calibration phase contexts use amber, not blue
- [ ] Active signal contexts use Signal Blue, not green
- [ ] Verified result contexts use Edge Green
- [ ] All interactive elements have 44×44px minimum tap targets
- [ ] Color contrast meets WCAG AA on all text/surface pairs
- [ ] Evan Cole title reads "Head of Signal Intelligence" verbatim
- [ ] Numbers are JetBrains Mono with proper formatting
- [ ] Diverging-axis bars used for any directional data (not full-width single-color bars)

---

# PART VIII — OPEN QUESTIONS

These are unresolved decisions captured honestly so they can be addressed deliberately rather than drift unresolved.

## 39. Known gaps and unresolved decisions

### 39.1 Bottom nav tab order

**Status:** Unresolved
**Conflict:** Currently shipped app shows "Signals · Results · Insights · Account." The redesigned home screen and signal card mockups from this design pass reference "Signals · Track · Journal · Account."

**The trade-off:** "Results" is established and users know it. "Track" is more action-oriented and aligns with the "Track this signal" CTA on signal cards. "Journal" is stronger than "Insights" because it ties to the Sharp Journal content brand.

**Recommendation:** Migrate to "Signals · Track · Journal · Account" but only after the WNBA launch is stable. Don't change UI navigation in the same week as a new sport launches.

### 39.2 Field Guide content backlog

**Status:** Critical gap
**The issue:** The While You Wait 3-card stack on the home screen includes a Field Guide article rotator. Currently only one Field Guide article exists ("A Field Guide to Surviving a Losing Streak"). To make the rotation feel meaningful, 4-5 more articles are needed.

**Suggested topics:**
- "Why pace differentials matter more in the W than in the NBA"
- "Reading WNBA injury reports — three signals the market reacts late to"
- "The anti-favorite bias in WNBA totals markets"
- "Closing line value, explained without math"
- "What 'discipline' actually means in sharp betting"

**Recommendation:** Generate 4 more Field Guide articles before the WNBA launch on May 8. Without them, users tap the rotator and see the same article repeatedly.

### 39.3 Founding Fifty perks

**Status:** Documented but unconfirmed
**The issue:** The Power User email variant references "locked pricing for the life of the subscription" and "private channel with the founder." These claims need to be verified against what's actually offered before the email ships.

**Action item:** Confirm the actual Founding Fifty perks before the next email send.

### 39.4 OG images for evening edition

**Status:** Referenced but not designed
**The issue:** The Sharp Journal evening edition template references `og-report-evening.png` for social sharing. This image doesn't exist yet.

**Action item:** Generate `og-report-morning.png` and `og-report-evening.png` at 1200×630 for social link previews. Use the same brand-locked rendering pipeline as the WNBA teaser cards.

### 39.5 Sport-specific accent colors

**Status:** Locked for MLB (blue), NBA/WNBA (orange). Future sports?
**The issue:** When SharpPicks adds NHL, NCAAB, or other sports, what accent color do they get?

**Recommendation:** Maintain the three-color base (blue/orange/orange currently) and consider:
- NHL: cyan / ice blue
- NCAAB: red
- Soccer: yellow / gold
- Tennis: green-yellow

Lock these the moment a new sport's calibration phase begins, not earlier.

### 39.6 Dark mode is the only mode

**Status:** Confirmed but documented for future consideration
**The issue:** SharpPicks ships dark-only. There is no light theme. This is intentional — the institutional aesthetic depends on the dark surfaces.

**Future consideration:** If a light mode is ever added (e.g., for accessibility, for printing reports), it must be designed from scratch. Inverting the dark theme will not work — it will produce a white-and-mint product that loses all institutional character. A light theme requires its own color system, which is a substantial design pass.

### 39.7 Loss framing precision

**Status:** Locked language, verify implementation
**The issue:** The design system says losses use muted rose `#C4868A` and never use red `L` badges on withdrawn picks. Verify the iOS app and Flask backend actually follow this rule across all loss contexts (Track tab, Results, Sharp Journal evening edition outcomes, email lifecycle templates).

**Action item:** Audit all "loss" rendering across the live codebase against this design system before the WNBA launch.

### 39.8 The MEI scoring methodology is opaque

**Status:** Visual treatment locked, methodology not documented for users
**The issue:** The MEI score (0-100) appears prominently on the Market Intelligence report, but users have no idea what 69 means or how it's computed. The `(i)` info tooltip is the only entry point.

**Recommendation:** Either (a) write a 2-3 sentence explainer that appears on first view (dismissible), or (b) add a Field Guide article titled "How to read the MEI score." The tooltip alone is not enough.

### 39.9 Calibration thresholds are not public

**Status:** Operational decision pending
**The issue:** When does WNBA exit calibration phase? Same question for MLB, NBA. The system says "calibration ends when validation threshold is met" but the threshold itself isn't documented in this spec — and it should be either documented in `docs/calibration-thresholds.md` or made transparently visible to users.

**Recommendation:** Decide whether calibration thresholds are a brand transparency feature (publish them) or an operational detail (keep internal). My read: publish them. It reinforces "verified by data, not talk."

### 39.10 The Signals tab vs. Sharp Journal split

**Status:** Architectural ambiguity
**The issue:** Today's Sharp Journal article is linked to from the signal card and the Market Intelligence report. But Sharp Journal articles ARE market reports (per the editorial system spec). Are they the same content with different framings, or different content surfaces?

**Recommendation (locked):** Sharp Journal articles ARE the market reports. The "Sharp Journal" name is the editorial brand applied to the existing market report URL. The Signals tab links to today's morning article. The Track tab links to specific game results. The Journal tab is the article archive. Three distinct routes into the same content.

This is documented in `sharp-journal-spec.md` but worth restating here as the architectural source of truth.

---

## End of design system v1.0

This document is the canonical source. When in doubt, this document wins. When this document is silent, propose an addition before improvising.

**Last reviewed:** May 6, 2026
**Next review trigger:** WNBA launch + 30 days, or any palette change, or any new component pattern
