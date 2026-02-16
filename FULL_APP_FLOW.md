# Sharp Picks - Full Application Flow
*Generated February 16, 2026 · Last updated February 16, 2026 (token-based auth, cron schedules, dual signup, transparency metrics, admin auth)*

---

## 1. LANDING PAGE (Unauthenticated Users)

**URL:** `/`

Dark institutional-grade design on `#0A0D14` background. Top-level brand mark: shield icon + "SHARP PICKS."

### Hero Section
- Headline: **"One Pick Beats Five"**
- Subtitle: *"Discipline is the product."*
- Primary CTA: Blue gradient "Start 14-Day Trial" button (opens AuthModal with `initialAccountType='trial'`)
- Secondary CTA: "Create Free Account" link (opens AuthModal with `initialAccountType='free'`)
- Sub-CTA: "Card required to start trial. Cancel anytime."

### Transparency Metrics (replaces volatile win-rate stats)
Three stat cards showcasing long-term discipline signals:
1. **Selectivity** — percentage of days a pick is published (lower = more disciplined)
2. **Picks / Passes** — raw count of published picks vs pass days
3. **Deleted** — always 0 (append-only transparency guarantee)

*Design rationale:* These metrics only improve over time as the track record grows, unlike win rate which can fluctuate and look bad early on with a small sample.

### Trust Bar
- `Active since Jan 2026 · All picks public · 0 deleted`

### Value Propositions (3 cards)
1. **No edge, no pick** — "We publish only when the model identifies sufficient value. Quiet days are intentional."
2. **Process over outcomes** — "All picks tracked publicly. No deletes. No hindsight editing."
3. *[Third card below fold]*

### Free vs Pro Comparison
Landing page includes a tier comparison showing what free users get (model activity, public record, pass-day summaries) vs what Pro users unlock (pick details, bet tracking, performance dashboard).

### Bottom CTA
- Dual CTA matching hero: "Start 14-Day Trial" (primary) + "Create Free Account" (secondary)

---

## 2. REGISTRATION / LOGIN

### Registration (Dual Signup Flow)
**Fields:** first_name, last_name, email, password
**AuthModal:** Shows both paths with "Start Trial — Card Required" (primary) and "Create Free Account" (secondary) buttons. Neutral subtitle: no pressure language.

#### Path A: Trial Account (`account_type='trial'`)
1. Gmail alias normalization applied (strips dots and +suffixes for gmail.com/googlemail.com)
2. `trial_used` flag checked — prevents repeat trials on same normalized email
3. User created with `subscription_status: "free"`, `is_premium: false`, `email_verified: false`
4. Verification email sent via Resend with signed, time-limited token (24h expiration)
5. User sees verification prompt: "Check your email for a verification link"

**Email verification flow:**
1. User clicks link in email → `/api/auth/verify-email?token=...`
2. Token validated (signature + expiration)
3. `email_verified` set to `true`
4. User redirected to Stripe checkout for card-on-file trial setup

**Card-on-file trial (via Stripe):**
1. Stripe checkout session created with `trial_period_days=14`, `payment_method_collection: 'always'`
2. $0 charged upfront, card stored on file
3. On successful checkout webhook: `subscription_status: "trial"`, `is_premium: true`, `trial_end_date` set to 14 days out, `trial_used: true`
4. After 14 days, Stripe automatically charges the selected plan unless cancelled

#### Path B: Free Account (`account_type='free'`)
1. Gmail alias normalization applied
2. User created with `subscription_status: "free"`, `is_premium: false`, `email_verified: true` (skips verification)
3. Welcome email sent (not verification email) via `send_welcome_email()`
4. User lands directly in the app — no email gate, no Stripe checkout
5. Free users see limited dashboard: model activity, public record, pass-day summaries
6. Pick details (side, spread, edge %), bet tracking, and performance dashboard hidden behind upgrade CTA

*Design rationale:* Free tier reduces trial abuse by giving tire-kickers a home without burning a trial slot. Users who just want to browse don't need a 14-day trial.

