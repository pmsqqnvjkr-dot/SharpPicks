# SharpPicks v4.3 Migration Checklist

**Operator:** Claude Code
**Update protocol:** Mark `[x]` when a task is complete. Add a verification note (one line) under each completed item.
**Order matters:** Earlier items unblock later ones. Do not skip ahead.

---

## How to use this checklist

Each task has the same structure:

```
- [ ] **Task name** (priority · estimated effort)
  - Surface: which repo and component path
  - Acceptance:
    1. Specific testable criteria
    2. Specific testable criteria
  - Depends on: previous task ID, if any
  - Notes: anything Claude Code should know
```

Acceptance criteria must ALL pass before checking the box. The audit checklist in `HANDOFF.md` Section 13 also applies to every task.

---

## Pre-flight (do this before starting Priority 1)

- [ ] **0.1 Read the handoff package end-to-end** (P0 · 30 min)
  - Files: `START_HERE.md`, `HANDOFF.md`, `BRAND_SPEC.md`, `DESIGN_SYSTEM.md`
  - Acceptance:
    1. You can articulate the two-spec system without looking
    2. You can name all four locked typeface families and their uses
    3. You can list the six locked color tokens by purpose
  - Notes: If you cannot pass acceptance, re-read. Do not start migration without context.

- [ ] **0.2 Verify both repos clone cleanly and build** (P0 · 15 min)
  - Surface: both repos
  - Commands:
    ```bash
    cd ~/Projects/SharpPicks && git status && python -m flask run --port 5001
    # In separate shell:
    cd ~/Projects/evan_cole_hq && git status && pnpm dev
    ```
  - Acceptance:
    1. Flask app starts on `:5001` without errors
    2. Next.js dev server starts on `:3000` without errors
    3. Both repos are on a feature branch (not main)
  - Notes: If either fails, stop and ask Evan. Do not "fix" build issues silently.

- [ ] **0.3 Audit existing brand drift** (P0 · 20 min)
  - Surface: both repos
  - Commands:
    ```bash
    cd ~/Projects/SharpPicks
    grep -rn "#34D399\|52, 211, 153" --include="*.css" --include="*.tsx" --include="*.jsx" --include="*.swift" --include="*.html" .
    grep -rn "#F87171\|248, 113, 113" --include="*.css" --include="*.tsx" --include="*.jsx" --include="*.swift" --include="*.html" .
    grep -rn "—\|✓\|🔥\|🔒" --include="*.tsx" --include="*.jsx" --include="*.html" .

    cd ~/Projects/evan_cole_hq
    # repeat above
    ```
  - Acceptance:
    1. Output saved to `audit-{date}.txt` in each repo's working directory
    2. Total drift count documented (e.g., "47 mint references, 3 red references, 12 em-dashes")
    3. No surprises — if the count is over 200, escalate to Evan before starting
  - Notes: This audit informs which surfaces have the most drift. Do not start fixing yet.

- [ ] **0.4 Drop the design system docs into both repos** (P0 · 10 min)
  - Surface: both repos
  - Action: Copy `BRAND_SPEC.md`, `DESIGN_SYSTEM.md`, `design-system.html`, `marks.html` into:
    - `~/Projects/SharpPicks/docs/design-system/`
    - `~/Projects/evan_cole_hq/docs/design-system/`
  - Acceptance:
    1. Both directories exist and contain all four files
    2. `git status` shows them as new files
    3. Commit with message: `docs: add v4.3 design system reference`
  - Notes: These are reference documents only. They do not get bundled into builds.

---

## Priority 1 — Must ship before Friday May 8 (WNBA tipoff)

These three surfaces are the public face of the WNBA launch. They must be live in staging by Thursday May 7, production by Friday morning May 8.

### P1.1 — Tokens and shared infrastructure

- [ ] **1.1.1 Update `tokens.css` in SharpPicks** (P1 · 30 min)
  - Surface: `~/Projects/SharpPicks/static/css/tokens.css`
  - Action: Replace contents with the canonical `tokens.css` from the handoff bundle
  - Acceptance:
    1. File matches handoff `tokens.css` exactly
    2. Every CSS variable from `BRAND_SPEC.md` v4.3 is present
    3. No old mint green `#34D399` references remain
    4. Flask app renders without console errors after restart
  - Notes: This is the foundation. Every other P1 task depends on this.

