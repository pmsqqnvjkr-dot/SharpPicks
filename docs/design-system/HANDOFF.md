# SharpPicks v4.3 Brand Migration — Handoff

**Owner:** Evan Cole / Erin Donnelly (founder)
**Operator:** Claude Code (autonomous with manual diff approval)
**Scope:** Both `~/Projects/SharpPicks` and `~/Projects/evan_cole_hq`
**Timeline:** 1-2 weeks, phased with WNBA launch (Fri May 8) as Priority 1
**Last updated:** May 6, 2026

---

## Table of contents

1. Context and goals
2. Brand system summary
3. The two-spec system (critical)
4. What you are migrating to v4.3
5. What is already done in v4.2
6. What NOT to touch
7. Repository layout
8. Files Evan handed off
9. Decision log (locked decisions you should not reopen)
10. Open questions (escalate to Evan)
11. Platform-conditional patterns
12. Debugging notes from the design pass
13. Brand audit checklist
14. Voice rules
15. How to ask for help

---

## 1. Context and goals

SharpPicks is a sports betting market intelligence platform. Not a sportsbook. Not a tipster service. The institutional voice (Bloomberg analyst, not ESPN personality) is the primary differentiator from every other sports betting account.

The brand system has gone through three patches in the past month:

- **v4.0 (April 2026)** — warm dark palette, mint Edge Green
- **v4.1 (early May)** — added Evan Cole title lock, voice rules tightened
- **v4.2 (mid May)** — Edge Green changed from mint `#34D399` to sage `#5A9E72` (more institutional, less SaaS)
- **v4.3 (late May)** — Wordmark geometry locked at M2 medium weight; two-spec system documented (wordmark uses M2, app icon uses light)

Your job is to migrate the **rendered surfaces** to match the v4.3 brand system. The CSS tokens may already be at v4.2 in some files. Verify before changing.

The institutional voice extends to interaction. No bouncy animations, no celebration confetti, no exclamation marks anywhere in copy. Every change should make the product feel MORE institutional, not less.

---

## 2. Brand system summary

The full system lives in `BRAND_SPEC.md` (v4.3) and `DESIGN_SYSTEM.md` (v1.1). Read both. Do not improvise.

**Color tokens (v4.3 locked):**

```css
--sp-bg:           #0A0D14;        /* warm dark */
--sp-surface:      #121725;        /* card surface */
--sp-surface-2:    #1B2030;        /* elevated surface */
--sp-border:       rgba(255, 255, 255, 0.08);
--sp-text:         #E8EAED;        /* sharp white */
--sp-text-2:       rgba(232, 234, 237, 0.7);
--sp-text-3:       rgba(232, 234, 237, 0.5);
--sp-blue:         #4F86F7;        /* signal blue (active signal only) */
--sp-green:        #5A9E72;        /* edge green (verified result, sage) */
--sp-amber:        #F59E0B;        /* calibration / live state */
--sp-negative:     #C4868A;        /* muted rose, never red */
--sp-navy:         #111827;        /* app icon background ONLY */
```

**Critical color rules:**

- **Signal Blue means "active signal."** Not for calibration framing, not for educational content. When you see Signal Blue on a surface, it should mean an active signal exists.
- **Edge Green means "positive result, verified."** For closing line wins, positive deltas, signal mark underline. Never for "active" framing.
- **Amber is the calibration color.** For "early-stage signal," "slate in progress," "live game," "first reads coming." Never for errors.
- **Negative is muted, not red.** `#C4868A` is desaturated rose. Losses do not deserve aggressive visual punishment.
- **Sharp Navy is restricted to the app icon background.** Do not use elsewhere.

**Typography:**

- IBM Plex Serif: hero headlines, editorial moments, principle quotes
- JetBrains Mono: numbers, units, ROI, stat values
- Inter: body text, UI, button labels, wordmark
- Courier New: uppercase eyebrow labels, status badges

**Common drift patterns to watch for (these will appear in old code):**

- `#34D399` (old mint green) — replace with `#5A9E72`
- `#F87171` (fire-truck red) — replace with `#C4868A`
- Em-dashes (`—`) in copy — replace with periods or split into two sentences
- "BETA" pills — replace with "Calibration v1" amber treatment
- Blue calibration banners — replace with amber calibration banner pattern
- Hard-coded hex values — replace with CSS variable references

---

## 3. The two-spec system (critical)

