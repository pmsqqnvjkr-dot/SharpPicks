# Phase 3 build spec — Command Center UI

Phase 2 must be merged and verified before starting Phase 3. Confirm before proceeding.

## Visual source of truth

Open `docs/command-center-mockup.html` (committed alongside this spec). That file is the locked design. Every visual decision — typography, color, spacing, chart styles, layout grid, hover states — is in there. When this spec and the mockup conflict, the mockup wins. When the mockup and `BRAND_GUIDELINES.md` conflict, the brand guidelines win.

Read the mockup before reading the rest of this spec. Open it on desktop, then resize to ~375px wide to see the mobile layout. Click between all four tabs (Command, Users, Model, Infra), tap the segment chips, tap the compare-toggle, tap the internal-events toggle. Everything that's interactive there must be interactive in the real build.

## Scope

A four-tab single-page admin dashboard at `/admin`. Replaces the existing `templates/admin.html`. Powered by Phase 2's `/api/admin/metrics` endpoint plus a small set of new endpoints described below.

Tabs: **Command · Users · Model · Infra**

The dashboard is read-only. No write operations except the two existing toggles (compare-window, internal-events) which persist in localStorage only.

## Architecture rule

Vanilla JavaScript and templated HTML — no framework. Match existing project conventions. The current `admin.html` is server-rendered Jinja with vanilla JS; stay in that pattern.

Single fetch on page load: `GET /api/admin/metrics?range=7d&include_internal=false`. All four tabs render from that one response. Switching tabs is pure DOM toggle, no refetch. Refresh-on-tab-change creates flicker and burns the cache; don't do it.

## Phase 3 step plan

Work in order. Stop and verify at each gate. Manual diff approval on every change. Time-cap research at 20 minutes.

---

### Step 3.1 — Brand tokens and shared CSS

Extract the design system from the mockup into `static/css/admin.css`. Specifically the `:root` CSS variable block, the typography rules (IBM Plex Serif / Inter / JetBrains Mono / Courier New), and the layout primitives (`.section`, `.stat-row`, `.label`, `.section-summary`, `.headline`).

Do **not** copy the mockup wholesale into `admin.css`. The mockup is a single file for ease of review. The real build splits into:

- `static/css/admin.css` — everything in the mockup's `<style>` block, organized into sections
- `templates/admin.html` — the markup, broken into Jinja partials
- `static/js/admin.js` — the JavaScript at the bottom of the mockup

Load order: brand fonts via Google Fonts `<link>` (already used elsewhere in the app — confirm pattern), then `admin.css`, then `admin.js` at end of body.

Surface where the existing fonts are loaded so we don't double-load.

**Verification 3.1:**
- Open `/admin`, confirm a single header element with the wordmark renders correctly with the two Edge Green bars between "Sharp" and "Picks"
- Page passes brand check: no Tailwind, no `font-black`, no emoji anywhere, no exclamation marks

Stop and surface.

---

### Step 3.2 — Tab strip and panel skeleton

Render the four tabs (`Command · Users · Model · Infra`) and four empty `<div class="panel">` containers. Tab switching is JS-only DOM toggle (no URL hash, no router). Default active tab is Command.

The deep-link card from Command's User Activity section ("View full user activity → users tab") should switch the user to the Users tab when clicked, matching the mockup behavior.

**Verification 3.2:**
- All four tabs clickable, active state highlights correctly
- Tab text is Courier New 11px, 2px letter-spacing, uppercase, font-weight 700
- Active tab gets the Signal Blue underline
- The deep-link card switches tabs (not just an alert)
- Mobile: tab strip horizontal-scrolls if needed, no other horizontal scroll on the page

Stop and surface.

---

### Step 3.3 — `/api/admin/metrics` shape extension

Phase 2 already built the unified endpoint. Phase 3 needs three additions to its response shape:

```json
{
  ...existing phase 2 envelopes (cloudflare, stripe, revenuecat, events, ga4, gsc)...
  "headline": {
    "template": "good_day" | "quiet_day" | "mixed_day" | "bad_day" | "anomaly_day",
    "sentence": "MRR up $58 this week. Three new subscribers, no churn.",
    "color": "green" | "blue" | "amber" | "red"
  },
  "actions": [
    { "type": "trial_no_card", "message": "Trial expires for sarah_g in 2 days, no card on file. Reach out before friday.", "priority": "warn" },
    { "type": "gsc_growth", "message": "GSC clicks up 41% vs prev 7d. Review top queries for content opportunities.", "priority": "info" }
  ],
  "what_moved": [
    { "label": "New subscribers today", "value": 2, "delta": "+1 vs avg", "delta_direction": "up", "annotation": null },
    { "label": "Bet taps last 24h", "value": 1, "delta": "below threshold", "delta_direction": "neutral", "annotation": "Typical week 0-3, mostly Evan. Today's tap was external." }
  ]
}
```