- [ ] **1.1.2 Update `tokens.css` and Tailwind config in evan_cole_hq** (P1 · 45 min)
  - Surface: `~/Projects/evan_cole_hq/styles/tokens.css` AND `tailwind.config.ts`
  - Action: Update CSS variables and Tailwind theme tokens to match v4.3
  - Acceptance:
    1. `tokens.css` matches handoff bundle
    2. `tailwind.config.ts` theme.colors maps to CSS variables (e.g., `'sp-green': 'var(--sp-green)'`)
    3. `pnpm build` succeeds without warnings
    4. Visual check on `/today` page: no green color regressions
  - Depends on: 1.1.1 (use SharpPicks tokens.css as source of truth)
  - Notes: The Tailwind config is the gotcha. If tokens are updated but Tailwind references old values, Tailwind classes still render mint.

- [ ] **1.1.3 Update Capacitor iOS Swift brand constants** (P1 · 30 min)
  - Surface: `~/Projects/SharpPicks/ios/App/App/brand-tokens.swift` (or wherever Swift brand constants live)
  - Action: Update Swift `Color` constants to match v4.3 hex values
  - Acceptance:
    1. `Color.spGreen` (or equivalent) is `#5A9E72`, not `#34D399`
    2. `Color.spBackground` is `#0A0D14`
    3. `Color.spSurface` is `#121725`
    4. `Color.spNegative` is `#C4868A`, not `#F87171`
    5. iOS app builds in Xcode without errors
  - Depends on: 1.1.1
  - Notes: If the file does not exist yet, create it. Coordinate with Capacitor color handling — some projects bridge CSS variables to Swift, others duplicate.

### P1.2 — Calibration banner pattern (used by both MLB and WNBA)

- [ ] **1.2.1 Build `<CalibrationBanner />` React component** (P1 · 1 hour)
  - Surface: `~/Projects/SharpPicks/src/components/brand/CalibrationBanner.tsx` (or equivalent path)
  - Action: Build a reusable React component matching the locked pattern from `DESIGN_SYSTEM.md` section 16.1
  - Acceptance:
    1. Renders amber-tinted background `rgba(245, 158, 11, 0.08)` with amber border at 22% opacity
    2. Pulsing amber dot (8×8px, 2-second cycle)
    3. Eyebrow in JetBrains Mono, 9px, 0.22em tracking, uppercase, amber
    4. Body in IBM Plex Serif at 14px, line-height 1.5
    5. Accepts `eyebrow` and `children` (or `body`) props
    6. Respects `prefers-reduced-motion` (disables pulse animation)
  - Notes: This is THE most-reused calibration UI element. Get it right once, use it everywhere.

- [ ] **1.2.2 Replace existing calibration callouts with `<CalibrationBanner />`** (P1 · 1 hour)
  - Surface: `~/Projects/SharpPicks/src/components/screens/`
  - Action: Find every existing "Model Phase: Calibration" blue strip and "CALIBRATION BETA" green callout. Replace with single amber `<CalibrationBanner />`.
  - Acceptance:
    1. Zero blue calibration framing remains in MLB screens
    2. Zero "BETA" green callouts remain
    3. Each screen has at most ONE calibration banner (not stacked)
    4. Banner copy matches the canonical mockups
  - Depends on: 1.2.1
  - Notes: Reference `mlb-home-redesigned.html` for the consolidated banner copy.

### P1.3 — WNBA pre-launch page

- [ ] **1.3.1 Build `<WNBAPreLaunchScreen />` component** (P1 · 3 hours)
  - Surface: `~/Projects/SharpPicks/src/components/screens/WNBAPreLaunchScreen.tsx`
  - Action: Build component matching `wnba-prelaunch-page.html` exactly
  - Acceptance:
    1. Countdown strip with pulsing amber dot
    2. Hero with "WNBA signals go live" headline in IBM Plex Serif
    3. "First reads" timeline card
    4. "How the model thinks about WNBA" card with 4 weighted inputs
    5. "Meet the model" methodology card with 3-cell stat row
    6. Comparison block (other accounts vs us)
    7. Sample format preview (Calibration Log)
    8. "Notify me" CTA (Edge Green primary button)
    9. Footer principle: "Calibration phase. Live signals. Receipts tracked publicly."
  - Notes: Model input weights (88%/76%/64%/58%) are placeholders. Either replace with real values from Evan or generalize to qualitative bands ("primary," "secondary"). ASK BEFORE LAUNCH.

