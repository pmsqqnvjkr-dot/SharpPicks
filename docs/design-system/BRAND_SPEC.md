# SharpPicks Brand Specification

**Version:** 4.3
**Status:** LOCKED
**Last updated:** May 2026
**Supersedes:** v4.2 (May 2026)

---

## Changelog

### v4.3 — May 2026 (patch)

**Wordmark + signal mark geometry refined to medium weight.** The v4.2 construction used absolute positioning with `0.13em × 0.85em` bars (a wkhtmltoimage-driven workaround). After A/B testing heavy `0.16em × 1.35em` against light `0.08em × 1.24em` and three medium intermediates, **M2 medium weight `0.12em × 1.30em` is locked** for the wordmark and standalone signal mark.

**Two-spec system explicitly documented.** The wordmark/signal mark and the app icon now use different bar weights by deliberate design:

- **Wordmark + standalone signal mark:** medium weight (`0.12em × 1.30em`, `0.20em` gap)
- **App icon:** light weight (`3.8% × 34%` of icon dimensions)

The rationale: app icons render at notification-badge sizes (29×29px) where bar widths are measured in fractional pixels. Anything heavier than 3.8% width turns into chunky rectangles that lose typographic identity at small sizes. Wordmarks render in typographic contexts where bar weight should harmonize with surrounding letter weight, which medium achieves better than light.

**Construction approach:** the canonical implementation uses `display: inline-flex` with `align-items: center` (cleanest code, modern browsers). A documented absolute-positioning fallback exists for render-anywhere contexts (PDF generators, server-side image renderers, older WebKit). See section "Wordmark" for both implementations.

**Other v4.3 fixes:**

- Asymmetric margin around signal cluster locked: `0 0.5em 0 0.22em`. The right margin is larger than the left because letter-spacing adds more visible space on the trailing edge of `P` (in SHARP) than the leading edge of `P` (in PICKS).
- Tagline lockup added to canonical components: "ONE PICK BEATS FIVE" in Inter 400, 0.35em tracking, Edge Green, sized at 35% of wordmark font-size.

### v4.2 — May 2026 (patch)

**Edge Green color refined.** Reverted from the saturated mint `#34D399` (introduced in v4.0) to a more institutional sage `#5A9E72` (originally from v3.0). The mint read as generic SaaS/fintech. It is the default Tailwind emerald-400 and appears in nearly every product in the category. Sage green carries a Bloomberg terminal register that aligns with the brand's institutional positioning.

This is a **green-only change**. The warmer v4 background and surface tokens are unchanged. All other tokens unchanged.

**Color changes from v4.1:**

- Edge Green `#34D399` → `#5A9E72` (sage, restored from v3 palette)
- Edge Green muted `rgba(52, 211, 153, 0.4)` → `rgba(90, 158, 114, 0.4)`
- Positive (semantic alias) `#34D399` → `#5A9E72`

**Why this works against the warmer surface:** The v3 sage was originally tested against the cold v3 background `#0A0C10` and surface `#12151C`. Against the warmer v4 surfaces (`#0A0D14` / `#121725`), the sage retains its institutional character without feeling drab. The warm neutrals carry the energy that the saturated mint was previously providing.

**Files updated in this migration:**

- All CSS uses of `#34D399` → `#5A9E72`
- All rgba `52, 211, 153` → `90, 158, 114`
- iOS Swift brand constants (if present)
- Marks document
- Email templates
- All app surface mockups

### v4.1 — May 2026 (patch)

Added Evan Cole canonical attributes section. Title locked as "Head of Signal Intelligence" across all surfaces. Added "no hyphens-as-sentence-separators" to voice rules — surfaced during May 2026 Sharp Journal article audit where headlines were using ` - ` as a substitute for em-dashes (still violates the spirit of the no-em-dash rule).

### v4.0 — May 2026

Reverted the color palette to the warmer system originally locked in April 2026. The v3.0 (March 2026) institutional revision read as cold and over-corrected in passive contexts — email inboxes, social previews, and ad placements specifically. The warmer palette tested better as a brand surface and was already the system of record in the iOS app and the SharpPicks Flask backend.

**Color changes from v3:**

- Background `#0A0C10` → `#0A0D14` (warmer black with blue undertone)
- Surface `#12151C` → `#121725` (warmer card surface)
- Edge Green `#5A9E72` → `#34D399` (saturated mint, restored)
- Signal Blue restored as `#4F86F7` (was absent in v3)
- Sharp White `#E8EAED` retained from v3 — proven easier on the eyes than pure white
- Sharp Navy `#111827` retained from v3 — used only in marks document, not as primary background

**Unchanged from v3:**

- Wordmark geometry (Inter 500, 0.25em tracking, bar proportions)
- Typography stack (IBM Plex Serif, JetBrains Mono, Inter, Courier New)
- Sharp Principles (locked content)
- Voice rules (no em-dashes, no exclamation marks, no AI-speak, no hype)
- Signal mark || construction and standalone usage rules