In v4.3, the wordmark and the app icon use **different bar weights by deliberate design**. Do not "harmonize" them.

**Wordmark and standalone signal mark — M2 medium weight:**
- Bar width: `0.12em`
- Bar height: `1.30em`
- Bar gap: `0.20em`
- Margin around signal cluster: `0 0.5em 0 0.22em` (asymmetric, optical correction)

**App icon — light weight:**
- Bars: `3.8%` width × `34%` height of icon
- Accent: `15%` width × `1.2%` height
- Below 40×40px: omit the accent

**Why the difference:** the app icon renders at notification-badge sizes (29×29px) where bar widths are measured in fractional pixels. Anything heavier than 3.8% turns into chunky rectangles. The wordmark renders in typographic contexts where M2 medium harmonizes with surrounding letter weight.

This is documented at length in `DESIGN_SYSTEM.md` section 8.3. If you find code that "fixes" what looks like an inconsistency between these two, that fix is wrong. Revert.

---

## 4. What you are migrating to v4.3

The redesigned mockups in the handoff folder show every surface that needs migration. Each maps to React/Capacitor components or Flask templates in the live codebases.

**iOS / Capacitor surfaces (in `~/Projects/SharpPicks`):**

| Mockup file | Maps to (probably) |
|---|---|
| `mlb-home-redesigned.html` | `<MLBHomeScreen />` or signals tab default view |
| `home-redesigned.html` | `<SignalsHomeScreen />` (NBA / generic) |
| `signal-card-redesigned.html` | `<DailyTopSignalCard />` |
| `market-intelligence-redesigned.html` | `<MarketIntelligenceReport />` |
| `wnba-prelaunch-page.html` | New component, build from scratch |
| `sharp-journal-mockup.html` | `<SharpJournalArticle />` morning variant |
| `sharp-journal-evening.html` | `<SharpJournalArticle />` evening variant |

**Email templates (in `~/Projects/SharpPicks/templates/emails/`):**

| Mockup file | Maps to |
|---|---|
| `email-master.html` | Base lifecycle email template (nested-table for Outlook compat) |
| `email-variants.js` | Variant content + Resend dispatcher logic |

**Web surfaces (in `~/Projects/evan_cole_hq`):**

The Sharp Journal articles ARE the market reports per the editorial system. Same content, different surfaces. Web routes:

- `/today` — Daily Market Scan tweet draft
- `/sharp-journal/[date]` — Article archive
- `/wnba` — Pre-launch landing (May 6-7), then redirects to `/sharp-journal/[date]` after Friday

---

## 5. What is already done in v4.2

The CSS tokens may already be partially migrated. Before changing anything, verify with:

```bash
# In each repo:
grep -r "#34D399\|52, 211, 153" --include="*.css" --include="*.tsx" --include="*.jsx" --include="*.swift" .
```

If you find old mint references, those need updating to `#5A9E72` / `90, 158, 114`.

The April 2026 cleanup also addressed:

- Sport tab active states (MLB blue, NBA orange)
- Sharp Journal evening edition mixed-state handling
- Tracking confirmation chip pattern
- Twitter teaser cards for WNBA launch (already rendered to PNG)

If these are working in production and look like the canonical mockups, leave them.

---

## 6. What NOT to touch

This is brand and UI work. Do not touch:

- **Backend signal computation logic.** The model code in `~/Projects/SharpPicks/sharp_picks/` (and the daily cron at 11:30 AM ET) is out of scope.
- **Postgres schemas.** The shared Railway DB schema is locked. Don't migrate, don't add columns.
- **SQLite at `/data/sharp_picks.db`.** Same. Read-only from your perspective.
- **Cron schedules.** Currently 11:30 AM ET market scan, 5:30 PM ET pre-game log, 11:30 PM ET closing line audit.
- **RevenueCat / Stripe webhook handlers.** Payment integration is sensitive. If a UI change requires a payment flow change, stop and ask.
- **Sign in with Apple / OAuth flows.** App Store rejection cycle was painful. Don't reopen.
- **API contracts.** Existing route shapes and response shapes stay stable. Add new endpoints if you need to. Don't rename or restructure existing ones.
- **Notification event system.** The push notification dispatch logic is out of scope.
- **The Evan Cole system prompt** at `docs/evan-cole-system-prompt.md`. Voice is locked.

If you are unsure whether something is in scope, ask before touching it.

---

## 7. Repository layout