- [ ] **1.3.2 Wire WNBA tab routing to pre-launch page** (P1 · 30 min)
  - Surface: `~/Projects/SharpPicks/src/navigation/SignalsHomeScreen.tsx` (or equivalent)
  - Action: When user taps WNBA tab, render `<WNBAPreLaunchScreen />` until launch flag flips
  - Acceptance:
    1. Tapping WNBA tab on home screen renders pre-launch page
    2. Tab pill shows "WNBA · FRI" with amber accent (not "SOON")
    3. Feature flag `WNBA_LIVE` controls render: false → pre-launch, true → normal signals view
    4. Default flag value is `false` until Friday May 8 morning
  - Depends on: 1.3.1, 1.1.3
  - Notes: Adding the flag is fine. Flipping it on Friday is Evan's call.

- [ ] **1.3.3 "Notify me" CTA wires to email capture** (P1 · 1 hour)
  - Surface: same as 1.3.2
  - Action: CTA opens iOS native modal or in-app sheet with email field; on submit, POST to existing `/api/notify-wnba` endpoint or create one
  - Acceptance:
    1. CTA opens email capture sheet
    2. Submit POSTs `{ email, sport: 'wnba', source: 'pre-launch-page' }` to backend
    3. Backend stores in `notification_signups` table (verify table exists; if not, ASK Evan)
    4. Success state shows "We'll notify you Friday morning" in IBM Plex Serif
    5. Failure state shows muted rose error message (no exclamation marks)
  - Depends on: 1.3.1
  - Notes: If the table does not exist, do not create it. Ask Evan first.

### P1.4 — Signal card paywalled state on home

- [ ] **1.4.1 Update `<DailyTopSignalCard />` to support paywalled rendering** (P1 · 2 hours)
  - Surface: `~/Projects/SharpPicks/src/components/cards/DailyTopSignalCard.tsx`
  - Action: Refactor to accept `isPaywalled` prop. When true, render the design from `mlb-home-redesigned.html` paywalled state.
  - Acceptance:
    1. `isPaywalled={true}` renders blurred stat values (CSS `filter: blur(6px)`)
    2. Headline shows real edge type (e.g., "A qualified edge fired tonight. +6.0%")
    3. Sub-text describes type of edge without giving the bet
    4. 4-cell stat grid (Side / Line / Tier / Size) shows blurred real values
    5. Unlock strip shows lock icon + "Unlock to see side, line, edge breakdown, and Kelly sizing"
    6. CTA button is Edge Green primary, copy: "Start 14-day free trial"
    7. CTA subtext is platform-conditional (see 1.4.2)
    8. Bottom strip: "Calibration v1" amber tag if model in calibration phase
  - Depends on: 1.1.3, 1.2.1
  - Notes: The blur is a deliberate UX choice over `[Pro]` placeholders. Reference handoff debug notes Section 12.

- [ ] **1.4.2 Implement platform-conditional trial CTA copy** (P1 · 30 min)
  - Surface: `~/Projects/SharpPicks/src/components/cards/DailyTopSignalCard.tsx` AND any other place the trial CTA appears
  - Action: Centralize platform check
    ```tsx
    import { Capacitor } from '@capacitor/core';

    const trialSubtext = Capacitor.getPlatform() === 'ios'
      ? 'Cancel anytime'
      : 'Card required · Cancel anytime';
    ```
  - Acceptance:
    1. iOS build shows "Cancel anytime" subtext
    2. Web build (evan_cole_hq) shows "Card required · Cancel anytime"
    3. Android build (Capacitor + Stripe) shows "Card required · Cancel anytime"
    4. Logic centralized in a hook or helper, not duplicated
    5. Tested in all three target platforms
  - Depends on: 1.4.1
  - Notes: This is the most likely place for inconsistency to creep in. Centralize the helper.

- [ ] **1.4.3 Verify slate preview shows free-user-visible signal flags** (P1 · 1 hour)
  - Surface: `~/Projects/SharpPicks/src/components/screens/MLBHomeScreen.tsx` and similar
  - Action: Today's Slate section shows games with Signal/Edge/Below classification visible to free users
  - Acceptance:
    1. Free user sees 5 games minimum in slate
    2. Signal-fired games show "Signal" pill in Edge Green
    3. Edge-detected (below threshold) games show "Edge" pill in muted green
    4. Below-threshold games show "Below" in tertiary text
    5. Specific side/line values NOT shown to free users for signal-fired games
    6. Slate filter tabs (All / Edges / Upcoming / Live / Final) functional
  - Depends on: 1.1.3
  - Notes: This is what makes the home screen useful for evaluation, not just upgrade pressure.