The `headline` and `actions` are computed by a new `services/headline.py` module — **rule-based, not LLM-based.** A small set of `if/then` checks against the data already in the response. Examples:

```python
def compute_headline(metrics: dict) -> dict:
    mrr_delta = metrics["stripe"]["payload"]["mrr_30d_delta"] + metrics["revenuecat"]["payload"]["mrr_30d_delta"]
    new_subs_7d = metrics["stripe"]["payload"]["new_subs_7d"] + metrics["revenuecat"]["payload"]["new_subs_7d"]
    canceled_7d = metrics["stripe"]["payload"]["canceled_7d"] + metrics["revenuecat"]["payload"]["canceled_7d"]
    failed_payments_7d = metrics["stripe"]["payload"]["failed_payments_7d"]

    if failed_payments_7d > 0 and canceled_7d > 0:
        return {"template": "bad_day", "sentence": f"...", "color": "red"}
    if mrr_delta > 0 and canceled_7d == 0:
        return {"template": "good_day", "sentence": f"MRR up ${mrr_delta} this week. {new_subs_7d} new subscribers, no churn.", "color": "green"}
    # ...etc
```

The `what_moved` list is computed similarly. Always shown: new subs today, signals issued today, bet taps last 24h, traffic last 24h, failed payments last 7d. Conditionally shown: any metric where today's value is more than 1 standard deviation from its 14-day rolling mean.

**Surface the rule logic for review before applying.** This is the most opinionated part of the build — get it right once.

**Verification 3.3:**
- New endpoint shape returns all three additions
- `services/headline.py` rules are reviewable as a single file, not scattered
- No LLM API calls anywhere in the headline/action computation
- Rules produce different headlines for different data states (test by tweaking inputs)

Stop and surface.

---

### Step 3.4 — Command tab

Render Stack 1 (status), Stack 2 (what moved), and the detail sections (Revenue, User Activity summary, Signals, Funnel, Traffic, Bet Taps, freshness line, internal toggle).

Charts use Chart.js 4.4.1 from CDN, matching the mockup. Default styling block from the mockup goes into `admin.js`:

```javascript
Chart.defaults.color = '#8B92A5';
Chart.defaults.borderColor = 'rgba(255,255,255,0.06)';
Chart.defaults.font.family = "'JetBrains Mono', monospace";
Chart.defaults.font.size = 10;
```

Specific chart wirings (data sources):