### v3.0 — March 2026 (deprecated)

Institutional palette revision. Deprecated in v4.

### v2.0 — April 2026

Initial locked brand system with Signal Blue and Edge Green. The warmer system v4 returns to.

---

## Color tokens

### Surfaces

| Token | Value | Usage |
|---|---|---|
| `--sp-bg` | `#0A0D14` | Outer page background, email body, root canvas |
| `--sp-surface` | `#121725` | Cards, modals, sheets, sections |
| `--sp-surface-2` | `#1B2030` | Elevated surface (hover, nested cards) |
| `--sp-border` | `rgba(255, 255, 255, 0.08)` | Default border on dark |
| `--sp-border-strong` | `rgba(255, 255, 255, 0.15)` | Emphasized border, dividers |

### Brand colors

| Token | Value | Usage |
|---|---|---|
| `--sp-signal-blue` | `#4F86F7` | Primary CTA, links, brand accent |
| `--sp-signal-blue-hover` | `#3D72E0` | CTA hover state |
| `--sp-edge-green` | `#5A9E72` | Verified results, positive deltas, signal underline |
| `--sp-edge-green-muted` | `rgba(90, 158, 114, 0.4)` | Inactive Edge Green (borders, low-emphasis) |

### Text

| Token | Value | Usage |
|---|---|---|
| `--sp-text-primary` | `#E8EAED` | Body text, headlines, primary readable surface (Sharp White) |
| `--sp-text-secondary` | `rgba(232, 234, 237, 0.7)` | Subheads, descriptions |
| `--sp-text-tertiary` | `rgba(232, 234, 237, 0.5)` | Captions, secondary metadata |
| `--sp-text-quaternary` | `rgba(232, 234, 237, 0.35)` | Footer text, very low-emphasis |
| `--sp-text-muted` | `rgba(232, 234, 237, 0.25)` | Placeholder text, disabled |

### Semantic

| Token | Value | Usage |
|---|---|---|
| `--sp-positive` | `#5A9E72` | Wins, gains, positive ROI (Edge Green) |
| `--sp-negative` | `#F87171` | Losses, errors |
| `--sp-warning` | `#FBBF24` | Caution states, used sparingly |

### Sharp Navy (limited use)

| Token | Value | Usage |
|---|---|---|
| `--sp-navy` | `#111827` | Brand marks document only, not used as primary surface |

---

## Typography

| Family | Use |
|---|---|
| `IBM Plex Serif` | Hero headlines, editorial moments, principle quotes (italic) |
| `JetBrains Mono` | Numbers, units, ROI, stat values |
| `Inter` | Body text, UI, button labels, wordmark |
| `Courier New` | Uppercase labels, status badges, eyebrows, footer meta |

Weight rules:

- IBM Plex Serif headlines: 500 (Medium) for primary, 400 for principle quotes
- JetBrains Mono numbers: 500 (Medium)
- Inter body: 400 regular, 500 for buttons and emphasis
- Inter wordmark: 500 (Medium) — never 300, never 600
- Courier New labels: regular weight, always uppercase, letter-spacing 0.18em–0.28em depending on size

---

## Wordmark

The locked wordmark is `SHARPPICKS` in Inter 500, all caps, 0.25em letter-spacing, with the signal mark `||` set inline between SHARP and PICKS.

### Bar geometry — M2 medium (locked v4.3)

- **Width:** `0.12em`
- **Height:** `1.30em` (15% overshoot above and below cap-height equally)
- **Gap between bars:** `0.20em`
- **Border-radius:** `999px` (full pill)

### Margins around the signal cluster

The signal cluster uses asymmetric margin: `margin: 0 0.5em 0 0.22em`.

The right margin is larger than the left because letter-spacing adds more visible space on the trailing edge of `P` (in SHARP) than the leading edge of `P` (in PICKS). This is an optical correction. Do not symmetrize.

### Canonical implementation (modern browsers)

Use `display: inline-flex` with `align-items: center`. Cleaner code, hold up reliably in any modern browser context.

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

### Fallback implementation (render-anywhere)

Use this when targeting PDF generators (`wkhtmltoimage`, `wkhtmltopdf`), server-side image renderers, or older WebKit. The flexbox `align-items: center` aligns to the lowercase x-height midline in these engines, making bars hang low. Absolute positioning forces cap-line-to-baseline placement.

```css
.wordmark {
  display: inline-block;
  font-weight: 500;
  font-size: 30px;
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
  left: 0;
  right: 0;
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

### Color rules

- On dark backgrounds: Sharp White `#E8EAED`
- On light backgrounds: Sharp Navy `#111827`
- Tagline (when locked up): Edge Green `#5A9E72`, Inter 400, 0.35em tracking, 35% of wordmark size

### Tagline lockup (locked component)

When pairing the wordmark with a tagline:

- **Text:** "ONE PICK BEATS FIVE" (uppercase)
- **Font:** Inter weight 400
- **Letter-spacing:** `0.35em`
- **Color:** Edge Green `#5A9E72`
- **Size:** 35% of wordmark font-size
- **Position:** Centered below wordmark, gap of `1.4em` (relative to wordmark size)

### Sizing rules

- **Minimum render width:** 120px. Below that, switch to standalone signal mark.
- **Common sizes:** 18px (UI footer), 22–30px (mobile app header, email header), 60–88px (hero contexts)

---

## Signal mark (the ||)

The two-bar pill cluster is THE SIGNAL — the standalone brand signature. Used for favicons, social avatars, watermarks, and merchandise.

### Geometry — M2 medium (locked v4.3)

- **Bar width:** `0.15em` (slightly heavier than wordmark inline bars to compensate for the standalone context)
- **Bar height:** `1em`
- **Gap:** `0.22em`
- **Edge Green underline:** `0.5em` wide, `0.07em` tall, `0.18em` margin-top, **always present**

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

### The Edge Green underline is non-negotiable

Without the underline, the standalone signal mark is just a generic vertical-bars glyph. The underline is what distinguishes brand use. Never remove it on standalone usage.

---

## App icon

Background: Sharp Navy `#111827` (kept for icon legibility against home screens).

### Geometry — light weight (locked v4.3, intentionally different from wordmark)

The app icon uses **light bar weight** by deliberate design. At notification-badge sizes (29×29px) and tab icon sizes (60×60px), bar widths are measured in fractional pixels. Anything heavier than 3.8% width turns into chunky rectangles that lose typographic identity. The two-spec system is the institutional move.

- **Bars:** Sharp White, `3.8%` width × `34%` height of icon, centered slightly above true center
- **Edge Green accent:** `15%` width × `1.2%` height, centered below bars
- **Below 40×40px:** omit the Edge Green accent

### Pixel reference (master 1024 → exports)

Required exports: 1024, 512, 256, 180, 167, 152, 120, 87, 80, 76, 60, 58, 40, 29, 20.

| Size | Bar dimensions | Accent dimensions |
|---|---|---|
| 1024 | 39 × 348 | 154 × 12 |
| 512 | 19.5 × 174 | 77 × 6 |
| 256 | 9.7 × 87 | 38 × 3 |
| 128 | 4.9 × 44 | 19 × 1.5 |
| 96 | 3.7 × 33 | 14 × 1.2 |
| 64 | 2.5 × 22 | 9.5 × 1 |
| 40 | 1.6 × 14 | (omit accent) |
| 29 | 1.1 × 10 | (omit accent) |
| 20 | 0.8 × 7 | (omit accent) |

### Why the two-spec system

- **App icon:** must hold structural identity at sizes where bars are 1–2 pixels wide. Light weight survives. Medium would chunk.
- **Wordmark + signal mark:** rendered in typographic contexts where bar weight harmonizes with surrounding letter weight. Medium has presence without dominating.

This is documented as a deliberate two-spec brand decision. Do not "harmonize" the wordmark and app icon weights. They serve different rendering contexts and need different geometry.

---

## Sharp Principles (locked content)

These are functional copy across the product, marketing, and email. They never change.

- One pick beats five.
- Discipline is the edge.
- Verified by data, not talk.
- Pass days are not missed opportunities. They are proof the system is working.
- No edge, no pick.

---

## Voice rules (locked)

- No em-dashes
- No exclamation marks (zero exceptions)
- No emoji
- No hyphens-as-sentence-separators — use periods
- No AI-speak ("let's dive in," "happy to help," "great question," "it's worth noting")
- No capital letters for emphasis
- No gambling slang (no "lock," no "hammer," no "bag")
- No hype words

Bloomberg analyst, not ESPN personality.

---

## Evan Cole — locked attributes

The Evan Cole AI operator is the editorial voice of SharpPicks. The following attributes are locked and do not vary by surface (in-app, email, Sharp Journal, X, ad copy):

- **Name:** Evan Cole
- **Title:** Head of Signal Intelligence
- **Voice:** Bloomberg analyst, institutional, data-forward
- **System prompt source of truth:** `docs/evan-cole-system-prompt.md`
- **Signature surfaces:** Sharp Journal bylines, transactional email signatures, X bio, in-app journal entries

The title "Head of Signal Intelligence" supersedes any prior variants ("Founder," "Chief Analyst," "Senior Analyst," etc.). All future copy must use this exact title.

---

## Files affected by v4 migration

- `~/Projects/SharpPicks/static/css/tokens.css` — update CSS variables
- `~/Projects/SharpPicks/ios/App/App/brand-tokens.swift` — update Swift constants if present
- `~/Projects/evan_cole_hq/styles/tokens.css` or `tailwind.config.ts` — update theme
- `docs/brand/marks.html` — backgrounds rolled to `#0A0D14` / `#121725`
- `docs/brand/BRAND_SPEC.md` — this file
- Email templates — already on warmer palette, no change required
