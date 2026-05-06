# START HERE — SharpPicks v4.3 Brand Migration

You are Claude Code, picking up a brand system migration for SharpPicks. Read this file completely before doing anything else.

## The very first command

Open both companion docs in your context:

```bash
cat HANDOFF.md MIGRATION_CHECKLIST.md
```

Then verify your working directory:

```bash
pwd && ls
```

You should see this file plus `HANDOFF.md` and `MIGRATION_CHECKLIST.md` in the same directory.

---

## Who you are working for

Evan (legal name Erin Donnelly) is the founder and sole builder of SharpPicks LLC. Two repos:

- `~/Projects/SharpPicks` — Flask/Python backend + Capacitor iOS app + static frontend
- `~/Projects/evan_cole_hq` — Next.js 16 / Cloudflare Workers (Evan Cole content brand)

Shared Railway Postgres at `nozomi.proxy.rlwy.net:14576/railway`.

---

## What you are doing

Migrating the SharpPicks brand system to v4.3 across both repos. This is **visual/UI work only**. Do not modify:

- Backend signal computation logic
- Postgres schemas
- Railway cron schedules
- RevenueCat / Stripe payment integration
- Authentication flows
- API contracts (route shapes, response shapes)

You ARE modifying:

- CSS tokens and color values
- Wordmark and signal mark rendering across surfaces
- Calibration banner placement and styling
- Signal card layout (paywalled and unlocked states)
- Market Intelligence report layout
- Sharp Journal article layout
- Email lifecycle template visuals
- Mobile home screen layout

---

## How to work

1. Read `HANDOFF.md` end-to-end first. It explains the brand system, what's locked, what's open, and where the canonical specs live.

2. Open `MIGRATION_CHECKLIST.md` and work through it sequentially. The order matters — earlier items unblock later ones.

3. For every meaningful change, present a manual diff to Evan for approval. Do not bulk-modify files without showing what you are doing.

4. Time-cap research spikes at 20 minutes. If you cannot find an answer, ask.

5. Two-strike rule on brand voice violations. If you write content with em-dashes, exclamation marks, or AI-speak, fix it immediately. Second violation in the same session, stop and ask Evan to review.

6. When uncertain, the `/mnt/user-data/outputs/` directory in the conversation context (or wherever Evan has saved them) contains the canonical mockups for every surface. Open them, look at them, then implement.

---

## Critical files Evan has handed off

In the same directory as this START_HERE.md:

- `HANDOFF.md` — the full migration brief, decisions log, and what-not-to-touch
- `MIGRATION_CHECKLIST.md` — sequenced task list, you update as you go
- `BRAND_SPEC.md` — v4.3 canonical brand system (colors, typography, marks)
- `DESIGN_SYSTEM.md` — v1.1 complete design guide (subsumes BRAND_SPEC)
- `design-system.html` — visual reference site (open in browser to see every locked pattern)
- `marks.html` — wordmark and signal mark visual reference
- `tokens.css` — universal CSS variables ready to drop into both repos

Mockup HTMLs (visual reference for each surface):

- `home-redesigned.html` and `mlb-home-redesigned.html` — Signals tab home screen
- `signal-card-redesigned.html` — Daily Top Signal card
- `market-intelligence-redesigned.html` — Market Intelligence report
- `wnba-prelaunch-page.html` — WNBA tab pre-launch state
- `sharp-journal-mockup.html` — Sharp Journal morning edition
- `sharp-journal-evening.html` — Sharp Journal evening edition with mixed-state handling
- `email-master.html` and `email-preview.html` — email lifecycle templates
- `card-1-announce.png`, `card-2-explain.png`, `card-3-preview.png` — WNBA launch teaser cards

---

## Timeline

**Priority 1 — must ship before Friday May 8 (WNBA tipoff):**
- WNBA tab pre-launch page in iOS app
- Calibration banner pattern in iOS app (used by both MLB and WNBA)
- Signal card paywalled state for free users on home

**Priority 2 — within 1 week of WNBA launch:**
- Sharp Journal morning + evening editions
- Market Intelligence redesign
- Email template visual refresh
- Signal card unlocked state

**Priority 3 — within 2 weeks:**
- Marketing site refresh in evan_cole_hq
- Open question resolution (bottom nav order, Field Guide content)
- App Store screenshots regenerated

---

## What "done" looks like

Each task in `MIGRATION_CHECKLIST.md` has explicit acceptance criteria. A task is done when:

1. The code change matches the canonical mockup visually
2. The code uses tokens from `tokens.css` (no hardcoded hex values)
3. The audit checklist in `DESIGN_SYSTEM.md` Part VII passes
4. The change is deployed to staging and visually verified
5. The checkbox is marked complete in `MIGRATION_CHECKLIST.md`

Not "done" until all five.

---

## When to stop and ask

Stop and ask Evan when:
- A design decision conflicts with what's documented (do not improvise)
- A backend change would be needed to support a UI change (out of your scope)
- An open question from `DESIGN_SYSTEM.md` Part VIII blocks progress
- You discover the canonical spec is wrong or contradictory
- You are about to delete user-facing content
- You are about to change navigation routes or URL shapes

---

## What success looks like in 2 weeks

- Both repos render the v4.3 brand system consistently
- WNBA launch shipped on Friday May 8 with pre-launch page transitioning to live signals
- All 6 mobile surfaces match the canonical mockups
- Email templates updated and tested in 3+ clients (Gmail, Outlook, Apple Mail)
- Marketing site refreshed
- Migration checklist 100% complete with verification notes
- Brand audit checklist passes on every surface
- Open questions either resolved or escalated to Evan with recommendations

Now read `HANDOFF.md`.