**`~/Projects/SharpPicks` (Flask + Capacitor iOS):**

```
SharpPicks/
├── app.py                              # Flask main, blueprint registration
├── public_api.py                       # Public market report endpoint
├── sharp_picks/                        # Model logic (out of scope)
├── static/
│   ├── css/
│   │   └── tokens.css                  # CSS variable definitions (UPDATE THIS)
│   └── js/
├── templates/
│   ├── emails/                         # Email lifecycle templates (UPDATE THESE)
│   └── pages/
├── ios/
│   └── App/App/
│       ├── brand-tokens.swift          # Swift brand constants (UPDATE IF EXISTS)
│       └── Assets.xcassets/AppIcon.appiconset/  # App icon exports
└── docs/
    └── design-system/                  # Drop the handoff bundle here
```

**`~/Projects/evan_cole_hq` (Next.js 16 / Cloudflare Workers):**

```
evan_cole_hq/
├── app/
│   ├── layout.tsx                      # Root layout, brand colors injected
│   ├── page.tsx                        # Landing
│   └── sharp-journal/[date]/page.tsx   # Article reader
├── components/
│   ├── brand/                          # Wordmark, signal mark components
│   └── ui/                             # Cards, buttons, etc.
├── styles/
│   └── tokens.css                      # CSS variables (UPDATE THIS)
├── tailwind.config.ts                  # Theme configuration (UPDATE THIS)
└── docs/
    └── design-system/                  # Drop the handoff bundle here
```

---

## 8. Files Evan handed off

All in the handoff folder:

| File | Purpose |
|---|---|
| `START_HERE.md` | Quick orientation, the very first command to run |
| `HANDOFF.md` | This file |
| `MIGRATION_CHECKLIST.md` | Sequenced task list, you update as you go |
| `BRAND_SPEC.md` | v4.3 canonical brand system |
| `DESIGN_SYSTEM.md` | v1.1 complete design guide |
| `design-system.html` | Visual reference site |
| `marks.html` | Wordmark and signal mark visual reference |
| `tokens.css` | Universal CSS variables |
| `mlb-home-redesigned.html` | MLB home (free user paywalled state) |
| `home-redesigned.html` | Generic Signals home |
| `signal-card-redesigned.html` | Daily Top Signal card (unlocked) |
| `market-intelligence-redesigned.html` | Market Intelligence report |
| `wnba-prelaunch-page.html` | WNBA tab pre-launch state |
| `sharp-journal-mockup.html` | Sharp Journal morning edition |
| `sharp-journal-evening.html` | Sharp Journal evening edition |
| `email-master.html` | Email lifecycle template (master) |
| `email-preview.html` | All 7 email variants in one preview file |
| `email-variants.js` | Email content + Resend dispatcher |
| `RatePromptSheet.jsx` | Rate prompt React component |
| `card-1-announce.png` | WNBA launch teaser card 1 |
| `card-2-explain.png` | WNBA launch teaser card 2 |
| `card-3-preview.png` | WNBA launch teaser card 3 |
| `wnba-launch-tweets.md` | Friday May 8 launch tweet pack |
| `wnba-teaser-tweets.md` | May 6-7 teaser tweets paired with cards |

---

## 9. Decision log (locked decisions, do not reopen)

These were decided after extensive discussion. Do not propose changes:

- **Edge Green is `#5A9E72` sage**, not `#34D399` mint. v4.2 lock.
- **Wordmark uses M2 medium geometry** (`0.12em × 1.30em`, `0.20em` gap). v4.3 lock.
- **App icon uses light weight** (`3.8% × 34%`), intentionally different from wordmark. v4.3 lock.
- **Asymmetric margin around signal cluster** is `0 0.5em 0 0.22em`. Optical correction for letter-spacing imbalance. v4.3 lock.
- **Edge Green underline on standalone signal mark is non-negotiable.** Without it, the mark is a generic glyph.
- **Sharp Navy `#111827` is restricted to app icon background.** Not used elsewhere.
- **Tagline lockup pattern exists in spec** but should NOT appear in the design system reference site itself. Removed from design-system.html. Available as a documented pattern for marketing surfaces.
- **Negative color is muted rose `#C4868A`.** Not red. Losses do not get fire-truck treatment.
- **Withdrawn picks are blue, never red.** Capital was preserved when a pick was withdrawn. Positive framing.
- **Pass days use "capital preserved" framing.** Never "no signal" or "pass day" as primary framing.
- **Calibration phase uses amber.** Not blue. Signal Blue is for active signals only.
- **Sharp Journal articles ARE the market reports.** One content type, three routes into it (Signals tab links to morning article, Track tab links to game results, Journal tab is the archive).
- **Evan Cole title is "Head of Signal Intelligence" verbatim.** No variants.
- **No em-dashes, no exclamation marks, no emoji, no AI-speak, no hyphens-as-sentence-separators in any copy.**