### Login
- Email + password authentication
- Hybrid auth: Flask-Login session + signed Bearer token (itsdangerous, 30-day TTL)
- Token returned in login response, stored in localStorage, sent as `Authorization: Bearer` header
- Server checks Flask session first, falls back to Bearer token (required for autoscale where sessions don't persist)
- Session token validated on every request (invalidated on password reset)
- **Rate limiting:** 5 failed login attempts → 15-minute lockout per email

### Password Reset
- Secure time-limited token flow via `/api/auth/forgot-password` and `/api/auth/reset-password`
- On reset: `session_token` regenerated → all existing sessions invalidated

---

## 3. AUTHENTICATED DASHBOARD (4-Tab Shell)

After login, users see the main dashboard with 4 tabs:

### First-Time Onboarding
New users see an onboarding flow with steps including:
- Welcome + product philosophy
- How picks work
- **Pass-day preview** — "Most days look like this" with a mini no-pick card showing what a typical pass day looks like
- Notification preferences setup

### Tab Navigation
| Tab | Icon | Content |
|-----|------|---------|
| **Picks** | Chart trend icon | Today's pick or no-pick state |
| **Insights** | Book icon | Educational content + discipline coaching |
| **Performance** | Bar chart icon | Model performance + bet tracking stats |
| **Profile** | User icon | Account, subscription, settings |

---

### 3A. PICKS TAB (Default)

**Trial Banner:** Shows "PRO TRIAL · X DAYS LEFT" with countdown and urgency pulse animation for last day

**Active Pick State (when model finds edge):**
- Pick card showing: team, spread line, edge percentage, sportsbook
- Detailed analysis notes (rest days, scoring margins, defensive matchups)
- "Track This Bet" button for personal bet tracking
- Confidence level and model explanation

**No Pick / Pass State (most days):**
- Calm "no pick today" messaging
- What-if analysis: shows what the model's closest call was
- Pass reason documented

**Free-Tier Users:**
- Can see whether a pick exists today
- Pick details blurred/hidden behind upgrade CTA
- "Full decision visibility ends after trial" notice

**Current picks record:** 9 picks published, 23 passes

**Sample picks from public record:**
| Date | Pick | Line | Edge | Result |
|------|------|------|------|--------|
| 2026-02-12 | Los Angeles Lakers | -7.5 | 10.0% | W |
| 2026-02-11 | Philadelphia 76ers | +24.5 | 10.0% | L |
| 2026-02-02 | Charlotte Hornets | -8.5 | 4.1% | L |
| 2026-02-01 | LA Clippers | +0.5 | 6.4% | W |
| 2026-01-31 | Chicago Bulls | +5.0 | 5.8% | W |
| 2026-01-30 | Los Angeles Lakers | +5.0 | 7.7% | W |
| 2026-01-29 | Houston Rockets | +4.5 | 5.1% | W |
| 2026-01-28 | San Antonio Spurs | -2.5 | 8.2% | W |
| 2026-01-27 | Detroit Pistons | +2.0 | 4.5% | W |

**Pick record:** 7W-2L on published picks (77.8% win rate)
**Edge range:** 4.1% to 10.0% (capped at 8% post-calibration, with "Pre-Cal" tags for earlier picks)

---

### 3B. INSIGHTS TAB

Educational content on:
- Betting discipline methodology
- Market dynamics and line movement
- Model methodology explanation
- Category filters for content
- Pass-day CTA integration (links to understanding why no-pick days matter)

---

### 3C. PERFORMANCE TAB

**Overall Stats:**
- Total predictions tracked: 67 (from model runs)
- Record: 20W-30L (40% on all model runs, NOT just published picks)
- Published picks record: 7W-2L (77.8%)
- Pending: 17

**Closing Line Value (CLV) Tracking:**
- Beat closing rate: tracked per pick
- Average line movement: monitored

**Model Calibration:**
- Confidence buckets: 50-55%, 55-60%, 60-65%, 65-70%, 70-75%, 80-100%
- Calibration status: "excellent" (on published picks)

**User Bet Tracking:**
- Personal equity curve
- Monthly breakdown
- ROI, win rate, streak tracking
- Adherence score: how closely user follows published picks

**Behavioral Analytics:**
- Capital preserved percentage
- Selectivity score
- Picks followed vs. picks passed
- Industry average comparison (78% capital preservation)

**Free-tier users:** See blurred/abstract performance charts with upgrade CTA

---

### 3D. PROFILE TAB

**Account Management:**
- Display name, email
- Unit size setting (default: $100)
- Notification preferences:
  - Pick alerts: ON/OFF
  - Outcome notifications: ON/OFF
  - Weekly summary: ON/OFF
  - No-action day alerts: ON/OFF

**Subscription Management:**
- Current plan display with tier badge (FREE / PRO TRIAL / PRO / FOUNDING)
- Trial countdown with progress bar and days remaining
- Upgrade/downgrade options
- Cancel subscription flow (sets `cancel_at_period_end`, access continues until period end with "cancelling" status)
- **Reactivation:** `/api/subscriptions/reactivate` reverses `cancel_at_period_end` for users who change their mind

**Pricing Section:**
| Plan | Price | Notes |
|------|-------|-------|
| Free | $0 | See if a pick exists today, public record access |
| Monthly | $29/mo | Card required to start 14-day trial. Cancel anytime. |
| Annual | $99/yr (founding) / $149/yr (standard) | Founding rate locked for first 500 members |

**Trial Signup (within pricing):**
- Heading: "14-Day Trial"
- Description: "Full access to all picks and features. Card required to start — cancel anytime."
- Button: "Start Trial"
- Fine print: "$0 today — you won't be charged until your trial ends. $29/mo or $99/yr (founding rate). Cancel anytime."

**Referral Program:**
- Personal referral code (format: SHARP-XXXX)
- Referral tracking
- Both referrer and referred get a month of free access

---

## 4. SUBSCRIPTION SYSTEM

### Plans (via Stripe)
| Plan | Price | Stripe Price ID | Notes |
|------|-------|-----------------|-------|
| Monthly | $29/mo | `STRIPE_PRICE_MONTHLY` | Cancel anytime |
| Founding Annual | $99/yr | `STRIPE_PRICE_FOUNDING` | Locked forever, 500-member cap |
| Standard Annual | $149/yr | `STRIPE_PRICE_ANNUAL` | Standard annual rate |

### Trial Flow (Card-on-File)
1. New user registers → email verified → Stripe checkout with card collection
2. $0 charged, `trial_period_days=14` on Stripe subscription
3. Webhook sets `subscription_status: "trial"`, `is_premium: true`, `trial_used: true`
4. 2-day warning email sent via `check_expiring_trials` cron job
5. Trial expiration: `expire_trials` cron job sets status to "expired", sends expired email
6. If user doesn't cancel, Stripe auto-charges after 14 days → webhook sets "active"

### Subscription Lifecycle
- **active**: Paid subscriber with full access
- **trial**: Active trial with full access
- **cancelling**: User cancelled but access continues until `current_period_end`
- **expired**: Trial ended without payment
- **free**: No active subscription

### Anti-Abuse Measures
- `trial_used` flag prevents repeat free trials per normalized email
- Gmail alias normalization (removes dots, strips +suffixes)
- Card-on-file requirement eliminates casual abuse
- Email verification required before any trial access

### Webhook Security
- **ProcessedEvent table:** Every Stripe event ID stored on first processing
- **Idempotency:** Insert-first pattern — if event ID already exists, skip processing
- **Atomic founding assignment:** PostgreSQL `FOR UPDATE` row-level lock on FoundingCounter prevents race conditions

### Current Users
| Status | Count |
|--------|-------|
| Trial | 5 |
| Active (paid) | 1 (Founding #1) |
| Free (expired) | 3 |
| Cancelling | 1 |
| **Total** | **13** |

---

## 5. SECURITY & AUTHENTICATION

### Hybrid Auth System (Session + Bearer Token)
Autoscale-compatible authentication using both Flask sessions and signed Bearer tokens. Required because Flask sessions don't persist across Replit autoscale instances — cookies are sent but session validation fails on different replicas.

**Token implementation:**
- Signed using `itsdangerous.URLSafeTimedSerializer` with `SESSION_SECRET`
- Token payload: `{uid: user_id, st: session_token}` with salt `'auth-token'`
- 30-day TTL, stored in localStorage as `sp_auth_token`
- Sent as `Authorization: Bearer <token>` header on all API requests
- Server-side invalidation via `session_token` rotation (on password reset, logout)

**Auth resolution order (all protected endpoints):**
1. Flask-Login session (if available)
2. Flask session `user_id` + `session_token` validation
3. Bearer token verification (itsdangerous signature + session_token match)

**Token flow:**
- Login/register/auth-user endpoints return `token` in JSON response
- Frontend (`useApi.js`) auto-stores token from any API response containing `token` field
- `useAuth.jsx` stores token on login/register, clears on logout
- All `apiPost()`, `apiGet()`, `apiDelete()`, `useApi()` attach Bearer header automatically

**Blueprint auth migration:**
- `picks_api.py`: Replaced `flask_login.current_user` with `get_current_user_obj()` (supports token fallback)
- `insights_api.py`: Local `get_current_user()` now delegates to `get_current_user_obj()`
- `admin_api.py`: `require_superuser()` checks Flask-Login → X-Admin-Token → Bearer token (triple auth)
- `app.py`: All `@login_required` decorators replaced with `get_current_user_obj()` calls

### Login Security
- **Rate limiting:** 5 failed attempts per email → 15-minute lockout
- Lockout tracked by email address with timestamp
- Failed attempt counter resets on successful login

### Email Verification
- Required before trial access
- Signed token with 24-hour expiration
- Resend verification endpoint available

### CORS Configuration
- **Production:** Restricted to `sharppicks.ai` domains only
- **Development:** Allows Replit dev domains + localhost

### API Access Controls
| Endpoint | Auth Required | Access Level |
|----------|--------------|--------------|
| `/api/predictions` | Yes | Pro users only (is_pro) |
| `/api/recent-results` | Yes | Pro users only (is_pro) |
| `/api/model/calibration` | Yes | Pro users only (is_pro) |
| `/api/performance` | No | Public (aggregate record only) |
| `/api/public/stats` | No | Public |
| `/api/public/record` | No | Public |
| `/admin` | Yes | Superuser only (is_superuser) |
| `/api/admin/*` | Yes | Superuser only |
| `/api/cron/*` | X-Cron-Secret header | Server-to-server only |

### Stripe Webhook Security
- Signature verification in production (via `STRIPE_WEBHOOK_SECRET`)
- Event idempotency via ProcessedEvent table
- Atomic operations for founding member assignment

---

## 6. NOTIFICATIONS & ENGAGEMENT

### Push Notifications (OneSignal)
Requires `ONESIGNAL_APP_ID` + `ONESIGNAL_API_KEY` environment variables.

| Notification | Trigger | Segment |
|-------------|---------|---------|
| Pick alert | Qualified pick published | "Pro Users" |
| Pass-day alert (no games) | No games scheduled today | "Pass Alerts" |
| Pass-day alert (paper trade) | WNBA paper trade only | "Pass Alerts" |
| Pass-day alert (below threshold) | No edge met threshold | "Pass Alerts" |
| Win result | Pick graded as win | "Pro Users" |
| Loss result | Pick graded as loss | "Pro Users" |
| Push result | Pick graded as push | "Pro Users" |

### Lifecycle Emails (Resend)
| Email | Trigger | Content |
|-------|---------|---------|
| Verification | Registration | Verify email link (24h expiration) |
| Trial expiring | 2 days before trial end | Reminder to subscribe |
| Trial expired | Trial end date passed | Prompt to upgrade |
| Cancellation | User cancels subscription | Confirmation + access end date |
| Payment failed | Stripe payment_intent.failed | Prompt to update payment method |
| Weekly summary | Monday 9 AM ET | Weekly stats for pro users with `weekly_summary` pref |

### Weekly Summary Email
- Sent Monday 9 AM ET to all pro users with `weekly_summary` notification preference enabled
- Contains global model stats for the week (not per-user tracking)
- Delivered via Resend API

### Onboarding Flow
Multi-step onboarding for new users including:
- Welcome and philosophy
- How picks work
- **Pass-day step:** "Most days look like this" — shows mini no-pick preview to set expectations
- Notification preferences setup

---

## 7. POST-CALIBRATION MODEL (Feb 12, 2026)

### Core Parameters
- **MODEL_WEIGHT:** 0.3 (30% model, 70% market)
- **MAX_EDGE_PCT:** 8.0% cap on displayed edges
- **EDGE_THRESHOLD:** 3.5% minimum to publish a pick
- **Market shrinkage validated:** Model MAE 12.03 vs Market MAE 10.06

### Prediction Pipeline
1. Collect today's games from ESPN
2. Fetch real-time odds from 6 sportsbooks (DraftKings, FanDuel, BetMGM, Caesars, PointsBet, BetRivers)
3. ML ensemble (56 features) predicts margin
4. Apply 30/70 shrinkage: `blended_margin = 0.3 * model + 0.7 * market`
5. Compute cover probability via Normal CDF with calibrated sigma
6. Compare to implied probability (-110 standard juice)
7. If edge >= 3.5%, publish pick; otherwise pass with what-if analysis
8. Maximum 1 pick per day
9. Push notification sent (pick alert or pass-day alert)

### Risk Filters
- High spread exclusion
- Missing data exclusion
- Stale data / imminent tip-off failsafe
- Line movement penalty: 1.0 per point moved, hard stop at 2.5pts

---

## 8. DATA ARCHITECTURE

### PostgreSQL (Primary - Application Data)
| Table | Purpose |
|-------|---------|
| `users` | User accounts, subscriptions, preferences, trial tracking, founding status |
| `picks` | Published predictions (append-only, one per day max) |
| `passes` | No-pick days with what-if analysis (append-only) |
| `model_runs` | Every model execution logged per sport |
| `tracked_bets` | User bet tracking against published picks |
| `founding_counter` | Atomic founding member slot counter (500 cap) |
| `insights` | Educational content for Insights tab |
| `processed_events` | Stripe webhook idempotency tracking |
| `cron_logs` | Cron job execution history (job_name, status, duration_ms, message) |
| `referrals` | Referral tracking |

### SQLite (Legacy - ML Training)
- Historical NBA game data
- ML model training datasets
- WNBA backtest data (753 games across 2022-2024)

### Key Design Principles
- **Append-only:** Picks and passes never deleted or modified
- **Full transparency:** Complete audit trail of all predictions
- **Eastern Time:** All date logic standardized to America/New_York

### Database Backups
- Daily pg_dump at 3 AM ET to `/tmp/backups/` (keeps last 7 days)
- JSON backup of picks, passes, and users (sensitive fields stripped)
- Generic SQLAlchemy serializer (no per-model `to_dict()` needed)
- Note: `/tmp` is ephemeral on Replit deploys; production needs external storage or Replit PostgreSQL snapshots

---

## 9. API ENDPOINTS

### Authentication
| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/api/auth/register` | No | Create account (triggers verification email) |
| POST | `/api/auth/login` | No | Login with email/password (rate limited) |
| POST | `/api/auth/logout` | Yes | End session |
| GET | `/api/auth/user` | Yes | Get current user data |
| GET | `/api/auth/verify-email` | No | Verify email via signed token |
| POST | `/api/auth/resend-verification` | No | Resend verification email |
| POST | `/api/auth/forgot-password` | No | Request password reset |
| POST | `/api/auth/reset-password` | No | Complete password reset (invalidates sessions) |
| POST | `/api/auth/unit-size` | Yes | Set bet unit size |
| POST | `/api/auth/trial` | Yes | Trial management |
| GET | `/api/auth/check-trial` | Yes | Check trial status |

### Picks & Predictions
| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/api/predictions` | Pro | Today's published picks |
| GET | `/api/recent-results` | Pro | Last 5 resolved picks |
| GET | `/api/performance` | No | Overall win/loss record (public) |
| GET | `/api/model/calibration` | Pro | Model calibration data |
| GET | `/api/picks/today` | Yes | Today's pick for authenticated users |
| GET | `/api/public/stats` | No | Public aggregate stats |
| GET | `/api/public/record` | No | Public pick record |
| GET | `/api/public/founding-count` | No | Founding member count |

### User Bet Tracking
| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/api/bets` | Yes | User's tracked bets |
| POST | `/api/bets` | Yes | Track a new bet |
| GET | `/api/bets/trackable` | Yes | All picks available to track |
| POST | `/api/bets/:id/result` | Yes | Record bet result |
| DELETE | `/api/bets/:id` | Yes | Remove tracked bet |
| GET | `/api/user/stats` | Yes | Comprehensive user analytics |

### Subscriptions
| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/api/subscriptions/create-checkout` | Yes | Start Stripe checkout (card-on-file trial) |
| POST | `/api/subscriptions/cancel` | Yes | Cancel subscription (cancel_at_period_end) |
| POST | `/api/subscriptions/reactivate` | Yes | Reverse cancellation |
| GET | `/api/subscriptions/status` | Yes | Current subscription state |
| GET | `/api/stripe/config` | No | Stripe publishable key |
| GET | `/api/stripe/products` | No | Available plans + prices |
| POST | `/webhooks/stripe` | No* | Stripe webhook handler (*signature verified) |

### Notifications & Profile
| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/api/user/notifications` | Yes | Notification preferences |
| POST | `/api/user/notifications` | Yes | Update notification prefs |

### Cron Endpoints (External Trigger)
All secured by `X-Cron-Secret` header. All log execution to `cron_logs` table.

| Method | Path | Schedule (cron-job.org) | Purpose |
|--------|------|------------------------|---------|
| POST | `/api/cron/collect-games` | Daily 9:00 AM ET | Fetch today's NBA games |
| POST | `/api/cron/refresh-lines` | Every 2 hours, 10 AM–6 PM ET | Refresh odds from all sportsbooks |
| POST | `/api/cron/closing-lines` | Daily 6:30 PM ET | Capture closing lines before tipoff |
| POST | `/api/cron/grade-picks` | Daily 12:00 AM ET | Grade pending picks |
| POST | `/api/cron/grade-whatifs` | Daily 12:30 AM ET | Grade what-if passes |
| POST | `/api/cron/expire-trials` | Daily 8:00 AM ET | Expire trials + 2-day warnings |
| POST | `/api/cron/weekly-summary` | Mon 9:00 AM ET | Send weekly summary email |
| POST | `/api/cron/backup` | Daily 3:00 AM ET | pg_dump + JSON backup |
| POST | `/api/cron/check-data-quality` | Daily 7:00 AM ET | Validate data integrity |

**External scheduler:** cron-job.org (all endpoints hit via HTTPS POST with `X-Cron-Secret` header)

### Admin (Superuser Only)
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/admin` | Admin Command Center dashboard (HTML) |
| GET | `/api/admin/command-center` | Revenue, model stats, users, picks, runs |
| GET | `/api/admin/health-checks` | External service health (PG, APIs, Stripe) |
| GET | `/api/admin/cron-health` | Cron job health monitoring |
| GET | `/api/admin/users` | Full user list |
| GET | `/api/admin/users/export` | CSV user export |
| GET | `/api/admin/export` | Full model data export |
| POST | `/api/admin/retro-calibrate` | Retroactive calibration analysis |

---

## 10. ADMIN COMMAND CENTER (`/admin`)

Superuser-only dashboard with auto-refreshing panels.

**Auth approach (autoscale-compatible):** Admin HTML route loads without server-side auth gate. All data fetched client-side via `/api/admin/*` endpoints. `require_superuser()` uses triple auth: Flask-Login session → X-Admin-Token header/query param → Authorization Bearer token (with session_token validation). Returns 401 (not logged in) or 403 (not authorized). This pattern works reliably in Replit's autoscale deployment where Flask sessions don't persist.

### Revenue & Sales (refreshes every 30s)
- MRR, ARR, active subscribers breakdown
- Founding member count with progress bar (X/500)
- User distribution: paid, trial, free, founding

### NBA/WNBA Model Performance
- Season record, win rate, ROI
- Selectivity (picks vs passes ratio)
- Confidence buckets (3.5-5%, 5-7.5%, 7.5-10%)
- Pre-cal vs post-cal breakdown
- CLV positive rate
- Equity curve visualization
- Recent picks with results
- Model run history

### Infrastructure
- **Cron Job Health** (refreshes every 30s): Per-job status with last run time, duration, success rate, overdue detection
- **External Services** (refreshes every 60s): PostgreSQL, Odds API, balldontlie, ESPN, Resend, Stripe — with latency, remaining quota, connection status
- Model runs log
- Content/insights count

### Users
- Recent user table with email, name, tier badge, plan, signup date, trial end countdown

---

## 11. FRONTEND COMPONENT ARCHITECTURE

```
src/
  App.jsx                          # Router: / -> SharpPicksApp, /reset-password -> ResetPassword
  pages/
    SharpPicksApp.jsx              # Main app shell with auth routing + email verification gate
  hooks/
    useApi.js                      # API helpers with Bearer token auth (setAuthToken, getAuthToken, authHeaders)
    useAuth.jsx                    # Authentication context + provider (stores/clears token on login/logout)
    useSport.jsx                   # Sport selection context (NBA/future WNBA)
  components/sharp/
    LandingPage.jsx                # Marketing page (card-on-file trial copy)
    AuthModal.jsx                  # Login/Register/Verify modal
    AppHeader.jsx                  # Top header bar (+ admin Command Center link for superusers)
    TabNav.jsx                     # 4-tab navigation (Picks, Insights, Performance, Profile)
    OnboardingFlow.jsx             # First-time onboarding with pass-day step

    # Picks Tab
    PicksTab.jsx                   # Main picks view with trial banner
    PickCard.jsx                   # Individual pick display
    NoPickCard.jsx                 # No-pick / pass day display
    TodayTab.jsx                   # Today's analysis view
    DashboardTab.jsx               # Dashboard overview
    FreeTierDashboard.jsx          # Blurred/limited view for free users
    UnifiedDashboard.jsx           # Combined dashboard view

    # Insights Tab
    InsightsTab.jsx                # Educational content + articles

    # Performance Tab
    PerformanceTab.jsx             # Model performance + user stats
    PickHistoryScreen.jsx          # Full pick history
    WeeklySummary.jsx              # Weekly performance summary
    ResolutionScreen.jsx           # Win/loss resolution coaching

    # Profile Tab
    ProfileTab.jsx                 # Account + subscription + trial signup + pricing
    UpgradeScreen.jsx              # Plan upgrade flow
    CancelScreen.jsx               # Cancellation flow with retention
    BetTrackingScreen.jsx          # Personal bet tracker
    NotificationsScreen.jsx        # Notification preferences
    ReferralScreen.jsx             # Referral program
    HowItWorksScreen.jsx           # Methodology explanation
    AnnualConversion.jsx           # Monthly -> annual upsell

    # Shared
    LoadingState.jsx               # Skeleton loading states
    EmptyState.jsx                 # Designed empty states
    ErrorStates.jsx                # Error handling displays
```

---

## 12. DESIGN SYSTEM

- **Background:** `#0A0D14` (dark navy)
- **Cards:** Subtle border with dark fill, no heavy shadows
- **Primary accent:** Blue gradient (`--blue-primary` to `--blue-deep`)
- **Typography:**
  - Serif: IBM Plex Serif (headlines)
  - Sans: Inter (body text)
  - Mono: JetBrains Mono (numbers, data)
- **Tone:** Calm, institutional — no FOMO, no exclamation marks, no "free" language in trial copy
- **Loading:** Skeleton states with pulse animation
- **Empty states:** Designed messaging with next-action guidance

---

## 13. COMPLIANCE & RISK

- Betting disclaimers integrated into UI and API responses
- No guarantee of results language
- Append-only audit trail for complete transparency
- Webhook signature verification for production Stripe events
- Secure password hashing (Werkzeug)
- Time-limited, signed tokens for password resets and email verification
- Session invalidation on password reset
- HTTPS-only in production
- CORS restricted to production domains
- Rate limiting on login attempts
- Sensitive fields (password_hash, session_token) stripped from backups

---

## 14. WNBA EXPANSION (In Development)

**Status:** Data collection complete, awaiting spread data for backtest

- 753 games collected (2022: 241, 2023: 248, 2024: 264)
- Walk-forward backtest pipeline ready
- Shrinkage sweep: 0.3 to 0.7
- Edge threshold sweep: 3.0% to 5.0%
- Go/no-go gate: requires positive ROI AND model adds value over market
- Decision: "Don't ship until backtest proves the model adds value"
- Paper-trade pass notifications active (via push)

---

## 15. ENVIRONMENT VARIABLES

### Required Secrets
| Key | Purpose |
|-----|---------|
| `STRIPE_LIVE_SECRET_KEY` | Stripe API (payments) |
| `STRIPE_LIVE_PUBLISHABLE_KEY` | Stripe frontend key |
| `STRIPE_PRICE_MONTHLY` | Monthly plan price ID |
| `STRIPE_PRICE_ANNUAL` | Standard annual plan price ID |
| `STRIPE_PRICE_FOUNDING` | Founding annual plan price ID |
| `RESEND_API_KEY` | Transactional email delivery |
| `BALLDONTLIE_API_KEY` | NBA stats API |
| `CRON_SECRET` | Secures all `/api/cron/*` endpoints |

### Optional Secrets
| Key | Purpose |
|-----|---------|
| `ONESIGNAL_APP_ID` | Push notifications (app ID) |
| `ONESIGNAL_API_KEY` | Push notifications (REST API key) |
| `ODDS_API_KEY` | Real-time sportsbook odds |
| `STRIPE_WEBHOOK_SECRET` | Webhook signature verification (production) |
