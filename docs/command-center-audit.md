# Command center rebuild — Phase 0 audit

Read-only reconnaissance. No code changes in this phase. Everything below
is anchored to file:line references and live prod queries (run via the
postgres proxy URL on 2026-05-01).

## 0.1 Bet tap audit

### Client emission

There is exactly **one** `tap_bet_link` emission in the entire codebase:

- `src/components/sharp/PickCard.jsx:91` — fires inside `handleTrackPick`,
  which runs when the user submits the tracked-bet form (the "I placed
  this bet" confirmation modal). Payload: `{ game_id, pick_type:'spread',
  sportsbook }`.
- Transport: `trackEvent()` from `src/utils/eventTracker.js:125`, which
  enqueues to a 30-second batch flush via `apiPost('/events', ...)`.
- The fetch call (`apiPost`) does not use `keepalive: true` and does not
  fall back to `navigator.sendBeacon`.

There is no `place_own_bet` emitter anywhere. There is no outbound
sportsbook anchor (`target="_blank"`) anywhere in `PickCard.jsx` or
`BetTrackingScreen.jsx`. Greps for `target="_blank"` and `window.open`
in the components return only share-link helpers and external profile
links, none of which fire `tap_bet_link`.

### Spec mismatch — flagged

The spec's hypothesis 1 ("Handler fires on the outbound `target="_blank"`
anchor and the navigation kills the `fetch`") does not match current
code. There is no outbound bet-link tap surface to lose events on. The
emission today is on form submit (no nav). Evan's mental model of "tap
the signal card to bet" does not correspond to any wired event.

The spec's "two surfaces (signal card + place-own-bet)" should be
treated as **two surfaces to add**, not two surfaces with a known
transport bug.

### Server endpoint

- `app.py:3932` `POST /api/events` — registered directly on the app,
  not in a blueprint.
- **Auth: REQUIRES authenticated session** (`app.py:3935-3936`). Returns
  401 if `get_current_user_from_session()` is None. **No mechanism for
  unauthenticated event writes.** This is real and matches spec hypothesis
  2 partially: an unauthenticated tap is dropped at the door.
- Internal-user filter: **none in code.** The endpoint accepts events
  from any authenticated user including `evan@sharppicks.ai`, with no
  `is_internal` flag written to storage.
- Schema: writes to `user_events` table (`models.py:361`). Columns:
  `id, user_id, event_type, event_data (JSONB), page, session_id,
  created_at`. No `surface` column. No `is_internal` column. No
  IP/user_agent capture.

### Internal-user filter at READ side

Inside `admin_api.py:_admin_engagement_inner` (`admin_api.py:2667`), the
"feature adoption" aggregation counts unique `user_id` per event type.
There is **no Evan-exclusion** in this aggregation either. Evan's events
are counted alongside everyone else's.

### Last-30d event counts (live query, 2026-05-01)

```
page_view              2431
session_end            1618
session_start           915
view_model_performance  432
view_article            287
tap_bet_link             52   <-- emissions ARE landing
view_pick                26
view_market_scan          9
notification_opened       9
```

`tap_bet_link` last 30 days, per-row: 51 of 52 from
`evan@sharppicks.ai`, 1 from `isaac03.wilson@proton.me`. Last 7 days: 13
events from 2 unique users (Evan + Isaac).

### Spec mismatch — flagged

Spec says "the 1 bet tap visible on the funnel is from a real user, not
Evan." Live data: dashboard formula returns **2 unique users with
`tap_bet_link` in last 7d** (Evan + Isaac). Either the dashboard reads
something other than `feature_adoption`, the spec is misremembering, or
there's a UI rendering bug. Will need clarification before Phase 1
relies on the "1 vs 2" framing.

### What's actually broken

Three real defects, distinct from the spec's framing:

1. **No outbound bet-link surface exists.** Until that surface is built,
   "tap_bet_link" can only fire from form submit. Add an outbound
   sportsbook click handler (with `sendBeacon` transport) in Phase 1.
2. **Endpoint requires auth.** Logged-out taps from the marketing page
   or pre-login tappers (free-tier promo cards, etc.) are dropped. Any
   future unauthenticated emitter will silently fail. Phase 1 should
   make this endpoint accept unauthenticated writes with `user_id=null`.
3. **No surface field.** Even if both surfaces ship in Phase 1, the
   schema can't distinguish them. Add a `surface` column or emit it as
   `event_data.surface` and grep on JSONB.

## 0.2 Data source audit

### Cloudflare

Wired, partially.

- `admin_api.py:2210` `GET /api/admin/cf-analytics` — pulls Cloudflare
  GraphQL Analytics API (RUM page-load events) for `sharppicks.ai`
  marketing site only.
- Auth env vars: `CF_API_TOKEN`, `CF_ACCOUNT_ID`,
  `CF_WEB_ANALYTICS_SITE_TAG`. Returns 503 if unconfigured.
- Date range: configurable via `_analytics_period_days()`.
- Pulls: totals, daily breakdown, top paths, top referrers.
- **Gap:** the app subdomain (`app.sharppicks.ai`) is not in the RUM
  query; it has its own internal `PageView` table (admin endpoint
  `app-analytics`, `admin_api.py:2360`). Two separate "what is traffic"
  numbers come from two different systems.

### GA4

**Not wired.** No imports of `google-analytics-data` or
`google.analytics.data_v1beta` anywhere. No `GA4_PROPERTY_ID` env var
referenced. No service-account JSON. Phase 2 has to set up the GA4
property side as well as the SDK.

### Search Console

**Not wired.** No imports of `googleapiclient.discovery` for the Search
Console API. No `GSC_SITE_URL` env var. Phase 2 has to handle property
verification too.

### Stripe

Wired, but MRR is computed from internal `User` table, not Stripe.

- `stripe_client.py` exists (existing Stripe integration; not deeply
  reviewed in this audit — out of 20-min scope).
- `admin_api.py:913-915` MRR calc:
  ```python
  monthly_rev = len(monthly_subs) * 29
  annual_rev = len(annual_subs) * (99 / 12)
  mrr = round(monthly_rev + annual_rev, 2)
  ```
  Hardcoded prices ($29/mo, $99/yr). Reads from
  `User.subscription_plan` strings, not Stripe `plan.amount`. Live
  query: 15 active subs but only 2 match the formula's plan-name
  filter, so dashboard MRR = $37.25 — almost certainly wrong.
- `models.py:394` `MrrSnapshot` (`mrr_daily_snapshots`) exists for
  history. Population path not audited yet.

### Postgres event tables

- `user_events` (`models.py:361`) — see 0.1.
- `mrr_daily_snapshots` (`models.py:394`).
- `page_views` (`models.py:355`-ish, used by app-analytics).
- `content_page_views` (`models.py:372`) — separate table for SEO pages.
- No `product_events` table exists. Phase 1 can either (a) create one
  per spec, or (b) extend `user_events` with `surface` and
  `is_internal` columns to avoid table proliferation. Recommend (b)
  unless `user_events` schema migration is hard.

## 0.3 Mobile readability audit

`templates/admin.html` — 1803 lines, single-file SPA-ish.

- **Viewport correct:** `templates/admin.html:5` sets
  `width=device-width, initial-scale=1.0, user-scalable=no`. (The
  `user-scalable=no` is hostile to a11y; spec doesn't address but
  worth flagging.)
- **Body width:** line 33 sets `max-width:960px` with `overflow-x:hidden`.
  OK as a top-level container.
- **Tables horizontally scroll, do not stack.** Line 193 defines
  `.table-scroll{overflow-x:auto}`. Line 194 `.content-table{min-width:280px}`.
  Line 1251 user-table is wrapped in `overflow-x:auto` with
  `min-width:600px` — guaranteed horizontal scroll on a 375px screen.
  Spec requires stacked label/value lists below 640px; this is
  contradicted today.
- **Some media queries exist:** lines 260, 261, 276, 294, 309, 326 —
  the Business tab has SOME responsive grid breakdowns
  (`grid-template-columns:1fr` below 360px / 600px / 900px). Coverage
  is partial; many cards still rely on natural flex behavior.
- **Touch targets:** not audited in detail (would need to inspect each
  button's padding); the cron-row `.cron-ago` and `.user-date` use
  9-10px font with tight padding — likely below 44x44.
- **Tab structure:** in-page state, not real routes. Persisted via
  `localStorage`. No SPA framework.

## 0.4 Reconciliation audit

Three metrics, each with the source-of-truth query and the dashboard's
computed value.

### Metric 1: Active subscribers (Business tab)

- Source of truth: `SELECT COUNT(*) FROM users WHERE subscription_status='active'`
  → **15** as of 2026-05-01.
- Dashboard reads from `len(active_subs)` at `admin_api.py:899` — same
  query semantically, no discrepancy.
- **Match.**

### Metric 2: Monthly Recurring Revenue (Business tab)

- Source of truth: Stripe API (active subscriptions, sum of monthly
  amounts). Not queried in this audit (no Stripe SDK calls in
  reconciliation script).
- Dashboard: `admin_api.py:913-915`. Formula:
  `(monthly_subs_count * 29) + (annual_subs_count * 99/12)`. Live:
  monthly_subs_count = 1, annual_subs_count = 1 → MRR = **$37.25**.
- 13 of 15 active subs have NULL or unrecognized `subscription_plan`
  strings and contribute $0 to dashboard MRR. **Almost certainly
  divergent from Stripe truth.** Phase 2 must replace this with a
  Stripe API pull.

### Metric 3: tap_bet_link unique users last 7d (Funnel/Engagement)

- Source of truth: `SELECT COUNT(DISTINCT user_id) FROM user_events
  WHERE event_type='tap_bet_link' AND created_at > NOW()-INTERVAL '7 days'
  AND user_id IS NOT NULL` → **2** (Evan + Isaac).
- Dashboard reads `feature_adoption.tap_bet_link.users` which uses the
  same logic at `admin_api.py:2710-2745`. Should also report 2.
- **If the rendered dashboard shows "1," there is a UI bug or stale
  cache somewhere between server and template.** Spec says "1 bet
  tap visible from a real user" which I cannot reproduce against live
  data. Flagged for clarification.

## Open questions — answers

1. **Is there already a `/api/events` endpoint?**
   Yes — `app.py:3932`. **Schema does not match spec.** Required
   fields: `events` array of objects with `event_type`, `event_data`,
   `page`, `session_id`, `timestamp`. Spec wants single-event payload
   with top-level `event`, `surface`, `signal_id`, `sport`, `ts`,
   `client_ts`. Phase 1 needs a migration plan: either accept both
   shapes, or roll out a new `/api/events/v2` and migrate the client.

2. **Is the existing dashboard auth gated on email allowlist or a
   real role table?**
   Email allowlist + role flag, both required (`admin_api.py:23-30`).
   `ADMIN_EMAIL = 'evan@sharppicks.ai'` is hardcoded. Auth requires
   `current_user.is_superuser AND current_user.email == ADMIN_EMAIL`.
   Lives in `admin_api.py:23`. Phase 1 internal-user allowlist for
   event tagging should reuse this constant; do not introduce a
   second source of truth.

3. **Does the app already have a Slack alerting path?**
   Not audited deeply within 20-min cap. Greps for "slack" in *.py
   show no Slack webhook integration in scope. There is an `AdminAlert`
   model (`models.py:382`) and an admin-alert cron, but it appears to
   be in-app alert rows, not Slack. Phase 4 likely needs a new Slack
   path. Flag and confirm before adding.

4. **Are GA4 and Search Console set up as properties yet?**
   No code-side setup. Whether the GA4 property exists in Google's
   side and whether the site is verified in Search Console is not
   knowable from the codebase. **Evan must confirm property setup
   before Phase 2 SDK work; if not set up, that's a separate blocker.**

5. **Is there an existing `product_events` or `analytics_events`
   table we should extend?**
   `user_events` is the closest existing table. It already has
   `event_type`, `event_data`, `user_id`, `session_id`, `created_at`.
   Missing relative to spec: `surface`, `is_internal`, `signal_id`,
   `sport`, `client_ts`/`server_ts` distinction (only `created_at`
   exists), `ip`, `user_agent`. Recommend extending `user_events` with
   the missing columns rather than creating a parallel
   `product_events`. Avoids dual writes and double aggregation paths.
   Schema migration scope: 6 new columns + indexes.

## Conflicts with spec — summary

Stop and decide on these before Phase 1:

- **Spec hypothesis 1 (transport-on-outbound) does not match code.**
  No outbound bet-link surface exists. Phase 1 work is "build the
  surface and instrument it correctly," not "fix existing transport."
- **Spec hypothesis 2 (auth requirement drops events) IS true** for
  any unauthenticated tap. Spec section 1.1 asks for "no auth
  required" which is a real change.
- **Spec table `product_events` collides with existing `user_events`.**
  Recommend extending the existing table.
- **Spec's "1 bet tap from a real user" claim is not reproducible.**
  Live data shows 2 unique users in last 7d. Need clarification on
  what dashboard widget Evan was looking at.
- **MRR calc is computed from User table, not Stripe.** Spec's Phase 2
  Stripe pull is a meaningful correction, not just a refresh.
- **GA4 and Search Console are not wired at all** (not partial). Phase
  2 is greenfield work for both, including potential property setup
  that may require Evan's hands.

## What's next

Hold here. Before Phase 1 starts, decide:
- Extend `user_events` vs new `product_events`?
- Confirm "1 bet tap" framing — what widget, what number Evan saw?
- Confirm GA4 + GSC property setup status?
- Confirm Slack alerting path exists or needs new wiring?

No code changes have been made. Files modified by this audit: this doc
only.

---

## Phase 1 implementation notes (added 2026-05-01)

### `created_at` semantic shift at the Phase 1 deploy boundary

Pre-Phase-1, `/api/events` mapped the client-supplied `timestamp` field into
`user_events.created_at` directly. Post-Phase-1, the server sets
`created_at` to the server-side wall clock (`datetime.utcnow()`) and the
client's wall clock lands in the new `client_ts` column.

Implication for any timeseries grouped by `created_at`:

- Rows written before the deploy carry client-side time (subject to
  client clock skew and the up-to-30s eventTracker batch flush delay).
- Rows written after the deploy carry server-side time at the moment of
  insert.

The discontinuity is small in practice (skew typically < 1 minute) but
non-zero. Phase 4 reconciliation should not treat `created_at`
distributions as continuous across the Phase 1 deploy date.

### Returning 200 with `{"ok": true}` instead of 204 No Content

Returning 200 with `{'ok': true}` instead of 204 is a deliberate
concession to single-deploy architecture. Frontend bundle and Flask
backend ship in one Railway artifact, so we cannot land a client-side
204 handler before the server starts returning 204. Browser tabs already
loaded at deploy time would hit the new server with the old client (no
204 handler), eventTracker would fail to parse the empty body, and the
retry queue would back up until the user reloaded. The 200-with-body
shape is parseable by every version of the client. Do not change to 204
without solving the sticky-tab transition first.

The companion `apiPost` 204-handling tweak shipped in `useApi.js` is a
defensive fix: future endpoints can return 204 without breaking new
browsers, but `/api/events` itself stays on 200-with-body for the
sticky-tab reason above.

### `INTERNAL_EMAILS` allowlist

Module-level constant in `app.py`, env-overridable via the
`INTERNAL_EMAILS` env var (comma-separated). Default is
`['evan@sharppicks.ai']`, matching the existing `ADMIN_EMAIL` constant
in `admin_api.py:23`. Lowercase normalized at parse time. Used to set
`user_events.is_internal = true` server-side at write time.

### Phase 1 ground truth (snapshot 2026-05-01)

For Phase 2 to start from current state, here's what shipped:

**Schema (Step 1.1):** `migrations/2026-05-01-extend-user-events.sql`
applied to prod. 7 new columns on `user_events`: `surface`,
`is_internal` (NOT NULL DEFAULT false), `signal_id`, `sport`,
`client_ts` (TIMESTAMPTZ), `ip` (INET), `user_agent`. 2 new indexes:
`ix_user_events_event_type_created_at` (composite), `ix_user_events_surface`.
Backfill set `is_internal=true` for 5588 rows tied to
`evan@sharppicks.ai`.

**Server (Step 1.2):** `app.py` route `POST /api/events`
(`post_user_events`). Accepts both new single-event shape
(`{event, surface, signal_id, sport, client_ts, ...}`) and old batch
shape (`{events: [...]}`). No auth wall. Both `application/json` and
`text/plain` content types accepted (sendBeacon path). 60-second
dedupe on (event_type, client_ts, signal_id, surface, ip). Returns
`{"ok": true}` 200 (NOT 204). Server-side: attaches `user_id` from
session if present, computes `is_internal` from `INTERNAL_EMAILS`,
sets `created_at = utcnow()`, captures `ip` and `user_agent`.

**Client (Step 1.3):** `src/utils/track.js` is the new helper —
sendBeacon-first, fetch-with-keepalive fallback. Wired at:
- `src/components/sharp/PickCard.jsx:handleTrackPick` — emits
  `bet_tap` with `surface=signal_card`. Existing
  `trackEvent('tap_bet_link', ...)` left in place alongside.
- `src/components/sharp/BetTrackingScreen.jsx:handleSubmitBet` —
  emits `bet_tap` with `surface=place_own_bet`. Manual / parlay
  sub-paths pass `signal_id=null` and `sport=null`.

**Event-type cohorts in `user_events` for Phase 2 funnel queries:**
- Pre-1.3: `event_type='tap_bet_link'`, no surface, ~52 rows over 30d.
- Post-1.3 from PickCard: both `tap_bet_link` AND `bet_tap` fire from
  the same handler. The `bet_tap` row carries `surface=signal_card`.
- Post-1.3 from BetTrackingScreen: `bet_tap` with
  `surface=place_own_bet` (no `tap_bet_link`).

Phase 2 funnel queries that want pre/post continuity:
`WHERE event_type IN ('tap_bet_link', 'bet_tap')`. Queries that need
surface granularity: `WHERE event_type = 'bet_tap'` and group by
`surface`.

## Phase 2 event-name mapping (added 2026-05-01)

The Phase 2 spec uses generic terms like `signal_view` and
`bet_tap_signal_card` for funnel steps. Actual emissions in the code
use different concrete names. Mapping used by `services/sources/events.py`:

| Spec funnel step       | Actual `user_events` query                              |
|------------------------|---------------------------------------------------------|
| `signal_view`          | `event_type='view_pick'`                                |
| `bet_tap_signal_card`  | `event_type='bet_tap'` AND `surface='signal_card'`      |
| `bet_tap_place_bet`    | `event_type='bet_tap'` AND `surface='place_own_bet'`    |

`signals_issued` does NOT come from `user_events` — signals are
system-generated when the model writes a Pick. The events source
queries the `picks` table directly grouped by sport.

Anonymous users (user_id IS NULL) are excluded from the funnel — we
cannot follow them across steps without session-level identity. Future
improvement: COALESCE(user_id::text, session_id) for logged-out users.