---

## 10. Open questions (escalate to Evan)

These are unresolved. If you encounter them in code, ask before deciding:

1. **Bottom nav tab order.** Currently shipped: "Signals · Results · Insights · Account." Redesigned mockups reference: "Signals · Track · Journal · Account." Migrate to the new order or keep the old? Recommended: migrate AFTER WNBA launch, not during.

2. **Field Guide content backlog.** Only one Field Guide article exists. The home screen "While You Wait" rotator needs 4-5 articles minimum to feel meaningful. If you encounter the rotator, gracefully handle the single-article state.

3. **Founding Fifty perks.** Power User email references "locked pricing for life" and "private channel with founder." Verify before sending.

4. **OG images for Sharp Journal evening edition.** `og-report-evening.png` referenced but not designed. Generate at 1200×630 if you have time, otherwise document as gap.

5. **MEI scoring methodology.** Visible to users but never explained. Add explainer or escalate.

6. **Calibration thresholds.** When does a sport exit calibration? Documented internally as "validation threshold met" but threshold value not public. Recommended: publish them. Confirm with Evan first.

7. **App icon master file.** Need to verify the 1024×1024 master exists in `~/Projects/SharpPicks/ios/App/App/Assets.xcassets/AppIcon.appiconset/` and that all required exports (1024, 512, 256, 180, 167, 152, 120, 87, 80, 76, 60, 58, 40, 29, 20) are present.

---

## 11. Platform-conditional patterns

Some UI patterns must vary by platform. Centralize the conditional logic.

**Trial CTA copy:**

| Platform | Subtext under CTA button |
|---|---|
| Web (evan_cole_hq, marketing site) | "Card required · Cancel anytime" |
| Android (Capacitor + Stripe checkout) | "Card required · Cancel anytime" |
| iOS (Capacitor + RevenueCat IAP) | "Cancel anytime" (no card mention — Apple ID is implicit) |

The iOS path uses RevenueCat for IAP, which charges through the user's Apple ID. Mentioning "card required" on iOS is misleading because Apple may have multiple payment methods and the user doesn't enter card details. Web and Android both route to Stripe checkout where a card IS required.

Implement this as a platform check in the component:

```jsx
// Pseudocode
const ctaSubtext = Capacitor.getPlatform() === 'ios'
  ? 'Cancel anytime'
  : 'Card required · Cancel anytime';
```

Or for the marketing site (always web), hardcode "Card required · Cancel anytime."

**App icon accent omission:**

App icon at 40×40px and below: omit the Edge Green accent. The accent becomes too thin to render cleanly. iOS export pipeline should handle this in the Asset Catalog: provide accent-included versions for 60+, accent-omitted versions for 29 and 20.

**Sharp Journal cross-link visibility:**

The cross-link card (signal card → Sharp Journal article) should only render if a Sharp Journal article exists for that day. If no article published yet (early morning, before 11:30 AM ET cron), hide the cross-link. Don't show "Article coming soon."

---

## 12. Debugging notes from the design pass

Things that wasted time during the design work. Avoid these:

**Wordmark rendering inconsistency between browsers and PDF generators.** The flexbox `align-items: center` aligns to the lowercase x-height midline in some rendering engines (wkhtmltoimage, wkhtmltopdf, older WebKit), making the `||` bars hang low. Two implementations are documented:

- **Canonical (modern browsers):** `display: inline-flex` with `align-items: center`. Use this in React components.
- **Render-anywhere (PDF / image generators):** absolute positioning forcing cap-line-to-baseline placement. Use this for OG image generation, PDF reports, server-side image rendering.

Both implementations are in `BRAND_SPEC.md` v4.3 section "Wordmark."

**The marks.html file Evan provided originally had an encoding bug.** Every `var(--sp-...)` was rendered as `var(–sp-...)` (en-dashes from clipboard). The handoff version is fixed. If you receive any old marks.html copies, check for this.