- **MRR chart** (90-day stacked area, Stripe + RevenueCat): `metrics.stripe.payload.mrr_daily_90d` + `metrics.revenuecat.payload.mrr_daily_90d`. If either source returns less than 90 days of data, pad with the earliest known value backward (don't show a misleading rising curve from null-coalesced zeros).
- **DAU bar chart** (30 days): new query `events.daily_active_users(range_=30)` — count distinct `user_id` per day from `user_events` where `event_type = 'login'` (or whichever event indicates login — Darell to confirm in audit).
- **Sparkline** (14-day MRR): same source as MRR chart, last 14 days only.
- **Traffic area chart** (30 days): `metrics.ga4.payload.sessions_daily_30d`.
- **Funnel bars**: `metrics.events.payload.funnel_7d`. Each bar's width is a percentage of the *original visit count*, not the previous step. This is intentional — it shows the brutal funnel honestly.

Two toggles persist in localStorage:

- `compare_window`: `'7d' | '30d'` — default `'7d'`. Changes the delta basis in Stack 2.
- `include_internal`: `'true' | 'false'` — default `'false'`. When toggled, refetches `/api/admin/metrics?include_internal=true`. The `INTERNAL ON` indicator in the page header shows when active.

Source freshness line at the bottom reads `metrics.<source>.fetched_at` for each of the six sources. Stale states (`metrics.<source>.last_error` not null) render as red `STALE`.

**Verification 3.4:**
- All charts render correctly with real data, not the mockup's `Math.random()` placeholders
- Toggle states persist across reloads
- Internal toggle actually changes counts (specifically, bet taps row should drop when toggled off)
- Stack 1's headline sentence and "what to do today" lines come from the headline/actions API additions, not hardcoded
- One source forced into failure (Phase 2's pattern from earlier) shows STALE in freshness line, headline gracefully omits that source's data

Stop and surface.

---

### Step 3.5 — Users tab

This is the new data domain. Two new endpoints and two new query modules.

**New endpoint 1:** `GET /api/admin/users/activity?range=30d`
Returns the snapshots, login frequency distribution, and cohort retention data. Cache TTL 10 minutes.

```json
{
  "snapshot": { "dau": 47, "wau": 186, "mau": 412, "total_registered": 847, "stickiness_pct": 11.4, "new_7d": 14 },
  "dau_daily_90d": [...],
  "login_frequency_buckets": { "0": 72, "1": 86, "2-3": 132, "4-5": 88, "6-9": 56, "10-14": 38, "15-19": 18, "20-29": 8, "30+": 2 },
  "tier_counts": { "power": 28, "engaged": 94, "light": 218, "dormant": 72 },
  "cohort_retention": [
    { "cohort_week": "2026-03-09", "size": 42, "retention_by_week": [100, 35, 28, 22, 18, 17, 15, 14] },
    ...
  ]
}
```

**New endpoint 2:** `GET /api/admin/users/list?segment=all&search=&limit=50&offset=0`
Returns the user list. Segments: `all | paid | trial | power | dormant | churned`. Search matches email substring (case-insensitive).

```json
{
  "total": 847,
  "filtered": 28,
  "users": [
    {
      "id": "uuid",
      "email": "marcus.chen@gmail.com",
      "tags": ["power", "paid_yearly", "ios"],
      "logins_30d": 42,
      "bet_taps_30d": 14,
      "days_active_30d": 28,
      "last_seen_at": "2026-05-01T18:30:00Z"
    }
  ]
}
```

**Power user definition (locked for v1):** `logins_30d >= 15`. Calibrate after real data lands.

**Tag computation rules:**
- `power` — logins_30d >= 15
- `paid_yearly` / `paid_monthly` — from Stripe + RevenueCat subscription type
- `trial` — active subscription with `status = 'trialing'`
- `trial_no_card` — trial with no payment method on file (Stripe only — RC trials always have an Apple ID payment context)
- `dormant` — registered > 30d ago, logins_30d == 0
- `churned` — had a paid subscription, now canceled, > 30d since cancellation
- `internal` — email in `INTERNAL_EMAILS` allowlist
- `ios` — has any `INITIAL_PURCHASE` event in `webhook_events` (RC source)

**Needs Attention computation:** the section at the bottom of the Users tab. New module `services/user_attention.py`. Rules:

```python
def compute_attention_queue() -> list:
    # Trial expirations without payment method
    # Power user with paid subscription whose last login > 5d (typical: < 2d)
    # Trial with payment method on file expiring in < 4d (status update only, not action)
    # ...
```

Cap at 8 items. Sort by priority (trial-no-card > churn risk > re-engage > on-track).

**Cohort retention query** is the heaviest piece. Group users by their `created_at` week, then for each cohort compute the % who logged in during week N after signup. Cache for 1 hour. Surface the actual SQL before applying — it's the most likely place for performance issues if the user_events table grows.

**Verification 3.5:**
- All charts and tables on Users tab render with real data
- Search bar filters in <200ms for typical queries
- Segment chips switch the visible list
- Cohort retention SQL uses indexes (EXPLAIN ANALYZE shows index scan, not seq scan)
- Attention queue surfaces real users in real states (not mocked)
- Mobile: user rows reflow into stacked label/value layout (matches mockup)

Stop and surface.

---

### Step 3.6 — Model tab

Charts:
- **Win rate vs market** (90-day rolling 14-day, by sport): new module `services/model_perf.py`. Pulls from `signals` joined to game results. NBA solid line, MLB dashed (lower confidence), break-even at 52.4% as a reference dashed line.
- **Signal hit rate by MEI tier**: bar chart with 4 tiers. Color-coded — high MEI tier in Edge Green, others in Signal Blue or muted.
- **Calibration plots** (NBA + MLB side-by-side scatter): predicted probability vs observed win rate, with a perfect-calibration diagonal.
- **MEI distribution histogram**: spread of MEI scores across all scored games last 30 days.

**New endpoint:** `GET /api/admin/model/perf?range=90d`. Cache TTL 1 hour (model perf doesn't change minute-to-minute).

**Last 10 issued signals** at the bottom: `SELECT ... FROM signals ORDER BY created_at DESC LIMIT 10` joined to game results to compute hit/miss. If a signal's game hasn't closed yet, render as `pending` instead of hit/miss.

This step depends on Darell knowing how the existing model stores its data — surface the schema for `signals`, `model_runs`, and game-results tables before proposing query SQL.

**Verification 3.6:**
- Charts render with real model data
- Calibration plots accurately reflect actual prediction vs outcome (sanity check: a few hand-computed points)
- Last 10 signals show real recent signals

Stop and surface.

---

### Step 3.7 — Infra tab

Server health chips: pull from Railway's API if available, otherwise compute from internal app metrics.

- **Uptime 30d**: from a new `health_checks` table that the app self-records every minute (Phase 4 reconciliation cron will write to it). For Phase 3 v1, hardcode "100%" if Railway API isn't easily callable — surface as a known gap.
- **p95 latency**: from request middleware. Add Flask middleware that records `request.duration_ms` to a rolling time-series table (`request_metrics`).
- **Errors 24h**: count of 5xx responses, same source.
- **Memory / CPU**: Railway API or `psutil` from inside the app process.

**p50/p95/p99 chart** (7 days): aggregates from `request_metrics`.

**Recent deploys**: parse `git log` from inside the running container, or pull from Railway's deploys API. For v1, file a TODO if Railway API requires more setup than budget allows.

**Pipeline status**: list of cron jobs and their last successful run. Read from a new `cron_runs` table that each cron writes to on completion. Status dot is green if ran in last expected window, amber if 1-2 windows late, red if more.

**Database health chips**: Postgres `pg_stat_*` views for connection count, storage, slow queries.

**This step has the most "TBD per environment" content.** Surface what's actually achievable on Railway before writing fake values. We'd rather ship Infra with 4 working chips than 8 chips half of which lie.

**Verification 3.7:**
- Server health chips show real values (or are explicitly marked TODO)
- Pipeline status reflects actual cron run state
- Deploy history shows the last 4 commits matching `git log`

Stop and surface.

---

### Step 3.8 — Auth and admin gating

Reuse Phase 2's `@admin_required` decorator. The dashboard is one route (`/admin`) plus the new endpoints under `/api/admin/`. All require admin session.

Confirm `ADMIN_EMAILS` allowlist still includes both `evan@sharppicks.ai` and `dev@sharppicks.ai`. Add a config note that this allowlist is the only auth gate — there's no role table.

**Verification 3.8:**
- Anonymous request to `/admin` returns 403 (or redirects to login, depending on existing pattern)
- Anonymous request to `/api/admin/metrics` returns 403
- Authenticated non-admin user returns 403

Stop and surface.

---

### Step 3.9 — Mobile verification

Test on actual iPhone (not just Chrome DevTools mobile emulation — real device).

- Open `/admin` on iPhone Safari
- Walk through all four tabs
- Verify no horizontal scroll anywhere except the cohort retention table on Users tab (intentional)
- Verify all touch targets are ≥44×44px
- Verify body copy renders ≥15px
- Verify the back button collapses to just the arrow on narrow viewports (<480px)

This is manual verification, no curl tests. Surface "verified on iPhone 14 Pro Safari, all tabs scroll cleanly" or list specific issues found.

---

## What Phase 3 deliberately does not include

- **No charts or tables Darell can't build with the data we have today.** Every chart in the mockup either has a real Phase 2 data source backing it, or is on the explicitly-TODO list (Infra tab specifically).
- **No customization, drag-to-reorder, theme picker, etc.** Static layout, opinionated.
- **No write operations from the dashboard.** Read-only with two persisted toggles.
- **No multi-user features.** One operator. No share links, no permissions UI.
- **No export buttons.** Copy-paste numbers if needed.
- **No mobile app version.** Web at `/admin`, used on iPhone Safari and desktop browsers.

## Done means

- All four tabs render with real data
- Mockup design is matched 1:1 in spacing, typography, color, layout
- Charts use Chart.js with the brand defaults
- Toggles persist across reloads
- Mobile verified on real iPhone
- No horizontal scroll anywhere except intentional (cohort table)
- Page loads in under 2s on cache hit, under 5s cold cache
- Every chart and table has a real data source — no placeholder `Math.random()` from the mockup remains

## Lessons from Phase 1 to carry forward

- **Sticky-tab problem.** The dashboard adds new client-side JS that consumers will have cached. If Phase 3 ever needs a breaking server-side response shape change, follow the same pattern Phase 1 used: keep both old and new shapes accepted at the server side for one deploy cycle.
- **Read-then-conditional-delete pattern** for any prod cleanup operations during testing.
- **Local SQLite-via-`db.create_all()` for handler verification** before deploying.
- **Manual diff approval gate** before any prod deploy.
- **Time-cap research at 20 minutes**, surface and ask if longer.
