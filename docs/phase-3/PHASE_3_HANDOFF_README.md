# Phase 3 handoff to Claude Code

Phase 2 must be merged and verified before starting Phase 3. Confirm before proceeding.

This handoff is two files:

1. **`PHASE_3_BUILD_SPEC.md`** — the spec. Step plan, endpoint shapes, data wirings, verification gates. Read this for the build order.

2. **`command-center-mockup.html`** — the locked design. Open it in a browser, resize to 375px to see mobile, click between all four tabs (Command, Users, Model, Infra). Every visual decision is in there. When the spec and the mockup conflict, the mockup wins.

## How to use this packet

1. Save both files into the SharpPicks repo at `docs/phase-3/`. Commit them as a standalone docs commit (no code changes) before starting any implementation. Lessons-from-Phase-1 pattern.

2. Open `docs/phase-3/command-center-mockup.html` in your browser. Walk through it once before reading the spec. Click everything that's clickable. Resize the window to 375px and walk through it again. The mockup uses fake `Math.random()` data for charts — the real build replaces those with Phase 2 endpoint data. Everything else (typography, color, spacing, layout, brand wordmark, interactive states) is the locked target.

3. Read `PHASE_3_BUILD_SPEC.md` top to bottom. It's organized into 9 steps. Each step has a verification gate. Do not skip ahead.

4. Same workflow as Phases 1 and 2:
   - Surface proposed diffs before applying
   - Manual approval gate on every meaningful change
   - Stop and surface at each verification gate
   - Time-cap research at 20 minutes
   - No `Co-Authored-By` trailers in commits (per `CLAUDE.md`)

## Decisions already locked in

These were made during the design phase. Don't re-litigate.

- **Four tabs:** Command, Users, Model, Infra. Single page. JS-only DOM toggle for tab switching, no URL hash, no router.
- **Single fetch on page load:** all four tabs render from one `/api/admin/metrics` response. No refetch on tab change.
- **Headline sentence is the hero**, not the MRR number. Number sits underneath. Rule-based generation, not LLM.
- **"What to do today" lines:** rule-based action surfacing.
- **Charts use Chart.js 4.4.1** with brand-locked defaults. No other chart library.
- **Vanilla JavaScript**, no framework. Match existing project conventions.
- **Stripe + RevenueCat MRR is combined** on Command headline; split available on Revenue section.
- **Power user threshold:** 15+ logins in 30 days. Calibrate after real data lands.
- **Cohort retention table is the only place mobile gets horizontal scroll.** Tables of that shape don't reflow honestly. Acceptable tradeoff.
- **Brand wordmark:** "Sharp ‖ Picks" with two Edge Green bars (3px × 14px, 2px gap) between the words. Implemented as divs, not text characters.

## Open items for Darell to surface in Phase 3.0 (audit)

Before coding starts, Darell should surface the following from the existing codebase. Same shape as the Phase 0 audit:

1. **Login event source.** The Users tab assumes there's a `login` event in `user_events` (or a `last_login_at` column on the User model). Confirm what exists. If neither, propose what to add.
2. **Existing `signals` and game-results schema.** The Model tab needs to join signals to outcomes to compute hit/miss and calibration. Surface the schema before writing query SQL.
3. **Existing fonts loaded in the app.** IBM Plex Serif, Inter, JetBrains Mono — confirm the existing pattern (CDN link in base template? webpack import?) so we don't double-load.
4. **Existing `/admin` route.** Confirm the current `templates/admin.html` is the right thing to replace, and that no other admin views depend on it.
5. **Railway API access.** The Infra tab wants real uptime/deploy data. Confirm whether the Railway API is callable from inside the app (auth, env vars), or whether we need to fall back to internal-only metrics.

Surface these five items before starting Step 3.1.

## Phase order recap

- ✅ Phase 1 — bet tap tracking foundation (done)
- ✅ Phase 2 — data layer + 6 sources + unified endpoint (assumed done before Phase 3 starts)
- 🟡 **Phase 3 — UI rebuild** (this packet)
- ⬜ Phase 4 — reconciliation + Postgres-only alerting (next)