**The WNBA pre-launch page model input weights are placeholders.** The "How the model thinks about WNBA" section shows weight bars (88%, 76%, 64%, 58%) for four inputs (pace differential, rest disadvantage, roster turnover, late line movement). These are placeholder values shaped by general WNBA betting market knowledge. Replace with actual model weights before launch, or generalize to qualitative bands ("primary input," "secondary input").

**The signal card paywalled state uses CSS `filter: blur(6px)`** on the stat values rather than `[Pro]` placeholders. This is more emotionally honest. A determined user could screenshot and squint to read the blurred values, but the risk of reverse-engineering a single signal is operationally low. If you want stricter security, replace blurred values with `••••` placeholders.

**Email templates use table-based standalone signal mark for Outlook compatibility.** Bars are `3px × 28px` (10.7% width-to-height ratio), slightly lighter than the canonical M2 standalone mark (`0.15em × 1em` = 15% ratio). This is a deliberate compensation for Outlook table-rendering which can make bars feel heavier than CSS would. Do not "fix" this to match the standalone mark spec.

**The "Welcome back, Support" bug** in the original screenshot suggests user's first name field is null or API returns "Support" as placeholder. The redesigned mockup uses just "Welcome back" without name interpolation. Check the auth payload before re-introducing the name.

---

## 13. Brand audit checklist

Run this before marking any task complete in `MIGRATION_CHECKLIST.md`:

- [ ] Colors come exclusively from `tokens.css` (no hardcoded hex values)
- [ ] Typography uses only the four locked families (IBM Plex Serif, JetBrains Mono, Inter, Courier New)
- [ ] Wordmark renders with M2 geometry (`0.12em × 1.30em`, `0.20em` gap)
- [ ] App icon uses light geometry (`3.8% × 34%`)
- [ ] Edge Green is `#5A9E72`, not `#34D399`
- [ ] Background `#0A0D14`, surface `#121725`
- [ ] No em-dashes in any copy
- [ ] No exclamation marks anywhere
- [ ] No emoji anywhere
- [ ] No hyphens as sentence separators
- [ ] No "L" badges on withdrawn picks
- [ ] Pass days use "capital preserved" framing, not "no signal"
- [ ] Calibration contexts use amber, not blue
- [ ] Active signal contexts use Signal Blue, not green
- [ ] Verified result contexts use Edge Green
- [ ] All tap targets ≥ 44×44px
- [ ] Color contrast meets WCAG AA on all text/surface pairs
- [ ] Evan Cole title is "Head of Signal Intelligence" verbatim
- [ ] Numbers are JetBrains Mono with proper formatting
- [ ] Diverging-axis bars used for any directional data
- [ ] Trial CTA copy is platform-conditional (iOS omits "card required")

---

## 14. Voice rules

Forbidden in all copy:

- Em-dashes (`—`). Use periods.
- Exclamation marks. Zero exceptions.
- Emoji. Anywhere. Ever.
- Hyphens as sentence separators. Use periods.
- AI-speak: "let's dive in," "happy to help," "great question," "it's worth noting."
- Capital letters for emphasis.
- Gambling slang: "lock," "hammer," "smash," "cash," "bag."
- Hype words: "incredible," "huge," "massive," "fire," "loaded."

Required posture:

- Bloomberg analyst, not ESPN personality.
- Specific over general: "10 of 14 edges on dogs" not "lots of underdog action."
- Falsifiable over vague: "The market catches up by Memorial Day" not "the market eventually adjusts."
- Short over long: cut every word that does not earn its place.

If you write copy, run it through these rules before committing.

---

## 15. How to ask for help

When you encounter something you cannot resolve:

1. **First, search the docs.** `BRAND_SPEC.md`, `DESIGN_SYSTEM.md`, this file. Time-cap at 10 minutes.
2. **If still stuck, check the mockups.** Open the relevant HTML file. The visual answer is usually there.
3. **If still stuck, post a question to Evan with this template:**

```
**Stuck on:** [one-sentence description]

**What I tried:**
- [search 1]
- [search 2]
- [mockup checked]

**The conflict / ambiguity:**
[concrete description]

**Two paths I see:**
1. [option A with tradeoff]
2. [option B with tradeoff]

**My recommendation:**
[your read]
```

4. **Stop work on the blocked task.** Move to the next item in `MIGRATION_CHECKLIST.md`. Do not improvise.

---

## End of handoff

Now open `MIGRATION_CHECKLIST.md` and start with item 1.