### P1.5 — WNBA launch tweet pack and teaser cards

- [ ] **1.5.1 Verify teaser card PNGs in social media management tool** (P1 · 30 min)
  - Surface: External (Twitter / Buffer / Typefully / direct upload)
  - Action: Upload `card-1-announce.png`, `card-2-explain.png`, `card-3-preview.png` to scheduled tweets
  - Acceptance:
    1. May 6 teaser tweet scheduled with card-1-announce.png
    2. May 7 teaser tweet scheduled with card-2-explain.png
    3. May 7 evening tweet scheduled with card-3-preview.png
    4. Friday May 8 launch tweet pack staged (do not auto-send)
  - Notes: Reference `wnba-teaser-tweets.md` and `wnba-launch-tweets.md` for tweet copy.

- [ ] **1.5.2 Test rendered cards on actual Twitter** (P1 · 15 min)
  - Surface: External
  - Action: Pre-tweet the cards to a private/test account or draft state. Verify rendering.
  - Acceptance:
    1. Cards display at correct 4:5 aspect ratio (1080×1350)
    2. Wordmark renders cleanly without compression artifacts
    3. Edge Green underline visible
    4. Text is readable on mobile and desktop Twitter
  - Notes: Twitter sometimes recompresses images. If it ruins the wordmark, escalate to Evan.

### P1 sign-off gate

- [ ] **1.6 Priority 1 sign-off** (P1 · 30 min)
  - Action: All P1 items checked. Visual check on staging.
  - Acceptance:
    1. iOS staging build deployed and TestFlight invitation sent to Evan
    2. evan_cole_hq staging URL accessible and reviewed
    3. All P1 acceptance criteria met (re-verify)
    4. Brand audit checklist (HANDOFF.md Section 13) passes on every modified surface
    5. Evan has signed off via reply
  - Notes: Do not flip the WNBA_LIVE flag until Evan signs off.

---

## Priority 2 — Within 1 week of WNBA launch

These improve the post-launch experience but don't block the launch itself.

### P2.1 — Sharp Journal article surfaces

- [ ] **2.1.1 Build `<SharpJournalArticle />` morning variant** (P2 · 3 hours)
  - Surface: `~/Projects/evan_cole_hq/app/sharp-journal/[date]/page.tsx` AND `~/Projects/SharpPicks/src/components/screens/SharpJournalArticleScreen.tsx`
  - Action: Build component matching `sharp-journal-mockup.html`
  - Acceptance:
    1. Nav bar with "SHARP JOURNAL" caps title
    2. Article meta row (content tag, section, edition, read time)
    3. Headline in IBM Plex Serif 30-32px
    4. Date line in JetBrains Mono with timezone
    5. Byline: "Evan Cole · Head of Signal Intelligence"
    6. Observation block (bordered-left card with green accent)
    7. Stat cards (4-up Slate Result grid, Bias bar, Top Edge with explainer)
    8. Edge Map (diverging-axis bar list)
    9. Closing Line Audit table with verdict pills
    10. Near Misses list with edge values
    11. Implication block (bordered-left)
    12. Sharp Principle quote (italic IBM Plex Serif)
    13. Cross-edition link to evening
  - Notes: Section eyebrow colors are fixed: green for editorial, amber for live, blue for cross-content.

- [ ] **2.1.2 Build evening variant with mixed-state handling** (P2 · 2 hours)
  - Surface: same as 2.1.1
  - Action: Add evening-specific elements from `sharp-journal-evening.html`
  - Acceptance:
    1. Pulsing amber banner when slate is partially settled
    2. "Preliminary · X of Y" markers on aggregate stats during mixed state
    3. Mixed Edge Map showing both settled (final scores) and live (B7 inning) games
    4. Dedicated "Still in progress" section listing live games
    5. Auto-refresh footer note: "This report updates automatically when games settle"
    6. Cross-edition link to morning
  - Depends on: 2.1.1
  - Notes: The mixed-state handling is documented in `DESIGN_SYSTEM.md` section 31.2.

- [ ] **2.1.3 Wire Sharp Journal cross-links from signal card and Market Intelligence** (P2 · 1 hour)
  - Surface: both `<DailyTopSignalCard />` and `<MarketIntelligenceReport />`
  - Action: Add cross-link card at bottom that links to today's morning Sharp Journal article
  - Acceptance:
    1. Cross-link only renders if Sharp Journal article exists for today
    2. Link card matches the visual pattern from mockups
    3. Tap navigates to Sharp Journal route, not external URL
    4. Hidden if no article published yet (early morning state)
  - Depends on: 2.1.1
  - Notes: Reference HANDOFF.md Section 11 for the visibility logic.

