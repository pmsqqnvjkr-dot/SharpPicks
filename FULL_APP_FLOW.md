# Sharp Picks - Full Application Flow
*Generated February 16, 2026*

---

## 1. LANDING PAGE (Unauthenticated Users)

**URL:** `/`

Dark institutional-grade design on `#0A0D14` background. Top-level brand mark: shield icon + "SHARP PICKS."

### Hero Section
- Headline: **"One Pick Beats Five"**
- Subtitle: *"Discipline is the product."*
- CTA: Blue gradient "Start Free" button
- Sub-CTA: "Sign up free — no card required"

### Trust Bar
- `Active since Jan 2026 · All picks public · 0 deleted`

### Value Propositions (3 cards)
1. **No edge, no pick** — "We publish only when the model identifies sufficient value. Quiet days are intentional."
2. **Process over outcomes** — "All picks tracked publicly. No deletes. No hindsight editing. 9 picks · 23 passes to date"
3. *[Third card below fold]*

### Bottom CTA
- Links to registration with 14-day free trial

---

## 2. REGISTRATION / LOGIN

**Registration fields:** first_name, last_name, email, password

**On registration:**
- User created with `subscription_status: "trial"`, `is_premium: true`
- 14-day free trial begins immediately (no card required)
- `trial_end_date` set to 14 days from registration

**Login:** email + password, Flask-Login session with remember_me cookie (30 days)

**Password Reset:** Secure time-limited token flow via `/api/auth/forgot-password` and `/api/auth/reset-password`

---

## 3. AUTHENTICATED DASHBOARD (4-Tab Shell)

After login, users see the main dashboard with 4 tabs:

### Tab Navigation
| Tab | Icon | Content |
|-----|------|---------|
| **Picks** | Chart trend icon | Today's pick or no-pick state |
| **Insights** | Book icon | Educational content + discipline coaching |
| **Performance** | Bar chart icon | Model performance + bet tracking stats |
| **Profile** | User icon | Account, subscription, settings |

---

### 3A. PICKS TAB (Default)

**Active Pick State (when model finds edge):**
- Pick card showing: team, spread line, edge percentage, sportsbook
- Detailed analysis notes (rest days, scoring margins, defensive matchups)
- "Track This Bet" button for personal bet tracking
- Confidence level and model explanation

**No Pick / Pass State (most days):**
- Calm "no pick today" messaging
- What-if analysis: shows what the model's closest call was
- Pass reason documented

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
- Current plan display
- Trial status with end date
- Upgrade/downgrade options
- Cancel subscription flow

**Referral Program:**
- Personal referral code
- Referral tracking

---

## 4. SUBSCRIPTION SYSTEM

### Plans (via Stripe)
| Plan | Price | Stripe Price ID | Notes |
|------|-------|-----------------|-------|
| Monthly | $29/mo | `price_1T1E64PIYiKWXum1nyJsR3Dm` | Cancel anytime |
| Founding Annual | $99/yr | `price_1T1E65PIYiKWXum1rjMfedcX` | Locked forever, 500-member cap |
| Standard Annual | $149/yr | `price_1T1E65PIYiKWXum1bHp64sSp` | Standard annual rate |

### Flow
1. New user registers -> 14-day free trial (full access, no card)
2. Trial expiration -> prompted to subscribe
3. Checkout via Stripe-hosted page
4. Webhook confirms payment -> `subscription_status: "active"`
5. Founding members get `founding_member: true` + sequential `founding_number`

### Current Users
| Status | Count |
|--------|-------|
| Trial | 5 |
| Active (paid) | 1 (Founding #1) |
| Free (expired) | 3 |
| Cancelling | 1 |
| **Total** | **13** |

---

## 5. POST-CALIBRATION MODEL (Feb 12, 2026)

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

### Risk Filters
- High spread exclusion
- Missing data exclusion
- Stale data / imminent tip-off failsafe
- Line movement penalty: 1.0 per point moved, hard stop at 2.5pts

---

## 6. DATA ARCHITECTURE

### PostgreSQL (Primary - Application Data)
| Table | Records | Purpose |
|-------|---------|---------|
| `users` | 13 | User accounts, subscriptions, preferences |
| `picks` | 9 | Published predictions (append-only) |
| `passes` | 23 | No-pick days with what-if analysis (append-only) |
| `model_runs` | 31 | Every model execution logged |
| `referrals` | 0 | Referral tracking |

### SQLite (Legacy - ML Training)
- Historical NBA game data
- ML model training datasets
- WNBA backtest data (753 games across 2022-2024)

### Key Design Principles
- **Append-only:** Picks and passes never deleted or modified
- **Full transparency:** Complete audit trail of all predictions
- **Eastern Time:** All date logic standardized to America/New_York

---

## 7. API ENDPOINTS

### Authentication
| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/api/auth/register` | No | Create account + start trial |
| POST | `/api/auth/login` | No | Login with email/password |
| POST | `/api/auth/logout` | Yes | End session |
| GET | `/api/auth/user` | Yes | Get current user data |
| POST | `/api/auth/forgot-password` | No | Request password reset |
| POST | `/api/auth/reset-password` | No | Complete password reset |
| POST | `/api/auth/unit-size` | Yes | Set bet unit size |
| POST | `/api/auth/trial` | Yes | Trial management |
| GET | `/api/auth/check-trial` | Yes | Check trial status |

### Picks & Predictions
| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/api/predictions` | No | Today's published picks |
| GET | `/api/recent-results` | No | Last 5 resolved picks |
| GET | `/api/performance` | No | Overall win/loss record |
| GET | `/api/model/calibration` | No | Model calibration data |

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
| POST | `/api/subscriptions/create-checkout` | Yes | Start Stripe checkout |
| POST | `/api/subscriptions/cancel` | Yes | Cancel subscription |
| GET | `/api/subscriptions/status` | Yes | Current subscription state |
| GET | `/api/stripe/config` | No | Stripe publishable key |
| GET | `/api/stripe/products` | No | Available plans + prices |
| POST | `/webhooks/stripe` | No | Stripe webhook handler |

### Notifications & Profile
| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/api/user/notifications` | Yes | Notification preferences |
| POST | `/api/user/notifications` | Yes | Update notification prefs |

### Admin
| Path | Auth | Purpose |
|------|------|---------|
| `/admin` | Basic Auth | Admin dashboard (HTML) |
| `/api/admin/stats` | Admin | System statistics |
| `/api/admin/users/export` | Admin | Export user data |

---

## 8. SCHEDULED TASKS

| Job | Schedule | Purpose |
|-----|----------|---------|
| `collect_todays_games` | Multiple times daily | Fetch NBA schedule from ESPN |
| `collect_closing_lines` | Multiple times daily | Fetch current odds from 6 books |
| `grade_pending_picks` | Multiple times daily | Resolve picks with final scores |
| `grade_whatif_passes` | Daily | Grade what-if analysis on pass days |
| `check_data_quality` | Daily | Validate data freshness and integrity |

---

## 9. FRONTEND COMPONENT ARCHITECTURE

```
src/
  App.jsx                          # Router: / -> SharpPicksApp, /reset-password -> ResetPassword
  pages/
    SharpPicksApp.jsx              # Main app shell with auth routing
  hooks/
    useAuth.jsx                    # Authentication context + provider
    useSport.jsx                   # Sport selection context (NBA/future WNBA)
  components/sharp/
    LandingPage.jsx                # Marketing page for unauthenticated users
    AuthModal.jsx                  # Login/Register modal
    AppHeader.jsx                  # Top header bar
    TabNav.jsx                     # 4-tab navigation (Picks, Insights, Performance, Profile)
    OnboardingFlow.jsx             # First-time user onboarding
    
    # Picks Tab
    PicksTab.jsx                   # Main picks view
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
    ProfileTab.jsx                 # Account + subscription management
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

## 10. DESIGN SYSTEM

- **Background:** `#0A0D14` (dark navy)
- **Cards:** Subtle border with dark fill, no heavy shadows
- **Primary accent:** Blue gradient (`--blue-primary` to `--blue-deep`)
- **Typography:**
  - Serif: IBM Plex Serif (headlines)
  - Sans: Inter (body text)
  - Mono: JetBrains Mono (numbers, data)
- **Tone:** Calm, institutional — no FOMO, no exclamation marks
- **Loading:** Skeleton states with pulse animation
- **Empty states:** Designed messaging with next-action guidance

---

## 11. COMPLIANCE & RISK

- Betting disclaimers integrated into UI and API responses
- No guarantee of results language
- Append-only audit trail for complete transparency
- Webhook signature verification for production Stripe events
- Secure password hashing
- Time-limited reset tokens
- HTTPS-only in production

---

## 12. WNBA EXPANSION (In Development)

**Status:** Data collection complete, awaiting spread data for backtest

- 753 games collected (2022: 241, 2023: 248, 2024: 264)
- Walk-forward backtest pipeline ready
- Shrinkage sweep: 0.3 to 0.7
- Edge threshold sweep: 3.0% to 5.0%
- Go/no-go gate: requires positive ROI AND model adds value over market
- Decision: "Don't ship until backtest proves the model adds value"