### P2.2 — Market Intelligence report

- [ ] **2.2.1 Update `<MarketIntelligenceReport />`** (P2 · 3 hours)
  - Surface: `~/Projects/SharpPicks/src/components/screens/MarketIntelligenceScreen.tsx`
  - Action: Refactor to match `market-intelligence-redesigned.html`
  - Acceptance:
    1. Article-styled header with sport tag and date line
    2. Calibration banner (when model in calibration)
    3. 3-up headline grid (MEI / Regime / Top Edge)
    4. MEI scale strip with gradient bar and marker
    5. Edge breakdown (proportional bar + 3-cell legend)
    6. Observation block
    7. Moneyline Movement table with significant-move flagging
    8. Movement summary (Toward / Away / No movement counts)
    9. Model vs Market Delta with diverging bars
    10. Footer summary with average delta
    11. Sharp Journal cross-link
    12. Footer meta with last update + next refresh time
  - Depends on: 2.1.1 (cross-link target must exist)

### P2.3 — Email lifecycle templates

- [ ] **2.3.1 Update master email template** (P2 · 2 hours)
  - Surface: `~/Projects/SharpPicks/templates/emails/master.html`
  - Action: Update to match `email-master.html` from handoff
  - Acceptance:
    1. Header uses table-based standalone signal mark (do NOT switch to CSS-based)
    2. All colors match v4.3 tokens
    3. Sharp Principle in footer in italic IBM Plex Serif (where supported)
    4. List-Unsubscribe headers present
    5. Tested in Gmail, Outlook web, Apple Mail
  - Notes: The lighter table bars are intentional for Outlook compat. Do not "fix" to match standalone mark spec.

- [ ] **2.3.2 Update all 7 email variants** (P2 · 3 hours)
  - Surface: `~/Projects/SharpPicks/email-variants.js`
  - Action: Update content for each variant to match handoff `email-preview.html`
  - Acceptance:
    1. All 7 variants render correctly
    2. Voice rules pass (no em-dashes, no exclamation marks, etc.)
    3. Founding Fifty perks verified by Evan before sending Power User variant (open question 9.3)
    4. Test send to staging email captures
  - Depends on: 2.3.1

### P2.4 — Signal card unlocked state

- [ ] **2.4.1 Update `<DailyTopSignalCard />` unlocked rendering** (P2 · 2 hours)
  - Surface: same as 1.4.1
  - Action: When `isPaywalled={false}`, render full unlocked design from `signal-card-redesigned.html`
  - Acceptance:
    1. All 14 sections from DESIGN_SYSTEM.md section 19 present
    2. Diverging edge bar with -10pp / 0 / +10pp scale
    3. Calibration disclosure (when applicable)
    4. Playability range with target + floor markers
    5. Sizing block with Flat + Kelly toggle
    6. Track button (primary green CTA)
    7. Tracking confirmation state ("Tracking · TEX +1.5 · 1.5u")
  - Depends on: 1.4.1, 2.1.3 (cross-link)

---

## Priority 3 — Within 2 weeks

### P3.1 — Marketing site refresh

- [ ] **3.1.1 Update evan_cole_hq landing page** (P3 · 4 hours)
  - Surface: `~/Projects/evan_cole_hq/app/page.tsx`
  - Action: Apply v4.3 brand system to landing
  - Acceptance:
    1. Hero uses M2 wordmark
    2. Tagline lockup permitted here (it's marketing, not the design system itself)
    3. All CTAs use platform-correct copy
    4. Sharp Principle quotes use locked component pattern
    5. No mint green anywhere

- [ ] **3.1.2 Update `/today` page** (P3 · 2 hours)
  - Surface: `~/Projects/evan_cole_hq/app/today/page.tsx`
  - Action: Apply v4.3 brand to Daily Market Scan tweet draft view
  - Acceptance:
    1. Wordmark in header
    2. Calibration banner (if applicable)
    3. Copy / Regenerate buttons use Edge Green primary + Ghost secondary
    4. Tweet preview rendered in proper SharpPicks frame

### P3.2 — Open question resolution

- [ ] **3.2.1 Bottom nav tab order migration** (P3 · 2 hours)
  - Surface: `~/Projects/SharpPicks/src/navigation/BottomNav.tsx`
  - Action: Migrate "Signals · Results · Insights · Account" → "Signals · Track · Journal · Account"
  - Acceptance:
    1. Tab order updated in nav component
    2. Routes updated to match new labels
    3. Analytics events updated with new tab names
    4. Deep links from email/notifications still work
  - Notes: Do not do this until AFTER WNBA launch is stable. Ask Evan to confirm.

- [ ] **3.2.2 Field Guide content backlog** (P3 · variable)
  - Action: Write 4-5 Field Guide articles for the home rotator
  - Topics suggested in HANDOFF.md Section 10, item 2
  - Notes: Coordinate with Evan on tone and final topic list. This is content work, not just code.

- [ ] **3.2.3 MEI methodology explainer** (P3 · 2 hours)
  - Action: Either (a) add 2-3 sentence first-view explainer (dismissible) on Market Intelligence, OR (b) create Field Guide article "How to read the MEI score"
  - Notes: Tooltip alone is not enough. Choose one path with Evan.

### P3.3 — App Store assets

- [ ] **3.3.1 Regenerate App Store screenshots** (P3 · 3 hours)
  - Surface: External (Xcode + screenshot tool)
  - Action: Capture v4.3 brand-correct screenshots for App Store listing
  - Acceptance:
    1. 6.5" iPhone screenshots (required size for App Store)
    2. iPad screenshots if listing supports iPad
    3. All screenshots show v4.3 brand (not v4.2 mint or earlier)
    4. Required device frames applied
    5. Screenshots uploaded to App Store Connect

- [ ] **3.3.2 OG images for Sharp Journal** (P3 · 2 hours)
  - Action: Generate `og-report-morning.png` and `og-report-evening.png` at 1200×630
  - Acceptance:
    1. Both PNGs use brand-locked rendering pipeline (same as WNBA teaser cards)
    2. Wordmark renders correctly (use absolute-positioning fallback for image generation)
    3. Stored in `~/Projects/evan_cole_hq/public/og/`
    4. Referenced in Sharp Journal article metadata
  - Depends on: 2.1.1

### P3.4 — Cleanup and documentation

- [ ] **3.4.1 Remove deprecated components and styles** (P3 · 2 hours)
  - Surface: both repos
  - Action: Find any v4.0/v4.1 brand artifacts that are no longer used. Remove.
  - Acceptance:
    1. Zero references to old mint `#34D399`
    2. Zero blue calibration banners
    3. Zero "BETA" pill components
    4. Old tagline lockup variants (other than marketing-permitted) removed
    5. Removed code committed with message: `chore: remove v4.0/v4.1 brand artifacts`

- [ ] **3.4.2 Document any new patterns discovered during migration** (P3 · 1 hour)
  - Surface: `~/Projects/SharpPicks/docs/design-system/DESIGN_SYSTEM.md` (add to)
  - Action: If you encountered patterns not in DESIGN_SYSTEM.md, document them
  - Acceptance:
    1. Each new pattern has: name, use case, locked construction, forbidden uses
    2. Each new pattern has visual reference (screenshot or HTML mockup)
    3. Changes proposed to Evan via PR before committing to main
  - Notes: Do not invent new patterns to solve problems. If you reach for a new pattern, that is the moment to ask whether an existing one fits.

---

## Final sign-off

- [ ] **F.1 All checklist items complete** (P0 · final review)
  - Acceptance:
    1. Every checkbox above is `[x]` with verification note
    2. Brand audit checklist passes on every surface
    3. Both staging environments deployed and reviewed
    4. Production deployment scheduled with Evan
    5. Open questions document updated with resolutions or escalations

- [ ] **F.2 Migration retrospective document** (P0 · 30 min)
  - Action: Write a brief retrospective in `docs/migrations/v4.3-retrospective.md`
  - Content:
    1. What went well
    2. What was harder than expected
    3. New patterns discovered (link to design system updates)
    4. Recommendations for the next migration
  - Notes: This becomes the institutional knowledge for the next person doing this work.

---

## Status summary

**Total tasks:** 30 (excluding pre-flight)
**Estimated effort:** 48-60 hours over 2 weeks
**Critical path:** 0.x → 1.1.x → 1.2.x → 1.3.x → 1.4.x → 1.5.x → 1.6 (WNBA LAUNCH GATE) → P2 → P3

When you complete a task, update the checkbox AND add a one-line verification note. Do not mark a task complete unless all acceptance criteria pass.

If any task is blocked, stop work on that task, document why, and move to the next. Do not improvise around documented decisions.
